# -*- coding: utf-8 -*-
"""
Point-in-time factor backtest.

Every factor in the app is computed over the full 2021-2025 window, which makes
any comparison against returns from that same window circular. This rebuilds the
price-based factors using ONLY data available on a formation date, then measures
what happened afterwards. That is a genuine out-of-sample test.

Two formation dates are used so the result is not a single lucky year.
"""
import warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)                    # the application folder

APP = SRC                                         # stage 7 writes back into it

NLP = OUT
os.makedirs(OUT, exist_ok=True)




px = pd.read_csv(SRC + 'prices.csv.gz', parse_dates=['date'],
                 usecols=['symbol', 'date', 'close', 'total_value', 'market_cap',
                          'pe', 'pbv', 'dividend_yield'])
px = px.sort_values(['symbol', 'date'])
mkt = pd.read_csv(SRC + 'market_index.csv.gz', parse_dates=['date']).sort_values('date')
mkt['idx'] = (1 + mkt['ret'].fillna(0)).cumprod()
LAST = px['date'].max()
print('last date', LAST.date(), flush=True)

FORMATIONS = [pd.Timestamp('2023-12-29'), pd.Timestamp('2024-12-30')]
HOLD_DAYS = 365

rows = []
for form in FORMATIONS:
    hist = px[px['date'] <= form]
    fut_end = min(form + pd.Timedelta(days=HOLD_DAYS), LAST)
    fut = px[(px['date'] > form) & (px['date'] <= fut_end)]
    if fut.empty:
        continue
    mi0 = mkt.loc[mkt['date'] <= form, 'idx'].iloc[-1]
    mi1 = mkt.loc[mkt['date'] <= fut_end, 'idx'].iloc[-1]
    mret = (mi1 / mi0 - 1) * 100

    for sym, g in hist.groupby('symbol', observed=True):
        g = g.sort_values('date')
        if len(g) < 250:
            continue
        c = g['close']
        r = c.pct_change(); r = r.where(r.abs() <= 1)
        w1y = g[g['date'] >= form - pd.Timedelta(days=365)]
        if len(w1y) < 150 or w1y['close'].iloc[0] <= 0:
            continue
        f2 = fut[fut['symbol'] == sym]
        if len(f2) < 100:
            continue
        p0 = c.iloc[-1]; p1 = f2['close'].iloc[-1]
        if p0 <= 0:
            continue
        rows.append({
            'formation': form.date().isoformat(), 'symbol': sym,
            # --- factors known at the formation date only ---
            'mom_12m': (w1y['close'].iloc[-1] / w1y['close'].iloc[0] - 1) * 100,
            'mom_6m': ((c.iloc[-1] / g[g['date'] >= form - pd.Timedelta(days=182)]['close'].iloc[0] - 1) * 100
                       if len(g[g['date'] >= form - pd.Timedelta(days=182)]) > 2 else np.nan),
            'vol_12m': r[g['date'] >= form - pd.Timedelta(days=365)].std() * np.sqrt(252) * 100,
            'max_dd_12m': ((w1y['close'] / w1y['close'].cummax()) - 1).min() * 100,
            'pe': g['pe'].dropna().iloc[-1] if g['pe'].notna().any() else np.nan,
            'pbv': g['pbv'].dropna().iloc[-1] if g['pbv'].notna().any() else np.nan,
            'dividend_yield': g['dividend_yield'].dropna().iloc[-1] if g['dividend_yield'].notna().any() else np.nan,
            'market_cap': g['market_cap'].dropna().iloc[-1] if g['market_cap'].notna().any() else np.nan,
            'liquidity': g['total_value'].tail(60).mean(),
            # --- what happened next ---
            'fwd_return': (p1 / p0 - 1) * 100,
            'fwd_excess': (p1 / p0 - 1) * 100 - mret,
        })
    print(f'formation {form.date()} -> {fut_end.date()}  market {mret:+.2f}%  '
          f'names {sum(1 for x in rows if x["formation"]==form.date().isoformat()):,}', flush=True)

d = pd.DataFrame(rows)
d = d[d['liquidity'].fillna(0) >= 1e6]
d.to_pickle(OUT + 'factor_backtest_raw.pkl')
print('\nrows', len(d), flush=True)

FACTORS = [('mom_12m', True, 'Momentum 12M'), ('mom_6m', True, 'Momentum 6M'),
           ('vol_12m', False, 'Low volatility'), ('max_dd_12m', True, 'Shallow drawdown'),
           ('pe', False, 'Low P/E'), ('pbv', False, 'Low P/BV'),
           ('dividend_yield', True, 'High dividend yield'),
           ('market_cap', True, 'Large size')]

out = []
for col, higher_better, label in FACTORS:
    sub = d.dropna(subset=[col, 'fwd_excess']).copy()
    if len(sub) < 200:
        continue
    if col in ('pe', 'pbv'):
        sub = sub[sub[col] > 0]
    sub['dec'] = sub.groupby('formation')[col].transform(
        lambda s: pd.qcut(s.rank(method='first'), 10, labels=False) + 1)
    if not higher_better:
        sub['dec'] = 11 - sub['dec']
    g = sub.groupby('dec')['fwd_excess'].agg(['mean', 'median', 'count'])
    top, bot = g.loc[10, 'mean'], g.loc[1, 'mean']
    tv = sub[sub.dec == 10]['fwd_excess']; bv = sub[sub.dec == 1]['fwd_excess']
    se = np.sqrt(tv.var()/len(tv) + bv.var()/len(bv))
    ic = sub.groupby('formation').apply(
        lambda x: x[col].corr(x['fwd_excess'], method='spearman')).mean()
    for dec in range(1, 11):
        out.append({'factor': col, 'label': label, 'decile': dec,
                    'mean_excess': g.loc[dec, 'mean'], 'median_excess': g.loc[dec, 'median'],
                    'n': int(g.loc[dec, 'count']),
                    'spread': top - bot, 't_spread': (top - bot) / se if se > 0 else np.nan,
                    'rank_ic': ic})
    print(f'{label:22s} top-bottom spread {top-bot:+7.2f}%  t={((top-bot)/se if se>0 else 0):+5.2f}  IC={ic:+.3f}', flush=True)

pd.DataFrame(out).to_csv(OUT + 'factor_backtest.csv', index=False)
print('\nsaved', flush=True)
