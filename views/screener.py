# -*- coding: utf-8 -*-
"""Screener — the main self-service research tool."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import store
from core import tables as TB
from core import theme as T
from core.screener import (FIELDS, NUMERIC_FILTERS, DEFAULT_COLUMNS, PRESETS,
                           apply_filters, format_table)

GROUPS = ["Momentum", "Risk", "Valuation", "Quality", "Growth",
          "Technical", "Liquidity", "Size", "News", "Factor score"]


def _defaults():
    return {"numeric": {"avg_value_1y": (1e6, None)},
            "sectors": [], "markets": [], "buckets": [],
            "liquidity": [], "size": [], "exclude_flagged": True,
            "require_financials": False, "min_history": 250, "search": "",
            "sort": "overall_score", "ascending": False}


def render():
    f = D.active_factors()
    st.session_state.setdefault("scr", _defaults())
    S = st.session_state["scr"]

    T.topbar("Screener",
             f"{len(f)} securities · {len(FIELDS)} metrics · as of {D.as_of()}")

    # ------------------------------------------------ preset row
    c1, c2 = st.columns([2, 3])
    with c1:
        preset = st.selectbox("Start from a ready-made screen", list(PRESETS), key="scr_preset")
    with c2:
        p = PRESETS.get(preset) or {}
        if p.get("desc"):
            st.markdown(f'<div class="caption" style="padding-top:26px">{p["desc"]}</div>',
                        unsafe_allow_html=True)
    b1, b2, b3 = st.columns([1, 1, 6])
    if b1.button("Apply preset", width="stretch", disabled=not p):
        S.update(_defaults())
        S["numeric"] = dict(p.get("filters", {}))
        S["exclude_flagged"] = p.get("exclude_flagged", True)
        S["sort"] = p.get("sort", "overall_score")
        S["ascending"] = p.get("ascending", False)
        st.session_state.pop("scr_sort", None)
        st.session_state.pop("scr_dir", None)
        st.rerun()
    if b2.button("Reset all", width="stretch"):
        st.session_state["scr"] = _defaults()
        st.rerun()

    # ------------------------------------------------ sidebar filters
    with st.sidebar:
        st.markdown("### Filters")
        S["search"] = st.text_input("Search by symbol or company name", S["search"])

        st.markdown("**Classification**")
        S["sectors"] = st.multiselect("Sector", sorted(f["sector"].unique()),
                                      default=S["sectors"])
        S["markets"] = st.multiselect("Market", sorted(f["market"].unique()),
                                      default=S["markets"])
        S["size"] = st.multiselect("Size", ["Large", "Mid", "Small", "Micro"],
                                   default=S["size"])
        S["buckets"] = st.multiselect("Risk band", sorted(f["risk_bucket"].unique()),
                                      default=S["buckets"])
        S["liquidity"] = st.multiselect("Liquidity", ["Liquid", "Normal", "Thin", "Illiquid"],
                                        default=S["liquidity"])

        st.markdown("**Quality gates**")
        lo = (S["numeric"].get("avg_value_1y") or (None, None))[0]
        tradeable = st.checkbox(
            "Only names trading at least 1M THB a day", lo is not None,
            help="Just over half the listed universe turns over less than this. "
                 "They are still here — this only decides whether the screen "
                 "starts with them included.")
        if tradeable:
            S["numeric"]["avg_value_1y"] = (1e6, (S["numeric"].get("avg_value_1y") or (None, None))[1])
        elif lo is not None:
            hi = (S["numeric"].get("avg_value_1y") or (None, None))[1]
            if hi is None:
                S["numeric"].pop("avg_value_1y", None)
            else:
                S["numeric"]["avg_value_1y"] = (None, hi)
        S["exclude_flagged"] = st.checkbox(
            "Exclude names flagged for negative news", S["exclude_flagged"])
        S["require_financials"] = st.checkbox(
            "Require reported financial statements", S["require_financials"])
        S["min_history"] = st.slider("Minimum trading history (days)",
                                     0, 1200, S["min_history"], 10)

        st.markdown("**Numeric criteria**")
        st.markdown('<div class="caption">Leave a box empty to ignore that bound.</div>',
                    unsafe_allow_html=True)
        for grp in GROUPS:
            keys = [k for k in NUMERIC_FILTERS if FIELDS[k][1] == grp]
            if not keys:
                continue
            active = sum(1 for k in keys if k in S["numeric"])
            label = f"{grp}" + (f"  ({active})" if active else "")
            with st.expander(label, expanded=bool(active)):
                for k in keys:
                    lab, _g, unit, dp, _h = FIELDS[k]
                    cur = S["numeric"].get(k, (None, None))
                    # Streamlit requires value/step to share a numeric type,
                    # so normalise whatever a preset supplied to float.
                    cur = (None if cur[0] is None else float(cur[0]),
                           None if cur[1] is None else float(cur[1]))
                    a, b = st.columns(2)
                    lo = a.number_input(f"{lab} min", value=cur[0], step=1.0,
                                        format="%.4g", key=f"lo_{k}",
                                        label_visibility="visible")
                    hi = b.number_input("max", value=cur[1], step=1.0,
                                        format="%.4g", key=f"hi_{k}",
                                        label_visibility="visible")
                    if lo is None and hi is None:
                        S["numeric"].pop(k, None)
                    else:
                        S["numeric"][k] = (lo, hi)

    # ------------------------------------------------ run
    res = apply_filters(f, S["numeric"], S["sectors"], S["markets"], S["buckets"],
                        S["liquidity"], S["size"], S["exclude_flagged"],
                        S["require_financials"], S["min_history"], S["search"])

    active_n = len(S["numeric"]) + sum(bool(S[k]) for k in
                                       ["sectors", "markets", "buckets", "liquidity", "size"])
    chips = "".join(
        T.badge(f"{FIELDS[k][0]} "
                f"{'≥' + format(v[0], '.4g') if v[0] is not None else ''}"
                f"{' ' if v[0] is not None and v[1] is not None else ''}"
                f"{'≤' + format(v[1], '.4g') if v[1] is not None else ''}", "accent")
        for k, v in S["numeric"].items())
    st.markdown(
        f'<div class="panel"><b>{len(res):,}</b> of {len(f):,} securities match '
        f'<span style="color:{T.MUTED}">· {active_n} active filter'
        f'{"s" if active_n != 1 else ""}</span><br>{chips}</div>',
        unsafe_allow_html=True)

    if res.empty:
        st.warning("No securities match these criteria. Relax a bound or reset the filters.")
        return

    # ------------------------------------------------ table
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        cols = st.multiselect(
            "Columns", [c for c in f.columns if c in FIELDS or c in
                        ("symbol", "company", "sector", "industry", "market",
                         "risk_bucket", "liquidity_tier", "size_tier", "latest_period")],
            default=DEFAULT_COLUMNS, key="scr_cols")
    with c2:
        sort_opts = [c for c in cols if c in FIELDS] or ["overall_score"]
        want = S.get("sort", "overall_score")
        idx = sort_opts.index(want) if want in sort_opts else 0
        sort_by = st.selectbox("Sort by", sort_opts, index=idx,
                               format_func=lambda c: FIELDS[c][0] if c in FIELDS else c,
                               key="scr_sort")
        S["sort"] = sort_by
    with c3:
        order_opts = ["Descending", "Ascending"]
        desc = st.selectbox("Order", order_opts,
                            index=1 if S.get("ascending") else 0, key="scr_dir")
        S["ascending"] = (desc == "Ascending")

    if sort_by in res.columns:
        res = res.sort_values(sort_by, ascending=(desc == "Ascending"), na_position="last")

    show = format_table(res, cols)
    picked = TB.grid(show, height=470, spark=True, select=True, key="scr_grid",
                     money_cols=[c for c in show.columns
                                 if "THB" in str(c) or "cap" in str(c).lower()])
    if picked:
        TB.open_security(picked)
    T.caption("Click any row to open that security. Coloured cells are scaled to "
              "the spread of the column, so a strong number reads at a glance.")

    d1, d2 = st.columns([1, 5])
    d1.download_button("Download CSV", res.to_csv(index=False).encode("utf-8"),
                       "screen_results.csv", "text/csv", width="stretch")
    d2.markdown(f'<div class="caption" style="padding-top:8px">'
                f'Exports all {len(res)} matching rows with every metric, '
                f'not just the visible columns.</div>', unsafe_allow_html=True)

    # ------------------------------------------------ send to other tools
    T.section("Send these stocks to another tool")
    picked = st.multiselect("Pick stocks", res["symbol"].tolist(),
                            default=res["symbol"].head(5).tolist(), key="scr_send")
    a, b, c = st.columns(3)
    if a.button("Compare these", width="stretch") and picked:
        st.session_state["compare_symbols"] = picked[:8]
        st.success(f"{len(picked[:8])} securities queued — open **Compare**.")
    if b.button("Add to watchlist", width="stretch") and picked:
        wl = set(st.session_state.get("watchlist", []))
        wl.update(picked)
        st.session_state["watchlist"] = sorted(wl); store.save()
        st.success(f"Watchlist now holds {len(wl)} securities.")
    if c.button("Build portfolio from these", width="stretch") and picked:
        st.session_state["sim_symbols"] = picked[:15]
        st.success("Loaded into **Portfolio Lab**.")

    # ------------------------------------------------ visual analysis
    T.section("Charts")
    v1, v2 = st.tabs(["Scatter", "Factor profile"])
    numeric_opts = [c for c in FIELDS if c in res.columns]
    with v1:
        x1, x2, x3 = st.columns(3)
        xk = x1.selectbox("X axis", numeric_opts,
                          index=numeric_opts.index("vol_1y") if "vol_1y" in numeric_opts else 0,
                          format_func=lambda c: FIELDS[c][0], key="sc_x")
        yk = x2.selectbox("Y axis", numeric_opts,
                          index=numeric_opts.index("ret_1y") if "ret_1y" in numeric_opts else 1,
                          format_func=lambda c: FIELDS[c][0], key="sc_y")
        ck = x3.selectbox("Colour by", ["sector", "risk_bucket", "size_tier", "liquidity_tier"],
                          key="sc_c")
        m = res.dropna(subset=[xk, yk])
        if m.empty:
            st.info("Not enough data for these two metrics.")
        else:
            fig = go.Figure()
            for i, (g, gg) in enumerate(m.groupby(ck)):
                fig.add_trace(go.Scatter(
                    x=gg[xk], y=gg[yk], mode="markers", name=str(g),
                    marker=dict(size=8, opacity=0.8,
                                color=T.SERIES[i % len(T.SERIES)], line=dict(width=0)),
                    customdata=np.stack([gg["symbol"], gg["company"].str.title()], axis=-1),
                    hovertemplate="<b>%{customdata[0]}</b> %{customdata[1]}<br>"
                                  f"{FIELDS[xk][0]}: %{{x:.2f}}<br>"
                                  f"{FIELDS[yk][0]}: %{{y:.2f}}<extra></extra>"))
            fig.update_layout(height=470, xaxis_title=FIELDS[xk][0],
                              yaxis_title=FIELDS[yk][0])
            st.plotly_chart(fig, width="stretch")
    with v2:
        top = res.nlargest(min(12, len(res)), sort_by if sort_by in res.columns else "overall_score")
        cols_f = ["value_score", "quality_score", "momentum_score",
                  "lowvol_score", "income_score", "growth_score"]
        z = top[cols_f].values
        fig = go.Figure(go.Heatmap(
            z=z, x=[FIELDS[c][0].replace(" score", "") for c in cols_f],
            y=top["symbol"], colorscale=[[0, T.DOWN], [0.5, T.PANEL_2], [1, T.UP]],
            zmid=50, zmin=0, zmax=100, text=np.round(z, 0),
            texttemplate="%{text:.0f}",
            textfont=dict(family=T.MONO, size=10),
            colorbar=dict(title="", tickfont=dict(size=10))))
        fig.update_layout(height=max(260, 30 * len(top)))
        st.plotly_chart(fig, width="stretch")
        T.caption("Each cell is a percentile rank against the whole market — "
                  "100 means best in class on that factor.")
