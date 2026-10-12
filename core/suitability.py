# -*- coding: utf-8 -*-
"""
Investor Suitability Test
=========================
Ten-question risk-profiling questionnaire following the standard form used by
Thai securities companies and asset managers under SEC Thailand guidance.

Scoring: option 1 = 1 point ... option 4 = 4 points. Maximum 40 points.
Question 4 allows multiple selections; the highest-scoring option is used.
"""

QUESTIONS = [
    {
        "id": "q1", "short": "Age",
        "text": "What is your current age?",
        "options": ["60 years or older", "45 – 59 years",
                    "35 – 44 years", "Under 35 years"],
    },
    {
        "id": "q2", "short": "Financial burden",
        "text": "What share of your income goes to regular commitments such as "
                "mortgage or car payments, personal expenses and family support?",
        "options": ["More than 75% of total income",
                    "Between 50% and 75% of total income",
                    "Between 25% and 50% of total income",
                    "Less than 25% of total income"],
    },
    {
        "id": "q3", "short": "Net worth",
        "text": "How would you describe your current financial position?",
        "options": ["Assets are lower than liabilities",
                    "Assets roughly equal liabilities",
                    "Assets exceed liabilities",
                    "Confident that savings and investments already cover retirement"],
    },
    {
        "id": "q4", "short": "Experience", "multi": True,
        "text": "Which asset classes do you have experience with or knowledge of? "
                "Select all that apply — the highest-scoring answer is used.",
        "options": ["Bank deposits",
                    "Government bonds or government bond funds",
                    "Corporate bonds or fixed income funds",
                    "Common stocks, equity funds or other high-risk assets"],
    },
    {
        "id": "q5", "short": "Horizon",
        "text": "How long do you expect to leave this money invested without "
                "needing to withdraw it?",
        "options": ["Up to 1 year", "1 to 3 years", "3 to 5 years", "More than 5 years"],
    },
    {
        "id": "q6", "short": "Risk capacity",
        "text": "Which statement best describes your capacity to bear risk?",
        "options": ["Principal must stay safe; I accept a steady but low return",
                    "I want a steady return and accept some risk to principal",
                    "I want a higher return and accept greater risk to principal",
                    "I want the highest long-term return and accept losing most of the principal"],
    },
    {
        "id": "q7", "short": "Risk / reward",
        "text": "Looking at the illustrative outcomes below, which portfolio "
                "would you most willingly invest in?",
        "options": ["Portfolio 1 — up to 2.5% return with no possibility of loss",
                    "Portfolio 2 — up to 7% return, but may lose up to 1%",
                    "Portfolio 3 — up to 15% return, but may lose up to 5%",
                    "Portfolio 4 — up to 25% return, but may lose up to 15%"],
    },
    {
        "id": "q8", "short": "Comfort",
        "text": "If you invested in an asset with high return potential but an "
                "equally high chance of loss, how would you feel?",
        "options": ["Anxious and alarmed; afraid of losing money",
                    "Uncomfortable, but I can partly accept it",
                    "I understand it and can tolerate a degree of volatility",
                    "Untroubled by the downside and focused on the higher potential return"],
    },
    {
        "id": "q9", "short": "Loss tolerance",
        "text": "At what level of decline in your investment value would you "
                "start to feel uncomfortable?",
        "options": ["5% or less", "More than 5% up to 10%",
                    "More than 10% up to 20%", "More than 20%"],
    },
    {
        "id": "q10", "short": "Reaction to loss",
        "text": "You invested 100,000 baht last year and it is now worth 85,000 baht. "
                "What would you do?",
        "options": ["Panic and sell whatever is left",
                    "Worry, and shift part of the money into lower-risk assets",
                    "Hold on patiently and wait for the value to recover",
                    "Stay confident, treat it as long-term, and invest more to average down"],
    },
]

MAX_SCORE = len(QUESTIONS) * 4

PROFILES = {
    1: {
        "name": "Conservative", "thai": "เสี่ยงต่ำ", "range": "Below 15 points",
        "equity_cap": 0.00,
        "desc": "Very limited tolerance for volatility. Capital preservation is "
                "the first priority, and the standard guidance is fixed income only.",
        "allowed_buckets": ["1 Very Low"],
        "liquidity": ["Normal", "Liquid"],
        "max_beta": 0.8,
    },
    2: {
        "name": "Moderately Conservative", "thai": "เสี่ยงปานกลางค่อนข้างต่ำ",
        "range": "15 – 21 points", "equity_cap": 0.25,
        "desc": "Some tolerance for volatility, but stability of capital still "
                "dominates the objective.",
        "allowed_buckets": ["1 Very Low", "2 Low"],
        "liquidity": ["Normal", "Liquid"],
        "max_beta": 1.0,
    },
    3: {
        "name": "Balanced", "thai": "เสี่ยงปานกลางค่อนข้างสูง",
        "range": "22 – 29 points", "equity_cap": 0.50,
        "desc": "Willing to accept meaningful drawdowns along the way in "
                "exchange for a higher expected return.",
        "allowed_buckets": ["1 Very Low", "2 Low", "3 Moderate"],
        "liquidity": ["Thin", "Normal", "Liquid"],
        "max_beta": 1.3,
    },
    4: {
        "name": "Growth", "thai": "เสี่ยงสูง", "range": "30 – 36 points",
        "equity_cap": 0.75,
        "desc": "Comfortable with high volatility, focused on long-term capital growth.",
        "allowed_buckets": ["1 Very Low", "2 Low", "3 Moderate", "4 High"],
        "liquidity": ["Thin", "Normal", "Liquid"],
        "max_beta": 1.8,
    },
    5: {
        "name": "Aggressive", "thai": "เสี่ยงสูงมาก", "range": "37 points and above",
        "equity_cap": 1.00,
        "desc": "Accepts large losses in pursuit of the highest possible return.",
        "allowed_buckets": ["1 Very Low", "2 Low", "3 Moderate", "4 High", "5 Very High"],
        "liquidity": ["Thin", "Normal", "Liquid"],
        "max_beta": 99.0,
    },
}


def score_answers(answers: dict) -> int:
    total = 0
    for q in QUESTIONS:
        a = answers.get(q["id"])
        if a is None:
            continue
        if q.get("multi"):
            total += max(a) if a else 0
        else:
            total += int(a)
    return total


def profile_from_score(score: int) -> int:
    if score < 15:
        return 1
    if score <= 21:
        return 2
    if score <= 29:
        return 3
    if score <= 36:
        return 4
    return 5


def assess(answers: dict) -> dict:
    score = score_answers(answers)
    level = profile_from_score(score)
    p = dict(PROFILES[level])
    p.update({"level": level, "score": score, "max_score": MAX_SCORE,
              "answers": dict(answers)})
    return p
