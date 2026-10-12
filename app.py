# -*- coding: utf-8 -*-
"""
SET Equity Terminal
===================
Risk-profiled equity research, news intelligence and portfolio construction for
the Stock Exchange of Thailand, built on cleaned 2021-2025 exchange data.

Run with:  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="SET Equity Terminal", page_icon="▮",
                   layout="wide", initial_sidebar_state="expanded")

from core import theme as T
T.apply()

from core import data as D
from core import store
from views import (welcome, overview, heatmap, rankings, screener, compare,
                   stock, news as news_view, signals, watchlist, holdings,
                   assessment, portfolio, lab)

NAV = [
    ("RESEARCH", [
        ("Market Overview", ":material/monitoring:", overview.render),
        ("Heat Map", ":material/grid_view:", heatmap.render),
        ("Rankings", ":material/leaderboard:", rankings.render),
        ("Screener", ":material/filter_alt:", screener.render),
        ("Compare", ":material/compare_arrows:", compare.render),
        ("Security Detail", ":material/candlestick_chart:", stock.render),
        ("News Intelligence", ":material/newspaper:", news_view.render),
        ("Signals", ":material/bolt:", signals.render),
        ("Watchlist", ":material/visibility:", watchlist.render),
    ]),
    ("PORTFOLIO", [
        ("My Portfolio", ":material/account_balance_wallet:", holdings.render),
        ("Risk Profile", ":material/assignment:", assessment.render),
        ("Recommended Portfolio", ":material/verified:", portfolio.render),
        ("Portfolio Lab", ":material/science:", lab.render),
    ]),
]
PAGES = {name: fn for _section, items in NAV for name, _icon, fn in items}

store.load_into_session()
st.session_state.setdefault("page", "Market Overview")
st.session_state.setdefault("entered", False)

# ---------------------------------------------------------------- landing
if not st.session_state["entered"]:
    st.markdown("<style>section[data-testid='stSidebar']{display:none !important;}"
                "#setx-sb-toggle{display:none !important;}</style>",
                unsafe_allow_html=True)
    welcome.render()
    st.stop()

# ---------------------------------------------------------------- shell
with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="mark">SET</div>'
        '<div><div class="name">Equity Terminal</div>'
        '<div class="sub">STOCK EXCHANGE OF THAILAND</div></div></div>',
        unsafe_allow_html=True)

    for section, items in NAV:
        st.markdown(f'<div class="navlabel">{section}</div>', unsafe_allow_html=True)
        for name, icon, _fn in items:
            active = st.session_state["page"] == name
            if st.button(name, key=f"nav_{name}", icon=icon,
                         type="primary" if active else "secondary",
                         width="stretch"):
                st.session_state["page"] = name
                st.rerun()

    st.divider()

    res = st.session_state.get("result")
    if res:
        st.markdown(
            f'<div class="sidecard"><div class="k">RISK PROFILE</div>'
            f'<div class="v">Cat {res["level"]} · {res["name"]}</div>'
            f'<div class="s">{res["score"]}/{res["max_score"]} pts · '
            f'equity ≤ {res["equity_cap"]*100:.0f}%</div></div>',
            unsafe_allow_html=True)
        if st.button("Retake questionnaire", key="retake", width="stretch"):
            for k in ("result", "answers"):
                st.session_state.pop(k, None)
            store.save()
            st.rerun()
    else:
        st.markdown(
            '<div class="sidecard"><div class="k">RISK PROFILE</div>'
            '<div class="v" style="font-size:0.8rem">Not set</div>'
            '<div class="s">Open Risk Profile to build<br>a personalised portfolio</div>'
            '</div>', unsafe_allow_html=True)

    hs = st.session_state.get("holdings", [])
    if hs:
        st.markdown(
            f'<div class="sidecard" style="margin-top:8px"><div class="k">PORTFOLIO</div>'
            f'<div class="v">{len(hs)} positions</div>'
            f'<div class="s">saved on this machine</div></div>',
            unsafe_allow_html=True)

    wl = st.session_state.get("watchlist", [])
    if wl:
        st.markdown(
            f'<div class="sidecard" style="margin-top:8px"><div class="k">WATCHLIST</div>'
            f'<div class="v">{len(wl)} securities</div>'
            f'<div class="s">{", ".join(wl[:4])}{" …" if len(wl) > 4 else ""}</div></div>',
            unsafe_allow_html=True)

    st.divider()
    st.markdown(
        f'<div class="sidefoot"><span class="dot"></span>DATA AS OF '
        f'{D.as_of().upper()}<br>{len(D.universe())} SECURITIES · SET / MAI<br>'
        f'{D.news_count():,} HEADLINES ANALYSED</div>', unsafe_allow_html=True)
    if st.button("← Back to start", key="back_home", width="stretch"):
        st.session_state["entered"] = False
        st.rerun()
    if store.SHARED:
        st.markdown('<div class="caption" style="margin-top:8px">Shared deployment '
                    '— your watchlist and holdings live in this browser session '
                    'only.</div>', unsafe_allow_html=True)
    st.markdown('<div class="caption" style="margin-top:8px">Educational research '
                'tool built on historical data. Not investment advice.</div>',
                unsafe_allow_html=True)

if st.session_state.pop("show_onboarding", False):
    st.session_state["onboarding_open"] = True
if st.session_state.get("onboarding_open") and not st.session_state.get("onboarded"):
    welcome.onboarding_banner()

PAGES[st.session_state["page"]]()
