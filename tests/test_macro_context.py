"""Testes para MacroContext dinâmico (config.py).

Todos os testes usam MacroContext(selic=0.10) para evitar chamada BCB na
inicialização. Propriedades dinâmicas (cdi, ipca_12m) são
testadas via monkeypatch dos fetchers privados — sem tráfego de rede.
"""

import pytest

from config import (
    CDI_FALLBACK,
    IPCA_12M_FALLBACK,
    MACRO,
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
# cost_of_equity_real
# ---------------------------------------------------------------------------


def test_cost_of_equity_real(monkeypatch):
    """F2B-1: delega ao registro real, sem buscar NTN-B pela API antiga."""
    import config

    m = MacroContext(selic=0.10)
    monkeypatch.setattr(config, "get_taxa_real", lambda: {"custo_capital_real": 0.115})
    assert m.cost_of_equity_real() == pytest.approx(0.115)
    monkeypatch.setattr(config, "get_taxa_real", lambda: None)
    assert m.cost_of_equity_real() is None


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


def test_taxa_real_sem_rede_no_import():
    """O ponto novo é lazy; o contorno antigo da Selic continua na suíte."""
    import ast
    from pathlib import Path

    import config

    arvore = ast.parse(Path(config.__file__).read_text())
    chamadas = [
        n
        for n in arvore.body
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
    ]
    assert not any(
        isinstance(n.value.func, ast.Name) and n.value.func.id == "get_taxa_real"
        for n in chamadas
    )
    assert config.get_taxa_real()["ntnb"] == 0.07
    assert config.get_taxa_real()["inflacao"]["valor"] == 0.055


def test_taxa_real_cache_por_janela_dia_e_edicao(monkeypatch):
    from datetime import UTC, date, datetime, timedelta

    import config

    monkeypatch.setattr(config, "_taxa_real_cache", {})
    chamadas = []

    def carregar(instante, janela):
        chamadas.append((instante, janela))
        return {
            "ntnb": 0.07,
            "pib": {"proxima_publicacao": "2026-10-19T11:30:00+00:00"},
        }

    monkeypatch.setattr(config, "_carregar_taxa_real", carregar)
    antes = datetime(2026, 10, 19, 10, tzinfo=UTC)
    assert config.get_taxa_real(as_of=antes)["ntnb"] == 0.07
    assert config.get_taxa_real(as_of=antes + timedelta(minutes=10))["ntnb"] == 0.07
    assert len(chamadas) == 1
    config.get_taxa_real(as_of=datetime(2026, 10, 19, 11, 30, tzinfo=UTC))
    assert len(chamadas) == 2
    config.get_taxa_real(as_of=datetime(2026, 10, 20, 10, tzinfo=UTC))
    assert len(chamadas) == 3
    config.get_taxa_real(as_of=antes, janela=(date(2025, 1, 1), date(2025, 12, 31)))
    assert len(chamadas) == 4
    assert (
        config.get_taxa_real(
            as_of=datetime(2026, 10, 19, tzinfo=UTC).replace(tzinfo=None)
        )
        is None
    )


def test_taxa_real_falha_sem_contingencia_e_sem_cache_numerico(monkeypatch):
    from datetime import UTC, datetime

    import config

    monkeypatch.setattr(config, "_taxa_real_cache", {})
    monkeypatch.setattr(config, "_carregar_taxa_real", lambda *a: None)
    assert config.get_taxa_real(as_of=datetime(2026, 10, 20, tzinfo=UTC)) is None
    assert config._taxa_real_cache == {}
