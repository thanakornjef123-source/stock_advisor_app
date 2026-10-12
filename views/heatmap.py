# -*- coding: utf-8 -*-
"""Heat Map — the whole market on one screen."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import tables as TB
from core import theme as T

PERIODS = {"1 week": "ret_1w", "1 month": "ret_1m", "3 months": "ret_3m",
           "6 months": "ret_6m", "1 year": "ret_1y"}
SIZE_BY = {"Market cap": "market_cap", "Daily turnover": "avg_value_1y",
           "Equal weight": None}

# diverging red -> grey -> green, the convention every terminal uses
SCALE = [[0.0, "#B3251F"], [0.25, "#7A2320"], [0.5, "#2A313C"],
         [0.75, "#1E6E5E"], [1.0, "#1B9E7A"]]


def _tree(d, period_col, size_col, group):
    d = d.dropna(subset=[period_col]).copy()
    if size_col:
        d = d[d[size_col].notna() & (d[size_col] > 0)]
        d["value"] = d[size_col]
    else:
        d["value"] = 1.0
    if d.empty:
        return None

    labels, parents, values, colors, text, custom = [], [], [], [], [], []
    root = "Market"
    labels.append(root); parents.append(""); values.append(0)
    colors.append(0.0); text.append(""); custom.append(["", "", ""])

    for gname, gg in d.groupby(group):
        w = gg["value"].sum()
        ret = float((gg[period_col] * gg["value"]).sum() / w) if w > 0 else 0.0
        labels.append(gname); parents.append(root); values.append(0)
        colors.append(ret); text.append(f"{ret:+.1f}%")
        custom.append([gname, f"{len(gg)} securities", f"{ret:+.2f}%"])
        for r in gg.itertuples():
            labels.append(f"{r.symbol}|{gname}")
            parents.append(gname)
            values.append(float(r.value))
            colors.append(float(getattr(r, period_col)))
            text.append(f"<b>{r.symbol}</b><br>{getattr(r, period_col):+.1f}%")
            custom.append([str(r.company).title(), gname,
                           f"{getattr(r, period_col):+.2f}%"])

    lim = float(np.nanpercentile(np.abs(d[period_col]), 92)) or 1.0
    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values, branchvalues="remainder",
        marker=dict(colors=colors, colorscale=SCALE, cmid=0, cmin=-lim, cmax=lim,
                    line=dict(width=1, color=T.BG),
                    colorbar=dict(title="", tickfont=dict(family=T.MONO, size=10),
                                  thickness=12, len=0.6)),
        text=text, textinfo="text",
        textfont=dict(family=T.MONO, size=11, color="#FFFFFF"),
        customdata=custom,
        hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}"
                      "<br>Return %{customdata[2]}<extra></extra>",
        tiling=dict(pad=2), pathbar=dict(visible=True, thickness=18)))
    fig.update_layout(height=720, margin=dict(t=28, l=4, r=4, b=4))
    return fig


def render():
    f = D.active_factors()
    T.topbar("Market Heat Map", f"{len(f)} securities · as of {D.as_of()}")

    c1, c2, c3, c4 = st.columns([1.4, 1.3, 1.3, 2])
    period = c1.selectbox("Period", list(PERIODS), index=1, key="hm_p")
    size_by = c2.selectbox("Rectangle size", list(SIZE_BY), key="hm_s")
    group = c3.selectbox("Group by", ["industry", "sector"], key="hm_g")
    min_liq = c4.select_slider(
        "Minimum daily turnover", [0, 1e6, 5e6, 10e6, 50e6, 100e6], value=1e6,
        format_func=lambda v: "All" if v == 0 else T.fmt_big(v) + " THB", key="hm_l")

    col = PERIODS[period]
    d = f[f["avg_value_1y"].fillna(0) >= min_liq]
    d = d[d[group] != "Unclassified"]

    up = int((d[col] > 0).sum()); dn = int((d[col] < 0).sum())
    med = float(d[col].median())
    T.stat_cards([
        ("Securities shown", f"{len(d):,}", f"turnover ≥ {T.fmt_big(min_liq)}", ""),
        ("Advancing", f"{up:,}", f"{up/max(len(d),1)*100:.0f}% of shown", "up"),
        ("Declining", f"{dn:,}", f"{dn/max(len(d),1)*100:.0f}% of shown", "down"),
        ("Median return", f"{med:+.2f}%", period, T.tone(med)),
        ("Best", f"{d.loc[d[col].idxmax(), 'symbol']}" if d[col].notna().any() else "—",
         f"{d[col].max():+.1f}%" if d[col].notna().any() else "", "up"),
        ("Worst", f"{d.loc[d[col].idxmin(), 'symbol']}" if d[col].notna().any() else "—",
         f"{d[col].min():+.1f}%" if d[col].notna().any() else "", "down"),
    ])

    fig = _tree(d, col, SIZE_BY[size_by], group)
    if fig is None:
        st.info("No securities match this filter.")
        return
    st.plotly_chart(fig, width="stretch")
    T.caption("Rectangle size is the chosen weighting, colour is the return over the "
              "selected period. Click a group to zoom in, then use the trail at the "
              "top to come back out. Colour is clipped at the 92nd percentile so a "
              "single outlier does not wash out the rest of the map.")

    # ------------------------------------------------ sector matrices
    st.markdown("### Sector matrices")
    t1, t2, t3 = st.tabs(["Returns by period", "Factor scores", "Drill down"])

    with t1:
        rows = []
        for sec, g in f[f["sector"] != "Unclassified"].groupby("sector"):
            w = g["market_cap"].fillna(0)
            row = {"Sector": sec, "n": len(g)}
            for lab, c in PERIODS.items():
                m = g[c].notna() & (w > 0)
                row[lab] = float((g.loc[m, c] * w[m]).sum() / w[m].sum()) if m.any() else np.nan
            rows.append(row)
        m = pd.DataFrame(rows).set_index("Sector").sort_values("1 year", ascending=False)
        z = m[list(PERIODS)].values.astype(float)
        lim = float(np.nanpercentile(np.abs(z), 95)) or 1.0
        fig = go.Figure(go.Heatmap(
            z=z, x=list(PERIODS), y=m.index, colorscale=SCALE, zmid=0,
            zmin=-lim, zmax=lim, text=np.round(z, 1), texttemplate="%{text:+.1f}",
            textfont=dict(family=T.MONO, size=10),
            hovertemplate="%{y}<br>%{x}: %{z:+.2f}%<extra></extra>",
            colorbar=dict(thickness=12, tickfont=dict(size=10))))
        fig.update_layout(height=max(420, 26 * len(m)), margin=dict(l=8, t=20))
        st.plotly_chart(fig, width="stretch")
        T.caption("Cap-weighted return, so a sector is not dragged around by its "
                  "smallest constituents.")

    with t2:
        fcols = ["value_score", "quality_score", "momentum_score", "lowvol_score",
                 "income_score", "growth_score", "nlp_sentiment_score"]
        names = ["Value", "Quality", "Momentum", "Low vol", "Income", "Growth", "News"]
        avail = [c for c in fcols if c in f.columns]
        nm = [n for c, n in zip(fcols, names) if c in f.columns]
        m = (f[f["sector"] != "Unclassified"].groupby("sector")[avail].median()
             .sort_values(avail[0], ascending=False))
        z = m.values.astype(float)
        fig = go.Figure(go.Heatmap(
            z=z, x=nm, y=m.index,
            colorscale=[[0, "#B3251F"], [0.5, "#2A313C"], [1, "#1B9E7A"]],
            zmid=50, zmin=15, zmax=85, text=np.round(z, 0), texttemplate="%{text:.0f}",
            textfont=dict(family=T.MONO, size=10),
            hovertemplate="%{y}<br>%{x}: %{z:.1f}<extra></extra>",
            colorbar=dict(thickness=12, tickfont=dict(size=10))))
        fig.update_layout(height=max(420, 26 * len(m)), margin=dict(l=8, t=20))
        st.plotly_chart(fig, width="stretch")
        T.caption("Median percentile rank of the securities in each sector. 50 is the "
                  "market median, so this shows where each sector's character lies.")

    with t3:
        secs = sorted(f[f["sector"] != "Unclassified"]["sector"].unique())
        sec = st.selectbox("Sector", secs, key="hm_sec")
        g = f[f["sector"] == sec].copy()
        w = g["market_cap"].fillna(0)
        cw = (float((g["ret_1y"] * w).sum() / w.sum())
              if w.sum() > 0 and g["ret_1y"].notna().any() else np.nan)
        T.stat_cards([
            ("Securities", str(len(g)), sec, ""),
            ("Total market cap", T.fmt_big(g["market_cap"].sum()), "THB", ""),
            ("Cap-weighted 1Y", f"{cw:+.2f}%" if pd.notna(cw) else "—", "return", T.tone(cw)),
            ("Median volatility", f"{g['vol_1y'].median():.1f}%", "annualised", ""),
            ("Median P/E", f"{g['pe'].median():.1f}" if g['pe'].notna().any() else "—", "", ""),
            ("Median yield", f"{g['dividend_yield'].median():.2f}%"
             if g['dividend_yield'].notna().any() else "—", "", ""),
        ])
        v = pd.DataFrame({
            "Symbol": g["symbol"], "Company": g["company"].str.title(),
            "Price": g["last_close"].round(2),
            "1M (%)": g["ret_1m"].round(2), "1Y (%)": g["ret_1y"].round(2),
            "Vol (%)": g["vol_1y"].round(1), "P/E": g["pe"].round(1),
            "P/BV": g["pbv"].round(2), "Yield (%)": g["dividend_yield"].round(2),
            "ROE (%)": g["roe"].round(1),
            "News rank": g.get("nlp_sentiment_score", pd.Series(index=g.index)).round(0),
            "Overall": g["overall_score"].round(1),
            "Market cap": g["market_cap"].round(0),
        }).sort_values("Market cap", ascending=False)
        picked = TB.grid(v, height=440, spark=True, select=True, key="hm_grid",
                         money_cols=["Market cap"])
        if picked:
            TB.open_security(picked)
        st.download_button(f"Download {sec} CSV", g.to_csv(index=False).encode("utf-8"),
                           f"sector_{sec.replace(' ', '_')}.csv", "text/csv")
