# -*- coding: utf-8 -*-
"""
Screening engine.

Filters are declared as data so the UI can render them generically and new
criteria can be added in one place. Ready-made strategies are expressed with
exactly the same primitives a user would set by hand — nothing is hidden.
"""
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- field catalogue
# key -> (label, group, unit, decimals, higher_is_better)
FIELDS = {
    "last_close":        ("Price", "Price", "THB", 2, None),
    "market_cap":        ("Market cap", "Size", "THB", 0, None),
    "avg_value_1y":      ("Avg daily value 1Y", "Liquidity", "THB", 0, True),
    "avg_value_20d":     ("Avg daily value 20D", "Liquidity", "THB", 0, True),
    "days_to_exit_500k": ("Days to exit 500k THB", "Liquidity", "days", 1, False),
    "ret_1w":            ("Return 1W", "Momentum", "%", 2, True),
    "ret_1m":            ("Return 1M", "Momentum", "%", 2, True),
    "ret_3m":            ("Return 3M", "Momentum", "%", 2, True),
    "ret_6m":            ("Return 6M", "Momentum", "%", 2, True),
    "ret_1y":            ("Return 1Y", "Momentum", "%", 2, True),
    "ret_3y":            ("Return 3Y", "Momentum", "%", 2, True),
    "cagr":              ("CAGR since 2021", "Momentum", "%", 2, True),
    "vol_30d":           ("Volatility 30D", "Risk", "%", 1, False),
    "vol_90d":           ("Volatility 90D", "Risk", "%", 1, False),
    "vol_1y":            ("Volatility 1Y", "Risk", "%", 1, False),
    "vol_all":           ("Volatility since 2021", "Risk", "%", 1, False),
    "beta_1y":           ("Beta 1Y", "Risk", "x", 2, None),
    "max_dd_1y":         ("Max drawdown 1Y", "Risk", "%", 1, True),
    "max_dd_all":        ("Max drawdown since 2021", "Risk", "%", 1, True),
    "sharpe_1y":         ("Sharpe 1Y", "Risk", "", 2, True),
    "dd_from_peak":      ("Below all-time peak", "Risk", "%", 1, True),
    "pe":                ("P/E", "Valuation", "x", 2, False),
    "pbv":               ("P/BV", "Valuation", "x", 2, False),
    "pe_median_3y":      ("P/E median 3Y", "Valuation", "x", 2, False),
    "dividend_yield":    ("Dividend yield", "Valuation", "%", 2, True),
    "roe":               ("ROE", "Quality", "%", 2, True),
    "roa":               ("ROA", "Quality", "%", 2, True),
    "de":                ("Debt / equity", "Quality", "x", 2, False),
    "net_margin":        ("Net margin", "Quality", "%", 2, True),
    "revenue_growth_yoy": ("Revenue growth YoY", "Growth", "%", 1, True),
    "profit_growth_yoy": ("Profit growth YoY", "Growth", "%", 1, True),
    "revenue_2y_growth": ("Revenue growth 2Y p.a.", "Growth", "%", 1, True),
    "profit_2y_growth":  ("Profit growth 2Y p.a.", "Growth", "%", 1, True),
    "roic":              ("ROIC (TTM)", "Quality", "%", 2, True),
    "free_cash_flow":    ("Free cash flow (TTM)", "Quality", "THB", 0, True),
    "fcf_margin":        ("FCF margin", "Quality", "%", 1, True),
    "accruals":          ("Accruals / assets", "Quality", "%", 1, False),
    "ttm_net_margin":    ("Net margin (TTM)", "Quality", "%", 2, True),
    "quality_fscore":    ("Quality F-score (0-7)", "Quality", "", 0, True),
    "rsi14":             ("RSI (14)", "Technical", "", 1, None),
    "px_vs_ma50":        ("Price vs MA50", "Technical", "%", 2, True),
    "px_vs_ma200":       ("Price vs MA200", "Technical", "%", 2, True),
    "pct_from_52w_high": ("From 52W high", "Technical", "%", 2, None),
    "pct_from_52w_low":  ("From 52W low", "Technical", "%", 2, None),
    "risk_news_2y":      ("Negative news 2Y (rules)", "News", "", 0, False),
    "news_2y":           ("Total news 2Y", "News", "", 0, None),
    "nlp_sentiment":      ("NLP sentiment", "News", "", 3, True),
    "nlp_sentiment_score": ("NLP sentiment rank", "News", "", 1, True),
    "nlp_negative_items_2y": ("NLP negative items 2Y", "News", "", 0, False),
    "nlp_items_2y":      ("NLP items scored 2Y", "News", "", 0, None),
    "value_score":       ("Value score", "Factor score", "", 1, True),
    "quality_score":     ("Quality score", "Factor score", "", 1, True),
    "momentum_score":    ("Momentum score", "Factor score", "", 1, True),
    "lowvol_score":      ("Low-volatility score", "Factor score", "", 1, True),
    "income_score":      ("Income score", "Factor score", "", 1, True),
    "growth_score":      ("Growth score", "Factor score", "", 1, True),
    "overall_score":     ("Overall score", "Factor score", "", 1, True),
}

NUMERIC_FILTERS = [k for k in FIELDS if k != "last_close"]

DEFAULT_COLUMNS = ["symbol", "company", "sector", "last_close", "ret_1y",
                   "vol_1y", "max_dd_1y", "pe", "pbv", "dividend_yield",
                   "roe", "avg_value_1y", "nlp_sentiment_score", "overall_score"]

# ---------------------------------------------------------------- presets
# Each preset is just a set of filters + a sort key, so the user can open it,
# see exactly what it does, and adjust any part of it.
PRESETS = {
    "— None (start blank) —": {},
    "Dividend Income": {
        "desc": "High, well-covered dividend payers with real trading liquidity.",
        "filters": {"dividend_yield": (4.0, None), "avg_value_1y": (10e6, None),
                    "de": (None, 2.5), "vol_1y": (None, 45.0)},
        "exclude_flagged": True, "sort": "dividend_yield",
    },
    "Low Volatility / Defensive": {
        "desc": "The steadiest names in the market — shallow drawdowns and low beta.",
        "filters": {"vol_1y": (None, 25.0), "max_dd_1y": (-30.0, None),
                    "beta_1y": (None, 0.9), "avg_value_1y": (10e6, None)},
        "exclude_flagged": True, "sort": "lowvol_score",
    },
    "Momentum / Trend": {
        "desc": "Names in a confirmed uptrend: above the 200-day average, strong 6-month return.",
        "filters": {"ret_6m": (10.0, None), "px_vs_ma200": (0.0, None),
                    "rsi14": (45.0, 80.0), "avg_value_1y": (20e6, None)},
        "exclude_flagged": True, "sort": "momentum_score",
    },
    "Deep Value": {
        "desc": "Cheap on both earnings and book value, while still profitable.",
        "filters": {"pe": (0.1, 12.0), "pbv": (0.1, 1.5), "roe": (5.0, None),
                    "avg_value_1y": (5e6, None)},
        "exclude_flagged": True, "sort": "value_score",
    },
    "Quality Growth": {
        "desc": "Growing revenue and profit with strong returns on capital and modest leverage.",
        "filters": {"revenue_growth_yoy": (5.0, None), "profit_growth_yoy": (5.0, None),
                    "roe": (12.0, None), "de": (None, 2.0), "avg_value_1y": (10e6, None)},
        "exclude_flagged": True, "sort": "growth_score",
    },
    "Oversold Rebound Candidates": {
        "desc": "Heavily sold names with a low RSI that still have sound fundamentals. "
                "Higher risk — read the news timeline before acting.",
        "filters": {"rsi14": (None, 35.0), "pct_from_52w_high": (None, -20.0),
                    "roe": (0.0, None), "avg_value_1y": (10e6, None)},
        "exclude_flagged": True, "sort": "rsi14", "ascending": True,
    },
    "Clean News Record": {
        "desc": "Liquid names whose disclosure record scores in the top half on "
                "the empirically weighted NLP sentiment measure.",
        "filters": {"nlp_sentiment_score": (60.0, None), "nlp_items_2y": (8.0, None),
                    "avg_value_1y": (10e6, None)},
        "exclude_flagged": True, "sort": "nlp_sentiment_score",
    },
    "Negative News Watch": {
        "desc": "The opposite screen — securities with the weakest news record. "
                "Shown so the signal can be inspected, not as a buy list.",
        "filters": {"nlp_sentiment_score": (None, 15.0), "nlp_items_2y": (8.0, None)},
        "exclude_flagged": False, "sort": "nlp_sentiment_score", "ascending": True,
    },
    "Cash Generative Quality": {
        "desc": "Positive free cash flow, profit backed by cash rather than "
                "accruals, and a quality score of five or better out of seven.",
        "filters": {"free_cash_flow": (0.0, None), "accruals": (None, 0.0),
                    "quality_fscore": (5.0, None), "avg_value_1y": (10e6, None)},
        "exclude_flagged": True, "sort": "quality_fscore",
    },
    "Large Cap Core": {
        "desc": "The most liquid large companies — the natural core of a portfolio.",
        "filters": {"market_cap": (5e10, None), "avg_value_1y": (50e6, None)},
        "exclude_flagged": False, "sort": "market_cap",
    },
}


def apply_filters(df: pd.DataFrame, numeric: dict, sectors=None, markets=None,
                  buckets=None, liquidity=None, size=None,
                  exclude_flagged=False, require_financials=False,
                  min_history=0, search="", exclude_nlp_flagged=False,
                  index_scope=None) -> pd.DataFrame:
    """
    numeric: {field: (min_or_None, max_or_None)}
    Every filter is optional; None means unbounded.
    """
    d = df
    if search:
        s = search.strip().upper()
        d = d[d["symbol"].str.upper().str.contains(s, na=False) |
              d["company"].str.upper().str.contains(s, na=False)]
    if sectors:
        d = d[d["sector"].isin(sectors)]
    if markets:
        d = d[d["market"].isin(markets)]
    if buckets:
        d = d[d["risk_bucket"].isin(buckets)]
    if liquidity:
        d = d[d["liquidity_tier"].isin(liquidity)]
    if size:
        d = d[d["size_tier"].isin(size)]
    if index_scope and "index_proxy" in d.columns:
        d = d[d["index_proxy"].isin(index_scope)]
    if exclude_flagged:
        d = d[d["news_red_flag"] == 0]
    if exclude_nlp_flagged and "nlp_red_flag" in d.columns:
        d = d[d["nlp_red_flag"] == 0]
    if require_financials:
        d = d[d["has_financials"] == 1]
    if min_history:
        d = d[d["n_days"] >= min_history]

    for field, (lo, hi) in (numeric or {}).items():
        if field not in d.columns:
            continue
        if lo is None and hi is None:
            continue
        col = d[field]
        # A row with no value for a field cannot be shown to satisfy it.
        keep = col.notna()
        if lo is not None:
            keep &= col >= lo
        if hi is not None:
            keep &= col <= hi
        d = d[keep]
    return d


def run_preset(df: pd.DataFrame, name: str) -> tuple:
    """Returns (filtered_df, preset_dict)."""
    p = PRESETS.get(name) or {}
    if not p:
        return df, {}
    out = apply_filters(df, p.get("filters", {}),
                        exclude_flagged=p.get("exclude_flagged", False))
    key = p.get("sort", "overall_score")
    if key in out.columns:
        out = out.sort_values(key, ascending=p.get("ascending", False))
    return out, p


def format_table(d: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Rename to display labels and round sensibly for the grid."""
    cols = [c for c in columns if c in d.columns]
    t = d[cols].copy()
    ren = {}
    for c in cols:
        if c in FIELDS:
            label, _grp, unit, dp, _hib = FIELDS[c]
            t[c] = pd.to_numeric(t[c], errors="coerce").round(dp)
            ren[c] = f"{label} ({unit})" if unit else label
        else:
            ren[c] = {"symbol": "Symbol", "company": "Company", "sector": "Sector",
                      "industry": "Industry", "market": "Market",
                      "risk_bucket": "Risk band", "liquidity_tier": "Liquidity",
                      "size_tier": "Size", "latest_period": "Last reported",
                      "news_red_flag": "News flag"}.get(c, c)
    return t.rename(columns=ren)
