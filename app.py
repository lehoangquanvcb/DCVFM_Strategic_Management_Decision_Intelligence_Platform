from __future__ import annotations

import json
import importlib.util
import os
import time
from datetime import date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from advisory import generate_advisories
from analytics import advanced_fund_analytics, attribution, aum_bridge, competitor_score, executive_metrics, flow_table, integrated_financial_model, stress_test, product_profitability, distribution_intelligence, investor_ews, compliance_cockpit, product_strategy, business_plan_kpi, decision_summary, scenario_financial_impact, three_statement_comparison
from config import APP_NAME, APP_VERSION, AUTHOR, DEFAULT_MASTER, COLORS
from copilot import answer as copilot_answer
from data_loader import company_profile, config_map, load_master, validate_master
from data_quality import action_summary, quality_summary, quality_table
from export_pack import board_pack_pdf, board_pack_pptx
from market_data import get_market_data, market_metrics, market_regime, market_technical_frame
from ui import dataframe, header, inject_css, tabs_note
from vnstock_auth import configure_vnstock_auth, resolve_api_key
from investment_ai import load_stock_universe, score_stocks, construct_portfolio, load_silver_flow
from portfolio_compare import current_portfolio, compare_portfolios

st.set_page_config(page_title=APP_NAME, page_icon="📊", layout="wide", initial_sidebar_state="expanded")
START_TS=time.time()
HAS_VNSTOCK=bool(importlib.util.find_spec("vnstock_data") or importlib.util.find_spec("vnstock"))
CLOUD_SAFE=not HAS_VNSTOCK
print(f"[DCVFM V3.3] startup | vnstock_available={HAS_VNSTOCK} | cloud_safe={CLOUD_SAFE}", flush=True)
inject_css()

@st.cache_data(show_spinner=False)
def cached_master(source): return load_master(source)
@st.cache_data(ttl=3600, show_spinner=False)
def cached_market(symbol,start,end,source,fallback,base,allow_live): return get_market_data(symbol,start,end,source,fallback,base,allow_live=allow_live)
@st.cache_resource(show_spinner=False)
def cached_auth(api_key): return configure_vnstock_auth(api_key)

with st.sidebar:
    st.markdown("### Control Panel")
    uploaded=st.file_uploader("Upload Master Excel",type=["xlsx"])
    st.caption("No upload: packaged V4.4 Master is used.")
    if st.button("Refresh cached data",use_container_width=True): st.cache_data.clear(); st.rerun()
    st.divider()
    NAV_PAGES=[
        "01 Macro Intelligence",
        "02 Sector Intelligence",
        "03 Market Overview",
        "04 Recommended BUY",
        "05 REDUCE & SELL",
        "06 Recommended Portfolio",
        "07 Current Fund Portfolio",
        "08 Portfolio Comparison",
        "09 Fund & Business Intelligence",
        "10 Risk, Governance & Advisory",
    ]
    selected_page=st.radio("Navigation",NAV_PAGES,index=0,key="main_vertical_nav")

source=uploaded.getvalue() if uploaded else str(DEFAULT_MASTER)
print("[DCVFM V3.3] loading Master Excel", flush=True)
try: data=cached_master(source)
except Exception as exc: st.error(f"Unable to load Master Excel: {exc}"); st.stop()
issues=validate_master(data)
if issues: st.warning("Data quality issues: "+" | ".join(issues))
profile=company_profile(data); cfg=config_map(data); funds=data["Fund_Master"]["Fund_Code"].dropna().astype(str).tolist()
print("[DCVFM V3.3] Master Excel loaded", flush=True)
api_key=resolve_api_key(st.secrets) if HAS_VNSTOCK else None
auth_state=cached_auth(api_key) if HAS_VNSTOCK else {"available":False,"authenticated":False,"tier":"Cloud-safe","membership":None,"reported_plan":None,"limit":None,"message":"Sponsor runtime intentionally disabled on Streamlit Cloud"}
with st.sidebar:
    selected_fund=st.selectbox("Fund / strategy",funds,index=0)
    symbol=st.text_input("Market index",str(cfg.get("Index_Symbol","VNINDEX")))
    start=st.date_input("Market start",pd.to_datetime(cfg.get("Start_Date","2025-01-01")).date())
    fallback=st.toggle("Safe fallback",value=str(cfg.get("Fallback_Enabled","Yes")).lower()=="yes")
    st.divider()
    if auth_state["authenticated"]:
        limit_text=f" • {auth_state['limit']} req/min" if auth_state.get("limit") else ""
        st.success(f"Vnstock API authenticated{limit_text}")
        if auth_state.get("membership"):
            st.caption(f"Membership reported by Vnstock: {auth_state['membership']}")
        elif auth_state.get("reported_plan"):
            st.caption(f"API plan reported by Vnstock: {auth_state['reported_plan']} (website sponsor badge may be separate)")
        else:
            st.caption("Vnstock did not return membership metadata to this runtime.")
    elif auth_state["available"]:
        st.warning("Vnstock installed but no authenticated identity detected")
    else:
        st.info("Cloud-safe mode: Vnstock Sponsor calls are disabled here; the app reads sanitized local Silver caches.")
    st.caption("API key is never displayed, logged or stored in the Master Excel.")
    st.caption(f"Master {profile.get('Model_Version',APP_VERSION)} • {profile.get('Platform_As_of','')}")

print(f"[DCVFM V3.3] market layer | live={HAS_VNSTOCK}", flush=True)
market,market_source,market_error=cached_market(symbol,start.isoformat(),date.today().isoformat(),str(cfg.get("Preferred_Source","VCI")),fallback,float(cfg.get("Offline_Base_Index",1265)),HAS_VNSTOCK)
mm=market_metrics(market); regime=market_regime(mm); ex=executive_metrics(data); quality=quality_summary(data); actions=action_summary(data); advice=generate_advisories(data,regime); plan_kpis=business_plan_kpi(data); offtrack=int((plan_kpis["Status"]=="OFF TRACK").sum())
header(APP_VERSION,AUTHOR)
stock_raw,stock_source=load_stock_universe(); stock_scores=score_stocks(stock_raw)
silver_flow,silver_flow_source=load_silver_flow()
print(f"[DCVFM V3.3.9] render ready in {time.time()-START_TS:.2f}s | stock_source={stock_source} | flow_source={silver_flow_source}", flush=True)
if market_error:
    if market_source == "Vnstock Cache":
        st.info("VNSTOCK SILVER CACHE • Local authenticated refresh; Cloud does not call Sponsor APIs.")
    else:
        st.info("Live Vnstock and local cache are unavailable; the platform is using a clearly labelled illustrative fallback. Company data still comes from Master Excel.")

# V3.3 investment decision flow: Macro -> Sector -> Market -> BUY -> REDUCE/SELL -> Recommended -> Current -> Comparison.
from pathlib import Path as _Path
_V33_CACHE=_Path(__file__).resolve().parent/'data_cache'
def _v33_csv(name):
    p=_V33_CACHE/name
    try: return pd.read_csv(p) if p.exists() else pd.DataFrame()
    except Exception: return pd.DataFrame()
def _silver_cache_status():
    """Separate cache presence from model readiness; never infer readiness from row count alone."""
    meta={}
    try:
        path=_V33_CACHE/'silver_metadata.json'
        if path.exists(): meta=json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        pass
    real_source=str(meta.get('source','')).upper()=='VNSTOCK_SILVER'
    cache_present=real_source and not stock_raw.empty and 'Illustrative' not in str(stock_source)
    coverage=meta.get('coverage') or {}
    sector_coverage=float(coverage.get('sector') or 0)
    model_ready=bool(cache_present and meta.get('full_factor_ready',False) and sector_coverage>0 and not stock_scores.empty)
    return {'meta':meta,'available':cache_present,'ready':model_ready,'sector_coverage':sector_coverage}

def _production_ready():
    return _silver_cache_status()['ready']

def _status_banner():
    status=_silver_cache_status(); meta=status['meta']
    if status['ready']:
        st.success(f"VNSTOCK SILVER • Recommendation quality gate passed • {meta.get('stock_rows',len(stock_raw)):,} stocks • Refresh: {meta.get('refresh_timestamp','unknown')}")
    elif status['available']:
        st.info(f"VNSTOCK SILVER CACHE AVAILABLE • {meta.get('stock_rows',len(stock_raw)):,} stocks • {meta.get('score_version','unknown version')} • Refresh: {meta.get('refresh_timestamp','unknown')}")
        st.warning(f"Recommendation quality gate NOT PASSED • Sector coverage: {status['sector_coverage']:.1%}. Market, macro, and available stock factors remain viewable; official BUY/SELL and model portfolio remain withheld.")
    else:
        st.warning('Silver stock cache not found in this deployment. Verify tracked cache files and metadata in the deployed Git commit.')

def _stock_factor_diagnostics():
    status=_silver_cache_status()
    if not status['available']:
        st.info('No deployed Silver stock cache. Check GitHub deployment and data_cache metadata.')
        return
    st.markdown('### Silver stock-factor explorer — NOT investment recommendations')
    st.caption('Raw observations, not BUY/SELL signals. Coverage does not guarantee accuracy. Filters and rankings below are descriptive only.')
    d=stock_raw.copy()
    if 'exchange' in d:
        exchanges=sorted(d['exchange'].dropna().astype(str).unique().tolist())
        chosen=st.multiselect('Exchanges',exchanges,default=exchanges,key='factor_exchange')
        d=d[d['exchange'].astype(str).isin(chosen)]
    metric=st.selectbox('Sort by available factor',[c for c in ['ret_60d','ret_20d','money_flow_score','roe','revenue_growth','profit_growth','liquidity_score'] if c in d],key='factor_sort')
    if metric:
        d=d.sort_values(metric,ascending=False,na_position='last')
    cols=[c for c in ['symbol','exchange','sector','close','pe','pb','roe','revenue_growth','profit_growth','ret_20d','ret_60d','money_flow_score'] if c in d]
    st.metric('Securities in view',f'{len(d):,}')
    dataframe(d[cols].head(200))
    st.download_button('Export research factors CSV',d[cols].to_csv(index=False).encode('utf-8-sig'),'silver_factor_research.csv','text/csv')
    st.caption(f"Source: {status['meta'].get('source','N/A')} • Refreshed: {status['meta'].get('refresh_timestamp','N/A')}")

if selected_page=='01 Macro Intelligence':
    st.markdown('## 01 • Macro Intelligence')
    _status_banner(); macro=_v33_csv('silver_macro_snapshot.csv')
    st.caption('Decision order starts with the macro regime. Macro observations are cached from the licensed local Vnstock Silver environment.')
    if macro.empty: st.info('Macro Silver cache is not available yet. Run the V3.3 local refresh.')
    else:
        st.metric('Macro observations',f'{len(macro):,}'); groups=macro.get('indicator_group',pd.Series(dtype=str)).dropna().unique().tolist(); st.write('Coverage: '+', '.join(groups))
        show=[c for c in ['indicator_group','time','report_time','last_updated','group_name','name','value','unit','source','gdp','cpi_total','cpi_core','center_rate'] if c in macro.columns]
        dataframe(macro[show].tail(80))
    st.markdown('### Macro → investment interpretation')
    st.write('The CIO layer should translate growth, inflation, liquidity/rates and FX into **Risk-On / Neutral / Risk-Off / Stress**, then pass that regime to sector allocation and portfolio cash limits.')

if selected_page=='02 Sector Intelligence':
    st.markdown('## 02 • Sector Intelligence'); _status_banner()
    sec=_v33_csv('silver_sector_snapshot.csv')
    status=_silver_cache_status()
    if status['available']:
        st.markdown('### Universe diagnostics — real Silver cache')
        stock_count=len(stock_raw)
        classified=stock_raw.get('sector',pd.Series(['Unknown']*stock_count)).fillna('Unknown').astype(str).str.strip().ne('Unknown').sum()
        a,b,c=st.columns(3)
        a.metric('Stocks with price/factors',f'{stock_count:,}')
        b.metric('Classified stocks',f'{classified:,}')
        c.metric('Sector coverage',f'{classified/max(stock_count,1):.1%}')
        if 'exchange' in stock_raw:
            ex=stock_raw.groupby('exchange',dropna=False).agg(stocks=('symbol','nunique'),median_60d=('ret_60d','median'),median_flow=('money_flow_score','median')).reset_index()
            st.markdown('#### Exchange breadth (not sector ranking)')
            dataframe(ex)
        st.markdown('#### Securities awaiting verified classification')
        cols=[c for c in ['symbol','exchange','close','ret_60d','money_flow_score'] if c in stock_raw]
        unknown=stock_raw[stock_raw.get('sector',pd.Series('Unknown',index=stock_raw.index)).fillna('Unknown').eq('Unknown')]
        dataframe(unknown[cols].head(200))
        st.download_button('Export unmapped tickers (CSV)',unknown[[c for c in ['symbol','exchange'] if c in unknown]].to_csv(index=False).encode('utf-8-sig'),'sector_mapping_worklist.csv','text/csv')
    if sec.empty or 'sector' not in sec or sec['sector'].fillna('Unknown').eq('Unknown').all():
        st.warning('Verified sector classification is missing. No sector rotation ranking is calculated. Add an audited sector_mapping.csv to the local refresh pipeline.')
    else:
        sec=sec[sec['sector'].fillna('Unknown').ne('Unknown')].copy()
        if all(c in sec for c in ['sector','sector_score','ret_60d','money_flow_score','stocks']):
            a,b=st.columns([1.25,1])
            a.plotly_chart(px.bar(sec.sort_values('sector_score'),x='sector_score',y='sector',orientation='h',title='Sector opportunity score'),use_container_width=True)
            b.plotly_chart(px.scatter(sec,x='ret_60d',y='money_flow_score',size='stocks',color='sector_score',hover_name='sector',title='Sector rotation: 3M return vs money flow'),use_container_width=True)
        dataframe(sec)

if selected_page=='03 Market Overview':
    st.markdown('## 03 • Market Overview'); _status_banner()
    c=st.columns(6); vals=[('VN-Index',f"{mm['level']:,.1f}"),('1M',f"{mm['return_1m']:.1%}"),('3M',f"{mm['return_3m']:.1%}"),('YTD',f"{mm['return_ytd']:.1%}"),('Volatility',f"{mm['volatility']:.1%}"),('Regime',regime)]
    for x,(k,v) in zip(c,vals):x.metric(k,v)
    tech=market_technical_frame(market); fig=go.Figure(); fig.add_trace(go.Scatter(x=tech.date,y=tech.close,name='VN-Index')); fig.add_trace(go.Scatter(x=tech.date,y=tech.MA20,name='MA20')); fig.add_trace(go.Scatter(x=tech.date,y=tech.MA50,name='MA50')); fig.update_layout(template='plotly_dark',height=440,title=f'Market trend • source: {market_source}'); st.plotly_chart(fig,use_container_width=True)
    if not silver_flow.empty:
        st.markdown('### Market money-flow leaders'); dataframe(silver_flow.sort_values('money_flow_score',ascending=False,na_position='last').head(15)[[c for c in ['symbol','foreign_flow_score','proprietary_flow_score','active_flow_score','money_flow_score'] if c in silver_flow.columns]])

if selected_page=='04 Recommended BUY':
    st.markdown('## 04 • Recommended BUY'); _status_banner()
    if _production_ready():
        buy=stock_scores[stock_scores.Signal.astype(str).isin(['BUY','STRONG BUY'])].copy()
        dataframe(buy[[c for c in ['symbol','sector','close','DCVFM_Score','Signal','Holding_Horizon','Model_Upside_Pct','Fundamental','Valuation','Momentum','Money_Flow','Risk_Liquidity','ret_20d','ret_60d'] if c in buy.columns]].head(30))
        st.caption('Model research signal; final implementation remains subject to mandate, liquidity, concentration and Investment Committee review.')
    else:
        st.warning('Official BUY recommendations withheld: verified sector coverage is missing. Explore observed financial, valuation, momentum and flow factors below.')
        _stock_factor_diagnostics()

if selected_page=='05 REDUCE & SELL':
    st.markdown('## 05 • REDUCE & SELL'); _status_banner()
    if _production_ready():
        sell=stock_scores[stock_scores.Signal.astype(str).isin(['REDUCE','SELL'])].sort_values('DCVFM_Score')
        dataframe(sell[[c for c in ['symbol','sector','close','DCVFM_Score','Signal','Fundamental','Valuation','Momentum','Money_Flow','Risk_Liquidity','ret_20d','ret_60d'] if c in sell.columns]].head(30))
    else:
        st.warning('Official REDUCE/SELL recommendations withheld: sector validation incomplete. Factor diagnostics are available below.')
        _stock_factor_diagnostics()

if selected_page=='06 Recommended Portfolio':
    st.markdown('## 06 • Recommended Portfolio'); _status_banner(); profile_ai=st.selectbox('Portfolio profile',['Conservative','Balanced','Growth','Aggressive'],index=1,key='v33_profile')
    if _production_ready():
        ideal,cash=construct_portfolio(stock_scores,profile_ai); c=st.columns(3); c[0].metric('Equity allocation',f'{100-cash:.0f}%'); c[1].metric('Cash reserve',f'{cash:.0f}%'); c[2].metric('Positions',len(ideal))
        dataframe(ideal[[c for c in ['symbol','sector','DCVFM_Score','Signal','Holding_Horizon','Weight_Pct','ret_20d','ret_60d'] if c in ideal.columns]])
    else:
        st.warning('Official model portfolio withheld: missing sector classifications prevent enforcing diversification and concentration constraints. Review investable universe factors below.')
        _stock_factor_diagnostics()

if selected_page=='07 Current Fund Portfolio':
    st.markdown(f'## 07 • Current Fund Portfolio — {selected_fund}'); cur=current_portfolio(data,selected_fund)
    if cur.empty: st.info('No current portfolio rows are available for this fund.')
    else:
        st.metric('Portfolio date',str(pd.to_datetime(cur.Date).max().date())); dataframe(cur.sort_values('Weight_Pct',ascending=False))
        sec=cur.groupby('Sector',as_index=False).Weight_Pct.sum().sort_values('Weight_Pct',ascending=False); st.plotly_chart(px.bar(sec,x='Weight_Pct',y='Sector',orientation='h',title='Current sector allocation'),use_container_width=True)

if selected_page=='08 Portfolio Comparison':
    st.markdown(f'## 08 • Current vs Recommended — {selected_fund}'); _status_banner()
    if _production_ready():
        ideal,cash=construct_portfolio(stock_scores,'Balanced'); comp,detail=compare_portfolios(data,selected_fund,stock_scores,ideal)
        st.markdown('### Comparable historical performance')
        st.caption('1M≈20 trading days, 3M≈60, 6M≈120, 12M≈250. Both portfolios use the same stock-return window and current/recommended weights. This is a holdings-based comparison, not a backtest of historical rebalancing.')
        if comp.empty: st.info('Insufficient overlapping holdings/price history for comparison.')
        else:
            fmt=comp.copy()
            for c in ['Current_Fund_Return','Recommended_Return','Excess_Recommended']:fmt[c]=fmt[c].map(lambda x:f'{x:.1%}' if pd.notna(x) else 'N/A')
            for c in ['Current_Coverage_Pct','Recommended_Coverage_Pct']:fmt[c]=fmt[c].map(lambda x:f'{x:.1f}%')
            dataframe(fmt)
            z=comp.melt(id_vars='Horizon',value_vars=['Current_Fund_Return','Recommended_Return'],var_name='Portfolio',value_name='Return'); st.plotly_chart(px.bar(z,x='Horizon',y='Return',color='Portfolio',barmode='group',title='Current fund vs recommended portfolio'),use_container_width=True)
        st.markdown('### Current holdings mapped to V3.3 signals'); dataframe(detail[[c for c in ['Ticker','Sector','Weight_Pct','DCVFM_Score','Signal','ret_20d','ret_60d','ret_120d','ret_250d'] if c in detail.columns]])
        st.warning('Recommended-portfolio returns shown above are ex-post historical diagnostics using today’s recommended weights; they are not a claim that the strategy earned those returns in real time. A proper walk-forward backtest should be added once daily score snapshots accumulate.')
    else:
        st.warning('Recommended-portfolio comparison withheld: recommendation quality gate has not passed.')
        _stock_factor_diagnostics()


# Main navigation is vertical in the left sidebar. Related legacy tabs are consolidated below.
if selected_page == '09 Fund & Business Intelligence':
    cols=st.columns(8)
    vals=[("AUM",f"{ex['aum']/1000:,.1f} tn",f"{ex['aum_growth']:.1%} MoM"),("3M net flow",f"{ex['flow_3m']:,.0f} bn",None),("VN-Index",f"{mm['level']:,.1f}",f"{mm['return_3m']:.1%} / 3M"),("Regime",regime,None),("Risk",f"{ex['risk_score']:.0f}/100",None),("Off-track KPIs",str(offtrack),"FY forecast"),("Data quality",f"{quality['score']:.0f}/100",f"{quality['overdue']} overdue"),("Actions",str(actions['open']),f"{actions['avg_progress']:.0%} progress")]
    for c,(label,value,delta) in zip(cols,vals): c.metric(label,value,delta)
    st.markdown("### Executive performance overview")
    left,centre,right=st.columns([1.25,1.05,.9])
    with left:
        aum=data["AUM"].groupby("Date",as_index=False)["AUM_VND_bn"].sum()
        fig=px.area(aum,x="Date",y="AUM_VND_bn",title="Total AUM trajectory",color_discrete_sequence=[COLORS["teal"]])
        fig.update_layout(template="plotly_dark",height=360,yaxis_title="VND bn",margin=dict(l=20,r=10,t=55,b=30)); st.plotly_chart(fig,use_container_width=True)
    with centre:
        exec_bridge=aum_bridge(data).tail(12).melt(id_vars="Date",value_vars=["Net_Flow_VND_bn","Market_and_Other_Effect"],var_name="Driver",value_name="VND_bn")
        exec_bridge["Driver"]=exec_bridge["Driver"].replace({"Net_Flow_VND_bn":"Net flow","Market_and_Other_Effect":"Market & other"})
        fig=px.bar(exec_bridge,x="Date",y="VND_bn",color="Driver",barmode="relative",title="AUM growth drivers",color_discrete_map={"Net flow":COLORS["blue"],"Market & other":COLORS["teal"]})
        fig.update_layout(template="plotly_dark",height=360,yaxis_title="VND bn",legend_orientation="h",legend_y=1.08,margin=dict(l=20,r=10,t=55,b=30)); st.plotly_chart(fig,use_container_width=True)
    with right:
        st.markdown("### Top management actions")
        for _,r in advice.head(3).iterrows(): st.markdown(f"<div class='advisory-card'><b>{r['Priority']} · {r['Domain']}</b><br>{r['Recommended_Action']}<br><span class='muted'>Owner: {r['Owner']}</span></div>",unsafe_allow_html=True)

    flow_panel,performance_panel=st.columns(2)
    with flow_panel:
        latest_flow_date=data["Fund_Flows"]["Date"].max(); recent_flows=data["Fund_Flows"].loc[data["Fund_Flows"]["Date"]>=latest_flow_date-pd.DateOffset(months=3)].groupby("Fund_Code",as_index=False)["Net_Flow_VND_bn"].sum().sort_values("Net_Flow_VND_bn")
        fig=px.bar(recent_flows,x="Net_Flow_VND_bn",y="Fund_Code",orientation="h",color="Net_Flow_VND_bn",color_continuous_scale="RdYlGn",title="Three-month net flow by fund")
        fig.update_layout(template="plotly_dark",height=350,xaxis_title="VND bn",yaxis_title=None,coloraxis_showscale=False,margin=dict(l=20,r=10,t=55,b=30)); st.plotly_chart(fig,use_container_width=True)
    with performance_panel:
        exec_perf=advanced_fund_analytics(data).copy()
        fig=px.scatter(exec_perf,x="Volatility",y="Annualized_Return",text="Fund_Code",size="NAV",color="Alpha_3M",color_continuous_scale="RdYlGn",title="Fund risk–return positioning",hover_data=["Sharpe","Max_Drawdown"])
        fig.update_traces(textposition="top center"); fig.update_layout(template="plotly_dark",height=350,xaxis_tickformat=".0%",yaxis_tickformat=".0%",margin=dict(l=20,r=10,t=55,b=30)); st.plotly_chart(fig,use_container_width=True)

    plan_panel,risk_panel=st.columns(2)
    with plan_panel:
        plan_view=plan_kpis.copy(); plan_view["Forecast_Attainment"]=plan_view["FY_Forecast"]/plan_view["FY_Plan"].replace(0,pd.NA)
        fig=px.bar(plan_view.sort_values("Forecast_Attainment"),x="Forecast_Attainment",y="KPI",orientation="h",color="Status",title="Full-year forecast attainment",color_discrete_map={"ON TRACK":COLORS["green"],"WATCH":COLORS["amber"],"OFF TRACK":COLORS["red"]},hover_data=["FY_Forecast","FY_Plan","Owner"])
        fig.add_vline(x=1,line_dash="dash",line_color="#F8FAFC"); fig.update_layout(template="plotly_dark",height=380,xaxis_tickformat=".0%",xaxis_title="Forecast / Plan",yaxis_title=None,margin=dict(l=20,r=10,t=55,b=30)); st.plotly_chart(fig,use_container_width=True)
    with risk_panel:
        risk_view=data["Risk_Indicators"].copy(); risk_view["Current_Score"]=pd.to_numeric(risk_view["Current_Score"],errors="coerce")
        fig=px.bar(risk_view.sort_values("Current_Score"),x="Current_Score",y="Risk_Type",orientation="h",color="Current_Score",range_color=[0,100],color_continuous_scale="RdYlGn_r",title="Enterprise risk priorities",hover_data=["Severity","Owner","Recommended_Action"])
        fig.update_layout(template="plotly_dark",height=380,xaxis_title="Risk score / 100",yaxis_title=None,coloraxis_showscale=False,margin=dict(l=20,r=10,t=55,b=30)); st.plotly_chart(fig,use_container_width=True)

    st.markdown("### Management watchlist")
    watchlist=plan_view.loc[plan_view["Status"].isin(["WATCH","OFF TRACK"]),["KPI","Status","Forecast_Attainment","Owner"]].sort_values("Forecast_Attainment")
    dataframe(watchlist.style.format({"Forecast_Attainment":"{:.1%}"}))


    st.markdown("### Market & investment intelligence")
    live_mode="Illustrative" not in stock_source and "demo" not in stock_source.lower()
    if live_mode and not stock_scores.empty:
        valid=stock_scores.dropna(subset=["DCVFM_Score"]).copy()
        buys=valid[valid["Signal"].astype(str).isin(["BUY","STRONG BUY"])].head(5)
        sells=valid[valid["Signal"].astype(str).isin(["SELL","REDUCE"])].sort_values("DCVFM_Score").head(5)
        ideal_exec,cash_exec=construct_portfolio(valid,"Balanced")
        ec=st.columns(4)
        ec[0].metric("Investment data", "SILVER CACHE")
        ec[1].metric("BUY candidates",len(buys))
        ec[2].metric("REDUCE / SELL",len(sells))
        ec[3].metric("Recommended cash",f"{cash_exec}%")
        a,b,c=st.columns(3)
        with a:
            st.markdown("#### Recommended BUY")
            dataframe(buys[[x for x in ["symbol","DCVFM_Score","Signal","Holding_Horizon"] if x in buys.columns]]) if not buys.empty else st.info("No BUY signal passes current model rules.")
        with b:
            st.markdown("#### Recommended REDUCE / SELL")
            dataframe(sells[[x for x in ["symbol","DCVFM_Score","Signal","Holding_Horizon"] if x in sells.columns]]) if not sells.empty else st.info("No REDUCE/SELL signal passes current model rules.")
        with c:
            st.markdown("#### Recommended portfolio")
            dataframe(ideal_exec[[x for x in ["symbol","Weight_Pct","DCVFM_Score","Signal"] if x in ideal_exec.columns]]) if not ideal_exec.empty else st.info("Portfolio not generated because evidence is insufficient.")
    else:
        st.warning("Full-factor Silver recommendation cache is not available. BUY/SELL and recommended portfolio are intentionally withheld rather than inferred from demo data.")
        if not silver_flow.empty and "money_flow_score" in silver_flow.columns:
            st.caption(f"Verified source available: {silver_flow_source}. Showing flow leaders/laggards, not BUY/SELL recommendations.")
            fa,fb=st.columns(2)
            with fa:
                st.markdown("#### Silver money-flow leaders")
                dataframe(silver_flow.head(8)[[c for c in ["symbol","money_flow_score","foreign_flow_score","proprietary_flow_score","active_flow_score"] if c in silver_flow.columns]])
            with fb:
                st.markdown("#### Silver money-flow laggards")
                dataframe(silver_flow.tail(8).sort_values("money_flow_score")[[c for c in ["symbol","money_flow_score","foreign_flow_score","proprietary_flow_score","active_flow_score"] if c in silver_flow.columns]])

if selected_page == '09 Fund & Business Intelligence':
    perf=advanced_fund_analytics(data)
    formatters={c:"{:.1%}" for c in ["Return_1M","Return_3M","Return_12M","Alpha_3M","Annualized_Return","Volatility","Tracking_Error","Max_Drawdown","Positive_Month_Ratio","Peer_Percentile"]}
    formatters.update({"NAV":"{:,.2f}","Sharpe":"{:.2f}","Sortino":"{:.2f}","Information_Ratio":"{:.2f}"})
    dataframe(perf.style.format(formatters))
    nav=data["NAV_History"].copy(); nav["Indexed_NAV"]=nav.groupby("Fund_Code")["NAV"].transform(lambda s:s/s.iloc[0]*100)
    fig=px.line(nav,x="Date",y="Indexed_NAV",color="Fund_Code",title="Indexed NAV and performance persistence"); fig.update_layout(template="plotly_dark",height=440); st.plotly_chart(fig,use_container_width=True)

if selected_page == '09 Fund & Business Intelligence':
    bridge=aum_bridge(data); a,b=st.columns(2)
    with a:
        fig=px.area(data["AUM"],x="Date",y="AUM_VND_bn",color="Fund_Code",title="AUM composition"); fig.update_layout(template="plotly_dark",height=420); st.plotly_chart(fig,use_container_width=True)
    with b:
        recent=bridge.tail(12).melt(id_vars="Date",value_vars=["Net_Flow_VND_bn","Market_and_Other_Effect"],var_name="Driver",value_name="VND_bn"); fig=px.bar(recent,x="Date",y="VND_bn",color="Driver",barmode="relative",title="AUM bridge: flow vs market/other effect"); fig.update_layout(template="plotly_dark",height=420); st.plotly_chart(fig,use_container_width=True)
    dataframe(flow_table(data))

if selected_page == '09 Fund & Business Intelligence':
    port=data["Portfolio"]; fund_port=port[port["Fund_Code"]==selected_fund].copy(); a,b=st.columns(2)
    with a:
        fig=px.treemap(fund_port,path=["Sector","Ticker"],values="Weight_Pct",title=f"{selected_fund} allocation"); fig.update_layout(template="plotly_dark",height=480); st.plotly_chart(fig,use_container_width=True)
    with b:
        att=attribution(data,selected_fund)
        if not att.empty:
            fig=px.bar(att,x="Ticker",y="Contribution_Pct",color="Contribution_Pct",color_continuous_scale="RdYlGn",title="Active contribution"); fig.update_layout(template="plotly_dark",height=480,yaxis_tickformat=".2%"); st.plotly_chart(fig,use_container_width=True)
        else: st.info("No attribution rows for selected strategy.")
    dataframe(fund_port)

if selected_page == '09 Fund & Business Intelligence':
    etfs=["E1VFVN30","FUEVFVND"]; p=advanced_fund_analytics(data).query("Fund_Code in @etfs"); dataframe(p.style.format(formatters))
    ef=data["Fund_Flows"].query("Fund_Code in @etfs"); fig=px.bar(ef,x="Date",y="Net_Flow_VND_bn",color="Fund_Code",barmode="group",title="ETF creation/redemption proxy"); fig.update_layout(template="plotly_dark",height=440); st.plotly_chart(fig,use_container_width=True)

if selected_page == '09 Fund & Business Intelligence':
    k=st.columns(8); market_kpis=[("VN-Index",f"{mm['level']:,.1f}"),("1M return",f"{mm['return_1m']:.1%}"),("3M return",f"{mm['return_3m']:.1%}"),("YTD return",f"{mm['return_ytd']:.1%}"),("20D volatility",f"{mm['volatility']:.1%}"),("Drawdown",f"{mm['drawdown']:.1%}"),("52W high gap",f"{mm['distance_52w_high']:.1%}"),("Regime",regime)]
    for col,(label,value) in zip(k,market_kpis): col.metric(label,value)
    st.caption(f"Market source: {market_source} • MA20 {mm['ma20']:,.1f} • MA50 {mm['ma50']:,.1f} • MA200 {mm['ma200']:,.1f}")
    volume_series=pd.to_numeric(market.get("volume",pd.Series(dtype=float)),errors="coerce").dropna()
    close_series=pd.to_numeric(market.get("close",pd.Series(dtype=float)),errors="coerce").dropna()
    volume_latest=mm.get("volume_latest",float(volume_series.iloc[-1]) if not volume_series.empty else float("nan"))
    volume_20d_avg=mm.get("volume_20d_avg",float(volume_series.tail(20).mean()) if not volume_series.empty else float("nan"))
    volume_ratio_20d=mm.get("volume_ratio_20d",volume_latest/volume_20d_avg if pd.notna(volume_20d_avg) and volume_20d_avg>0 else float("nan"))
    if "rsi14" in mm:
        rsi14=mm["rsi14"]
    else:
        price_delta=close_series.diff(); avg_gain=price_delta.clip(lower=0).tail(14).mean(); avg_loss=(-price_delta.clip(upper=0)).tail(14).mean()
        rsi14=100-(100/(1+avg_gain/avg_loss)) if pd.notna(avg_loss) and avg_loss>0 else float("nan")
    liquidity_cols=st.columns(4)
    liquidity_kpis=[("Latest volume",f"{volume_latest/1e9:,.2f} bn" if pd.notna(volume_latest) else "N/A"),("20D average volume",f"{volume_20d_avg/1e9:,.2f} bn" if pd.notna(volume_20d_avg) else "N/A"),("Volume / 20D average",f"{volume_ratio_20d:.2f}x" if pd.notna(volume_ratio_20d) else "N/A"),("RSI 14",f"{rsi14:.1f}" if pd.notna(rsi14) else "N/A")]
    for col,(label,value) in zip(liquidity_cols,liquidity_kpis): col.metric(label,value)
    tech=market_technical_frame(market)
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.05,row_heights=[.75,.25])
    fig.add_trace(go.Candlestick(x=tech["date"],open=tech["open"],high=tech["high"],low=tech["low"],close=tech["close"],name=symbol),row=1,col=1)
    for name,color in [("MA20","#17C3B2"),("MA50","#F59E0B"),("MA200","#A78BFA")]: fig.add_trace(go.Scatter(x=tech["date"],y=tech[name],name=name,line=dict(width=1.4,color=color)),row=1,col=1)
    fig.add_trace(go.Bar(x=tech["date"],y=tech["volume"],name="Volume",marker_color="#2F80ED"),row=2,col=1); fig.add_trace(go.Scatter(x=tech["date"],y=tech["Volume_MA20"],name="Volume MA20",line=dict(color="#F8FAFC",width=1)),row=2,col=1)
    fig.update_layout(template="plotly_dark",height=650,title=f"{symbol}: price, trend and liquidity",xaxis_rangeslider_visible=False,legend_orientation="h",legend_y=1.02); st.plotly_chart(fig,use_container_width=True)
    st.caption("Tab 06 contains market and liquidity indicators only. Price, volume and technical measures are sourced from the live Vnstock market feed when available; cache or labelled fallback is used only when the live request fails.")

if selected_page == '09 Fund & Business Intelligence':
    comp=competitor_score(data); name_col=comp.columns[0]; fig=px.bar(comp,x="Competitive_Score",y=name_col,orientation="h",color="Competitive_Score",color_continuous_scale="Blues",title="Competitive position score"); fig.update_layout(template="plotly_dark",height=430); st.plotly_chart(fig,use_container_width=True); dataframe(comp)

if selected_page == '09 Fund & Business Intelligence':
    fin=integrated_financial_model(data); c1,c2=st.columns(2)
    c1.plotly_chart(px.bar(fin,x="Year",y=["Revenue_VND_bn","NPAT_VND_bn"],barmode="group",title="AUM-driven revenue and NPAT").update_layout(template="plotly_dark",height=410),use_container_width=True)
    c2.plotly_chart(px.line(fin,x="Year",y=["Fee_Yield_Pct","PBT_Margin_Pct"],markers=True,title="Fee yield and operating leverage").update_layout(template="plotly_dark",height=410,yaxis_tickformat=".1%"),use_container_width=True)
    dataframe(fin.style.format({"Market_Return_Pct":"{:.1%}","Fee_Yield_Pct":"{:.2%}","Effective_Tax_Pct":"{:.1%}","AUM_Growth_Pct":"{:.1%}","PBT_Margin_Pct":"{:.1%}"}))

if selected_page == '10 Risk, Governance & Advisory':
    risk=data["Risk_Indicators"].copy(); risk["Current_Score"]=pd.to_numeric(risk["Current_Score"],errors="coerce"); fig=px.bar(risk.sort_values("Current_Score"),x="Current_Score",y="Risk_Type",orientation="h",color="Current_Score",color_continuous_scale="RdYlGn_r",range_color=[0,100],title="Enterprise early-warning scores"); fig.update_layout(template="plotly_dark",height=460); st.plotly_chart(fig,use_container_width=True); dataframe(risk)

if selected_page == '09 Fund & Business Intelligence':
    c1,c2,c3=st.columns(3); shock=c1.slider("VN-Index shock",-0.40,0.10,-0.20,0.05); redemption=c2.slider("Redemption",0.0,0.40,0.15,0.05); fee=c3.slider("Fee compression",0.0,0.30,0.10,0.05); s=stress_test(data,shock,redemption,fee); d=st.columns(4); d[0].metric("Stressed AUM",f"{s['AUM']/1000:,.1f} tn"); d[1].metric("Revenue",f"{s['Revenue']:,.0f} bn"); d[2].metric("PBT",f"{s['PBT']:,.0f} bn"); d[3].metric("PBT impact",f"{s['PBT_Impact']:.1%}"); st.warning("Illustrative management stress test; validate financial assumptions before formal use.")

if selected_page == '10 Risk, Governance & Advisory':
    own=data["Shareholders"].copy(); own["Ownership_Pct"]=pd.to_numeric(own["Ownership_Pct"],errors="coerce"); fig=px.pie(own,names="Shareholder",values="Ownership_Pct",hole=.55,title="Ownership structure"); fig.update_layout(template="plotly_dark",height=430); st.plotly_chart(fig,use_container_width=True); dataframe(data["Board_Events"])

if selected_page == '10 Risk, Governance & Advisory':
    q=quality_table(data); c=st.columns(4); c[0].metric("Quality score",f"{quality['score']:.0f}/100"); c[1].metric("Verified fields",f"{quality['verified_pct']:.0%}"); c[2].metric("Assumption domains",f"{quality['assumption_pct']:.0%}"); c[3].metric("Overdue domains",quality['overdue'])
    fig=px.bar(q,x="Quality_Score",y="Data_Domain",orientation="h",color="Quality_Score",range_x=[0,100],color_continuous_scale="RdYlGn",title="Data lineage and quality by domain"); fig.update_layout(template="plotly_dark",height=430); st.plotly_chart(fig,use_container_width=True); dataframe(q)
    st.markdown("### News and operating events")
    events=data.get("News_Events",pd.DataFrame()).copy()
    if events.empty:
        st.info("No news or operating events are available in the current Master.")
    else:
        date_col=next((c for c in ["Date","Event_Date","As_of","Published_Date","time"] if c in events.columns),None)
        if date_col:
            events[date_col]=pd.to_datetime(events[date_col],errors="coerce")
            events=events.sort_values(date_col,ascending=False,na_position="last")
        dataframe(events)

if selected_page == '10 Risk, Governance & Advisory':
    for _,r in advice.iterrows(): st.markdown(f"<div class='advisory-card'><b>{r['Priority']} · {r['Domain']}</b><br><b>Observation:</b> {r['Observation']}<br><b>Diagnosis:</b> {r['Diagnosis']}<br><b>Implication:</b> {r['Implication']}<br><b>Recommendation:</b> {r['Recommended_Action']}<br><span class='muted'>Owner: {r['Owner']}</span></div>",unsafe_allow_html=True)
    st.markdown("### Management Action Tracker"); tracker=data.get("Action_Tracker",pd.DataFrame()).copy(); dataframe(tracker.style.format({"Progress_Pct":"{:.0%}"}))

if selected_page == '10 Risk, Governance & Advisory':
    st.subheader("Board / Executive Pack")
    pdf=board_pack_pdf(ex,mm,regime,quality,advice,offtrack,actions); pptx=board_pack_pptx(ex,regime,quality,advice,offtrack,actions); pack={"as_of":str(ex["as_of"]),"executive_metrics":ex,"market_metrics":mm,"market_regime":regime,"off_track_kpis":offtrack,"open_actions":actions,"data_quality":quality,"top_recommendations":advice.head(5).to_dict(orient="records")}
    c=st.columns(4); c[0].download_button("Board Pack PDF",pdf,"DCVFM_Board_Pack_V4_4.pdf","application/pdf",use_container_width=True); c[1].download_button("Board Pack PPTX",pptx,"DCVFM_Board_Pack_V4_4.pptx","application/vnd.openxmlformats-officedocument.presentationml.presentation",use_container_width=True); c[2].download_button("Board Pack JSON",json.dumps(pack,default=str,ensure_ascii=False,indent=2),"DCVFM_Board_Pack_V4_4.json","application/json",use_container_width=True); c[3].download_button("Recommendations CSV",advice.to_csv(index=False).encode("utf-8-sig"),"DCVFM_Recommendations_V4_4.csv","text/csv",use_container_width=True)
    st.markdown("### Intelligence Copilot")
    question=st.text_input("Ask about AUM, funds, market, liquidity, financials, operations or data quality",placeholder="Ví dụ: KPI vận hành nào đang cần xử lý?")
    if question: st.markdown(f"<div class='advisory-card'>{copilot_answer(question,data,regime)}</div>",unsafe_allow_html=True)
    st.caption("Copilot V4.4 is deterministic and grounded in the loaded Master; it does not make external factual claims.")

if selected_page == '09 Fund & Business Intelligence':
    prof=product_profitability(data); dist=distribution_intelligence(data)
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Product revenue",f"{prof['Revenue_VND_bn'].sum():,.0f} bn")
    c2.metric("Product contribution",f"{prof['Contribution_VND_bn'].sum():,.0f} bn")
    c3.metric("Net channel sales",f"{dist['Net_Sales_VND_bn'].sum():,.0f} bn")
    c4.metric("Largest channel share",f"{dist['AUM_Share_Pct'].max():.1%}")
    a,b=st.columns(2)
    a.plotly_chart(px.bar(prof,x="Fund_Code",y="Contribution_VND_bn",color="Contribution_Margin_Pct",color_continuous_scale="Blues",title="Product contribution and margin").update_layout(template="plotly_dark",height=420),use_container_width=True)
    b.plotly_chart(px.scatter(dist,x="Net_Sales_VND_bn",y="Ending_AUM_VND_bn",size="Active_Investors",color="Retention_Pct",hover_name="Channel",title="Distribution economics").update_layout(template="plotly_dark",height=420),use_container_width=True)
    dataframe(prof.style.format({"Effective_Fee_Pct":"{:.2%}","Contribution_Margin_Pct":"{:.1%}"}))
    dataframe(dist.style.format({"Retention_Pct":"{:.1%}","AUM_Share_Pct":"{:.1%}","Cost_per_Net_Sales":"{:.2f}"}))

if selected_page == '09 Fund & Business Intelligence':
    inv=investor_ews(data); compc=compliance_cockpit(data)
    a,b=st.columns(2)
    a.plotly_chart(px.bar(inv,x="Cohort",y="Risk_Score",color="Risk_Level",title="Investor redemption early-warning score").update_layout(template="plotly_dark",height=420),use_container_width=True)
    b.plotly_chart(px.bar(compc,x="Control_ID",y="Headroom",color="Status",hover_data=["Control_Area","Metric","Owner"],title="Compliance control headroom").update_layout(template="plotly_dark",height=420),use_container_width=True)
    st.caption("Redemption Risk Score is a monitoring signal, not a forecast probability. Compliance rows require Legal/Compliance validation.")
    dataframe(inv.style.format({"Underperformance_3M_Pct":"{:.1%}","Concentration_Pct":"{:.1%}"}))
    dataframe(compc)

if selected_page == '09 Fund & Business Intelligence':
    products=product_strategy(data); kpis=business_plan_kpi(data)
    a,b=st.columns(2)
    a.plotly_chart(px.bar(products,x="Weighted_Score",y="Product_Idea",orientation="h",color="Decision",range_x=[0,10],title="Product strategy screening").update_layout(template="plotly_dark",height=430),use_container_width=True)
    b.plotly_chart(px.bar(kpis,x="KPI",y="Forecast_vs_Plan_Pct",color="Status",title="FY forecast versus plan").update_layout(template="plotly_dark",height=430,yaxis_tickformat=".1%"),use_container_width=True)
    dataframe(products)
    dataframe(kpis.style.format({"Variance_Pct":"{:.1%}","Forecast_vs_Plan_Pct":"{:.1%}"}))

if selected_page == '10 Risk, Governance & Advisory':
    decisions=data["Decision_Tracker"].copy(); ds=decision_summary(data); ops=data["Operating_KPI"].copy()
    c1,c2,c3=st.columns(3); c1.metric("Open decisions",ds["open"]); c2.metric("High priority",ds["high"]); c3.metric("Average progress",f"{ds['avg_progress']:.0%}")
    a,b=st.columns(2)
    ops["Current_Value"]=pd.to_numeric(ops["Current_Value"],errors="coerce"); ops["Target_Value"]=pd.to_numeric(ops["Target_Value"],errors="coerce")
    a.plotly_chart(px.bar(ops,x="Current_Value",y="KPI",orientation="h",color="Status",hover_data=["Target_Value","Unit","Owner","Management_Action"],title="Operating KPI status").update_layout(template="plotly_dark",height=430),use_container_width=True)
    decisions["Progress_Pct"]=pd.to_numeric(decisions["Progress_Pct"],errors="coerce")
    b.plotly_chart(px.bar(decisions,x="Progress_Pct",y="Decision_ID",orientation="h",color="Priority",hover_data=["Recommendation","Decision_Status","Action_Owner"],title="Decision execution progress").update_layout(template="plotly_dark",height=430,xaxis_tickformat=".0%"),use_container_width=True)
    dataframe(ops)
    dataframe(decisions.style.format({"Progress_Pct":"{:.0%}"}))

if selected_page == '09 Fund & Business Intelligence':
    initial_impact=scenario_financial_impact(data)
    selected=st.selectbox("Scenario for management review",initial_impact["Scenario"].tolist(),index=1)
    preset=data["Scenarios"].loc[data["Scenarios"]["Scenario"]==selected].iloc[0]
    st.markdown("### Editable management assumptions")
    st.caption("Values below start from the selected preset. Changes recalculate the linked income statement, balance sheet and cash flow statement immediately; the Master Excel is not overwritten.")
    with st.expander("Adjust scenario drivers",expanded=True):
        r1=st.columns(4)
        market_input=r1[0].number_input("Market return",value=float(preset["Market_Return_Shock_Pct"]),step=.01,format="%.2f")
        flow_input=r1[1].number_input("Net flow / beginning AUM",value=float(preset["Net_Flow_Pct_Beg_AUM"]),step=.01,format="%.2f")
        fee_input=r1[2].number_input("Fee yield change (bps)",value=float(preset["Fee_Yield_Change_bps"]),step=5.0)
        payout_input=r1[3].number_input("Dividend payout",min_value=0.0,max_value=1.0,value=float(preset["Dividend_Payout_Pct"]),step=.05,format="%.2f")
        r2=st.columns(4)
        personnel_input=r2[0].number_input("Personnel cost change",value=float(preset["Personnel_Cost_Change_Pct"]),step=.01,format="%.2f")
        opex_input=r2[1].number_input("Other opex change",value=float(preset["Other_Opex_Change_Pct"]),step=.01,format="%.2f")
        oneoff_input=r2[2].number_input("One-off cost (VND bn)",min_value=0.0,value=float(preset["One_Off_Cost_VND_bn"]),step=5.0)
        capex_input=r2[3].number_input("CAPEX (VND bn)",min_value=0.0,value=float(preset["Capex_VND_bn"]),step=5.0)
        r3=st.columns(4)
        ar_input=r3[0].number_input("AR days change",value=float(preset["AR_Days_Change"]),step=1.0)
        ap_input=r3[1].number_input("AP days change",value=0.0,step=1.0)
        debt_input=r3[2].number_input("Debt change (VND bn)",value=0.0,step=10.0)
        equity_input=r3[3].number_input("Equity injection (VND bn)",min_value=0.0,value=0.0,step=10.0)
    overrides={"Market_Return_Shock_Pct":market_input,"Net_Flow_Pct_Beg_AUM":flow_input,"Fee_Yield_Change_bps":fee_input,"Dividend_Payout_Pct":payout_input,"Personnel_Cost_Change_Pct":personnel_input,"Other_Opex_Change_Pct":opex_input,"One_Off_Cost_VND_bn":oneoff_input,"Capex_VND_bn":capex_input,"AR_Days_Change":ar_input,"AP_Days_Change":ap_input,"Debt_Change_VND_bn":debt_input,"Equity_Injection_VND_bn":equity_input}
    impact=scenario_financial_impact(data,overrides,selected)
    row=impact.loc[impact["Scenario"]==selected].iloc[0]; base=impact.iloc[0]
    k=st.columns(8)
    cards=[("Ending AUM",f"{row['Ending_AUM_VND_bn']/1000:,.1f} tn",f"{row['Ending_AUM_VND_bn']-base['Ending_AUM_VND_bn']:+,.0f} bn vs Base"),("Revenue",f"{row['Revenue_VND_bn']:,.0f} bn",f"{row['Revenue_vs_Base_VND_bn']:+,.0f} bn"),("PBT",f"{row['PBT_VND_bn']:,.0f} bn",f"{row['PBT_vs_Base_VND_bn']:+,.0f} bn"),("NPAT",f"{row['NPAT_VND_bn']:,.0f} bn",f"{row['NPAT_vs_Base_VND_bn']:+,.0f} bn"),("Ending cash",f"{row['Ending_Cash_VND_bn']:,.0f} bn",f"{row['Cash_Headroom_VND_bn']:+,.0f} bn headroom"),("Total assets",f"{row['Total_Assets_VND_bn']:,.0f} bn",None),("ROA",f"{row['ROA_Pct']:.1%}",None),("ROE",f"{row['ROE_Pct']:.1%}",None)]
    for col,(label,value,delta) in zip(k,cards): col.metric(label,value,delta)
    a,b=st.columns(2)
    compare=impact.melt(id_vars="Scenario",value_vars=["Revenue_VND_bn","PBT_VND_bn","NPAT_VND_bn"],var_name="Metric",value_name="VND_bn")
    a.plotly_chart(px.bar(compare,x="Scenario",y="VND_bn",color="Metric",barmode="group",title="Income statement outcomes by scenario").update_layout(template="plotly_dark",height=450),use_container_width=True)
    bridge=pd.DataFrame({"Driver":["Base PBT","Revenue impact","Personnel impact","Other opex impact","Scenario PBT"],"Value":[base['PBT_VND_bn'],row['Revenue_VND_bn']-base['Revenue_VND_bn'],-(row['Personnel_VND_bn']-base['Personnel_VND_bn']),-(row['Other_Opex_VND_bn']-base['Other_Opex_VND_bn']),row['PBT_VND_bn']],"Measure":["absolute","relative","relative","relative","total"]})
    fig=go.Figure(go.Waterfall(x=bridge["Driver"],y=bridge["Value"],measure=bridge["Measure"],connector={"line":{"color":"#8FA3BF"}})); fig.update_layout(template="plotly_dark",height=450,title=f"PBT bridge — {selected}",yaxis_title="VND bn"); b.plotly_chart(fig,use_container_width=True)
    st.markdown("### Linked three-statement comparison")
    comparison=three_statement_comparison(base,row)
    statement_view=st.selectbox("Statement view",["Income Statement","Balance Sheet","Cash Flow Statement","All statements"],key="statement_view")
    statement_data=comparison if statement_view=="All statements" else comparison.loc[comparison["Statement"]==statement_view]
    dataframe(statement_data.style.format({"Base_VND_bn":"{:,.1f}","Scenario_VND_bn":"{:,.1f}","Variance_VND_bn":"{:+,.1f}","Variance_Pct":"{:+.1%}"}))
    st.markdown("### Controls and management ratios")
    controls=st.columns(6)
    control_cards=[("Balance check",row["Balance_Check_VND_bn"]),("Cash tie",row["Cash_Tie_Check_VND_bn"]),("Retained earnings tie",row["Retained_Earnings_Check_VND_bn"]),("Current ratio",row["Current_Ratio"]),("ROA",row["ROA_Pct"]),("ROE",row["ROE_Pct"])]
    for col,(label,value) in zip(controls,control_cards): col.metric(label,f"{value:.2f}" if "ratio" in label.lower() or "check" in label.lower() or "tie" in label.lower() else f"{value:.1%}")
    if row["Ending_Cash_VND_bn"]<300: st.error("Liquidity alert: ending cash is below the illustrative minimum threshold in the Master Excel.")
    if abs(row["Balance_Check_VND_bn"])>0.1: st.error("Model control failed: projected balance sheet does not balance.")
    if abs(row["Cash_Tie_Check_VND_bn"])>0.1 or abs(row["Retained_Earnings_Check_VND_bn"])>0.1: st.error("Three-statement linkage failed: review the cash or retained-earnings roll-forward.")
    st.caption("Illustrative management forecast. Editable values affect the current session only. Replace blue assumptions in the Master with approved budget/actual data before formal use.")


# --- V4.4 baseline + V3.1 AI/Silver investment intelligence extension ---

if selected_page == '__LEGACY_STOCK_DISABLED__':
    st.markdown("### Stock Screener AI")
    st.caption(f"Source: {stock_source}. Production target: Vnstock Silver market-screener + Fundamental/Insights. Demo rows are never presented as live recommendations.")
    c1,c2,c3=st.columns(3); min_roe=c1.number_input("Minimum ROE",0.0,1.0,.15,.01); max_pe=c2.number_input("Maximum P/E",1.0,100.0,20.0,1.0); min_liq=c3.slider("Minimum liquidity score",0,100,50)
    screened=stock_scores[(stock_scores.roe>=min_roe)&(stock_scores.pe<=max_pe)&(stock_scores.liquidity_score>=min_liq)]
    dataframe(screened)
if selected_page == '__LEGACY_STOCK_DISABLED__':
    st.markdown("### Quant Opportunity Radar")
    threshold=st.slider("Minimum DCVFM Score",0,100,65)
    dataframe(stock_scores.loc[stock_scores.DCVFM_Score>=threshold,["symbol","sector","close","DCVFM_Score","Signal","Holding_Horizon","Fundamental","Valuation","Momentum","Money_Flow","Risk_Liquidity","Model_Upside_Pct"]])
    if "Illustrative" in stock_source: st.warning("Illustrative universe is active. Run refresh_silver_ai.py and create the Silver cache before treating signals as current-market output.")
if selected_page == '__LEGACY_STOCK_DISABLED__':
    st.markdown("### Sell & Risk Radar")
    dataframe(stock_scores.sort_values("DCVFM_Score").head(15)[["symbol","sector","close","DCVFM_Score","Signal","Fundamental","Valuation","Momentum","Money_Flow","Risk_Liquidity"]])
    st.caption("REDUCE/SELL is a model research signal, subject to mandate, liquidity, tracking error and Investment Committee review.")
if selected_page == '__LEGACY_STOCK_DISABLED__':
    st.markdown("### AI Stock Analyst")
    ticker=st.selectbox("Stock",stock_scores.symbol.tolist(),key="ai_stock")
    r=stock_scores.loc[stock_scores.symbol==ticker].iloc[0]
    st.markdown(f"#### {ticker} — {r['Signal']} | {r['DCVFM_Score']:.1f}/100 | {r['Holding_Horizon']}")
    cols=st.columns(5)
    for col,(label,val) in zip(cols,[("Fundamental",r.Fundamental),("Valuation",r.Valuation),("Momentum",r.Momentum),("Money Flow",r.Money_Flow),("Risk/Liquidity",r.Risk_Liquidity)]): col.metric(label,f"{val:.0f}")
    st.info("AI memo contract: verified Silver data/news first → Thesis → Catalysts → Risks → Entry → Exit triggers. Missing evidence must be disclosed; AI must not invent figures.")
if selected_page == '__LEGACY_PORT_DISABLED__':
    st.markdown("### AI Portfolio Constructor")
    profile_ai=st.selectbox("Portfolio profile",["Conservative","Balanced","Growth","Aggressive"],index=1,key="ai_portfolio")
    ideal,cash=construct_portfolio(stock_scores,profile_ai)
    if ideal.empty: st.warning("No securities pass the BUY threshold.")
    else: dataframe(ideal[["symbol","sector","DCVFM_Score","Signal","Holding_Horizon","Weight_Pct"]]); st.metric("Strategic cash reserve",f"{cash}%")
    st.caption("Production optimizer should additionally enforce sector/single-name caps, covariance, liquidity, turnover, benchmark tracking error and mandate constraints.")
if selected_page == '__LEGACY_PORT_DISABLED__':
    st.markdown("### CIO AI Copilot")
    q=st.selectbox("Decision question",["Which stocks have the strongest 3–6 month risk-adjusted setup?","Why is the top BUY stronger than the first HOLD?","How should the portfolio change if VN-Index falls 10%?","Which positions should be reduced first if liquidity deteriorates?","Summarize market regime, sector rotation and recommended actions."])
    st.code(q,language="text")
    st.write("Required output: **Observation → Evidence → Diagnosis → Investment View → Action → Horizon → Risk/Exit Trigger**.")
    st.warning("For security, Sponsor credentials stay in the licensed local/secured environment; the public Streamlit layer consumes only permitted cache/derived outputs.")
