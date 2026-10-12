# -*- coding: utf-8 -*-
"""Technical indicators computed on demand for the chart page."""
import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=max(2, n // 3)).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def bollinger(s: pd.Series, n: int = 20, k: float = 2.0):
    mid = s.rolling(n, min_periods=max(2, n // 3)).mean()
    sd = s.rolling(n, min_periods=max(2, n // 3)).std()
    return mid - k * sd, mid, mid + k * sd


def macd(s: pd.Series, fast=12, slow=26, signal=9):
    line = ema(s, fast) - ema(s, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Attach the standard indicator set to a single-symbol price frame."""
    d = df.copy()
    c = d["close"]
    d["ma20"] = sma(c, 20)
    d["ma50"] = sma(c, 50)
    d["ma200"] = sma(c, 200)
    d["rsi14"] = rsi(c)
    d["bb_low"], d["bb_mid"], d["bb_high"] = bollinger(c)
    d["macd"], d["macd_signal"], d["macd_hist"] = macd(c)
    d["atr14"] = atr(d)
    d["ret"] = c.pct_change() * 100
    return d
