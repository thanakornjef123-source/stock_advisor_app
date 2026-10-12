# -*- coding: utf-8 -*-
"""Compare — side-by-side analysis of up to eight securities."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import charts as CH
from core import theme as T
from core.screener import FIELDS

ROWS = [
    ("last_close", "Price"), ("market_cap", "Market cap"),
    ("ret_1m", "Return 1M"), ("ret_3m", "Return 3M"), ("ret_6m", "Return 6M"),
    ("ret_1y", "Return 1Y"), ("cagr", "CAGR since 2021"),
    ("vol_1y", "Volatility 1Y"), ("vol_all", "Volatility since 2021"),
    ("beta_1y", "Beta 1Y"), ("max_dd_1y", "Max drawdown 1Y"),
    ("sharpe_1y", "Sharpe 1Y"),
    ("pe", "P/E"), ("pbv", "P/BV"), ("dividend_yield", "Dividend yield"),
    ("roe", "ROE"), ("roa", "ROA"), ("de", "Debt / equity"),
    ("net_margin", "Net margin"),
    ("revenue_growth_yoy", "Revenue growth YoY"),
    ("profit_growth_yoy", "Profit growth YoY"),
    ("rsi14", "RSI (14)"), ("px_vs_ma200", "Price vs MA200"),
    ("avg_value_1y", "Avg daily value 1Y"),
    ("risk_news_2y", "Negative news 2Y"),
    ("overall_score", "Overall score"),
]


def render():
    T.topbar("Compare Securities", f"Up to 8 at a time · as of {D.as_of()}")
    f = D.active_factors()
    syms = D.universe()
    default = [s for s in st.session_state.get("compare_symbols",
                                               ["PTT", "ADVANC", "CPALL"]) if s in syms]
    sel = st.multiselect("Securities", syms, default=default[:8],
                         max_selections=8, key="cmp_sel")
    if not sel:
        st.info("Select at least one security.")
        return
    st.session_state["compare_symbols"] = sel

    cm = D.close_matrix()
    cols = [s for s in sel if s in cm.columns]
    if not cols:
        st.warning("No price history for the selected securities.")
        return

    c1, c2 = st.columns([2, 2])
    rng = c1.radio("Range", ["3M", "6M", "1Y", "2Y", "3Y", "All"], index=2,
                   horizontal=True, key="cmp_rng")
    mode = c2.radio("Display", ["Cumulative return", "Price", "Drawdown"],
                    horizontal=True, key="cmp_mode")
    days = {"3M": 91, "6M": 182, "1Y": 365, "2Y": 730, "3Y": 1095, "All": 99999}[rng]
    start = cm.index.max() - pd.Timedelta(days=days)
    sub = cm.loc[cm.index >= start, cols].dropna(how="all")

    fig = go.Figure()
    if mode == "Cumulative return":
        for i, c in enumerate(cols):
            s = sub[c].dropna()
            if s.empty:
                continue
            fig.add_trace(go.Scatter(x=s.index, y=(s / s.iloc[0] - 1) * 100, name=c,
                                     line=dict(color=T.SERIES[i % len(T.SERIES)], width=1.8)))
        mk = D.market_index()
        mk = mk[mk["date"] >= start]
        if len(mk) > 1:
            cum = (1 + mk["ret"].fillna(0)).cumprod()
            fig.add_trace(go.Scatter(x=mk["date"], y=(cum / cum.iloc[0] - 1) * 100,
                                     name="Market index",
                                     line=dict(color=T.MUTED, width=1.4, dash="dash")))
        fig.add_hline(y=0, line_dash="dot", line_color=T.BORDER)
        fig.update_layout(yaxis_title="Cumulative return (%)")
    elif mode == "Price":
        for i, c in enumerate(cols):
            fig.add_trace(go.Scatter(x=sub.index, y=sub[c], name=c,
                                     line=dict(color=T.SERIES[i % len(T.SERIES)], width=1.8)))
        fig.update_layout(yaxis_title="Close (THB)")
    else:
        for i, c in enumerate(cols):
            s = sub[c].dropna()
            if s.empty:
                continue
            fig.add_trace(go.Scatter(x=s.index, y=(s / s.cummax() - 1) * 100, name=c,
                                     line=dict(color=T.SERIES[i % len(T.SERIES)], width=1.5)))
        fig.update_layout(yaxis_title="Drawdown from peak (%)")
    CH.time_series(fig, height=430, ranges=True,
                   zero_line=mode != "Price")
    st.plotly_chart(fig, width="stretch")

    # ---------------- metric table ----------------
    T.section("Side-by-side metrics")
    r = f[f["symbol"].isin(cols)].set_index("symbol").reindex(cols)
    best_note = []
    table = {}
    for key, label in ROWS:
        if key not in r.columns:
            continue
        vals = pd.to_numeric(r[key], errors="coerce")
        dp = FIELDS.get(key, (None, None, None, 2, None))[3]
        table[label] = [T.fmt_big(v) if key in ("market_cap", "avg_value_1y")
                        else (f"{v:,.{dp}f}" if pd.notna(v) else "—") for v in vals]
        hib = FIELDS.get(key, (None, None, None, None, None))[4]
        if hib is not None and vals.notna().any():
            best = vals.idxmax() if hib else vals.idxmin()
            best_note.append((label, best))
    t = pd.DataFrame(table, index=cols).T
    t.index.name = "Metric"
    st.dataframe(t, width="stretch", height=min(760, 36 * len(t) + 40))

    if best_note:
        wins = pd.Series([b for _, b in best_note]).value_counts()
        chips = "".join(T.badge(f"{s}: best on {n} metrics",
                                "up" if i == 0 else "neutral")
                        for i, (s, n) in enumerate(wins.items()))
        st.markdown(chips, unsafe_allow_html=True)
        T.caption("Counts how often each security ranks best among those selected, "
                  "on metrics where a clear direction exists. A convenience summary, "
                  "not a recommendation.")

    # ---------------- correlation ----------------
    if len(cols) > 1:
        T.section("How closely they move together")
        rets = sub.pct_change().dropna(how="all")
        if len(rets) > 30:
            corr = rets.corr().round(2)
            fig = go.Figure(go.Heatmap(
                z=corr.values, x=corr.columns, y=corr.index,
                colorscale=[[0, T.DOWN], [0.5, T.PANEL_2], [1, T.ACCENT]],
                zmid=0, zmin=-1, zmax=1, text=corr.values,
                texttemplate="%{text:.2f}",
                textfont=dict(family=T.MONO, size=11),
                colorbar=dict(tickfont=dict(size=10))))
            fig.update_layout(height=110 + 52 * len(cols))
            st.plotly_chart(fig, width="stretch")
            avg = corr.values[np.triu_indices(len(cols), 1)].mean()
            T.caption(f"Average pairwise correlation {avg:.2f}. Values close to 1 mean "
                      "the securities move together, so holding several of them adds "
                      "less diversification than the count suggests.")
        else:
            st.info("Not enough overlapping history to compute correlation.")

    # ---------------- factor radar ----------------
    T.section("Score breakdown")
    fcols = ["value_score", "quality_score", "momentum_score",
             "lowvol_score", "income_score", "growth_score"]
    labels = ["Value", "Quality", "Momentum", "Low vol", "Income", "Growth"]
    fig = go.Figure()
    for i, s in enumerate(cols):
        rr = f[f["symbol"] == s]
        if rr.empty:
            continue
        v = [float(rr.iloc[0][c]) if pd.notna(rr.iloc[0][c]) else 50.0 for c in fcols]
        fig.add_trace(go.Scatterpolar(r=v + [v[0]], theta=labels + [labels[0]],
                                      name=s, fill="toself",
                                      opacity=0.45,
                                      line=dict(color=T.SERIES[i % len(T.SERIES)], width=1.8)))
    fig.update_layout(height=470, polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(range=[0, 100], gridcolor=T.GRID,
                        tickfont=dict(family=T.MONO, size=9, color=T.MUTED)),
        angularaxis=dict(gridcolor=T.GRID, tickfont=dict(size=11, color=T.TEXT))))
    st.plotly_chart(fig, width="stretch")
