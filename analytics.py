from __future__ import annotations

import numpy as np
import pandas as pd


def latest_by_date(frame: pd.DataFrame) -> pd.DataFrame:
    if "Date" not in frame or frame.empty:
        return frame.copy()
    return frame[frame["Date"] == frame["Date"].max()].copy()


def executive_metrics(data: dict[str, pd.DataFrame]) -> dict:
    aum = data["AUM"].copy()
    flow = data["Fund_Flows"].copy()
    nav = data["NAV_History"].copy()
    latest_date = aum["Date"].max()
    current = aum[aum["Date"] == latest_date]["AUM_VND_bn"].sum()
    prior_dates = sorted(aum["Date"].dropna().unique())
    prior = aum[aum["Date"] == prior_dates[-2]]["AUM_VND_bn"].sum() if len(prior_dates) > 1 else current
    flow3 = flow[flow["Date"] >= flow["Date"].max() - pd.DateOffset(months=3)]["Net_Flow_VND_bn"].sum()
    risks = data["Risk_Indicators"]["Current_Score"].pipe(pd.to_numeric, errors="coerce")
    latest_nav = latest_by_date(nav)
    return {
        "as_of": latest_date,
        "aum": float(current),
        "aum_growth": float(current / prior - 1) if prior else 0.0,
        "flow_3m": float(flow3),
        "risk_score": float(risks.mean()),
        "funds": int(latest_nav["Fund_Code"].nunique()),
    }


def fund_performance(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    nav = data["NAV_History"].sort_values(["Fund_Code", "Date"]).copy()
    nav["Return_1M"] = nav.groupby("Fund_Code")["NAV"].pct_change(1)
    nav["Return_3M"] = nav.groupby("Fund_Code")["NAV"].pct_change(3)
    nav["Return_12M"] = nav.groupby("Fund_Code")["NAV"].pct_change(12)
    nav["Peak"] = nav.groupby("Fund_Code")["NAV"].cummax()
    nav["Drawdown"] = nav["NAV"] / nav["Peak"] - 1
    latest = latest_by_date(nav)
    return latest[["Fund_Code", "NAV", "Return_1M", "Return_3M", "Return_12M", "Drawdown", "Status"]]


def advanced_fund_analytics(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Monthly risk/return analytics with fund-specific benchmark mapping."""
    nav = data["NAV_History"].copy().sort_values(["Fund_Code", "Date"])
    master = data["Fund_Master"][["Fund_Code", "Benchmark"]].copy()
    bench = data.get("Benchmark_History", pd.DataFrame()).copy()
    if bench.empty:
        base = fund_performance(data)
        base["Alpha_3M"] = np.nan
        return base
    bench = bench.sort_values(["Benchmark", "Date"])
    bench["Benchmark_Return"] = bench.groupby("Benchmark")["Index_Level"].pct_change()
    nav["Fund_Return"] = nav.groupby("Fund_Code")["NAV"].pct_change()
    nav = nav.merge(master, on="Fund_Code", how="left").merge(
        bench[["Date", "Benchmark", "Benchmark_Return"]], on=["Date", "Benchmark"], how="left"
    )
    rows = []
    for fund, g in nav.groupby("Fund_Code"):
        g = g.sort_values("Date").copy()
        r = g["Fund_Return"].dropna()
        active = (g["Fund_Return"] - g["Benchmark_Return"]).dropna()
        downside = r[r < 0]
        navs = g["NAV"].dropna()
        drawdowns = navs / navs.cummax() - 1
        annual_return = float((1 + r).prod() ** (12 / len(r)) - 1) if len(r) else np.nan
        annual_vol = float(r.std() * np.sqrt(12)) if len(r) > 1 else np.nan
        tracking = float(active.std() * np.sqrt(12)) if len(active) > 1 else np.nan
        rows.append({
            "Fund_Code": fund,
            "NAV": float(navs.iloc[-1]) if len(navs) else np.nan,
            "Return_1M": float(r.iloc[-1]) if len(r) else np.nan,
            "Return_3M": float((1 + r.tail(3)).prod() - 1) if len(r) else np.nan,
            "Return_12M": float((1 + r.tail(12)).prod() - 1) if len(r) else np.nan,
            "Alpha_3M": float((1 + active.tail(3)).prod() - 1) if len(active) else np.nan,
            "Annualized_Return": annual_return,
            "Volatility": annual_vol,
            "Sharpe": annual_return / annual_vol if annual_vol and annual_vol > 0 else np.nan,
            "Sortino": annual_return / (float(downside.std() * np.sqrt(12)) if len(downside) > 1 else np.nan),
            "Tracking_Error": tracking,
            "Information_Ratio": float(active.mean() * 12 / tracking) if tracking and tracking > 0 else np.nan,
            "Max_Drawdown": float(drawdowns.min()) if len(drawdowns) else np.nan,
            "Positive_Month_Ratio": float((r > 0).mean()) if len(r) else np.nan,
        })
    out = pd.DataFrame(rows)
    out["Peer_Percentile"] = out["Annualized_Return"].rank(pct=True)
    return out.sort_values("Annualized_Return", ascending=False)


def aum_bridge(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    aum = data["AUM"].groupby("Date", as_index=False)["AUM_VND_bn"].sum().sort_values("Date")
    flow = data["Fund_Flows"].groupby("Date", as_index=False)["Net_Flow_VND_bn"].sum()
    out = aum.merge(flow, on="Date", how="left")
    out["Beginning_AUM"] = out["AUM_VND_bn"].shift(1)
    out["Market_and_Other_Effect"] = out["AUM_VND_bn"] - out["Beginning_AUM"] - out["Net_Flow_VND_bn"]
    return out.dropna(subset=["Beginning_AUM"])


def integrated_financial_model(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if "Financial_Drivers" not in data:
        return financial_metrics(data)
    df = data["Financial_Drivers"].copy()
    numeric = [c for c in df.columns if c.endswith("_bn") or c.endswith("_Pct")]
    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["AUM_Growth_Pct"] = df["Ending_AUM_VND_bn"].pct_change()
    df["PBT_Margin_Pct"] = df["PBT_VND_bn"] / df["Revenue_VND_bn"]
    return df


def flow_table(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    flow = data["Fund_Flows"].copy()
    end = flow["Date"].max()
    recent = flow[flow["Date"] >= end - pd.DateOffset(months=3)]
    out = recent.groupby("Fund_Code", as_index=False)["Net_Flow_VND_bn"].sum().rename(columns={"Net_Flow_VND_bn": "Net_Flow_3M_VND_bn"})
    return out.sort_values("Net_Flow_3M_VND_bn", ascending=False)


def attribution(data: dict[str, pd.DataFrame], fund: str) -> pd.DataFrame:
    if "Attribution_Input" in data and not data["Attribution_Input"].empty:
        df = data["Attribution_Input"].copy()
        df = df[df["Fund_Code"] == fund]
        for col in ["Fund_Weight_Pct", "Benchmark_Weight_Pct", "Security_Return_Pct", "Benchmark_Return_Pct"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["Contribution_Pct"] = df["Fund_Weight_Pct"] * (df["Security_Return_Pct"] - df["Benchmark_Return_Pct"])
        return df.sort_values("Contribution_Pct", ascending=False)
    portfolio = data["Portfolio"]
    df = portfolio[portfolio["Fund_Code"] == fund].copy()
    df["Contribution_Pct"] = pd.to_numeric(df["Active_Weight_Pct"], errors="coerce") / 100 * 0.02
    return df


def competitor_score(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data["Competitors"].copy()
    numeric = [c for c in df.columns if c.endswith("Score") or c in ["AUM_VND_bn", "AUM_Growth_Pct", "Performance_Score", "Product_Innovation_Score", "Distribution_Score"]]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    available = [c for c in ["Performance_Score", "Product_Innovation_Score", "Distribution_Score"] if c in df]
    if available:
        df["Competitive_Score"] = df[available].mean(axis=1) * 10
    else:
        df["Competitive_Score"] = df["AUM_VND_bn"].rank(pct=True) * 100
    return df.sort_values("Competitive_Score", ascending=False)


def financial_metrics(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data["Financials"].copy().sort_values("Year")
    for col in ["Revenue_VND_bn", "PBT_VND_bn", "NPAT_VND_bn", "Avg_AUM_VND_bn"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Revenue_AUM_Pct"] = df["Revenue_VND_bn"] / df["Avg_AUM_VND_bn"]
    df["NPAT_Margin_Pct"] = df["NPAT_VND_bn"] / df["Revenue_VND_bn"]
    df["Revenue_Growth_Pct"] = df["Revenue_VND_bn"].pct_change()
    return df


def stress_test(data: dict[str, pd.DataFrame], market_shock: float, redemption: float, fee_compression: float) -> dict:
    base = financial_metrics(data).iloc[-1]
    current_aum = executive_metrics(data)["aum"]
    stressed_aum = current_aum * (1 + market_shock) * (1 - redemption)
    revenue = float(base["Revenue_VND_bn"]) * stressed_aum / current_aum * (1 - fee_compression)
    fixed_cost = float(base["Personnel_VND_bn"] + base["Other_Opex_VND_bn"]) * 0.65
    variable_cost = float(base["Personnel_VND_bn"] + base["Other_Opex_VND_bn"]) * 0.35 * stressed_aum / current_aum
    pbt = revenue - fixed_cost - variable_cost
    return {"AUM": stressed_aum, "Revenue": revenue, "PBT": pbt, "PBT_Impact": pbt / float(base["PBT_VND_bn"]) - 1}


def product_profitability(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data["Product_Profitability"].copy()
    numeric = ["Average_AUM_VND_bn", "Effective_Fee_Pct", "Other_Revenue_VND_bn", "Direct_Cost_VND_bn", "Allocated_Cost_VND_bn"]
    for c in numeric: df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Revenue_VND_bn"] = df["Average_AUM_VND_bn"] * df["Effective_Fee_Pct"] + df["Other_Revenue_VND_bn"]
    df["Contribution_VND_bn"] = df["Revenue_VND_bn"] - df["Direct_Cost_VND_bn"] - df["Allocated_Cost_VND_bn"]
    df["Contribution_Margin_Pct"] = df["Contribution_VND_bn"] / df["Revenue_VND_bn"]
    df["Break_Even_AUM_VND_bn"] = (df["Direct_Cost_VND_bn"] + df["Allocated_Cost_VND_bn"] - df["Other_Revenue_VND_bn"]) / df["Effective_Fee_Pct"]
    return df.sort_values("Contribution_VND_bn", ascending=False)


def distribution_intelligence(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data["Distribution_Channels"].copy()
    for c in ["Gross_Sales_VND_bn", "Redemptions_VND_bn", "Ending_AUM_VND_bn", "Distribution_Cost_VND_bn", "Retention_Pct"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Net_Sales_VND_bn"] = df["Gross_Sales_VND_bn"] - df["Redemptions_VND_bn"]
    df["AUM_Share_Pct"] = df["Ending_AUM_VND_bn"] / df["Ending_AUM_VND_bn"].sum()
    df["Cost_per_Net_Sales"] = df["Distribution_Cost_VND_bn"] / df["Net_Sales_VND_bn"].replace(0, np.nan)
    return df.sort_values("Ending_AUM_VND_bn", ascending=False)


def investor_ews(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data["Investor_Behaviour"].copy()
    for c in ["Opening_AUM_VND_bn", "Subscriptions_VND_bn", "Redemptions_VND_bn", "Avg_Holding_Months", "Underperformance_3M_Pct", "Concentration_Pct"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Ending_AUM_VND_bn"] = df["Opening_AUM_VND_bn"] + df["Subscriptions_VND_bn"] - df["Redemptions_VND_bn"]
    df["Risk_Score"] = (df["Redemptions_VND_bn"] / (df["Opening_AUM_VND_bn"] + df["Subscriptions_VND_bn"]) * 50 + (-df["Underperformance_3M_Pct"]).clip(lower=0) * 800 + df["Concentration_Pct"] * 50 + np.where(df["Avg_Holding_Months"] < 6, 20, 0)).clip(0, 100)
    df["Risk_Level"] = pd.cut(df["Risk_Score"], [-1, 45, 70, 101], labels=["LOW", "MEDIUM", "HIGH"])
    return df.sort_values("Risk_Score", ascending=False)


def compliance_cockpit(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data["Regulatory_Compliance"].copy()
    for c in ["Current_Value", "Limit_Value"]: df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Headroom"] = np.where(df["Unit"].eq("days"), df["Current_Value"] - df["Limit_Value"], df["Limit_Value"] - df["Current_Value"])
    return df


def product_strategy(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data["Product_Strategy"].copy()
    cols = ["Market_Demand", "Revenue_Potential", "Distribution_Fit", "Investment_Capability", "Regulatory_Feasibility", "Cannibalisation_Risk"]
    for c in cols: df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Weighted_Score"] = df["Market_Demand"]*.2 + df["Revenue_Potential"]*.2 + df["Distribution_Fit"]*.2 + df["Investment_Capability"]*.15 + df["Regulatory_Feasibility"]*.2 - df["Cannibalisation_Risk"]*.05
    df["Decision"] = np.select([df["Weighted_Score"] >= 7.5, df["Weighted_Score"] >= 6], ["PILOT", "MONITOR"], default="HOLD")
    return df.sort_values("Weighted_Score", ascending=False)


def business_plan_kpi(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data["Business_Plan_KPI"].copy()
    for c in ["Actual_YTD", "Budget_YTD", "FY_Forecast", "FY_Plan"]: df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Variance_Abs"] = df["Actual_YTD"] - df["Budget_YTD"]
    df["Variance_Pct"] = df["Variance_Abs"] / df["Budget_YTD"].replace(0, np.nan)
    df["Forecast_vs_Plan_Pct"] = df["FY_Forecast"] / df["FY_Plan"].replace(0, np.nan) - 1
    df["Status"] = np.select([df["Forecast_vs_Plan_Pct"] >= 0, df["Forecast_vs_Plan_Pct"] >= -.05], ["ON TRACK", "WATCH"], default="OFF TRACK")
    return df


def decision_summary(data: dict[str, pd.DataFrame]) -> dict:
    df = data["Decision_Tracker"].copy()
    progress = pd.to_numeric(df["Progress_Pct"], errors="coerce").fillna(0)
    open_mask = ~df["Decision_Status"].isin(["Closed", "Rejected"])
    return {"open": int(open_mask.sum()), "high": int(((df["Priority"] == "HIGH") & open_mask).sum()), "avg_progress": float(progress[open_mask].mean() if open_mask.any() else 0)}
