"""Contratos de calendário, modelo D20 e disponibilidade por campo (F2C-29/31).

Metadados CVM definem início/fim/referência; hipóteses e contas sintéticas explícitas,
sem rede ou método de valuation como esperado.
"""

from datetime import date
from types import SimpleNamespace

import pytest
import requests

from cvm_provider import CVMProvider
from tests.test_cvm_series import CD_CVM, _Hoje, _ind, _zip
from tests.test_market_engine import _engine


@pytest.mark.parametrize(
    "inicio,fim,esperado",
    [
        ("2025-03-01", "2026-02-28", 2026),
        ("2025-04-01", "2026-03-31", 2026),
        ("2026-01-01", "2026-12-31", 2025),
        ("2026-01-01", "2026-09-30", 2025),
        ("2025-03-02", "2026-02-28", 2025),
    ],
)
def test_exercicio_anual_e_periodo_completo_encerrado(
    tmp_path, monkeypatch, inicio, fim, esperado
):
    dre = [
        (
            fim,
            "1",
            "ÚLTIMO",
            inicio,
            fim,
            "3.11",
            "Lucro/Prejuízo Consolidado do Período",
            100,
        )
    ]
    caminho = _zip(tmp_path / "dfp.zip", "dfp", 2026, dre, [])
    p = CVMProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(p, "baixar_dfp", lambda ano: caminho)
    assert p.exercicio_anual_mais_recente(CD_CVM, date(2026, 10, 26)) == esperado
    assert p.exercicio_anual_mais_recente(CD_CVM + 1, date(2026, 10, 26)) == 2025


@pytest.mark.parametrize("status", [404, 500])
def test_somente_404_demonstra_arquivo_anual_ausente(tmp_path, monkeypatch, status):
    p = CVMProvider(cache_dir=str(tmp_path / "cache"))
    erro = requests.HTTPError(
        "falha de fonte", response=SimpleNamespace(status_code=status)
    )

    def fonte(ano):
        raise erro

    monkeypatch.setattr(p, "baixar_dfp", fonte)
    if status == 404:
        assert p.exercicio_anual_mais_recente(CD_CVM, date(2026, 10, 26)) == 2025
    else:
        with pytest.raises(requests.HTTPError):
            p.exercicio_anual_mais_recente(CD_CVM, date(2026, 10, 26))


def test_quatro_exercicios_declaram_a_lacuna_sem_deslocar_ano(monkeypatch):
    class Fonte:
        def indicadores_da_serie(self, *args):
            return {a: _ind(a) for a in range(2022, 2026)}

        def acumulados_ttm(self, *args):
            return []

    monkeypatch.setattr("market_engine.date", _Hoje)
    e = _engine(monkeypatch, info={})
    dados = {}
    e._serie_cvm("TSTA3", dados, Fonte(), CD_CVM, "empresa")
    assert dados["serie_cvm"]["cobertura"] == {
        "esperados": 5,
        "disponiveis": 4,
        "anos_ausentes": [2021],
    }
    assert [a["exercicio"] for a in dados["serie_cvm"]["exercicios"]] == [
        2022,
        2023,
        2024,
        2025,
    ]


def test_cascata_passa_modelo_banco_a_serie_e_ao_ttm(monkeypatch):
    chamadas = []

    class Banco:
        def indicadores_da_serie(self, codigo, ano, modelo):
            chamadas.append(("serie", modelo))
            return {}

        def acumulados_ttm(self, codigo, referencia, modelo):
            chamadas.append(("ttm", modelo))
            return []

        def calcular_indicadores(self, codigo, anos=1, modelo="empresa"):
            chamadas.append(("anual", modelo))
            return {}

    e = _engine(monkeypatch, info={}, cvm=Banco())
    e._buscar_cvm("ITUB4", {"cd_cvm": 19348, "setor": "Bancos"})
    assert chamadas == [("serie", "banco"), ("ttm", "banco"), ("anual", "banco")]


def test_ttm_banco_le_lucro_consolidado_pelo_par_correto(tmp_path):
    dt = "2025-03-31"
    inicio = "2025-01-01"
    dre = [
        (
            dt,
            "1",
            "ÚLTIMO",
            inicio,
            dt,
            "3.09",
            "Lucro/Prejuízo Consolidado do Período",
            100,
        ),
        (
            dt,
            "1",
            "ÚLTIMO",
            inicio,
            dt,
            "3.09.01",
            "Atribuído a Sócios da Empresa Controladora",
            80,
        ),
    ]
    caminho = _zip(tmp_path / "itr.zip", "itr", 2025, dre, [])
    p = CVMProvider(cache_dir=str(tmp_path / "cache"))
    (banco,) = p._acumulados_do_arquivo(caminho, "ITR", CD_CVM, "banco")
    assert banco.valores["lucro_liquido"] == 100_000
    assert banco.valores["lucro_controladores"] == 80_000
    assert banco.valores["receita_liquida"] is None
    assert banco.proveniencia["lucro_liquido"]["modelo"] == "banco"
    (empresa,) = p._acumulados_do_arquivo(caminho, "ITR", CD_CVM, "empresa")
    assert empresa.valores["lucro_liquido"] is None


@pytest.mark.parametrize("erro", [OSError, KeyError, ValueError])
def test_falha_ttm_nao_apaga_serie_anual(monkeypatch, erro):
    class Fonte:
        def indicadores_da_serie(self, *args):
            return {ano: _ind(ano) for ano in range(2021, 2026)}

        def acumulados_ttm(self, *args):
            raise erro("fonte TTM indisponível")

    monkeypatch.setattr("market_engine.date", _Hoje)
    dados = {}
    _engine(monkeypatch, info={})._serie_cvm("TSTA3", dados, Fonte(), CD_CVM, "empresa")
    assert dados["serie_cvm"]["cobertura"] == {
        "esperados": 5,
        "disponiveis": 5,
        "anos_ausentes": [],
    }
    assert [e["exercicio"] for e in dados["serie_cvm"]["exercicios"]] == [
        2021,
        2022,
        2023,
        2024,
        2025,
    ]
    assert "fonte TTM indisponível" in dados["ttm_cvm"]["abstencao"]


def test_interface_ttm_ausente_preserva_serie(monkeypatch):
    fonte = SimpleNamespace(
        indicadores_da_serie=lambda *a: {2025: _ind(2025)}, acumulados_ttm=None
    )
    monkeypatch.setattr("market_engine.date", _Hoje)
    dados = {}
    _engine(monkeypatch, info={})._serie_cvm("TSTA3", dados, fonte, CD_CVM, "empresa")
    assert [e["exercicio"] for e in dados["serie_cvm"]["exercicios"]] == [2025]
    assert dados["ttm_cvm"]["abstencao"] == "interface TTM indisponível no provedor"


@pytest.mark.parametrize("etapa", ["serie_anual", "ttm"])
@pytest.mark.parametrize("erro", [KeyError, ValueError])
def test_erro_na_transformacao_pura_nao_vira_falha_de_fonte(monkeypatch, etapa, erro):
    from sentinela.data import series_cvm

    fonte = SimpleNamespace(
        indicadores_da_serie=lambda *a: {}, acumulados_ttm=lambda *a: []
    )

    def quebrado(*args, **kwargs):
        raise erro("erro na transformação pura")

    monkeypatch.setattr(series_cvm, etapa, quebrado)
    e = _engine(monkeypatch, info={}, cvm=fonte)
    with pytest.raises(erro, match="erro na transformação pura"):
        e._buscar_cvm("TSTA3", {"cd_cvm": CD_CVM})
