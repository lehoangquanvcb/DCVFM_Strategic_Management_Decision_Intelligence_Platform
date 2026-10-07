# DCVFM V3.3 — Macro-to-Portfolio Silver Decision Flow

## New decision sequence
1. Macro Intelligence
2. Sector Intelligence
3. Market Overview
4. Recommended BUY
5. REDUCE & SELL
6. Recommended Portfolio
7. Current Fund Portfolio
8. Current vs Recommended Portfolio
9. Fund & Business Intelligence
10. Risk, Governance & Advisory

## Silver architecture
Run `python refresh_silver_ai.py` only in the licensed local Silver environment. The script creates sanitized caches in `data_cache/` for Streamlit Cloud. It uses current Unified UI patterns including `Market().equity(symbol).ohlcv(...)`, `Market().index('VNINDEX').ohlcv(...)`, `Macro().economy()/currency()`, `Insights()` and `Fundamental()` with compatibility handling for the installed Sponsor build.

Generated caches include stock factors/prices, money flow, sectors, macro observations, VN-Index history and metadata. Cloud does not authenticate Sponsor credentials.

## Portfolio comparison
V3.3 compares the selected fund's latest holdings with the Balanced recommended portfolio over approximately 1M/3M/6M/12M (20/60/120/250 trading days). The comparison uses today's holdings/weights against common historical stock returns. It is an ex-post holdings diagnostic, not a historical walk-forward strategy backtest. Coverage is displayed because not every current holding may exist in the Silver investable universe.

## Production guardrail
If the real `silver_stock_snapshot.csv` is absent, BUY/SELL/recommended portfolio/comparison are withheld. Demo rows are never promoted to production recommendations.
