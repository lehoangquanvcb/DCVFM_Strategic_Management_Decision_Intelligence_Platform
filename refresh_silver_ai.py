"""V3.1 local Silver/AI bootstrap. Never prints or stores VNSTOCK_API_KEY."""
import importlib, json
from pathlib import Path
OUT=Path(__file__).resolve().parent/"data_cache"; OUT.mkdir(exist_ok=True)
mods={}
for name in ("vnstock","vnai","vnstock_data","vnstock_ta","vnstock_news"):
    try:
        m=importlib.import_module(name); mods[name]=getattr(m,"__version__","installed")
    except Exception as e: mods[name]="NOT AVAILABLE: "+type(e).__name__
print(json.dumps(mods,ensure_ascii=False,indent=2))
if str(mods["vnstock_data"]).startswith("NOT AVAILABLE"):
    raise SystemExit("Activate the licensed Vnstock Silver Python 3.12 environment first.")
from vnstock_data import Market, Reference, Fundamental, Insights
print("Silver core imports OK")
print("Cache target:",OUT/"silver_stock_snapshot.csv")
print("Use current Vnstock Agent Guide/Skills for installed-version screener, fundamental, macro and indicator calls.")
