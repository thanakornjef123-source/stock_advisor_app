# -*- coding: utf-8 -*-
"""Historical portfolio simulation from actual closing prices."""
import numpy as np
import pandas as pd

TD = 252
RISK_FREE = 2.0     # assumed annual risk-free rate, in percent


def simulate(close: pd.DataFrame, weights: dict, start=None, end=None,
             initial: float = 100_000.0, rebalance: str = "hold",
             commission_pct: float = 0.0, sell_tax_pct: float = 0.0) -> pd.DataFrame:
    """
    close          : DataFrame indexed by date, one column per symbol
    weights        : {symbol: weight}, need not sum to exactly 1
    rebalance      : 'hold' (buy once) or 'monthly' (reset to target each month)
    commission_pct : brokerage plus VAT, charged on both sides of every trade
    sell_tax_pct   : any additional levy charged on sales only
    """
    syms = [s for s in weights if s in close.columns]
    if not syms:
        return pd.DataFrame()
    px = close[syms].copy()
    if start is not None:
        px = px[px.index >= pd.Timestamp(start)]
    if end is not None:
        px = px[px.index <= pd.Timestamp(end)]
    px = px.dropna(how="all").ffill().dropna()
    if len(px) < 2:
        return pd.DataFrame()

    w = np.array([float(weights[s]) for s in px.columns], dtype=float)
    if w.sum() <= 0:
        return pd.DataFrame()
    w = w / w.sum()

    buy_cost = commission_pct / 100.0
    sell_cost = (commission_pct + sell_tax_pct) / 100.0
    cash0 = initial * (1 - buy_cost)          # entry commission

    if rebalance == "monthly":
        month = px.index.to_period("M")
        units = cash0 * w / px.iloc[0].values
        vals = []
        for i in range(len(px)):
            v = float((units * px.iloc[i].values).sum())
            vals.append(v)
            if i + 1 < len(px) and month[i + 1] != month[i]:
                # only the part of the book that actually changes hands is charged
                target = v * w
                current = units * px.iloc[i].values
                turnover = float(np.abs(target - current).sum()) / 2.0
                v -= turnover * (buy_cost + sell_cost)
                vals[-1] = v
                units = v * w / px.iloc[i].values
        series = pd.Series(vals, index=px.index)
    else:
        units = cash0 * w / px.iloc[0].values
        series = (px * units).sum(axis=1)

    series = series.copy()
    if sell_cost:                              # exit commission on the final day
        series.iloc[-1] = series.iloc[-1] * (1 - sell_cost)
    out = pd.DataFrame({"date": px.index, "value": series.values})
    out["return_pct"] = (out["value"] / initial - 1) * 100
    out["drawdown_pct"] = (out["value"] / out["value"].cummax() - 1) * 100
    return out


def metrics(series: pd.Series) -> dict:
    s = pd.Series(series).dropna()
    if len(s) < 2:
        return {}
    r = s.pct_change().dropna()
    if isinstance(s.index, pd.DatetimeIndex):
        years = max((s.index[-1] - s.index[0]).days / 365.25, 1e-9)
    else:
        years = len(s) / TD
    total = float(s.iloc[-1] / s.iloc[0] - 1) * 100
    cagr = float((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100
    vol = float(r.std() * np.sqrt(TD) * 100)
    dd = float(((s / s.cummax()) - 1).min() * 100)
    downside = r[r < 0]
    dvol = float(downside.std() * np.sqrt(TD) * 100) if len(downside) > 2 else np.nan
    return {
        "Total return": total,
        "CAGR": cagr,
        "Volatility": vol,
        "Max drawdown": dd,
        "Sharpe": (cagr - RISK_FREE) / vol if vol > 0 else np.nan,
        "Sortino": (cagr - RISK_FREE) / dvol if dvol and dvol > 0 else np.nan,
        "Calmar": (cagr / abs(dd)) if dd else np.nan,
        "Positive days": float((r > 0).mean() * 100),
        "Best day": float(r.max() * 100),
        "Worst day": float(r.min() * 100),
    }


def benchmark(market: pd.DataFrame, start=None, end=None,
              initial: float = 100_000.0) -> pd.DataFrame:
    m = market.copy()
    if start is not None:
        m = m[m["date"] >= pd.Timestamp(start)]
    if end is not None:
        m = m[m["date"] <= pd.Timestamp(end)]
    if m.empty:
        return pd.DataFrame()
    m = m.sort_values("date").copy()
    m["value"] = initial * (1 + m["ret"].fillna(0)).cumprod()
    m["drawdown_pct"] = (m["value"] / m["value"].cummax() - 1) * 100
    return m[["date", "value", "drawdown_pct"]]


def contribution(close: pd.DataFrame, weights: dict, start, end,
                 initial: float = 100_000.0) -> pd.DataFrame:
    """How much each holding added to the final result."""
    rows = []
    for s, w in weights.items():
        if s not in close.columns:
            continue
        px = close[s]
        px = px[(px.index >= pd.Timestamp(start)) & (px.index <= pd.Timestamp(end))].dropna()
        if len(px) < 2:
            continue
        r = float(px.iloc[-1] / px.iloc[0] - 1)
        rows.append({"symbol": s, "weight": w, "return_pct": r * 100,
                     "start_value": initial * w, "end_value": initial * w * (1 + r),
                     "pnl": initial * w * r, "contribution_pct": w * r * 100})
    return pd.DataFrame(rows).sort_values("contribution_pct", ascending=False)


# ---------------------------------------------------------------- optimisation
def optimise(close: pd.DataFrame, symbols: list, start=None, end=None,
             objective: str = "min_variance", max_weight: float = 0.35) -> dict:
    """
    Long-only weights from the sample covariance of daily returns.

    objective: 'min_variance'  - smallest portfolio volatility
               'max_sharpe'    - best return per unit of volatility
               'risk_parity'   - each holding contributes equal risk
               'equal'         - the honest baseline

    Solved by projected gradient descent rather than a solver library, so the
    application keeps its four dependencies. The weight cap keeps the answer
    from collapsing into one or two names, which is what unconstrained
    optimisers usually do on real data.
    """
    cols = [s for s in symbols if s in close.columns]
    if len(cols) < 2:
        return {s: 1.0 / max(len(cols), 1) for s in cols}
    px = close[cols]
    if start is not None:
        px = px[px.index >= pd.Timestamp(start)]
    if end is not None:
        px = px[px.index <= pd.Timestamp(end)]
    r = px.ffill().pct_change().dropna(how="all")
    r = r.dropna(axis=1, thresh=int(len(r) * 0.6)).fillna(0.0)
    cols = list(r.columns)
    if len(cols) < 2 or len(r) < 60:
        return {s: 1.0 / len(cols) for s in cols}

    n = len(cols)
    cov = r.cov().values * TD
    mu = r.mean().values * TD
    cap = max(float(max_weight), 1.0 / n)

    if objective == "equal":
        return {s: 1.0 / n for s in cols}

    def project(w):
        """Nearest point with weights >= 0, <= cap, summing to 1."""
        w = np.clip(w, 0.0, cap)
        for _ in range(60):
            s = w.sum()
            if abs(s - 1.0) < 1e-9:
                break
            w = np.clip(w * (1.0 / s if s > 0 else 1.0), 0.0, cap)
            if w.sum() >= 1.0 - 1e-9 and (w >= cap - 1e-12).all():
                break
        return w / w.sum() if w.sum() > 0 else np.full(n, 1.0 / n)

    w = np.full(n, 1.0 / n)
    step = 0.06
    for i in range(900):
        pv = float(w @ cov @ w)
        vol = np.sqrt(max(pv, 1e-12))
        if objective == "max_sharpe":
            grad = -(mu / vol) + ((mu @ w) * (cov @ w)) / (vol ** 3)
        elif objective == "risk_parity":
            contrib = w * (cov @ w)
            grad = (contrib - contrib.mean()) * 2.0
        else:
            grad = 2.0 * (cov @ w)
        w = project(w - step * grad / (np.linalg.norm(grad) + 1e-12))
        step *= 0.997
    return {s: float(round(x, 4)) for s, x in zip(cols, w)}
