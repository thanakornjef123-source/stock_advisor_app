# -*- coding: utf-8 -*-
"""Security Detail — chart, technicals, fundamentals, news."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from core import data as D
from core import store
from core import tables as TB
from core import charts as CH
from core import theme as T
from core import indicators as I

CATEGORY_LABEL = {
    "financial_statement": "Financial statement", "mdna": "MD&A",
    "dividend": "Dividend", "capital_increase": "Capital increase",
    "warrant": "Warrant", "mna": "M&A / asset deal",
    "connected_txn": "Connected transaction", "board_change": "Board or management",
    "shareholder_meeting": "Shareholder meeting", "nav_report": "NAV report",
    "share_repurchase": "Share buyback", "ipo_listing": "Listing",
    "book_closure": "Book closure", "public_presentation": "Public presentation",
    "corporate_admin": "Corporate admin", "dw_notice": "Derivative warrant",
    "trading_sign_halt": "Trading sign / halt", "delisting": "Delisting risk",
    "market_surveillance": "Market surveillance", "set_clarification": "SET clarification request",
    "auditor_issue": "Auditor issue", "litigation": "Litigation",
    "default_debt": "Debt default", "capital_reduction": "Capital reduction",
    "resignation": "Resignation", "net_loss": "Reported loss",
    "subsidiary_action": "Subsidiary / JV action",
    "date_only_corrupted": "Headline lost in source export", "other": "Unresolved",
}
SOURCE_LABEL = {"rule": "rule", "model_routine": "model", "model_risk": "model",
                "rule_v2": "rule", "data_quality": "corrupted",
                "unresolved": "", "rejected_positive_context": "",
                "rejected_no_lexicon": ""}


def render():
    f = D.factors()
    syms = D.universe()
    cur = st.session_state.get("detail_symbol", "PTT")
    if cur not in syms:
        cur = syms[0]

    top = st.columns([2, 6])
    sym = top[0].selectbox("Security", syms, index=syms.index(cur),
                           key="dt_sym", label_visibility="collapsed")
    st.session_state["detail_symbol"] = sym
    row = f[f["symbol"] == sym]
    if row.empty:
        st.warning("No data for this security.")
        return
    r = row.iloc[0]

    T.topbar(f"{sym} · {str(r['company']).title()}",
             f"{r['sector']} · {r['market']} · as of {D.as_of()}")

    with top[1]:
        wl = set(st.session_state.get("watchlist", []))
        c = st.columns([1, 1, 4])
        if sym in wl:
            if c[0].button("Remove from watchlist", width="stretch"):
                wl.discard(sym); st.session_state["watchlist"] = sorted(wl); store.save(); st.rerun()
        else:
            if c[0].button("Add to watchlist", width="stretch"):
                wl.add(sym); st.session_state["watchlist"] = sorted(wl); store.save(); st.rerun()
        if c[1].button("Compare", width="stretch"):
            cs = list(dict.fromkeys(st.session_state.get("compare_symbols", []) + [sym]))
            st.session_state["compare_symbols"] = cs[:8]
            st.success("Added to Compare.")

    # ---------------- headline ----------------
    T.stat_cards([
        ("Last price", f"{r['last_close']:,.2f}", f"THB · {r['last_date']}", ""),
        ("1 month", f"{r['ret_1m']:+.2f}%" if pd.notna(r["ret_1m"]) else "—",
         "price return", T.tone(r["ret_1m"])),
        ("1 year", f"{r['ret_1y']:+.2f}%" if pd.notna(r["ret_1y"]) else "—",
         "price return", T.tone(r["ret_1y"])),
        ("Volatility 1Y", f"{r['vol_1y']:.1f}%" if pd.notna(r["vol_1y"]) else "—",
         "annualised", ""),
        ("Beta 1Y", f"{r['beta_1y']:.2f}" if pd.notna(r["beta_1y"]) else "—",
         "vs market", ""),
        ("Max DD 1Y", f"{r['max_dd_1y']:.1f}%" if pd.notna(r["max_dd_1y"]) else "—",
         "peak to trough", "down"),
        ("Market cap", T.fmt_big(r["market_cap"]), "THB", ""),
        ("Dividend", f"{r['dividend_yield']:.2f}%" if pd.notna(r["dividend_yield"]) else "—",
         "trailing yield", "warn" if r.get("yield_trap", False) else ""),
        ("Days to exit 500k",
         f"{r['days_to_exit_500k']:,.1f}" if pd.notna(r.get("days_to_exit_500k")) else "—",
         "at 20% of turnover",
         "down" if pd.notna(r.get("days_to_exit_500k")) and r["days_to_exit_500k"] > 5 else ""),
    ])

    badges = (T.badge(r["risk_bucket"], "neutral") + T.badge(r["liquidity_tier"], "neutral")
              + T.badge(f"{r['size_tier']} cap", "neutral")
              + T.badge(f"Overall {r['overall_score']:.0f}", "accent"))
    if not r.get("is_active", True):
        badges += T.badge("No longer trading", "down")
    if r.get("yield_trap", False):
        badges += T.badge("Yield is a price artefact", "warn")
    if r["news_red_flag"]:
        badges += T.badge("Elevated negative news", "warn")
    if r.get("nlp_red_flag", 0):
        badges += T.badge("Weak news sentiment", "warn")
    if pd.notna(r["px_vs_ma200"]):
        badges += T.badge("Above MA200" if r["px_vs_ma200"] > 0 else "Below MA200",
                          "up" if r["px_vs_ma200"] > 0 else "down")
    st.markdown(badges, unsafe_allow_html=True)
    st.write("")

    if not r.get("is_active", True):
        d_since = r.get("days_since_trade")
        st.error(
            f"This security last traded on {r['last_date']}"
            + (f", {int(d_since):,} days ago. " if pd.notna(d_since) else ". ")
            + "Every figure below was measured up to that date, not to "
            f"{D.as_of()}. It is excluded from screens, rankings and "
            "recommendations, and is shown here only so the record can be read.")

    if r.get("yield_trap", False):
        st.warning(
            f"The {r['dividend_yield']:.1f}% yield shown above is dividends already "
            f"paid divided by today's price — and the price has fallen "
            f"{abs(r['ret_1y']):.0f}% over the year. The ratio rose because the "
            "denominator collapsed, not because the payout improved. This name "
            "earns no income credit and is kept out of recommendations.")

    if r["news_red_flag"]:
        st.warning("This security is flagged: the frequency of negative regulatory "
                   "news over the past two years sits in the market's top 5%. "
                   "Read the news timeline before drawing conclusions from the price.")

    hist = D.symbol_history(sym)
    if hist.empty:
        st.warning("No price history.")
        return
    ind = I.enrich(hist)

    t1, t2, t3, t4 = st.tabs(["Chart", "Fundamentals", "News", "Factor profile"])

    # ---------------- chart ----------------
    with t1:
        c = st.columns([1.5, 3, 2])
        rng = c[0].selectbox("Range", ["3M", "6M", "1Y", "2Y", "3Y", "All"],
                             index=2, key="dt_rng")
        overlays = c[1].multiselect("Overlays", ["MA20", "MA50", "MA200", "Bollinger"],
                                    default=["MA50", "MA200"], key="dt_ov")
        lower = c[2].selectbox("Lower panel", ["Volume", "RSI (14)", "MACD"],
                               key="dt_low")
        log_scale = c[2].toggle("Log scale", value=False, key="dt_log")
        days = {"3M": 91, "6M": 182, "1Y": 365, "2Y": 730, "3Y": 1095, "All": 99999}[rng]
        d = ind[ind["date"] >= ind["date"].max() - pd.Timedelta(days=days)]

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.74, 0.26], vertical_spacing=0.03)
        fig.add_trace(CH.candles(d, sym), row=1, col=1)
        ov = {"MA20": ("ma20", T.WARN), "MA50": ("ma50", T.ACCENT),
              "MA200": ("ma200", "#A78BFA")}
        for name, (col, colour) in ov.items():
            if name in overlays and d[col].notna().any():
                fig.add_trace(go.Scatter(x=d["date"], y=d[col], name=name,
                                         line=dict(color=colour, width=1.2)), row=1, col=1)
        if "Bollinger" in overlays and d["bb_high"].notna().any():
            fig.add_trace(go.Scatter(x=d["date"], y=d["bb_high"], name="BB upper",
                                     line=dict(color=T.MUTED, width=0.8, dash="dot")), row=1, col=1)
            fig.add_trace(go.Scatter(x=d["date"], y=d["bb_low"], name="BB lower",
                                     line=dict(color=T.MUTED, width=0.8, dash="dot"),
                                     fill="tonexty",
                                     fillcolor="rgba(124,135,151,0.07)"), row=1, col=1)

        if lower == "Volume":
            fig.add_trace(CH.volume_bars(d), row=2, col=1)
            fig.update_yaxes(title_text="Volume", row=2, col=1)
        elif lower == "RSI (14)":
            fig.add_trace(go.Scatter(x=d["date"], y=d["rsi14"], name="RSI",
                                     line=dict(color=T.ACCENT, width=1.3)), row=2, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color=T.DOWN, row=2, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color=T.UP, row=2, col=1)
            fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
        else:
            hc = np.where(d["macd_hist"] >= 0, T.UP, T.DOWN)
            fig.add_trace(go.Bar(x=d["date"], y=d["macd_hist"], name="Histogram",
                                 marker_color=hc, opacity=0.55), row=2, col=1)
            fig.add_trace(go.Scatter(x=d["date"], y=d["macd"], name="MACD",
                                     line=dict(color=T.ACCENT, width=1.2)), row=2, col=1)
            fig.add_trace(go.Scatter(x=d["date"], y=d["macd_signal"], name="Signal",
                                     line=dict(color=T.WARN, width=1.2)), row=2, col=1)
            fig.update_yaxes(title_text="MACD", row=2, col=1)

        # negative-news markers
        nw = D.news()
        risky = nw[(nw["symbol"] == sym) & (nw["is_risk_signal"] == 1) &
                   (nw["datetime"] >= d["date"].min())]
        if len(risky):
            j = pd.merge_asof(risky.sort_values("datetime"),
                              d[["date", "high"]].rename(columns={"date": "datetime"}),
                              on="datetime", direction="nearest")
            fig.add_trace(go.Scatter(
                x=j["datetime"], y=j["high"] * 1.02, mode="markers", name="Negative news",
                marker=dict(color=T.DOWN, size=7, symbol="triangle-down"),
                text=j["subject"], hovertemplate="%{text}<extra></extra>"), row=1, col=1)

        fig.update_layout(height=590, xaxis_rangeslider_visible=False,
                          showlegend=True, margin=dict(l=8, r=8, t=26, b=8))
        fig.update_yaxes(title_text="Price (THB)", row=1, col=1,
                         type="log" if log_scale else "linear")
        CH.crosshair(fig)
        st.plotly_chart(fig, width="stretch")

        T.stat_cards([
            ("52-week high", f"{r['high_52w']:,.2f}" if pd.notna(r["high_52w"]) else "—",
             f"{r['pct_from_52w_high']:+.1f}% away" if pd.notna(r["pct_from_52w_high"]) else "", ""),
            ("52-week low", f"{r['low_52w']:,.2f}" if pd.notna(r["low_52w"]) else "—",
             f"{r['pct_from_52w_low']:+.1f}% above" if pd.notna(r["pct_from_52w_low"]) else "", ""),
            ("RSI (14)", f"{r['rsi14']:.1f}" if pd.notna(r["rsi14"]) else "—",
             "overbought >70 · oversold <30", ""),
            ("Price vs MA50", f"{r['px_vs_ma50']:+.2f}%" if pd.notna(r["px_vs_ma50"]) else "—",
             "", T.tone(r["px_vs_ma50"])),
            ("Price vs MA200", f"{r['px_vs_ma200']:+.2f}%" if pd.notna(r["px_vs_ma200"]) else "—",
             "", T.tone(r["px_vs_ma200"])),
            ("Avg value 20D", T.fmt_big(r["avg_value_20d"]), "THB per day", ""),
        ])

    # ---------------- fundamentals ----------------
    with t2:
        fin = D.financials()
        g = fin[fin["symbol"] == sym].sort_values(["year", "quarter"])
        if g.empty:
            st.info("No company financial statements in the dataset. This is normal "
                    "for REITs, infrastructure funds and ETFs, which do not report "
                    "in the same format as operating companies.")
        else:
            T.stat_cards([
                ("Last reported", str(r["latest_period"]), "fiscal period", ""),
                ("ROE", f"{r['roe']:.2f}%" if pd.notna(r["roe"]) else "—", "return on equity", T.tone(r["roe"])),
                ("ROA", f"{r['roa']:.2f}%" if pd.notna(r["roa"]) else "—", "return on assets", T.tone(r["roa"])),
                ("Debt / equity", f"{r['de']:.2f}" if pd.notna(r["de"]) else "—", "leverage", ""),
                ("Net margin", f"{r['net_margin']:.2f}%" if pd.notna(r["net_margin"]) else "—", "quarter", T.tone(r["net_margin"])),
                ("Revenue YoY", f"{r['revenue_growth_yoy']:+.1f}%" if pd.notna(r["revenue_growth_yoy"]) else "—",
                 "same quarter", T.tone(r["revenue_growth_yoy"])),
                ("Profit YoY", f"{r['profit_growth_yoy']:+.1f}%" if pd.notna(r["profit_growth_yoy"]) else "—",
                 "same quarter", T.tone(r["profit_growth_yoy"])),
            ])
            fig = make_subplots(rows=2, cols=2, vertical_spacing=0.16,
                                subplot_titles=("Quarterly revenue", "Quarterly net profit",
                                                "ROE and ROA (%)", "Debt / equity"))
            fig.add_trace(go.Bar(x=g["period"], y=g["total_revenue_quarter"],
                                 marker_color=T.ACCENT, name="Revenue"), row=1, col=1)
            pc = np.where(g["net_profit_quarter"].fillna(0) >= 0, T.UP, T.DOWN)
            fig.add_trace(go.Bar(x=g["period"], y=g["net_profit_quarter"],
                                 marker_color=pc, name="Net profit"), row=1, col=2)
            fig.add_trace(go.Scatter(x=g["period"], y=g["roe"], name="ROE",
                                     line=dict(color=T.UP, width=1.6)), row=2, col=1)
            fig.add_trace(go.Scatter(x=g["period"], y=g["roa"], name="ROA",
                                     line=dict(color=T.WARN, width=1.6)), row=2, col=1)
            fig.add_trace(go.Scatter(x=g["period"], y=g["de"], name="D/E",
                                     line=dict(color=T.SERIES[4], width=1.6)), row=2, col=2)
            fig.update_layout(height=560, showlegend=False)
            for a in fig.layout.annotations:
                a.font.size = 12
            st.plotly_chart(fig, width="stretch")
            T.section("Reported statements",
                      "Straight from the exchange filings, most recent quarter "
                      "first. Figures are in thousands of baht.")
            n_q = st.radio("Quarters", [4, 8, 12, 20], index=1, horizontal=True,
                           key="dt_fin_n", format_func=lambda v: f"Last {v}")
            gv = g.tail(int(n_q)).iloc[::-1]

            STATEMENTS = {
                "Income statement": [
                    ("Revenue", "total_revenue_quarter"),
                    ("Expenses", "total_expenses_quarter"),
                    ("Operating profit (EBIT)", "ebit_quarter"),
                    ("Net profit", "net_profit_quarter"),
                    ("Net profit, year to date", "net_profit_accum"),
                    ("Earnings per share (THB)", "eps_quarter"),
                    ("Net margin (%)", "net_profit_margin_quarter"),
                ],
                "Balance sheet": [
                    ("Total assets", "total_assets"),
                    ("Total liabilities", "total_liabilities"),
                    ("Total equity", "total_equity"),
                    ("Paid-up share capital", "paidup_share_capital"),
                    ("Debt / equity", "de"),
                    ("Return on equity (%)", "roe"),
                    ("Return on assets (%)", "roa"),
                    ("Asset turnover", "total_asset_turnover"),
                ],
                "Cash flow": [
                    ("Operating cash flow", "operating_cash_flow"),
                    ("Investing cash flow", "investing_cash_flow"),
                    ("Financing cash flow", "financing_cash_flow"),
                ],
            }
            for name, rows in STATEMENTS.items():
                present = [(lbl, col) for lbl, col in rows if col in gv.columns]
                if not present:
                    continue
                table = pd.DataFrame(
                    {lbl: pd.to_numeric(gv[col], errors="coerce").values
                     for lbl, col in present},
                    index=gv["period"].astype(str).values).T
                table.index.name = name
                st.markdown(f"**{name}**")
                st.dataframe(
                    table.style.format("{:,.2f}", na_rep="—")
                         .map(lambda v: f"color:{T.DOWN}"
                              if isinstance(v, (int, float)) and v < 0 else ""),
                    width="stretch")
            st.download_button(
                "Download statements CSV",
                gv.to_csv(index=False).encode("utf-8"),
                file_name=f"{sym}_statements.csv", mime="text/csv",
                key="dt_fin_dl")

    # ---------------- news ----------------
    with t3:
        nw = D.news()
        n = nw[nw["symbol"] == sym].sort_values("datetime", ascending=False)
        if n.empty:
            st.info("No news items for this security.")
        else:
            sent = r.get("nlp_sentiment", float("nan"))
            rank = r.get("nlp_sentiment_score", float("nan"))
            T.stat_cards([
                ("Items, 2 years", f"{int(r['news_2y'])}", "total disclosures", ""),
                ("NLP sentiment", f"{sent:+.3f}" if pd.notna(sent) else "—",
                 "impact-weighted", T.tone(sent)),
                ("Sentiment rank", f"{rank:.0f}" if pd.notna(rank) else "—",
                 "percentile vs market", T.tone((rank - 50) if pd.notna(rank) else None)),
                ("Negative items, 2Y", f"{int(r.get('nlp_negative_items_2y', 0))}",
                 "categories with measured negative impact",
                 "down" if r.get("nlp_negative_items_2y", 0) > 0 else ""),
                ("Negative, 1 year", f"{int(r['risk_news_1y'])}", "rule-flagged items",
                 "down" if r["risk_news_1y"] > 0 else ""),
                ("Negative, 3 months", f"{int(r['risk_news_3m'])}", "rule-flagged items",
                 "down" if r["risk_news_3m"] > 0 else ""),
            ])
            T.caption("Sentiment weights each disclosure by the abnormal return "
                      "actually observed after that category of news, decayed with a "
                      "180-day half-life. See News Intelligence for the calibration.")
            cnt = (n.assign(y=n["datetime"].dt.year)
                     .groupby(["y", "is_risk_signal"]).size().reset_index(name="n"))
            fig = go.Figure()
            for flag, colour, label in [(0, T.PANEL_2, "Routine"), (1, T.DOWN, "Negative")]:
                cc = cnt[cnt["is_risk_signal"] == flag]
                fig.add_trace(go.Bar(x=cc["y"], y=cc["n"], name=label,
                                     marker_color=colour,
                                     marker_line=dict(color=T.BORDER, width=1)))
            fig.update_layout(barmode="stack", height=230, xaxis_title="Year",
                              yaxis_title="Disclosures")
            st.plotly_chart(fig, width="stretch")

            only = st.checkbox("Only show negative news", key="dt_news_only")
            show = n[n["is_risk_signal"] == 1] if only else n
            v = pd.DataFrame({
                "Date": show["datetime"].dt.strftime("%d %b %Y  %H:%M"),
                "Category": show["news_category"].map(lambda c: CATEGORY_LABEL.get(c, c)),
                "Labelled by": show["source"].map(lambda c: SOURCE_LABEL.get(c, "")),
                "Signal": show["is_risk_signal"].map({1: "Negative", 0: ""}),
                "Headline": show["subject"]})
            st.dataframe(v.head(400), hide_index=True, width="stretch", height=420)
            T.caption("Categories come from keyword rules, extended by a trained "
                      "classifier where the rules had no pattern — the source column "
                      "shows which. Only headlines are read, never the body text.")

    # ---------------- factor profile ----------------
    with t4:
        cols = ["value_score", "quality_score", "momentum_score",
                "lowvol_score", "income_score", "growth_score"]
        labels = ["Value", "Quality", "Momentum", "Low volatility", "Income", "Growth"]
        vals = [float(r[c]) if pd.notna(r[c]) else 50.0 for c in cols]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=labels + [labels[0]], fill="toself",
            name=sym, line=dict(color=T.ACCENT, width=2),
            fillcolor="rgba(45,140,255,0.18)"))
        med = [50] * (len(labels) + 1)
        fig.add_trace(go.Scatterpolar(r=med, theta=labels + [labels[0]],
                                      name="Market median",
                                      line=dict(color=T.MUTED, width=1, dash="dot")))
        fig.update_layout(height=430, polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, 100], gridcolor=T.GRID,
                            tickfont=dict(family=T.MONO, size=9, color=T.MUTED)),
            angularaxis=dict(gridcolor=T.GRID,
                             tickfont=dict(size=11, color=T.TEXT))))
        st.plotly_chart(fig, width="stretch")
        T.caption("Each axis is a percentile rank against every security in the "
                  "dataset. 50 is the market median; 100 is best in class.")

        T.section("Most similar stocks",
                  "Nearest neighbours in six-dimensional factor space — the names that most resemble this one on style, regardless of sector.")
        fc = ["value_score", "quality_score", "momentum_score",
              "lowvol_score", "income_score", "growth_score"]
        M = f[["symbol", "company", "sector"] + fc].dropna(subset=fc).copy()
        if sym in set(M["symbol"]):
            target = M.loc[M["symbol"] == sym, fc].values[0]
            M["distance"] = np.sqrt(((M[fc].values - target) ** 2).sum(axis=1))
            near = M[M["symbol"] != sym].nsmallest(8, "distance")
            near = near.merge(f[["symbol", "last_close", "ret_1y", "vol_1y", "pe",
                                 "dividend_yield", "overall_score"]], on="symbol", how="left")
            p = TB.grid(pd.DataFrame({
                "Symbol": near["symbol"], "Company": near["company"].str.title(),
                "Sector": near["sector"], "Distance": near["distance"].round(1),
                "Price": near["last_close"].round(2),
                "1Y (%)": near["ret_1y"].round(1), "Vol (%)": near["vol_1y"].round(1),
                "P/E": near["pe"].round(1), "Yield (%)": near["dividend_yield"].round(2),
                "Overall": near["overall_score"].round(1)}),
                height=330, spark=True, select=True, key="dt_near")
            if p:
                TB.open_security(p)

        peers = f[(f["sector"] == r["sector"]) & (f["symbol"] != sym)]
        peers = peers.nlargest(min(10, len(peers)), "market_cap")
        if not peers.empty:
            T.section("Biggest names in the same sector")
            pv = pd.DataFrame({
                "Symbol": peers["symbol"], "Company": peers["company"].str.title(),
                "Price": peers["last_close"].round(2),
                "1Y (%)": peers["ret_1y"].round(1),
                "Vol (%)": peers["vol_1y"].round(1),
                "P/E": peers["pe"].round(1), "P/BV": peers["pbv"].round(2),
                "Yield (%)": peers["dividend_yield"].round(2),
                "ROE (%)": peers["roe"].round(1),
                "Market cap": peers["market_cap"].round(0)})
            p2 = TB.grid(pv, height=min(420, 44 + 34 * len(pv)), spark=True,
                         select=True, key="dt_peers", money_cols=["Market cap"])
            if p2:
                TB.open_security(p2)
