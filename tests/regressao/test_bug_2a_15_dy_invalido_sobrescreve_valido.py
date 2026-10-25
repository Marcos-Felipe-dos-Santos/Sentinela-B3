"""BUG-2A-15: DY finito mas fora de 0–25% de uma fonte posterior sobrescreve o DY válido.

O merge da brapi (`market_engine.MarketEngine._buscar_brapi`, `overwrite=True`) aceita
qualquer DY finito; o invariante dos motores (`config._normalizar_dy`) só o zera depois, e o
DY válido do yfinance se perde. Origem: auditoria externa da Fase 2A (Codex, 15/10/2026).
"""

import pytest

from tests.test_market_engine import FakeBrapi, _engine, _historico


def test_dy_fora_da_faixa_da_brapi_nao_apaga_o_do_yfinance(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(20.0),
        # yfinance: DY em percentual (F2A-16); 6,0 vira 0,06 na fronteira.
        info={"currentPrice": 20.0, "quoteType": "EQUITY", "dividendYield": 6.0},
        brapi=FakeBrapi({"dy": 0.40}),
    )
    dados = engine.buscar_dados_ticker("PETR4")
    assert dados["dy"] == pytest.approx(0.06)
