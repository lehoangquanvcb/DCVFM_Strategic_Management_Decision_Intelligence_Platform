# DCVFM V3.3.11 — Full-Market ICB Sector Mapping

Uses verified `Reference().equity.list_by_industry(lang='vi')` schema (`symbol`, `icb_level`, `icb_code`, `icb_name`). Selects ICB level 2 per ticker, falls back to level 1; preserves levels 1–4 for audit. Ambiguous code assignments at the same level are excluded. Symbols are filtered to three uppercase letters, then merged into the **existing** stock cache; no price or financial statement refresh.

## Run locally (Windows CMD)

```bat
cd /d "E:\Lac Viet\DCVFM_Strategic_Management_Decision_Intelligence_Platform"
call C:\Users\HP\.venv\Scripts\activate.bat
python refresh_silver_ai.py --sector-only
```

Look for `REFERENCE ICB: ... unique symbols`, `SECTOR: mapped ... / 1220`, `DATA QUALITY` and `READY`. Mapping is written to `sector_mapping.csv`; keep it local unless your Vnstock data license permits redistribution. `data_cache/silver_stock_snapshot.csv`, `silver_sector_snapshot.csv`, and `silver_metadata.json` are regenerated. Back up `data_cache` before first run.

If API fails, existing mapping is retained, not fabricated. A successful mapping does **not** by itself validate investment recommendations, model assumptions, timeliness, or regulatory/licensing requirements. Verify source rights before publishing caches to a public repository or Streamlit Cloud.
