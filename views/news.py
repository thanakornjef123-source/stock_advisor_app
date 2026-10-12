# -*- coding: utf-8 -*-
"""News Intelligence — the NLP pipeline and what it found."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import data as D
from core import theme as T

LABEL = {
    "financial_statement": "Financial statement", "mdna": "MD&A",
    "dividend": "Dividend", "capital_increase": "Capital increase",
    "warrant": "Warrant", "mna": "M&A / asset deal",
    "connected_txn": "Connected transaction", "board_change": "Board or management",
    "shareholder_meeting": "Shareholder meeting", "nav_report": "NAV report",
    "share_repurchase": "Share buyback", "ipo_listing": "Listing",
    "book_closure": "Book closure", "public_presentation": "Public presentation",
    "corporate_admin": "Corporate admin", "dw_notice": "Derivative warrant",
    "trading_sign_halt": "Trading sign / halt", "delisting": "Delisting risk",
    "market_surveillance": "Market surveillance", "set_clarification": "SET clarification request",
    "auditor_issue": "Auditor issue", "litigation": "Litigation",
    "default_debt": "Debt default", "capital_reduction": "Capital reduction",
    "resignation": "Resignation", "net_loss": "Reported loss",
    "subsidiary_action": "Subsidiary / JV action",
    "date_only_corrupted": "Headline lost in source export", "other": "Unresolved",
}


def render():
    meta = D.nlp_meta()
    T.topbar("News Intelligence",
             f"{meta['n_headlines']:,} headlines · {meta['n_categories_final']} categories "
             f"· {meta['uncat_final']:.1f}% unresolved")

    st.markdown(
        '<div class="panel"><b>What this is.</b> Company disclosures are text, and '
        'text is only useful once it is turned into something measurable. This '
        'pipeline classifies every headline, then tests whether those classes '
        'correspond to real price movements — so the news signal is validated '
        'against the market rather than asserted.</div>', unsafe_allow_html=True)

    T.stat_cards([
        ("Headlines processed", f"{meta['n_headlines']:,}", "common stock only", ""),
        ("Categories", str(meta["n_categories_final"]), "final taxonomy", ""),
        ("Unresolved before", f"{meta['uncat_before']:.1f}%", "keyword rules alone", "down"),
        ("Unresolved after", f"{meta['uncat_final']:.1f}%", "after the full pipeline", "up"),
        ("Classifier accuracy", f"{meta['cv_accuracy']*100:.1f}%", "3-fold cross-validation", ""),
        ("Macro F1", f"{meta['macro_f1']:.3f}", f"across {meta['n_classes']} classes", ""),
    ])

    t1, t2, t3, t4, t5 = st.tabs([
        "Pipeline", "Event study", "Induced lexicon", "Classifier", "Topics"])

    # ---------------------------------------------------------------- pipeline
    with t1:
        T.section("What the audit removed",
                  "Before any page reads the factor table, values that are "
                  "arithmetically valid but economically meaningless are voided. "
                  "Each rule below exists because a specific security exposed it.")
        cl = D.correction_log()
        if not cl.empty:
            disp = cl.rename(columns={"rule": "Field or flag", "rows": "Securities",
                                      "detail": "Why"})
            st.dataframe(disp, hide_index=True, width="stretch",
                         column_config={"Why": st.column_config.TextColumn(width="large")})
            T.caption(
                "Worked examples: RS reported a 48.2% dividend yield and an income "
                "score of 84.8 while its price fell 96.3% over the year — the "
                "payout was ordinary, the denominator had collapsed. WELL last "
                "traded in October 2021 and still carried an above-median overall "
                "score. 88TH reported a three-year return from 59 days of history. "
                "FNS turned a loss into a +251.8% margin by dividing a negative "
                "profit by a negative revenue.")

        T.section("How a headline gets its label")
        steps = [
            ("1 · Keyword rules", f"{100-meta['uncat_before']:.1f}% labelled",
             "Twenty-nine regular-expression patterns over the headline. Fast and "
             "fully transparent, but blind to any phrasing not anticipated in advance."),
            ("2 · Weak supervision", f"+{meta['accepted_routine']:,} routine, "
             f"+{meta['accepted_risk']:,} negative",
             "The rule labels become training data for a TF-IDF linear SVM, which "
             "then labels what the rules missed. The rules are the labelling "
             "function; the model learns the pattern behind them."),
            ("3 · Safety gate", f"{meta['rejected_guard']:,} rejected",
             "Inspection showed the model calling 'mai adds new listed securities' a "
             "delisting. So a negative label now needs a high margin, support from "
             "the induced lexicon, and no positive-context phrase such as "
             "'sign lifted' or 'first day of trading'."),
            ("4 · Topic discovery", "2 categories recovered",
             "Non-negative matrix factorisation over the remainder surfaced a real "
             "missing category — subsidiary and joint-venture actions — and "
             "independently rediscovered the headlines destroyed by Excel in the "
             "source export."),
            ("5 · Event study", "calibration",
             "Each category is scored by the abnormal return that actually follows "
             "it, which replaces any human judgement about what counts as bad news."),
        ]
        for title, stat, body in steps:
            st.markdown(
                f'<div class="panel"><div style="display:flex;justify-content:space-between;'
                f'align-items:baseline;gap:12px"><b>{title}</b>'
                f'<span style="font-family:{T.MONO};font-size:0.72rem;color:{T.ACCENT}">'
                f'{stat}</span></div>'
                f'<div class="caption" style="margin-top:6px">{body}</div></div>',
                unsafe_allow_html=True)

        nw = D.news()
        src = nw["source"].value_counts()
        names = {"rule": "Keyword rules", "model_routine": "Model — routine class",
                 "model_risk": "Model — negative class", "rule_v2": "Rules, second pass",
                 "data_quality": "Corrupted in source export",
                 "unresolved": "Still unresolved",
                 "rejected_positive_context": "Rejected by safety gate",
                 "rejected_no_lexicon": "Rejected, no lexicon support"}
        fig = go.Figure(go.Bar(
            x=src.values, y=[names.get(i, i) for i in src.index], orientation="h",
            marker_color=[T.ACCENT if i == "rule" else
                          (T.WARN if str(i).startswith("rejected") or i == "unresolved"
                           else T.UP) for i in src.index],
            text=[f"{v:,}" for v in src.values], textposition="outside",
            textfont=dict(family=T.MONO, size=10)))
        fig.update_layout(height=300, xaxis_title="Headlines", margin=dict(r=70))
        st.plotly_chart(fig, width="stretch")

    # ---------------------------------------------------------------- event study
    with t2:
        ev = D.nlp_category_weights().copy()
        T.section("Do these categories actually move prices?")
        T.caption("Abnormal return = the security's return after the disclosure minus "
                  "the cap-weighted market return over the same window. Every headline "
                  "is mapped to the next trading day, so nothing uses information "
                  "before it was public. A t-statistic beyond ±2 is the usual "
                  "threshold for treating an effect as real rather than noise.")

        h = st.radio("Window", ["1 day", "5 days", "20 days"], index=1,
                     horizontal=True, key="nlp_h")
        col = {"1 day": "ar1", "5 days": "ar5", "20 days": "ar20"}[h]
        d = ev.dropna(subset=[f"{col}_mean"]).copy()
        d = d[d["n"] >= 30].sort_values(f"{col}_mean")
        sig = d[f"{col}_t"].abs() >= 2
        fig = go.Figure(go.Bar(
            x=d[f"{col}_mean"], y=[LABEL.get(c, c) for c in d["category"]],
            orientation="h",
            marker_color=[(T.UP if v >= 0 else T.DOWN) if s else T.MUTED
                          for v, s in zip(d[f"{col}_mean"], sig)],
            customdata=np.stack([d["n"], d[f"{col}_t"]], axis=-1),
            hovertemplate="%{y}<br>Mean AR %{x:.3f}%<br>n=%{customdata[0]:,}"
                          "<br>t=%{customdata[1]:.2f}<extra></extra>",
            text=[f"{v:+.2f}%" for v in d[f"{col}_mean"]], textposition="outside",
            textfont=dict(family=T.MONO, size=10)))
        fig.add_vline(x=0, line_color=T.BORDER)
        fig.update_layout(height=max(420, 24 * len(d)),
                          xaxis_title=f"Mean abnormal return over {h} (%)",
                          margin=dict(r=60))
        st.plotly_chart(fig, width="stretch")
        T.caption("Grey bars are not statistically significant. Colour means the "
                  "effect survives a t-test.")

        T.section("The finding that changed the model")
        st.markdown(
            f'<div class="panel">The original design flagged nine categories as '
            f'"negative news" based on what sounded bad. Tested against actual '
            f'returns, that binary flag had <b>no predictive power at all</b> '
            f'(mean 5-day abnormal return +0.13%, t = +1.00). Individual categories '
            f'clearly do move prices — warrant activity −2.57% over twenty days '
            f'(t = −15.8), capital increases −1.50% (t = −6.2), SET clarification '
            f'requests −1.85% (t = −3.1) — but the way they had been bucketed '
            f'destroyed the signal.<br><br>'
            f'So the sentiment score no longer uses my judgement. Each category is '
            f'weighted by the abnormal return measured after it, shrunk toward zero '
            f'in proportion to how noisy that estimate is:<br>'
            f'<span style="font-family:{T.MONO};font-size:0.8rem;color:{T.ACCENT}">'
            f'weight = mean 20-day AR × t² / (t² + 4)</span></div>',
            unsafe_allow_html=True)

        T.section("One result worth reading carefully")
        st.warning(
            "Market surveillance notices show a **positive** abnormal return "
            "(+2.99% over twenty days, t = +4.8). That does not mean regulatory "
            "attention is good news. Surveillance measures are imposed *after* a "
            "sharp run-up, so what the number captures is momentum continuing, not "
            "the notice causing a gain. It is a clean illustration of why an "
            "automated signal still needs a human reading it.")

        show = ev.copy()
        show["Category"] = show["category"].map(lambda c: LABEL.get(c, c))
        st.dataframe(pd.DataFrame({
            "Category": show["Category"], "Events": show["n"],
            "AR 1D (%)": show["ar1_mean"].round(3),
            "AR 5D (%)": show["ar5_mean"].round(3), "t (5D)": show["ar5_t"].round(2),
            "AR 20D (%)": show["ar20_mean"].round(3), "t (20D)": show["ar20_t"].round(2),
            "Impact weight": show["impact_weight"],
            "Significant": show["reliable"].map({1: "yes", 0: ""})
        }).sort_values("Impact weight"), hide_index=True, width="stretch", height=420)

    # ---------------------------------------------------------------- lexicon
    with t3:
        lex = D.nlp_lexicon()
        T.section("Words that signal good and bad news")
        T.caption("No off-the-shelf word list is used. Terms are scored by the "
                  "log-odds ratio with an informative Dirichlet prior (Monroe, "
                  "Colaresi & Quinn, 2008), which finds the words that genuinely "
                  "separate negative from routine disclosures while damping down "
                  "rare words that only look extreme because they are rare.")
        n = st.slider("Words to show each side", 10, 40, 20, 5, key="nlp_lexn")
        top = lex.nlargest(n, "z"); bot = lex.nsmallest(n, "z")
        c1, c2 = st.columns(2)
        for col, d, title, colour in [(c1, top, "Negative-leaning terms", T.DOWN),
                                      (c2, bot.iloc[::-1], "Routine-leaning terms", T.UP)]:
            with col:
                fig = go.Figure(go.Bar(
                    x=d["z"].abs(), y=d["term"], orientation="h",
                    marker_color=colour,
                    customdata=np.stack([d["n_neg"], d["n_routine"]], axis=-1),
                    hovertemplate="%{y}<br>|z| %{x:.1f}<br>negative %{customdata[0]:,}"
                                  " · routine %{customdata[1]:,}<extra></extra>"))
                fig.update_layout(height=26 * n + 60, title=title,
                                  xaxis_title="|z| score", yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, width="stretch")
        st.dataframe(lex.reindex(lex["z"].abs().sort_values(ascending=False).index)
                     .head(200)[["term", "z", "n_neg", "n_routine", "n_total"]].round(2),
                     hide_index=True, width="stretch", height=300)

    # ---------------------------------------------------------------- classifier
    with t4:
        rep = D.nlp_report()
        T.section("How accurate is the labelling?")
        st.markdown(
            f'<div class="panel">TF-IDF over word unigrams and bigrams feeding a '
            f'linear support vector machine, validated with stratified 3-fold '
            f'cross-validation across {meta["n_classes"]} classes and '
            f'{meta["n_train"]:,} training headlines.<br><br>'
            f'<b>Read the accuracy honestly.</b> {meta["cv_accuracy"]*100:.1f}% does '
            f'not mean the labels are {meta["cv_accuracy"]*100:.1f}% correct about '
            f'reality. The training labels came from keyword rules, so a high score '
            f'means the model faithfully reproduces those rules. Its real value is '
            f'generalising to phrasings the rules never saw — which is what the '
            f'{meta["accepted_routine"]:,} newly labelled headlines represent, and '
            f'why the safety gate in step 3 exists.</div>',
            unsafe_allow_html=True)
        r = rep.drop(index=[i for i in ("accuracy", "macro avg", "weighted avg")
                            if i in rep.index]).copy()
        r = r.sort_values("f1-score")
        fig = go.Figure(go.Bar(
            x=r["f1-score"], y=[LABEL.get(i, i) for i in r.index], orientation="h",
            marker_color=[T.UP if v >= 0.9 else (T.WARN if v >= 0.7 else T.DOWN)
                          for v in r["f1-score"]],
            customdata=r["support"],
            hovertemplate="%{y}<br>F1 %{x:.3f}<br>n=%{customdata:,.0f}<extra></extra>",
            text=[f"{v:.3f}" for v in r["f1-score"]], textposition="outside",
            textfont=dict(family=T.MONO, size=10)))
        fig.update_layout(height=max(400, 24 * len(r)), xaxis_title="F1 score",
                          xaxis_range=[0, 1.12], margin=dict(r=50))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(rep.round(3), width="stretch", height=300)

    # ---------------------------------------------------------------- topics
    with t5:
        tp = D.nlp_topics()
        T.section("Themes the model found on its own",
                  "Non-negative matrix factorisation over the headlines that neither the rules nor the classifier could place, to find out what was actually in the residual rather than guessing.")
        st.dataframe(pd.DataFrame({
            "Topic": tp["topic"], "Headlines": tp["n_headlines"],
            "Leading terms": tp["top_terms"]}), hide_index=True, width="stretch")
        st.markdown(
            '<div class="panel"><b>What it found.</b> One topic held roughly 8,800 '
            'headlines about establishing subsidiaries and joint ventures — a real '
            'corporate-action category the keyword rules had no pattern for, now '
            'added as <code>subsidiary_action</code>.<br><br>'
            'Every other topic was dominated by bare dates. That is the Excel '
            'corruption documented in the data-quality report, where headlines '
            'beginning with a date-like string were converted to date values during '
            'the original export and the text was lost before this project ever '
            'received the file. The topic model rediscovered it independently, which '
            'is a useful confirmation that the finding was real and not an artefact '
            'of the cleaning code.</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown(
        '<div class="caption"><b>Limitations.</b> Only headlines are read, never the '
        'body text. Classification identifies the type of disclosure, and the event '
        'study measures the average price reaction to that type — neither is a '
        'judgement about an individual company. The event study is measured '
        'in-sample over 2021–2025 and is not evidence that the signal will persist. '
        'All estimates are averages: a category with a negative mean still contains '
        'many individually positive events.</div>', unsafe_allow_html=True)
