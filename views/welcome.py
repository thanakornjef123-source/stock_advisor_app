# -*- coding: utf-8 -*-
"""Welcome — the landing screen shown before the terminal opens."""
import html

import pandas as pd
import streamlit as st

from core import data as D
from core import store
from core import theme as T

FEATURES = [
    ("01", "Market overview",
     "Index level, breadth, cap-weighted sector performance and a risk/return "
     "map of every listed security on one screen."),
    ("02", "Heat map",
     "The whole market as a treemap, sized by capitalisation and coloured by "
     "return, with click-through into any industry or sector."),
    ("03", "Rankings",
     "Composite A+ to F grades across six style factors, leaderboards for each, "
     "and an out-of-sample test of which factors actually paid."),
    ("04", "Screener",
     "Forty-two numeric criteria, seven ready-made strategies you can open and "
     "edit, custom columns and CSV export."),
    ("05", "News intelligence",
     "Every disclosure classified by an NLP pipeline, then validated against the "
     "price reaction that followed it."),
    ("06", "Portfolio construction",
     "A suitability assessment sets your equity ceiling and eligible universe, "
     "then the model builds and tests a portfolio around it."),
]

NEWS_LABEL = {
    "financial_statement": "Financials", "mdna": "MD&A", "dividend": "Dividend",
    "capital_increase": "Capital raise", "warrant": "Warrant", "mna": "M&A",
    "board_change": "Board", "shareholder_meeting": "Meeting",
    "share_repurchase": "Buyback", "subsidiary_action": "Subsidiary",
    "trading_sign_halt": "Trading sign", "delisting": "Delisting",
    "set_clarification": "SET query", "litigation": "Litigation",
    "capital_reduction": "Capital cut", "resignation": "Resignation",
    "market_surveillance": "Surveillance", "book_closure": "Book closure",
    "corporate_admin": "Admin", "public_presentation": "Presentation",
    "connected_txn": "Related party", "ipo_listing": "Listing",
    "date_only_corrupted": "—", "other": "Other",
}


def _rows(d, change_col):
    out = []
    for r in d.itertuples():
        chg = getattr(r, change_col)
        cls = "up" if (pd.notna(chg) and chg >= 0) else "dn"
        sign = "+" if (pd.notna(chg) and chg >= 0) else ""
        comp = html.escape(str(r.company).title()[:38])
        out.append(
            f'<div class="lp-row">'
            f'<div class="lp-tick">{html.escape(str(r.symbol)[:4])}</div>'
            f'<div class="lp-nm"><div class="s">{html.escape(str(r.symbol))}</div>'
            f'<div class="c">{comp}</div></div>'
            f'<div class="lp-px">{r.last_close:,.2f}</div>'
            f'<div class="lp-ch {cls}">{sign}{chg:.2f}%</div></div>')
    return "".join(out)


def _movers_card():
    f = D.active_factors()
    d = f[f["avg_value_1y"].fillna(0) >= 10e6].dropna(subset=["ret_1m"])
    st.markdown(
        '<div class="lp-card-h" style="margin-bottom:2px">'
        '<div class="t">Market movers</div>'
        f'<div class="m">1 MONTH · AS OF {D.as_of().upper()}</div></div>',
        unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["Gainers", "Losers", "Most active"])
    with t1:
        st.markdown(_rows(d.nlargest(5, "ret_1m"), "ret_1m"), unsafe_allow_html=True)
    with t2:
        st.markdown(_rows(d.nsmallest(5, "ret_1m"), "ret_1m"), unsafe_allow_html=True)
    with t3:
        st.markdown(_rows(d.nlargest(5, "avg_value_20d"), "ret_1m"),
                    unsafe_allow_html=True)
    st.caption("Restricted to securities trading at least 10M THB per day.")


def _news_card():
    nw = D.news()
    recent = nw[nw["symbol"].notna()].sort_values("datetime", ascending=False).head(5)
    rows = []
    for r in recent.itertuples():
        cat = NEWS_LABEL.get(r.news_category, r.news_category)
        neg = " neg" if int(getattr(r, "is_risk_signal", 0) or 0) else ""
        head = html.escape(str(r.subject))[:96]
        rows.append(
            f'<div class="lp-news"><div class="h">{head}</div>'
            f'<div class="m"><span class="lp-tag{neg}">{html.escape(str(cat))}</span>'
            f'{html.escape(str(r.symbol))} · {r.datetime:%d %b %Y}</div></div>')
    st.markdown(
        '<div class="lp-card"><div class="lp-card-h">'
        '<div class="t">Latest disclosures</div>'
        '<div class="m">CLASSIFIED BY NLP</div></div>'
        + "".join(rows) + '</div>', unsafe_allow_html=True)


def _backdrop() -> str:
    """The market index itself, drawn as the backdrop of the landing page."""
    try:
        m = D.market_index()
    except Exception:
        return ""
    v = m["index_value"].to_numpy(dtype=float)
    if len(v) < 20:
        return ""
    step = max(1, len(v) // 220)
    v = v[::step]
    lo, hi = float(v.min()), float(v.max())
    rng = (hi - lo) or 1.0
    W, H = 1440.0, 620.0
    pts = [(i / (len(v) - 1) * W, H - 60 - ((x - lo) / rng) * (H - 190))
           for i, x in enumerate(v)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{H} " + line + f" {W},{H}"

    return (
        f'<div class="lp-bg"><svg viewBox="0 0 {W:.0f} {H:.0f}" '
        f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
        f'<defs><linearGradient id="lpfill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{T.ACCENT}" stop-opacity=".085"/>'
        f'<stop offset="100%" stop-color="{T.ACCENT}" stop-opacity="0"/>'
        f'</linearGradient>'
        f'<linearGradient id="lpline" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0%" stop-color="{T.UP}" stop-opacity=".26"/>'
        f'<stop offset="55%" stop-color="{T.ACCENT}" stop-opacity=".34"/>'
        f'<stop offset="100%" stop-color="{T.ACCENT}" stop-opacity=".12"/>'
        f'</linearGradient></defs>'
        f'<polygon points="{area}" fill="url(#lpfill)"/>'
        f'<polyline points="{line}" fill="none" stroke="url(#lpline)" '
        f'stroke-width="1.35" stroke-linejoin="round" stroke-linecap="round"/>'
        f'</svg></div>')


def render():
    st.markdown(_backdrop(), unsafe_allow_html=True)
    meta = {}
    try:
        meta = D.nlp_meta()
    except Exception:
        pass
    n_news = meta.get("n_headlines", 148733)
    total = 961842 + n_news + 15160

    left, right = st.columns([1.06, 1], gap="large")

    with left:
        st.markdown(
            f'<div class="lp-wrap">'
            f'<div class="lp-num">{total:,}</div>'
            f'<div class="lp-head">RECORDS<br>ANALYSED</div>'
            f'<div class="lp-sub">Equity research and portfolio construction '
            f'for the Stock Exchange of Thailand</div>'
            f'<div class="lp-lede">Five years of exchange data, cleaned and '
            f'documented. Answer ten questions, get a portfolio built around '
            f'your tolerance for risk, and check the reasoning yourself.</div>'
            f'<div class="lp-awards">'
            f'<div class="lp-award"><div class="n">{len(D.universe())}</div>'
            f'<div class="t">Listed securities</div></div>'
            f'<div class="lp-award"><div class="n">94</div>'
            f'<div class="t">Metrics per security</div></div>'
            f'<div class="lp-award"><div class="n">{meta.get("n_categories_final", 29)}</div>'
            f'<div class="t">News categories</div></div>'
            f'<div class="lp-award"><div class="n">5</div>'
            f'<div class="t">Years of history</div></div>'
            f'</div></div>', unsafe_allow_html=True)

        st.write("")
        c = st.columns([1.25, 1, 1.05, 0.5])
        if c[0].button("Enter terminal  →", type="primary", width="stretch",
                       key="wc_enter"):
            st.session_state["entered"] = True
            st.session_state["show_onboarding"] = True
            st.rerun()
        if c[1].button("Risk profile", width="stretch", key="wc_profile"):
            st.session_state["entered"] = True
            st.session_state["onboarded"] = True
            st.session_state["page"] = "Risk Profile"
            st.rerun()
        if c[2].button("Methodology", width="stretch", key="wc_method"):
            st.session_state["entered"] = True
            st.session_state["onboarded"] = True
            st.session_state["page"] = "News Intelligence"
            st.rerun()
        st.markdown(
            '<div class="caption" style="margin-top:6px">No account, no sign-in. '
            + ('Nothing you enter is stored on the server — your watchlist and '
               'holdings live in this browser session only.'
               if store.SHARED else
               'Everything runs locally on this machine.')
            + '</div>',
            unsafe_allow_html=True)

    with right:
        st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)
        with st.container(border=True):
            _movers_card()
        _news_card()

    st.write("")
    T.section("What is inside",
              "Thirteen tools, all built on the same cleaned exchange data.")
    for row in (FEATURES[:3], FEATURES[3:]):
        cols = st.columns(3)
        for col, (icon, head, body) in zip(cols, row):
            col.markdown(
                f'<div class="feature"><div class="ico">{icon}</div>'
                f'<div class="h">{head}</div><div class="b">{body}</div></div>',
                unsafe_allow_html=True)
        st.write("")

    st.markdown(
        '<div class="caption" style="margin-top:18px">Educational research tool '
        'built on historical data ending December 2025. Not investment advice, '
        'not a recommendation to buy or sell any security, and no part of it is '
        'a forecast. Past behaviour does not predict future results.</div>',
        unsafe_allow_html=True)


def onboarding_banner():
    """Shown once, in the page itself.

    This started life as a modal. Modals in Streamlit re-run as fragments and
    the buttons proved unreliable, so it is now an ordinary panel — which is
    also easier to ignore, which is the point of an optional step.
    """
    st.markdown(
        '<div class="onboard">'
        '<div class="h">Set your risk profile first?</div>'
        '<div class="b">Everything here works without it. The '
        '<b>Recommended Portfolio</b> page is the exception — it needs to know '
        'how much risk you can carry before it can suggest anything. The '
        'questionnaire is the standard ten-question suitability test and takes '
        'about two minutes.</div></div>', unsafe_allow_html=True)
    a, b, _ = st.columns([1.4, 1.1, 4])
    if a.button("Take the assessment", type="primary", width="stretch",
                key="ob_take"):
        st.session_state["onboarded"] = True
        st.session_state["page"] = "Risk Profile"
        st.rerun()
    if b.button("Not now", width="stretch", key="ob_skip"):
        st.session_state["onboarded"] = True
        st.rerun()
