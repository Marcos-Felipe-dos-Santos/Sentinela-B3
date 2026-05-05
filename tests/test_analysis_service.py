from unittest.mock import MagicMock

from sentinela.services.analyze_asset import AnalysisService


def _service(
    *,
    market_data,
    valuation_result=None,
    fii_result=None,
    tech_result=None,
    peers_result=None,
    ai_result=None,
):
    market = MagicMock()
    market.buscar_dados_ticker.return_value = market_data

    valuation = MagicMock()
    valuation.processar.return_value = valuation_result or {
        "fair_value": 40.0,
        "upside": 20.0,
        "score_final": 70,
        "recomendacao": "COMPRA",
        "metodos_usados": "Fake",
        "perfil": "RENDA/VALOR",
    }

    fii = MagicMock()
    fii.analisar.return_value = fii_result or {
        "fair_value": 10.0,
        "upside": 0.0,
        "score_final": 50,
        "recomendacao": "NEUTRO",
        "perfil": "FII",
        "metodos_usados": "Fake FII",
    }

    technical = MagicMock()
    technical.calcular_indicadores.return_value = tech_result or {
        "rsi": 55,
        "tendencia": "Alta",
        "atr": 1.0,
    }

    peers = MagicMock()
    peers.comparar.return_value = peers_result or {"Setor": "petroleo"}

    ai = MagicMock()
    ai.analisar.return_value = ai_result or {"content": "analise fake"}

    repository = MagicMock()

    service = AnalysisService(
        market_engine=market,
        valuation_engine=valuation,
        fii_engine=fii,
        technical_engine=technical,
        peers_engine=peers,
        ai_engine=ai,
        repository=repository,
    )
    return service, market, valuation, fii, technical, peers, ai, repository


def test_analysis_service_happy_path_stock_uses_existing_engine_methods():
    market_data = {
        "ticker": "PETR4",
        "preco_atual": 30.0,
        "historico": "HIST",
        "quote_type": "EQUITY",
        "pl": 6.0,
        "pvp": 1.2,
        "dy": 0.08,
        "roe": 0.18,
    }
    service, market, valuation, fii, technical, peers, ai, repository = _service(
        market_data=market_data
    )

    result = service.analyze("petr4")

    market.buscar_dados_ticker.assert_called_once_with("PETR4")
    valuation.processar.assert_called_once()
    fii.analisar.assert_not_called()
    technical.calcular_indicadores.assert_called_once_with("HIST")
    peers.comparar.assert_called_once_with("PETR4")
    ai.analisar.assert_called_once()
    repository.salvar_analise.assert_called_once()

    saved_payload = repository.salvar_analise.call_args.args[0]
    assert "historico" not in saved_payload
    assert saved_payload["analise_ia"] == "analise fake"
    assert result.success is True
    assert result.is_fii is False
    assert result.valuation.recomendacao == "COMPRA"
    assert result.peers == {"Setor": "petroleo"}


def test_analysis_service_happy_path_fii_uses_real_fii_method_name():
    market_data = {
        "ticker": "MXRF11",
        "preco_atual": 10.0,
        "historico": "HIST",
        "quote_type": "EQUITY",
        "pvp": 1.0,
        "dy": 0.12,
    }
    service, _, valuation, fii, technical, peers, ai, repository = _service(
        market_data=market_data
    )

    result = service.analyze("MXRF11")

    fii.analisar.assert_called_once()
    valuation.processar.assert_not_called()
    peers.comparar.assert_not_called()
    technical.calcular_indicadores.assert_called_once_with("HIST")
    ai.analisar.assert_called_once()
    repository.salvar_analise.assert_called_once()
    assert result.success is True
    assert result.is_fii is True
    assert result.valuation.perfil == "FII"


def test_analysis_service_returns_insufficient_data_when_market_data_is_none():
    service, _, valuation, fii, technical, peers, ai, repository = _service(market_data=None)

    result = service.analyze("PETR4")

    valuation.processar.assert_not_called()
    fii.analisar.assert_not_called()
    technical.calcular_indicadores.assert_not_called()
    peers.comparar.assert_not_called()
    ai.analisar.assert_not_called()
    repository.salvar_analise.assert_not_called()
    assert result.success is False
    assert result.error == "DADOS INSUFICIENTES"
    assert result.data_quality.dados_parciais is True


def test_analysis_service_does_not_call_repository_when_persist_false():
    market_data = {
        "ticker": "ITUB4",
        "preco_atual": 30.0,
        "historico": "HIST",
        "quote_type": "EQUITY",
    }
    service, _, _, _, _, _, _, repository = _service(market_data=market_data)

    result = service.analyze("ITUB4", persist=False)

    repository.salvar_analise.assert_not_called()
    assert result.success is True


def test_analysis_service_does_not_call_ai_when_use_ai_false():
    market_data = {
        "ticker": "ITUB4",
        "preco_atual": 30.0,
        "historico": "HIST",
        "quote_type": "EQUITY",
    }
    service, _, _, _, _, _, ai, repository = _service(market_data=market_data)

    result = service.analyze("ITUB4", use_ai=False)

    ai.analisar.assert_not_called()
    repository.salvar_analise.assert_called_once()
    assert result.ai_analysis is None
    assert "analise_ia" not in result.raw

