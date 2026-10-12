# -*- coding: utf-8 -*-
"""
Stage 1 - text preparation and a data-driven sentiment lexicon.

Rather than importing a generic sentiment word list, the lexicon is induced
from this corpus using the log-odds ratio with an informative Dirichlet prior
(Monroe, Colaresi & Quinn 2008). That method is designed for exactly this
problem: finding the words that genuinely distinguish two classes of text
while damping down rare words that look extreme only because they are rare.
"""
import re, json, warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from collections import Counter

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)                    # the application folder
SRC = os.path.join(_ROOT, "data") + os.sep        # inputs the app already ships
APP = SRC                                         # stage 7 writes back into it
OUT = os.path.join(_HERE, "work") + os.sep        # intermediate artefacts
NLP = OUT
os.makedirs(OUT, exist_ok=True)




nw = pd.read_csv(SRC + 'news.csv.gz', parse_dates=['datetime'])
print('headlines', len(nw))

STOP = set("""a an the and or but if then than that this these those of in on at to for from by
with without within into onto over under about as is are was were be been being do does did
has have had will would shall should may might must can could not no nor its it their our your
his her they them we you he she i me my mine ours yours theirs which who whom whose what when
where why how all any both each few more most other some such only own same so too very s t
per re also up down out off again further once here there both any""".split())

def tokens(s):
    s = str(s).lower()
    s = re.sub(r"[^a-z0-9&/\-\s]", " ", s)
    out = []
    for w in s.split():
        w = w.strip("-/&")
        if len(w) < 2 or w in STOP or w.isdigit():
            continue
        out.append(w)
    return out

nw['tokens'] = nw['subject'].map(tokens)
nw['clean'] = nw['tokens'].map(lambda t: " ".join(t))
nw['n_tok'] = nw['tokens'].map(len)
print('empty after cleaning:', int((nw.n_tok == 0).sum()))

# ---------- log-odds ratio with informative Dirichlet prior ----------
neg = nw[nw.is_risk_signal == 1]
pos = nw[(nw.is_risk_signal == 0) & (nw.news_category != 'other')]
print('negative class', len(neg), '| routine class', len(pos))

ci = Counter(w for t in neg.tokens for w in t)
cj = Counter(w for t in pos.tokens for w in t)
alpha = Counter(w for t in nw.tokens for w in t)          # corpus prior

vocab = [w for w in alpha if alpha[w] >= 25]
a0 = sum(alpha[w] for w in vocab)
ni = sum(ci[w] for w in vocab); nj = sum(cj[w] for w in vocab)

rows = []
for w in vocab:
    a = alpha[w]
    li = np.log((ci[w] + a) / (ni + a0 - ci[w] - a))
    lj = np.log((cj[w] + a) / (nj + a0 - cj[w] - a))
    d = li - lj
    var = 1.0 / (ci[w] + a) + 1.0 / (cj[w] + a)
    rows.append({'term': w, 'z': d / np.sqrt(var), 'delta': d,
                 'n_neg': ci[w], 'n_routine': cj[w], 'n_total': a})

# z > 0 means the term leans to the negative-news class
lex = pd.DataFrame(rows).sort_values('z', ascending=False)
lex.to_csv(OUT + 'lexicon.csv', index=False)
nw[['datetime', 'symbol', 'subject', 'clean', 'news_category', 'is_risk_signal']].to_pickle(OUT + 'news_clean.pkl')

print('\nvocabulary kept:', len(lex))
print('\nTerms most indicative of NEGATIVE news (z > 0):')
print(lex.head(20)[['term', 'z', 'n_neg', 'n_routine']].to_string(index=False))
print('\nTerms most indicative of ROUTINE news (z < 0):')
print(lex.tail(12)[['term', 'z', 'n_neg', 'n_routine']].to_string(index=False))
