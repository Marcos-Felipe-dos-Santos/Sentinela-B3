from sentinela.domain.provenance import (
    FieldProvenance,
    FieldValue,
    ProvenancedPayload,
)


def test_field_provenance_defaults():
    provenance = FieldProvenance.from_dict(None)

    assert provenance.source == "unknown"
    assert provenance.confidence == 1.0
    assert isinstance(provenance.warnings, list)


def test_field_provenance_confidence_clamped():
    assert FieldProvenance(confidence=1.4).normalized_confidence() == 1.0
    assert FieldProvenance(confidence=-0.2).normalized_confidence() == 0.0


def test_field_value_nested_roundtrip():
    field_value = FieldValue(
        value=10,
        unit="BRL",
        provenance=FieldProvenance(source="yfinance", collected_at="2026-05-05"),
        name="preco_atual",
    )

    roundtrip = FieldValue.from_dict(field_value.to_dict())

    assert roundtrip.value == 10
    assert roundtrip.unit == "BRL"
    assert roundtrip.name == "preco_atual"
    assert roundtrip.provenance.source == "yfinance"
    assert roundtrip.provenance.collected_at == "2026-05-05"


def test_field_value_missing_and_warning_flags():
    field_value = FieldValue(
        value=None,
        provenance=FieldProvenance(
            source="cache",
            confidence=0.2,
            stale=True,
            manual=True,
            cached=True,
        ),
    )

    flags = field_value.warning_flags()

    assert "missing_value" in flags
    assert "stale_data" in flags
    assert "manual_data" in flags
    assert "cached_data" in flags
    assert "low_confidence" in flags


def test_provenanced_payload_set_and_get_field():
    payload = ProvenancedPayload()
    payload.set_field(
        "preco_atual",
        25.5,
        unit="BRL",
        provenance={"source": "yfinance"},
    )

    assert payload.get_value("preco_atual") == 25.5
    field_value = payload.get_field("preco_atual")
    assert isinstance(field_value, FieldValue)
    assert field_value.unit == "BRL"
    assert field_value.provenance.source == "yfinance"


def test_provenanced_payload_missing_fields():
    payload = ProvenancedPayload()
    payload.set_field("preco_atual", 25.5)

    missing = payload.missing_fields(["preco_atual", "dy", "pl"])

    assert missing == ["dy", "pl"]


def test_provenanced_payload_warnings_by_field():
    payload = ProvenancedPayload()
    payload.set_field(
        "vacancia",
        0.12,
        provenance=FieldProvenance(
            source="manual_fallback",
            stale=True,
            manual=True,
            warnings=["estimated"],
        ),
    )

    warnings = payload.warnings_by_field()

    assert "vacancia" in warnings
    assert "estimated" in warnings["vacancia"]
    assert "stale_data" in warnings["vacancia"]
    assert "manual_data" in warnings["vacancia"]


def test_provenanced_payload_quality_score_degrades():
    clean = ProvenancedPayload()
    clean.set_field("preco_atual", 25.5, provenance={"source": "yfinance"})
    clean.set_field("dy", 0.08, provenance={"source": "brapi"})

    dirty = ProvenancedPayload()
    dirty.set_field(
        "preco_atual",
        None,
        provenance={"source": "cache", "cached": True, "stale": True},
    )
    dirty.set_field(
        "dy",
        0.08,
        provenance={"source": "manual_fallback", "manual": True, "confidence": 0.3},
    )

    clean_score = clean.data_quality_score()
    dirty_score = dirty.data_quality_score()

    assert 0.0 <= clean_score <= 1.0
    assert 0.0 <= dirty_score <= 1.0
    assert dirty_score < clean_score


def test_provenanced_payload_from_malformed_input_does_not_crash():
    empty_none = ProvenancedPayload.from_dict(None)
    empty_dict = ProvenancedPayload.from_dict({})
    with_field = ProvenancedPayload.from_dict({"fields": {"dy": {"value": 0.08}}})

    assert empty_none.fields == {}
    assert empty_dict.fields == {}
    assert with_field.get_value("dy") == 0.08

