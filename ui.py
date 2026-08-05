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
    .platform-header {margin:0 0 .55rem 0;}
    .platform-title {color:#F8FAFC; font-size:clamp(1.55rem,2.15vw,2.05rem); font-weight:750; line-height:1.12; letter-spacing:-.025em; margin:0;}
    .platform-author {color:#AAB8CB; font-size:1rem; font-weight:500; line-height:1.25; margin-top:.22rem;}
    .tabs-note {color:#B8C7DB; background:rgba(16,35,61,.72); border:1px solid #233A57; border-left:3px solid #2F80ED; border-radius:8px; font-size:.88rem; line-height:1.35; padding:.48rem .72rem; margin:.1rem 0 .55rem 0;}
    @media (max-width: 768px) {
        .block-container {padding-left:.65rem; padding-right:.65rem; padding-top:.65rem;}
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] [data-testid="stMetric"]) {
            display:grid !important;
            grid-template-columns:repeat(2,minmax(0,1fr)) !important;
            gap:.48rem !important;
            align-items:stretch !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] [data-testid="stMetric"]) > div[data-testid="stColumn"] {
            width:auto !important;
            min-width:0 !important;
            flex:unset !important;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"]:nth-child(odd):last-child) > div[data-testid="stColumn"]:last-child {
            grid-column:1 / -1;
        }
        [data-testid="stMetric"] {height:100%; min-height:64px; padding:7px 9px;}
        [data-testid="stMetricLabel"] {font-size:.68rem;}
        [data-testid="stMetricValue"] {font-size:1rem;}
        [data-testid="stMetricDelta"] {font-size:.61rem;}
        .platform-header {margin-bottom:.45rem;}
        .platform-title {font-size:1.38rem; line-height:1.16;}
        .platform-author {font-size:.92rem; margin-top:.2rem;}
        .tabs-note {font-size:.8rem; padding:.42rem .58rem;}
    }
    </style>
    """, unsafe_allow_html=True)


def header(version: str, author: str):
    st.markdown(
        f"""
        <div class="platform-header">
            <div class="platform-title">Fund Performance, Risk &amp; Management Intelligence Platform</div>
            <div class="platform-author">Author: {author}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def tabs_note():
    st.markdown(
        '<div class="tabs-note">This platform includes multiple tabs. Click each tab below to view detailed information.</div>',
        unsafe_allow_html=True,
    )


def dataframe(df, **kwargs):
    st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)
