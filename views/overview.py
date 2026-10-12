# -*- coding: utf-8 -*-
"""Market Overview — the landing screen."""
import numpy as np
import pandas as pd
import plotly.express as pex
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import tables as TB
from core import charts as CH
from core import theme as T


def _movers(f, col, n, ascending):
    d = f[f["avg_value_1y"].fillna(0) >= 10e6].dropna(subset=[col])
    d = d.sort_values(col, ascending=ascending).head(n)
    return d[["symbol", "company", "sector", "last_close", col, "avg_value_1y"]]


def render():
    T.topbar("Market Overview",
             f"SET universe · {len(D.universe())} securities · as of {D.as_of()}")

    f = D.active_factors()
    mkt = D.market_index()

    # ---------- headline stats ----------
    last = mkt["index_value"].iloc[-1]
    def idx_ret(days):
        cut = mkt["date"].max() - pd.Timedelta(days=days)
        w = mkt[mkt["date"] >= cut]
        return (w["index_value"].iloc[-1] / w["index_value"].iloc[0] - 1) * 100 if len(w) > 1 else np.nan

    adv = int((f["ret_1m"] > 0).sum())
    dec = int((f["ret_1m"] < 0).sum())
    above200 = float((f["px_vs_ma200"] > 0).mean() * 100)
    med_vol = float(f["vol_1y"].median())

    r1m, r3m, r1y = idx_ret(30), idx_ret(91), idx_ret(365)
    T.stat_cards([
        ("Market index", f"{last:,.1f}", "cap-weighted, 100 = Jan 2021", T.tone(last - 100)),
        ("1 month", f"{r1m:+.2f}%", "index return", T.tone(r1m)),
        ("3 months", f"{r3m:+.2f}%", "index return", T.tone(r3m)),
        ("1 year", f"{r1y:+.2f}%", "index return", T.tone(r1y)),
        ("Breadth 1M", f"{adv} / {dec}", "advancers vs decliners", T.tone(adv - dec)),
        ("Above MA200", f"{above200:.0f}%", "of all securities", T.tone(above200 - 50)),
        ("Median volatility", f"{med_vol:.1f}%", "annualised, 1 year", ""),
    ])

    # ---------- index chart ----------
    c1, c2 = st.columns([3, 2])
    with c1:
        T.section("Market index")
        rng = st.radio("Range", ["6M", "1Y", "3Y", "All"], index=1,
                       horizontal=True, label_visibility="collapsed",
                       key="ov_range")
        days = {"6M": 182, "1Y": 365, "3Y": 1095, "All": 99999}[rng]
        m = mkt[mkt["date"] >= mkt["date"].max() - pd.Timedelta(days=days)]
        base = m["index_value"].iloc[0]
        norm = m["index_value"] / base * 100
        up = norm.iloc[-1] >= 100
        col = T.UP if up else T.DOWN
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=m["date"], y=norm, name="Index", mode="lines",
            line=dict(color=col, width=2), fill="tozeroy",
            fillcolor=f"rgba({'38,166,154' if up else '239,83,80'},0.08)"))
        fig.add_hline(y=100, line_dash="dot", line_color=T.BORDER)
        CH.time_series(fig, height=304, y_title="Rebased to 100", legend=False)
        st.plotly_chart(fig, width="stretch")

    with c2:
        T.section("Sector performance")
        sp = D.sector_performance()
        horizon = st.radio("Horizon", ["1M", "3M", "6M", "1Y"], index=3,
                           horizontal=True, label_visibility="collapsed",
                           key="ov_sector_h")
        s = sp.dropna(subset=[horizon]).sort_values(horizon)
        fig = go.Figure(go.Bar(
            x=s[horizon], y=s["sector"], orientation="h",
            marker_color=[T.UP if v >= 0 else T.DOWN for v in s[horizon]],
            text=[f"{v:+.1f}%" for v in s[horizon]], textposition="outside",
            textfont=dict(family=T.MONO, size=10),
            hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>"))
        fig.add_vline(x=0, line_color=T.BORDER)
        fig.update_layout(height=max(300, 22 * len(s)), showlegend=False,
                          xaxis_title=f"Cap-weighted return {horizon} (%)",
                          yaxis_title="", margin=dict(l=8, r=40, t=10, b=8))
        st.plotly_chart(fig, width="stretch")

    # ---------- breadth ----------
    T.section("How many stocks are taking part",
              "The cumulative advance-decline line counts how many securities rise versus fall each day. When it diverges from the index, the move is being carried by a shrinking number of names — something a capitalisation-weighted index hides.")
    ad = D.advance_decline()
    if not ad.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ad["date"], y=ad["ad_line"], name="A/D line",
                                 line=dict(color=T.ACCENT, width=1.8)))
        mi = mkt.set_index("date")["index_value"].reindex(ad["date"]).values
        mi = mi / mi[0] * 100
        fig.add_trace(go.Scatter(x=ad["date"], y=mi, name="Market index",
                                 line=dict(color=T.MUTED, width=1.4, dash="dash"),
                                 yaxis="y2"))
        fig.update_layout(height=304,
                          yaxis=dict(title="Cumulative advances − declines"),
                          yaxis2=dict(title="Index", overlaying="y", side="right",
                                      showgrid=False))
        CH.time_series(fig, height=304, ranges=False)
        st.plotly_chart(fig, width="stretch")

    # ---------- movers ----------
    T.section("Biggest moves")
    st.markdown('<div class="caption">Restricted to names trading at least '
                '10M THB per day, so the lists are actionable rather than noise.</div>',
                unsafe_allow_html=True)
    period = st.radio("Period", ["1 week", "1 month", "3 months", "1 year"],
                      index=1, horizontal=True, key="ov_mover_p")
    col = {"1 week": "ret_1w", "1 month": "ret_1m",
           "3 months": "ret_3m", "1 year": "ret_1y"}[period]

    t1, t2, t3, t4 = st.tabs(["Top gainers", "Top losers",
                              "Highest volume", "Near 52-week high"])
    def grid(d, valcol, label, key):
        if d.empty:
            st.info("No securities match.")
            return
        v = pd.DataFrame({
            "Symbol": d["symbol"], "Company": d["company"].str.title(),
            "Sector": d["sector"], "Price": d["last_close"].round(2),
            label: d[valcol].round(2),
            "Avg value (THB)": d["avg_value_1y"].round(0)})
        p = TB.grid(v, height=392, spark=True, select=True,
                    key=f"ov_{key}", money_cols=["Avg value (THB)"])
        if p:
            TB.open_security(p)
    with t1:
        grid(_movers(f, col, 15, False), col, f"{period} (%)", "gain")
    with t2:
        grid(_movers(f, col, 15, True), col, f"{period} (%)", "lose")
    with t3:
        d = f.dropna(subset=["avg_value_20d"]).nlargest(15, "avg_value_20d")
        grid(d.assign(avg_value_1y=d["avg_value_20d"]), col, f"{period} (%)", "active")
    with t4:
        d = f[(f["avg_value_1y"].fillna(0) >= 10e6)].dropna(subset=["pct_from_52w_high"])
        grid(d.nlargest(15, "pct_from_52w_high"), "pct_from_52w_high",
             "From 52W high (%)", "near_high")

    # ---------- market heat map ----------
    T.section("Market heat map")
    h1, h2, h3 = st.columns([2, 2, 2])
    hm_period = h1.selectbox("Colour by", ["1 week", "1 month", "3 months",
                                           "6 months", "1 year"],
                             index=1, key="ov_hm_p")
    hm_group = h2.selectbox("Group by", ["Industry → Sector", "Sector only",
                                         "Size tier → Sector"], key="ov_hm_g")
    hm_min = h3.selectbox("Minimum liquidity", ["All", "1M THB/day", "10M THB/day",
                                                "50M THB/day"], index=1, key="ov_hm_l")
    ccol = {"1 week": "ret_1w", "1 month": "ret_1m", "3 months": "ret_3m",
            "6 months": "ret_6m", "1 year": "ret_1y"}[hm_period]
    minv = {"All": 0, "1M THB/day": 1e6, "10M THB/day": 1e7, "50M THB/day": 5e7}[hm_min]

    hm = f.dropna(subset=["market_cap", ccol]).copy()
    hm = hm[(hm["market_cap"] > 0) & (hm["avg_value_1y"].fillna(0) >= minv)]
    if hm.empty:
        st.info("No securities match that liquidity filter.")
    else:
        # cap the colour scale at the 5th/95th percentile so a couple of extreme
        # movers do not wash out every other tile
        lim = float(np.nanpercentile(hm[ccol].abs(), 95))
        lim = max(lim, 1.0)
        hm["ret_disp"] = hm[ccol].clip(-lim, lim)
        hm["label"] = hm["symbol"] + "<br>" + hm[ccol].map(lambda v: f"{v:+.1f}%")
        path = {"Industry → Sector": ["industry", "sector", "label"],
                "Sector only": ["sector", "label"],
                "Size tier → Sector": ["size_tier", "sector", "label"]}[hm_group]
        fig = pex.treemap(
            hm, path=[pex.Constant("SET / mai")] + path, values="market_cap",
            color="ret_disp", color_continuous_scale=[T.DOWN, "#2A3441", T.UP],
            color_continuous_midpoint=0, range_color=[-lim, lim],
            custom_data=["symbol", "company", ccol, "market_cap", "vol_1y"])
        fig.update_traces(
            marker=dict(line=dict(color=T.BG, width=1)),
            textfont=dict(family=T.MONO, size=11),
            tiling=dict(pad=2),
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>"
                          "Return %{customdata[2]:.2f}%<br>"
                          "Market cap %{customdata[3]:,.0f}<br>"
                          "Volatility %{customdata[4]:.1f}%<extra></extra>")
        fig.update_layout(height=620, margin=dict(t=10, l=4, r=4, b=4),
                          coloraxis_colorbar=dict(
                              title=dict(text=f"{hm_period} %", font=dict(size=10)),
                              tickfont=dict(family=T.MONO, size=10), thickness=12))
        st.plotly_chart(fig, width="stretch")
        up = int((hm[ccol] > 0).sum())
        T.caption(f"Tile area is market capitalisation, colour is the {hm_period.lower()} "
                  f"return. {len(hm):,} securities shown · {up:,} up, {len(hm)-up:,} down. "
                  f"Colour is capped at ±{lim:.0f}% so a few extreme movers do not "
                  f"flatten the rest. Click a block to zoom in, click the header to go back.")

    # ---------- risk map ----------
    T.section("Risk against return")
    m = f.dropna(subset=["vol_1y", "ret_1y"]).copy()
    m = m[m["avg_value_1y"].fillna(0) >= 5e6]
    m["size"] = m["market_cap"].fillna(m["market_cap"].median()).clip(lower=1)
    fig = go.Figure()
    for i, (sec, g) in enumerate(m.groupby("sector")):
        fig.add_trace(go.Scatter(
            x=g["vol_1y"], y=g["ret_1y"], mode="markers", name=sec,
            marker=dict(size=np.sqrt(g["size"]) / 3200 + 5, opacity=0.75,
                        color=T.SERIES[i % len(T.SERIES)],
                        line=dict(width=0)),
            customdata=np.stack([g["symbol"], g["company"].str.title()], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>"
                          "Volatility %{x:.1f}%<br>Return %{y:.1f}%<extra></extra>"))
    fig.add_hline(y=0, line_dash="dot", line_color=T.BORDER)
    fig.update_layout(height=460, xaxis_title="Annualised volatility 1Y (%)",
                      yaxis_title="Total return 1Y (%)",
                      legend=dict(font=dict(size=10)))
    st.plotly_chart(fig, width="stretch")
    T.caption("Upper left is the desirable quadrant — higher return for less volatility. "
              "Bubble size is market capitalisation.")
