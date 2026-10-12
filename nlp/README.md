# NLP pipeline

Run in order. Each stage writes its artefacts for the next one, so a stage can
be re-run on its own without repeating the whole chain.

```
s1_prep.py    clean text, induce the sentiment lexicon (log-odds ratio)
s2_clf.py     cross-validate the classifier and report per-class scores
s2b_fit.py    fit the final model, predict the uncategorised headlines
s3_merge.py   merge rules with predictions under the safety gate
s4_event.py   event study: abnormal returns after each category
s5_factor.py  topic discovery and the first sentiment build
s6_final.py   add discovered categories, re-run the study, final artefacts
s7_wire.py    merge NLP output into data/factors.csv.gz
```

Requires `scikit-learn` in addition to the application's own dependencies:

```bash
pip install scikit-learn
```

The application itself does not need scikit-learn — everything is precomputed
into the data files, so the deployed app stays light.
