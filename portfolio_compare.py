from __future__ import annotations
import numpy as np, pandas as pd

def current_portfolio(data,fund_code):
    p=data['Portfolio'].copy(); p=p[p.Fund_Code.astype(str)==str(fund_code)]
    if p.empty:return p
    latest=pd.to_datetime(p.Date).max(); p=p[pd.to_datetime(p.Date)==latest].copy()
    p['Weight_Pct']=pd.to_numeric(p.Weight_Pct,errors='coerce').fillna(0)
    return p

def compare_portfolios(data,fund_code,scored,recommended):
    cur=current_portfolio(data,fund_code)
    if cur.empty or scored.empty:return pd.DataFrame(),pd.DataFrame()
    retcols=[('1M','ret_20d'),('3M','ret_60d'),('6M','ret_120d'),('12M','ret_250d')]
    px=scored.set_index('symbol')
    def calc(items,symcol,wcol):
        out={}; coverage={}
        for label,col in retcols:
            if col not in px:out[label]=np.nan; coverage[label]=0; continue
            z=items[[symcol,wcol]].copy(); z[symcol]=z[symcol].astype(str).str.upper(); z['ret']=z[symcol].map(px[col]); z=z.dropna(subset=['ret']); total=pd.to_numeric(z[wcol],errors='coerce').sum()
            out[label]=float((z.ret*pd.to_numeric(z[wcol],errors='coerce')).sum()/total) if total>0 else np.nan
            coverage[label]=float(total)
        return out,coverage
    cr,cc=calc(cur,'Ticker','Weight_Pct')
    rr,rc=calc(recommended,'symbol','Weight_Pct') if not recommended.empty else ({k:np.nan for k,_ in retcols},{k:0 for k,_ in retcols})
    rows=[]
    for label,_ in retcols:rows.append({'Horizon':label,'Current_Fund_Return':cr[label],'Recommended_Return':rr[label],'Excess_Recommended':rr[label]-cr[label] if pd.notna(rr[label]) and pd.notna(cr[label]) else np.nan,'Current_Coverage_Pct':cc[label],'Recommended_Coverage_Pct':rc[label]})
    detail=cur.merge(scored[['symbol','DCVFM_Score','Signal','ret_20d','ret_60d','ret_120d','ret_250d']],left_on='Ticker',right_on='symbol',how='left')
    return pd.DataFrame(rows),detail
