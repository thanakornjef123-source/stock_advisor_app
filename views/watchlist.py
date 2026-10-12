# -*- coding: utf-8 -*-
"""Watchlist — a personal shortlist that persists across the session."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import store
from core import tables as TB
from core import theme as T


def render():
    T.topbar("Watchlist", f"Session shortlist · as of {D.as_of()}")
    f = D.active_factors()
    syms = D.universe()
    wl = st.session_state.setdefault("watchlist", [])

    c1, c2 = st.columns([4, 1])
    add = c1.multiselect("Add securities", [s for s in syms if s not in wl],
                         key="wl_add")
    if c2.button("Add", width="stretch") and add:
        st.session_state["watchlist"] = sorted(set(wl) | set(add)); store.save()
        st.rerun()

    if not wl:
        st.info("Your watchlist is empty. Add securities here, or send them across "
                "from the Screener or a security page.")
        return

    d = f[f["symbol"].isin(wl)].copy()

    up = int((d["ret_1m"] > 0).sum())
    T.stat_cards([
        ("Securities", str(len(d)), "on watch", ""),
        ("Up on 1 month", f"{up} / {len(d)}", "advancers", T.tone(up - (len(d) - up))),
        ("Median 1Y return", f"{d['ret_1y'].median():+.1f}%", "price only",
         T.tone(d["ret_1y"].median())),
        ("Median volatility", f"{d['vol_1y'].median():.1f}%", "annualised 1Y", ""),
        ("Flagged", str(int(d["news_red_flag"].sum())), "elevated negative news",
         "down" if d["news_red_flag"].sum() else ""),
    ])

    view = pd.DataFrame({
        "Symbol": d["symbol"], "Company": d["company"].str.title(),
        "Sector": d["sector"], "Price": d["last_close"].round(2),
        "1W (%)": d["ret_1w"].round(2), "1M (%)": d["ret_1m"].round(2),
        "3M (%)": d["ret_3m"].round(2), "1Y (%)": d["ret_1y"].round(2),
        "Vol 1Y (%)": d["vol_1y"].round(1), "Beta": d["beta_1y"].round(2),
        "P/E": d["pe"].round(1), "Yield (%)": d["dividend_yield"].round(2),
        "RSI": d["rsi14"].round(0), "vs MA200 (%)": d["px_vs_ma200"].round(1),
        "Neg news 2Y": d["risk_news_2y"],
    }).sort_values("1M (%)", ascending=False)
    picked = TB.grid(view, height=min(560, 44 + 34 * len(view)), spark=True,
                     select=True, key="wl_grid")
    if picked:
        TB.open_security(picked)

    a, b, c = st.columns([1, 1, 3])
    a.download_button("Download CSV", d.to_csv(index=False).encode("utf-8"),
                      "watchlist.csv", "text/csv", width="stretch")
    rm = b.selectbox("Remove", ["—"] + wl, key="wl_rm", label_visibility="collapsed")
    if rm != "—":
        st.session_state["watchlist"] = [s for s in wl if s != rm]; store.save()
        st.rerun()
    if c.button("Clear watchlist"):
        st.session_state["watchlist"] = []; store.save()
        st.rerun()

    T.section("Relative performance")
    cm = D.close_matrix()
    cols = [s for s in wl if s in cm.columns]
    if cols:
        rng = st.radio("Range", ["1M", "3M", "6M", "1Y", "3Y"], index=3,
                       horizontal=True, key="wl_rng")
        days = {"1M": 30, "3M": 91, "6M": 182, "1Y": 365, "3Y": 1095}[rng]
        sub = cm.loc[cm.index >= cm.index.max() - pd.Timedelta(days=days), cols]
        fig = go.Figure()
        for i, s in enumerate(cols):
            ser = sub[s].dropna()
            if ser.empty:
                continue
            fig.add_trace(go.Scatter(x=ser.index, y=(ser / ser.iloc[0] - 1) * 100,
                                     name=s, line=dict(color=T.SERIES[i % len(T.SERIES)],
                                                       width=1.6)))
        fig.add_hline(y=0, line_dash="dot", line_color=T.BORDER)
        fig.update_layout(height=400, yaxis_title="Cumulative return (%)",
                          hovermode="x unified")
        st.plotly_chart(fig, width="stretch")

    T.section("Heat map — 1-month return")
    hm = d.dropna(subset=["ret_1m"]).sort_values("ret_1m", ascending=False)
    if not hm.empty:
        fig = go.Figure(go.Bar(
            x=hm["symbol"], y=hm["ret_1m"],
            marker_color=[T.UP if v >= 0 else T.DOWN for v in hm["ret_1m"]],
            text=[f"{v:+.1f}%" for v in hm["ret_1m"]], textposition="outside",
            textfont=dict(family=T.MONO, size=10)))
        fig.add_hline(y=0, line_color=T.BORDER)
        fig.update_layout(height=320, yaxis_title="1-month return (%)")
        st.plotly_chart(fig, width="stretch")
