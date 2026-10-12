# -*- coding: utf-8 -*-
"""Stage 7 - merge NLP output into the factor table used by the whole app."""
import warnings, json, os, shutil
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




f = pd.read_csv(APP + 'factors.csv.gz')
s = pd.read_csv(NLP + 'symbol_sentiment.csv')
ev = pd.read_csv(NLP + 'category_weights.csv')

f = f.drop(columns=[c for c in f.columns if c.startswith('nlp_')], errors='ignore')
f = f.merge(s, on='symbol', how='left')
f['nlp_items_2y'] = f['nlp_items_2y'].fillna(0).astype(int)
f['nlp_negative_items_2y'] = f['nlp_negative_items_2y'].fillna(0).astype(int)
# securities with no news get the neutral midpoint rather than a missing value
f['nlp_sentiment_score'] = f['nlp_sentiment_score'].fillna(50.0)

# Replace the hand-made binary flag with one grounded in measured impact:
# bottom decile of sentiment AND a meaningful number of items behind it.
thr = f.loc[f['nlp_items_2y'] >= 8, 'nlp_sentiment'].quantile(0.10)
f['nlp_red_flag'] = ((f['nlp_sentiment'] <= thr) & (f['nlp_items_2y'] >= 8)).astype(int)
print(f'sentiment 10th percentile threshold {thr:.4f}')
print(f'nlp_red_flag securities {int(f.nlp_red_flag.sum())} '
      f'(old rule-based flag {int(f.news_red_flag.sum())})')
overlap = int(((f.nlp_red_flag == 1) & (f.news_red_flag == 1)).sum())
print(f'overlap between the two flags: {overlap}')

f.to_csv(APP + 'factors.csv.gz', index=False, compression='gzip', float_format='%.6g')
shutil.copy(NLP + 'news_nlp.csv.gz', APP + 'news_nlp.csv.gz')
shutil.copy(NLP + 'category_weights.csv', APP + 'nlp_category_weights.csv')
shutil.copy(NLP + 'lexicon.csv', APP + 'nlp_lexicon.csv')
shutil.copy(NLP + 'topics.csv', APP + 'nlp_topics.csv')
shutil.copy(NLP + 'clf_report.csv', APP + 'nlp_clf_report.csv')
meta = json.load(open(NLP + 'merge_meta.json'))
meta.update(json.load(open(NLP + 'clf_meta.json')))
news = pd.read_csv(APP + 'news_nlp.csv.gz')
meta['uncat_final'] = float((news.final_category == 'other').mean() * 100)
meta['n_categories_final'] = int(news.final_category.nunique())
meta['n_headlines'] = int(len(news))
json.dump(meta, open(APP + 'nlp_meta.json', 'w'), indent=1)

print('\nfactor columns added:', [c for c in f.columns if c.startswith('nlp_')])
print('\nlowest sentiment:')
print(f.nsmallest(6, 'nlp_sentiment')[['symbol', 'company', 'nlp_sentiment',
      'nlp_items_2y', 'ret_1y']].round(3).to_string(index=False))
for k, v in meta.items():
    print(f'  {k}: {v}')
