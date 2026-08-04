from pathlib import Path

APP_NAME = "DCVFM Corporate Performance, Risk & Management Intelligence Platform"
APP_VERSION = "V4.2"
AUTHOR = "Le Hoang Quan"
ROOT = Path(__file__).resolve().parent
DEFAULT_MASTER = ROOT / "data" / "DCVFM_Corporate_Performance_Risk_Management_Intelligence_Master_V4_2.xlsx"

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
    "Portfolio", "Financials", "Shareholders", "Board_Events",
    "Competitors", "Risk_Indicators", "Scenarios", "Advisory_Rules",
    "Product_Profitability", "Distribution_Channels", "Investor_Behaviour",
    "Regulatory_Compliance", "Product_Strategy", "Business_Plan_KPI",
    "Decision_Tracker", "Macro_Indicators", "Operating_KPI",
]
