import market_engine
import pandas as pd
import pytest

from market_engine import (
    MarketEngine,
    _is_fii_ticker,
    list_missing_required_fields,
    merge_if_valid,
)
from sentinela.domain.provenance import FieldValue


class FakeCVM:
    """CVM provider stub para testes de market_engine."""

    def __init__(self, resultado=None):
        # resultado=None → sem dado; resultado={ano: {...}} → retorna esse dict
        self._resultado = resultado

    def calcular_indicadores(self, cd_cvm: int, anos: int = 1) -> dict:
        if self._resultado is None:
            return {}
        return self._resultado


def _cvm_ind(
    *,
    patrimonio_liquido=300_000_000.0,
    lucro_liquido=60_000_000.0,
    receita_liquida=500_000_000.0,
    roe=0.20,
    margem_liquida=0.12,
    divida_pl=0.80,
    ativo_total=1_000_000_000.0,
    ativo_circulante=300_000_000.0,
):
    return {
        2025: {
            "patrimonio_liquido": patrimonio_liquido,
            "lucro_liquido":      lucro_liquido,
            "receita_liquida":    receita_liquida,
            "roe":                roe,
            "margem_liquida":     margem_liquida,
            "divida_pl":          divida_pl,
            "ativo_total":        ativo_total,
            "ativo_circulante":   ativo_circulante,
        }
    }


class FakeTicker:
    def __init__(self, info=None, historico=None):
        self.info = info or {}
        self._historico = historico if historico is not None else pd.DataFrame()

    def history(self, *args, **kwargs):
        return self._historico


class FakeScraper:
    def __init__(self, resposta):
        self.resposta = resposta
        self.calls = 0

    def buscar_dados(self, ticker):
        self.calls += 1
        return self.resposta


class FakeBrapi:
    def __init__(self, resposta=None, disponivel=True):
        self.resposta = resposta
        self.disponivel = disponivel

    def get_fundamentals(self, ticker):
        return self.resposta


class FakeCache:
    def __init__(self, resposta=None):
        self.resposta = resposta
        self.saved = []

    def buscar_fundamentos_cache(self, ticker, max_age_days=7):
        return self.resposta

    def salvar_fundamentos_cache(self, ticker, dados, fonte):
        self.saved.append((ticker, dados, fonte))


def _historico(preco=10.0):
    return pd.DataFrame(
        {
            "Open": [preco - 1, preco],
            "High": [preco + 1, preco + 2],
            "Low": [preco - 2, preco - 1],
            "Close": [preco - 0.5, preco],
        },
        index=pd.date_range("2024-01-01", periods=2),
    )


def _engine(monkeypatch, *, info, historico=None, scraper=None, brapi=None, cache=None, cvm=None):
    monkeypatch.setattr(
        "market_engine.yf.Ticker",
        lambda ticker: FakeTicker(info=info, historico=historico),
    )
    engine = MarketEngine.__new__(MarketEngine)
    engine.scraper = FakeScraper(scraper if scraper is not None else {"erro_scraper": True})
    engine.brapi = brapi if brapi is not None else FakeBrapi(disponivel=False)
    engine.database = cache
    # cvm=None → atributo não definido → getattr(engine, 'cvm', None) retorna None → pula CVM
    if cvm is not None:
        engine.cvm = cvm
    return engine


def test_market_engine_known_unit_not_treated_as_fii():
    assert _is_fii_ticker("SANB11", {"quote_type": "MUTUALFUND"}) is False


def test_market_engine_known_fii_treated_as_fii():
    assert _is_fii_ticker("HGLG11", {}) is True


def test_market_engine_suffix_11_non_unit_still_fii():
    assert _is_fii_ticker("ABCD11", {}) is True


def test_yfinance_data_is_preserved_when_fundamentus_fails(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(22.0),
        info={
            "currentPrice": 21.0,
            "trailingPE": 8.0,
            "priceToBook": 1.2,
            "returnOnEquity": 0.15,
            "dividendYield": 0.04,
            "quoteType": "EQUITY",
        },
    )

    dados = engine.buscar_dados_ticker("PETR4")

    assert dados["ticker"] == "PETR4"
    assert dados["preco_atual"] == 22.0
    assert dados["pl"] == 8.0
    assert dados["pvp"] == 1.2
    assert dados["roe"] == 0.15
    assert dados["dy"] == 0.04
    assert dados["fonte_preco"] == "yfinance"
    assert dados["fonte_fundamentos"] == "yfinance_partial"
    assert dados["erro_scraper"] is True
    assert dados["campos_faltantes"] == []
    assert dados["dados_parciais"] is False


def test_brapi_fills_missing_fields(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(10.0),
        info={"currentPrice": 10.0, "quoteType": "EQUITY"},
        brapi=FakeBrapi(
            {
                "pl": 9.0,
                "pvp": 1.1,
                "roe": 0.20,
                "dy": 0.05,
                "quote_type": "EQUITY",
            }
        ),
    )

    dados = engine.buscar_dados_ticker("ITUB4")

    assert dados["pl"] == 9.0
    assert dados["pvp"] == 1.1
    assert dados["roe"] == 0.20
    assert dados["dy"] == 0.05
    assert "brapi" in dados["fonte_fundamentos"]
    assert dados["campos_faltantes"] == []


def test_market_engine_adds_field_provenance_for_core_fields(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(22.0),
        info={
            "currentPrice": 21.0,
            "trailingPE": 8.0,
            "priceToBook": 1.2,
            "returnOnEquity": 0.15,
            "dividendYield": 0.04,
            "quoteType": "EQUITY",
        },
    )

    dados = engine.buscar_dados_ticker("PETR4")

    assert "field_provenance" in dados
    assert set(dados["field_provenance"]) == {"preco_atual", "dy", "pl", "pvp", "roe"}


def test_field_provenance_preserves_raw_values(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(22.0),
        info={
            "currentPrice": 21.0,
            "trailingPE": 8.0,
            "priceToBook": 1.2,
            "returnOnEquity": 0.15,
            "dividendYield": 0.04,
            "quoteType": "EQUITY",
        },
    )

    dados = engine.buscar_dados_ticker("PETR4")

    assert dados["dy"] == 0.04
    assert dados["field_provenance"]["dy"]["value"] == dados["dy"]
    assert not isinstance(dados["dy"], FieldValue)
    assert not isinstance(dados["pl"], FieldValue)
    assert not isinstance(dados["pvp"], FieldValue)
    assert not isinstance(dados["roe"], FieldValue)


def test_price_provenance_uses_fonte_preco(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(22.0),
        info={"currentPrice": 21.0, "quoteType": "EQUITY"},
    )

    dados = engine.buscar_dados_ticker("PETR4")

    assert dados["fonte_preco"] == "yfinance"
    assert dados["field_provenance"]["preco_atual"]["provenance"]["source"] == "yfinance"


def test_fundamentals_provenance_uses_fonte_fundamentos(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(10.0),
        info={"currentPrice": 10.0, "quoteType": "EQUITY"},
        brapi=FakeBrapi(
            {
                "pl": 9.0,
                "pvp": 1.1,
                "roe": 0.20,
                "dy": 0.05,
                "quote_type": "EQUITY",
            }
        ),
    )

    dados = engine.buscar_dados_ticker("ITUB4")

    assert dados["fonte_fundamentos"] == "brapi"
    for field in ("dy", "pl", "pvp", "roe"):
        assert dados["field_provenance"][field]["provenance"]["source"] == "brapi"


def test_brapi_overrides_yfinance_fundamentals_when_valid(monkeypatch):
    cache = FakeCache()
    engine = _engine(
        monkeypatch,
        historico=_historico(22.0),
        info={
            "currentPrice": 21.0,
            "trailingPE": 12.0,
            "priceToBook": 2.5,
            "returnOnEquity": 0.08,
            "dividendYield": 0.01,
            "quoteType": "EQUITY",
        },
        brapi=FakeBrapi(
            {
                "preco_atual": 99.0,
                "pl": 7.0,
                "pvp": 1.3,
                "roe": 0.22,
                "dy": 0.06,
                "quote_type": "EQUITY",
            }
        ),
        cache=cache,
    )

    dados = engine.buscar_dados_ticker("PETR4")

    assert dados["preco_atual"] == 22.0
    assert dados["fonte_preco"] == "yfinance"
    assert dados["pl"] == 7.0
    assert dados["pvp"] == 1.3
    assert dados["roe"] == 0.22
    assert dados["dy"] == 0.06
    assert dados["fonte_fundamentos"] == "brapi"
    assert dados["dados_parciais"] is False
    assert cache.saved


def test_brapi_does_not_overwrite_valid_fields_with_missing_values(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(30.0),
        info={
            "currentPrice": 30.0,
            "trailingPE": 7.0,
            "priceToBook": 1.4,
            "returnOnEquity": 0.12,
            "dividendYield": 0.03,
        },
        brapi=FakeBrapi({"pl": None, "pvp": 0, "roe": 0, "dy": None, "preco_atual": 0}),
    )

    dados = engine.buscar_dados_ticker("BBAS3")

    assert dados["preco_atual"] == 30.0
    assert dados["pl"] == 7.0
    assert dados["pvp"] == 1.4
    assert dados["roe"] == 0.12
    assert dados["dy"] == 0.03


def test_fundamentus_fills_only_missing_fields(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(18.0),
        info={"currentPrice": 18.0, "quoteType": "EQUITY"},
        brapi=FakeBrapi({"pl": 9.0, "dy": 0.04, "quote_type": "EQUITY"}),
        scraper={"pl": 1.0, "pvp": 1.2, "roe": 0.18, "dy": 0.99},
        cache=FakeCache(),
    )

    dados = engine.buscar_dados_ticker("ITUB4")

    assert dados["pl"] == 9.0
    assert dados["dy"] == 0.04
    assert dados["pvp"] == 1.2
    assert dados["roe"] == 0.18
    assert dados["fonte_fundamentos"] == "brapi+fundamentus"
    assert dados["dados_parciais"] is False


def test_scraper_failure_does_not_make_data_partial_when_brapi_complete(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(25.0),
        info={"currentPrice": 25.0, "quoteType": "EQUITY"},
        brapi=FakeBrapi({"pl": 8.0, "pvp": 1.1, "roe": 0.16, "dy": 0.05}),
        scraper={"erro_scraper": True},
        cache=FakeCache(),
    )

    dados = engine.buscar_dados_ticker("BBAS3")

    assert dados["fonte_fundamentos"] == "brapi"
    assert dados["erro_scraper"] is False
    assert dados["campos_faltantes"] == []
    assert dados["dados_parciais"] is False
    assert engine.scraper.calls == 0


def test_missing_fields_and_partial_flag_are_set(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(15.0),
        info={"currentPrice": 15.0, "dividendYield": 0.0},
    )

    dados = engine.buscar_dados_ticker("ABCD3")

    assert dados["ticker"] == "ABCD3"
    assert dados["campos_faltantes"] == ["pl", "pvp", "roe"]
    assert dados["dados_parciais"] is True


def test_no_cache_path_does_not_mark_cached_data(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(12.0),
        info={"currentPrice": 12.0, "dividendYield": 0.0},
    )

    dados = engine.buscar_dados_ticker("CACHE3")

    assert dados["dados_cache"] is False
    assert dados.get("fonte_fundamentos") != "cache"


def test_cache_is_used_when_providers_fail(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(12.0),
        info={"currentPrice": 12.0, "trailingPE": 99.0},
        brapi=FakeBrapi(disponivel=False),
        scraper={"erro_scraper": True},
        cache=FakeCache({"pl": 6.0, "pvp": 0.9, "roe": 0.14, "dy": 0.07}),
    )

    dados = engine.buscar_dados_ticker("CACHE3")

    assert dados["pl"] == 6.0
    assert dados["pvp"] == 0.9
    assert dados["roe"] == 0.14
    assert dados["dy"] == 0.07
    assert dados["dados_cache"] is True
    assert dados["fonte_fundamentos"].endswith("cache")
    assert "campos fundamentais preenchidos via cache" in dados["riscos_dados"]
    assert dados["dados_parciais"] is False


def test_cache_provenance_marks_cached_fields(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(12.0),
        info={"currentPrice": 12.0, "trailingPE": 99.0},
        brapi=FakeBrapi(disponivel=False),
        scraper={"erro_scraper": True},
        cache=FakeCache({"pl": 6.0, "pvp": 0.9, "roe": 0.14, "dy": 0.07}),
    )

    dados = engine.buscar_dados_ticker("CACHE3")

    for field in ("dy", "pl", "pvp", "roe"):
        provenance = dados["field_provenance"][field]["provenance"]
        assert provenance["source"] == "fundamentals_cache"
        assert provenance["cached"] is True


def test_fii_without_pl_roe_but_with_dy_pvp_is_not_partial(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(100.0),
        info={"currentPrice": 100.0, "priceToBook": 0.98, "dividendYield": 0.10},
        brapi=FakeBrapi(disponivel=False),
        scraper={"erro_scraper": True},
    )

    dados = engine.buscar_dados_ticker("MXRF11")

    assert dados["pvp"] == 0.98
    assert dados["dy"] == 0.10
    assert dados["campos_faltantes"] == []
    assert dados["dados_parciais"] is False


def test_cache_fills_missing_required_stock_fields(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(12.0),
        info={"currentPrice": 12.0, "trailingPE": 8.0, "dividendYield": 0.04},
        brapi=FakeBrapi(disponivel=False),
        scraper={"erro_scraper": True},
        cache=FakeCache({"pvp": 1.1, "roe": 0.18, "dy": 0.06}),
    )

    dados = engine.buscar_dados_ticker("CACHE3")

    assert dados["pl"] == 8.0
    assert dados["pvp"] == 1.1
    assert dados["roe"] == 0.18
    assert dados["dy"] == 0.04
    assert dados["dados_cache"] is True
    assert dados["campos_faltantes"] == []
    assert dados["dados_parciais"] is False


def test_manual_fii_fallback_fills_missing_dy_pvp(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(100.0),
        info={"currentPrice": 100.0},
        brapi=FakeBrapi(disponivel=False),
        scraper={"erro_scraper": True},
        cache=FakeCache(),
    )

    dados = engine.buscar_dados_ticker("CVBI11")

    assert dados["dy"] == 0.10
    assert dados["pvp"] == 0.85
    assert dados["vacancia"] == 0.25
    assert dados["dados_manual"] is True
    assert dados["fonte_fundamentos"] == "manual_fii"
    assert "fundamentos FII preenchidos manualmente" in dados["riscos_dados"]
    assert dados["dados_parciais"] is False


def test_manual_fallback_provenance_marks_manual_fields(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(100.0),
        info={"currentPrice": 100.0},
        brapi=FakeBrapi(disponivel=False),
        scraper={"erro_scraper": True},
        cache=FakeCache(),
    )

    dados = engine.buscar_dados_ticker("CVBI11")

    for field in ("dy", "pvp"):
        provenance = dados["field_provenance"][field]["provenance"]
        assert provenance["source"] == "manual_fallback"
        assert provenance["manual"] is True
        assert "manual_fallback" in provenance["warnings"]


def test_market_engine_manual_fii_fallback_does_not_apply_to_known_unit(monkeypatch):
    monkeypatch.setitem(
        market_engine.FII_MANUAL_FALLBACK,
        "SANB11",
        {"dy": 0.11, "pvp": 0.88, "vacancia": 0.02},
    )
    engine = MarketEngine.__new__(MarketEngine)
    dados = {
        "ticker": "SANB11",
        "quote_type": "MUTUALFUND",
        "riscos_dados": [],
    }

    applied = engine._aplicar_fallback_manual_fii("SANB11", dados)

    assert applied is False
    assert dados.get("dados_manual") is not True
    assert "dy" not in dados
    assert "pvp" not in dados
    assert "vacancia" not in dados


def test_manual_fii_fallback_never_overwrites_fresh_provider_values(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(100.0),
        info={"currentPrice": 100.0, "priceToBook": 1.05, "dividendYield": 0.09},
        brapi=FakeBrapi(disponivel=False),
        scraper={"erro_scraper": True},
        cache=FakeCache(),
    )

    dados = engine.buscar_dados_ticker("HGLG11")

    assert dados["pvp"] == 1.05
    assert dados["dy"] == 0.09
    assert dados["dados_manual"] is False
    assert "manual_fii" not in (dados.get("fonte_fundamentos") or "")


def test_quality_helpers_respect_zero_dy_but_not_zero_price():
    dados = {"preco_atual": 0, "pl": 0, "pvp": 1.0, "roe": 0, "dy": 0}

    assert list_missing_required_fields(dados) == ["pl", "roe"]


def test_missing_field_provenance_is_safe(monkeypatch):
    engine = _engine(
        monkeypatch,
        historico=_historico(15.0),
        info={"currentPrice": 15.0, "dividendYield": 0.0},
    )

    dados = engine.buscar_dados_ticker("ABCD3")

    for field in ("pl", "pvp", "roe"):
        field_data = dados["field_provenance"][field]
        provenance = field_data["provenance"]
        assert field_data["value"] is None
        assert provenance["confidence"] == 0.0
        assert "missing_value" in provenance["warnings"]


def test_merge_if_valid_only_fills_missing_fields():
    base = {"pl": 10.0, "pvp": 0, "dy": 0}
    changed = merge_if_valid(base, {"pl": None, "pvp": 1.2, "dy": 0.05})

    assert changed == ["pvp"]
    assert base == {"pl": 10.0, "pvp": 1.2, "dy": 0}


# ---------------------------------------------------------------------------
# CVM integration tests
# ---------------------------------------------------------------------------

def test_cvm_fills_fundamentals_when_ticker_mapped(monkeypatch):
    """CVM preenche roe, margem_liquida e patrimonio_liquido para PETR4."""
    engine = _engine(
        monkeypatch,
        historico=_historico(38.0),
        info={"currentPrice": 38.0, "quoteType": "EQUITY"},
        cvm=FakeCVM(_cvm_ind(roe=0.18, margem_liquida=0.14)),
    )

    dados = engine.buscar_dados_ticker("PETR4")

    assert dados["roe"] == pytest.approx(0.18)
    assert dados["margem_liquida"] == pytest.approx(0.14)
    assert dados["patrimonio_liquido"] == pytest.approx(300_000_000.0)
    assert dados["cvm_disponivel"] is True
    assert dados["fonte_fundamentos"] == "CVM"


def test_cvm_disponivel_false_when_ticker_not_mapped(monkeypatch):
    """Ticker sem mapeamento CVM deve ter cvm_disponivel=False."""
    engine = _engine(
        monkeypatch,
        historico=_historico(15.0),
        info={"currentPrice": 15.0, "quoteType": "EQUITY", "trailingPE": 10.0,
              "priceToBook": 1.2, "returnOnEquity": 0.10, "dividendYield": 0.04},
        cvm=FakeCVM(_cvm_ind()),  # CVM ativo mas ticker ZZZZZ9 não está no mapa
    )

    dados = engine.buscar_dados_ticker("ZZZZZ9")

    assert dados["cvm_disponivel"] is False


def test_cvm_failure_falls_back_gracefully(monkeypatch):
    """Exceção no CVM não impede retorno dos dados das fontes existentes."""
    class ErrorCVM:
        def calcular_indicadores(self, *args, **kwargs):
            raise RuntimeError("simulated CVM failure")

    engine = _engine(
        monkeypatch,
        historico=_historico(22.0),
        info={"currentPrice": 22.0, "trailingPE": 8.0, "priceToBook": 1.2,
              "returnOnEquity": 0.15, "dividendYield": 0.04, "quoteType": "EQUITY"},
        cvm=ErrorCVM(),
    )

    dados = engine.buscar_dados_ticker("PETR4")

    assert dados["preco_atual"] == pytest.approx(22.0)
    assert dados["cvm_disponivel"] is False
    assert dados["pl"] == pytest.approx(8.0)   # yfinance fallback intacto


def test_cvm_computes_pl_pvp_from_shares(monkeypatch):
    """Com sharesOutstanding disponível, CVM deriva P/L e P/VP."""
    shares = 13_000_000_000.0  # 13 bilhões de ações
    lucro  = 60_000_000_000.0  # 60 bi lucro
    pl_val = 300_000_000_000.0  # 300 bi PL
    preco  = 38.0

    lpa_esperado = lucro / shares
    vpa_esperado = pl_val / shares

    engine = _engine(
        monkeypatch,
        historico=_historico(preco),
        info={"currentPrice": preco, "quoteType": "EQUITY",
              "sharesOutstanding": shares},
        cvm=FakeCVM(_cvm_ind(lucro_liquido=lucro, patrimonio_liquido=pl_val)),
    )

    dados = engine.buscar_dados_ticker("PETR4")

    assert dados["lpa"] == pytest.approx(lpa_esperado)
    assert dados["vpa"] == pytest.approx(vpa_esperado)
    assert dados["pl"]  == pytest.approx(preco / lpa_esperado)
    assert dados["pvp"] == pytest.approx(preco / vpa_esperado)


def test_cvm_overrides_brapi_fundamentals(monkeypatch):
    """CVM (mais confiável) deve sobrescrever ROE fornecido pelo brapi."""
    engine = _engine(
        monkeypatch,
        historico=_historico(30.0),
        info={"currentPrice": 30.0, "quoteType": "EQUITY"},
        brapi=FakeBrapi({"pl": 9.0, "pvp": 1.5, "roe": 0.99, "dy": 0.05}),
        cvm=FakeCVM(_cvm_ind(roe=0.20)),
    )

    dados = engine.buscar_dados_ticker("PETR4")

    # CVM sobrescreve o roe absurdo do brapi
    assert dados["roe"] == pytest.approx(0.20)
    assert dados["fonte_fundamentos"] == "CVM"
