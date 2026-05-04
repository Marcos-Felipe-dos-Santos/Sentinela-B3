import pandas as pd

from market_engine import MarketEngine, list_missing_required_fields, merge_if_valid


class FakeTicker:
    def __init__(self, info=None, historico=None):
        self.info = info or {}
        self._historico = historico if historico is not None else pd.DataFrame()

    def history(self, *args, **kwargs):
        return self._historico


class FakeScraper:
    def __init__(self, resposta):
        self.resposta = resposta

    def buscar_dados(self, ticker):
        return self.resposta


class FakeBrapi:
    def __init__(self, resposta=None, disponivel=True):
        self.resposta = resposta
        self.disponivel = disponivel

    def get_fundamentals(self, ticker):
        return self.resposta


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


def _engine(monkeypatch, *, info, historico=None, scraper=None, brapi=None):
    monkeypatch.setattr(
        "market_engine.yf.Ticker",
        lambda ticker: FakeTicker(info=info, historico=historico),
    )
    engine = MarketEngine.__new__(MarketEngine)
    engine.scraper = FakeScraper(scraper if scraper is not None else {"erro_scraper": True})
    engine.brapi = brapi if brapi is not None else FakeBrapi(disponivel=False)
    return engine


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

    assert "dados_cache" not in dados
    assert dados.get("fonte_fundamentos") != "cache"


def test_quality_helpers_respect_zero_dy_but_not_zero_price():
    dados = {"preco_atual": 0, "pl": 0, "pvp": 1.0, "roe": 0, "dy": 0}

    assert list_missing_required_fields(dados) == ["preco_atual", "pl", "roe"]


def test_merge_if_valid_only_fills_missing_fields():
    base = {"pl": 10.0, "pvp": 0, "dy": 0}
    changed = merge_if_valid(base, {"pl": None, "pvp": 1.2, "dy": 0.05})

    assert changed == ["pvp"]
    assert base == {"pl": 10.0, "pvp": 1.2, "dy": 0}
