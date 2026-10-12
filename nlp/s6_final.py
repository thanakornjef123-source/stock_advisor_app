# -*- coding: utf-8 -*-
"""
Stage 6 - close the loop.

Topic modelling surfaced two things the keyword rules had missed:

  * ~8,800 headlines about establishing or acquiring subsidiaries, which is a
    genuine corporate-action category in its own right
  * several thousand headlines that are nothing but a date, which is the Excel
    corruption already identified in the data-quality report, independently
    rediscovered here by the topic model

Both are now explicit categories, the event study is re-run over the complete
labelling, and the final artefacts for the application are written out.
"""
import re, warnings, json
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

news = pd.read_pickle(OUT + 'news_final.pkl')

SUBSIDIARY = re.compile(r"establish\w*.*(subsidiar|joint.?venture|new company)|"
                        r"(subsidiar|joint.?venture).*establish|"
                        r"incorporation of.*(subsidiar|company)|"
                        r"acquisition of.*shares? in", re.I)
DATE_ONLY = re.compile(r"^\[date\]", re.I)

m = news.final_category == 'other'
sub = m & news.subject.fillna('').str.contains(SUBSIDIARY)
dat = m & news.subject.fillna('').str.contains(DATE_ONLY)
news.loc[sub, ['final_category', 'source']] = ['subsidiary_action', 'rule_v2']
news.loc[dat, ['final_category', 'source']] = ['date_only_corrupted', 'data_quality']
print(f'subsidiary_action      +{int(sub.sum()):,}')
print(f'date_only_corrupted    +{int(dat.sum()):,}')
print(f'uncategorised now      {(news.final_category=="other").mean()*100:.1f}%')

# ---------------- re-run the event study over the final labelling ----------------
px = pd.read_csv(SRC + 'prices.csv.gz', parse_dates=['date'], usecols=['symbol', 'date', 'close'])
px = px.sort_values(['symbol', 'date'])
mkt = pd.read_csv(SRC + 'market_index.csv.gz', parse_dates=['date']).sort_values('date')
mkt['idx'] = (1 + mkt['ret'].fillna(0)).cumprod()
for h in HORIZONS:
    px[f'fwd{h}'] = px.groupby('symbol', observed=True)['close'].shift(-h) / px['close'] - 1
mkt = mkt.set_index('date')
for h in HORIZONS:
    mkt[f'mfwd{h}'] = mkt['idx'].shift(-h) / mkt['idx'] - 1

td = np.array(sorted(px['date'].unique()), dtype='datetime64[ns]')
n2 = news[news['symbol'].notna()].copy()
pos = np.searchsorted(td, n2['datetime'].values.astype('datetime64[ns]'), side='right')
ok = pos < len(td)
n2 = n2[ok].copy(); n2['event_date'] = td[pos[ok]]

j = n2.merge(px[['symbol', 'date'] + [f'fwd{h}' for h in HORIZONS]],
             left_on=['symbol', 'event_date'], right_on=['symbol', 'date'], how='inner')
j = j.join(mkt[[f'mfwd{h}' for h in HORIZONS]], on='event_date')
for h in HORIZONS:
    j[f'ar{h}'] = (j[f'fwd{h}'] - j[f'mfwd{h}']) * 100

rows = []
for cat, g in j.groupby('final_category'):
    r = {'category': cat, 'n': len(g)}
    for h in HORIZONS:
        v = g[f'ar{h}'].dropna(); v = v[v.abs() < 100]
        r[f'ar{h}_mean'] = v.mean(); r[f'ar{h}_median'] = v.median()
        r[f'ar{h}_t'] = (v.mean() / (v.std() / np.sqrt(len(v)))) if len(v) > 30 and v.std() > 0 else np.nan
        r[f'ar{h}_n'] = int(len(v))
    rows.append(r)
ev = pd.DataFrame(rows)
t = ev['ar20_t'].fillna(0.0)
ev['impact_weight'] = (ev['ar20_mean'].fillna(0.0) * (t**2 / (t**2 + 4.0))).round(4)
ev['reliable'] = (t.abs() >= 2).astype(int)
ev = ev.sort_values('impact_weight')
ev.to_csv(OUT + 'category_weights.csv', index=False)
print('\n=== final category impact table ===')
print(ev[['category', 'n', 'ar5_mean', 'ar5_t', 'ar20_mean', 'ar20_t',
          'impact_weight', 'reliable']].round(3).to_string(index=False))

# ---------------- per-security sentiment ----------------
wmap = dict(zip(ev['category'], ev['impact_weight']))
HL = 180
s = news[news['symbol'].notna()].copy()
last = s['datetime'].max()
s['age'] = (last - s['datetime']).dt.days
s = s[s['age'] <= 730]
s['decay'] = 0.5 ** (s['age'] / HL)
s['w'] = s['final_category'].map(wmap).fillna(0.0) * s['decay']
agg = s.groupby('symbol').agg(nlp_raw=('w', 'sum'), nlp_wsum=('decay', 'sum'),
                              nlp_items_2y=('w', 'size')).reset_index()
agg['nlp_sentiment'] = (agg['nlp_raw'] / agg['nlp_wsum'].replace(0, np.nan)).round(4)
agg['nlp_sentiment_score'] = (agg['nlp_sentiment'].rank(pct=True) * 100).round(1)
neg = set(ev[(ev.impact_weight < 0) & (ev.reliable == 1)]['category'])
agg = agg.merge(s[s.final_category.isin(neg)].groupby('symbol').size()
                .rename('nlp_negative_items_2y'), left_on='symbol', right_index=True, how='left')
agg['nlp_negative_items_2y'] = agg['nlp_negative_items_2y'].fillna(0).astype(int)
agg[['symbol', 'nlp_sentiment', 'nlp_sentiment_score', 'nlp_items_2y',
     'nlp_negative_items_2y']].to_csv(OUT + 'symbol_sentiment.csv', index=False)

# ---------------- artefacts for the app ----------------
news[['datetime', 'symbol', 'subject', 'news_category', 'final_category',
      'source', 'conf', 'is_risk_signal', 'is_risk_signal_final']] \
    .to_csv(OUT + 'news_nlp.csv.gz', index=False, compression='gzip')
j[['datetime', 'symbol', 'final_category', 'ar1', 'ar5', 'ar20']] \
    .to_csv(OUT + 'events.csv.gz', index=False, compression='gzip', float_format='%.4f')
print(f'\nscored {len(agg):,} securities · uncategorised '
      f'{(news.final_category=="other").mean()*100:.1f}%')
