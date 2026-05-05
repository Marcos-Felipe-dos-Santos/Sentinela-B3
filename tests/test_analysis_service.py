from unittest.mock import MagicMock

import pandas as pd

from sentinela.services.analyze_asset import AnalysisService
from sentinela.services.asset_classifier import AssetClassifier


def _service(
    *,
    market_data,
    valuation_result=None,
    fii_result=None,
    tech_result=None,
    peers_result=None,
    ai_result=None,
    asset_classifier=None,
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
        asset_classifier=asset_classifier,
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


def test_analysis_service_uses_empty_dataframe_when_historico_missing():
    market_data = {
        "ticker": "ITUB4",
        "preco_atual": 30.0,
        "quote_type": "EQUITY",
    }
    service, _, _, _, technical, _, _, _ = _service(market_data=market_data)

    result = service.analyze("ITUB4")

    hist = technical.calcular_indicadores.call_args.args[0]
    assert isinstance(hist, pd.DataFrame)
    assert hist.empty
    assert result.success is True


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


def test_analysis_service_calls_save_run_for_append_only_repository():
    class AppendOnlyRepository:
        def __init__(self):
            self.saved = []

        def save_run(self, analysis):
            self.saved.append(analysis)

    market_data = {
        "ticker": "ITUB4",
        "preco_atual": 30.0,
        "historico": "HIST",
        "quote_type": "EQUITY",
    }
    service, _, _, _, _, _, _, _ = _service(market_data=market_data)
    repository = AppendOnlyRepository()
    service.repository = repository

    result = service.analyze("ITUB4")

    assert repository.saved == [result]


def test_analysis_service_uses_asset_classifier_by_default():
    market_data = {
        "ticker": "ABCD11",
        "preco_atual": 10.0,
        "historico": "HIST",
        "quote_type": "EQUITY",
    }
    service, _, valuation, fii, _, peers, _, _ = _service(market_data=market_data)

    result = service.analyze("ABCD11.SA")

    assert isinstance(service.asset_classifier, AssetClassifier)
    fii.analisar.assert_called_once()
    valuation.processar.assert_not_called()
    peers.comparar.assert_not_called()
    assert result.is_fii is True


def test_analysis_service_injected_classifier_is_used():
    class FakeClassifier:
        def __init__(self):
            self.calls = []

        def is_fii(self, ticker, dados):
            self.calls.append((ticker, dados))
            return True

    market_data = {
        "ticker": "PETR4",
        "preco_atual": 30.0,
        "historico": "HIST",
        "quote_type": "EQUITY",
    }
    classifier = FakeClassifier()
    service, _, valuation, fii, _, peers, _, _ = _service(
        market_data=market_data,
        asset_classifier=classifier,
    )

    result = service.analyze("PETR4")

    assert classifier.calls == [("PETR4", market_data)]
    fii.analisar.assert_called_once()
    valuation.processar.assert_not_called()
    peers.comparar.assert_not_called()
    assert result.is_fii is True


def test_analysis_service_default_asset_classifier_keeps_suffix_11_as_fii():
    market_data = {
        "ticker": "ABCD11",
        "preco_atual": 10.0,
        "historico": "HIST",
        "quote_type": "EQUITY",
    }
    service, _, valuation, fii, _, peers, _, _ = _service(market_data=market_data)

    result = service.analyze("ABCD11")

    fii.analisar.assert_called_once()
    valuation.processar.assert_not_called()
    peers.comparar.assert_not_called()
    assert result.is_fii is True


def test_analysis_service_known_unit_with_mutualfund_quote_type_routes_as_stock_or_non_fii():
    market_data = {
        "ticker": "SANB11",
        "preco_atual": 30.0,
        "historico": "HIST",
        "quote_type": "MUTUALFUND",
    }
    service, _, valuation, fii, _, peers, _, _ = _service(market_data=market_data)

    result = service.analyze("SANB11")

    fii.analisar.assert_not_called()
    valuation.processar.assert_called_once()
    peers.comparar.assert_called_once_with("SANB11")
    assert result.is_fii is False


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
