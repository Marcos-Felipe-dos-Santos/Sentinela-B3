"""Rendimento de 12 meses do FII pelo Informe Mensal da CVM (F2B-28).

Os números são os do exemplo do HGLG11 em `docs/metodologia/fii.md`, seção 5 (Informe de
2025 e 2026, maior versão de cada mês): valor da cota de 2025-09 a 2026-08 e DY do mês de
2025-10 a 2026-09; rendimento de 12 meses de R$ 13,240530 por cota.
"""

import zipfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from sentinela.data import normalizacao, rendimento_fii
from tests.test_market_engine_fii_cvm import INFORME, _cascata, _InformeFalso

# (mês, valor da cota no fim do mês, DY do mês)
HGLG = [
    ("2025-09-01", "162.498293", None),
    ("2025-10-01", "162.238907", "0.006769"),
    ("2025-11-01", "165.789389", "0.005901"),
    ("2025-12-01", "166.576588", "0.006635"),
    ("2026-01-01", "166.408892", "0.006604"),
    ("2026-02-01", "165.744203", "0.006610"),
    ("2026-03-01", "165.712611", "0.006637"),
    ("2026-04-01", "166.490023", "0.006477"),
    ("2026-05-01", "166.003651", "0.006607"),
    ("2026-06-01", "166.603103", "0.006626"),
    ("2026-07-01", "166.431221", "0.007023"),
    ("2026-08-01", "165.951408", "0.007027"),
    ("2026-09-01", "165.476630", "0.007052"),
]
PRECO = 147.86  # COTAHIST, 25/09/2026


def _registros(linhas=HGLG, versao="1"):
    return [
        {
            "Data_Referencia": mes,
            "Versao": versao,
            "Valor_Patrimonial_Cotas": cota,
            "Percentual_Dividend_Yield_Mes": dy,
        }
        for mes, cota, dy in linhas
    ]


def test_doze_meses_somam_os_rendimentos():
    resultado = rendimento_fii.rendimento_12_meses(_registros(), PRECO)
    assert resultado["rendimento_12m"] == pytest.approx(13.240530, abs=1e-5)
    assert resultado["dy"] == pytest.approx(0.089548, abs=1e-6)
    assert resultado["meses"] == 12
    assert resultado["mes_final"] == "2026-09"
    assert resultado["base"] == rendimento_fii.BASE


def test_mes_com_duas_versoes_usa_a_maior():
    # Reapresentações de 2026-04 (versões 9 e 10: como texto, "9" ganharia) e de 2026-03
    # (o valor da cota do mês anterior): a soma muda pelas duas maiores.
    reapresentados = _registros() + [
        {
            "Data_Referencia": "2026-04-01",
            "Versao": "10",
            "Valor_Patrimonial_Cotas": "166.490023",
            "Percentual_Dividend_Yield_Mes": "0.016477",
        },
        {
            "Data_Referencia": "2026-04-01",
            "Versao": "9",
            "Valor_Patrimonial_Cotas": "166.490023",
            "Percentual_Dividend_Yield_Mes": "0.026477",
        },
        {
            "Data_Referencia": "2026-03-01",
            "Versao": "9",
            "Valor_Patrimonial_Cotas": "175.712611",
            "Percentual_Dividend_Yield_Mes": "0.006637",
        },
        {
            "Data_Referencia": "2026-05-01",
            "Versao": "ilegível",
            "Valor_Patrimonial_Cotas": "1000",
            "Percentual_Dividend_Yield_Mes": "0.5",
        },
    ]
    resultado = rendimento_fii.rendimento_12_meses(reapresentados, PRECO)
    base = 13.240530
    abril = 0.016477 * 175.712611 - 0.006477 * 165.712611
    assert resultado["rendimento_12m"] == pytest.approx(base + abril, abs=1e-5)


@pytest.mark.parametrize(
    "linhas",
    [
        HGLG[1:],  # sem o valor da cota de 2025-09: 11 meses completos
        HGLG[:6] + HGLG[7:],  # buraco em 2026-02
        HGLG[:12] + [("2026-09-01", "165.476630", None)],  # DY do último mês ausente
        HGLG[:4] + [("2026-01-01", "0", "0.006604")] + HGLG[5:],  # cota zero
        HGLG[:12] + [("2026-09-01", "165.476630", True)],  # booleano não é número
    ],
)
def test_menos_de_doze_meses_abstem(linhas):
    assert rendimento_fii.rendimento_12_meses(
        _registros(linhas), PRECO
    ) == rendimento_fii.Abstencao(rendimento_fii.MOTIVO_MESES_INCOMPLETOS)


def test_sem_meses_ou_sem_preco_abstem():
    assert rendimento_fii.rendimento_12_meses([], PRECO) == rendimento_fii.Abstencao(
        rendimento_fii.MOTIVO_SEM_MESES
    )
    invalido = [{"Data_Referencia": "2026-13-01"}, {"Data_Referencia": "sem data"}, {}]
    assert rendimento_fii.rendimento_12_meses(
        invalido, PRECO
    ) == rendimento_fii.Abstencao(rendimento_fii.MOTIVO_SEM_MESES)
    for preco in (None, 0.0, -1.0, float("nan")):
        assert rendimento_fii.rendimento_12_meses(
            _registros(), preco
        ) == rendimento_fii.Abstencao(rendimento_fii.MOTIVO_PRECO)


def test_virada_de_ano_virgula_decimal_e_valores_abaixo_de_um():
    # Doze meses de 2025-01 a 2025-12: o primeiro usa a cota de 2024-12. Cota e preço
    # abaixo de 1 são válidos; registro sem data no começo da lista é ignorado.
    linhas = [("2024-12-01", "0,5", None)] + [
        (f"2025-{m:02d}-01", "0,5", "0,01") for m in range(1, 13)
    ]
    registros = [{"Data_Referencia": None}] + _registros(linhas)
    resultado = rendimento_fii.rendimento_12_meses(registros, "0,6")
    assert resultado["rendimento_12m"] == pytest.approx(0.06)
    assert resultado["dy"] == pytest.approx(0.1)
    assert resultado["mes_final"] == "2025-12"


def test_conversao_pela_fronteira(monkeypatch):
    resultado = rendimento_fii.rendimento_12_meses(_registros(), PRECO)
    assert resultado["conversao"] == normalizacao.proveniencia_dy("cvm_fii")
    assert (
        resultado["conversao"]["representacao"]
        == normalizacao.Representacao.RAZAO_INFORME_FII.value
    )
    # A representação é a declarada na fronteira, não uma conversão local.
    monkeypatch.setitem(
        normalizacao.REPRESENTACAO_DY, "cvm_fii", normalizacao.Representacao.PERCENTUAL
    )
    em_percentual = rendimento_fii.rendimento_12_meses(_registros(), PRECO)
    assert em_percentual["rendimento_12m"] == pytest.approx(0.13240530, abs=1e-7)


# ── provedor ─────────────────────────────────────────────────────────────────


class _Hoje(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 19)


def _zip(destino: Path, ano: int, linhas: list[dict]) -> Path:
    csv = pd.DataFrame(linhas).to_csv(sep=";", index=False).encode("latin-1")
    with zipfile.ZipFile(destino, "w") as zf:
        zf.writestr(f"inf_mensal_fii_complemento_{ano}.csv", csv)
    return destino


def test_provedor_le_o_ano_e_o_anterior(tmp_path, monkeypatch):
    import cvm_fii_provider
    from cvm_fii_provider import CVMFIIProvider

    cnpj = INFORME["cnpj_fundo"]
    registros = [{"CNPJ_Fundo_Classe": cnpj, **r} for r in _registros()]
    outro = {**registros[0], "CNPJ_Fundo_Classe": "00.000.000/0001-00"}
    zips = {
        2025: _zip(
            tmp_path / "2025.zip",
            2025,
            [r for r in registros if r["Data_Referencia"] < "2026"] + [outro],
        ),
        2026: _zip(
            tmp_path / "2026.zip",
            2026,
            [r for r in registros if r["Data_Referencia"] >= "2026"],
        ),
    }
    provedor = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(cvm_fii_provider, "date", _Hoje)
    monkeypatch.setattr(provedor, "baixar_informe", lambda ano: zips[ano])
    monkeypatch.setattr(
        provedor,
        "_proveniencia",
        lambda caminho, ano, linha: (ano, linha["Data_Referencia"]),
    )
    informe = provedor.obter_rendimentos_fii(cnpj)
    assert sorted(r["Data_Referencia"] for r in informe["registros"]) == [
        m for m, _, _ in HGLG
    ]
    assert informe["proveniencia"] == (2026, "2026-09-01")
    resultado = rendimento_fii.rendimento_12_meses(informe["registros"], PRECO)
    assert resultado["rendimento_12m"] == pytest.approx(13.240530, abs=1e-5)


@pytest.mark.parametrize("ano_corrente", ["vazio", "ilegivel"])
def test_provedor_no_comeco_do_ano_le_dois_anos_atras(
    tmp_path, monkeypatch, ano_corrente
):
    # Em 2027, antes do Informe de janeiro: o último mês é 2026-09 e a cota de 2025-09
    # está no Informe de 2025.
    import cvm_fii_provider
    from cvm_fii_provider import CVMFIIProvider

    class _Em2027(date):
        @classmethod
        def today(cls):
            return cls(2027, 1, 10)

    cnpj = INFORME["cnpj_fundo"]
    registros = [{"CNPJ_Fundo_Classe": cnpj, **r} for r in _registros()]
    zips = {
        2025: _zip(
            tmp_path / "2025.zip",
            2025,
            [r for r in registros if r["Data_Referencia"] < "2026"],
        ),
        2026: _zip(
            tmp_path / "2026.zip",
            2026,
            [r for r in registros if r["Data_Referencia"] >= "2026"],
        ),
        2027: _zip(tmp_path / "2027.zip", 2027, [{"CNPJ_Fundo_Classe": "x"}]),
    }
    lidos = []

    def baixar(ano):
        lidos.append(ano)
        if ano == 2027 and ano_corrente == "ilegivel":
            raise OSError("404")
        return zips[ano]

    provedor = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(cvm_fii_provider, "date", _Em2027)
    monkeypatch.setattr(provedor, "baixar_informe", baixar)
    monkeypatch.setattr(provedor, "_proveniencia", lambda caminho, ano, linha: ano)
    informe = provedor.obter_rendimentos_fii(cnpj)
    assert lidos == [2027, 2026, 2025]
    assert informe["proveniencia"] == 2026
    resultado = rendimento_fii.rendimento_12_meses(informe["registros"], PRECO)
    assert resultado["rendimento_12m"] == pytest.approx(13.240530, abs=1e-5)


def test_provedor_com_o_ano_corrente_le_so_dois_anos(tmp_path, monkeypatch):
    import cvm_fii_provider
    from cvm_fii_provider import CVMFIIProvider

    lidos = []
    cnpj = INFORME["cnpj_fundo"]
    linha = {"CNPJ_Fundo_Classe": cnpj, "Data_Referencia": "2026-01-01"}

    def baixar(ano):
        lidos.append(ano)
        return _zip(tmp_path / f"{ano}.zip", ano, [linha])

    provedor = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(cvm_fii_provider, "date", _Hoje)
    monkeypatch.setattr(provedor, "baixar_informe", baixar)
    monkeypatch.setattr(provedor, "_proveniencia", lambda caminho, ano, linha: ano)
    provedor.obter_rendimentos_fii(cnpj)
    assert lidos == [2026, 2025]


def test_provedor_sem_o_fundo_devolve_lista_vazia(tmp_path, monkeypatch):
    import cvm_fii_provider
    from cvm_fii_provider import CVMFIIProvider

    provedor = CVMFIIProvider(cache_dir=str(tmp_path / "cache"))
    monkeypatch.setattr(cvm_fii_provider, "date", _Hoje)

    def baixar(ano):
        if ano == 2026:
            raise OSError("sem rede")
        return _zip(
            tmp_path / "2025.zip",
            2025,
            [{"CNPJ_Fundo_Classe": "x", "Data_Referencia": "2025-01-01"}],
        )

    monkeypatch.setattr(provedor, "baixar_informe", baixar)
    assert provedor.obter_rendimentos_fii(INFORME["cnpj_fundo"]) == {
        "registros": [],
        "proveniencia": None,
    }


# ── cascata ──────────────────────────────────────────────────────────────────


class _InformeComRendimentos(_InformeFalso):
    def __init__(self, registros=None, erro=None):
        super().__init__(INFORME)
        self.registros, self.erro_rendimentos = registros, erro

    def obter_rendimentos_fii(self, cnpj):
        if self.erro_rendimentos:
            raise self.erro_rendimentos
        return {
            "registros": self.registros,
            "proveniencia": {"documento": "Informe Mensal"},
        }


def test_cascata_grava_o_rendimento_fora_do_prompt(monkeypatch):
    from ai_core import SentinelaAI

    dados = _cascata(monkeypatch, _InformeComRendimentos(_registros()))
    medida = dados["rendimento_fii_cvm"]
    assert medida["dy"] == pytest.approx(
        13.240530 / 90.0, abs=1e-6
    )  # preço do yfinance
    assert medida["proveniencia"] == {"documento": "Informe Mensal"}
    assert dados["dy"] == pytest.approx(0.09)  # o DY da cascata não muda
    assert "rendimento_fii_cvm" not in SentinelaAI._formatar_dados(None, dados)


def test_cascata_grava_a_abstencao(monkeypatch):
    dados = _cascata(monkeypatch, _InformeComRendimentos(_registros(HGLG[1:])))
    assert dados["rendimento_fii_cvm"] == {
        "abstencao": rendimento_fii.MOTIVO_MESES_INCOMPLETOS
    }


@pytest.mark.parametrize(
    "informe",
    [_InformeFalso(INFORME), _InformeComRendimentos(erro=OSError("sem rede"))],
)
def test_cascata_sem_rendimentos_deixa_a_chave_de_fora(monkeypatch, informe):
    dados = _cascata(monkeypatch, informe)
    assert "rendimento_fii_cvm" not in dados
    assert dados["vpa"] == 100.0  # o resto do Informe fica


# ── relatório do F1-12 ───────────────────────────────────────────────────────


def test_relatorio_mostra_o_dy_do_informe_ao_lado_do_da_cascata():
    from sentinela.reports.rastreabilidade import _texto_rendimento_fii

    medida = rendimento_fii.rendimento_12_meses(_registros(), PRECO)
    assert _texto_rendimento_fii(medida, 0.0936) == (
        "DY de 12 meses 8,95% pelo Informe (até 2026-09, rendimento de R$ 13,24 por cota, "
        f"sobre o {rendimento_fii.BASE}) contra 9,36% da cascata"
    )
    assert _texto_rendimento_fii(medida, None).endswith("contra n/d da cascata")
    assert _texto_rendimento_fii({"abstencao": "x"}, 0.09) == "não calculado: x"
