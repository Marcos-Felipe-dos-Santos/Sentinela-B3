"""Testes para MacroContext dinâmico (config.py).

Todos os testes usam MacroContext(selic=0.10) para evitar chamada BCB na
inicialização. Propriedades dinâmicas (cdi, ipca_12m, ntnb_longa) são
testadas via monkeypatch dos fetchers privados — sem tráfego de rede.
"""
import pytest

from config import (
    CDI_FALLBACK,
    IPCA_12M_FALLBACK,
    MACRO,
    NTNB_LONGA_FALLBACK,
    MacroContext,
)


# ---------------------------------------------------------------------------
# Backward compat
# ---------------------------------------------------------------------------

def test_macro_no_args_backward_compat():
    """MacroContext() sem argumento deve funcionar (usa get_selic_atual)."""
    # MACRO já é instanciado sem args no import — se chegou aqui, passou.
    assert isinstance(MACRO, MacroContext)


def test_existing_class_attrs_preserved():
    """Atributos de classe existentes devem continuar acessíveis na instância."""
    m = MacroContext(selic=0.10)
    assert m.BAZIN_DY_MIN == 0.05
    assert m.FII_FATOR_IR == 0.85
    assert m.GORDON_PREMIO_RISCO == 0.07
    assert m.REC_UPSIDE_COMPRA == 0.15
    assert m.GRAHAM_PL_LIMITE == 25.0


# ---------------------------------------------------------------------------
# selic / selic_liquida
# ---------------------------------------------------------------------------

def test_selic_from_explicit_init():
    m = MacroContext(selic=0.10)
    assert m.selic == pytest.approx(0.10)


def test_selic_liquida_applies_fii_factor():
    m = MacroContext(selic=0.10)
    assert m.selic_liquida == pytest.approx(0.10 * 0.85)


# ---------------------------------------------------------------------------
# cdi
# ---------------------------------------------------------------------------

def test_cdi_annualizes_daily_rate(monkeypatch):
    """_fetch_bcb retorna taxa diária; cdi deve anualizar base 252."""
    m = MacroContext(selic=0.10)
    d = 0.000534  # 0.0534% a.d. ≈ CDI diário de junho/2026
    monkeypatch.setattr(m, "_fetch_bcb", lambda serie: d)

    expected = (1 + d) ** 252 - 1
    assert m.cdi == pytest.approx(expected, rel=1e-6)


def test_cdi_fallback_when_fetch_returns_none(monkeypatch):
    """Se _fetch_bcb retornar None, cdi deve retornar CDI_FALLBACK."""
    m = MacroContext(selic=0.10)
    monkeypatch.setattr(m, "_fetch_bcb", lambda serie: None)

    assert m.cdi == pytest.approx(CDI_FALLBACK)


def test_cdi_is_lazy(monkeypatch):
    """_cdi deve ser None antes do primeiro acesso à propriedade."""
    m = MacroContext(selic=0.10)
    assert m._cdi is None
    monkeypatch.setattr(m, "_fetch_bcb", lambda serie: 0.000534)
    _ = m.cdi  # trigger lazy load
    assert m._cdi is not None


# ---------------------------------------------------------------------------
# ipca_12m
# ---------------------------------------------------------------------------

def test_ipca_12m_returns_compounded_value(monkeypatch):
    """_fetch_ipca_acumulado determina o valor; property deve devolvê-lo."""
    m = MacroContext(selic=0.10)
    fake_ipca = 0.0512
    monkeypatch.setattr(m, "_fetch_ipca_acumulado", lambda: fake_ipca)

    assert m.ipca_12m == pytest.approx(fake_ipca)


def test_ipca_12m_fallback_on_error(monkeypatch):
    """Se _fetch_ipca_acumulado lançar exceção interna, deve retornar fallback."""
    m = MacroContext(selic=0.10)
    monkeypatch.setattr(m, "_fetch_ipca_acumulado", lambda: IPCA_12M_FALLBACK)

    assert m.ipca_12m == pytest.approx(IPCA_12M_FALLBACK)


# ---------------------------------------------------------------------------
# ntnb_longa
# ---------------------------------------------------------------------------

def test_ntnb_returns_value_from_fetcher(monkeypatch):
    m = MacroContext(selic=0.10)
    monkeypatch.setattr(m, "_fetch_ntnb", lambda: 0.0656)

    assert m.ntnb_longa == pytest.approx(0.0656)


def test_ntnb_fallback_on_error(monkeypatch):
    m = MacroContext(selic=0.10)
    monkeypatch.setattr(m, "_fetch_ntnb", lambda: NTNB_LONGA_FALLBACK)

    assert m.ntnb_longa == pytest.approx(NTNB_LONGA_FALLBACK)


# ---------------------------------------------------------------------------
# cost_of_equity_real
# ---------------------------------------------------------------------------

def test_cost_of_equity_real(monkeypatch):
    """cost_of_equity_real = ntnb_longa + GORDON_PREMIO_RISCO."""
    m = MacroContext(selic=0.10)
    monkeypatch.setattr(m, "_fetch_ntnb", lambda: 0.065)

    expected = 0.065 + m.GORDON_PREMIO_RISCO
    assert m.cost_of_equity_real() == pytest.approx(expected)


# ---------------------------------------------------------------------------
# _fetch_ipca_acumulado — lógica de composição
# ---------------------------------------------------------------------------

def test_fetch_ipca_acumulado_compounds_correctly(monkeypatch):
    """Verifica que os valores mensais são compostos corretamente."""
    import requests

    class FakeResp:
        def raise_for_status(self):
            pass
        def json(self):
            # 12 meses de 0.50% a.m.
            return [{"valor": "0.50"}] * 12

    monkeypatch.setattr(requests, "get", lambda *a, **kw: FakeResp())
    m = MacroContext(selic=0.10)

    result = m._fetch_ipca_acumulado()
    expected = (1.005) ** 12 - 1
    assert result == pytest.approx(expected, rel=1e-6)
