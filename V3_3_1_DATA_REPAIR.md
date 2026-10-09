# V3.3.1 Data Repair

- Full-factor readiness now requires >=80% non-null coverage for sector, PE, PB, ROE, price returns, liquidity and money flow, with >=20 stocks.
- Optional `sector_mapping.csv` at project root: columns `symbol,sector`, sourced from a verified security master. Unknown sectors are not guessed.
- Flow scores are explicitly merged by normalized symbol and missing scores are not replaced with 50.
- Sector charts are withheld if all sectors are Unknown.
- Cloud banner accurately describes authenticated local Silver cache.
- If data quality is insufficient, BUY/SELL and recommended portfolio must remain withheld.
- Macro GDP endpoint failures remain visible as missing coverage; no synthetic macro figures.

Run `python refresh_silver_ai.py` locally, inspect coverage and READY status, then redeploy cache only after verifying permitted redistribution.
