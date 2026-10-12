# -*- coding: utf-8 -*-
"""Corrections applied to the factor table before anything reads it.

Every rule here exists because an audit of the built factor table found a value
that was arithmetically valid but economically meaningless, or a label that
promised more than the data behind it could deliver. Each one records the case
that exposed it, so the reasoning survives after the numbers change.

The corrections run inside ``data.factors()``, which means no page, score or
recommendation can see the uncorrected values.
"""
import numpy as np
import pandas as pd

# A stock that has not printed a trade in this many calendar days is treated as
# no longer trading. The gap between an ordinary holiday cluster (~10 days) and
# a genuine suspension is wide, so the exact threshold is not delicate.
INACTIVE_AFTER_DAYS = 20

# Below this many trading days a security has not lived through three years, so
# a "3 year return" for it would be a return over whatever time it has existed.
MIN_DAYS_FOR_3Y = 700          # ~2.8 trading years, allows for holiday variation
MIN_DAYS_FOR_1Y = 220          # ~0.9 trading years

# A trailing yield is dividends already paid divided by today's price. When the
# price collapses the ratio explodes even though nothing good happened, so a
# yield above this is treated as a symptom rather than a payout.
YIELD_SUSPECT_PCT = 12.0
YIELD_TRAP_DRAWDOWN = -30.0    # ...and the price fell at least this much in a year
YIELD_SCORING_CAP = 10.0       # yield above this earns no extra credit

# Beyond this a P/E is a statement about earnings being near zero, not about how
# expensive the stock is.
PE_MAX_MEANINGFUL = 150.0

# A margin outside this band means revenue and profit are not measuring the same
# thing — a holding company booking investment gains outside revenue, or a
# securities firm reporting negative revenue after trading losses.
MARGIN_BAND = 150.0

# Exiting a position without moving the price means taking only a fraction of a
# normal day's turnover. Twenty percent is the common desk rule of thumb.
PARTICIPATION = 0.20
EXIT_POSITION_THB = 500_000


def _num(df, col):
    return pd.to_numeric(df[col], errors="coerce") if col in df.columns else None


def apply(df: pd.DataFrame, last_trading_day: pd.Timestamp) -> pd.DataFrame:
    """Return a corrected copy of the factor table plus the flags it earned."""
    d = df.copy()
    log = []

    def note(rule, n, detail):
        log.append({"rule": rule, "rows": int(n), "detail": detail})

    # ------------------------------------------------------- 1. dead entries
    # Audit case: WELL last traded 25 Oct 2021 and still carried an overall
    # score of 53.6 — above the median of the live universe — because every
    # factor was computed from its final, four-year-old prices.
    if "last_date" in d.columns:
        ld = pd.to_datetime(d["last_date"], errors="coerce")
        d["days_since_trade"] = (last_trading_day - ld).dt.days
        d["is_active"] = (d["days_since_trade"] <= INACTIVE_AFTER_DAYS).fillna(False)
        note("inactive", (~d["is_active"]).sum(),
             f"no trade in {INACTIVE_AFTER_DAYS} days — hidden from tables by default")
    else:
        d["days_since_trade"] = np.nan
        d["is_active"] = True

    # -------------------------------------------------- 2. horizons not lived
    # Audit case: 88TH has 59 trading days of history but reported a 3-year
    # return of -46.34% — identical to its 1-year return, because both were
    # "return since listing" wearing different labels.
    nd = _num(d, "n_days")
    if nd is not None:
        for col, need in (("ret_3y", MIN_DAYS_FOR_3Y), ("cagr", MIN_DAYS_FOR_3Y),
                          ("ret_1y", MIN_DAYS_FOR_1Y), ("vol_1y", MIN_DAYS_FOR_1Y),
                          ("beta_1y", MIN_DAYS_FOR_1Y), ("max_dd_1y", MIN_DAYS_FOR_1Y),
                          ("sharpe_1y", MIN_DAYS_FOR_1Y)):
            if col in d.columns:
                short = nd < need
                n = int((short & _num(d, col).notna()).sum())
                d.loc[short, col] = np.nan
                if n:
                    note(col, n, f"fewer than {need} trading days of history")
        d["history_days"] = nd

    # ------------------------------------------------------ 3. the yield trap
    # Audit case: RS showed a 48.22% yield and an income score of 84.8 while the
    # price was down 96.3% over the year. The payout was ordinary; the
    # denominator had collapsed.
    dy = _num(d, "dividend_yield")
    r1 = _num(d, "ret_1y")
    if dy is not None:
        trap = dy > YIELD_SUSPECT_PCT
        if r1 is not None:
            trap = trap & (r1 < YIELD_TRAP_DRAWDOWN)
        d["yield_trap"] = trap.fillna(False)
        # The raw yield stays visible — hiding it would hide the warning too —
        # but a separate column is what earns points.
        d["dividend_yield_scoring"] = dy.clip(upper=YIELD_SCORING_CAP)
        d.loc[d["yield_trap"], "dividend_yield_scoring"] = 0.0
        note("yield_trap", d["yield_trap"].sum(),
             f"yield over {YIELD_SUSPECT_PCT:.0f}% produced by a fall of "
             f"{abs(YIELD_TRAP_DRAWDOWN):.0f}%+, not by the payout")

        # The income score ranked almost exactly with the raw yield (Spearman
        # 0.97), which is why RS reached 84.8 on a payout its own collapse had
        # manufactured. Rebuilding from the capped yield keeps the ordering it
        # always had and drops only the part that was an artefact of the
        # denominator. Names with no dividend data keep the neutral 50 the
        # original score gave them.
        if "income_score" in d.columns:
            before = _num(d, "income_score")
            ys = d["dividend_yield_scoring"]
            d["income_score"] = (ys.rank(pct=True) * 100).where(ys.notna(), 50.0).round(1)
            moved = int((before.round(0) != d["income_score"].round(0)).sum())
            note("income_score", moved, "rebuilt from the capped yield")
    else:
        d["yield_trap"] = False
        d["dividend_yield_scoring"] = np.nan

    # ----------------------------------------------------- 4. runaway ratios
    # Audit case: ASIA reported a P/E of 12,664 and one security carried exactly
    # -100000, a sentinel that had leaked into a numeric column.
    pe = _num(d, "pe")
    if pe is not None:
        bad = (pe <= 0) | (pe > PE_MAX_MEANINGFUL) | (pe.abs() >= 99_999)
        n = int((bad & pe.notna()).sum())
        d["pe_unusable"] = bad.fillna(False)
        d.loc[bad, "pe"] = np.nan
        note("pe", n, f"non-positive, sentinel, or above {PE_MAX_MEANINGFUL:.0f}x")

    # ------------------------------------------------- 5. margins that invert
    # Audit case: FNS reported revenue of -1,111,710 and profit of -2,798,880.
    # Dividing one negative by another produced +251.8% — a loss-making company
    # displaying a healthy margin. ACAP showed 2,245% from profit 22x revenue.
    for mcol, rcol in (("ttm_net_margin", "ttm_revenue"),
                       ("net_margin", "ttm_revenue"),
                       ("fcf_margin", "ttm_revenue")):
        m = _num(d, mcol)
        rev = _num(d, rcol)
        if m is None:
            continue
        bad = m.abs() > MARGIN_BAND
        if rev is not None:
            bad = bad | (rev <= 0)
        n = int((bad & m.notna()).sum())
        d.loc[bad, mcol] = np.nan
        if n:
            note(mcol, n, f"revenue not positive, or margin outside \u00b1{MARGIN_BAND:.0f}%")

    # -------------------------------------------------- 6. days to liquidate
    # Thai small caps are thin enough that position size, not conviction, is
    # often the binding constraint. This is how many sessions it takes to leave
    # a 500,000 THB position while staying inside a normal share of the volume.
    turnover = _num(d, "avg_value_20d")
    if turnover is not None:
        capacity = (turnover * PARTICIPATION).replace(0, np.nan)
        exit_days = (EXIT_POSITION_THB / capacity).round(1)
        d["days_to_exit_500k"] = exit_days.replace([np.inf, -np.inf], np.nan)
        note("days_to_exit_500k", (d["days_to_exit_500k"] > 5).sum(),
             f"over five sessions to exit {EXIT_POSITION_THB:,.0f} THB "
             f"at {PARTICIPATION:.0%} of turnover")

    # Stored as plain tuples, not a DataFrame. pandas compares ``attrs`` with
    # ``==`` inside __finalize__, and comparing two DataFrames there returns a
    # DataFrame, which then fails the truthiness check — every nlargest() on the
    # factor table would raise. Tuples compare to a clean bool.
    d.attrs["corrections"] = tuple(
        (r["rule"], r["rows"], r["detail"]) for r in log)
    return d


def log_frame(corrected: pd.DataFrame) -> pd.DataFrame:
    """The correction record, as a table for the methodology page."""
    return pd.DataFrame(list(corrected.attrs.get("corrections", ())),
                        columns=["rule", "rows", "detail"])
