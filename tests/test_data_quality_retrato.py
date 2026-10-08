"""Retrato dos valores coletados (F2A-6, E-3): o relatório de qualidade avalia o que a cascata
entregou, não o que os motores sobrescreveram com `dados.update(analise)` (`app.py`)."""

import json

import pandas as pd
import pytest

from ai_core import SentinelaAI
from data_quality import DataQualityReport
from tests.test_market_engine import _engine, _historico

INFO = {
    "currentPrice": 20.0,
    "quoteType": "EQUITY",
    "trailingPE": 10.0,
    "priceToBook": 1.2,
    "returnOnEquity": 0.15,
    "dividendYield": 0.04,
}


def _cascata(monkeypatch):
    engine = _engine(monkeypatch, historico=_historico(20.0), info=INFO)
    return engine.buscar_dados_ticker("PETR4")


def test_saida_do_motor_nao_muda_o_que_o_relatorio_avalia(monkeypatch):
    dados = _cascata(monkeypatch)
    antes = DataQualityReport(dict(dados))
    completude, alertas = antes.completude(), antes.validacao_cruzada()

    dados.update(
        {"dy": 0.5, "pvp": 9.0, "lpa": 0.5}
    )  # como o app.py: dados.update(analise)

    depois = DataQualityReport(dados)
    assert depois.validacao_cruzada() == alertas
    assert depois.completude() == completude


def test_retrato_e_serializavel_em_json(monkeypatch):
    dados = _cascata(monkeypatch)
    retrato = dados["valores_coletados"]
    assert json.loads(json.dumps(retrato, allow_nan=False)) == retrato
    assert retrato["preco_atual"] == pytest.approx(20.0)
    assert retrato["dy"] == pytest.approx(0.04)
    assert retrato["pvp"] == pytest.approx(1.2)
    assert retrato["quote_type"] == "EQUITY"
    assert retrato["vacancia"] is None  # campo não coletado fica explícito


def test_retrato_e_uma_copia(monkeypatch):
    dados = _cascata(monkeypatch)
    dados.update({"dy": 0.5})
    assert dados["valores_coletados"]["dy"] == pytest.approx(0.04)


def test_retrato_troca_nao_finito_e_numpy_por_tipos_simples():
    from market_engine import _retrato

    retrato = _retrato(
        {"preco_atual": pd.Series([10.5]).iloc[0], "pl": float("nan"), "roe": float("inf"),
         "quote_type": "EQUITY", "dy": None}
    )  # fmt: skip
    assert retrato["preco_atual"] == 10.5 and type(retrato["preco_atual"]) is float
    assert retrato["pl"] is None and retrato["roe"] is None
    assert retrato["quote_type"] == "EQUITY"
    json.dumps(retrato, allow_nan=False)


def test_sem_retrato_o_relatorio_usa_dados():
    dados = {"preco_atual": 10.0, "dy": 0.5}
    assert any("dy=" in a for a in DataQualityReport(dados).validacao_cruzada())


def test_retrato_vale_para_a_completude():
    dados = {"preco_atual": 10.0, "pl": 5.0, "pvp": 1.0, "roe": 0.1, "dy": 0.05}
    dados["valores_coletados"] = {"preco_atual": 10.0, "pl": None, "pvp": None, "roe": None,
                                  "dy": None}  # fmt: skip
    completude = DataQualityReport(dados).completude()
    assert completude["campos"]["pl"]["presente"] is False
    assert completude["campos"]["preco_atual"]["presente"] is True


def test_retrato_fica_fora_do_prompt():
    texto = SentinelaAI.__new__(SentinelaAI)._formatar_dados(
        {"ticker": "TSTA3", "valores_coletados": {"dy": 0.04}}
    )
    assert "valores_coletados" not in texto


def test_retrato_vai_na_analise_gravada(monkeypatch):
    dados = _cascata(monkeypatch)
    dados.update({"dy": 0.5})
    gravado = json.loads(
        json.dumps({k: v for k, v in dados.items() if k != "historico"}, default=str)
    )
    assert gravado["valores_coletados"]["dy"] == pytest.approx(0.04)
    assert gravado["dy"] == pytest.approx(0.5)
