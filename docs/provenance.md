# Field-Level Provenance

Phase 4.1 introduces pure domain models for field-level provenance. It does not
wire them into runtime engines, persistence, UI, formulas, or recommendation
rules yet.

## Why It Matters

Current analysis payloads expose aggregate source flags such as
`fonte_preco`, `fonte_fundamentos`, `dados_cache`, `dados_manual`,
`dados_parciais`, `campos_faltantes`, and `riscos_dados`.

Those flags are useful, but a single analysis can mix fields from different
sources:

- price from yfinance
- DY from Brapi
- P/VP from Fundamentus
- vacancy from manual fallback
- older fundamentals from SQLite cache
- Selic from API or fallback config

Field-level provenance makes that mixture explicit without changing the current
dict-based runtime flow.

## Examples

`preco_atual` from yfinance:

```python
FieldValue(
    name="preco_atual",
    value=25.50,
    unit="BRL",
    provenance=FieldProvenance(source="yfinance", confidence=1.0),
)
```

`dy` from Brapi:

```python
FieldValue(
    name="dy",
    value=0.08,
    unit="ratio",
    provenance=FieldProvenance(source="brapi", confidence=0.9),
)
```

`pvp` from Fundamentus:

```python
FieldValue(
    name="pvp",
    value=1.15,
    provenance=FieldProvenance(source="fundamentus", confidence=0.85),
)
```

`vacancia` from manual fallback:

```python
FieldValue(
    name="vacancia",
    value=0.12,
    unit="ratio",
    provenance=FieldProvenance(
        source="manual_fallback",
        manual=True,
        warnings=["estimated_value"],
    ),
)
```

`selic` from API or fallback:

```python
FieldValue(
    name="selic",
    value=0.1475,
    unit="annual_ratio",
    provenance=FieldProvenance(source="bacen_api", confidence=1.0),
)
```

If API retrieval fails, a future integration can mark the fallback explicitly:

```python
FieldValue(
    name="selic",
    value=0.1475,
    unit="annual_ratio",
    provenance=FieldProvenance(
        source="config_fallback",
        confidence=0.6,
        warnings=["api_unavailable"],
    ),
)
```

## Phase 4.2 - Parallel MarketEngine Metadata

`MarketEngine.buscar_dados_ticker()` now adds `field_provenance` as a parallel
metadata structure for the core fields in scope:

- `preco_atual`
- `dy`
- `pl`
- `pvp`
- `roe`

The raw fields remain unchanged. For example, `dados["dy"]` is still the numeric
ratio consumed by valuation, FII analysis, AI formatting, UI rendering, cache
logic, and legacy persistence. The new metadata lives beside it:

```python
dados["dy"] == 0.08
dados["field_provenance"]["dy"]["value"] == 0.08
```

Valuation engines still consume the existing dict values and do not receive
`FieldValue` objects. Provenance is not displayed in the Streamlit UI yet, and
it is not persisted as a first-class database feature. The current metadata is a
foundation for future auditability work.

## Phase 4.3 - Append-Only Payload Preservation

`AnalysisRepository` stores `field_provenance` inside the existing
`payload_json` snapshot. This keeps provenance attached to each append-only
analysis run without introducing a separate database table.

The legacy `DatabaseManager` and legacy `analises` table are unchanged. Older
payloads without `field_provenance` remain valid and can still be saved through
the append-only repository.
