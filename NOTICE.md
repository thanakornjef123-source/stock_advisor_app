# Notice on data and use

## The data is not mine to give away

Every figure in this application derives from files supplied by the Stock
Exchange of Thailand covering 2021–2025. Those files arrived under whatever
terms accompanied them, and this project does not grant anyone a licence to
them. If you publish this application on the open internet you are
redistributing that data, which those terms may not permit.

The safe route is to deploy from a **private** repository and switch only the
app to public, so the interface is reachable by link while the underlying files
are not downloadable. `DEPLOY.md` explains how.

## The code

The application code — everything in `app.py`, `core/`, `views/` and `nlp/` —
was written for this project and may be read, modified and reused freely for
study. The `data/` folder is a different matter, as above.

## What this application is not

It is an educational research tool built on historical data that ends in
December 2025. It is not investment advice, not a recommendation to buy or sell
any security, and nothing in it is a forecast.

Three limitations are worth repeating because they change how the numbers should
be read:

* The portfolio suggested after the risk questionnaire is selected using
  volatility and return measured over the whole 2021–2025 window and then tested
  inside that same window. That is lookahead bias, and the application says so on
  the page where the simulation appears.
* Returns are price returns. Dividends are never reinvested, so income-oriented
  holdings are understated everywhere.
* The news signal is calibrated on the same period it is measured over. It
  describes what happened after each category of disclosure in that window; it
  does not predict what will happen next.

Anyone presenting this work should state these plainly rather than let a viewer
assume otherwise.
