"""DCVFM V3.2 Silver refresh.
Creates verified Silver flow cache and metadata without exposing credentials.
A recommendation cache is only written when sufficient fundamental/technical evidence exists.
"""
from __future__ import annotations
import json, re
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

OUT=Path(__file__).resolve().parent/'data_cache'; OUT.mkdir(exist_ok=True)
from vnstock_data import Insights

def pct(s):
    x=pd.to_numeric(s,errors='coerce')
    return (x.rank(pct=True)*100).round(1)

def prep(df,prefix):
    if df is None or df.empty: return pd.DataFrame(columns=['symbol'])
    d=df.copy(); d['symbol']=d['symbol'].astype(str).str.upper().str.strip()
    keep=['symbol']+[c for c in ['value_1d','value_10d','value_1m','value_3m','value_6m','volume_1d','volume_10d'] if c in d]
    d=d[keep].drop_duplicates('symbol')
    return d.rename(columns={c:f'{prefix}_{c}' for c in d.columns if c!='symbol'})

i=Insights()
print('Fetching Vnstock Silver market flows...')
foreign=prep(i.flow.foreign(exchange='HOSE',group_by='stock'),'foreign')
prop=prep(i.flow.proprietary(exchange='HOSE',group_by='stock'),'proprietary')
try: active=prep(i.flow.active(exchange='HOSE',group_by='stock'),'active')
except Exception as e:
    print('Active flow unavailable:',type(e).__name__); active=pd.DataFrame(columns=['symbol'])
flow=foreign.merge(prop,on='symbol',how='outer').merge(active,on='symbol',how='outer')
# Conservative base-equity heuristic: exactly 3 uppercase letters. This removes warrants such as CSTB2619.
flow=flow[flow['symbol'].str.fullmatch(r'[A-Z]{3}',na=False)].copy()
for prefix in ['foreign','proprietary','active']:
    scores=[]
    for col,w in [(f'{prefix}_value_1d',.20),(f'{prefix}_value_10d',.35),(f'{prefix}_value_1m',.45)]:
        if col in flow: scores.append((pct(flow[col]),w))
    if scores:
        den=sum(w for _,w in scores); flow[f'{prefix}_flow_score']=sum(s*w for s,w in scores)/den
parts=[c for c in ['foreign_flow_score','proprietary_flow_score','active_flow_score'] if c in flow]
if parts: flow['money_flow_score']=flow[parts].mean(axis=1).round(1)
flow['refresh_timestamp']=datetime.now().astimezone().isoformat(timespec='seconds')
flow['source']='VNSTOCK_SILVER'
flow=flow.sort_values('money_flow_score',ascending=False) if 'money_flow_score' in flow else flow
flow.to_csv(OUT/'silver_flow_snapshot.csv',index=False,encoding='utf-8-sig')
meta={'source':'VNSTOCK_SILVER','refresh_timestamp':flow['refresh_timestamp'].iloc[0] if len(flow) else datetime.now().astimezone().isoformat(timespec='seconds'),'equity_symbols':int(len(flow)),'foreign_rows_raw':int(len(foreign)),'proprietary_rows_raw':int(len(prop)),'active_rows_raw':int(len(active)),'recommendation_status':'WITHHELD_UNTIL_FULL_FACTOR_CACHE','note':'Flow cache is verified Silver data. BUY/SELL requires sufficient fundamental, valuation, technical and liquidity evidence.'}
(OUT/'silver_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print('Saved:',OUT/'silver_flow_snapshot.csv')
print('Base-equity symbols:',len(flow))
print('Saved:',OUT/'silver_metadata.json')
print('Recommendation cache: WITHHELD until full-factor evidence is available.')
