from pathlib import Path

APP_NAME = "DCVFM Strategic Management & Decision Intelligence Platform"
APP_VERSION = "V4.1"
AUTHOR = "Le Hoang Quan"
ROOT = Path(__file__).resolve().parent
DEFAULT_MASTER = ROOT / "data" / "DCVFM_Strategic_Management_Decision_Intelligence_Master_V4.xlsx"

COLORS = {
    "navy": "#081426",
    "blue": "#2F80ED",
    "teal": "#17C3B2",
    "green": "#22C55E",
    "amber": "#F59E0B",
    "red": "#EF4444",
    "muted": "#8FA3BF",
    "panel": "#101F35",
}

REQUIRED_SHEETS = [
    "Company_Profile", "Fund_Master", "AUM", "Fund_Flows", "NAV_History",
    "Portfolio", "Financials", "Shareholders", "Board_Events", "M&A_Events",
    "Competitors", "Risk_Indicators", "Scenarios", "Advisory_Rules",
    "Product_Profitability", "Distribution_Channels", "Investor_Behaviour",
    "Regulatory_Compliance", "Product_Strategy", "Business_Plan_KPI",
    "Valuation_Scenarios", "Decision_Tracker",
]
