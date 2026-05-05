from sentinela.domain.enums import AssetType
from sentinela.services.asset_classifier import AssetClassifier


def test_normalize_ticker_removes_sa_and_uppercases():
    classifier = AssetClassifier(fiis_conhecidos=set(), units_conhecidas=set())

    assert classifier.normalize_ticker(" petr4.sa ") == "PETR4"


def test_known_fii_is_classified_as_fii_without_quote_type():
    classifier = AssetClassifier(fiis_conhecidos={"HGLG11"}, units_conhecidas=set())

    assert classifier.classify("HGLG11") == AssetType.FII
    assert classifier.is_fii("HGLG11") is True


def test_known_unit_is_not_classified_as_fii():
    classifier = AssetClassifier(
        fiis_conhecidos=set(),
        units_conhecidas={"SANB11", "TAEE11"},
    )

    assert classifier.classify("SANB11") == AssetType.UNIT
    assert classifier.is_fii("SANB11") is False


def test_mutualfund_quote_type_classifies_as_fii():
    classifier = AssetClassifier(fiis_conhecidos=set(), units_conhecidas=set())

    assert classifier.classify("ABCD3", {"quote_type": "MUTUALFUND"}) == AssetType.FII


def test_mutualfund_known_unit_still_classifies_as_unit():
    classifier = AssetClassifier(fiis_conhecidos=set(), units_conhecidas={"SANB11"})

    result = classifier.classify("SANB11", {"quote_type": "MUTUALFUND"})

    assert result == AssetType.UNIT
    assert classifier.is_fii("SANB11", {"quote_type": "MUTUALFUND"}) is False


def test_suffix_11_classifies_as_fii_when_not_unit():
    classifier = AssetClassifier(fiis_conhecidos=set(), units_conhecidas=set())

    assert classifier.classify("ABCD11") == AssetType.FII


def test_suffix_11_known_unit_classifies_as_unit():
    classifier = AssetClassifier(fiis_conhecidos=set(), units_conhecidas={"TAEE11"})

    assert classifier.classify("TAEE11") == AssetType.UNIT


def test_regular_stock_classifies_as_stock():
    classifier = AssetClassifier(fiis_conhecidos=set(), units_conhecidas=set())

    assert classifier.classify("PETR4") == AssetType.STOCK


def test_empty_ticker_classifies_as_unknown():
    classifier = AssetClassifier(fiis_conhecidos=set(), units_conhecidas=set())

    assert classifier.classify("") == AssetType.UNKNOWN
    assert classifier.classify(None) == AssetType.UNKNOWN
    assert classifier.classify("   ") == AssetType.UNKNOWN


def test_classifier_does_not_require_market_data():
    classifier = AssetClassifier(fiis_conhecidos={"HGLG11"}, units_conhecidas=set())

    assert classifier.classify("HGLG11", dados=None) == AssetType.FII

