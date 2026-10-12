# SET Equity Terminal

A risk-profiled equity research and portfolio-construction workstation for the
Stock Exchange of Thailand, built on cleaned exchange data covering 2021–2025.

The application does three things. It profiles the investor with the standard
suitability questionnaire, it constructs a portfolio whose equity ceiling and
eligible universe both follow from that profile, and it hands the user a full
set of research tools to check the recommendation and go further on their own.

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://stockadvisorapp-di9ewtrmurthsaabwplsgt.streamlit.app)

**Live demo** — https://stockadvisorapp-di9ewtrmurthsaabwplsgt.streamlit.app

No install and no account: the link opens the terminal in a browser. Watchlists
and holdings entered there live in your own browser session and are discarded
when the tab closes, so visitors never see each other's portfolios.

**Coverage** — 915 securities · 961,842 daily price bars · 15,160 quarterly
financial statements · 148,733 company disclosures classified by an NLP pipeline
· 80 computed metrics per security.

---

## The documents in this project

| File | What it covers |
|---|---|
| `README.md` | this file — what the terminal does and how it was built |
| `DEPLOY.md` | publishing it as a website, and the sharing setting that decides whether a link alone is enough |
| `NOTICE.md` | data rights, and the three limitations that change how the numbers should be read |
| `docs/DATA_QUALITY.md` | every defect found in the raw exchange files and what was done about it |
| `nlp/README.md` | the five-stage news pipeline, re-runnable end to end |

## Running it

```bash
pip install -r requirements.txt
streamlit run app.py
```

The browser opens at `http://localhost:8501`. On Windows you can instead
double-click `RUN_APP.py`, which creates a virtual environment, installs the
dependencies and launches the app in one step.

Keep the terminal window open while presenting — closing it stops the server.

---

## First run

The app opens on a welcome screen rather than dropping straight into the tools:
what the terminal is, what data sits behind it, and how it was built. Pressing
**Enter terminal** raises a short dialog asking whether to take the suitability
assessment first or skip it — everything works either way, but the Recommended
Portfolio page needs a profile before it can suggest anything. The sidebar
appears only after entering, and **← Back to start** at its foot returns to the
welcome screen.

## The thirteen screens

**Market Overview** — the landing page. Index level and returns across four
horizons, market breadth, the share of securities trading above their 200-day
average, cap-weighted sector performance, movers and extremes, and a risk/return
map of the whole market.

**Heat Map** — the whole market on one screen. A treemap sized by market cap,
turnover or equal weight, coloured by return over any of five periods, grouped by
industry or sector, with click-through zoom. Below it, two matrix views: sector
returns across every period, and sector median scores across every factor. A
drill-down tab lists the constituents of any sector with aggregate statistics.

**Rankings** — composite letter grades from A+ to F, leaderboards for each of the
seven factors, and an out-of-sample test of whether those factors actually paid.

**Screener** — the core research tool. Forty-two numeric criteria organised into
ten groups, plus classification filters for sector, market, size, risk band and
liquidity. Seven ready-made strategies load a complete filter set that the user
can then inspect and modify. Results are sortable on any column, the column set
is user-chosen, and everything exports to CSV. Selections can be pushed straight
into Compare, the Watchlist or the Portfolio Lab.

**Compare** — up to eight securities side by side: rebased performance, price,
or drawdown; a twenty-six-row metric table; a return-correlation matrix; and a
factor radar.

**Security Detail** — candlestick chart with moving averages, Bollinger bands
and a choice of volume, RSI or MACD in the lower panel, with negative news
events marked on the price line. Plus quarterly fundamentals, a categorised news
timeline, a factor radar and a sector-peer table.

**News Intelligence** — the NLP pipeline and its findings: how each headline is
labelled, the sentiment vocabulary induced from the corpus, classifier
performance, discovered topics, and the event study measuring what actually
happens to prices after each category of disclosure.

**Signals** — thirteen rule-based conditions evaluated against the latest close:
trend crossings, RSI extremes, 52-week positions, dividend cover, negative-news
clusters, earnings-quality warnings. Scoped to the whole market, an index proxy,
your watchlist or your holdings.

**Watchlist** — a shortlist with relative performance and a one-month return
heat map, saved to disk.

**My Portfolio** — record what you actually hold, with share count, cost basis
and purchase date. The terminal values it at the latest close, reports
unrealised profit and loss per position, weighted volatility, beta and dividend
income, warns on concentration above a third of the book, and travels the
current weights back through history against the market index.

**Risk Profile** — the ten-question suitability test.

**Recommended Portfolio** — asset allocation, selected holdings with weights and
cash amounts, portfolio characteristics, a written rationale for every holding,
and a historical simulation against the market index.

**Portfolio Lab** — build any book by hand, weight it four different ways, choose
the window and the rebalancing rule, and measure it against the benchmark with
drawdown and per-holding contribution analysis.

---

## The NLP pipeline

Company disclosures are text, and text is only useful once it becomes something
measurable. Five stages, all running locally with no paid API and no external
model download.

### 1 · Keyword rules

Twenty-nine regular-expression patterns over the headline. Transparent and fast,
but blind to any phrasing not anticipated in advance — they left **23.4%** of
headlines unresolved.

### 2 · Weak supervision

The rule labels become training data for a TF-IDF linear support vector machine
(word unigrams and bigrams, 3-fold stratified cross-validation, 99.6% accuracy
and 0.986 macro-F1 across 23 classes). The model then labels what the rules
missed.

The accuracy figure must be read carefully. Because the training labels came
from the rules themselves, a high score means the model faithfully reproduces
the rules — not that it is 99.6% correct about reality. Its value is
generalisation to phrasings the rules never saw.

### 3 · Safety gate

Inspecting the model's output revealed a real failure: it labelled *"mai adds
new listed securities"* as a delisting, because exchange-administration
vocabulary co-occurs with delisting notices in training. Unchecked, that would
mark a healthy company as carrying negative news.

The merge is therefore asymmetric. Routine categories are accepted at a moderate
decision margin. A **negative** label additionally requires a high margin,
corroboration from a term in the induced lexicon, and the absence of a
positive-context phrase such as *"sign lifted"* or *"first day of trading"*.
Thirty-one predictions were rejected by that gate. False negatives are cheap;
false positives put a red flag on a company.

### 4 · Topic discovery

Non-negative matrix factorisation over the residual found two things. One topic
held roughly 8,800 headlines about establishing subsidiaries and joint ventures —
a genuine category the rules had no pattern for. Every other topic was dominated
by bare dates, independently rediscovering the Excel corruption documented in the
data-quality report.

**Unresolved headlines fell from 23.4% to 5.6%.**

### 5 · Event study — and the finding that changed the model

Classification is only worth something if the classes correspond to reality. For
every disclosure, the security's return over the following 1, 5 and 20 trading
days is compared with the cap-weighted market return over the same window. News
is mapped to the next trading day, so nothing uses information before it was
public.

The original design flagged nine categories as "negative news" on the basis of
what sounded bad. Measured against actual returns, **that binary flag had no
predictive power whatsoever**: mean 5-day abnormal return +0.13%, t = +1.00.

Individual categories clearly do move prices:

| Category | 20-day abnormal return | t |
|---|---|---|
| Warrant activity | −2.57% | −15.8 |
| Capital increase | −1.50% | −6.2 |
| SET clarification request | −1.85% | −3.1 |
| Financial statement | +0.62% | +9.6 |
| MD&A | +0.59% | +5.4 |
| Dividend | +0.28% | +2.2 |

So the sentiment score stopped relying on judgement. Each category is weighted by
the abnormal return actually observed after it, shrunk toward zero in proportion
to the noise in that estimate:

```
weight(category) = mean 20-day abnormal return × t² / (t² + 4)
```

Per security, those weights are summed over two years of disclosures with a
180-day half-life decay, producing `nlp_sentiment` and its market percentile
`nlp_sentiment_score`. These feed the screener, the security pages and the
stock-selection model, replacing the keyword red flag.

**One result deserves care.** Market surveillance notices show a *positive*
abnormal return (+2.99% over 20 days, t = +4.8). That does not mean regulatory
attention is good news — surveillance measures are imposed *after* a sharp
run-up, so the figure captures momentum continuing. It is a clean illustration
of why an automated signal still needs a human reading it.

### Honest limits of the NLP

Only headlines are read, never body text. The classification identifies the type
of disclosure; the event study measures the average reaction to that type;
neither is a judgement about an individual company. The event study is measured
in-sample over 2021–2025 and is not evidence that the effect will persist. All
figures are averages — a category with a negative mean still contains many
individually positive events. And 18,408 headlines were already destroyed by
Excel in the source export before this project received the file.

---

## Corporate actions — what the data actually showed

An earlier draft of this document warned that returns might be wrong because
prices were not adjusted for splits. That warning was tested and turned out to
be overstated, so it has been replaced with what the evidence shows.

Shares outstanding were inferred as market capitalisation divided by close. A
split or stock dividend appears as that count jumping while price falls by the
reciprocal. Across 914 securities and five years, exactly **seven** such events
exist, all small — ratios between 1.20 and 1.40, consistent with stock dividends
rather than par splits. They are listed in `data/corporate_actions.csv` and the
price history now carries an `adj_close` column that corrects for them. Only
0.14% of rows are affected.

The 164 days on which a security fell more than 35% were checked separately. In
every case market capitalisation fell in the same proportion as price, meaning
no share-count change occurred — these were real collapses, and the disclosure
record confirms it: KKC announced a default on loan interest and principal, and
KWI, CV and SAM were resuming trade after suspension.

Dividends are still not reinvested, so every return figure remains a price
return. That part of the original caveat stands.

---

## Does any of this actually work?

Every score in the app is computed over the full 2021–2025 window, so testing it
against returns from that same window would be circular. The Rankings page
therefore carries a genuine out-of-sample test. Factors are rebuilt using **only**
data available on a formation date — end of 2023 and end of 2024 — securities are
sorted into deciles, and the excess return over the following year is measured
against the market.

| Factor | Top − bottom decile | t | Verdict |
|---|---|---|---|
| Shallow drawdown | +26.0% | +5.8 | Works |
| Momentum 12M | +14.2% | +3.1 | Works |
| Momentum 6M | +16.8% | +1.5 | Weak evidence |
| Low volatility | +14.8% | +1.3 | Weak evidence |
| High dividend yield | +13.0% | +1.8 | Weak evidence |
| Large size | +6.1% | +0.5 | No evidence |
| Low P/BV | +5.6% | +1.2 | No evidence |
| **Low P/E** | **−0.9%** | **−0.1** | **No evidence** |

Avoiding deep drawdowns was the strongest signal in this market, and twelve-month
momentum also worked. Low P/E did not — the cheapest decile on earnings very
slightly underperformed the most expensive, with a t-statistic of −0.07. That is
worth stating plainly, because "buy low P/E" is exactly the rule a stock screener
is expected to endorse.

Two formation dates and roughly 800 securities is a small sample, and both test
years were falling markets, which flatters defensive factors. This is evidence,
not proof.

---

## How the recommendation works

### Layer 1 — asset allocation

The suitability score maps to one of five investor categories, and the category
sets the ceiling on risk assets.

| Score | Category | Investor type | Maximum in equities |
|---|---|---|---|
| Below 15 | 1 | Conservative | Fixed income only |
| 15 – 21 | 2 | Moderately Conservative | 25% |
| 22 – 29 | 3 | Balanced | 50% |
| 30 – 36 | 4 | Growth | 75% |
| 37 and above | 5 | Aggressive | 100% |

### Layer 2 — stock selection

Every candidate must first clear four hard gates: at least 250 trading days of
history, at least 1M THB of average daily turnover, no red flag for negative
news, and a risk band and liquidity tier permitted for that category.

Survivors are then scored, and **the scoring weights change with the category**.
A conservative mandate rewards low volatility, shallow drawdowns and dividend
income; an aggressive mandate rewards growth and return on capital instead. This
is what makes the five portfolios genuinely different rather than the same
defensive names re-ordered.

Selection is capped at two names per sector. Categories 1 to 3 are weighted
inversely to volatility, which lowers the volatility of the book as a whole;
categories 4 and 5 are weighted by fit score so that a promising name is not
penalised merely for being volatile.

---

## Metrics computed for every security

**Momentum** — returns over 1 week, 1, 3, 6 months, 1 and 3 years; CAGR; total
return.

**Risk** — annualised volatility over 30 days, 90 days, 1 year and the full
history; beta against the cap-weighted market index; maximum drawdown over 1
year and full history; Sharpe ratio; current distance below the all-time peak.

**Technical** — 52-week high and low and distance from each; 50- and 200-day
moving averages and price relative to them; golden-cross state; RSI(14).

**Valuation** — P/E, P/BV and dividend yield, both current and 3-year median.

**Quality and growth** — ROE, ROA, debt/equity, net margin, year-on-year revenue
and profit growth, plus trailing-twelve-month free cash flow, FCF margin, ROIC,
accruals as a share of assets, two-year annualised revenue and profit growth,
and a seven-point Piotroski-style quality score.

**News** — disclosure counts and negative-signal counts over 3 months, 1 year
and 2 years; the impact-weighted NLP sentiment score and its market percentile;
a count of items in categories with measured negative impact; and a red flag for
securities in the bottom decile of sentiment.

**Composite scores** — value, quality, momentum, low-volatility, income, growth
and overall, each expressed as a percentile rank against the full market.

---

## Known limits — please read before presenting

**Lookahead bias in the backtest.** The selection model uses volatility and
return computed over the entire 2021–2025 window and is then tested inside that
same window, so it effectively knew the future when it chose. The reported
results are therefore better than reality. The application states this on both
pages where a simulation appears. A methodologically sound test needs a training
window and a separate, later testing window.

**Prices are not adjusted for corporate actions.** No adjustment is made for
stock splits or dividends, so every return figure is a price return only.

**Historical data, not live.** The dataset ends in December 2025.

**News categories come from headline keywords.** They identify the type of
disclosure, not whether it is good or bad news, and the body text is never read.
Roughly 28% of headlines fall into "other", and 18,408 headlines were already
converted to date values by Excel in the source export and cannot be recovered.

**Survivorship bias.** The universe is what was listed at export time, so
securities delisted along the way are partly absent, which flatters
market-wide historical returns.

**Beta is measured against a constructed index.** No SET index series was
supplied, so the benchmark is a cap-weighted index built from these same
securities. It is verified: the cap-weighted average beta is 1.07, as it should
be by construction. Note that a single security, DELTA, is 13.9% of total market
capitalisation, which depresses measured beta for smaller names.

**This is an educational research tool, not investment advice.**

---

## Project layout

```
app.py                  navigation, sidebar, page registry
core/theme.py           colours, Plotly template, CSS — restyle from here
core/data.py            cached loaders
core/suitability.py     questionnaire, scoring, investor categories
core/screener.py        field catalogue, filter engine, strategy presets
core/recommend.py       allocation, eligibility, scoring, weighting
core/backtest.py        simulation, performance metrics, contribution
core/indicators.py      moving averages, RSI, Bollinger, MACD, ATR
core/store.py           local persistence for holdings, watchlist and profile
core/tables.py          the grid system — cell shading, sparklines, row selection
core/charts.py          chart treatment — crosshair, range buttons, candles
views/                  one file per screen
data/factor_backtest.csv  point-in-time decile test results
data/                   pre-built datasets, 22 MB total
```

### The interface

Tables are built through a single `tables.grid()` entry point, so every grid in
the application shares the same behaviour: signed percentages are shaded on a
diverging red-to-green scale whose intensity tracks the size of the move, scores
render as bars against the market percentile, a 60-session sparkline sits beside
each security, and clicking any row opens that security's detail page.

Charts go through `charts.py`, which adds a crosshair that labels both axes,
range buttons on every time series, and an optional log scale on price.

To restyle the whole application, edit the palette at the top of
`core/theme.py`. To change how every table behaves, edit `core/tables.py` once.

### Editing

Streamlit reloads on save, so changes appear immediately in the browser.

To change wording, edit the relevant file in `views/`. To restyle the whole
application, edit the palette at the top of `core/theme.py`. To change how
securities are selected, edit `WEIGHTS` and the gate constants at the top of
`core/recommend.py`. To add a screening criterion, add one line to `FIELDS` in
`core/screener.py` — the user interface builds itself from that dictionary.

Adding a metric that is not yet computed means rebuilding `data/factors.csv.gz`
from the full cleaned database in `../clean_data/set_clean.sqlite`.

---

## Deploying so others can reach it

See `DEPLOY.md` for the full walkthrough. In short: the repository is prepared at
60 files and 24 MB, nothing near GitHub's limits, with the virtual environment
and your personal `user_data.json` excluded. Push it with GitHub Desktop, deploy
from share.streamlit.io with `app.py` as the main file, then **check the app's
sharing setting** — an app inherits its visibility from the repository, so one
deployed from a private repo is invite-only until you switch it to public, and a
link alone will not let anyone in.

Two behaviours change once hosted. Saved state is no longer written to disk,
because every visitor would otherwise share one file; the app detects this and
keeps each person's watchlist and holdings in their own browser session. And the
app sleeps after a quiet period, taking about thirty seconds to wake, so open it
before you need to show it.
