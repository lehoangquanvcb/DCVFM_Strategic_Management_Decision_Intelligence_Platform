from __future__ import annotations

import pandas as pd

from analytics import executive_metrics, fund_performance, business_plan_kpi, compliance_cockpit, product_profitability
from forensic import mna_signal


def generate_advisories(data: dict[str, pd.DataFrame], regime: str) -> pd.DataFrame:
    ex = executive_metrics(data)
    perf = fund_performance(data)
    mna = mna_signal(data)
    rows = []

    def add(priority, domain, observation, diagnosis, implication, action, owner):
        rows.append({"Priority": priority, "Domain": domain, "Observation": observation, "Diagnosis": diagnosis, "Implication": implication, "Recommended_Action": action, "Owner": owner})

    if ex["flow_3m"] < 0:
        add("HIGH", "Growth & Liquidity", f"Cumulative 3-month flow is {ex['flow_3m']:,.0f} VND bn.", "Net redemptions are offsetting market-led AUM growth.", "Persistent outflows can pressure liquidity and fee revenue.", "Launch top-client retention review; separate channel, product and performance causes.", "Distribution / CIO")
    weak = perf.nsmallest(1, "Return_3M").iloc[0]
    if pd.notna(weak["Return_3M"]) and weak["Return_3M"] < 0:
        add("HIGH", "Investment", f"{weak['Fund_Code']} has the weakest 3-month return at {weak['Return_3M']:.1%}.", "Short-horizon performance weakness requires sector/stock attribution.", "Continued weakness may raise redemption and reputation risk.", "Run attribution challenge and define a 30-day remediation/communication plan.", "CIO")
    if regime in {"RISK-OFF", "STRESS"}:
        add("HIGH", "Market Risk", f"Market regime is {regime}.", "Momentum/drawdown indicators show a less supportive risk environment.", "Equity AUM, revenues and fund liquidity buffers may be affected.", "Re-test liquidity, concentration and redemption scenarios weekly.", "CRO / CIO")
    if mna["score"] >= 50:
        add("HIGH", "Ownership & Governance", f"M&A monitoring signal is {mna['score']:.0f}/100 ({mna['level']}).", "Multiple ownership/governance clues are present, but evidence remains incomplete.", "Board and shareholder preparedness is more valuable than rumor confirmation.", "Complete evidence gaps, map regulatory approvals and prepare four ownership scenarios.", "Board Secretariat / Strategy")
    risks = data["Risk_Indicators"].copy()
    risks["Current_Score"] = pd.to_numeric(risks["Current_Score"], errors="coerce")
    for _, risk in risks.nlargest(2, "Current_Score").iterrows():
        add("MEDIUM", "Enterprise Risk", f"{risk['Risk_Type']} score is {risk['Current_Score']:.0f}/100.", str(risk.get("Trigger", "Risk trigger active.")), "Risk may escalate without accountable follow-up.", str(risk.get("Recommended_Action", "Assign and monitor mitigation.")), str(risk.get("Owner", "Risk")))
    kpi = business_plan_kpi(data)
    off = kpi[kpi["Status"] == "OFF TRACK"]
    if not off.empty:
        r = off.sort_values("Forecast_vs_Plan_Pct").iloc[0]
        add("HIGH", "Business Plan", f"{r['KPI']} forecast is {r['Forecast_vs_Plan_Pct']:.1%} versus plan.", "The driver-based forecast indicates a material plan gap.", "The gap may weaken growth, fee revenue or operating leverage.", "Assign a recovery owner and reforecast the underlying commercial drivers monthly.", str(r["Owner"]))
    exceptions = compliance_cockpit(data).query("Status == 'Action'")
    if not exceptions.empty:
        add("HIGH", "Compliance", f"{len(exceptions)} controls require action.", "Control evidence or headroom is not yet satisfactory.", "Unresolved items can create regulatory, disclosure or governance exposure.", "Close evidence gaps by due date and escalate overdue items to the responsible committee.", "CRO / Compliance")
    low_margin = product_profitability(data).nsmallest(1, "Contribution_Margin_Pct").iloc[0]
    add("MEDIUM", "Product Economics", f"{low_margin['Fund_Code']} has the lowest contribution margin at {low_margin['Contribution_Margin_Pct']:.1%}.", "Product scale, fee yield and allocated cost are not fully aligned.", "Low-margin products can dilute operating leverage despite AUM growth.", "Validate product-level cost allocation and prepare a scale/reprice/reposition decision.", "CFO / Product")
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.assign(_order=out["Priority"].map(order)).sort_values("_order").drop(columns="_order").head(8)
