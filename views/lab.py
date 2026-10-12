# -*- coding: utf-8 -*-
"""Portfolio Lab — build a book by hand and test it against history."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import charts as CH
from core import theme as T
from core import backtest as B
from core import backtest as bt
from core.recommend import build as build_reco


def _weights_ui(sel, f):
    mode = st.radio("How to split the money",
                    ["Equal weight", "Inverse volatility", "Market cap", "Manual",
                     "Optimised"],
                    horizontal=True, key="lab_wmode")
    if mode == "Optimised":
        c1, c2 = st.columns([2, 1])
        obj = c1.selectbox("Objective",
                           ["Minimum variance", "Maximum Sharpe", "Risk parity"],
                           key="lab_obj")
        cap = c2.slider("Maximum weight per holding (%)", 10, 100, 35, 5,
                        key="lab_maxw") / 100.0
        key = {"Minimum variance": "min_variance", "Maximum Sharpe": "max_sharpe",
               "Risk parity": "risk_parity"}[obj]
        cm = D.close_matrix()
        end = cm.index.max()
        w = bt.optimise(cm, sel, end - pd.Timedelta(days=1095), end, key, cap)
        if w:
            T.caption("Solved from the sample covariance of daily returns over the "
                      "past three years. Long only, capped per holding. The "
                      "covariance is estimated from the same history the result is "
                      "then measured against, so treat it as a description of that "
                      "period rather than a forecast.")
            return w
        st.warning("Not enough overlapping history to optimise; using equal weight.")
        return {s: 1 / len(sel) for s in sel}
    r = f[f["symbol"].isin(sel)].set_index("symbol").reindex(sel)
    if mode == "Equal weight":
        w = pd.Series(1.0, index=sel)
    elif mode == "Inverse volatility":
        w = 1 / r["vol_all"].fillna(r["vol_all"].median()).clip(lower=1)
    elif mode == "Market cap":
        w = r["market_cap"].fillna(r["market_cap"].median()).clip(lower=1)
    else:
        cols = st.columns(min(len(sel), 5))
        raw = {}
        for i, s in enumerate(sel):
            raw[s] = cols[i % len(cols)].number_input(
                s, 0.0, 100.0, round(100 / len(sel), 1), 1.0, key=f"lab_w_{s}")
        w = pd.Series(raw)
    w = w.astype(float)
    if w.sum() <= 0:
        w = pd.Series(1.0, index=sel)
    return (w / w.sum()).to_dict()


def render():
    T.topbar("Portfolio Lab",
             f"Construct · weight · test against history · as of {D.as_of()}")
    st.markdown(
        '<div class="panel">Build any book you like, choose how it is weighted, '
        'then measure it against the cap-weighted market index over a window you '
        'choose. Everything here is computed from actual closing prices.</div>',
        unsafe_allow_html=True)

    f = D.active_factors()
    cm = D.close_matrix()
    syms = [s for s in D.universe() if s in cm.columns]

    src = st.radio("Starting cash",
                   ["Choose securities", "Use my recommended portfolio", "Use my watchlist"],
                   horizontal=True, key="lab_src")

    if src == "Use my recommended portfolio":
        res = st.session_state.get("result")
        if not res:
            st.warning("No risk profile yet. Complete the questionnaire, or pick "
                       "securities manually.")
            return
        picks = build_reco(f, res, 10)
        if picks.empty:
            st.error("No eligible securities for that profile.")
            return
        sel = [s for s in picks["symbol"] if s in cm.columns]
        weights = dict(zip(picks["symbol"], picks["weight"]))
        weights = {k: v for k, v in weights.items() if k in sel}
        st.success(f"Loaded category {res['level']} {res['name']} portfolio: "
                   + ", ".join(f"{k} {v*100:.0f}%" for k, v in weights.items()))
    else:
        if src == "Use my watchlist":
            default = [s for s in st.session_state.get("watchlist", []) if s in syms]
            if not default:
                st.warning("Watchlist is empty. Add securities from the Screener or "
                           "a security page first.")
                return
        else:
            default = [s for s in st.session_state.get("sim_symbols",
                       ["PTT", "ADVANC", "CPALL", "TISCO"]) if s in syms]
        sel = st.multiselect("Holdings", syms, default=default[:20], key="lab_sel")
        if not sel:
            st.info("Select at least one security.")
            return
        st.session_state["sim_symbols"] = sel
        weights = _weights_ui(sel, f)

    if not weights:
        st.info("Nothing to simulate.")
        return

    c1, c2, c3, c4 = st.columns(4)
    lo = cm.index.min().to_pydatetime()
    hi = cm.index.max().to_pydatetime()
    start = c1.date_input("Start date", value=max(lo, hi - pd.Timedelta(days=1095)),
                          min_value=lo, max_value=hi, key="lab_start")
    end = c2.date_input("End date", value=hi, min_value=lo, max_value=hi, key="lab_end")
    initial = c3.number_input("Initial capital (THB)", 10_000, 1_000_000_000,
                              1_000_000, 100_000, key="lab_cap")
    reb = c4.selectbox("Rebalancing", ["Buy and hold", "Monthly"], key="lab_reb")

    with st.expander("Fees and tax"):
        f1, f2, f3 = st.columns(3)
        comm = f1.number_input("Commission incl. VAT (% per side)", 0.0, 2.0,
                               0.157, 0.01, key="lab_comm",
                               help="Thai online brokerage is commonly around "
                                    "0.15% plus VAT. Charged on entry, on exit and "
                                    "on the traded portion of each rebalance.")
        stax = f2.number_input("Additional levy on sales (%)", 0.0, 2.0, 0.0, 0.01,
                               key="lab_stax")
        f3.markdown('<div class="caption" style="padding-top:26px">Dividends are '
                    'still excluded, so a high-yield book is understated either '
                    'way.</div>', unsafe_allow_html=True)

    if pd.Timestamp(start) >= pd.Timestamp(end):
        st.error("Start date must be earlier than the end date.")
        return

    sim = B.simulate(cm, weights, start, end, float(initial),
                     "monthly" if reb == "Monthly" else "hold",
                     commission_pct=float(comm), sell_tax_pct=float(stax))
    if sim.empty:
        st.error("Not enough overlapping price history in this window. Try a later "
                 "start date, or remove recently listed securities.")
        return
    bm = B.benchmark(D.market_index(), start, end, float(initial))

    mp = B.metrics(sim.set_index("date")["value"])
    final = sim["value"].iloc[-1]
    T.stat_cards([
        ("Final value", f"{final:,.0f}", "THB", T.tone(final - initial)),
        ("Total return", f"{mp['Total return']:+.2f}%", "over the window", T.tone(mp["Total return"])),
        ("CAGR", f"{mp['CAGR']:+.2f}%", "annualised", T.tone(mp["CAGR"])),
        ("Volatility", f"{mp['Volatility']:.2f}%", "annualised", ""),
        ("Max drawdown", f"{mp['Max drawdown']:.2f}%", "peak to trough", "down"),
        ("Sharpe", f"{mp['Sharpe']:.2f}", "rf 2%", T.tone(mp["Sharpe"])),
        ("Sortino", f"{mp['Sortino']:.2f}" if pd.notna(mp["Sortino"]) else "—", "downside only", ""),
        ("Positive days", f"{mp['Positive days']:.1f}%", "of trading days", ""),
    ])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sim["date"], y=sim["value"], name="Portfolio",
                             line=dict(color=T.ACCENT, width=2)))
    if not bm.empty:
        fig.add_trace(go.Scatter(x=bm["date"], y=bm["value"], name="Market index",
                                 line=dict(color=T.MUTED, width=1.5, dash="dash")))
    fig.add_hline(y=initial, line_dash="dot", line_color=T.BORDER)
    CH.time_series(fig, height=384, y_title="Value (THB)")
    st.plotly_chart(fig, width="stretch")

    t1, t2, t3 = st.tabs(["Drawdown", "Contribution", "Versus benchmark"])
    with t1:
        fig = go.Figure(go.Scatter(x=sim["date"], y=sim["drawdown_pct"],
                                   fill="tozeroy", name="Portfolio",
                                   line=dict(color=T.DOWN, width=1),
                                   fillcolor="rgba(239,83,80,0.18)"))
        if not bm.empty:
            fig.add_trace(go.Scatter(x=bm["date"], y=bm["drawdown_pct"],
                                     name="Market index",
                                     line=dict(color=T.MUTED, width=1, dash="dash")))
        fig.update_layout(height=300, yaxis_title="Drawdown from peak (%)")
        st.plotly_chart(fig, width="stretch")
        T.caption("This is the loss an investor would actually have lived through. "
                  "For most people it is a better description of risk than volatility.")
    with t2:
        contrib = B.contribution(cm, weights, start, end, float(initial))
        if contrib.empty:
            st.info("No contribution data.")
        else:
            cc = contrib.sort_values("contribution_pct")
            fig = go.Figure(go.Bar(
                x=cc["contribution_pct"], y=cc["symbol"], orientation="h",
                marker_color=[T.UP if v >= 0 else T.DOWN for v in cc["contribution_pct"]],
                text=[f"{v:+.2f}%" for v in cc["contribution_pct"]],
                textposition="outside", textfont=dict(family=T.MONO, size=10)))
            fig.add_vline(x=0, line_color=T.BORDER)
            fig.update_layout(height=max(280, 26 * len(cc)),
                              xaxis_title="Contribution to total return (%)",
                              margin=dict(r=50))
            st.plotly_chart(fig, width="stretch")
            v = pd.DataFrame({
                "Symbol": contrib["symbol"],
                "Weight (%)": (contrib["weight"] * 100).round(2),
                "Return (%)": contrib["return_pct"].round(2),
                "P&L (THB)": contrib["pnl"].round(0),
                "Contribution (%)": contrib["contribution_pct"].round(2)})
            st.dataframe(v, hide_index=True, width="stretch",
                         column_config={"P&L (THB)": st.column_config.NumberColumn(format="%,.0f")})
    with t3:
        if bm.empty:
            st.info("No benchmark data for this window.")
        else:
            mb = B.metrics(bm.set_index("date")["value"])
            rows = [{"Metric": k, "Portfolio": round(v, 2),
                     "Market index": round(mb.get(k, np.nan), 2),
                     "Difference": round(v - mb[k], 2) if k in mb else None}
                    for k, v in mp.items()]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            rel = sim.set_index("date")["value"] / bm.set_index("date")["value"].reindex(
                sim["date"]).values
            fig = go.Figure(go.Scatter(x=sim["date"], y=(rel / rel.iloc[0] - 1) * 100,
                                       line=dict(color=T.ACCENT, width=1.6),
                                       name="Relative"))
            fig.add_hline(y=0, line_dash="dot", line_color=T.BORDER)
            fig.update_layout(height=280,
                              yaxis_title="Cumulative out/underperformance (%)")
            st.plotly_chart(fig, width="stretch")

    st.warning(
        "**Limits of this simulation.** Closing prices only — dividends, commission, "
        "spread and tax are excluded, and prices are not adjusted for stock splits. "
        "If the holdings came from the recommended portfolio, the result also carries "
        "lookahead bias, because the selection model saw the whole period before "
        "choosing. Past behaviour does not predict future results.")
