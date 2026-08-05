# DCVFM Corporate Performance, Risk & Management Intelligence Platform V4.4

Market and liquidity update: tab 06 now contains market and liquidity indicators
only. VN-Index OHLCV, returns, volatility, drawdown, moving averages, RSI and
volume measures are retrieved from Vnstock. The app uses the last successful
cache or a clearly labelled fallback only when the live request fails.

V4.4 upgrades Financial Impact into a linked three-statement management model.
Users can adjust scenario drivers in the app and immediately compare Base versus
Scenario income statement, balance sheet and cash flow results. Balance-sheet,
cash and retained-earnings roll-forward checks are shown explicitly.

Author: Le Hoang Quan

V4.3 adds a scenario-to-financial-statements engine to the complete V4.2 operating platform.

## V4.3 focus

- 19 consolidated tabs for company operations and management.
- Financial Impact tab translating market and management scenarios into AUM, revenue, PBT, NPAT, cash flow, assets, equity, ROA and ROE.
- Formula-driven scenario assumptions, financial impact model and reconciliation checks in the Master Excel.
- Fund performance, AUM, flows, portfolio and ETF monitoring.
- Market & Liquidity Intelligence with VN-Index level, 1M/3M/YTD returns, volatility, drawdown, 52-week-high gap, regime, MA20/50/200, RSI14, latest volume, 20-day average volume and volume ratio.
- Financial performance, product profitability and distribution economics.
- Business-plan Actual/Budget/Forecast control.
- Enterprise risk, investor-redemption EWS and compliance cockpit.
- Operating KPI, service quality and management decision tracker.
- Advisory Engine, grounded Copilot and PDF/PPTX Board Pack.
- Responsive KPI cards: compact on desktop and two-column mobile grid.

## Data architecture

- Company and operating inputs: `data/DCVFM_Corporate_Performance_Risk_Management_Intelligence_Master_V4_4.xlsx`.
- Live market inputs: authenticated Vnstock routes.
- Failure order: live Vnstock → last successful cache → clearly labelled illustrative fallback.
- The API key is never written to source code, Master Excel, logs or downloads.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For Streamlit Community Cloud, store `VNSTOCK_API_KEY` in App Settings → Secrets. Rows labelled `Assumption` must be replaced or verified before formal management or regulatory use.
