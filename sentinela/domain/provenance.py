"""Field-level provenance transport models."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any


def _as_dict(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return dict(data)
    return {}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    return [str(value)]


def _as_provenance(value: Any) -> "FieldProvenance":
    if isinstance(value, FieldProvenance):
        return value
    return FieldProvenance.from_dict(value)


def _clamp(value: Any, default: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, min(1.0, number))


@dataclass
class FieldProvenance:
    source: str = "unknown"
    collected_at: str | None = None
    as_of: str | None = None
    confidence: float = 1.0
    stale: bool = False
    manual: bool = False
    cached: bool = False
    warnings: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.source = str(self.source or "unknown")
        self.warnings = _as_list(self.warnings)
        self.extra = _as_dict(self.extra)

    @classmethod
    def from_dict(cls, data: dict | None) -> "FieldProvenance":
        raw = _as_dict(data)
        known = {
            "source",
            "collected_at",
            "as_of",
            "confidence",
            "stale",
            "manual",
            "cached",
            "warnings",
            "extra",
        }
        extra = _as_dict(raw.get("extra"))
        extra.update({key: value for key, value in raw.items() if key not in known})
        return cls(
            source=raw.get("source") or "unknown",
            collected_at=raw.get("collected_at"),
            as_of=raw.get("as_of"),
            confidence=raw.get("confidence", 1.0),
            stale=bool(raw.get("stale", False)),
            manual=bool(raw.get("manual", False)),
            cached=bool(raw.get("cached", False)),
            warnings=_as_list(raw.get("warnings")),
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source or "unknown",
            "collected_at": self.collected_at,
            "as_of": self.as_of,
            "confidence": self.confidence,
            "stale": self.stale,
            "manual": self.manual,
            "cached": self.cached,
            "warnings": list(self.warnings),
            "extra": dict(self.extra),
        }

    def add_warning(self, warning: str) -> None:
        if warning:
            self.warnings.append(str(warning))

    def with_warning(self, warning: str) -> "FieldProvenance":
        clone = replace(self, warnings=list(self.warnings), extra=dict(self.extra))
        clone.add_warning(warning)
        return clone

    def normalized_confidence(self) -> float:
        return _clamp(self.confidence)


@dataclass
class FieldValue:
    value: Any
    unit: str | None = None
    provenance: FieldProvenance = field(default_factory=FieldProvenance)
    name: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.provenance = _as_provenance(self.provenance)
        self.extra = _as_dict(self.extra)

    @classmethod
    def from_dict(cls, data: dict | None) -> "FieldValue":
        if not isinstance(data, dict):
            return cls(value=data)

        known = {"value", "unit", "provenance", "name", "extra"}
        extra = _as_dict(data.get("extra"))
        extra.update({key: value for key, value in data.items() if key not in known})
        return cls(
            value=data.get("value"),
            unit=data.get("unit"),
            provenance=FieldProvenance.from_dict(data.get("provenance")),
            name=data.get("name"),
            extra=extra,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "provenance": self.provenance.to_dict(),
            "name": self.name,
            "extra": dict(self.extra),
        }

    def is_missing(self) -> bool:
        return self.value is None or self.value == ""

    def warning_flags(self) -> list[str]:
        flags = list(self.provenance.warnings)
        if self.is_missing():
            flags.append("missing_value")
        if self.provenance.stale:
            flags.append("stale_data")
        if self.provenance.manual:
            flags.append("manual_data")
        if self.provenance.cached:
            flags.append("cached_data")
        if self.provenance.normalized_confidence() < 0.5:
            flags.append("low_confidence")
        return flags


@dataclass
class ProvenancedPayload:
    fields: dict[str, FieldValue] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.fields = {
            str(name): value if isinstance(value, FieldValue) else FieldValue.from_dict(value)
            for name, value in _as_dict(self.fields).items()
        }
        self.extra = _as_dict(self.extra)

    @classmethod
    def from_dict(cls, data: dict | None) -> "ProvenancedPayload":
        raw = _as_dict(data)
        raw_fields = raw.get("fields")
        fields = raw_fields if isinstance(raw_fields, dict) else {}
        extra = _as_dict(raw.get("extra"))
        extra.update({key: value for key, value in raw.items() if key not in {"fields", "extra"}})
        return cls(fields={key: FieldValue.from_dict(value) for key, value in fields.items()}, extra=extra)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fields": {name: field_value.to_dict() for name, field_value in self.fields.items()},
            "extra": dict(self.extra),
        }

    def set_field(
        self,
        name: str,
        value: Any,
        unit: str | None = None,
        provenance: FieldProvenance | dict | None = None,
    ) -> None:
        field_name = str(name)
        self.fields[field_name] = FieldValue(
            value=value,
            unit=unit,
            provenance=_as_provenance(provenance),
            name=field_name,
        )

    def get_value(self, name: str, default: Any = None) -> Any:
        field_value = self.get_field(name)
        if field_value is None:
            return default
        return field_value.value

    def get_field(self, name: str) -> FieldValue | None:
        return self.fields.get(str(name))

    def missing_fields(self, names: list[str]) -> list[str]:
        missing: list[str] = []
        for name in names:
            field_value = self.get_field(name)
            if field_value is None or field_value.is_missing():
                missing.append(name)
        return missing

    def warnings_by_field(self) -> dict[str, list[str]]:
        return {
            name: warnings
            for name, field_value in self.fields.items()
            if (warnings := field_value.warning_flags())
        }

    def data_quality_score(self) -> float:
        if not self.fields:
            return 1.0

        penalty = 0.0
        for field_value in self.fields.values():
            flags = set(field_value.warning_flags())
            if "missing_value" in flags:
                penalty += 0.25
            if "stale_data" in flags:
                penalty += 0.15
            if "manual_data" in flags:
                penalty += 0.10
            if "cached_data" in flags:
                penalty += 0.05
            if "low_confidence" in flags:
                penalty += 0.15
            penalty += min(0.10, 0.02 * len(field_value.provenance.warnings))

        score = 1.0 - (penalty / max(len(self.fields), 1))
        return _clamp(score)
