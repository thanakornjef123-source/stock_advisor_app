# -*- coding: utf-8 -*-
"""Recommended Portfolio — output of the suitability profile."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import charts as CH
from core import theme as T
from core import backtest as B
from core.recommend import (asset_allocation, eligible, build, money_table,
                            portfolio_stats, MAX_PER_SECTOR)


def render():
    res = st.session_state.get("result")
    if not res:
        T.topbar("Recommended Portfolio", "No risk profile on file")
        st.warning("Complete the **Risk Profile** questionnaire first — the "
                   "allocation and the eligible universe both depend on it.")
        return

    T.topbar(f"Recommended Portfolio · Category {res['level']} {res['name']}",
             f"Score {res['score']}/{res['max_score']} · as of {D.as_of()}")

    f = D.active_factors()
    pool = eligible(f, res)

    T.stat_cards([
        ("Investor category", f"{res['level']} {res['name']}", res["thai"], ""),
        ("Suitability score", f"{res['score']} / {res['max_score']}", res["range"], ""),
        ("Equity ceiling", f"{res['equity_cap']*100:.0f}%", "of total portfolio", ""),
        ("Eligible universe", f"{len(pool):,}", f"of {len(f):,} securities", ""),
        ("Risk bands allowed", str(len(res["allowed_buckets"])), 
         ", ".join(b.split(" ", 1)[1] for b in res["allowed_buckets"]), ""),
    ])
    T.caption(res["desc"])

    c1, c2 = st.columns(2)
    amount = c1.number_input("Amount to allocate (THB)", 10_000, 1_000_000_000,
                             1_000_000, 100_000, key="pf_amt")
    n = c2.slider("Number of holdings", 5, 20, 10, key="pf_n")

    alloc = asset_allocation(res)
    picks = build(f, res, n)

    # ---------------------------------------------------- 1. allocation
    st.markdown("### 1 · Asset allocation")
    a1, a2 = st.columns([1, 1.3])
    with a1:
        fig = go.Figure(go.Pie(
            labels=alloc["Asset class"], values=alloc["Weight"], hole=0.55,
            marker=dict(colors=[T.SERIES[i] for i in range(len(alloc))],
                        line=dict(color=T.BG, width=2)),
            textinfo="percent", textfont=dict(family=T.MONO, size=11),
            hovertemplate="%{label}<br>%{percent}<extra></extra>"))
        fig.update_layout(height=290, showlegend=False,
                          annotations=[dict(text=f"{res['equity_cap']*100:.0f}%<br>"
                                                 "<span style='font-size:10px'>EQUITY</span>",
                                            showarrow=False, font=dict(family=T.MONO,
                                            size=20, color=T.TEXT))])
        st.plotly_chart(fig, width="stretch")
    with a2:
        v = alloc.copy()
        v["Amount (THB)"] = (v["Weight"] * amount).round(0)
        v["Weight"] = (v["Weight"] * 100).round(1)
        st.dataframe(v, hide_index=True, width="stretch",
                     column_config={"Weight": st.column_config.NumberColumn("Weight (%)", format="%.1f"),
                                    "Amount (THB)": st.column_config.NumberColumn(format="%,.0f")})
        if res["equity_cap"] == 0:
            st.warning("Your profile indicates fixed income only. The equity list "
                       "below is shown for reference — these are the least volatile "
                       "names in the market, should you decide to allocate a small "
                       "portion to stocks against the standard guidance.")

    if picks.empty:
        st.error("No securities clear the eligibility rules for this profile.")
        return

    # ---------------------------------------------------- 2. holdings
    st.markdown("### 2 · Equity holdings")
    T.caption(f"Selected from {len(pool):,} eligible names, capped at "
              f"{MAX_PER_SECTOR} per sector for diversification. "
              f"{'Weighted inversely to volatility' if res['level'] <= 3 else 'Weighted by fit score'}.")

    mt = money_table(picks, alloc, amount)
    view = pd.DataFrame({
        "Symbol": mt["symbol"],
        "Company": mt["company"].str.title(),
        "Sector": mt["sector"],
        "Price": mt["last_close"].round(2),
        "Equity wt (%)": (mt["equity_weight"] * 100).round(1),
        "Portfolio wt (%)": (mt["portfolio_weight"] * 100).round(1),
        "Amount (THB)": mt["amount"],
        "Shares": mt["shares"],
        "Vol (%)": mt["vol_all"].round(1),
        "Max DD (%)": mt["max_dd_all"].round(1),
        "Beta": mt["beta_1y"].round(2),
        "Yield (%)": mt["dividend_yield"].round(2),
        "Fit": mt["fit_score"].round(1)})
    st.dataframe(view, hide_index=True, width="stretch",
                 column_config={"Amount (THB)": st.column_config.NumberColumn(format="%,.0f"),
                                "Shares": st.column_config.NumberColumn(format="%,.0f")})
    st.download_button("Download holdings CSV",
                       mt.to_csv(index=False).encode("utf-8"),
                       f"portfolio_category_{res['level']}.csv", "text/csv")

    b1, b2 = st.columns(2)
    with b1:
        s = view.sort_values("Equity wt (%)")
        fig = go.Figure(go.Bar(
            x=s["Equity wt (%)"], y=s["Symbol"], orientation="h",
            marker_color=T.ACCENT, text=[f"{v:.1f}%" for v in s["Equity wt (%)"]],
            textposition="outside", textfont=dict(family=T.MONO, size=10)))
        fig.update_layout(height=max(280, 26 * len(s)), xaxis_title="Weight (%)",
                          yaxis_title="", margin=dict(r=45))
        st.plotly_chart(fig, width="stretch")
    with b2:
        sec = view.groupby("Sector")["Equity wt (%)"].sum().reset_index()
        fig = go.Figure(go.Pie(
            labels=sec["Sector"], values=sec["Equity wt (%)"], hole=0.45,
            marker=dict(colors=T.SERIES, line=dict(color=T.BG, width=2)),
            textinfo="percent", textfont=dict(family=T.MONO, size=10)))
        fig.update_layout(height=max(280, 26 * len(view)),
                          legend=dict(font=dict(size=10), orientation="v",
                                      x=1.0, y=0.5, xanchor="left", yanchor="middle"))
        st.plotly_chart(fig, width="stretch")

    # ---------------------------------------------------- 3. characteristics
    st.markdown("### 3 · Portfolio characteristics")
    ps = portfolio_stats(picks)
    T.stat_cards([
        ("Weighted volatility", f"{ps['Weighted volatility']:.1f}%", "annualised", ""),
        ("Weighted beta", f"{ps['Weighted beta']:.2f}", "vs market index", ""),
        ("Weighted yield", f"{ps['Weighted dividend yield']:.2f}%", "dividend", "up"),
        ("Weighted 1Y return", f"{ps['Weighted 1Y return']:+.1f}%", "price only",
         T.tone(ps["Weighted 1Y return"])),
        ("Weighted CAGR", f"{ps['Weighted CAGR']:+.1f}%", "since 2021",
         T.tone(ps["Weighted CAGR"])),
        ("Sectors", f"{ps['Sectors covered']:.0f}", "represented", ""),
    ])

    # ------------------------------------------- 3b. is it actually spread out
    # Capping names per sector is not the same as spreading risk. Two holdings
    # in different sectors can still rise and fall together, in which case the
    # portfolio is less diversified than its sector count suggests.
    T.section("Does the diversification hold up?",
              "Sector labels say these are different businesses. Their prices "
              "are the test of whether they actually behave differently.")
    cm_all = D.close_matrix()
    held = [s_ for s_ in picks["symbol"] if s_ in cm_all.columns]
    sub = cm_all[held].tail(504).dropna(axis=1, thresh=250)
    rets = sub.pct_change().dropna(how="all")
    if rets.shape[1] < 2 or len(rets) < 60:
        st.info("Not enough overlapping price history to measure how these "
                "holdings move together.")
    else:
        cmat = rets.corr()
        iu = np.triu_indices(len(cmat), 1)
        pair_vals = cmat.values[iu]
        avg_corr = float(np.nanmean(pair_vals))
        # Effective number of independent bets: N holdings that all move
        # together behave like one. This is the standard portfolio-variance
        # identity with equal weights.
        n_h = len(cmat)
        eff_n = n_h / (1 + (n_h - 1) * max(avg_corr, 0.0)) if n_h else 0.0
        worst = int(np.nanargmax(pair_vals))
        pi, pj = iu[0][worst], iu[1][worst]

        verdict = ("well spread" if avg_corr < 0.35 else
                   "moderately linked" if avg_corr < 0.55 else "closely linked")
        T.stat_cards([
            ("Holdings", f"{n_h}", "in the equity sleeve", ""),
            ("Average correlation", f"{avg_corr:.2f}", verdict,
             "up" if avg_corr < 0.35 else "warn" if avg_corr < 0.55 else "down"),
            ("Effective bets", f"{eff_n:.1f}",
             f"of {n_h} — independent positions",
             "up" if eff_n > n_h * 0.6 else "warn"),
            ("Most alike", f"{cmat.index[pi]} · {cmat.columns[pj]}",
             f"correlation {pair_vals[worst]:.2f}", "warn"),
        ])
        fig = go.Figure(go.Heatmap(
            z=cmat.values, x=cmat.columns, y=cmat.index, zmid=0, zmin=-1, zmax=1,
            colorscale=[[0, T.DOWN], [0.5, T.PANEL_2], [1, T.ACCENT]],
            text=cmat.round(2).values, texttemplate="%{text}",
            textfont=dict(family=T.MONO, size=10),
            hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>"))
        fig.update_layout(height=max(300, 30 * len(cmat) + 120),
                          margin=dict(l=8, r=8, t=10, b=8))
        st.plotly_chart(fig, width="stretch")
        T.caption(
            f"Daily returns over the last two years. {eff_n:.1f} effective bets out "
            f"of {n_h} holdings means the portfolio carries about as much "
            f"independent risk as {eff_n:.0f} unrelated positions would. The "
            "selection caps how many names come from one sector but does not "
            "read this matrix, so a low number here is a limitation of the "
            "method, not a bug in the calculation.")

    # ---------------------------------------------------- 4. rationale
    st.markdown("### 4 · Why each holding was selected")
    for r in mt.itertuples():
        flag = (T.badge("news flag", "warn") if r.news_red_flag else "")
        with st.expander(f"{r.symbol} — {str(r.company).title()}   ·   "
                         f"{r.equity_weight*100:.1f}% of equity sleeve"):
            st.markdown(
                T.badge(r.risk_bucket, "neutral") + T.badge(r.liquidity_tier, "neutral")
                + T.badge(r.size_tier + " cap", "neutral")
                + T.badge(r.sector, "accent") + flag, unsafe_allow_html=True)
            st.write("")
            st.write(r.rationale)
            m = st.columns(6)
            m[0].metric("Volatility", f"{r.vol_all:.1f}%" if pd.notna(r.vol_all) else "—")
            m[1].metric("Max drawdown", f"{r.max_dd_all:.1f}%" if pd.notna(r.max_dd_all) else "—")
            m[2].metric("CAGR", f"{r.cagr:+.1f}%" if pd.notna(r.cagr) else "—")
            m[3].metric("Dividend", f"{r.dividend_yield:.2f}%" if pd.notna(r.dividend_yield) else "—")
            m[4].metric("P/E", f"{r.pe:.1f}" if pd.notna(r.pe) else "—")
            m[5].metric("ROE", f"{r.roe:.1f}%" if pd.notna(r.roe) else "—")

    # ---------------------------------------------------- 5. historical shape
    st.markdown("### 5 · How this portfolio would have behaved")
    st.warning(
        "**Read this before the numbers.** The selection uses volatility and "
        "return computed over the whole 2021–2025 window, then the result is "
        "tested inside that same window. That is lookahead bias — the model "
        "effectively knew the future when it picked. Treat the chart as a "
        "description of the portfolio's character, not as evidence that the "
        "method works. A fair test needs a training window and a separate, "
        "later testing window.")

    cm = D.close_matrix()
    w = dict(zip(picks["symbol"], picks["weight"]))
    end = cm.index.max()
    yrs = st.radio("Test period", ["1 year", "2 years", "3 years", "Full history"],
                   index=2, horizontal=True, key="pf_bt")
    days = {"1 year": 365, "2 years": 730, "3 years": 1095, "Full history": 99999}[yrs]
    start = end - pd.Timedelta(days=days)
    sim = B.simulate(cm, w, start, end, float(amount))
    if sim.empty:
        st.info("Not enough overlapping price history for this window.")
        return
    bm = B.benchmark(D.market_index(), start, end, float(amount))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sim["date"], y=sim["value"], name="Recommended portfolio",
                             line=dict(color=T.ACCENT, width=2)))
    if not bm.empty:
        fig.add_trace(go.Scatter(x=bm["date"], y=bm["value"], name="Market index",
                                 line=dict(color=T.MUTED, width=1.5, dash="dash")))
    CH.time_series(fig, height=364, y_title="Portfolio value (THB)")
    st.plotly_chart(fig, width="stretch")

    mp = B.metrics(sim.set_index("date")["value"])
    mb = B.metrics(bm.set_index("date")["value"]) if not bm.empty else {}
    rows = [{"Metric": k,
             "Portfolio": round(v, 2),
             "Market index": round(mb.get(k), 2) if mb.get(k) is not None else None,
             "Difference": round(v - mb[k], 2) if k in mb else None}
            for k, v in mp.items()]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
