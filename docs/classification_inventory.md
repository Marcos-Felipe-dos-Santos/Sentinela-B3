# Asset Classification Inventory

Phase 3.8 is documentation only. It records the current state after the active
asset-routing paths were migrated to `AssetClassifier`.

## Summary

Central classifier:

- `sentinela/services/asset_classifier.py` contains the central implementation.
- It normalizes tickers, preserves `FIIS_CONHECIDOS`, preserves
  `UNITS_CONHECIDAS`, treats known Units as non-FII, and keeps the safety
  invariant that a known Unit must not become FII even if
  `quote_type == "MUTUALFUND"`.

Active files now migrated to `AssetClassifier`:

- `sentinela/services/analyze_asset.py`
- `auditar_recomendacoes.py`
- `portfolio_engine.py`
- `app.py`
- `market_engine.py`

`app.py` and `market_engine.py` should no longer be listed as active
unmigrated production code. Their remaining references to FII/Unit
classification should be through `AssetClassifier` or historical comments.

Remaining non-central copies:

- `auditoria.py` is legacy/deep diagnostic and should remain untouched until a
  dedicated phase.
- `limpar_banco.py` is a maintenance cleanup utility with historical checks.
- `tests/test_asset_classifier_equivalence.py` intentionally keeps a local
  legacy-rule helper as a regression/documentation fixture.
- `AGENTS.md` may contain archived historical snippets; those are documentation,
  not active production rules.

## Current Migrated Files

### `sentinela/services/analyze_asset.py`

- Context: service-level routing between `FIIEngine` and `ValuationEngine`.
- Current state: initializes or accepts `AssetClassifier` and calls
  `self.asset_classifier.is_fii(ticker_norm, dados)`.
- Classification source: `AssetClassifier`.
- Risk: low. Keep as migrated.

### `auditar_recomendacoes.py`

- Context: operational audit routing between `FIIEngine` and `ValuationEngine`.
- Current state: instantiates one `AssetClassifier` during audit setup and calls
  `asset_classifier.is_fii(ticker, dados)`.
- Classification source: `AssetClassifier`.
- Risk: low to medium. Audit output may drift for unsafe Unit cases, but this is
  intended.
- Recommendation: keep as migrated.

### `portfolio_engine.py`

- Context: groups portfolio columns into FII and stock buckets before applying
  the current allocation policy.
- Current state: `PortfolioEngine.__init__` accepts/initializes
  `AssetClassifier`, and `otimizar()` calls `self.asset_classifier.is_fii(c)`.
- Classification source: `AssetClassifier`.
- Risk: low to medium. Known Units now stay in the stock bucket, which is
  intended.
- Recommendation: keep as migrated.

### `app.py`

- Context: Terminal mode route from collected market data into either
  `FIIEngine.analisar()` or `ValuationEngine.processar()`.
- Current state: `load_engines()` creates one `AssetClassifier`, and the local
  `is_fii` variable is assigned with `asset_classifier.is_fii(ticker, dados)`.
- Classification source: `AssetClassifier`.
- Risk: medium. This is user-facing routing, so future edits should preserve UI,
  persistence, AI, metrics, tabs, and chart behavior.
- Recommendation: keep as migrated.

### `market_engine.py`

- Context: required fundamentals, `dados_parciais`, `campos_faltantes`, cache
  validity, and manual FII fallback.
- Current state: `MarketEngine` accepts/initializes `AssetClassifier`;
  `_is_fii_ticker()` delegates to the classifier; required-field and cache checks
  pass through the same classifier source.
- Classification source: `AssetClassifier`.
- Risk: medium. This affects data-quality flags and fallback decisions, not just
  valuation routing.
- Recommendation: keep as migrated and avoid changing provider order or manual
  fallback values.

## Remaining Duplicated Logic

### `auditoria.py`

- Approximate context: legacy/deep diagnostic routing near the valuation
  section.
- Pattern found:
  - imports `FIIS_CONHECIDOS` and `UNITS_CONHECIDAS`
  - local `is_fii` decision
  - `quote_type == "MUTUALFUND"` style checks
  - suffix-`11` checks with Unit exclusion
- Category: legacy diagnostic script.
- Risk level: medium if used for production decisions; low if kept as historical
  diagnostic.
- Recommendation: migrate later only in a dedicated `auditoria.py` phase, or keep
  as a legacy reference if the script is intentionally frozen.

### `limpar_banco.py`

- Approximate context: database cleanup rules for historical wrong
  classifications.
- Pattern found:
  - imports or defines FII/Unit sets
  - checks Units with `perfil == "FII"`
  - checks FIIs with `perfil != "FII"`
- Category: maintenance utility.
- Risk level: low to medium.
- Recommendation: migrate later only if this utility is still used
  operationally. Otherwise keep as maintenance reference.

### `tests/test_asset_classifier_equivalence.py`

- Approximate context: local helper `legacy_app_is_fii()`.
- Pattern found:
  - local reproduction of the pre-migration app rule
  - `quote_type == "MUTUALFUND"`
  - suffix-`11` checks
  - Unit exclusion
- Category: intentional test fixture.
- Risk level: low.
- Recommendation: keep as a regression/documentation fixture while it continues
  to clarify the legacy behavior and the known Unit safety invariant.

### `AGENTS.md`

- Approximate context: archived bug notes, roadmap notes, and instructions for
  future agents.
- Pattern found:
  - historical snippets containing `FIIS_CONHECIDOS`, `UNITS_CONHECIDAS`,
    `quote_type`, `MUTUALFUND`, and suffix `11`
- Category: documentation/history.
- Risk level: low.
- Recommendation: keep historical snippets clearly marked as old/archived, and
  keep the current-state sections aligned with the migrated active paths.

### Non-routing occurrences

These occurrences are not duplicated production classification decisions:

- `config.py`: owns the source constants `FIIS_CONHECIDOS` and
  `UNITS_CONHECIDAS`. Keep.
- `sentinela/services/asset_classifier.py`: owns the central classification
  rules. Keep.
- `brapi_provider.py`: maps provider `quoteType` into `quote_type`. Keep.
- `sentinela/domain/models.py`: has transport fields such as `quote_type` and
  `is_fii`. Keep.
- `sentinela/repositories/analysis_repository.py`: extracts/stores `asset_type`
  and `is_fii` metadata from payloads. Keep.
- Tests for providers, models, repository, service, audit, portfolio, and market
  use `quote_type`, `asset_type`, or fake `is_fii` methods as fixtures. Keep.

## app.py State Notes

`app.py` has already been migrated in Phase 3.6:

1. `AssetClassifier` is imported from
   `sentinela.services.asset_classifier`.
2. `load_engines()` instantiates the classifier once alongside the existing
   engines.
3. Terminal routing preserves the local `is_fii` variable but assigns it from
   `asset_classifier.is_fii(ticker, dados)`.
4. UI layout, tabs, metrics, chart rendering, AI flow, and database save flow are
   outside the classifier migration and should remain stable.
5. The Unit safety invariant applies in the app route:
   known Units must not go to `FIIEngine`, even if
   `quote_type == "MUTUALFUND"`.

## market_engine.py State Notes

`market_engine.py` has already been migrated in Phase 3.7:

1. `MarketEngine()` still works with no arguments.
2. Tests can inject a custom classifier through
   `MarketEngine(asset_classifier=...)`.
3. `_is_fii_ticker()` remains as a compatibility helper but delegates to
   `AssetClassifier`.
4. Required fundamental selection still uses the same field lists; only the
   classification source changed.
5. Manual FII fallback still requires the ticker to exist in
   `FII_MANUAL_FALLBACK`; classifier use does not loosen fallback values.
6. Provider order remains yfinance -> Brapi -> Fundamentus -> cache/manual
   fallback.

## Risks

- Known intentional divergence: Units should not become FIIs even if
  `quote_type == "MUTUALFUND"`.
- Route changes can switch an asset from `FIIEngine` to `ValuationEngine`,
  changing output while formulas remain untouched.
- Operational audit result drift is possible for bad provider classifications,
  but this was already accepted when `auditar_recomendacoes.py` migrated.
- `app.py` UI regression risk remains high for future edits because Streamlit
  flow mixes routing, rendering, AI, persistence, and chart tabs in one file.
- `market_engine.py` classification affects data-quality flags and cache
  decisions, so future changes need focused tests.
- `auditoria.py` is legacy/deep diagnostic; changing it casually could make
  historical diagnostic output harder to compare.

## Recommended Next Phase

Recommended next phase: **Phase 3.9: optionally migrate `auditoria.py` legacy
diagnostic to `AssetClassifier`**.

If `auditoria.py` is intentionally postponed or frozen as a historical
diagnostic, skip Phase 3.9 and begin **Phase 4: provenance-by-field work**.

Reasoning:

- All active app/service/operational-audit/portfolio/market paths now use the
  central classifier.
- The remaining production-adjacent duplicate is legacy diagnostic code, not the
  normal operational audit script.
- Phase 4 can start safely once the team accepts that `auditoria.py` stays
  legacy for now.
