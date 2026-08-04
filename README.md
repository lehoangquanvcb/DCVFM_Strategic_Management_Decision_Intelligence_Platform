# DCVFM Corporate Performance, Risk & Management Intelligence Platform V4.2

Author: Le Hoang Quan

V4.2 is an operating and management platform for DCVFM. It combines controlled company inputs from one Master Excel with authenticated Vnstock market data, analytics, risk monitoring, management recommendations and decision tracking.

## V4.2 focus

- 18 consolidated tabs for company operations and management.
- Fund performance, AUM, flows, portfolio and ETF monitoring.
- Upgraded Market, Liquidity & Macro Intelligence with VN-Index level, 1M/3M/YTD returns, volatility, drawdown, 52-week-high gap, regime, MA20/50/200, volume and macro pulse.
- Financial performance, product profitability and distribution economics.
- Business-plan Actual/Budget/Forecast control.
- Enterprise risk, investor-redemption EWS and compliance cockpit.
- Operating KPI, service quality and management decision tracker.
- Advisory Engine, grounded Copilot and PDF/PPTX Board Pack.
- Responsive KPI cards: compact on desktop and two-column mobile grid.

## Data architecture

- Company and operating inputs: `data/DCVFM_Corporate_Performance_Risk_Management_Intelligence_Master_V4_2.xlsx`.
- Live market inputs: authenticated Vnstock routes.
- Failure order: live Vnstock → last successful cache → clearly labelled illustrative fallback.
- The API key is never written to source code, Master Excel, logs or downloads.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For Streamlit Community Cloud, store `VNSTOCK_API_KEY` in App Settings → Secrets. Rows labelled `Assumption` must be replaced or verified before formal management or regulatory use.
