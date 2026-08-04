# DCVFM Strategic Management & Decision Intelligence Platform V4

Author: Le Hoang Quan

V4 inherits the complete V3.1 foundation—Master Excel ingestion, secure Vnstock Sponsor authentication, KBS/VCI routing, live/cache/fallback controls, fund analytics, M&A forensics, data quality, Board Packs and grounded Copilot.

## New V4 closed-loop management layer

- Product profitability and break-even AUM.
- Distribution channel economics and concentration.
- Investor cohort/redemption early-warning signals.
- Regulatory and compliance control cockpit.
- Product strategy screening.
- Actual/Budget/Forecast business-plan control.
- Valuation and deal-structuring scenarios.
- Decision and recommendation tracker.

The application has 20 consolidated tabs and the Master contains at least 38 sheets. New internal/company data is loaded only from Master Excel; Vnstock supplies market data.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If Vnstock has already been registered locally, the app will detect that identity. On a fresh machine, set `VNSTOCK_API_KEY` as an environment variable. For Streamlit Cloud, store it in App Settings → Secrets. Never paste a real key into source code or Master Excel.

## Evidence discipline

Rows labelled `Assumption`, `Working hypothesis` or `Analytical hypothesis` must be replaced or verified before formal use. M&A, redemption-risk and compliance scores are monitoring signals—not transaction probabilities, legal conclusions or allegations. Valuation scenarios are not an offer or fairness opinion.
