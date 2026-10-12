# -*- coding: utf-8 -*-
"""My Portfolio — track real holdings against the price history."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import store
from core import tables as TB
from core import charts as CH
from core import theme as T
from core import backtest as B


def _valued() -> pd.DataFrame:
    """Join stored holdings with current prices and factor data."""
    h = pd.DataFrame(st.session_state.get("holdings", []))
    if h.empty:
        return h
    f = D.factors()[["symbol", "company", "sector", "last_close", "vol_all",
                     "beta_1y", "dividend_yield", "ret_1y", "risk_bucket",
                     "nlp_sentiment_score", "news_red_flag"]]
    h = h.merge(f, on="symbol", how="left")
    h["shares"] = pd.to_numeric(h["shares"], errors="coerce").fillna(0)
    h["cost"] = pd.to_numeric(h["cost"], errors="coerce").fillna(0)
    h["cost_value"] = h["shares"] * h["cost"]
    h["market_value"] = h["shares"] * h["last_close"]
    h["pnl"] = h["market_value"] - h["cost_value"]
    h["pnl_pct"] = np.where(h["cost_value"] > 0, h["pnl"] / h["cost_value"] * 100, np.nan)
    total = h["market_value"].sum()
    h["weight"] = h["market_value"] / total * 100 if total > 0 else np.nan
    h["annual_dividend"] = h["market_value"] * h["dividend_yield"].fillna(0) / 100
    return h


def render():
    store.load_into_session()
    T.topbar("My Portfolio",
             f"Holdings valued at closing prices of {D.as_of()}")

    syms = D.universe()

    # ------------------------------------------------ add a position
    with st.expander("Add a holding", expanded=not st.session_state.get("holdings")):
        c = st.columns([2, 1.2, 1.2, 1.4, 1])
        sym = c[0].selectbox("Security", syms, key="hd_sym")
        shares = c[1].number_input("Shares", min_value=0.0, value=100.0, step=100.0,
                                   key="hd_sh")
        default_px = float(D.factors().loc[D.factors()["symbol"] == sym,
                                           "last_close"].iloc[0])
        cost = c[2].number_input("Cost per share (THB)", min_value=0.0,
                                 value=round(default_px, 2), step=0.25, key="hd_cost")
        bought = c[3].date_input("Purchase date", value=D.last_date(),
                                 max_value=D.last_date(), key="hd_date")
        c[4].markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if c[4].button("Add", type="primary", width="stretch", key="hd_add"):
            if shares > 0:
                hs = list(st.session_state.get("holdings", []))
                hs.append({"symbol": sym, "shares": float(shares),
                           "cost": float(cost), "date": str(bought)})
                st.session_state["holdings"] = hs
                store.save()
                st.rerun()
            else:
                st.warning("Enter a share count above zero.")

    h = _valued()
    if h.empty:
        st.info("No positions yet. Add one above — the terminal will value it "
                "against the price history, measure the risk of the combined book "
                "and compare it with the market.")
        return

    # ------------------------------------------------ headline
    cost_v, mkt_v = h["cost_value"].sum(), h["market_value"].sum()
    pnl = mkt_v - cost_v
    pnl_pct = pnl / cost_v * 100 if cost_v > 0 else np.nan
    w = h["market_value"] / mkt_v if mkt_v > 0 else h["market_value"] * 0

    def wavg(col):
        m = h[col].notna()
        return float((h.loc[m, col] * w[m]).sum() / w[m].sum()) if m.any() and w[m].sum() else np.nan

    T.stat_cards([
        ("Market value", f"{mkt_v:,.0f}", "THB", ""),
        ("Cost basis", f"{cost_v:,.0f}", "THB", ""),
        ("Unrealised P&L", f"{pnl:+,.0f}", f"{pnl_pct:+.2f}%", T.tone(pnl)),
        ("Positions", str(len(h)), f"{h['sector'].nunique()} sectors", ""),
        ("Weighted volatility", f"{wavg('vol_all'):.1f}%", "annualised", ""),
        ("Weighted beta", f"{wavg('beta_1y'):.2f}", "vs market", ""),
        ("Dividend income", f"{h['annual_dividend'].sum():,.0f}",
         f"{h['annual_dividend'].sum()/mkt_v*100:.2f}% yield" if mkt_v > 0 else "", "up"),
        ("Largest position", f"{h.loc[h['weight'].idxmax(), 'symbol']}",
         f"{h['weight'].max():.1f}% of book", ""),
    ])

    flagged = h[h["news_red_flag"] == 1]
    if not flagged.empty:
        st.warning("Held with an elevated negative-news record: "
                   + ", ".join(flagged["symbol"]) +
                   ". Open Security Detail to read the disclosure timeline.")
    if h["weight"].max() > 35:
        st.warning(f"{h.loc[h['weight'].idxmax(), 'symbol']} is "
                   f"{h['weight'].max():.0f}% of the book. A single position above "
                   "about a third means the portfolio's outcome is mostly that one "
                   "company's outcome.")

    # ------------------------------------------------ table
    st.markdown("### Positions")
    view = pd.DataFrame({
        "Symbol": h["symbol"], "Company": h["company"].str.title(),
        "Sector": h["sector"], "Shares": h["shares"],
        "Cost": h["cost"].round(2), "Last": h["last_close"].round(2),
        "Cost value": h["cost_value"].round(0),
        "Market value": h["market_value"].round(0),
        "P&L (THB)": h["pnl"].round(0), "P&L (%)": h["pnl_pct"].round(2),
        "Weight (%)": h["weight"].round(1),
        "Vol (%)": h["vol_all"].round(1), "Beta": h["beta_1y"].round(2),
        "Yield (%)": h["dividend_yield"].round(2)})
    picked = TB.grid(view, height=min(520, 44 + 34 * len(view)), spark=True,
                     select=True, key="hd_grid",
                     money_cols=["Shares", "Cost value", "Market value", "P&L (THB)"])
    if picked:
        TB.open_security(picked)

    c1, c2, c3 = st.columns([1.4, 1.4, 4])
    c1.download_button("Download CSV", h.to_csv(index=False).encode("utf-8"),
                       "my_portfolio.csv", "text/csv", width="stretch")
    rm = c2.selectbox("Remove position", ["—"] +
                      [f"{i}: {r['symbol']} × {r['shares']:,.0f}"
                       for i, r in enumerate(st.session_state["holdings"])],
                      key="hd_rm", label_visibility="collapsed")
    if rm != "—":
        idx = int(rm.split(":")[0])
        hs = list(st.session_state["holdings"])
        hs.pop(idx)
        st.session_state["holdings"] = hs
        store.save()
        st.rerun()
    if c3.button("Clear all positions", key="hd_clear"):
        st.session_state["holdings"] = []
        store.save()
        st.rerun()

    # ------------------------------------------------ charts
    a, b = st.columns(2)
    with a:
        T.section("How the money is split")
        fig = go.Figure(go.Pie(labels=h["symbol"], values=h["market_value"], hole=0.5,
                               marker=dict(colors=T.SERIES,
                                           line=dict(color=T.BG, width=2)),
                               textinfo="label+percent",
                               textfont=dict(family=T.MONO, size=10)))
        fig.update_layout(height=330, showlegend=False)
        st.plotly_chart(fig, width="stretch")
    with b:
        T.section("Gain and loss, holding by holding")
        s = h.sort_values("pnl")
        fig = go.Figure(go.Bar(
            x=s["pnl"], y=s["symbol"], orientation="h",
            marker_color=[T.UP if v >= 0 else T.DOWN for v in s["pnl"]],
            text=[f"{v:+,.0f}" for v in s["pnl"]], textposition="outside",
            textfont=dict(family=T.MONO, size=10)))
        fig.add_vline(x=0, line_color=T.BORDER)
        fig.update_layout(height=330, xaxis_title="Unrealised P&L (THB)",
                          margin=dict(r=70))
        st.plotly_chart(fig, width="stretch")

    T.section("Sector exposure")
    sec = h.groupby("sector")["market_value"].sum().sort_values(ascending=False)
    fig = go.Figure(go.Bar(x=sec.values / mkt_v * 100, y=sec.index, orientation="h",
                           marker_color=T.ACCENT,
                           text=[f"{v/mkt_v*100:.1f}%" for v in sec.values],
                           textposition="outside",
                           textfont=dict(family=T.MONO, size=10)))
    fig.update_layout(height=max(220, 30 * len(sec)), xaxis_title="Share of book (%)",
                      margin=dict(r=60))
    st.plotly_chart(fig, width="stretch")

    # ------------------------------------------------ history
    st.markdown("### How this book would have travelled")
    T.caption("Values the current weights back through history. It is not your "
              "actual trading record — it assumes you always held these "
              "proportions — but it shows the volatility and drawdown the "
              "combination carries.")
    cm = D.close_matrix()
    weights = dict(zip(h["symbol"], h["market_value"] / mkt_v))
    weights = {k: v for k, v in weights.items() if k in cm.columns}
    if not weights:
        return
    end = cm.index.max()
    rng = st.radio("Window", ["1 year", "2 years", "3 years", "Full history"],
                   index=1, horizontal=True, key="hd_win")
    days = {"1 year": 365, "2 years": 730, "3 years": 1095, "Full history": 99999}[rng]
    sim = B.simulate(cm, weights, end - pd.Timedelta(days=days), end, float(mkt_v))
    if sim.empty:
        st.info("Not enough overlapping price history for this window.")
        return
    bm = B.benchmark(D.market_index(), end - pd.Timedelta(days=days), end, float(mkt_v))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sim["date"], y=sim["value"], name="Your book",
                             line=dict(color=T.ACCENT, width=2)))
    if not bm.empty:
        fig.add_trace(go.Scatter(x=bm["date"], y=bm["value"], name="Market index",
                                 line=dict(color=T.MUTED, width=1.5, dash="dash")))
    CH.time_series(fig, height=364, y_title="Value (THB)")
    st.plotly_chart(fig, width="stretch")

    m = B.metrics(sim.set_index("date")["value"])
    T.stat_cards([
        ("Total return", f"{m['Total return']:+.2f}%", rng, T.tone(m["Total return"])),
        ("CAGR", f"{m['CAGR']:+.2f}%", "annualised", T.tone(m["CAGR"])),
        ("Volatility", f"{m['Volatility']:.2f}%", "annualised", ""),
        ("Max drawdown", f"{m['Max drawdown']:.2f}%", "peak to trough", "down"),
        ("Sharpe", f"{m['Sharpe']:.2f}", "rf 2%", T.tone(m["Sharpe"])),
        ("Positive days", f"{m['Positive days']:.1f}%", "of trading days", ""),
    ])
    T.caption(store.status_note())
