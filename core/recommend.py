# -*- coding: utf-8 -*-
"""
Portfolio construction for a given investor profile.

Two layers:
  1. Asset allocation — the equity ceiling comes straight from the suitability
     profile (Conservative = fixed income only, up to Aggressive = 100% equity).
  2. Stock selection — hard eligibility filters, then a scoring model whose
     weights change with the profile, then sector-capped selection and
     risk-aware weighting.
"""
import numpy as np
import pandas as pd

MIN_HISTORY_DAYS = 250          # at least one year of prices
MIN_DAILY_VALUE = 1_000_000     # at least 1M THB traded per day
MAX_PER_SECTOR = 2              # diversification cap

# Scoring weights by profile. Conservative investors are rewarded for low
# volatility and income; aggressive investors for growth and quality.
WEIGHTS = {
    1: {"lowvol": 26, "drawdown": 18, "income": 18, "growth": 5,  "quality": 13, "liquidity": 8,  "news": 12},
    2: {"lowvol": 22, "drawdown": 13, "income": 16, "growth": 11, "quality": 13, "liquidity": 13, "news": 12},
    3: {"lowvol": 13, "drawdown": 10, "income": 10, "growth": 23, "quality": 18, "liquidity": 14, "news": 12},
    4: {"lowvol": 7,  "drawdown": 7,  "income": 7,  "growth": 32, "quality": 22, "liquidity": 13, "news": 12},
    5: {"lowvol": 0,  "drawdown": 4,  "income": 4,  "growth": 40, "quality": 27, "liquidity": 13, "news": 12},
}


def asset_allocation(profile: dict) -> pd.DataFrame:
    """Top-level split between equities and fixed income."""
    eq = float(profile["equity_cap"])
    if eq == 0:
        rows = [("Cash and short-term deposits", 0.40),
                ("Government bonds", 0.40),
                ("Investment-grade corporate bonds", 0.20),
                ("Thai equities", 0.00)]
    else:
        safe = 1 - eq
        rows = [("Cash and short-term deposits", safe * 0.40),
                ("Government bonds", safe * 0.35),
                ("Investment-grade corporate bonds", safe * 0.25),
                ("Thai equities", eq)]
    df = pd.DataFrame(rows, columns=["Asset class", "Weight"])
    df["Weight"] = df["Weight"] / df["Weight"].sum()
    return df


def eligible(f: pd.DataFrame, profile: dict) -> pd.DataFrame:
    """Hard eligibility rules — a name must clear all of these."""
    d = f.copy()
    if "is_active" in d.columns:
        # A suspended name still carries a full set of factor values, computed
        # from its last live prices. It cannot be bought, so it cannot be
        # recommended.
        d = d[d["is_active"]]
    if "yield_trap" in d.columns:
        # A yield manufactured by a price collapse is not income.
        d = d[~d["yield_trap"]]
    d = d[d["n_days"] >= MIN_HISTORY_DAYS]
    d = d[d["avg_value_1y"].fillna(0) >= MIN_DAILY_VALUE]
    d = d[d["news_red_flag"] == 0]
    if "nlp_red_flag" in d.columns:
        # Sentiment measured against actual post-news returns, not a keyword guess.
        d = d[d["nlp_red_flag"] == 0]
    d = d[d["risk_bucket"].isin(profile["allowed_buckets"])]
    d = d[d["liquidity_tier"].isin(profile["liquidity"])]
    d = d[d["vol_all"].notna()]
    mb = profile.get("max_beta")
    if mb is not None:
        d = d[d["beta_1y"].isna() | (d["beta_1y"] <= mb)]
    return d


def score(d: pd.DataFrame, level: int) -> pd.Series:
    """Profile-weighted composite, expressed 0-100."""
    def pr(col, ascending=True):
        return d[col].rank(pct=True, ascending=ascending).fillna(0.5)

    w = WEIGHTS.get(level, WEIGHTS[3])
    s = (pr("vol_all", False) * w["lowvol"] +
         pr("max_dd_all", True) * w["drawdown"] +
         pr("dividend_yield", True) * w["income"] +
         pr("cagr", True) * w["growth"] * 0.5 +
         pr("ret_1y", True) * w["growth"] * 0.5 +
         pr("roe", True) * w["quality"] * 0.6 +
         pr("de", False) * w["quality"] * 0.4 +
         pr("avg_value_1y", True) * w["liquidity"] +
         (pr("nlp_sentiment", True) * w["news"]
          if "nlp_sentiment" in d.columns else w["news"] * 0.5))
    return s.round(1)


def build(f: pd.DataFrame, profile: dict, n: int = 10) -> pd.DataFrame:
    """Select n names, sector-capped, and assign weights."""
    pool = eligible(f, profile)
    if pool.empty:
        return pool
    pool = pool.assign(fit_score=score(pool, profile["level"]))
    pool = pool.sort_values("fit_score", ascending=False)

    picked, per_sector = [], {}
    for _, row in pool.iterrows():
        sec = row["sector"]
        if per_sector.get(sec, 0) >= MAX_PER_SECTOR:
            continue
        picked.append(row)
        per_sector[sec] = per_sector.get(sec, 0) + 1
        if len(picked) >= n:
            break
    if len(picked) < n:                      # top up if sector caps bit too hard
        have = {r["symbol"] for r in picked}
        for _, row in pool.iterrows():
            if row["symbol"] in have:
                continue
            picked.append(row)
            if len(picked) >= n:
                break

    out = pd.DataFrame(picked).reset_index(drop=True)
    if out.empty:
        return out

    if profile["level"] <= 3:
        # Inverse-volatility weighting damps the volatility of the whole book.
        raw = 1 / out["vol_all"].clip(lower=1)
    else:
        # Growth mandates should not penalise a name simply for being volatile.
        raw = out["fit_score"].clip(lower=1)
    w = (raw / raw.sum()).round(4)
    # Rounding to four places can leave the sum a hair off 1.0, which then makes
    # the cash amounts miss the equity sleeve. Absorb the residual in the
    # largest position so the weights always total exactly 100%.
    residual = 1.0 - float(w.sum())
    if abs(residual) > 0:
        w.iloc[int(np.argmax(w.values))] += residual
    out["weight"] = w.values
    out["rationale"] = out.apply(_rationale, axis=1)
    return out


def _rationale(r) -> str:
    bits = []
    if pd.notna(r.get("vol_all")):
        bits.append(f"{r['vol_all']:.0f}% annualised volatility ({r['risk_bucket']})")
    if pd.notna(r.get("max_dd_all")):
        bits.append(f"worst drawdown {r['max_dd_all']:.0f}%")
    if pd.notna(r.get("dividend_yield")) and r["dividend_yield"] >= 3:
        bits.append(f"{r['dividend_yield']:.1f}% dividend yield")
    if pd.notna(r.get("cagr")) and r["cagr"] > 0:
        bits.append(f"{r['cagr']:.1f}% per-year price growth since 2021")
    if pd.notna(r.get("roe")) and r["roe"] > 8:
        bits.append(f"ROE {r['roe']:.1f}%")
    if pd.notna(r.get("beta_1y")):
        bits.append(f"beta {r['beta_1y']:.2f}")
    bits.append(f"{r['liquidity_tier'].lower()} liquidity")
    if pd.notna(r.get("nlp_sentiment_score")):
        bits.append(f"news sentiment in the {r['nlp_sentiment_score']:.0f}th percentile")
    if r.get("risk_news_2y", 0) == 0:
        bits.append("no negative news in two years")
    return " · ".join(bits)


def money_table(picks: pd.DataFrame, alloc: pd.DataFrame, amount: float) -> pd.DataFrame:
    """Translate weights into actual baht amounts."""
    eq = float(alloc.loc[alloc["Asset class"] == "Thai equities", "Weight"].iloc[0])
    t = picks.copy()
    t["equity_weight"] = t["weight"]
    t["portfolio_weight"] = t["weight"] * eq
    t["amount"] = (t["weight"] * amount * eq).round(0)
    t["shares"] = np.where(t["last_close"] > 0,
                           np.floor(t["amount"] / t["last_close"] / 100) * 100, 0)
    return t


def portfolio_stats(picks: pd.DataFrame) -> dict:
    """Weighted characteristics of the equity sleeve."""
    if picks.empty:
        return {}
    w = picks["weight"]

    def wa(col):
        m = picks[col].notna()
        return float((picks.loc[m, col] * w[m]).sum() / w[m].sum()) if m.any() else np.nan

    return {
        "Weighted volatility": wa("vol_all"),
        "Weighted beta": wa("beta_1y"),
        "Weighted dividend yield": wa("dividend_yield"),
        "Weighted 1Y return": wa("ret_1y"),
        "Weighted CAGR": wa("cagr"),
        "Weighted P/E": wa("pe"),
        "Sectors covered": float(picks["sector"].nunique()),
    }
