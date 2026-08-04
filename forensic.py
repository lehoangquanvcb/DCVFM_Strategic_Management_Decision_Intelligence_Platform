from __future__ import annotations

import pandas as pd


def evidence_registry(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if "M&A_Evidence" in data:
        df = data["M&A_Evidence"].copy()
        for c in ["Evidence_Strength_1_3", "Materiality_1_3", "Direction_Minus1_1"]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        df["Weighted_Points"] = df["Evidence_Strength_1_3"] * df["Materiality_1_3"] * df["Direction_Minus1_1"] * 3
        return df.sort_values("Date", ascending=False)
    df = data["M&A_Events"].copy()
    df["Weighted_Points"] = pd.to_numeric(df.get("Signal_Points", 0), errors="coerce").fillna(0)
    return df


def mna_signal(data: dict[str, pd.DataFrame]) -> dict:
    df = evidence_registry(data)
    raw = float(df["Weighted_Points"].sum())
    evidence_count = int((df["Weighted_Points"].abs() > 0).sum())
    # Deliberately conservative calibration: evidence completeness matters, but
    # rumor-like items must not turn a monitoring signal into pseudo-probability.
    score = max(0.0, min(100.0, 20 + raw * 0.35 + min(evidence_count, 10) * 1.5))
    if score >= 70:
        level = "HIGH / ELEVATED"
    elif score >= 50:
        level = "ELEVATED"
    elif score >= 30:
        level = "WATCH"
    else:
        level = "LOW"
    return {"score": score, "level": level, "raw_points": raw, "evidence_count": evidence_count}


def buyer_scenarios(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if "Ownership_Scenarios" not in data:
        return pd.DataFrame()
    df = data["Ownership_Scenarios"].copy()
    cols = ["Strategic_Fit", "Financial_Capacity", "Regulatory_Fit", "Distribution_Synergy", "Asset_Mgmt_Capability", "Evidence_Strength", "Deal_Feasibility"]
    weights = [0.20, 0.15, 0.10, 0.15, 0.20, 0.10, 0.10]
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Weighted_Score"] = sum(df[c] * w for c, w in zip(cols, weights)) * 10
    return df.sort_values("Weighted_Score", ascending=False)


def entity_network(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return data.get("Entity_Network", pd.DataFrame()).copy()


def regulatory_scenarios(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    df = data.get("Regulatory_Scenarios", pd.DataFrame()).copy()
    if not df.empty:
        df["Stake_Acquired_Pct"] = pd.to_numeric(df["Stake_Acquired_Pct"], errors="coerce")
    return df
