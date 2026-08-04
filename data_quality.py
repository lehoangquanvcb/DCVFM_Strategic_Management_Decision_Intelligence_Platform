from __future__ import annotations

from datetime import date
import pandas as pd


def quality_table(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if "Data_Quality" not in data:
        return pd.DataFrame()
    df = data["Data_Quality"].copy()
    for c in ["Required_Fields", "Populated_Fields", "Verified_Fields", "Source_Risk_1_3", "Freshness_Target_Days", "Completeness_Weight", "Verification_Weight", "Freshness_Weight"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["Last_Update"] = pd.to_datetime(df["Last_Update"], errors="coerce")
    age = (pd.Timestamp(date.today()) - df["Last_Update"]).dt.days.clip(lower=0)
    completeness = (df["Populated_Fields"] / df["Required_Fields"].replace(0, pd.NA)).fillna(0).clip(0, 1)
    verification = (df["Verified_Fields"] / df["Required_Fields"].replace(0, pd.NA)).fillna(0).clip(0, 1)
    freshness = (1 - (age - df["Freshness_Target_Days"]).clip(lower=0) / 365).clip(0, 1)
    source_quality = (4 - df["Source_Risk_1_3"]) / 3
    residual = 100 - df["Completeness_Weight"] - df["Verification_Weight"] - df["Freshness_Weight"]
    df["Quality_Score"] = (
        completeness * df["Completeness_Weight"] + verification * df["Verification_Weight"] +
        freshness * df["Freshness_Weight"] + source_quality * residual
    ).clip(0, 100)
    df["Age_Days"] = age
    df["Freshness_Status"] = age.le(df["Freshness_Target_Days"]).map({True: "Current", False: "Overdue"})
    return df.sort_values("Quality_Score")


def quality_summary(data: dict[str, pd.DataFrame]) -> dict:
    df = quality_table(data)
    if df.empty:
        return {"score": 0, "verified_pct": 0, "assumption_pct": 0, "overdue": 0}
    total = df["Required_Fields"].sum()
    return {
        "score": float(df["Quality_Score"].mean()),
        "verified_pct": float(df["Verified_Fields"].sum() / total) if total else 0,
        "assumption_pct": float(df.loc[df["Source_Type"].eq("Assumption"), "Required_Fields"].sum() / total) if total else 0,
        "overdue": int(df["Freshness_Status"].eq("Overdue").sum()),
    }


def action_summary(data: dict[str, pd.DataFrame]) -> dict:
    if "Action_Tracker" not in data:
        return {"open": 0, "overdue": 0, "avg_progress": 0}
    df = data["Action_Tracker"].copy()
    df["Due_Date"] = pd.to_datetime(df["Due_Date"], errors="coerce")
    df["Progress_Pct"] = pd.to_numeric(df["Progress_Pct"], errors="coerce").fillna(0)
    active = ~df["Status"].eq("Completed")
    return {"open": int(active.sum()), "overdue": int((active & (df["Due_Date"] < pd.Timestamp(date.today()))).sum()), "avg_progress": float(df["Progress_Pct"].mean())}

