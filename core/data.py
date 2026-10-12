# -*- coding: utf-8 -*-
"""Data access layer. Every loader is cached so pages stay instant."""
import os
import numpy as np
import pandas as pd
import streamlit as st

from core import corrections

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _p(name):
    return os.path.join(DATA, name)


@st.cache_data(show_spinner="Loading price history…")
def prices() -> pd.DataFrame:
    df = pd.read_csv(_p("prices.csv.gz"), parse_dates=["date"])
    df["symbol"] = df["symbol"].astype("category")
    return df


CATEGORICAL = ["company", "market", "industry", "sector",
               "risk_bucket", "liquidity_tier", "size_tier", "latest_period"]


@st.cache_data(show_spinner="Loading factor library…")
def factors() -> pd.DataFrame:
    df = pd.read_csv(_p("factors.csv.gz"))
    # Keep every grouping column a clean string. Some placeholder words are
    # parsed back as NaN by read_csv, and a mixed str/float column breaks sorting.
    for c in CATEGORICAL:
        if c in df.columns:
            df[c] = df[c].fillna("Unclassified").astype(str)
    df["company"] = df["company"].replace("Unclassified", pd.NA).fillna(df["symbol"])
    # Void the values an audit showed to be meaningless, and add the flags that
    # replace them. Nothing downstream sees the raw table.
    df = corrections.apply(df, last_date())
    return df


@st.cache_data
def correction_log() -> pd.DataFrame:
    """What the corrections removed, for the methodology page."""
    return corrections.log_frame(factors())


@st.cache_data
def active_factors() -> pd.DataFrame:
    """The factor table minus securities that have stopped trading.

    This is what every screen, ranking and recommendation should use. The full
    table stays available for the few places that genuinely want history.
    """
    f = factors()
    return f[f["is_active"]].copy()


@st.cache_data
def companies() -> pd.DataFrame:
    return pd.read_csv(_p("companies.csv.gz"))


@st.cache_data
def financials() -> pd.DataFrame:
    return pd.read_csv(_p("financials.csv.gz"))


@st.cache_data(show_spinner="Loading news…")
def news() -> pd.DataFrame:
    """Headlines with both the rule label and the NLP-resolved label."""
    df = pd.read_csv(_p("news_nlp.csv.gz"), parse_dates=["datetime"])
    df["news_category"] = df["final_category"].fillna("other").astype(str)
    df["is_risk_signal"] = df["is_risk_signal_final"].fillna(0).astype(int)
    return df


@st.cache_data
def news_count() -> int:
    return len(news())


@st.cache_data
def nlp_category_weights() -> pd.DataFrame:
    return pd.read_csv(_p("nlp_category_weights.csv"))


@st.cache_data
def nlp_lexicon() -> pd.DataFrame:
    return pd.read_csv(_p("nlp_lexicon.csv"))


@st.cache_data
def nlp_topics() -> pd.DataFrame:
    return pd.read_csv(_p("nlp_topics.csv"))


@st.cache_data
def nlp_meta() -> dict:
    import json
    with open(_p("nlp_meta.json"), encoding="utf-8") as fh:
        return json.load(fh)


@st.cache_data
def factor_backtest() -> pd.DataFrame:
    return pd.read_csv(_p("factor_backtest.csv"))


@st.cache_data
def nlp_report() -> pd.DataFrame:
    return pd.read_csv(_p("nlp_clf_report.csv"), index_col=0)


@st.cache_data
def market_index() -> pd.DataFrame:
    m = pd.read_csv(_p("market_index.csv.gz"), parse_dates=["date"]).sort_values("date")
    m["index_value"] = 100 * (1 + m["ret"].fillna(0)).cumprod()
    return m


@st.cache_data(show_spinner="Building price matrix…")
def close_matrix() -> pd.DataFrame:
    """Rows = date, columns = symbol. Uses the corporate-action adjusted close
    where available so returns across a stock dividend are correct."""
    p = prices()
    col = "adj_close" if "adj_close" in p.columns else "close"
    return p.pivot_table(index="date", columns="symbol", values=col, observed=True)


@st.cache_data
def corporate_actions() -> pd.DataFrame:
    try:
        return pd.read_csv(_p("corporate_actions.csv"), parse_dates=["date"])
    except Exception:
        return pd.DataFrame(columns=["symbol", "date", "share_ratio", "price_ratio"])


@st.cache_data
def symbol_history(symbol: str) -> pd.DataFrame:
    p = prices()
    return p[p["symbol"] == symbol].sort_values("date").reset_index(drop=True)


@st.cache_data
def as_of() -> str:
    return prices()["date"].max().strftime("%d %b %Y")


@st.cache_data
def last_date() -> pd.Timestamp:
    return prices()["date"].max()


@st.cache_data
def universe() -> list:
    return sorted(factors()["symbol"].unique().tolist())


@st.cache_data(show_spinner="Computing breadth…")
def advance_decline() -> pd.DataFrame:
    """Cumulative advance-decline line across the whole universe."""
    p = prices()[["date", "symbol", "close"]].sort_values(["symbol", "date"])
    p["chg"] = p.groupby("symbol", observed=True)["close"].pct_change()
    p = p.dropna(subset=["chg"])
    g = p.groupby("date")["chg"].agg(
        adv=lambda s: int((s > 0).sum()), dec=lambda s: int((s < 0).sum()))
    g = g.reset_index()
    g["net"] = g["adv"] - g["dec"]
    g["ad_line"] = g["net"].cumsum()
    return g


@st.cache_data
def sector_performance() -> pd.DataFrame:
    """Cap-weighted return by sector across several horizons."""
    f = factors()
    d = f[f["market_cap"].notna() & (f["sector"] != "Unclassified")].copy()
    out = []
    for sec, g in d.groupby("sector"):
        w = g["market_cap"] / g["market_cap"].sum()
        row = {"sector": sec, "n": len(g),
               "market_cap": float(g["market_cap"].sum())}
        for col, label in [("ret_1m", "1M"), ("ret_3m", "3M"),
                           ("ret_6m", "6M"), ("ret_1y", "1Y")]:
            m = g[col].notna()
            row[label] = (float((g.loc[m, col] * w[m]).sum() / w[m].sum())
                          if m.any() and w[m].sum() > 0 else np.nan)
        out.append(row)
    return pd.DataFrame(out).sort_values("1Y", ascending=False)
