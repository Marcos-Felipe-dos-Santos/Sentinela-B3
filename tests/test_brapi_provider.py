from brapi_provider import BrapiProvider


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_brapi_returns_none_without_token(monkeypatch):
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)

    provider = BrapiProvider()

    assert provider.disponivel is False
    assert provider.get_fundamentals("PETR4.SA") is None


def test_brapi_normalizes_fields_without_network(monkeypatch):
    monkeypatch.setenv("BRAPI_TOKEN", "token-test")

    def fake_get(url, params, timeout):
        assert url.endswith("/quote/PETR4")
        assert params["token"] == "token-test"
        assert params["fundamental"] == "true"
        assert timeout == 10
        return FakeResponse(
            {
                "results": [
                    {
                        "regularMarketPrice": 38.5,
                        "priceEarnings": 6.2,
                        "priceToBookRatio": 1.1,
                        "returnOnEquity": 18.0,
                        "dividendYield": 7.5,
                        "netDebtToEbitda": 1.7,
                        "quoteType": "EQUITY",
                    }
                ]
            }
        )

    monkeypatch.setattr("brapi_provider.requests.get", fake_get)

    provider = BrapiProvider()
    dados = provider.get_fundamentals("petr4.sa")

    assert dados == {
        "preco_atual": 38.5,
        "pl": 6.2,
        "pvp": 1.1,
        "roe": 0.18,
        "dy": 0.075,
        "divida_liq_ebitda": 1.7,
        "quote_type": "EQUITY",
    }
