from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from config import REQUIRED_SHEETS


DATE_COLUMNS = {"Date", "As_of", "Start_Date", "End_Date"}
V4_MANAGEMENT_SHEETS = {
    "Product_Profitability", "Distribution_Channels", "Investor_Behaviour",
    "Regulatory_Compliance", "Product_Strategy", "Business_Plan_KPI",
    "Decision_Tracker",
    "Macro_Indicators", "Operating_KPI",
}


def _clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").dropna(axis=1, how="all").copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.columns:
        if col in DATE_COLUMNS or col.endswith("_Date"):
            df[col] = pd.to_datetime(df[col], errors="coerce")
        if col.endswith("_Pct"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_master(source: str | Path | BinaryIO | bytes) -> dict[str, pd.DataFrame]:
    if isinstance(source, bytes):
        source = BytesIO(source)
    book = pd.ExcelFile(source, engine="openpyxl")
    return {
        name: _clean_frame(pd.read_excel(book, sheet_name=name, header=2 if name in V4_MANAGEMENT_SHEETS else 0))
        for name in book.sheet_names
    }


def validate_master(data: dict[str, pd.DataFrame]) -> list[str]:
    issues = [f"Missing required sheet: {s}" for s in REQUIRED_SHEETS if s not in data]
    for name, frame in data.items():
        if frame.empty:
            issues.append(f"Empty sheet: {name}")
    return issues


def company_profile(data: dict[str, pd.DataFrame]) -> dict:
    frame = data["Company_Profile"]
    return dict(zip(frame["Field"].astype(str), frame["Value"]))


def config_map(data: dict[str, pd.DataFrame]) -> dict:
    if "Market_Config" not in data:
        return {}
    frame = data["Market_Config"]
    return dict(zip(frame["Parameter"].astype(str), frame["Value"]))
