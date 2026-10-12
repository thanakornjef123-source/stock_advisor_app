# -*- coding: utf-8 -*-
"""
Stage 2 - supervised classifier (weak / distant supervision).

The keyword rules confidently label ~77% of headlines. Those labels train a
linear model over TF-IDF features, which then generalises to the ~23% the rules
could not place. The rules are the labelling function; the model learns the
pattern behind them and extends it to phrasings the rules never anticipated.

Kept deliberately lean (word n-grams, linear SVM) so the whole thing trains in
under a minute on a laptop and can be re-run by anyone reading this project.
"""
import warnings, json, pickle
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from sklearn.metrics import classification_report, accuracy_score, f1_score

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)                    # the application folder
SRC = os.path.join(_ROOT, "data") + os.sep        # inputs the app already ships
APP = SRC                                         # stage 7 writes back into it
OUT = os.path.join(_HERE, "work") + os.sep        # intermediate artefacts
NLP = OUT
os.makedirs(OUT, exist_ok=True)



nw = pd.read_pickle(OUT + 'news_clean.pkl')
nw = nw[nw['clean'].str.len() > 0]

lab = nw[nw.news_category != 'other'].copy()
unlab = nw[nw.news_category == 'other'].copy()
vc = lab.news_category.value_counts()
keep = vc[vc >= 40].index
lab = lab[lab.news_category.isin(keep)]
print(f'labelled {len(lab):,} | unlabelled {len(unlab):,} | classes {len(keep)}', flush=True)

def build():
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=4, sublinear_tf=True,
                        max_features=40000, strip_accents='unicode',
                        dtype=np.float32),
        LinearSVC(C=0.5, class_weight='balanced', max_iter=3000, dual=True))

X, y = lab['clean'].values, lab['news_category'].values
cv = StratifiedKFold(3, shuffle=True, random_state=42)
pred = cross_val_predict(build(), X, y, cv=cv, n_jobs=1)
acc = accuracy_score(y, pred); f1 = f1_score(y, pred, average='macro')
print(f'3-fold CV accuracy {acc:.4f}  macro-F1 {f1:.4f}', flush=True)
pd.DataFrame(classification_report(y, pred, zero_division=0, output_dict=True)).T \
  .to_csv(OUT + 'clf_report.csv')
print(classification_report(y, pred, zero_division=0, digits=3), flush=True)

# Fit on everything, wrapped so we get calibrated probabilities for a
# confidence threshold when predicting the unlabelled pile.
final = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), min_df=4, sublinear_tf=True,
                    max_features=40000, strip_accents='unicode', dtype=np.float32),
    CalibratedClassifierCV(LinearSVC(C=0.5, class_weight='balanced',
                                     max_iter=3000, dual=True), cv=3))
final.fit(X, y)
with open(OUT + 'clf.pkl', 'wb') as fh:
    pickle.dump(final, fh)
json.dump({'cv_accuracy': float(acc), 'macro_f1': float(f1),
           'n_train': int(len(lab)), 'n_classes': int(len(keep)),
           'n_unlabelled': int(len(unlab))},
          open(OUT + 'clf_meta.json', 'w'), indent=1)
print('saved', flush=True)
