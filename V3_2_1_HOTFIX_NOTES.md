# V3.2.1 Cloud Startup Hotfix

- Keeps the V3.2 vertical left navigation and consolidated 9 functional groups.
- Prevents Streamlit Cloud from attempting Vnstock/Vnstock Sponsor network calls when Sponsor libraries are not installed.
- Uses local/cache/illustrative market fallback immediately in cloud-safe mode.
- Keeps Silver refresh as a local licensed workflow via `refresh_silver_ai.py`.
- Adds startup diagnostics to Cloud logs: Master load, market layer, and render-ready timing.
- Executive BUY/SELL/portfolio remains gated: it is shown only when a non-demo full-factor Silver cache exists.
- Silver flow cache can still be displayed as verified flow intelligence without being mislabeled as a full BUY/SELL recommendation.
