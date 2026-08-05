from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent; sys.path.insert(0,str(ROOT))
from config import DEFAULT_MASTER
from data_loader import load_master,validate_master
from analytics import advanced_fund_analytics,aum_bridge,executive_metrics,integrated_financial_model,stress_test,product_profitability,distribution_intelligence,investor_ews,compliance_cockpit,product_strategy,business_plan_kpi,decision_summary,scenario_financial_impact,three_statement_comparison
from data_quality import action_summary,quality_summary,quality_table
from advisory import generate_advisories
from export_pack import board_pack_pdf,board_pack_pptx
from market_data import get_market_data,market_metrics,market_technical_frame
from macro_data import get_macro_indicators
from vnstock_auth import configure_vnstock_auth,resolve_api_key

def main():
    data=load_master(DEFAULT_MASTER); issues=validate_master(data); assert not issues,issues
    assert len(data)>=37, f"Expected >=37 sheets, got {len(data)}"
    ex=executive_metrics(data); assert ex["aum"]>0 and ex["funds"]>=5
    perf=advanced_fund_analytics(data); assert len(perf)>=5 and perf["Sharpe"].notna().any()
    bridge=aum_bridge(data); assert not bridge.empty
    model=integrated_financial_model(data); assert len(model)>=5 and model["NPAT_VND_bn"].iloc[-1]>0
    q=quality_summary(data); assert 0<=q["score"]<=100 and not quality_table(data).empty
    assert action_summary(data)["open"]>=1
    advice=generate_advisories(data,"NEUTRAL"); assert not advice.empty
    actions=action_summary(data); offtrack=int((business_plan_kpi(data)["Status"]=="OFF TRACK").sum())
    pdf=board_pack_pdf(ex,{},"NEUTRAL",q,advice,offtrack,actions); pptx=board_pack_pptx(ex,"NEUTRAL",q,advice,offtrack,actions)
    assert pdf[:4]==b"%PDF" and pptx[:2]==b"PK"
    stressed=stress_test(data,-0.20,0.15,0.10); assert stressed["AUM"]>0
    assert product_profitability(data)["Contribution_VND_bn"].sum()>0
    assert distribution_intelligence(data)["AUM_Share_Pct"].sum()>0.99
    assert investor_ews(data)["Risk_Score"].between(0,100).all()
    assert not compliance_cockpit(data).empty and not product_strategy(data).empty
    assert not business_plan_kpi(data).empty and not data["Macro_Indicators"].empty and not data["Operating_KPI"].empty
    assert decision_summary(data)["open"]>=1
    events=data.get("News_Events"); assert events is not None and "Date" in events.columns and not events.empty
    macro,macro_errors=get_macro_indicators(data["Macro_Indicators"],False); assert len(macro)>=15 and {"Change","Source_Status","Show_KPI","Group"}.issubset(macro.columns) and not macro_errors
    history=data.get("Macro_History"); assert history is not None and len(history)>=60 and {"Period_End","Indicator","Value"}.issubset(history.columns)
    impact=scenario_financial_impact(data); assert len(impact)>=7 and impact["Balance_Check_VND_bn"].abs().max()<0.11
    assert impact["Cash_Tie_Check_VND_bn"].abs().max()<0.01 and impact["Retained_Earnings_Check_VND_bn"].abs().max()<0.01
    comparison=three_statement_comparison(impact.iloc[0],impact.iloc[1]); assert set(comparison["Statement"])=={"Income Statement","Balance Sheet","Cash Flow Statement"} and len(comparison)>=35
    auth=configure_vnstock_auth(None); resolved=resolve_api_key(None); assert "authenticated" in auth and (resolved is None or isinstance(resolved,str))
    market,source,error=get_market_data("VNINDEX","2026-01-01","2026-03-31",fallback=True); mm=market_metrics(market); assert len(market)>20 and mm["level"]>0 and "return_ytd" in mm and not market_technical_frame(market).empty
    print(f"VALID V4.4: {len(data)} sheets | {len(perf)} funds | {len(impact)} financial scenarios | three-statement checks PASS | DQ {q['score']:.1f}/100 | market={source} | PDF {len(pdf)} | PPTX {len(pptx)}")

if __name__=="__main__": main()
