# V3.3.6 — Multi-exchange flow discovery and verified sector mapping

- Default `--exchanges HOSE,HNX,UPCOM`: tries each Silver flow endpoint independently. Unsupported or empty exchanges are reported, never silently claimed as covered.
- `--max-symbols 0` processes every eligible symbol returned by supported endpoints.
- Optional `--universe-file verified_universe.csv` adds externally verified listed symbols absent from flow endpoints. CSV columns: `symbol,exchange,sector,source,as_of_date`. No fabricated labels.
- Optional `--sector-file verified_sector_mapping.csv` with `symbol,sector,source,as_of_date`; if omitted, `--universe-file` can supply sector labels. Sector coverage remains 0 if neither source nor screener supplies verified labels.
- Flow scores for symbols absent from flow endpoints are NaN (never default to 50). This may keep `READY=False`, appropriately.
- Example: `python refresh_silver_ai.py --max-symbols 0 --exchanges HOSE,HNX,UPCOM --enrich-growth`
- Example with verified source: `python refresh_silver_ai.py --max-symbols 0 --universe-file verified_universe.csv --enrich-growth`
- Back up data_cache before running; local Silver credentials are never included in the ZIP.
- CAUTION: Exchange endpoint support and sector taxonomy must be validated on the user's licensed Windows environment. This release does NOT claim automatic sector retrieval when the screener returns zero rows.
