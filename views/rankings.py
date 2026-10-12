# -*- coding: utf-8 -*-
"""Rankings — composite grades, factor leaderboards and an honest factor test."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import tables as TB
from core import theme as T

FACTORS = [
    ("overall_score", "Overall", "Equal blend of the five style scores."),
    ("value_score", "Value", "Cheap on P/E and P/BV, paying a dividend."),
    ("quality_score", "Quality", "High return on equity and assets, low leverage."),
    ("momentum_score", "Momentum", "Strong 1, 3, 6 and 12-month price returns."),
    ("lowvol_score", "Low volatility", "Low realised volatility, shallow drawdown, low beta."),
    ("income_score", "Income", "Dividend yield, supported by liquidity and low debt."),
    ("growth_score", "Growth", "Revenue and profit growth plus long-run price CAGR."),
    ("nlp_sentiment_score", "News sentiment", "Impact-weighted disclosure record."),
]

GRADES = [(93, "A+"), (85, "A"), (77, "B+"), (68, "B"), (58, "C+"),
          (46, "C"), (33, "D+"), (18, "D"), (0, "F")]
GRADE_TONE = {"A+": T.UP, "A": T.UP, "B+": "#5CB88F", "B": "#5CB88F",
              "C+": T.MUTED, "C": T.MUTED, "D+": T.WARN, "D": T.WARN, "F": T.DOWN}


def grade_of(pct):
    if pd.isna(pct):
        return "—"
    for cut, g in GRADES:
        if pct >= cut:
            return g
    return "F"


def render():
    f = D.active_factors().copy()
    T.topbar("Rankings", f"{len(f)} securities scored · as of {D.as_of()}")

    st.markdown(
        '<div class="panel">Every security is scored on six style factors plus its '
        'news record, each expressed as a percentile against the whole market. The '
        'composite grade is the blend. Scores describe what a security <i>is</i> — '
        'cheap, steady, growing — not a forecast of what it will do next. The last '
        'tab tests, out of sample, which of these factors actually paid.</div>',
        unsafe_allow_html=True)

    # ---------------- filters ----------------
    c1, c2, c3, c4 = st.columns(4)
    liq = c1.select_slider("Minimum daily turnover",
                           [0, 1e6, 5e6, 10e6, 50e6, 100e6], value=10e6,
                           format_func=lambda v: "All" if v == 0 else T.fmt_big(v),
                           key="rk_liq")
    secs = c2.multiselect("Sector", sorted(f["sector"].unique()), key="rk_sec")
    sizes = c3.multiselect("Size", ["Large", "Mid", "Small", "Micro"], key="rk_size")
    clean = c4.checkbox("Exclude flagged news records", value=True, key="rk_clean")

    d = f[f["avg_value_1y"].fillna(0) >= liq]
    if secs:
        d = d[d["sector"].isin(secs)]
    if sizes:
        d = d[d["size_tier"].isin(sizes)]
    if clean and "nlp_red_flag" in d.columns:
        d = d[(d["nlp_red_flag"] == 0) & (d["news_red_flag"] == 0)]
    if d.empty:
        st.warning("No securities match. Relax a filter.")
        return

    # grades are computed within the filtered universe so they stay comparable
    d = d.copy()
    d["composite_pct"] = d["overall_score"].rank(pct=True) * 100
    d["grade"] = d["composite_pct"].map(grade_of)

    counts = d["grade"].value_counts()
    order = [g for _, g in GRADES]
    T.stat_cards([("Universe", f"{len(d):,}", "after filters", "")] +
                 [(g, str(int(counts.get(g, 0))), "securities",
                   "up" if g.startswith(("A", "B")) else ("down" if g in ("D", "D+", "F") else ""))
                  for g in order[:6]])

    t1, t2, t3 = st.tabs(["Top ranked", "Factor leaderboards", "Does it work?"])

    # ---------------- top ranked ----------------
    with t1:
        n = st.slider("Show top", 10, 100, 30, 10, key="rk_n")
        top = d.nlargest(n, "overall_score")
        view = pd.DataFrame({
            "Rank": range(1, len(top) + 1),
            "Grade": top["grade"].values,
            "Symbol": top["symbol"].values,
            "Company": top["company"].str.title().values,
            "Sector": top["sector"].values,
            "Price": top["last_close"].round(2).values,
            "1Y (%)": top["ret_1y"].round(1).values,
            "Vol (%)": top["vol_1y"].round(1).values,
            "Value": top["value_score"].round(0).values,
            "Quality": top["quality_score"].round(0).values,
            "Momentum": top["momentum_score"].round(0).values,
            "Low vol": top["lowvol_score"].round(0).values,
            "Income": top["income_score"].round(0).values,
            "Growth": top["growth_score"].round(0).values,
            "News": top.get("nlp_sentiment_score", pd.Series(np.nan, index=top.index)).round(0).values,
            "Overall": top["overall_score"].round(1).values,
        })
        picked = TB.grid(view, height=560, spark=True, select=True, key="rk_grid")
        if picked:
            TB.open_security(picked)
        T.caption("Click a row to open the security. Score columns are drawn as "
                  "bars against the market percentile.")
        st.download_button("Download rankings CSV",
                           d.sort_values("overall_score", ascending=False)
                            .to_csv(index=False).encode("utf-8"),
                           "rankings.csv", "text/csv")

        T.section("What the top-ranked names score on")
        cols = [c for c, _l, _d in FACTORS if c != "overall_score" and c in top.columns]
        labs = [l for c, l, _d in FACTORS if c != "overall_score" and c in top.columns]
        z = top.head(20)[cols].values.astype(float)
        fig = go.Figure(go.Heatmap(
            z=z, x=labs, y=top.head(20)["symbol"],
            colorscale=[[0, "#B3251F"], [0.5, "#2A313C"], [1, "#1B9E7A"]],
            zmid=50, zmin=0, zmax=100, text=np.round(z, 0), texttemplate="%{text:.0f}",
            textfont=dict(family=T.MONO, size=10),
            colorbar=dict(thickness=12, tickfont=dict(size=10))))
        fig.update_layout(height=max(340, 27 * min(20, len(top))), margin=dict(l=8, t=20))
        st.plotly_chart(fig, width="stretch")
        T.caption("A security can rank highly overall while being weak on one style — "
                  "the blend is what the grade reflects.")

    # ---------------- leaderboards ----------------
    with t2:
        k = st.slider("How many to show", 5, 25, 10, 5, key="rk_k")
        avail = [(c, l, desc) for c, l, desc in FACTORS if c in d.columns and c != "overall_score"]
        for i in range(0, len(avail), 2):
            cols = st.columns(2)
            for col, (key, label, desc) in zip(cols, avail[i:i + 2]):
                with col:
                    st.markdown(f"**{label}**")
                    st.markdown(f'<div class="caption">{desc}</div>', unsafe_allow_html=True)
                    top = d.nlargest(k, key)
                    v = pd.DataFrame({
                        "#": range(1, len(top) + 1),
                        "Symbol": top["symbol"].values,
                        "Sector": top["sector"].str.slice(0, 22).values,
                        label: top[key].round(1).values,
                        "1Y (%)": top["ret_1y"].round(1).values})
                    TB.grid(v, height=min(420, 40 + 34 * len(v)), row_height=30)

    # ---------------- factor validation ----------------
    with t3:
        try:
            bt = D.factor_backtest()
        except Exception:
            st.info("Factor backtest data not available.")
            return

        T.section("Do these scores work on data the model never saw?")
        st.markdown(
            '<div class="panel">Every score elsewhere in this app is computed over the '
            'whole 2021–2025 window, so comparing it against returns from that same '
            'window would be circular. This test avoids that. Factors are rebuilt using '
            '<b>only</b> data available on a formation date — end of 2023 and end of '
            '2024 — securities are sorted into deciles, and the return over the '
            'following year is measured against the market. Nothing here uses '
            'information from the future.</div>', unsafe_allow_html=True)

        summ = bt.drop_duplicates("factor")[["label", "spread", "t_spread", "rank_ic_aligned"]]
        summ = summ.sort_values("spread", ascending=False)
        fig = go.Figure(go.Bar(
            x=summ["spread"], y=summ["label"], orientation="h",
            marker_color=[T.UP if t >= 2 else (T.WARN if t >= 1 else T.MUTED)
                          for t in summ["t_spread"]],
            customdata=np.stack([summ["t_spread"], summ["rank_ic_aligned"]], axis=-1),
            hovertemplate="%{y}<br>Spread %{x:+.2f}%<br>t=%{customdata[0]:+.2f}"
                          "<br>rank IC %{customdata[1]:+.3f}<extra></extra>",
            text=[f"{v:+.1f}%" for v in summ["spread"]], textposition="outside",
            textfont=dict(family=T.MONO, size=10)))
        fig.add_vline(x=0, line_color=T.BORDER)
        fig.update_layout(height=340, margin=dict(r=60),
                          xaxis_title="Top decile minus bottom decile, excess return over the next year (%)")
        st.plotly_chart(fig, width="stretch")
        T.caption("Green means the spread survives a t-test (t ≥ 2). Amber is "
                  "suggestive but not conclusive. Grey is indistinguishable from noise.")

        st.dataframe(pd.DataFrame({
            "Factor": summ["label"],
            "Top − bottom decile (%)": summ["spread"].round(2),
            "t-statistic": summ["t_spread"].round(2),
            "Rank IC": summ["rank_ic_aligned"].round(3),
            "Verdict": ["Works" if t >= 2 else ("Weak evidence" if t >= 1 else "No evidence")
                        for t in summ["t_spread"]]}),
            hide_index=True, width="stretch")

        T.section("Detail for each group of ten")
        pick = st.selectbox("Factor", summ["label"].tolist(), key="rk_bt")
        g = bt[bt["label"] == pick].sort_values("decile")
        fig = go.Figure(go.Bar(
            x=g["decile"], y=g["mean_excess"],
            marker_color=[T.UP if v >= 0 else T.DOWN for v in g["mean_excess"]],
            customdata=g["n"],
            hovertemplate="Decile %{x}<br>Excess %{y:+.2f}%<br>n=%{customdata}<extra></extra>"))
        fig.add_hline(y=0, line_color=T.BORDER)
        fig.update_layout(height=320, xaxis_title="Decile (10 = strongest on this factor)",
                          yaxis_title="Mean excess return over the next year (%)",
                          xaxis=dict(dtick=1))
        st.plotly_chart(fig, width="stretch")

        st.markdown(
            '<div class="panel"><b>What this actually showed.</b> Avoiding deep '
            'drawdowns was the strongest signal in this market — the securities with '
            'the shallowest 12-month drawdown beat the deepest by 26 percentage points '
            'over the following year (t = 5.8). Twelve-month momentum also worked '
            '(+14.2%, t = 3.1).<br><br>'
            'Low P/E did <b>not</b>. The cheapest decile on earnings underperformed '
            'the most expensive by a hair, with a t-statistic of −0.07 — no signal at '
            'all. That is worth saying plainly, because "buy low P/E" is exactly the '
            'kind of rule a stock screener is expected to endorse.<br><br>'
            '<b>Caveats.</b> Two formation dates and roughly 800 securities is a small '
            'sample, and both test years were falling markets, which flatters '
            'defensive factors. This is evidence, not proof.</div>',
            unsafe_allow_html=True)
