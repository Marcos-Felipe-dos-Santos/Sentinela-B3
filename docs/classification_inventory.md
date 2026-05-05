# Asset Classification Inventory

Phase 3.5 is documentation only. No caller was migrated in this phase.

## Summary

Central classifier:

- `sentinela/services/asset_classifier.py` contains the intended central implementation.
- It normalizes tickers, preserves `FIIS_CONHECIDOS`, preserves `UNITS_CONHECIDAS`, treats known Units as non-FII, and documents the intentional safety invariant that a known Unit must not become FII even if `quote_type == "MUTUALFUND"`.

Already migrated to `AssetClassifier`:

- `sentinela/services/analyze_asset.py`
- `auditar_recomendacoes.py`
- `portfolio_engine.py`

Still containing active duplicated classification logic:

- `app.py`
- `market_engine.py`

Legacy, maintenance, documentation, or test copies:

- `auditoria.py` is legacy/deep diagnostic and should remain untouched until a dedicated phase.
- `limpar_banco.py` is a maintenance cleanup script with its own historical checks.
- `tests/test_asset_classifier_equivalence.py` intentionally keeps a local copy of the app rule as a test fixture.
- `AGENTS.md` contains historical/documentation examples and should not be treated as production logic.

Recommended migration order:

1. `app.py`, because it is the UI routing point between `FIIEngine` and `ValuationEngine`.
2. `market_engine.py`, because it still chooses required fundamental fields and manual FII fallback using local classification helpers.
3. `limpar_banco.py`, only if that utility is still used operationally.
4. `auditoria.py`, only in a separate legacy diagnostic phase.

## Current Migrated Files

### `sentinela/services/analyze_asset.py`

- Context: service-level routing between `FIIEngine` and `ValuationEngine`.
- Current state: uses `self.asset_classifier.is_fii(ticker_norm, dados)`.
- Classification source: `AssetClassifier`.
- Risk: low. This service is not wired into `app.py` yet.
- Recommendation: keep as migrated.

### `auditar_recomendacoes.py`

- Context: operational audit routing between `FIIEngine` and `ValuationEngine`.
- Current state: instantiates one `AssetClassifier` during audit setup and calls `asset_classifier.is_fii(ticker, dados)`.
- Classification source: `AssetClassifier`.
- Risk: low to medium. Audit output may drift for unsafe Unit cases, but this is intended.
- Recommendation: keep as migrated.

### `portfolio_engine.py`

- Context: groups portfolio columns into FII and stock buckets before applying the current allocation policy.
- Current state: `PortfolioEngine.__init__` accepts/inits `AssetClassifier`, and `otimizar()` calls `self.asset_classifier.is_fii(c)`.
- Classification source: `AssetClassifier`.
- Risk: low to medium. Known Units now stay in the stock bucket, which is intended.
- Recommendation: keep as migrated.

## Remaining Duplicated Logic

### `app.py`

- Approximate context: Terminal mode, "B. Deteccao FII", before routing to `FIIEngine.analisar()` or `ValuationEngine.processar()`.
- Pattern found:
  - imports `FIIS_CONHECIDOS` and `UNITS_CONHECIDAS`
  - local `is_fii = (...)`
  - `ticker in FIIS_CONHECIDOS`
  - `dados.get('quote_type') == 'MUTUALFUND'`
  - `"11" in ticker`
  - `ticker not in UNITS_CONHECIDAS`
- Category: active production UI code.
- Risk level: high.
- Why it matters: this is the visible app route from market data into FII vs stock valuation. A wrong classification changes which engine handles the asset.
- Recommendation: migrate now, in the next phase, with the smallest possible diff.

### `market_engine.py`

- Approximate context: module helper `_is_fii_ticker()` and `_required_fundamentals_for()`.
- Pattern found:
  - imports `FIIS_CONHECIDOS` and `UNITS_CONHECIDAS`
  - `quote_type == 'MUTUALFUND'`
  - `ticker_norm.endswith("11")`
  - `ticker_norm not in UNITS_CONHECIDAS`
- Category: active production market-data code.
- Risk level: medium to high.
- Why it matters: this decides whether stock or FII fundamentals are required, which affects `campos_faltantes`, `dados_parciais`, cache validity, and downstream data quality.
- Recommendation: migrate later, after `app.py`, unless market data quality bugs become the immediate priority.

### `market_engine.py`

- Approximate context: `_aplicar_fallback_manual_fii()`.
- Pattern found:
  - `not ticker_norm.endswith("11")`
  - `ticker_norm in UNITS_CONHECIDAS`
  - `FII_MANUAL_FALLBACK`
- Category: active production fallback logic.
- Risk level: medium.
- Why it matters: this controls whether manual FII fallback data may fill missing fields. Units are already excluded, but the logic duplicates part of the classifier.
- Recommendation: migrate later together with `_is_fii_ticker()`, while preserving the separate requirement that a ticker must also exist in `FII_MANUAL_FALLBACK`.

### `auditoria.py`

- Approximate context: legacy/deep diagnostic routing near the valuation section.
- Pattern found:
  - imports `FIIS_CONHECIDOS` and `UNITS_CONHECIDAS`
  - `qt = dados.get('quote_type', '')`
  - local `is_fii = (...)`
  - `qt == 'MUTUALFUND'`
  - `'11' in ticker`
  - `ticker not in UNITS_CONHECIDAS`
- Category: legacy diagnostic script.
- Risk level: medium if used for production decisions; low if kept as historical diagnostic.
- Why it matters: it can still route Units differently from the central classifier in synthetic or bad-data cases.
- Recommendation: keep as legacy reference for now. Migrate only in a dedicated phase for `auditoria.py`.

### `limpar_banco.py`

- Approximate context: database cleanup rules for historical wrong classifications.
- Pattern found:
  - imports `FIIS_CONHECIDOS` and `UNITS_CONHECIDAS`
  - redefines a smaller local `FIIS_CONHECIDOS`
  - checks Units with `perfil == 'FII'`
  - checks FIIs with `perfil != 'FII'`
- Category: maintenance utility.
- Risk level: low to medium.
- Why it matters: it may intentionally encode historical cleanup assumptions rather than live routing.
- Recommendation: migrate later only if this script is still used. Otherwise keep as maintenance reference.

### `tests/test_asset_classifier_equivalence.py`

- Approximate context: local helper `legacy_app_is_fii()`.
- Pattern found:
  - imports `FIIS_CONHECIDOS` and `UNITS_CONHECIDAS`
  - local reproduction of the current app rule
  - `quote_type == "MUTUALFUND"`
  - `"11" in ticker_norm`
  - Unit exclusion
- Category: test fixture.
- Risk level: low.
- Why it matters: this is intentional coverage proving where `AssetClassifier` matches or intentionally improves the app rule.
- Recommendation: keep as test fixture until app migration is complete. After app migration, update it to compare against the new expected app path or archive the legacy-rule helper.

### `AGENTS.md`

- Approximate context: historical bug/improvement notes and architecture notes.
- Pattern found:
  - examples of old `app.py`, `auditoria.py`, and `portfolio_engine.py` classification snippets
  - references to `FIIS_CONHECIDOS`, `UNITS_CONHECIDAS`, `quote_type`, `MUTUALFUND`, suffix `11`
- Category: documentation/history.
- Risk level: low.
- Recommendation: keep as documentation, but update after `app.py` and `market_engine.py` migrations so future agents do not treat old snippets as active instructions.

### Non-routing occurrences

These occurrences are not duplicated classification decisions:

- `config.py`: owns the source constants `FIIS_CONHECIDOS` and `UNITS_CONHECIDAS`. Keep.
- `brapi_provider.py`: maps provider `quoteType` into `quote_type`. Keep.
- `sentinela/domain/models.py`: has transport fields such as `quote_type` and `is_fii`. Keep.
- `sentinela/repositories/analysis_repository.py`: extracts/stores `asset_type` and `is_fii` metadata from payloads. Keep.
- Tests for providers, models, repository, service, audit, and portfolio use `quote_type`, `asset_type`, or fake `is_fii` methods as fixtures. Keep.

## app.py Migration Notes

Later `app.py` migration should be deliberately small:

1. Import `AssetClassifier`:
   - `from sentinela.services.asset_classifier import AssetClassifier`
2. Instantiate the classifier once near engine/resource setup.
   - Best fit is likely inside `load_engines()` or immediately after it, matching how engines are cached.
3. Replace only the inline `is_fii = (...)` block in Terminal mode.
   - New route should call `asset_classifier.is_fii(ticker, dados)`.
4. Preserve current UI behavior around messages, tabs, metrics, persistence, and chart rendering.
5. Preserve the Unit safety invariant.
   - Known Units must not go to `FIIEngine`, even if `quote_type == "MUTUALFUND"`.
6. Add validation before/after:
   - `SANB11` or `TAEE11` should route as stock/non-FII.
   - `HGLG11` or `MXRF11` should route as FII even if `quote_type` is missing.
   - `ABCD11` style unknown suffix-11 ticker should preserve current fallback behavior.
   - Normal stocks such as `PETR4`, `VALE3`, `ITUB4`, and `WEGE3` should route as stocks.
7. Keep the diff limited to import/setup plus the routing line.

## Risks

- Known intentional divergence: Units should not become FIIs even if `quote_type == "MUTUALFUND"`.
- Route changes can switch an asset from `FIIEngine` to `ValuationEngine`, changing output while formulas remain untouched.
- Operational audit result drift is possible for bad provider classifications, but this was already accepted in Phase 3.3.
- `app.py` UI regression risk is high because Streamlit flow mixes routing, rendering, AI, persistence, and chart tabs in one file.
- `market_engine.py` classification affects data quality flags and cache decisions, not just valuation routing.
- `auditoria.py` is legacy/deep diagnostic; changing it casually could make historical diagnostic output harder to compare.

## Recommended Next Phase

Recommended next phase: **Phase 3.6: migrate `app.py` to `AssetClassifier` in the smallest possible diff**.

Reasoning:

- `app.py` is the only remaining active user-facing route that still duplicates the old classification logic.
- `AnalysisService`, operational audit, and portfolio grouping already use the classifier.
- The next change can be small and easy to review: import/setup classifier, replace inline `is_fii`, preserve all UI rendering and downstream behavior.
- `market_engine.py` should follow after `app.py`, because it has active duplicated logic but touches data quality and fallback behavior, which deserves its own focused phase.

