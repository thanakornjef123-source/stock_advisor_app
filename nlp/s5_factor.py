# -*- coding: utf-8 -*-
"""
Stage 5 - topic discovery on the residual, and an empirically weighted
sentiment score.

The event study showed the hand-made binary risk flag carries no measurable
information (t = +1.0). Individual categories, however, clearly do. So the
sentiment score stops relying on my judgement of what counts as bad news and
instead weights each category by the abnormal return actually observed after
it, shrunk toward zero in proportion to how noisy that estimate is.

    weight(category) = mean 20-day abnormal return x  t^2 / (t^2 + 4)

The shrinkage term is a standard James-Stein style correction: a category
measured over 30,000 events keeps almost all of its weight, one measured over
26 events is pulled to nearly nothing.
"""
import warnings, json
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)                    # the application folder
SRC = os.path.join(_ROOT, "data") + os.sep        # inputs the app already ships
APP = SRC                                         # stage 7 writes back into it
OUT = os.path.join(_HERE, "work") + os.sep        # intermediate artefacts
NLP = OUT
os.makedirs(OUT, exist_ok=True)




HALFLIFE_DAYS = 180

news = pd.read_pickle(OUT + 'news_final.pkl')
ev = pd.read_csv(OUT + 'event_study.csv')

# ---------------- topic discovery on what is still unlabelled ----------------
rest = news[news.final_category == 'other']
print(f'still unlabelled: {len(rest):,}', flush=True)
vec = TfidfVectorizer(ngram_range=(1, 2), min_df=8, max_df=0.4, sublinear_tf=True,
                      max_features=12000, strip_accents='unicode', dtype=np.float32)
Xt = vec.fit_transform(rest['clean'])
nmf = NMF(n_components=10, init='nndsvda', random_state=42, max_iter=250)
W = nmf.fit_transform(Xt)
terms = np.array(vec.get_feature_names_out())
topics = []
for k, comp in enumerate(nmf.components_):
    top = terms[np.argsort(-comp)[:8]]
    n = int((W.argmax(axis=1) == k).sum())
    topics.append({'topic': k, 'n_headlines': n, 'top_terms': ", ".join(top)})
    print(f'  topic {k}  n={n:>6,}  {", ".join(top)}', flush=True)
pd.DataFrame(topics).to_csv(OUT + 'topics.csv', index=False)

# ---------------- empirically calibrated category weights ----------------
ev = ev.copy()
t = ev['ar20_t'].fillna(0.0)
shrink = (t ** 2) / (t ** 2 + 4.0)
ev['impact_weight'] = (ev['ar20_mean'].fillna(0.0) * shrink).round(4)
ev['reliable'] = (t.abs() >= 2).astype(int)
ev[['category', 'n', 'ar5_mean', 'ar5_t', 'ar20_mean', 'ar20_t',
    'impact_weight', 'reliable']].to_csv(OUT + 'category_weights.csv', index=False)
print('\n=== category impact weights (empirically calibrated) ===', flush=True)
print(ev.sort_values('impact_weight')[['category', 'n', 'ar20_mean', 'ar20_t',
      'impact_weight', 'reliable']].round(3).to_string(index=False), flush=True)

wmap = dict(zip(ev['category'], ev['impact_weight']))

# ---------------- per-security sentiment score ----------------
n2 = news[news['symbol'].notna()].copy()
last = n2['datetime'].max()
n2['age_days'] = (last - n2['datetime']).dt.days
n2 = n2[n2['age_days'] <= 730]
n2['decay'] = 0.5 ** (n2['age_days'] / HALFLIFE_DAYS)
n2['w'] = n2['final_category'].map(wmap).fillna(0.0) * n2['decay']

agg = n2.groupby('symbol').agg(
    nlp_sentiment_raw=('w', 'sum'),
    nlp_news_weighted=('decay', 'sum'),
    nlp_items_2y=('w', 'size')).reset_index()
agg['nlp_sentiment'] = (agg['nlp_sentiment_raw'] /
                        agg['nlp_news_weighted'].replace(0, np.nan)).round(4)
agg['nlp_sentiment_score'] = (agg['nlp_sentiment'].rank(pct=True) * 100).round(1)

neg_cats = set(ev[(ev.impact_weight < 0) & (ev.reliable == 1)]['category'])
print(f'\nempirically negative categories: {sorted(neg_cats)}', flush=True)
nn = n2[n2['final_category'].isin(neg_cats)]
cnt = nn.groupby('symbol').size().rename('nlp_negative_items_2y')
agg = agg.merge(cnt, left_on='symbol', right_index=True, how='left')
agg['nlp_negative_items_2y'] = agg['nlp_negative_items_2y'].fillna(0).astype(int)

agg[['symbol', 'nlp_sentiment', 'nlp_sentiment_score', 'nlp_items_2y',
     'nlp_negative_items_2y']].to_csv(OUT + 'symbol_sentiment.csv', index=False)
print(f'\nscored {len(agg):,} securities', flush=True)
print(agg.nlargest(6, 'nlp_sentiment')[['symbol', 'nlp_sentiment', 'nlp_items_2y']].to_string(index=False), flush=True)
print('...')
print(agg.nsmallest(6, 'nlp_sentiment')[['symbol', 'nlp_sentiment', 'nlp_items_2y']].to_string(index=False), flush=True)
