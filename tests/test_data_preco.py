"""F3-A-F3 (BUG-3-16): a data do preço sai da fronteira da cascata e chega ao registro."""

import logging
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

import market_engine
from market_engine import MOTIVO_SEM_DATA, MarketEngine, _data_do_fechamento
from sentinela.data import normalizacao
from sentinela.data.store import migracoes, resultados
from sentinela.services.analyze_asset import AnalysisService
from tests.test_market_engine import FakeBrapi, FakeTicker, _engine

AGORA = datetime(2026, 11, 10, 15, tzinfo=UTC)


def _historico(indice):
    return pd.DataFrame({"Close": [20.0, 22.0]}, index=indice)


def _yfinance(monkeypatch, info=None, historico=None):
    ticker = FakeTicker(info=info, historico=historico)
    monkeypatch.setattr(market_engine, "yf", SimpleNamespace(Ticker=lambda *_: ticker))
    motor = MarketEngine.__new__(MarketEngine)
    dados = {}
    motor._buscar_yfinance("TSTA3", dados)
    return dados


def test_historico_com_data_grava_a_data_e_nenhum_motivo(monkeypatch):
    dados = _yfinance(
        monkeypatch, historico=_historico(pd.to_datetime(["2026-11-09", "2026-11-10"]))
    )
    assert dados["data_preco"] == "2026-11-10"
    assert "motivo_data_preco" not in dados


def test_historico_sem_data_legivel_grava_o_motivo(monkeypatch):
    dados = _yfinance(monkeypatch, historico=_historico([0, 1]))
    assert dados["preco_atual"] == 22.0
    assert "data_preco" not in dados
    assert dados["motivo_data_preco"] == MOTIVO_SEM_DATA["yfinance_historico"]


def test_current_price_sem_historico_grava_o_motivo(monkeypatch):
    dados = _yfinance(monkeypatch, info={"currentPrice": 21.0})
    assert dados["preco_atual"] == 21.0
    assert "data_preco" not in dados
    assert dados["motivo_data_preco"] == "yfinance: currentPrice sem data do fechamento"


def test_preco_da_brapi_grava_o_motivo(monkeypatch):
    engine = _engine(
        monkeypatch, info={}, brapi=FakeBrapi(resposta={"preco_atual": 30.0, "pl": 8.0})
    )
    dados = engine.buscar_dados_ticker("PETR4")
    assert dados["preco_atual"] == 30.0
    assert dados.get("data_preco") is None
    assert dados["motivo_data_preco"] == "brapi: preço sem data do fechamento"


@pytest.fixture
def conn():
    with closing(sqlite3.connect(":memory:")) as conexao:
        migracoes.aplicar(conexao)
        yield conexao


def _servico(conn, mercado):
    valuation = Mock()
    valuation.processar.return_value = {
        "apresentacao_versao": "1.0",
        "lentes": {"graham": {"valor": 20.0, "abstencao": None, "versao": "2.1.0"}},
    }
    tech = Mock()
    tech.calcular_indicadores.return_value = {}
    classe = SimpleNamespace(is_fii=lambda *a, **k: False)
    return AnalysisService(
        mercado, valuation, Mock(), tech, asset_classifier=classe, hoje=AGORA.date(),
        conexao_resultados=conn,
    )  # fmt: skip


def test_cascata_ate_o_registro_leva_a_data_do_fechamento(monkeypatch, conn):
    historico = _historico(pd.to_datetime(["2026-11-06", "2026-11-09"]))
    engine = _engine(monkeypatch, info={"quoteType": "EQUITY"}, historico=historico)
    _servico(conn, engine).analisar("PETR4", AGORA)
    (registro,) = resultados.buscar(conn, "PETR4", metodo="graham")
    assert registro.proveniencia["fonte_preco"] == "yfinance"
    assert registro.proveniencia["data_preco"] == "2026-11-09"
    assert registro.proveniencia["motivo_data_preco"] is None


def test_registro_sem_data_nem_motivo_recebe_motivo_explicito(conn):
    mercado = Mock(spec=["buscar_dados_ticker"])
    mercado.buscar_dados_ticker.return_value = {
        "ticker": "TSTA3",
        "preco_atual": 10,
        "classe_ativo": "STOCK",
    }
    _servico(conn, mercado).analisar("TSTA3", AGORA)
    (registro,) = resultados.buscar(conn, "TSTA3", metodo="graham")
    assert registro.proveniencia["data_preco"] is None
    assert registro.proveniencia["motivo_data_preco"] == "data do preço não informada"


def test_data_do_fechamento_recusa_nat():
    assert _data_do_fechamento(pd.NaT) is None
    assert _data_do_fechamento(pd.Timestamp("2026-11-10")) == "2026-11-10"


def test_fechamento_invalido_do_yfinance_e_preco_da_brapi_sem_a_data_do_yfinance(
    monkeypatch,
):
    historico = pd.DataFrame(
        {"Close": [20.0, float("nan")]},
        index=pd.to_datetime(["2026-11-09", "2026-11-10"]),
    )
    engine = _engine(
        monkeypatch,
        info={},
        historico=historico,
        brapi=FakeBrapi(resposta={"preco_atual": 30.0}),
    )
    dados = engine.buscar_dados_ticker("PETR4")
    assert dados["preco_atual"] == 30.0
    assert "data_preco" not in dados
    assert dados["motivo_data_preco"] == MOTIVO_SEM_DATA["brapi"]


# --- contrato do `_buscar_brapi` (gate de mutação do item) -----------------------------


class _Brapi:
    disponivel = True

    def __init__(self, resposta=None, erro=None):
        self.resposta, self.erro, self.pedidos = resposta, erro, []

    def get_fundamentals(self, ticker):
        self.pedidos.append(ticker)
        if self.erro:
            raise self.erro
        return self.resposta


def _motor_brapi(brapi):
    motor = MarketEngine.__new__(MarketEngine)
    motor.brapi = brapi
    return motor


def test_brapi_indisponivel_avisa_e_devolve_falso(caplog):
    brapi = _Brapi()
    brapi.disponivel = False
    with caplog.at_level(logging.WARNING, logger=market_engine.logger.name):
        assert _motor_brapi(brapi)._buscar_brapi("TSTA3", {}) is False
    assert caplog.messages == ["[TSTA3] Brapi indisponivel: BRAPI_TOKEN ausente"]
    assert brapi.pedidos == []


def test_brapi_sem_resposta_devolve_falso():
    brapi = _Brapi(resposta={})
    assert _motor_brapi(brapi)._buscar_brapi("TSTA3", {}) is False
    assert brapi.pedidos == ["TSTA3"]


def test_brapi_com_erro_avisa_e_devolve_falso(caplog):
    with caplog.at_level(logging.WARNING, logger=market_engine.logger.name):
        assert (
            _motor_brapi(_Brapi(erro=ValueError("fora")))._buscar_brapi("TSTA3", {})
            is False
        )
    assert caplog.messages == ["[TSTA3] Brapi error: fora"]


def test_brapi_guarda_o_que_entregou_e_a_proveniencia_do_roe(caplog):
    brapi = _Brapi(
        resposta={"preco_atual": 30.0, "pl": 8.0, "roe": 0.15, "quote_type": "EQUITY"}
    )
    dados = {}
    with caplog.at_level(logging.INFO, logger=market_engine.logger.name):
        assert _motor_brapi(brapi)._buscar_brapi("TSTA3", dados) is True
    assert dados["valores_por_fonte"]["brapi"]["preco_atual"] == 30.0
    assert dados["valores_por_fonte"]["brapi"]["pl"] == 8.0
    assert dados["proveniencia"]["roe"] == normalizacao.proveniencia_roe("brapi")
    assert dados["preco_atual"] == 30.0 and dados["fonte_preco"] == "brapi"
    assert "[TSTA3] Brapi definiu 2 fundamentos" in caplog.messages
