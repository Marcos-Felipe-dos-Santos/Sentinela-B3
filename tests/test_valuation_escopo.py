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
    with patch("valuation_engine.get_selic_atual", return_value=0.145):
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


def test_sem_classe_nada_muda():
    resultado = _processar()
    assert resultado["recomendacao"] != "FORA DO ESCOPO DOS MÉTODOS"
    assert resultado["metodos_usados"].startswith("Graham")
    assert {"fair_value", "upside", "score_final"} <= set(resultado)
    assert _processar(classe_ativo=None) == resultado


@pytest.mark.parametrize("classe", ["STOCK", "UNIT", AssetType.STOCK, "stock"])
def test_stock_e_unit_seguem_os_metodos(classe):
    assert _processar(classe_ativo=classe) == _processar()


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
        patch("valuation_engine.get_selic_atual", return_value=0.145),
        patch("fii_engine.get_selic_atual", return_value=0.145),
    ):
        contexto = rastreabilidade.construir_contexto(
            dados, False, date(2026, 10, 13), ValuationEngine(), FIIEngine()
        )
    motivo = "Classe ETF fora do escopo dos métodos de ação"
    assert all(m["nao_calculado"] == motivo for m in contexto["metodos"])
    assert contexto["sintese"] == [("Abstenção do motor", motivo)]
