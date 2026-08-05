from __future__ import annotations

import numpy as np
import pandas as pd


def scenario_financial_impact(data: dict[str, pd.DataFrame], overrides: dict | None = None, override_scenario: str | None = None) -> pd.DataFrame:
    """Translate market and management scenarios into a linked three-statement forecast."""
    assumptions = data["Scenario_Assumptions"].copy()
    amap = dict(zip(assumptions["Driver"].astype(str), assumptions["Value"]))

    def n(key, default=0.0):
        try:
            return float(amap.get(key, default))
        except (TypeError, ValueError):
            return float(default)

    beg_aum=n("Beginning AUM",140000); fee=n("Base Fee Yield",.00855)
    personnel=n("Base Personnel Cost",455); other_opex=n("Base Other Opex",360); tax_rate=n("Effective Tax Rate",.14)
    depreciation=n("Base Depreciation",40); finance_income=n("Base Finance Income",20)
    open_cash=n("Opening Cash",650); open_ar=n("Opening Receivables",250)
    open_ppe=n("Opening PPE",400); open_investments=n("Opening Investments",300); open_other=n("Opening Other Assets",200)
    open_payables=n("Opening Payables",150); open_provisions=n("Opening Provisions",100); open_other_liab=n("Opening Other Liabilities",100)
    open_share_capital=n("Opening Share Capital",1000); open_retained=n("Opening Retained Earnings",450)
    if "Opening PPE" not in amap:
        open_other=max((open_payables+open_provisions+open_other_liab+open_share_capital+open_retained)-open_cash-open_ar-open_ppe-open_investments,0)
    ar_days=n("Base AR Days",73.5); ap_days=n("Base AP Days",68.0); min_cash=n("Minimum Cash Threshold",300)
    opening_assets=open_cash+open_ar+open_ppe+open_investments+open_other
    opening_equity=open_share_capital+open_retained
    rows=[]
    for _,scenario_row in data["Scenarios"].iterrows():
        s=scenario_row.to_dict()
        if overrides and (override_scenario is None or s["Scenario"]==override_scenario):
            s.update(overrides)
        market=float(s["Market_Return_Shock_Pct"]); flow_pct=float(s["Net_Flow_Pct_Beg_AUM"]); fee_bps=float(s["Fee_Yield_Change_bps"])
        pchg=float(s["Personnel_Cost_Change_Pct"]); ochg=float(s["Other_Opex_Change_Pct"]); oneoff=float(s["One_Off_Cost_VND_bn"])
        capex=float(s["Capex_VND_bn"]); ar_delta_days=float(s["AR_Days_Change"]); payout=float(s["Dividend_Payout_Pct"])
        ap_delta_days=float(s.get("AP_Days_Change",0)); finance_income_change=float(s.get("Finance_Income_Change_Pct",0))
        debt_change=float(s.get("Debt_Change_VND_bn",0)); equity_injection=float(s.get("Equity_Injection_VND_bn",0)); investment_purchase=float(s.get("Investment_Purchase_VND_bn",0))
        net_flow=beg_aum*flow_pct; end_aum=beg_aum*(1+market)+net_flow; avg_aum=(beg_aum+end_aum)/2
        eff_fee=max(fee+fee_bps/10000,0); revenue=avg_aum*eff_fee; personnel_cost=personnel*(1+pchg); cash_other_opex=other_opex*(1+ochg)+oneoff
        finance_income_s=finance_income*(1+finance_income_change); ebit=revenue-personnel_cost-cash_other_opex-depreciation
        pbt=ebit+finance_income_s; tax=max(pbt,0)*tax_rate; npat=pbt-tax; pbt_margin=pbt/revenue if revenue else 0
        end_ar=revenue/365*max(ar_days+ar_delta_days,0); delta_ar=end_ar-open_ar
        cash_opex=personnel_cost+cash_other_opex; end_payables=cash_opex/365*max(ap_days+ap_delta_days,0); delta_payables=end_payables-open_payables
        cfo=npat+depreciation-delta_ar+delta_payables; cfi=-capex-investment_purchase
        dividends=-max(npat,0)*payout; cff=debt_change+equity_injection+dividends; net_cash_change=cfo+cfi+cff; end_cash=open_cash+net_cash_change
        end_ppe=open_ppe+capex-depreciation; end_investments=open_investments+investment_purchase
        current_assets=end_cash+end_ar; noncurrent_assets=end_ppe+end_investments+open_other; assets=current_assets+noncurrent_assets
        end_provisions=open_provisions; end_other_liab=open_other_liab; liabilities=end_payables+end_provisions+end_other_liab+debt_change
        share_capital=open_share_capital+equity_injection; retained=open_retained+npat+dividends; equity=share_capital+retained
        balance=assets-liabilities-equity; cash_tie=end_cash-(open_cash+net_cash_change); retained_tie=retained-(open_retained+npat+dividends)
        roa=npat/((opening_assets+assets)/2) if opening_assets+assets else np.nan; roe=npat/((opening_equity+equity)/2) if opening_equity+equity else np.nan
        current_liabilities=end_payables+end_provisions+end_other_liab; current_ratio=current_assets/current_liabilities if current_liabilities else np.nan
        rows.append({"Scenario":s["Scenario"],"Market_Return_Pct":market,"Net_Flow_VND_bn":net_flow,"Ending_AUM_VND_bn":end_aum,"Average_AUM_VND_bn":avg_aum,"Fee_Yield_Pct":eff_fee,
        "Revenue_VND_bn":revenue,"Personnel_VND_bn":personnel_cost,"Other_Opex_VND_bn":cash_other_opex,"Depreciation_VND_bn":depreciation,"EBIT_VND_bn":ebit,"Finance_Income_VND_bn":finance_income_s,"PBT_VND_bn":pbt,"Tax_VND_bn":tax,"NPAT_VND_bn":npat,"PBT_Margin_Pct":pbt_margin,
        "Opening_Cash_VND_bn":open_cash,"NPAT_CFS_VND_bn":npat,"Depreciation_CFS_VND_bn":depreciation,"Change_AR_VND_bn":delta_ar,"Change_Payables_VND_bn":delta_payables,"CFO_VND_bn":cfo,"Capex_VND_bn":capex,"Investment_Purchase_VND_bn":investment_purchase,"CFI_VND_bn":cfi,"Debt_Change_VND_bn":debt_change,"Equity_Injection_VND_bn":equity_injection,"Dividend_VND_bn":-dividends,"CFF_VND_bn":cff,"Net_Cash_Change_VND_bn":net_cash_change,"Ending_Cash_VND_bn":end_cash,
        "Receivables_VND_bn":end_ar,"PPE_VND_bn":end_ppe,"Investments_VND_bn":end_investments,"Other_Assets_VND_bn":open_other,"Current_Assets_VND_bn":current_assets,"Noncurrent_Assets_VND_bn":noncurrent_assets,"Total_Assets_VND_bn":assets,"Payables_VND_bn":end_payables,"Provisions_VND_bn":end_provisions,"Other_Liabilities_VND_bn":end_other_liab,"Total_Liabilities_VND_bn":liabilities,"Share_Capital_VND_bn":share_capital,"Retained_Earnings_VND_bn":retained,"Ending_Equity_VND_bn":equity,
        "ROA_Pct":roa,"ROE_Pct":roe,"Current_Ratio":current_ratio,"Cash_Headroom_VND_bn":end_cash-min_cash,"Balance_Check_VND_bn":balance,"Cash_Tie_Check_VND_bn":cash_tie,"Retained_Earnings_Check_VND_bn":retained_tie})
    out=pd.DataFrame(rows); base=out.iloc[0]
    out["Revenue_vs_Base_VND_bn"]=out["Revenue_VND_bn"]-base["Revenue_VND_bn"]
    out["PBT_vs_Base_VND_bn"]=out["PBT_VND_bn"]-base["PBT_VND_bn"]
    out["NPAT_vs_Base_VND_bn"]=out["NPAT_VND_bn"]-base["NPAT_VND_bn"]
    return out


def three_statement_comparison(base: pd.Series, scenario: pd.Series) -> pd.DataFrame:
    blocks = {
        "Income Statement": [("Revenue","Revenue_VND_bn"),("Personnel expense","Personnel_VND_bn"),("Other operating expense","Other_Opex_VND_bn"),("Depreciation","Depreciation_VND_bn"),("EBIT","EBIT_VND_bn"),("Finance income","Finance_Income_VND_bn"),("Profit before tax","PBT_VND_bn"),("Tax expense","Tax_VND_bn"),("Net profit after tax","NPAT_VND_bn")],
        "Balance Sheet": [("Cash and equivalents","Ending_Cash_VND_bn"),("Receivables","Receivables_VND_bn"),("Total current assets","Current_Assets_VND_bn"),("Property, plant and equipment","PPE_VND_bn"),("Investments","Investments_VND_bn"),("Other assets","Other_Assets_VND_bn"),("Total assets","Total_Assets_VND_bn"),("Payables","Payables_VND_bn"),("Provisions","Provisions_VND_bn"),("Other liabilities","Other_Liabilities_VND_bn"),("Total liabilities","Total_Liabilities_VND_bn"),("Share capital","Share_Capital_VND_bn"),("Retained earnings","Retained_Earnings_VND_bn"),("Total equity","Ending_Equity_VND_bn")],
        "Cash Flow Statement": [("Net profit after tax","NPAT_CFS_VND_bn"),("Depreciation add-back","Depreciation_CFS_VND_bn"),("Change in receivables","Change_AR_VND_bn"),("Change in payables","Change_Payables_VND_bn"),("Cash flow from operations","CFO_VND_bn"),("Capital expenditure","Capex_VND_bn"),("Investment purchases","Investment_Purchase_VND_bn"),("Cash flow from investing","CFI_VND_bn"),("Debt change","Debt_Change_VND_bn"),("Equity injection","Equity_Injection_VND_bn"),("Dividends paid","Dividend_VND_bn"),("Cash flow from financing","CFF_VND_bn"),("Net change in cash","Net_Cash_Change_VND_bn"),("Ending cash","Ending_Cash_VND_bn")],
    }
    rows=[]
    for statement,items in blocks.items():
        for line,key in items:
            b=float(base[key]); s=float(scenario[key]); variance=s-b
            rows.append({"Statement":statement,"Line_Item":line,"Base_VND_bn":b,"Scenario_VND_bn":s,"Variance_VND_bn":variance,"Variance_Pct":variance/abs(b) if b else np.nan})
    return pd.DataFrame(rows)
