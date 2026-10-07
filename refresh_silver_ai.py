"""DCVFM V3.3 local Silver data pipeline.
Run ONLY in the licensed local Vnstock Silver environment. It writes sanitized caches
for the public Streamlit layer; credentials are never written to cache.
"""
from __future__ import annotations
import json, re, time
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np, pandas as pd
from vnstock_data import Insights, Market, Fundamental, Macro

OUT=Path(__file__).resolve().parent/'data_cache'; OUT.mkdir(exist_ok=True)
NOW=datetime.now().astimezone(); START=(NOW-timedelta(days=420)).date().isoformat(); END=NOW.date().isoformat()
MAX_SYMBOLS=120

def pct(s, high=True):
    x=pd.to_numeric(s,errors='coerce'); return x.rank(pct=True,ascending=high)*100

def prep_flow(df,prefix):
    if df is None or df.empty:return pd.DataFrame(columns=['symbol'])
    d=df.copy(); d.columns=[str(c).lower() for c in d.columns]; d['symbol']=d['symbol'].astype(str).str.upper().str.strip()
    keep=['symbol']+[c for c in ['value_1d','value_10d','value_1m','value_3m','value_6m','volume_1d','volume_10d'] if c in d]
    return d[keep].drop_duplicates('symbol').rename(columns={c:f'{prefix}_{c}' for c in keep if c!='symbol'})

def base_equity(s): return bool(re.fullmatch(r'[A-Z]{3}',str(s or '')))

def std_ohlcv(d):
    if d is None or d.empty:return pd.DataFrame()
    x=d.copy(); x.columns=[str(c).lower() for c in x.columns]
    x=x.rename(columns={'time':'date','tradingdate':'date'})
    if 'date' not in x and isinstance(x.index,pd.DatetimeIndex):x=x.reset_index().rename(columns={x.index.name or 'index':'date'})
    if 'close' not in x:return pd.DataFrame()
    x['date']=pd.to_datetime(x['date'],errors='coerce'); x['close']=pd.to_numeric(x['close'],errors='coerce')
    if 'volume' not in x:x['volume']=np.nan
    x['volume']=pd.to_numeric(x['volume'],errors='coerce')
    return x.dropna(subset=['date','close']).sort_values('date')

def price_features(symbol,mkt):
    try:d=std_ohlcv(mkt.equity(symbol).ohlcv(start=START,end=END,interval='1D'))
    except Exception:return None
    if len(d)<25:return None
    c=d.close; v=d.volume
    ret=lambda n: float(c.iloc[-1]/c.iloc[-min(n+1,len(c))]-1) if len(c)>1 else np.nan
    vol=float(c.pct_change().tail(60).std()*np.sqrt(252))
    adtv=float((c*v).tail(20).mean()) if v.notna().any() else np.nan
    return {'symbol':symbol,'close':float(c.iloc[-1]),'ret_20d':ret(20),'ret_60d':ret(60),'ret_120d':ret(120),'ret_250d':ret(250),'volatility':vol,'adtv_20d':adtv,'price_date':d.date.iloc[-1].date().isoformat()}

def latest_ratio(symbol,fun):
    try:
        eq=fun.equity(symbol) if callable(fun.equity) else None
        d=eq.ratio() if eq is not None else fun.equity.ratio(symbol)
    except Exception:return {}
    if d is None or d.empty:return {}
    x=d.copy(); x.columns=[str(c).lower() for c in x.columns]
    # Long VAS taxonomy: choose latest period then map names/ids conservatively.
    if {'name','value'}.issubset(x.columns):
        if 'period' in x:x=x[x['period'].astype(str)==x['period'].astype(str).max()]
        def find(patterns):
            z=x[x['name'].astype(str).str.lower().apply(lambda s:any(p in s for p in patterns))]
            return pd.to_numeric(z['value'],errors='coerce').dropna().iloc[-1] if not z.empty and pd.to_numeric(z['value'],errors='coerce').notna().any() else np.nan
        return {'pe':find(['p/e','pe ']),'pb':find(['p/b','pb ']),'roe':find(['roe','lợi nhuận trên vốn chủ'])}
    # Wide schema fallback.
    row=x.iloc[-1]; out={}
    aliases={'pe':['pe','price_to_earning'],'pb':['pb','price_to_book'],'roe':['roe']}
    for k,opts in aliases.items():
        for c in opts:
            if c in x.columns: out[k]=pd.to_numeric(pd.Series([row[c]]),errors='coerce').iloc[0]; break
    return out

def save_macro():
    mac=Macro(); frames=[]
    calls=[('GDP',lambda:mac.economy().gdp(period='quarter',length=12)),('CPI',lambda:mac.economy().cpi(period='month',length=24)),('Credit',lambda:mac.economy().credit(period='month',length=24)),('Money Supply',lambda:mac.economy().money_supply(period='month',length=24)),('FX',lambda:mac.currency().exchange_rate(period='day',length=90)),('Interest Rate',lambda:mac.currency().interest_rate(period='day',length=90,format='long'))]
    for label,fn in calls:
        try:
            d=fn()
            if d is not None and not d.empty:
                z=d.reset_index().copy(); z['indicator_group']=label; frames.append(z)
                print('  macro',label,len(z))
        except Exception as e: print('  macro unavailable',label,type(e).__name__)
    if frames: pd.concat(frames,ignore_index=True,sort=False).to_csv(OUT/'silver_macro_snapshot.csv',index=False,encoding='utf-8-sig')

print('DCVFM V3.3 — refreshing Vnstock Silver caches')
i=Insights(); mkt=Market(); fun=Fundamental()
foreign=prep_flow(i.flow.foreign(exchange='HOSE',group_by='stock'),'foreign'); prop=prep_flow(i.flow.proprietary(exchange='HOSE',group_by='stock'),'proprietary')
try:active=prep_flow(i.flow.active(exchange='HOSE',group_by='stock'),'active')
except Exception:active=pd.DataFrame(columns=['symbol'])
flow=foreign.merge(prop,on='symbol',how='outer').merge(active,on='symbol',how='outer'); flow=flow[flow.symbol.map(base_equity)].copy()
for p in ['foreign','proprietary','active']:
    parts=[]
    for c,w in [(f'{p}_value_1d',.20),(f'{p}_value_10d',.35),(f'{p}_value_1m',.45)]:
        if c in flow:parts.append((pct(flow[c]),w))
    if parts:flow[f'{p}_flow_score']=sum(s*w for s,w in parts)/sum(w for _,w in parts)
sc=[c for c in ['foreign_flow_score','proprietary_flow_score','active_flow_score'] if c in flow]
flow['money_flow_score']=flow[sc].mean(axis=1) if sc else 50
flow['refresh_timestamp']=NOW.isoformat(timespec='seconds'); flow['source']='VNSTOCK_SILVER'
flow.sort_values('money_flow_score',ascending=False).to_csv(OUT/'silver_flow_snapshot.csv',index=False,encoding='utf-8-sig')

# Screener enriches sector + fundamental/valuation when endpoint is available.
try:
    scr=i.screener.filter(limit=2000); scr.columns=[str(c).lower() for c in scr.columns]
    if 'ticker' in scr and 'symbol' not in scr:scr=scr.rename(columns={'ticker':'symbol'})
    if 'symbol' in scr:scr['symbol']=scr.symbol.astype(str).str.upper().str.strip()
    print('Screener rows:',len(scr))
except Exception as e: print('Screener unavailable:',type(e).__name__); scr=pd.DataFrame()

# Investable universe: strongest combined absolute flows first; never call hundreds of fundamentals blindly.
flow['_absflow']=0.0
for c in ['foreign_value_1m','proprietary_value_1m','active_value_1m']:
    if c in flow:flow['_absflow']+=pd.to_numeric(flow[c],errors='coerce').abs().fillna(0)
universe=flow.sort_values('_absflow',ascending=False).symbol.head(MAX_SYMBOLS).tolist()
rows=[]
for n,s in enumerate(universe,1):
    pf=price_features(s,mkt)
    if pf:
        pf.update({'foreign_flow_score':float(flow.loc[flow.symbol==s,'foreign_flow_score'].iloc[0]) if 'foreign_flow_score' in flow else 50,'proprietary_flow_score':float(flow.loc[flow.symbol==s,'proprietary_flow_score'].iloc[0]) if 'proprietary_flow_score' in flow else 50,'money_flow_score':float(flow.loc[flow.symbol==s,'money_flow_score'].iloc[0])})
        if not scr.empty and 'symbol' in scr:
            q=scr[scr.symbol==s]
            if not q.empty:
                r=q.iloc[0]
                for c in ['sector','sector_lv1','pe','pb','roe','revenue_growth','npatmi_growth','adtv','avg_volume']:
                    if c in q.columns:pf[c]=r[c]
                if 'npatmi_growth' in pf:pf['profit_growth']=pf['npatmi_growth']
        if not all(k in pf and pd.notna(pf[k]) for k in ['pe','pb','roe']):pf.update({k:v for k,v in latest_ratio(s,fun).items() if k not in pf or pd.isna(pf[k])})
        rows.append(pf)
    if n%20==0:print('  prices/factors',n,'/',len(universe))

stocks=pd.DataFrame(rows)
if not stocks.empty:
    if 'sector' not in stocks:stocks['sector']=stocks.get('sector_lv1','Unknown')
    stocks['sector']=stocks['sector'].fillna(stocks.get('sector_lv1','Unknown')).fillna('Unknown')
    stocks['liquidity_score']=pct(stocks['adtv_20d']).fillna(50)
    for c in ['pe','pb','roe','revenue_growth','profit_growth']:stocks[c]=pd.to_numeric(stocks.get(c,np.nan),errors='coerce')
    stocks['data_timestamp']=stocks['price_date']; stocks['refresh_timestamp']=NOW.isoformat(timespec='seconds'); stocks['source']='VNSTOCK_SILVER'
    stocks.to_csv(OUT/'silver_stock_snapshot.csv',index=False,encoding='utf-8-sig')
    # sector cache from investable universe
    sec=stocks.groupby('sector',as_index=False).agg(stocks=('symbol','count'),ret_20d=('ret_20d','mean'),ret_60d=('ret_60d','mean'),money_flow_score=('money_flow_score','mean'),liquidity_score=('liquidity_score','mean'))
    sec['sector_score']=(pct(sec.ret_60d)*.45+pct(sec.money_flow_score)*.35+pct(sec.liquidity_score)*.20).round(1); sec.sort_values('sector_score',ascending=False).to_csv(OUT/'silver_sector_snapshot.csv',index=False,encoding='utf-8-sig')

# Index history for cloud market regime.
try:
    idx=std_ohlcv(mkt.index('VNINDEX').ohlcv(start=START,end=END,interval='1D')); idx.to_csv(OUT/'VNINDEX_ohlcv.csv',index=False,encoding='utf-8-sig')
except Exception as e:print('VNINDEX cache unavailable:',type(e).__name__)
save_macro()
meta={'source':'VNSTOCK_SILVER','refresh_timestamp':NOW.isoformat(timespec='seconds'),'stock_rows':int(len(stocks)),'flow_rows':int(len(flow)),'full_factor_ready':bool(len(stocks)>=20 and {'pe','pb','roe','ret_20d','ret_60d','liquidity_score','money_flow_score'}.issubset(stocks.columns)),'score_version':'DCVFM-V3.3','note':'Sanitized local Silver cache; public cloud performs no Sponsor authentication.'}
(OUT/'silver_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print('Saved caches to',OUT); print(json.dumps(meta,ensure_ascii=False,indent=2))
