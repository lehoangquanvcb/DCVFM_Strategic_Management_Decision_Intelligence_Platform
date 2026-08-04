from __future__ import annotations

from datetime import date
from typing import Callable

import numpy as np
import pandas as pd


INDICATOR_SPECS = {
    "CPI YoY": {"unit": "%", "field": "cpi_total"},
    "Credit Growth YTD": {"unit": "%", "field": "credit_growth"},
    "M2 Growth YoY": {"unit": "%", "field": "total"},
    "USD/VND": {"unit": "VND/USD", "field": "USD"},
    "Policy Rate": {"unit": "%", "field": "refinance"},
    "10Y Government Bond Yield": {"unit": "%", "field": "close"},
}


def _macro_client():
    """Prefer the authenticated Sponsor package; community builds are optional."""
    try:
        from vnstock_data import Macro
        return Macro(), "Vnstock Data Live"
    except Exception as sponsor_error:
        try:
            from vnstock import Macro
            return Macro(), "Vnstock Live"
        except Exception as community_error:
            raise RuntimeError(
                f"Macro API unavailable ({type(sponsor_error).__name__}; "
                f"{type(community_error).__name__})"
            ) from community_error


def _invoke(call: Callable, variants: list[dict]) -> pd.DataFrame:
    errors = []
    for kwargs in variants:
        try:
            result = call(**kwargs)
            if isinstance(result, pd.DataFrame) and not result.empty:
                return result
            errors.append("empty response")
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
    raise RuntimeError(" | ".join(errors[-3:]))


def _clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    time_col = next((c for c in ["time", "date", "report_time", "Date", "As_of"] if c in df.columns), None)
    if time_col is None:
        raise ValueError("Macro response has no time column")
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
    return df.dropna(subset=[time_col]).sort_values(time_col).rename(columns={time_col: "time"})


def _series(df: pd.DataFrame, field: str) -> pd.DataFrame:
    aliases = {
        "USD": ["USD", "usd", "usd_vnd", "USD/VND", "close"],
        "refinance": ["refinance", "refinancing", "refinancing_rate", "value", "close"],
        "credit_growth": ["credit_growth", "growth", "value"],
        "cpi_total": ["cpi_total", "cpi", "growth", "value"],
        "total": ["total", "m2", "money_supply", "value"],
        "close": ["close", "value", "yield"],
    }
    column = next((c for c in aliases[field] if c in df.columns), None)
    if column is None:
        raise ValueError(f"Macro response has no supported '{field}' field")
    out = df[["time", column]].rename(columns={column: "value"}).copy()
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    return out.dropna(subset=["value"]).drop_duplicates("time", keep="last")


def _latest_pair(values: pd.DataFrame, yoy: bool = False) -> tuple[pd.Timestamp, float, float]:
    if values.empty:
        raise ValueError("No usable macro observations")
    current_row = values.iloc[-1]
    current = float(current_row["value"])
    if yoy:
        cutoff = current_row["time"] - pd.DateOffset(months=12)
        prior = values.loc[values["time"] <= cutoff]
        if prior.empty or float(prior.iloc[-1]["value"]) == 0:
            raise ValueError("Insufficient history to calculate YoY growth")
        base = float(prior.iloc[-1]["value"])
        previous_cutoff = cutoff - pd.DateOffset(months=1)
        prior_previous = values.loc[values["time"] <= previous_cutoff]
        previous_base = float(prior_previous.iloc[-1]["value"]) if not prior_previous.empty else base
        previous_level = float(values.iloc[-2]["value"]) if len(values) > 1 else current
        previous = (previous_level / previous_base - 1.0) * 100.0 if previous_base else np.nan
        current = (current / base - 1.0) * 100.0
    else:
        previous = float(values.iloc[-2]["value"]) if len(values) > 1 else current
    return pd.Timestamp(current_row["time"]), current, previous


def _fetch_one(client, indicator: str) -> tuple[pd.Timestamp, float, float]:
    economy = client.economy()
    currency = client.currency()
    if indicator == "CPI YoY":
        raw = _invoke(economy.cpi, [{"period": "month", "length": 24}, {"period": "month"}, {}])
        return _latest_pair(_series(_clean(raw), "cpi_total"))
    if indicator == "Credit Growth YTD":
        raw = _invoke(economy.credit, [{"period": "month", "length": 24}, {"period": "month"}, {}])
        return _latest_pair(_series(_clean(raw), "credit_growth"))
    if indicator == "M2 Growth YoY":
        raw = _invoke(economy.money_supply, [{"period": "month", "length": 30}, {"period": "month"}, {}])
        return _latest_pair(_series(_clean(raw), "total"), yoy=True)
    if indicator == "USD/VND":
        raw = _invoke(currency.exchange_rate, [{"period": "day", "length": 15}, {"period": "month", "length": 3}, {}])
        stamp, current, previous = _latest_pair(_series(_clean(raw), "USD"))
        # The unified Macro schema may express FX in thousand VND.
        if 10 <= current < 100:
            current, previous = current * 1000.0, previous * 1000.0
        return stamp, current, previous
    if indicator == "Policy Rate":
        raw = _invoke(currency.policy_rate, [{"start": "2020-01-01", "end": date.today().isoformat()}, {"length": 30}, {}])
        return _latest_pair(_series(_clean(raw), "refinance"))
    if indicator == "10Y Government Bond Yield":
        global_domain = getattr(client, "global")
        raw = _invoke(global_domain.bond_yield, [{"market": "VN", "tenor": "10Y"}])
        return _latest_pair(_series(_clean(raw), "close"))
    raise KeyError(indicator)


def get_macro_indicators(master: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Overlay live Vnstock observations on the Master, with row-level fallback."""
    fallback = master.copy()
    for col in ["Current_Value", "Previous_Value"]:
        fallback[col] = pd.to_numeric(fallback.get(col), errors="coerce")
    fallback["Indicator"] = fallback["Indicator"].astype(str).str.strip()
    rows = []
    errors = []
    try:
        client, source_label = _macro_client()
    except Exception as exc:
        client, source_label = None, ""
        errors.append(str(exc))

    for _, base in fallback.iterrows():
        row = base.to_dict()
        indicator = row["Indicator"]
        if client is not None and indicator in INDICATOR_SPECS:
            try:
                stamp, current, previous = _fetch_one(client, indicator)
                row.update({
                    "As_of": stamp,
                    "Current_Value": current,
                    "Previous_Value": previous,
                    "Unit": INDICATOR_SPECS[indicator]["unit"],
                    "Source_Status": source_label,
                    "Source_Reference": "Vnstock Macro API",
                })
            except Exception as exc:
                row["Source_Status"] = "Master fallback"
                errors.append(f"{indicator}: {type(exc).__name__}: {exc}")
        rows.append(row)

    out = pd.DataFrame(rows)
    out["Change"] = out["Current_Value"] - out["Previous_Value"]
    out["Direction"] = np.select([out["Change"] > 0, out["Change"] < 0], ["Up", "Down"], default="Flat")
    return out, errors
