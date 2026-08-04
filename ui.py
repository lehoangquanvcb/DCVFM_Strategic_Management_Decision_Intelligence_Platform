from __future__ import annotations

import streamlit as st


def inject_css():
    st.markdown("""
    <style>
    .stApp {background: radial-gradient(circle at 85% 0%, #12294a 0%, #081426 35%, #06101e 100%);}
    .block-container {max-width: 1500px; padding-top: 1.1rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {background: linear-gradient(145deg,#10233d,#0c1a2d); border:1px solid #233a57; border-radius:11px; padding:7px 10px; box-shadow:0 6px 18px rgba(0,0,0,.12); min-width:0; min-height:68px; height:auto;}
    [data-testid="stMetric"] > div {gap:.08rem;}
    [data-testid="stMetricLabel"] {color:#8FA3BF; font-size:.73rem; line-height:1.05; margin-bottom:0;}
    [data-testid="stMetricValue"] {color:#F8FAFC; font-size:clamp(1.05rem,1.15vw,1.35rem); line-height:1.05; letter-spacing:-.015em; white-space:nowrap; overflow:visible;}
    [data-testid="stMetricValue"] > div {font-size:inherit; line-height:inherit; white-space:nowrap;}
    [data-testid="stMetricDelta"] {font-size:.66rem; line-height:1.0; margin-top:1px;}
    div[data-baseweb="tab-list"] {gap:6px; flex-wrap:wrap;}
    button[data-baseweb="tab"] {background:#0c1a2d; border:1px solid #203752; border-radius:10px; padding:8px 12px;}
    button[data-baseweb="tab"][aria-selected="true"] {background:#1d4ed8;}
    .advisory-card {background:#10233d;border-left:4px solid #2F80ED;border-radius:10px;padding:14px 16px;margin:8px 0;}
    .signal-high {color:#FCA5A5;font-weight:700}.signal-watch {color:#FCD34D;font-weight:700}.muted {color:#8FA3BF}
    h1,h2,h3 {letter-spacing:-.02em;}
    </style>
    """, unsafe_allow_html=True)


def header(version: str, author: str):
    st.markdown(f"# DCVFM Strategic Intelligence & Advisory Platform")
    st.caption(f"Fund Performance • Market Intelligence • Risk Monitoring • M&A Forensics • Executive Advisory | {version} | Author: {author}")


def dataframe(df, **kwargs):
    st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)
