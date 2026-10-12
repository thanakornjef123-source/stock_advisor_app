# -*- coding: utf-8 -*-
"""
Stage 3 - merge rule labels with model predictions, under a safety rule.

Inspecting the model's output showed a real failure mode: headlines like
"mai adds new listed securities" were predicted as `delisting`, because the
model had learned that exchange-administration vocabulary co-occurs with
delisting notices. Left alone, that would wrongly mark a healthy company as
carrying negative news.

So the merge is deliberately asymmetric:

  * routine categories   - accept a model prediction at a moderate margin
  * risk-signal categories - require a high margin AND corroboration from a
                             term in the induced negative lexicon, and reject
                             outright if an explicit positive-context phrase
                             is present

False negatives here are cheap (the item just stays "other"); false positives
are expensive, because they feed a red flag on a company.
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



RISK_CATS = {'trading_sign_halt', 'delisting', 'set_clarification', 'auditor_issue',
             'litigation', 'default_debt', 'capital_reduction', 'resignation',
             'net_loss', 'market_surveillance'}

MARGIN_ROUTINE = 0.30
MARGIN_RISK = 0.90

# phrases that make a negative reading implausible regardless of the model
POSITIVE_GUARD = re.compile(
    r"adds new listed|newly listed|first day of trading|commenc\w+ trading|"
    r"begin\w* trading|listing of|approved the listing|resumption of trading|"
    r"lifted|revoke\w* the|removal of.*sign|cancellation of.*sign", re.I)

nw = pd.read_pickle(OUT + 'news_clean.pkl')
nw = nw[nw['clean'].str.len() > 0].reset_index(drop=True)
pred = pd.read_pickle(OUT + 'predicted_other.pkl')
lex = pd.read_csv(OUT + 'lexicon.csv')

neg_terms = set(lex[lex.z >= 6.0].term)
print(f'negative lexicon terms: {len(neg_terms)}')

def corroborated(clean):
    return len(neg_terms.intersection(clean.split())) > 0

acc_cat, acc_src, acc_margin = [], [], []
n_routine = n_risk = n_reject_guard = n_reject_lex = n_low = 0
for row in pred.itertuples():
    cat, m = row.pred_category, float(row.margin)
    if cat in RISK_CATS:
        if m < MARGIN_RISK:
            acc_cat.append('other'); acc_src.append('unresolved'); n_low += 1
        elif POSITIVE_GUARD.search(row.subject or ''):
            acc_cat.append('other'); acc_src.append('rejected_positive_context'); n_reject_guard += 1
        elif not corroborated(row.clean):
            acc_cat.append('other'); acc_src.append('rejected_no_lexicon'); n_reject_lex += 1
        else:
            acc_cat.append(cat); acc_src.append('model_risk'); n_risk += 1
    else:
        if m >= MARGIN_ROUTINE:
            acc_cat.append(cat); acc_src.append('model_routine'); n_routine += 1
        else:
            acc_cat.append('other'); acc_src.append('unresolved'); n_low += 1
    acc_margin.append(m)

pred = pred.assign(final_category=acc_cat, source=acc_src, conf=acc_margin)
print(f'\naccepted routine   {n_routine:,}')
print(f'accepted risk      {n_risk:,}')
print(f'rejected by guard  {n_reject_guard:,}')
print(f'rejected, no lexicon support {n_reject_lex:,}')
print(f'left unresolved    {n_low:,}')

# ---- assemble the final labelled corpus ----
base = nw[['datetime', 'symbol', 'subject', 'clean', 'news_category', 'is_risk_signal']].copy()
base['final_category'] = base['news_category']
base['source'] = np.where(base['news_category'] == 'other', 'unresolved', 'rule')
base['conf'] = np.nan
key = ['datetime', 'symbol', 'subject']
upd = pred.set_index(key)[['final_category', 'source', 'conf']]
base = base.set_index(key)
mask = base['news_category'] == 'other'
common = base.index[mask].intersection(upd.index)
base.loc[common, ['final_category', 'source', 'conf']] = upd.loc[common].values
base = base.reset_index()
base['is_risk_signal_final'] = base['final_category'].isin(RISK_CATS).astype(int)

before = (base.news_category == 'other').mean() * 100
after = (base.final_category == 'other').mean() * 100
print(f"\nuncategorised: {before:.1f}%  ->  {after:.1f}%")
print(f"risk-signal rows: {int(base.is_risk_signal.sum()):,}  ->  {int(base.is_risk_signal_final.sum()):,}")
base.to_pickle(OUT + 'news_final.pkl')
json.dump({'uncat_before': float(before), 'uncat_after': float(after),
           'risk_before': int(base.is_risk_signal.sum()),
           'risk_after': int(base.is_risk_signal_final.sum()),
           'accepted_routine': n_routine, 'accepted_risk': n_risk,
           'rejected_guard': n_reject_guard, 'rejected_lexicon': n_reject_lex,
           'unresolved': n_low, 'margin_routine': MARGIN_ROUTINE,
           'margin_risk': MARGIN_RISK, 'neg_lexicon_terms': len(neg_terms)},
          open(OUT + 'merge_meta.json', 'w'), indent=1)
