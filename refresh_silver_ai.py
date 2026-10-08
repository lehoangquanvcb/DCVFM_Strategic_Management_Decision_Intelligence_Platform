"""DCVFM V3.3 local Silver data pipeline.
Run ONLY in the licensed local Vnstock Silver environment. It writes sanitized caches
for the public Streamlit layer; credentials are never written to cache.
"""
from __future__ import annotations
import json, re, time, sys, argparse
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np, pandas as pd
from vnstock_data import Insights, Market, Fundamental, Macro

OUT=Path(__file__).resolve().parent/'data_cache'; OUT.mkdir(exist_ok=True)
NOW=datetime.now().astimezone(); START=(NOW-timedelta(days=420)).date().isoformat(); END=NOW.date().isoformat()
# --max-symbols 0 selects every eligible HOSE flow symbol (potentially hundreds of API calls).
PARSER=argparse.ArgumentParser(add_help=True)
PARSER.add_argument('--repair-cache',action='store_true')
PARSER.add_argument('--enrich-growth',action='store_true')
PARSER.add_argument('--max-symbols',type=int,default=120,help='0 = all available eligible symbols; default 120 for backwards compatibility')
PARSER.add_argument('--sector-file',default='',help='Optional verified CSV with symbol,sector,source,as_of_date')
PARSER.add_argument('--exchanges',default='HOSE,HNX,UPCOM',help='Comma-separated exchange flow requests; unsupported exchanges are skipped')
PARSER.add_argument('--universe-file',default='',help='Optional verified listing CSV: symbol,exchange,sector,source,as_of_date')
ARGS=PARSER.parse_args()
if ARGS.max_symbols < 0: PARSER.error('--max-symbols must be >= 0')
MAX_SYMBOLS=ARGS.max_symbols
EXCHANGES=[x.strip().upper() for x in ARGS.exchanges.split(',') if x.strip()]
if not EXCHANGES or any(x not in {'HOSE','HNX','UPCOM'} for x in EXCHANGES):PARSER.error('exchanges must be HOSE,HNX,UPCOM')

def pct(s, high=True):
    x=pd.to_numeric(s.astype(str).str.replace(',', '', regex=False),errors='coerce'); return x.rank(pct=True,ascending=high)*100

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

def score_flow_table(flow):
    """Score only populated windows; do not let an all-NaN 1M term poison 1D/10D."""
    flow=flow.copy()
    for p in ['foreign','proprietary','active']:
        parts=[]
        for suffix,w in [('1d',.40),('10d',.60)]:
            c=f'{p}_value_{suffix}'
            if c in flow:
                numeric=pd.to_numeric(flow[c],errors='coerce')
                if numeric.notna().any():
                    parts.append((pct(numeric),w))
        if parts:
            numerator=sum(series.fillna(0)*w for series,w in parts)
            denominator=sum(series.notna().astype(float)*w for series,w in parts)
            flow[f'{p}_flow_score']=(numerator/denominator.replace(0,np.nan)).round(2)
    cols=[c for c in ['foreign_flow_score','proprietary_flow_score'] if c in flow]
    flow['money_flow_score']=flow[cols].mean(axis=1).round(2) if cols else np.nan
    return flow

def apply_verified_sector_mapping(stocks):
    """Only a user-verified symbol/sector mapping may fill Unknown sectors."""
    mapping_path=Path(ARGS.sector_file) if ARGS.sector_file else (Path(ARGS.universe_file) if ARGS.universe_file else OUT.parent/'sector_mapping.csv')
    if not mapping_path.exists():
        print('SECTOR: verified sector_mapping.csv absent; Unknown retained')
        return stocks
    mapping=pd.read_csv(mapping_path,encoding='utf-8-sig',dtype=str)
    mapping.columns=mapping.columns.str.lower().str.strip()
    if not {'symbol','sector'}.issubset(mapping.columns):
        print('SECTOR: mapping requires symbol,sector columns; skipped')
        return stocks
    mapping['symbol']=mapping['symbol'].str.upper().str.strip()
    mapping['sector']=mapping['sector'].str.strip()
    mapping=mapping.dropna(subset=['symbol','sector'])
    mapping=mapping[(mapping['sector']!='') & (mapping['sector'].str.lower()!='unknown')]
    duplicates=mapping.groupby('symbol')['sector'].nunique()
    bad=set(duplicates[duplicates>1].index)
    if bad: print('SECTOR: conflicting labels excluded for',len(bad),'symbols')
    mapping=mapping[~mapping.symbol.isin(bad)].drop_duplicates('symbol')
    lookup=mapping.set_index('symbol')['sector']
    stocks=stocks.copy()
    if 'sector' not in stocks:stocks['sector']='Unknown'
    missing=stocks['sector'].isna() | stocks['sector'].astype(str).str.strip().str.lower().isin(['unknown','','nan','none'])
    stocks.loc[missing,'sector']=stocks.loc[missing,'symbol'].map(lookup).fillna('Unknown')
    print('SECTOR: mapped',int((stocks.sector!='Unknown').sum()),'/',len(stocks))
    return stocks

def _growth_from_income(df):
    """Quarterly YoY from Silver long-format taxonomy; no ambiguous cumulative comparisons."""
    if not isinstance(df,pd.DataFrame) or df.empty:return {}
    d=df.copy(); d.columns=[str(c).lower().strip() for c in d.columns]
    if not {'period','id','value'}.issubset(d.columns):return {}
    d['period']=d['period'].astype(str).str.upper().str.strip()
    d['id']=d['id'].astype(str).str.upper().str.strip()
    d['value']=pd.to_numeric(d['value'],errors='coerce')
    d=d[d['period'].str.fullmatch(r'\d{4}-Q[1-4]')].dropna(subset=['value'])
    if d.empty:return {}
    targets={'revenue_growth':['IS_NET_REVENUE'],
             'profit_growth':['IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY','IS_NET_PROFIT_AFTER_TAX']}
    out={}
    for target,ids in targets.items():
        for metric in ids:
            x=d[d['id'].eq(metric)].copy()
            if x.empty or x['period'].duplicated().any():continue
            x=x.set_index('period')['value']
            periods=sorted(x.index,reverse=True)
            for period in periods:
                year=int(period[:4]); prior=f'{year-1}{period[4:]}'
                if prior not in x.index:continue
                old=float(x.loc[prior]); current=float(x.loc[period])
                if not np.isfinite(old) or not np.isfinite(current) or old<=0:continue
                # Quarterly data must be standalone quarterly values, not YTD accumulations.
                # Confirm report basis with issuer before using in investment decisions.
                out[target]=round(current/old-1,6)
                break
            if target in out:break
    return out

def enrich_growth_from_silver(stocks):
    """Opt-in licensed calls; leave unsupported/ambiguous financial statements as NaN."""
    f=Fundamental(); stocks=stocks.copy()
    for c in ['revenue_growth','profit_growth']:
        if c not in stocks:stocks[c]=np.nan
    for n,sym in enumerate(stocks.symbol,1):
        try:
            eq=f.equity(sym) if callable(f.equity) else f.equity
            d=eq.income_statement() if callable(f.equity) else eq.income_statement(sym)
            growth=_growth_from_income(d)
            for col,val in growth.items():
                if pd.isna(stocks.loc[stocks.symbol==sym,col]).all():stocks.loc[stocks.symbol==sym,col]=val
        except Exception as exc:
            if n<=3:print('GROWTH:',sym,type(exc).__name__)
        if n%20==0:print('  growth checked',n,'/',len(stocks))
    return stocks

def sector_snapshot(stocks):
    valid=stocks[stocks.sector.notna() & stocks.sector.astype(str).str.strip().ne('Unknown')].copy()
    columns=['sector','stocks','ret_20d','ret_60d','money_flow_score','liquidity_score','sector_score']
    if valid.empty:return pd.DataFrame(columns=columns)
    out=valid.groupby('sector',as_index=False).agg(stocks=('symbol','count'),ret_20d=('ret_20d','mean'),ret_60d=('ret_60d','mean'),money_flow_score=('money_flow_score','mean'),liquidity_score=('liquidity_score','mean'))
    out['sector_score']=(pct(out.ret_60d)*.45+pct(out.money_flow_score)*.35+pct(out.liquidity_score)*.20).round(1)
    return out.sort_values('sector_score',ascending=False)

def repair_existing_cache():
    fp=OUT/'silver_flow_snapshot.csv'; sp=OUT/'silver_stock_snapshot.csv'
    if not fp.exists() or not sp.exists():
        raise SystemExit('Missing flow/stock cache. Run full refresh first.')
    flow=pd.read_csv(fp,encoding='utf-8-sig'); stocks=pd.read_csv(sp,encoding='utf-8-sig')
    for df in (flow,stocks):df['symbol']=df['symbol'].astype(str).str.upper().str.strip()
    flow=score_flow_table(flow)
    cols=['foreign_flow_score','proprietary_flow_score','money_flow_score']
    stocks=stocks.drop(columns=cols,errors='ignore').merge(flow[['symbol']+cols].drop_duplicates('symbol'),on='symbol',how='left',validate='one_to_one')
    flow.to_csv(fp,index=False,encoding='utf-8-sig'); stocks.to_csv(sp,index=False,encoding='utf-8-sig')
    stocks=apply_verified_sector_mapping(stocks)
    if ARGS.enrich_growth:stocks=enrich_growth_from_silver(stocks)
    stocks.to_csv(sp,index=False,encoding='utf-8-sig')
    sector_snapshot(stocks).to_csv(OUT/'silver_sector_snapshot.csv',index=False,encoding='utf-8-sig')
    fields=['sector','pe','pb','roe','ret_20d','ret_60d','liquidity_score','money_flow_score','revenue_growth','profit_growth']
    coverage={c:round(float(stocks[c].notna().mean()),3) if c in stocks and len(stocks) else 0 for c in fields}
    coverage['sector']=round(float((stocks['sector'].notna() & stocks['sector'].ne('Unknown')).mean()),3) if 'sector' in stocks and len(stocks) else 0
    ready=bool(len(stocks)>=20 and all(coverage[c]>=.8 for c in fields))
    meta={'source':'VNSTOCK_SILVER','refresh_timestamp':NOW.isoformat(timespec='seconds'),'stock_rows':len(stocks),'flow_rows':len(flow),'coverage':coverage,'full_factor_ready':ready,'universe_scope':'Verified flow endpoints and optional listing CSV','universe_limit':MAX_SYMBOLS,'requested_exchanges':EXCHANGES,'score_version':'DCVFM-V3.3.6','note':'Verified sector mapping; quarterly YoY long-format income extraction (verify standalone quarter basis); missing values remain missing.'}
    (OUT/'silver_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FLOW REPAIR:',{c:round(float(stocks[c].notna().mean()),3) for c in cols})
    print('DATA QUALITY:',coverage,'READY:',ready)
    print('Saved repaired caches to',OUT)

if ARGS.repair_cache:
    repair_existing_cache()
    sys.exit(0)

print('DCVFM V3.3 — refreshing Vnstock Silver caches')
i=Insights(); mkt=Market(); fun=Fundamental()
frames=[]; successful_exchanges=[]
for exchange in EXCHANGES:
    try:
        foreign=prep_flow(i.flow.foreign(exchange=exchange,group_by='stock'),'foreign')
        prop=prep_flow(i.flow.proprietary(exchange=exchange,group_by='stock'),'proprietary')
        try:active=prep_flow(i.flow.active(exchange=exchange,group_by='stock'),'active')
        except Exception:active=pd.DataFrame(columns=['symbol'])
        one=foreign.merge(prop,on='symbol',how='outer').merge(active,on='symbol',how='outer')
        one=one[one.symbol.map(base_equity)].copy()
        if one.empty:
            print('EXCHANGE:',exchange,'no eligible symbols returned');continue
        one['exchange']=exchange;frames.append(one);successful_exchanges.append(exchange)
        print('EXCHANGE:',exchange,'eligible symbols',len(one))
    except Exception as exc:print('EXCHANGE:',exchange,'unavailable',type(exc).__name__)
if not frames:raise SystemExit('No supported exchange flow data returned; existing cache untouched')
flow=pd.concat(frames,ignore_index=True).drop_duplicates('symbol',keep='first')
listing=pd.DataFrame()
if ARGS.universe_file:
    listing=pd.read_csv(ARGS.universe_file,encoding='utf-8-sig',dtype=str)
    listing.columns=listing.columns.str.lower().str.strip()
    if not {'symbol','exchange','source','as_of_date'}.issubset(listing.columns):
        raise SystemExit('Universe file requires symbol,exchange,source,as_of_date')
    listing['symbol']=listing.symbol.str.upper().str.strip()
    listing['exchange']=listing.exchange.str.upper().str.strip()
    listing=listing[listing.symbol.map(base_equity)&listing.exchange.isin(EXCHANGES)].drop_duplicates('symbol')
    print('UNIVERSE FILE: verified listing rows',len(listing))
flow=score_flow_table(flow)
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
for c in ['foreign_value_10d','proprietary_value_10d','foreign_value_1d','proprietary_value_1d']:
    if c in flow:flow['_absflow']+=pd.to_numeric(flow[c],errors='coerce').abs().fillna(0)
ranked=flow.sort_values('_absflow',ascending=False).symbol.tolist()
if not listing.empty:
    ranked=list(dict.fromkeys(ranked+listing.symbol.tolist()))
universe=ranked[:MAX_SYMBOLS] if MAX_SYMBOLS else ranked
print('UNIVERSE: flow symbols',len(flow),'verified listing extras',max(0,len(universe)-len(flow)),'selected',len(universe),'max_symbols',MAX_SYMBOLS)
rows=[]
for n,s in enumerate(universe,1):
    pf=price_features(s,mkt)
    if pf:
        matched=flow.loc[flow.symbol==s]
        pf['exchange']=matched.exchange.iloc[0] if not matched.empty else (listing.loc[listing.symbol==s,'exchange'].iloc[0] if not listing.empty and s in set(listing.symbol) else 'Unknown')
        for score in ['foreign_flow_score','proprietary_flow_score','money_flow_score']:
            pf[score]=matched[score].iloc[0] if not matched.empty and score in matched else np.nan
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
    stocks['sector']=stocks['sector'].fillna(stocks['sector_lv1'] if 'sector_lv1' in stocks else 'Unknown').replace(['', 'nan', 'None'],np.nan).fillna('Unknown')
    stocks=apply_verified_sector_mapping(stocks)
    if ARGS.enrich_growth:stocks=enrich_growth_from_silver(stocks)
    stocks['liquidity_score']=pct(stocks['adtv_20d'])
    for c in ['pe','pb','roe','revenue_growth','profit_growth']:stocks[c]=pd.to_numeric(stocks.get(c,np.nan),errors='coerce')
    stocks['data_timestamp']=stocks['price_date']; stocks['refresh_timestamp']=NOW.isoformat(timespec='seconds'); stocks['source']='VNSTOCK_SILVER'
    # Reconcile flow scores by normalized ticker, independent of API result ordering.
    score_cols=[c for c in ['foreign_flow_score','proprietary_flow_score','active_flow_score','money_flow_score'] if c in flow.columns]
    stocks=stocks.drop(columns=score_cols,errors='ignore').merge(flow[['symbol']+score_cols].drop_duplicates('symbol'),on='symbol',how='left',validate='one_to_one')
    stocks.to_csv(OUT/'silver_stock_snapshot.csv',index=False,encoding='utf-8-sig')
    sector_snapshot(stocks).to_csv(OUT/'silver_sector_snapshot.csv',index=False,encoding='utf-8-sig')

# Index history for cloud market regime.
try:
    idx=std_ohlcv(mkt.index('VNINDEX').ohlcv(start=START,end=END,interval='1D')); idx.to_csv(OUT/'VNINDEX_ohlcv.csv',index=False,encoding='utf-8-sig')
except Exception as e:print('VNINDEX cache unavailable:',type(e).__name__)
save_macro()
coverage={c:round(float(stocks[c].notna().mean()),3) if c in stocks and len(stocks) else 0.0 for c in ['sector','pe','pb','roe','ret_20d','ret_60d','liquidity_score','money_flow_score','revenue_growth','profit_growth']}
coverage['sector']=round(float((stocks['sector'].notna() & stocks['sector'].ne('Unknown')).mean()),3) if len(stocks) else 0.0
ready=bool(len(stocks)>=20 and all(coverage.get(c,0)>=0.8 for c in ['sector','pe','pb','roe','ret_20d','ret_60d','liquidity_score','money_flow_score','revenue_growth','profit_growth']))
meta={'coverage':coverage,'source':'VNSTOCK_SILVER','refresh_timestamp':NOW.isoformat(timespec='seconds'),'stock_rows':int(len(stocks)),'flow_rows':int(len(flow)),'full_factor_ready':ready,'universe_scope':'Verified flow endpoints and optional listing CSV','universe_limit':MAX_SYMBOLS,'requested_exchanges':EXCHANGES,'score_version':'DCVFM-V3.3.6','note':'Sanitized local Silver cache; public cloud performs no Sponsor authentication.'}
(OUT/'silver_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print('DATA QUALITY:',coverage,'READY:',ready); print('Saved caches to',OUT); print(json.dumps(meta,ensure_ascii=False,indent=2))
