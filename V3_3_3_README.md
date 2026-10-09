# V3.3.3 Sector and Growth Repair

Use `python refresh_silver_ai.py --repair-cache` to reapply verified mapping and preserve existing prices and flows. Place `sector_mapping.csv` in project root, with `symbol,sector` and optionally `source,as_of_date`; populate only with verified security master labels. Template provided. Never infer sectors from ticker.

Use `python refresh_silver_ai.py --repair-cache --enrich-growth` to attempt licensed annual income statement extraction for 120 symbols. This can make many API requests. Only unambiguous long-form annual statements are supported; financial institutions or other schemas may remain unavailable. Missing values remain NaN and READY remains false until sufficient coverage.

Do not push credentials or confidential data. Do not treat ex-post holdings comparisons as investable backtests.
