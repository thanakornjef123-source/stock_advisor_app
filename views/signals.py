# -*- coding: utf-8 -*-
"""Signals — rule-based conditions evaluated on the latest data."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import store
from core import tables as TB
from core import theme as T

# name, description, mask builder, tone
RULES = [
    ("Crossed above MA200", "Price is above the 200-day average having been below "
     "it a month ago — a trend turning up.", "bull",
     lambda f: (f["px_vs_ma200"] > 0) & (f["ret_1m"] > 0) & (f["px_vs_ma50"] > 0)),
    ("Golden cross", "The 50-day average sits above the 200-day.", "bull",
     lambda f: f["golden_cross"] == 1),
    ("Oversold", "RSI below 30 — heavy recent selling.", "bear",
     lambda f: f["rsi14"] < 30),
    ("Overbought", "RSI above 70 — a strong run that may be stretched.", "warn",
     lambda f: f["rsi14"] > 70),
    ("Near 52-week high", "Within 3% of the highest price of the past year.", "bull",
     lambda f: f["pct_from_52w_high"] > -3),
    ("Near 52-week low", "Within 5% of the lowest price of the past year.", "bear",
     lambda f: f["pct_from_52w_low"] < 5),
    ("Deep drawdown", "More than 40% below its own all-time peak in this dataset.",
     "bear", lambda f: f["dd_from_peak"] < -40),
    ("High dividend, low payout risk", "Yield above 5% with debt-to-equity under 1.5.",
     "bull", lambda f: (f["dividend_yield"] > 5) & (f["de"] < 1.5)),
    ("Negative news cluster", "Three or more risk-signal disclosures in the past "
     "three months.", "bear", lambda f: f["risk_news_3m"] >= 3),
    ("Weak news sentiment", "Impact-weighted disclosure record in the bottom "
     "decile of the market.", "bear",
     lambda f: f.get("nlp_red_flag", pd.Series(0, index=f.index)) == 1),
    ("Improving fundamentals", "Quality score of 5 or more out of 7, with revenue "
     "growing over two years.", "bull",
     lambda f: (f["quality_fscore"] >= 5) & (f["revenue_2y_growth"] > 0)),
    ("Cash generative", "Positive free cash flow and low accruals — reported "
     "profit backed by cash.", "bull",
     lambda f: (f["free_cash_flow"] > 0) & (f["accruals"] < 0)),
    ("Earnings quality warning", "Accruals above 15% of assets — profit is running "
     "well ahead of the cash coming in.", "warn", lambda f: f["accruals"] > 15),
]

TONE_BADGE = {"bull": "up", "bear": "down", "warn": "warn"}


def render():
    store.load_into_session()
    f = D.active_factors()
    T.topbar("Signals",
             f"Conditions evaluated on the close of {D.as_of()}")

    st.markdown(
        '<div class="panel">These are rules evaluated against the most recent data, '
        'not predictions and not alerts pushed over time. A security appearing here '
        'means the stated condition is true today — nothing more. Read the rule '
        'before reading the list.</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.4, 1.4, 2])
    liq = c1.select_slider("Minimum daily turnover", [0, 1e6, 10e6, 50e6],
                           value=10e6,
                           format_func=lambda v: "All" if v == 0 else T.fmt_big(v),
                           key="sg_liq")
    scope = c2.selectbox("Universe", ["Whole market", "SET50 proxy",
                                      "SET50 + SET100 proxy", "My watchlist",
                                      "My holdings"], key="sg_scope")
    tone_pick = c3.multiselect("Signal type", ["bull", "bear", "warn"],
                               default=["bull", "bear", "warn"],
                               format_func={"bull": "Constructive", "bear": "Negative",
                                            "warn": "Caution"}.get, key="sg_tone")

    d = f[f["avg_value_1y"].fillna(0) >= liq].copy()
    if scope == "SET50 proxy":
        d = d[d["index_proxy"] == "SET50 proxy"]
    elif scope == "SET50 + SET100 proxy":
        d = d[d["index_proxy"].isin(["SET50 proxy", "SET100 proxy"])]
    elif scope == "My watchlist":
        wl = st.session_state.get("watchlist", [])
        if not wl:
            st.info("Watchlist is empty.")
            return
        d = d[d["symbol"].isin(wl)]
    elif scope == "My holdings":
        hs = [h["symbol"] for h in st.session_state.get("holdings", [])]
        if not hs:
            st.info("No holdings recorded. Add them in My Portfolio.")
            return
        d = d[d["symbol"].isin(hs)]

    if d.empty:
        st.warning("No securities in this universe.")
        return

    results = []
    for name, desc, tone, fn in RULES:
        if tone not in tone_pick:
            continue
        try:
            mask = fn(d).fillna(False)
        except Exception:
            continue
        hits = d[mask]
        results.append((name, desc, tone, hits))

    counts = pd.DataFrame([{"Signal": n, "Type": t, "Securities": len(h)}
                           for n, _dsc, t, h in results])
    if counts.empty:
        st.info("No signal types selected.")
        return

    T.section("What fired today")
    s = counts.sort_values("Securities")
    colour = {"bull": T.UP, "bear": T.DOWN, "warn": T.WARN}
    fig = go.Figure(go.Bar(
        x=s["Securities"], y=s["Signal"], orientation="h",
        marker_color=[colour[t] for t in s["Type"]],
        text=s["Securities"], textposition="outside",
        textfont=dict(family=T.MONO, size=10)))
    fig.update_layout(height=max(320, 27 * len(s)), xaxis_title="Securities meeting the rule",
                      margin=dict(r=50))
    st.plotly_chart(fig, width="stretch")

    T.section("Full table")
    for name, desc, tone, hits in results:
        if hits.empty:
            continue
        with st.expander(f"{name}  ·  {len(hits)} securities"):
            st.markdown(T.badge({"bull": "Constructive", "bear": "Negative",
                                 "warn": "Caution"}[tone], TONE_BADGE[tone])
                        + f'<span class="caption">{desc}</span>',
                        unsafe_allow_html=True)
            v = pd.DataFrame({
                "Symbol": hits["symbol"], "Company": hits["company"].str.title(),
                "Sector": hits["sector"], "Price": hits["last_close"].round(2),
                "1M (%)": hits["ret_1m"].round(1), "1Y (%)": hits["ret_1y"].round(1),
                "RSI": hits["rsi14"].round(0),
                "vs MA200 (%)": hits["px_vs_ma200"].round(1),
                "Yield (%)": hits["dividend_yield"].round(2),
                "F-score": hits["quality_fscore"],
                "News rank": hits["nlp_sentiment_score"].round(0),
                "Overall": hits["overall_score"].round(1)})
            p = TB.grid(v.sort_values("Overall", ascending=False),
                        height=min(400, 44 + 34 * len(v)), spark=True,
                        select=True, key=f"sig_{name}")
            if p:
                TB.open_security(p)
            st.download_button(f"Download · {name}",
                               hits.to_csv(index=False).encode("utf-8"),
                               f"signal_{name.lower().replace(' ', '_')}.csv",
                               "text/csv", key=f"dl_{name}")

    T.section("Stocks with the most alerts today")
    tally = {}
    for name, _d, tone, hits in results:
        for sym in hits["symbol"]:
            tally.setdefault(sym, {"bull": 0, "bear": 0, "warn": 0})[tone] += 1
    if tally:
        t = pd.DataFrame(tally).T.reset_index().rename(columns={"index": "symbol"})
        t["net"] = t["bull"] - t["bear"]
        t = t.merge(f[["symbol", "company", "sector", "last_close", "ret_1y"]],
                    on="symbol", how="left")
        top = pd.concat([t.nlargest(8, "net"), t.nsmallest(8, "net")]).drop_duplicates("symbol")
        TB.grid(pd.DataFrame({
            "Symbol": top["symbol"], "Company": top["company"].str.title(),
            "Sector": top["sector"], "Price": top["last_close"].round(2),
            "1Y (%)": top["ret_1y"].round(1),
            "Constructive": top["bull"], "Negative": top["bear"],
            "Caution": top["warn"], "Net": top["net"]}).sort_values("Net", ascending=False),
            height=min(520, 44 + 34 * len(top)), spark=True)
        T.caption("Net is constructive signals minus negative ones. It is a tally of "
                  "rules, not a rating, and the rules overlap — several of them read "
                  "the same trend from different angles.")
