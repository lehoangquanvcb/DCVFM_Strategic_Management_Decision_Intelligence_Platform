# DCVFM Corporate Performance, Risk & Management Intelligence Platform V4.3

Maintenance update: the Market, Liquidity & Macro tab now attempts row-level live
macro retrieval through Vnstock Data and falls back to the labelled Master row
when an endpoint is unavailable. News & Operating Events also tolerates missing
or alternative date fields without stopping the Streamlit app.

Author: Le Hoang Quan

V4.3 adds a scenario-to-financial-statements engine to the complete V4.2 operating platform.

## V4.3 focus

- 19 consolidated tabs for company operations and management.
- Financial Impact tab translating market and management scenarios into AUM, revenue, PBT, NPAT, cash flow, assets, equity, ROA and ROE.
- Formula-driven scenario assumptions, financial impact model and reconciliation checks in the Master Excel.
- Fund performance, AUM, flows, portfolio and ETF monitoring.
- Upgraded Market, Liquidity & Macro Intelligence with VN-Index level, 1M/3M/YTD returns, volatility, drawdown, 52-week-high gap, regime, MA20/50/200, volume and macro pulse.
- Financial performance, product profitability and distribution economics.
- Business-plan Actual/Budget/Forecast control.
- Enterprise risk, investor-redemption EWS and compliance cockpit.
- Operating KPI, service quality and management decision tracker.
- Advisory Engine, grounded Copilot and PDF/PPTX Board Pack.
- Responsive KPI cards: compact on desktop and two-column mobile grid.

## Data architecture

- Company and operating inputs: `data/DCVFM_Corporate_Performance_Risk_Management_Intelligence_Master_V4_3.xlsx`.
- Live market inputs: authenticated Vnstock routes.
- Failure order: live Vnstock → last successful cache → clearly labelled illustrative fallback.
- The API key is never written to source code, Master Excel, logs or downloads.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For Streamlit Community Cloud, store `VNSTOCK_API_KEY` in App Settings → Secrets. Rows labelled `Assumption` must be replaced or verified before formal management or regulatory use.
