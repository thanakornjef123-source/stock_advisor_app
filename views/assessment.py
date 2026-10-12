# -*- coding: utf-8 -*-
"""Risk Profile — the suitability questionnaire."""
import streamlit as st

from core import store
from core import theme as T
from core.suitability import QUESTIONS, MAX_SCORE, PROFILES, assess


def render():
    T.topbar("Investor Risk Profile",
             "Suitability Test · 10 questions · maximum 40 points")

    st.markdown(
        '<div class="panel"><b>What this is.</b> The ten questions below follow the '
        'standard suitability assessment used by Thai securities companies and asset '
        'managers under SEC guidance. Your score places you in one of five investor '
        'categories, and that category sets both the equity ceiling of the recommended '
        'portfolio and which securities are eligible for it.</div>',
        unsafe_allow_html=True)

    answers = st.session_state.setdefault("answers", {})

    with st.form("suitability"):
        for i, q in enumerate(QUESTIONS, start=1):
            st.markdown(f"**{i}. {q['text']}**")
            if q.get("multi"):
                cur = [q["options"][j - 1] for j in answers.get(q["id"], [])]
                picked = st.multiselect("Select all that apply", q["options"],
                                        default=cur, key=f"w_{q['id']}",
                                        label_visibility="collapsed")
                answers[q["id"]] = [q["options"].index(x) + 1 for x in picked]
            else:
                cur = answers.get(q["id"])
                choice = st.radio("Choose one", q["options"],
                                  index=(cur - 1) if cur else None,
                                  key=f"w_{q['id']}", label_visibility="collapsed")
                answers[q["id"]] = (q["options"].index(choice) + 1) if choice else None
            st.write("")
        submitted = st.form_submit_button("Calculate my profile", type="primary",
                                          width="stretch")

    if submitted:
        missing = [i for i, q in enumerate(QUESTIONS, 1) if not answers.get(q["id"])]
        if missing:
            st.error("Please answer every question. Still missing: "
                     + ", ".join(f"Q{m}" for m in missing))
        else:
            res = assess(answers)
            st.session_state["result"] = res
            st.session_state["answers"] = answers
            store.save()
            st.success(
                f"Score {res['score']} of {MAX_SCORE} — "
                f"Category {res['level']}: {res['name']} ({res['thai']}). "
                f"Equity ceiling {res['equity_cap']*100:.0f}%.")
            st.info("Open **Recommended Portfolio** in the sidebar to see your allocation.")

    with st.expander("How the score is built"):
        st.markdown(
            "Option 1 scores 1 point, option 2 scores 2, option 3 scores 3 and "
            "option 4 scores 4, for a maximum of 40. Question 4 allows several "
            "selections and takes the highest-scoring one.")
        st.dataframe(
            {"Category": [f"{k}" for k in PROFILES],
             "Score range": [PROFILES[k]["range"] for k in PROFILES],
             "Investor type": [PROFILES[k]["name"] for k in PROFILES],
             "Thai term": [PROFILES[k]["thai"] for k in PROFILES],
             "Maximum in risk assets": [
                 "Fixed income only" if PROFILES[k]["equity_cap"] == 0
                 else f"{PROFILES[k]['equity_cap']*100:.0f}%" for k in PROFILES]},
            hide_index=True, width="stretch")
        st.markdown(
            '<div class="caption">This assessment is a starting point, not advice. '
            'It should be revisited at least every two years, and sooner if your '
            'income, obligations or investment horizon change.</div>',
            unsafe_allow_html=True)
