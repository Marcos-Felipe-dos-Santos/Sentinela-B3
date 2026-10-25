"""Valores ≤ 0 da CVM na cascata (F2B-8; BUG-2A-01; [AUDITORIA] em (a), decisão de 18/10/2026).

Ausente, em `pl`, `pvp`, `roe`, `lpa` e `vpa`, é só `None` ou não finito. O prejuízo e o PL
negativo que a CVM apurou vencem o valor positivo do yfinance, da brapi ou do cache, e não
contam como campo faltando; cada método se abstém pela própria regra.
"""

import pytest

from market_engine import list_missing_required_fields
from tests.test_market_engine import FakeCache
from tests.test_market_engine_acoes_cvm import PRECO, _ind, _motor

# Prejuízo: lucro dos controladores −2.000 e LPA divulgado −2,1; PL dos controladores
# 10.000, ações 1.000 → LPA recalculado −2,0 e VPA 10,0.
PREJUIZO = {
    "lucro_liquido": -2_500.0,
    "lucro_controladores": -2_000.0,
    "roe": -0.2,
    "lpa_divulgado": {"especie": "ON", "conta": "3.99.01.01", "valor": -2.1},
}
YFINANCE = {"trailingPE": 8.0, "returnOnEquity": 0.10, "dividendYield": 4.0}


def _cascata(monkeypatch, cache=None, yfinance=YFINANCE):
    engine = _motor(monkeypatch, _ind(**PREJUIZO), info_extra=yfinance)
    engine.database = cache
    return engine.buscar_dados_ticker("PETR4")


def test_prejuizo_da_cvm_nao_e_trocado_por_valor_positivo(monkeypatch):
    dados = _cascata(monkeypatch)
    assert dados["lpa"] == pytest.approx(-2.0)
    assert dados["pl"] == pytest.approx(PRECO / -2.0)
    assert dados["roe"] == pytest.approx(-0.2)


def test_cache_nao_repoe_valor_que_a_cvm_entregou(monkeypatch):
    cache = FakeCache({"pl": 12.0, "lpa": 1.5, "roe": 0.15, "pvp": 1.0, "dy": 0.05})
    dados = _cascata(monkeypatch, cache=cache)
    assert dados["pl"] == pytest.approx(PRECO / -2.0)
    assert dados["lpa"] == pytest.approx(-2.0)
    assert dados["roe"] == pytest.approx(-0.2)
    assert not dados.get("dados_cache")


def test_lpa_cvm_e_valor_final_concordam(monkeypatch):
    dados = _cascata(monkeypatch)
    assert dados["lpa_cvm"]["origem"] == "recalculado"
    assert dados["lpa"] == pytest.approx(dados["valores_por_fonte"]["CVM"]["lpa"])
    assert dados["pl"] == pytest.approx(dados["valores_por_fonte"]["CVM"]["pl"])


def test_prejuizo_nao_conta_como_campo_faltando(monkeypatch):
    # Sem P/L e ROE no yfinance: só a CVM os informa, com o prejuízo.
    dados = _cascata(monkeypatch, yfinance={"dividendYield": 4.0})
    assert dados["fundamentos_incompletos"] is False
    assert dados["campos_faltantes"] == []
    assert (
        list_missing_required_fields(
            {"ticker": "TST3", "pl": -10.0, "pvp": -0.5, "roe": -0.2, "dy": 0.0}
        )
        == []
    )
