from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
import re

import numpy as np
import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent / ".cache" / "market"


def _standardize(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy(); df.columns = [str(c).strip().lower() for c in df.columns]
    aliases = {"time":"date", "tradingdate":"date", "indexvalue":"close", "value":"close"}
    df = df.rename(columns={k:v for k,v in aliases.items() if k in df.columns})
    if "date" not in df.columns:
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index().rename(columns={df.index.name or "index":"date"})
        else: raise ValueError("Market response has no date column")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for c in ["open","high","low","close","volume"]:
        if c in df: df[c] = pd.to_numeric(df[c], errors="coerce")
    if "close" not in df: raise ValueError("Market response has no close column")
    for c in ["open","high","low"]:
        if c not in df: df[c] = df["close"]
    if "volume" not in df: df["volume"] = np.nan
    return df[["date","open","high","low","close","volume"]].dropna(subset=["date","close"]).sort_values("date")


def _vnstock(symbol: str, start: str, end: str, source: str) -> tuple[pd.DataFrame,str]:
    errors=[]
    # Sponsor/Unified UI route.
    try:
        from vnstock import Market
        return _standardize(Market().index(symbol).ohlcv(start=start,end=end,interval="1D")), "Vnstock Market / Unified UI"
    except Exception as exc: errors.append(f"Market:{type(exc).__name__}")
    try:
        from vnstock_data import Market
        return _standardize(Market().index(symbol).ohlcv(start=start,end=end,interval="1D")), "Vnstock Market / vnstock_data"
    except Exception as exc: errors.append(f"vnstock_data:{type(exc).__name__}")
    # Current Quote API: KBS first, then the configured source and VCI.
    for provider in list(dict.fromkeys(["KBS", source.upper(), "VCI"])):
        try:
            from vnstock import Quote
            quote=Quote(source=provider,symbol=symbol)
            try: raw=quote.history(start=start,end=end,interval="1D")
            except TypeError: raw=quote.history(start_date=start,end_date=end)
            return _standardize(raw), f"Vnstock Quote / {provider}"
        except Exception as exc: errors.append(f"Quote-{provider}:{type(exc).__name__}")
    # Backward-compatible route.
    try:
        from vnstock import Vnstock
        raw=Vnstock().stock(symbol=symbol,source=source).quote.history(start=start,end=end,interval="1D")
        return _standardize(raw), f"Vnstock legacy / {source}"
    except Exception as exc: errors.append(f"Legacy:{type(exc).__name__}")
    raise RuntimeError(" | ".join(errors))


def _cache_path(symbol: str) -> Path:
    safe=re.sub(r"[^A-Za-z0-9_-]","_",symbol.upper())
    return CACHE_DIR / f"{safe}_ohlcv.csv"


def _save_cache(symbol: str, df: pd.DataFrame):
    try:
        CACHE_DIR.mkdir(parents=True,exist_ok=True)
        df.to_csv(_cache_path(symbol),index=False)
    except Exception:
        pass


def _load_cache(symbol: str, start: str, end: str) -> pd.DataFrame | None:
    path=_cache_path(symbol)
    if not path.exists(): return None
    try:
        df=_standardize(pd.read_csv(path)); mask=(df["date"]>=pd.Timestamp(start))&(df["date"]<=pd.Timestamp(end)); df=df.loc[mask]
        return df if len(df)>=5 else None
    except Exception: return None


def _fallback(symbol: str,start: str,end: str,base: float) -> pd.DataFrame:
    dates=pd.bdate_range(start=start,end=end); seed=int(hashlib.sha256(f"{symbol}-{start}-{end}".encode()).hexdigest()[:8],16); rng=np.random.default_rng(seed)
    returns=rng.normal(0.00025,0.011,len(dates)); close=base*np.exp(np.cumsum(returns)); open_=close*(1+rng.normal(0,0.003,len(dates))); high=np.maximum(open_,close)*(1+rng.uniform(0.001,0.009,len(dates))); low=np.minimum(open_,close)*(1-rng.uniform(0.001,0.009,len(dates))); volume=rng.integers(350_000_000,1_200_000_000,len(dates))
    return pd.DataFrame({"date":dates,"open":open_,"high":high,"low":low,"close":close,"volume":volume})


def get_market_data(symbol="VNINDEX",start="2025-01-01",end=None,source="KBS",fallback=True,base=1265.0):
    end=end or date.today().isoformat(); start=str(start)[:10]; end=str(end)[:10]
    try:
        frame,label=_vnstock(symbol,start,end,source)
        if len(frame)<5: raise ValueError("Insufficient observations")
        _save_cache(symbol,frame)
        return frame,label,None
    except Exception as exc:
        cached=_load_cache(symbol,start,end)
        if cached is not None: return cached,"Last successful Vnstock cache",str(exc)
        if not fallback: raise
        return _fallback(symbol,start,end,float(base)),"Offline illustrative fallback",str(exc)


def market_metrics(df: pd.DataFrame) -> dict:
    close=df["close"].dropna(); ret=close.pct_change().dropna(); periods=min(63,len(close)-1)
    return {"level":float(close.iloc[-1]),"return_1m":float(close.iloc[-1]/close.iloc[max(0,len(close)-22)]-1),"return_3m":float(close.iloc[-1]/close.iloc[-1-periods]-1) if periods else 0.0,"volatility":float(ret.std()*np.sqrt(252)) if len(ret) else 0.0,"drawdown":float(close.iloc[-1]/close.cummax().iloc[-1]-1)}


def market_regime(metrics: dict) -> str:
    if metrics["drawdown"]<=-0.12 or metrics["return_3m"]<=-0.08:return "STRESS"
    if metrics["return_3m"]>=0.08 and metrics["drawdown"]>-0.05:return "RISK-ON"
    if metrics["return_3m"]<0:return "RISK-OFF"
    return "NEUTRAL"
