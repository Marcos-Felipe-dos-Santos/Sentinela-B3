from sentinela.domain.models import (
    AnalysisResult,
    DataQualityReport,
    FundamentalsSnapshot,
    MarketSnapshot,
    TechnicalResult,
    ValuationResult,
)


def test_transport_models_roundtrip_and_keep_unknown_fields():
    payloads = {
        MarketSnapshot: {
            "ticker": "PETR4",
            "preco_atual": 30.5,
            "source": "yfinance",
            "warnings": ["partial"],
            "campo_novo": "preservado",
        },
        FundamentalsSnapshot: {
            "ticker": "PETR4",
            "pl": 6.2,
            "pvp": 1.1,
            "dy": 0.08,
            "roe": 0.18,
            "source": "brapi",
            "campo_novo": {"origem": "teste"},
        },
        DataQualityReport: {
            "erro_scraper": True,
            "dados_parciais": False,
            "campos_faltantes": None,
            "riscos_dados": ["cache"],
            "confidence": 80,
            "campo_novo": "ok",
        },
        ValuationResult: {
            "fair_value": 40.0,
            "upside": 20.0,
            "score_final": 70,
            "recomendacao": "COMPRA",
            "riscos": None,
            "campo_novo": 123,
        },
        TechnicalResult: {
            "rsi": 55,
            "tendencia": "Alta",
            "atr": 1.2,
            "campo_novo": "tecnico",
        },
        AnalysisResult: {
            "ticker": "PETR4",
            "is_fii": False,
            "success": True,
            "market": {"ticker": "PETR4", "preco_atual": 30.5, "campo_novo": "m"},
            "fundamentals": {"pl": 6.2, "campo_novo": "f"},
            "data_quality": {"dados_cache": True, "campo_novo": "q"},
            "valuation": {"recomendacao": "NEUTRO", "campo_novo": "v"},
            "technical": {"rsi": 50, "campo_novo": "t"},
            "peers": {"Setor": "petroleo"},
            "raw": {"ticker": "PETR4"},
            "campo_novo": "analysis",
        },
    }

    for model_cls, payload in payloads.items():
        first = model_cls.from_dict(payload).to_dict()
        second = model_cls.from_dict(first).to_dict()

        assert second == first
        assert first["campo_novo"] == payload["campo_novo"]


def test_missing_fields_default_safely():
    result = AnalysisResult.from_dict({})

    assert result.to_dict()["ticker"] == ""
    assert result.market.to_dict()["preco_atual"] is None
    assert result.data_quality.to_dict()["campos_faltantes"] == []
    assert result.valuation.to_dict()["riscos"] == []

