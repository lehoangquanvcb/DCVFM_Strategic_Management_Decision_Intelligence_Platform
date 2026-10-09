"""Auditable Vnstock ICB reference mapping; local licensed environment only."""
from pathlib import Path
import os
import re
import pandas as pd

LEVELS=(1,2,3,4)

def _clean(data):
    if not isinstance(data,pd.DataFrame) or data.empty:
        raise ValueError('Reference().equity.list_by_industry() returned no data')
    required={'symbol','icb_level','icb_code','icb_name'}
    if not required.issubset(data.columns):
        raise ValueError('Missing ICB columns: '+str(sorted(required-set(data.columns))))
    d=data.copy()
    d['symbol']=d['symbol'].astype('string').str.upper().str.strip()
    d['icb_level']=pd.to_numeric(d['icb_level'],errors='coerce')
    d['icb_code']=d['icb_code'].astype('string').str.strip()
    d['icb_name']=d['icb_name'].astype('string').str.strip()
    d=d[d.symbol.str.fullmatch(r'[A-Z]{3}',na=False) & d.icb_level.isin(LEVELS)]
    d=d[d.icb_code.notna() & d.icb_name.notna() & d.icb_name.ne('')]
    if d.empty:raise ValueError('No valid three-letter symbols with ICB levels')
    # Exclude ambiguous mappings for a symbol at the same level.
    conflict=d.groupby(['symbol','icb_level']).icb_code.nunique()
    conflicts=conflict[conflict>1].index
    if len(conflicts):
        idx=pd.MultiIndex.from_frame(d[['symbol','icb_level']])
        d=d[~idx.isin(conflicts)].copy()
    d=d.sort_values(['symbol','icb_level','icb_code']).drop_duplicates(['symbol','icb_level'])
    wide=d.pivot(index='symbol',columns='icb_level',values='icb_name')
    wide.columns=[f'icb_name_{int(i)}' for i in wide.columns]
    codes=d.pivot(index='symbol',columns='icb_level',values='icb_code')
    codes.columns=[f'icb_code_{int(i)}' for i in codes.columns]
    out=wide.join(codes).reset_index()
    for level in LEVELS:
        for prefix in ['icb_name','icb_code']:
            c=f'{prefix}_{level}'
            if c not in out:out[c]=pd.NA
    out['sector']=out['icb_name_2'].fillna(out['icb_name_1'])
    out=out[out.sector.notna() & out.sector.ne('')].copy()
    out['sector_level']=out['icb_name_2'].notna().map({True:2,False:1})
    out['source']='Vnstock Reference.equity.list_by_industry'
    out['as_of_date']=pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').date().isoformat()
    out=out.sort_values('symbol').reset_index(drop=True)
    print('REFERENCE ICB:',len(out),'unique symbols; ICB level 2:',int(out.icb_name_2.notna().sum()),'conflicting symbol-level pairs excluded:',len(conflicts))
    return out

def get_reference_mapping():
    from vnstock_data import Reference
    return _clean(Reference().equity.list_by_industry(lang='vi'))

def save_reference_mapping(path):
    out=get_reference_mapping()
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    out.to_csv(tmp,index=False,encoding='utf-8-sig')
    os.replace(tmp,path)
    return out
