"""Ticker validado por lista permitida antes de URL e prompt (F2A-12; E-18).

O ticker digitado chegava sem validação à URL da brapi, ao yfinance e ao prompt do LLM. Cada
fronteira passa a aceitar só raiz de 4 caracteres e 1 ou 2 dígitos (`^[A-Z0-9]{4}[0-9]{1,2}$`),
depois de normalizar (maiúsculas, sem espaços nas pontas, sem `.SA`).
"""

from unittest.mock import patch

import pytest

from tests.test_market_engine import FakeBrapi, _engine, _historico

INVALIDOS = [
    "",
    "PE TR4",
    "PETR4&x=1",
    "PETR4/../x",
    "PETR4;rm",
    "PETR\n4",
    "PETR4XX",
    "ABCDEFG1",
]


@pytest.mark.parametrize("ruim", INVALIDOS)
def test_ticker_invalido_nao_chega_ao_yfinance(monkeypatch, ruim):
    chamados = []
    engine = _engine(monkeypatch, info={}, historico=_historico(10.0))
    monkeypatch.setattr(
        "market_engine.yf.Ticker", lambda simbolo: chamados.append(simbolo)
    )
    assert engine.buscar_dados_ticker(ruim) is None
    assert chamados == []


@pytest.mark.parametrize("ruim", INVALIDOS[1:])  # o vazio a brapi já recusava
def test_ticker_invalido_nao_vira_url_da_brapi(monkeypatch, ruim):
    from brapi_provider import BrapiProvider

    urls = []
    monkeypatch.setenv("BRAPI_TOKEN", "token-test")
    monkeypatch.setattr(
        "brapi_provider.requests.get",
        lambda url, params, timeout: urls.append(url),
    )
    assert BrapiProvider().get_fundamentals(ruim) is None
    assert urls == []


@pytest.mark.parametrize("ruim", INVALIDOS)
def test_ticker_invalido_nao_entra_no_prompt(ruim):
    from ai_core import SentinelaAI

    with patch.dict("os.environ", {"GROQ_API_KEY": "", "GEMINI_API_KEY": ""}):
        ai = SentinelaAI()
    with (
        patch.object(ai, "_montar_prompt") as montar,
        patch.object(ai, "_call_ollama") as ollama,
    ):
        resposta = ai.analisar(ruim, {"classificacao_heuristica": "NEUTRO"})
    assert not montar.called and not ollama.called
    assert resposta["model"] == "nenhum"
    assert "ticker inválido" in resposta["content"]


@pytest.mark.parametrize(
    ("bruto", "normalizado"),
    [
        ("PETR4", "PETR4"),
        ("KLBN11", "KLBN11"),
        ("HGLG11", "HGLG11"),
        ("BOVA11", "BOVA11"),
        ("AAPL34", "AAPL34"),
        ("A1MD34", "A1MD34"),
        ("petr4.sa", "PETR4"),
        ("  vale3 ", "VALE3"),
        ("PETR4.SA", "PETR4"),
    ],
)
def test_formatos_validos(bruto, normalizado):
    from sentinela.domain import ticker

    assert ticker.normalizar(bruto) == normalizado
    assert ticker.validar(bruto) == normalizado


@pytest.mark.parametrize(
    "ruim", [*INVALIDOS, None, 123, "PETR", "PETRA", "TST3", "PETR4.SA.SA"]
)
def test_formatos_invalidos(ruim):
    from sentinela.domain import ticker

    assert ticker.normalizar(ruim) is None
    with pytest.raises(ValueError, match="ticker inválido"):
        ticker.validar(ruim)


def test_brapi_valida_e_normaliza_antes_da_url(monkeypatch):
    from brapi_provider import BrapiProvider

    urls = []

    class _Resposta:
        status_code = 200

        def json(self):
            return {"results": [{"regularMarketPrice": 10.0}]}

    def get(url, params, timeout):
        urls.append(url)
        return _Resposta()

    monkeypatch.setenv("BRAPI_TOKEN", "token-test")
    monkeypatch.setattr("brapi_provider.requests.get", get)
    assert BrapiProvider().get_quote(" petr4.sa ") is not None
    assert urls[0].endswith("/quote/PETR4")


def test_cascata_usa_o_ticker_normalizado(monkeypatch):
    chamados = []

    class _Ticker:
        def __init__(self, simbolo):
            self.info = {"currentPrice": 10.0}
            chamados.append(simbolo)

        def history(self, *a, **k):
            return _historico(10.0)

    engine = _engine(monkeypatch, info={}, brapi=FakeBrapi(disponivel=False))
    monkeypatch.setattr("market_engine.yf.Ticker", _Ticker)
    dados = engine.buscar_dados_ticker(" petr4.sa ")
    assert dados["ticker"] == "PETR4"
    assert chamados == ["PETR4.SA"]
