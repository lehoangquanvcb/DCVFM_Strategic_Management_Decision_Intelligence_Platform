from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

CACHE = Path(__file__).resolve().parent / "data_cache"

def _rank(s, higher=True):
    x=pd.to_numeric(s,errors="coerce"); r=x.rank(pct=True)*100
    return r if higher else 100-r

def _demo():
    syms=["FPT","TCB","MBB","ACB","HPG","MWG","VNM","VIC","SSI","VRE","GAS","VCB","CTG","STB","GMD"]
    sectors=["Technology","Banks","Banks","Banks","Materials","Retail","Consumer","Real Estate","Securities","Real Estate","Energy","Banks","Banks","Banks","Logistics"]
    rng=np.random.default_rng(44); n=len(syms)
    return pd.DataFrame({"symbol":syms,"sector":sectors,"close":rng.uniform(20,130,n),"pe":rng.uniform(7,25,n),"pb":rng.uniform(1,4,n),"roe":rng.uniform(.10,.28,n),"revenue_growth":rng.uniform(-.05,.30,n),"profit_growth":rng.uniform(-.10,.40,n),"ret_20d":rng.uniform(-.12,.18,n),"ret_60d":rng.uniform(-.18,.30,n),"volatility":rng.uniform(.18,.48,n),"foreign_flow_score":rng.uniform(20,90,n),"liquidity_score":rng.uniform(45,95,n)})

def load_stock_universe():
    p=CACHE/"silver_stock_snapshot.csv"
    if p.exists():
        try: return pd.read_csv(p),"Vnstock Silver cache"
        except Exception: pass
    return _demo(),"Illustrative demo — run Silver refresh locally"

def score_stocks(df):
    d=df.copy()
    needed=["pe","pb","roe","revenue_growth","profit_growth","ret_20d","ret_60d","volatility","foreign_flow_score","liquidity_score"]
    for c in needed:
        if c not in d: d[c]=np.nan
    f=(_rank(d.roe)+_rank(d.revenue_growth)+_rank(d.profit_growth))/3
    v=(_rank(d.pe,False)+_rank(d.pb,False))/2
    m=(_rank(d.ret_20d)+_rank(d.ret_60d))/2
    flow=pd.to_numeric(d.foreign_flow_score,errors="coerce").fillna(50).clip(0,100)
    risk=(_rank(d.volatility,False)+pd.to_numeric(d.liquidity_score,errors="coerce").fillna(50))/2
    d["Fundamental"]=f.round(1); d["Valuation"]=v.round(1); d["Momentum"]=m.round(1); d["Money_Flow"]=flow.round(1); d["Risk_Liquidity"]=risk.round(1)
    d["DCVFM_Score"]=(.30*f+.20*v+.25*m+.15*flow+.10*risk).round(1)
    d["Signal"]=pd.cut(d.DCVFM_Score,[-1,35,50,65,78,101],labels=["SELL","REDUCE","HOLD","BUY","STRONG BUY"])
    d["Holding_Horizon"]=np.select([(m>=75)&(f<60),(f>=65)&(m>=55),f>=75],["2–6 weeks","3–6 months","6–12 months"],default="1–3 months")
    d["Model_Upside_Pct"]=np.clip(6+(d.DCVFM_Score-50)*.32,4,22).round(1)
    return d.sort_values("DCVFM_Score",ascending=False)

def construct_portfolio(scored, profile="Balanced"):
    cash={"Conservative":30,"Balanced":20,"Growth":12,"Aggressive":7}[profile]
    cap={"Conservative":10,"Balanced":12,"Growth":15,"Aggressive":18}[profile]
    q=scored[scored.Signal.astype(str).isin(["BUY","STRONG BUY"])].head(12).copy()
    if q.empty:return q,cash
    raw=np.maximum(q.DCVFM_Score-50,1); w=raw/raw.sum()*(100-cash); w=np.minimum(w,cap)
    if w.sum()>0:w=w/w.sum()*(100-cash)
    q["Weight_Pct"]=w.round(1)
    return q,cash
