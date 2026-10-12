# -*- coding: utf-8 -*-
"""Fit the final classifier and label the uncategorised headlines."""
import warnings, json, pickle
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import accuracy_score, f1_score

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)                    # the application folder
SRC = os.path.join(_ROOT, "data") + os.sep        # inputs the app already ships
APP = SRC                                         # stage 7 writes back into it
OUT = os.path.join(_HERE, "work") + os.sep        # intermediate artefacts
NLP = OUT
os.makedirs(OUT, exist_ok=True)



nw = pd.read_pickle(OUT + 'news_clean.pkl')
nw = nw[nw['clean'].str.len() > 0].reset_index(drop=True)
lab = nw[nw.news_category != 'other']
unlab = nw[nw.news_category == 'other']
vc = lab.news_category.value_counts()
lab = lab[lab.news_category.isin(vc[vc >= 40].index)]

vec = TfidfVectorizer(ngram_range=(1, 2), min_df=4, sublinear_tf=True,
                      max_features=40000, strip_accents='unicode', dtype=np.float32)
Xtr = vec.fit_transform(lab['clean'])
svm = LinearSVC(C=0.5, class_weight='balanced', max_iter=3000, dual=True)
svm.fit(Xtr, lab['news_category'].values)
print('fitted. features', Xtr.shape[1], 'classes', len(svm.classes_), flush=True)

# Confidence = margin between the best and second-best class score.
Xun = vec.transform(unlab['clean'])
scores = svm.decision_function(Xun)
order = np.argsort(-scores, axis=1)
best = svm.classes_[order[:, 0]]
margin = scores[np.arange(len(scores)), order[:, 0]] - scores[np.arange(len(scores)), order[:, 1]]

res = unlab[['datetime', 'symbol', 'subject', 'clean']].copy()
res['pred_category'] = best
res['margin'] = margin.astype('float32')
res.to_pickle(OUT + 'predicted_other.pkl')

with open(OUT + 'model.pkl', 'wb') as fh:
    pickle.dump({'vec': vec, 'svm': svm}, fh)

print('\nmargin percentiles:', np.round(np.percentile(margin, [10, 25, 50, 75, 90]), 3), flush=True)
for thr in [0.0, 0.15, 0.3, 0.5]:
    n = int((margin >= thr).sum())
    print(f'  threshold {thr:.2f} -> {n:,} of {len(res):,} assigned ({n/len(res)*100:.1f}%)', flush=True)
print('\ntop predicted categories at margin >= 0.3:', flush=True)
print(res[res.margin >= 0.3].pred_category.value_counts().head(12).to_string(), flush=True)
