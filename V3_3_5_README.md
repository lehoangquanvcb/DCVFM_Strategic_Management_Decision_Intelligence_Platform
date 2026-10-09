# V3.3.5 — Dynamic HOSE Universe and Sector Mapping

## Why 120 stocks?
Previous refresh_silver_ai.py hard-coded `MAX_SYMBOLS=120` and selected the top 120 symbols by **absolute** foreign/proprietary flows. This is a data collection cap, not a Silver license limit or a ranking of best stocks.

## Commands

- `python refresh_silver_ai.py --repair-cache --enrich-growth`: reprocess current cache (does **not** expand the 120-stock universe).
- `python refresh_silver_ai.py --max-symbols 300 --enrich-growth`: new full HOSE refresh, capped at 300 symbols.
- `python refresh_silver_ai.py --max-symbols 0 --enrich-growth`: new full HOSE refresh for all 3-letter symbols available in HOSE flow results; potentially hundreds of paid API calls and considerable runtime.
- `python refresh_silver_ai.py --repair-cache --sector-file sector_mapping.csv`: apply verified sectors to existing stock cache.

The existing screener integration can automatically populate sectors **only if** the screener returns `sector`/`sector_lv1`. Prior user test returned zero screener rows; the package therefore does not claim working automatic Silver sector discovery. Supply `sector_mapping.csv` from a verified listing/reference source (columns `symbol,sector`, optionally `source,as_of_date`). Unknown sectors remain Unknown and quality gate remains false.

**Limitations**: universe expansion is currently HOSE only, because flow endpoints are explicitly `exchange='HOSE'`. The regex for three-letter tickers is a coarse filter, not definitive listing-status verification. The full refresh rewrites local caches; back up `data_cache` first. This does not expand existing cache when using `--repair-cache`. Data coverage alone does not prove financial correctness. Never publish keys or unlicensed raw market data.
