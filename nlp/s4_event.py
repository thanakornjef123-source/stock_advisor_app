# -*- coding: utf-8 -*-
"""
Stage 4 - event study.

Classifying news is only useful if the categories correspond to something real.
This measures the abnormal return after each type of disclosure:

    abnormal return = the security's return over the window
                    - the cap-weighted market return over the same window

News is mapped to the next trading day after it was published, so nothing here
uses information before it was public. Reported with a t-statistic so the
difference between signal and noise is explicit.
"""
import warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)                    # the application folder
SRC = os.path.join(_ROOT, "data") + os.sep        # inputs the app already ships
APP = SRC                                         # stage 7 writes back into it
OUT = os.path.join(_HERE, "work") + os.sep        # intermediate artefacts
NLP = OUT
os.makedirs(OUT, exist_ok=True)




HORIZONS = [1, 5, 20]

px = pd.read_csv(SRC + 'prices.csv.gz', parse_dates=['date'],
                 usecols=['symbol', 'date', 'close'])
px = px.sort_values(['symbol', 'date'])
mkt = pd.read_csv(SRC + 'market_index.csv.gz', parse_dates=['date']).sort_values('date')
mkt['idx'] = (1 + mkt['ret'].fillna(0)).cumprod()

# forward returns for every security-day
for h in HORIZONS:
    px[f'fwd{h}'] = px.groupby('symbol', observed=True)['close'].shift(-h) / px['close'] - 1
mkt = mkt.set_index('date')
for h in HORIZONS:
    mkt[f'mfwd{h}'] = mkt['idx'].shift(-h) / mkt['idx'] - 1

trading_days = np.array(sorted(px['date'].unique()), dtype='datetime64[ns]')
print('trading days', len(trading_days), 'security-days', len(px), flush=True)

news = pd.read_pickle(OUT + 'news_final.pkl')
news = news[news['symbol'].notna()].copy()
# map each item to the first trading day strictly after publication
pos = np.searchsorted(trading_days, news['datetime'].values.astype('datetime64[ns]'), side='right')
ok = pos < len(trading_days)
news = news[ok].copy()
news['event_date'] = trading_days[pos[ok]]
print('events mapped', len(news), flush=True)

m = news.merge(px[['symbol', 'date'] + [f'fwd{h}' for h in HORIZONS]],
               left_on=['symbol', 'event_date'], right_on=['symbol', 'date'], how='inner')
m = m.join(mkt[[f'mfwd{h}' for h in HORIZONS]], on='event_date')
for h in HORIZONS:
    m[f'ar{h}'] = (m[f'fwd{h}'] - m[f'mfwd{h}']) * 100
print('events with price data', len(m), flush=True)

rows = []
for cat, g in m.groupby('final_category'):
    r = {'category': cat, 'n': len(g)}
    for h in HORIZONS:
        v = g[f'ar{h}'].dropna()
        v = v[v.abs() < 100]                       # drop corporate-action artefacts
        r[f'ar{h}_mean'] = v.mean()
        r[f'ar{h}_median'] = v.median()
        r[f'ar{h}_t'] = (v.mean() / (v.std() / np.sqrt(len(v)))) if len(v) > 30 and v.std() > 0 else np.nan
        r[f'ar{h}_n'] = len(v)
    rows.append(r)
ev = pd.DataFrame(rows).sort_values('ar5_mean')
ev.to_csv(OUT + 'event_study.csv', index=False)

pd.set_option('display.width', 200)
print('\n=== Abnormal return after each news category (%) ===')
print(ev[['category', 'n', 'ar1_mean', 'ar5_mean', 'ar5_t', 'ar20_mean', 'ar20_t']]
      .round(3).to_string(index=False), flush=True)

# aggregate: does the risk flag itself carry information?
print('\n=== Risk-signal flag ===')
for name, sub in [('risk signal', m[m.is_risk_signal_final == 1]),
                  ('routine', m[m.is_risk_signal_final == 0])]:
    v = sub['ar5'].dropna(); v = v[v.abs() < 100]
    t = v.mean() / (v.std() / np.sqrt(len(v)))
    print(f'  {name:12s} n={len(v):>6,}  mean 5-day AR {v.mean():+.3f}%  t={t:+.2f}', flush=True)
m[['datetime', 'symbol', 'final_category', 'is_risk_signal_final',
   'ar1', 'ar5', 'ar20']].to_pickle(OUT + 'events.pkl')
