# -*- coding: utf-8 -*-
"""
The table system.

Tables are where anyone using a terminal spends most of their time, so they get
the same treatment a commercial platform gives them: numbers coloured by value
so a column can be read at a glance, sparklines in the row, score bars, and
rows that can be clicked through to the security.

Every page builds its grids through `grid()` so the whole application stays
consistent and a change here lands everywhere.
"""
import json
import os

import numpy as np
import pandas as pd
import streamlit as st

from core import theme as T

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# columns whose values are a signed percentage and should be shaded
PCT_HINTS = ("%", "return", "1w", "1m", "3m", "6m", "1y", "3y", "cagr", "p&l",
             "growth", "vs ma", "from 52", "drawdown", "dd")
# columns that are a 0-100 score and get a bar
SCORE_HINTS = ("score", "rank", "overall", "value", "quality", "momentum",
               "low vol", "income", "growth score", "news rank")


@st.cache_data
def sparklines() -> dict:
    p = os.path.join(DATA, "sparklines.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def add_spark(df: pd.DataFrame, symbol_col: str = "Symbol",
              label: str = "60d") -> pd.DataFrame:
    """Attach a rebased 60-session price series as a list column."""
    sp = sparklines()
    if not sp or symbol_col not in df.columns:
        return df
    out = df.copy()
    out.insert(min(3, len(out.columns)), label,
               [sp.get(str(s), []) for s in out[symbol_col]])
    return out


def _diverging(v, lo, hi):
    """Red below zero, green above, alpha scaled by magnitude."""
    if pd.isna(v):
        return ""
    if v >= 0:
        a = 0.10 + 0.42 * (min(v, hi) / hi if hi else 0)
        return f"background-color: rgba(38,166,154,{a:.3f}); color: #8FE3D5;"
    a = 0.10 + 0.42 * (min(-v, -lo) / -lo if lo else 0)
    return f"background-color: rgba(239,83,80,{a:.3f}); color: #F5A9A7;"


def _sequential(v, lo, hi):
    """Neutral to accent, for one-sided quantities."""
    if pd.isna(v) or hi == lo:
        return ""
    t = (v - lo) / (hi - lo)
    return f"background-color: rgba(45,140,255,{0.06 + 0.34 * t:.3f});"


def style(df: pd.DataFrame, pct_cols=None, seq_cols=None):
    """Return a Styler with value-scaled cell backgrounds."""
    num = df.select_dtypes("number").columns
    if pct_cols is None:
        pct_cols = [c for c in num
                    if any(h in str(c).lower() for h in PCT_HINTS)]
    if seq_cols is None:
        seq_cols = []
    pct_cols = [c for c in pct_cols if c in df.columns]
    seq_cols = [c for c in seq_cols if c in df.columns and c not in pct_cols]

    sty = df.style
    for c in pct_cols:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().sum() == 0:
            continue
        hi = float(np.nanpercentile(s[s > 0], 85)) if (s > 0).any() else 1.0
        lo = float(np.nanpercentile(s[s < 0], 15)) if (s < 0).any() else -1.0
        hi = hi if hi > 0 else 1.0
        lo = lo if lo < 0 else -1.0
        sty = sty.map(lambda v, lo=lo, hi=hi: _diverging(v, lo, hi), subset=[c])
    for c in seq_cols:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().sum() == 0:
            continue
        lo, hi = float(np.nanmin(s)), float(np.nanmax(s))
        sty = sty.map(lambda v, lo=lo, hi=hi: _sequential(v, lo, hi), subset=[c])
    return sty


def config(df: pd.DataFrame, spark_label: str = "60d",
           money_cols=(), extra=None) -> dict:
    """Column configuration: sparklines, score bars, money formatting."""
    cfg = {}
    if spark_label in df.columns:
        cfg[spark_label] = st.column_config.LineChartColumn(
            spark_label, width="small", color=T.ACCENT,
            help="Closing prices over the last 60 sessions, rebased to 100")
    for c in df.columns:
        lc = str(c).lower()
        if c in money_cols:
            cfg[c] = st.column_config.NumberColumn(c, format="%,.0f")
        elif any(h in lc for h in SCORE_HINTS) and pd.api.types.is_numeric_dtype(df[c]):
            s = pd.to_numeric(df[c], errors="coerce")
            if s.notna().any() and 0 <= s.min() and s.max() <= 100:
                cfg[c] = st.column_config.ProgressColumn(
                    c, format="%.0f", min_value=0, max_value=100, color=T.ACCENT)
    if extra:
        cfg.update(extra)
    return cfg


def grid(df: pd.DataFrame, *, height: int = 420, spark: bool = False,
         symbol_col: str = "Symbol", pct_cols=None, seq_cols=None,
         money_cols=(), select: bool = False, key: str = None,
         row_height: int = 32, extra_config=None):
    """
    One entry point for every table in the application.

    select=True makes rows clickable and returns the chosen symbol, which is how
    the screener, rankings and watchlist hand off to Security Detail.
    """
    d = df.copy()
    if spark:
        d = add_spark(d, symbol_col)
    styled = style(d, pct_cols, seq_cols)
    cfg = config(d, money_cols=money_cols, extra=extra_config)
    kwargs = dict(hide_index=True, width="stretch", height=height,
                  column_config=cfg, row_height=row_height)
    if select:
        ev = st.dataframe(styled, key=key, on_select="rerun",
                          selection_mode="single-row", **kwargs)
        rows = (ev.selection.rows if ev and getattr(ev, "selection", None) else [])
        if rows and symbol_col in d.columns:
            return str(d.iloc[rows[0]][symbol_col])
        return None
    st.dataframe(styled, key=key, **kwargs)
    return None


def open_security(symbol: str, note: str = "Opening security detail"):
    """Jump to the detail page for a symbol chosen in a table."""
    if not symbol:
        return
    st.session_state["detail_symbol"] = symbol
    st.session_state["page"] = "Security Detail"
    st.toast(f"{note} · {symbol}", icon="◧")
    st.rerun()
