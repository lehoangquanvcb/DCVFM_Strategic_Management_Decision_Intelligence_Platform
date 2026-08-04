from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent; sys.path.insert(0,str(ROOT))
from config import DEFAULT_MASTER
from data_loader import load_master,validate_master
from analytics import advanced_fund_analytics,aum_bridge,executive_metrics,integrated_financial_model,stress_test,product_profitability,distribution_intelligence,investor_ews,compliance_cockpit,product_strategy,business_plan_kpi,valuation_scenarios,decision_summary
from data_quality import action_summary,quality_summary,quality_table
from forensic import buyer_scenarios,entity_network,mna_signal,regulatory_scenarios
from advisory import generate_advisories
from export_pack import board_pack_pdf,board_pack_pptx
from market_data import get_market_data,market_metrics
from vnstock_auth import configure_vnstock_auth,resolve_api_key

def main():
    data=load_master(DEFAULT_MASTER); issues=validate_master(data); assert not issues,issues
    assert len(data)>=38, f"Expected >=38 sheets, got {len(data)}"
    ex=executive_metrics(data); assert ex["aum"]>0 and ex["funds"]>=5
    perf=advanced_fund_analytics(data); assert len(perf)>=5 and perf["Sharpe"].notna().any()
    bridge=aum_bridge(data); assert not bridge.empty
    model=integrated_financial_model(data); assert len(model)>=5 and model["NPAT_VND_bn"].iloc[-1]>0
    q=quality_summary(data); assert 0<=q["score"]<=100 and not quality_table(data).empty
    assert action_summary(data)["open"]>=1
    signal=mna_signal(data); assert 0<=signal["score"]<=100
    assert not buyer_scenarios(data).empty and not entity_network(data).empty and not regulatory_scenarios(data).empty
    advice=generate_advisories(data,"NEUTRAL"); assert not advice.empty
    pdf=board_pack_pdf(ex,{},"NEUTRAL",signal,q,advice); pptx=board_pack_pptx(ex,"NEUTRAL",signal,q,advice)
    assert pdf[:4]==b"%PDF" and pptx[:2]==b"PK"
    stressed=stress_test(data,-0.20,0.15,0.10); assert stressed["AUM"]>0
    assert product_profitability(data)["Contribution_VND_bn"].sum()>0
    assert distribution_intelligence(data)["AUM_Share_Pct"].sum()>0.99
    assert investor_ews(data)["Risk_Score"].between(0,100).all()
    assert not compliance_cockpit(data).empty and not product_strategy(data).empty
    assert not business_plan_kpi(data).empty and not valuation_scenarios(data).empty
    assert decision_summary(data)["open"]>=1
    auth=configure_vnstock_auth(None); resolved=resolve_api_key(None); assert "authenticated" in auth and (resolved is None or isinstance(resolved,str))
    market,source,error=get_market_data("VNINDEX","2026-01-01","2026-03-31",fallback=True); assert len(market)>20 and market_metrics(market)["level"]>0
    print(f"VALID V4.0: {len(data)} sheets | {len(perf)} funds | DQ {q['score']:.1f}/100 | M&A {signal['score']:.1f}/100 | market={source} | auth_available={auth['available']} | PDF {len(pdf)} | PPTX {len(pptx)}")

if __name__=="__main__": main()
