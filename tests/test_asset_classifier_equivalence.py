import pytest

from config import FIIS_CONHECIDOS, UNITS_CONHECIDAS
from sentinela.domain.enums import AssetType
from sentinela.services.asset_classifier import AssetClassifier


def _normalize_like_app_flow(ticker):
    ticker_norm = str(ticker or "").upper().strip()
    if ticker_norm.endswith(".SA"):
        ticker_norm = ticker_norm[:-3]
    return ticker_norm.strip()


def legacy_app_is_fii(ticker: str, dados: dict | None = None) -> bool:
    ticker_norm = _normalize_like_app_flow(ticker)
    dados = dados or {}
    return (
        ticker_norm in FIIS_CONHECIDOS
        or (
            dados.get("quote_type") == "MUTUALFUND"
            or (
                "11" in ticker_norm
                and "SA" not in ticker_norm
                and ticker_norm not in UNITS_CONHECIDAS
            )
        )
    )


@pytest.mark.parametrize(
    ("ticker", "dados"),
    [
        ("PETR4", None),
        ("VALE3", None),
        ("ITUB4", None),
        ("WEGE3", None),
        ("HGLG11", None),
        ("MXRF11", None),
        ("KNRI11", None),
        ("XPML11", None),
        ("SANB11", None),
        ("TAEE11", None),
        ("KLBN11", None),
        ("ABCD11", None),
        ("ABCD11.SA", None),
        (" abcd11 ", None),
        ("ABCD3", {"quote_type": "MUTUALFUND"}),
        ("PETR4", {"quote_type": "EQUITY"}),
        ("HGLG11", {}),
        ("HGLG11", None),
    ],
)
def test_asset_classifier_matches_legacy_app_fii_rule(ticker, dados):
    classifier = AssetClassifier()

    assert classifier.is_fii(ticker, dados) is legacy_app_is_fii(ticker, dados)


def test_mutualfund_known_unit_documents_literal_legacy_divergence():
    classifier = AssetClassifier()
    dados = {"quote_type": "MUTUALFUND"}

    assert legacy_app_is_fii("SANB11", dados) is True
    assert classifier.classify("SANB11", dados) == AssetType.UNIT
    assert classifier.is_fii("SANB11", dados) is False


@pytest.mark.parametrize("ticker", ["SANB11", "TAEE11", "KLBN11"])
def test_known_units_are_not_fiis(ticker):
    classifier = AssetClassifier()

    assert legacy_app_is_fii(ticker) is False
    assert classifier.classify(ticker) == AssetType.UNIT
    assert classifier.is_fii(ticker) is False


@pytest.mark.parametrize("ticker", ["HGLG11", "MXRF11", "KNRI11", "XPML11"])
def test_known_fiis_are_fiis(ticker):
    classifier = AssetClassifier()

    assert legacy_app_is_fii(ticker) is True
    assert classifier.classify(ticker) == AssetType.FII
    assert classifier.is_fii(ticker) is True


@pytest.mark.parametrize("ticker", ["", "   ", None])
def test_invalid_tickers_are_unknown_even_though_legacy_rule_returns_false(ticker):
    classifier = AssetClassifier()

    assert legacy_app_is_fii(ticker) is False
    assert classifier.classify(ticker) == AssetType.UNKNOWN
    assert classifier.is_fii(ticker) is False


def test_asset_type_classification_examples():
    classifier = AssetClassifier()

    assert classifier.classify("PETR4") == AssetType.STOCK
    assert classifier.classify("HGLG11") == AssetType.FII
    assert classifier.classify("SANB11") == AssetType.UNIT
    assert classifier.classify("") == AssetType.UNKNOWN
