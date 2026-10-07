# V3.2 Silver Executive Upgrade

- Main navigation consolidated from 25 horizontal tabs to 9 vertical sidebar sections.
- Related legacy modules are grouped under Funds/AUM/Portfolio; Market/Competitors; Financials/Scenarios; Risk/Governance/Data Quality; Advisory/Decisions/Board Pack; Commercial/Investor/Product Strategy; Stock Intelligence AI; Portfolio/CIO AI.
- Removed horizontal three-statement sub-tabs; replaced by a compact selector.
- Executive Command Center now reads the investment cache and surfaces BUY, REDUCE/SELL and recommended portfolio when a full-factor Silver cache is available.
- If a full-factor cache is not available, Executive intentionally withholds BUY/SELL and shows verified Silver money-flow leaders/laggards instead of demo recommendations.
- `refresh_silver_ai.py` now performs a real Silver refresh for foreign, proprietary and active flow, filters obvious non-equity warrant codes, calculates cross-sectional flow scores, and writes `data_cache/silver_flow_snapshot.csv` plus metadata.
- Credentials are not printed or stored.

## Local refresh
Activate the licensed Python 3.12 environment, then run:

    python refresh_silver_ai.py
    streamlit run app.py

The flow cache is verified Silver data. A BUY/SELL recommendation remains withheld until sufficient fundamental, valuation, technical and liquidity evidence is available in `silver_stock_snapshot.csv`.
