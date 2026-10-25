"""Classe fora do escopo dos métodos de ação (F2A-29, P7).

ETF, BDR e `UNKNOWN` chegam ao motor de ações (o `app.py`, travado, manda tudo que não é FII):
o motor se abstém antes de qualquer método, sem número no lugar da abstenção.
"""

from datetime import date
from unittest.mock import patch

import pytest

from sentinela.domain.enums import AssetType
from valuation_engine import ValuationEngine

DADOS = {
    "ticker": "TST3",
    "preco_atual": 100.0,
    "roe": 0.15,
    "pl": 10.0,
    "pvp": 1.5,
    "dy": 0.08,
}


def _processar(**extra):
    return ValuationEngine().processar({**DADOS, **extra})


@pytest.mark.parametrize("classe", ["ETF", "BDR", "UNKNOWN"])
def test_etf_bdr_e_unknown_se_abstem(classe):
    resultado = _processar(classe_ativo=classe)
    assert resultado["recomendacao"] == "FORA DO ESCOPO DOS MÉTODOS"
    assert resultado["metodos_usados"] == ""
    assert resultado["confianca"] == 0
    assert resultado["pl_confiavel"] is False and resultado["dy_confiavel"] is False
    assert resultado["riscos"] == [
        f"Classe {classe} fora do escopo dos métodos de ação"
    ]
    assert classe in resultado["perfil"]


def test_sem_classe_abstem_com_ou_sem_a_chave():
    # F2B-4: a classe oficial é exigida; sem ela, abstenção (antes, nada mudava).
    resultado = _processar(modelo_bpp="empresa")
    assert resultado["recomendacao"] == "FORA DO ESCOPO DOS MÉTODOS"
    assert resultado["riscos"] == ["classe do ativo não informada"]
    assert not {"fair_value", "upside", "score_final"} & set(resultado)
    assert _processar(classe_ativo=None, modelo_bpp="empresa") == resultado


@pytest.mark.parametrize("classe", ["STOCK", "UNIT", AssetType.STOCK, "stock"])
def test_stock_e_unit_seguem_os_metodos(classe):
    resultado = _processar(classe_ativo=classe, modelo_bpp="empresa")
    assert resultado["metodos_usados"].startswith("Graham")
    assert resultado == _processar(classe_ativo="STOCK", modelo_bpp="empresa")


@pytest.mark.parametrize("classe", ["ETF", "bdr", AssetType.UNKNOWN])
def test_abstencao_nao_traz_numero(classe):
    resultado = _processar(classe_ativo=classe)
    assert resultado["recomendacao"] == "FORA DO ESCOPO DOS MÉTODOS"
    assert not {"fair_value", "upside", "score_final"} & set(resultado)
    assert "compra" not in resultado["recomendacao"].lower()
    assert "venda" not in resultado["recomendacao"].lower()


def test_relatorio_mostra_a_abstencao_e_o_motivo():
    from fii_engine import FIIEngine
    from sentinela.reports import rastreabilidade

    dados = {**DADOS, "classe_ativo": "ETF", "fonte_preco": "yfinance"}
    with (
        patch("fii_engine.get_selic_atual", return_value=0.145),
    ):
        contexto = rastreabilidade.construir_contexto(
            dados, False, date(2026, 10, 13), ValuationEngine(), FIIEngine()
        )
    motivo = "Classe ETF fora do escopo dos métodos de ação"
    assert all(m["nao_calculado"] == motivo for m in contexto["metodos"])
    assert contexto["sintese"] == [("Abstenção do motor", motivo)]


@pytest.mark.parametrize("modelo", ["banco", "seguradora", None])
def test_banco_e_seguradora_nao_recebem_metodos_de_empresa(modelo):
    resultado = _processar(classe_ativo="STOCK", modelo_bpp=modelo)
    assert not {"fair_value", "upside", "score_final"} & set(resultado)
    assert resultado["metodos_usados"] == ""
    assert resultado["riscos"]


def test_classe_com_espacos_e_reconhecida():
    resultado = _processar(classe_ativo=" ETF")
    assert not {"fair_value", "upside", "score_final"} & set(resultado)


def test_abstencao_por_escopo_nao_traz_numero():
    resultado = _processar(classe_ativo="STOCK")
    assert not {"fair_value", "upside", "score_final"} & set(resultado)


# ── escopo pelo modelo do BPP consolidado (F2B-4) ────────────────────────────

_EMPRESA = {"classe_ativo": "STOCK", "modelo_bpp": "empresa"}
_PROVENIENCIA = {
    "data_entrega": "2026-02-12",
    "data_coleta": "2026-02-20T18:00:00+00:00",
}


def test_mesmo_setor_com_bpp_diferente():
    setor = "Seguradoras e Corretoras"
    empresa = _processar(**_EMPRESA, setor=setor)
    seguradora = _processar(classe_ativo="STOCK", modelo_bpp="seguradora", setor=setor)
    assert empresa["metodos_usados"].startswith("Graham")
    assert seguradora["riscos"] == [
        "modelo seguradora fora do escopo dos métodos de empresa"
    ]
    assert not {"fair_value", "upside", "score_final"} & set(seguradora)


@pytest.mark.parametrize("classe", ["STOCK", "UNIT", " stock "])
def test_bpp_de_empresa_segue_os_metodos(classe):
    # Fora do índice (classe do classificador) ou holding: vale o BPP de empresa.
    resultado = _processar(classe_ativo=classe, modelo_bpp="empresa", setor="Holdings")
    assert resultado["metodos_usados"].startswith("Graham")
    assert {"fair_value", "upside", "score_final"} <= set(resultado)


@pytest.mark.parametrize(
    "proveniencia",
    [
        {**_PROVENIENCIA, "data_entrega": "2026-03-01"},
        {**_PROVENIENCIA, "data_coleta": "2026-03-02T18:00:00+00:00"},
        {**_PROVENIENCIA, "data_entrega": None},
        None,
    ],
)
def test_evidencia_do_bpp_posterior_ao_as_of_abstem(proveniencia):
    from datetime import UTC, datetime

    resultado = ValuationEngine().processar(
        {**DADOS, **_EMPRESA, "modelo_bpp_proveniencia": proveniencia},
        as_of=datetime(2026, 3, 1, 18, tzinfo=UTC),
    )
    assert resultado["riscos"] == [
        "disponibilidade do BPP consolidado não demonstrada até o as_of"
    ]
    assert not {"fair_value", "upside", "score_final"} & set(resultado)


def test_evidencia_do_bpp_anterior_ao_as_of_segue():
    from datetime import UTC, datetime

    resultado = ValuationEngine().processar(
        {**DADOS, **_EMPRESA, "modelo_bpp_proveniencia": _PROVENIENCIA},
        as_of=datetime(2026, 3, 1, 18, tzinfo=UTC),
    )
    assert resultado["metodos_usados"].startswith("Graham")


def test_relatorio_mostra_o_escopo_com_o_modelo_e_a_classe():
    from fii_engine import FIIEngine
    from sentinela.reports import rastreabilidade

    def contexto(dados):
        with (
            patch("fii_engine.get_selic_atual", return_value=0.145),
        ):
            return rastreabilidade.construir_contexto(
                {**DADOS, "fonte_preco": "yfinance", **dados},
                False,
                date(2026, 10, 13),
                ValuationEngine(),
                FIIEngine(),
            )

    seguradora = contexto({"classe_ativo": "STOCK", "modelo_bpp": "seguradora"})
    escopos = {m["nome"]: m["applies_to"] for m in seguradora["metodos"]}
    assert escopos["Graham"] == "STOCK, UNIT; modelo empresa (BPP consolidado)"
    assert escopos["Bancos"] == "STOCK, UNIT; modelo banco (BPP consolidado)"
    assert seguradora["classe"] == "ação"
    assert seguradora["sintese"] == [
        (
            "Abstenção do motor",
            "modelo seguradora fora do escopo dos métodos de empresa",
        )
    ]
    etf = contexto({"classe_ativo": "ETF"})
    assert etf["classe"] == "ETF, fora do escopo dos métodos de ação"
    assert contexto({})["classe"] == "classe não informada"
