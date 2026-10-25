"""Bancos no motor de ações pela lente de P/VP justificado (F2B-32; ficha bancos 1.1)."""

from unittest.mock import patch

import pytest
from apoio_bancos import AS_OF_GORDON, VPA, enriquecer_bancos

from valuation_engine import ValuationEngine

BANCO = {
    "ticker": "TSTB4",
    "preco_atual": 44.28,
    "roe": 0.21,
    "pl": 9.0,
    "pvp": 44.28 / VPA,
    "dy": 0.07,
}
INADIMPLENCIA = {
    "inadimplencia": 65_383_226_229.80 / 1_115_404_849_436.43,
    "ifdata": {
        "fonte": "BCB IF.data (Olinda), relatório 16",
        "data_base": "202606",
        "codinst": "C0080329",
        "proveniencia": ({"data_coleta": "2026-10-19T02:16:32+00:00"},),
        "motivos": {},
    },
}


def _processar(dados):
    with patch("valuation_engine.get_selic_atual", return_value=0.145):
        return ValuationEngine().processar(dados, as_of=AS_OF_GORDON)


def test_banco_recebe_a_lente_de_bancos():
    r = _processar(enriquecer_bancos({**BANCO, **INADIMPLENCIA}))
    assert r["fair_value"] == pytest.approx(26.35, abs=0.01)
    assert r["metodos_usados"] == "Bancos: R$26.35"
    assert r["upside"] == pytest.approx((26.346908251509 / 44.28 - 1) * 100, abs=0.1)
    assert not any(
        m in r["metodos_usados"] for m in ("Graham", "Bazin", "Lynch", "Gordon")
    )


def test_sem_ifdata_a_limitacao_aparece():
    r = _processar(enriquecer_bancos(BANCO))
    assert r["inadimplencia_ifdata"] == (
        "inadimplência IF.data não informada: IF.data não consultado"
    )
    assert r["fair_value"] == pytest.approx(26.35, abs=0.01)


@pytest.mark.parametrize("vpa", [None, 0.0, -1.0])
def test_banco_sem_vpa_se_abstem(vpa):
    dados = enriquecer_bancos(BANCO, vpa=vpa)
    r = _processar(dados)
    assert "Bancos" not in r["metodos_usados"]
    assert r["recomendacao"] == "FORA DO ESCOPO DOS MÉTODOS"
    assert not {"fair_value", "upside", "score_final"} & set(r)
    assert dados["bancos_diagnostico"]


@pytest.mark.parametrize("valor", [float("nan"), 1.5, -0.1, "5%"])
def test_inadimplencia_invalida_aparece_com_motivo(valor):
    dados = enriquecer_bancos({**BANCO, **INADIMPLENCIA, "inadimplencia": valor})
    r = _processar(dados)
    assert r["inadimplencia_ifdata"].startswith(
        "inadimplência IF.data não informada: fora do domínio"
    )
    assert r["fair_value"] == pytest.approx(26.35, abs=0.01)


def test_inadimplencia_valida_aparece_sem_mudar_o_valor():
    com = _processar(enriquecer_bancos({**BANCO, **INADIMPLENCIA}))
    sem = _processar(enriquecer_bancos(BANCO))
    assert com["inadimplencia_ifdata"] == (
        "inadimplência IF.data (carteira ativa inadimplida arrastada ÷ Total Geral, "
        "relatório 16, conglomerado C0080329, data-base 06/2026): 5,86%"
    )
    assert {k: v for k, v in com.items() if k != "inadimplencia_ifdata"} == {
        k: v for k, v in sem.items() if k != "inadimplencia_ifdata"
    }


def test_basileia_nao_entra_na_saida_da_lente():
    r = _processar(enriquecer_bancos({**BANCO, **INADIMPLENCIA, "basileia": 0.0}))
    assert r["fair_value"] == pytest.approx(26.35, abs=0.01)
    assert not any("basileia" in str(x).lower() for x in r.values())


def test_classes_preferenciais_distintas_abstem():
    dados = enriquecer_bancos({**BANCO, "classes_preferenciais": ["PNA", "PNB"]})
    r = _processar(dados)
    assert "Bancos" not in r["metodos_usados"]
    assert dados["bancos_diagnostico"] == "classes com direitos distintos na fase 2B"


def test_unit_de_banco_usa_o_vpa_da_unit():
    dados = enriquecer_bancos(
        {**BANCO, "classe_ativo": "UNIT", "acoes_por_unit": {"ON": 1, "PN": 1}},
        vpa=2 * VPA,
        fator_unit=2,
    )
    r = _processar(dados)
    assert r["fair_value"] == pytest.approx(2 * 26.346908251509, abs=0.01)


def test_relatorio_mostra_a_lente_e_a_inadimplencia():
    from datetime import date

    from fii_engine import FIIEngine
    from sentinela.reports import rastreabilidade

    motor = ValuationEngine()
    original = motor.processar
    motor.processar = lambda d: original(d, as_of=AS_OF_GORDON)
    dados = enriquecer_bancos({**BANCO, **INADIMPLENCIA, "fonte_preco": "yfinance"})
    with patch("valuation_engine.get_selic_atual", return_value=0.145):
        contexto = rastreabilidade.construir_contexto(
            dados, False, date(2026, 10, 20), motor, FIIEngine()
        )
    bancos = next(m for m in contexto["metodos"] if m["nome"] == "Bancos")
    assert bancos["valor"] == "R$ 26,35"
    assert dict(bancos["intermediarios"])["pvp_justificado"].startswith("1,42")
    assert dict(contexto["fontes"])["DFP da lente de bancos"].startswith(
        "exercício 2025-01-01 a 2025-12-31, entrega 2026-02-12"
    )
    sintese = dict(contexto["sintese"])
    assert sintese["Inadimplência (IF.data, só leitura; não altera o valor)"].endswith(
        "data-base 06/2026): 5,86%"
    )


def test_relatorio_mostra_o_motivo_da_fronteira_no_bloco_da_lente():
    from datetime import date

    from fii_engine import FIIEngine
    from sentinela.reports import rastreabilidade

    motor = ValuationEngine()
    original = motor.processar
    motor.processar = lambda d: original(d, as_of=AS_OF_GORDON)
    dados = enriquecer_bancos(
        {**BANCO, "fonte_preco": "yfinance", "classes_preferenciais": ["PNA", "PNB"]}
    )
    with patch("valuation_engine.get_selic_atual", return_value=0.145):
        contexto = rastreabilidade.construir_contexto(
            dados, False, date(2026, 10, 20), motor, FIIEngine()
        )
    bancos = next(m for m in contexto["metodos"] if m["nome"] == "Bancos")
    assert bancos["abstencao"] == "classes com direitos distintos na fase 2B"


def test_diagnostico_antigo_nao_fica_depois_de_um_calculo():
    dados = enriquecer_bancos({**BANCO, "classes_preferenciais": ["PNA", "PNB"]})
    _processar(dados)
    assert dados["bancos_diagnostico"]
    dados["classes_preferenciais"] = []
    dados["gordon_cvm"]["vpa"] = 0.0  # a fronteira passa e a lente se abstém
    _processar(dados)
    assert dados["bancos_diagnostico"] == "VPA CVM não positivo"


@pytest.mark.parametrize(
    ("ifdata", "motivo"),
    [
        ({**INADIMPLENCIA["ifdata"], "proveniencia": ()}, "coleta não demonstrada até o as_of"),
        ({**INADIMPLENCIA["ifdata"], "proveniencia": ({"data_coleta": "2026-10-21T00:00:00+00:00"},)}, "coleta não demonstrada até o as_of"),
    ],
)  # fmt: skip
def test_inadimplencia_sem_coleta_ate_o_as_of_nao_e_informada(ifdata, motivo):
    r = _processar(enriquecer_bancos({**BANCO, **INADIMPLENCIA, "ifdata": ifdata}))
    assert r["inadimplencia_ifdata"] == f"inadimplência IF.data não informada: {motivo}"


def test_falha_do_ifdata_chega_com_o_motivo(monkeypatch):
    from datetime import UTC, datetime

    from tests.test_market_engine import _engine

    class _Falha:
        def capital(self, cnpj, data_referencia, *, as_of):
            raise OSError("sem rede")

    engine = _engine(monkeypatch, info={"currentPrice": 20.0})
    engine.ifdata = _Falha()
    dados = {"setor": "Bancos", "cnpj": "00.000.000/0001-91", "riscos_dados": []}
    engine._buscar_ifdata(dados, as_of=datetime(2026, 10, 13, 12, tzinfo=UTC))
    r = _processar(enriquecer_bancos({**BANCO, **dados}))
    assert r["inadimplencia_ifdata"] == (
        "inadimplência IF.data não informada: IF.data indisponível: sem rede"
    )
