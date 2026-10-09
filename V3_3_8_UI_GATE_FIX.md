# V3.3.8 — UI Cache Status & Quality Gate Fix

- Correctly distinguishes Silver cache presence from recommendation readiness.
- Shows source/version/stock count/refresh timestamp for valid cache.
- Preserves blocking of BUY/SELL, model portfolio, and model portfolio comparison when data-quality gate fails.
- Provides non-recommendation factor diagnostics in blocked tabs.
- Corrects empty-sector explanation; does not fabricate sector classifications.
- Does not call Silver APIs in Streamlit Cloud or modify local refresh caches.

## Deploy
Back up project, replace source files, then commit code changes. Cache snapshot must be separately committed only where license permits redistribution. Existing V3.3.7 refresh is reusable; no new refresh required.
