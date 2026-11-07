# CODEX PROMPT: Exchange Sentiment Price-Prediction Agent (CrowdWisdomTrading intern task)

Paste everything below the line into Codex. Put the first section in `AGENTS.md` at the repo root so it persists across sessions.

---

## Role and goal
You are a senior Python engineer. Build a reproducible, agent-style pipeline that scrapes retail-investor social posts (via Apify) and news (via Exa) for 5 assets per exchange, extracts structured per-ticker signals, ranks tickers in a visual HTML report, and predicts the next trading day's (n+1) price with honest out-of-sample validation.

This is a hiring assessment. Reviewers will (1) clone the repo, (2) run it with my Apify and Exa keys, (3) read the README and report. Optimise for: it runs first try, results are honest, code is clean, the report looks good. Do not over-engineer. A working end-to-end slice beats a half-finished framework.

## Hard requirements (from the task brief)
- Python only. Apify for all social scraping. Exa (exa.com) for news.
- Exchanges: **Hong Kong (HKEX / Hang Seng universe)** is mandatory. **Korea (KRX)** is the second exchange; implement it through the same config-driven code path, as a second milestone. Only 5 tickers per exchange.
- Per exchange, use **at least 2 different social sources** from this list:
  - HK: LIHKG, Telegram, Futu/Moomoo community, AAStocks, ETNet
  - KR: Naver Finance discussion boards (종목토론실), Daum Finance, KakaoTalk open chat / Telegram, Blind
- Scrape the **last 10 days** per asset using ticker, cashtag, and keyword searches (Chinese, Korean and English names/aliases).
- For each post extract: UTC timestamp, text, likes/reposts/views (whatever the source exposes, null if absent), author follower count (null if absent), source, URL. Align with price bars.
- Per ticker output: `ticker, asset_name, current_price, sentiment (score), direction (bullish/bearish/neutral), position (long/short/none, as stated by authors), support_levels, resistance_levels`, plus creative extras (see below).
- Visual report per exchange, tickers sorted by social mentions and by sentiment score and direction.
- Predict price at n+1 and check results (backtest and one genuine live forward prediction).
- Deliverables: GitHub repo, README, `.env.example`, list of Apify actor IDs used.

## Step 0: discover feasibility BEFORE writing the pipeline
1. Using the Apify API (`apify-client`), search the Apify Store for actors for each candidate source (LIHKG, Futu/Moomoo, AAStocks, ETNet, Naver Finance board, Daum, Telegram). A LIHKG actor exists in the store (e.g. `claude_code_reviewer/lihkg-scraper-en`); verify it by running a tiny test and inspecting output fields.
2. For each exchange pick the 2 most reliable sources. Run a small test (limit about 20 items) and log: actor ID, input schema used, fields returned, cost per 100 items.
3. If no usable store actor exists for a source, write a **small custom Apify actor** (Crawlee/Python or Node) and deploy it to my Apify account, or fall back to the next source on the list. Record the decision in `docs/source_decisions.md`. Never use a source that cannot be reproduced by a reviewer.
4. Budget: the Apify free plan has only about $5 of monthly credit. Set `maxItems` / `maxTotalChargeUsd` on every run, and estimate total cost in the README. Cache every raw response to `data/raw/<date>/<source>/<ticker>.json`.

## Architecture (agents = small, single-purpose modules with typed I/O, orchestrated by one CLI)
```
src/
  config.py            # exchanges, tickers, aliases (zh-HK, ko, en), sources; pydantic settings
  agents/
    collector.py       # ApifyCollector: runs actors, normalises to Post model, caches raw
    news.py            # ExaNewsAgent: news search per ticker (EN + local language), dated, deduped
    market.py          # MarketData: OHLCV via yfinance (0700.HK, 005930.KS ...), UTC/exchange-tz handling
    sentiment.py       # SentimentAgent: LLM structured extraction with fallback (below)
    levels.py          # support/resistance
    model.py           # n+1 predictor + walk-forward evaluation
    report.py          # Plotly HTML report
  pipeline.py          # orchestrates; each stage reads/writes parquet in data/processed
  cli.py               # typer: collect | analyse | train | predict | evaluate | report | run-all | replay
tests/                 # pytest: timestamp alignment, leakage test, dedupe, parsing, levels
data/sample/           # small committed sample so reviewers can run `replay` with NO API keys
```
- Pydantic models: `Post`, `NewsItem`, `TickerSignal`, `Prediction`.
- Async or threaded fetching with retries/backoff; structured logging; clear errors when a key is missing.
- Everything keyed by config: adding a ticker/exchange = editing YAML, not code.
- `replay` mode runs the full pipeline from cached/sample raw data without network. This is a key differentiator: reviewers can verify the pipeline even if my free credits run out.

## Data handling rules
- Convert all timestamps to UTC; keep original tz. Map each post to the **trading session** it can influence: HKEX 09:30-16:00 HKT (with lunch break), KRX 09:00-15:30 KST. Posts after the close go to the next session. Handle weekends and holidays using the price calendar.
- Dedupe (exact + near-duplicate), drop obvious spam/bots (very short, repeated, link-only), language-detect.
- Sentiment engagement weight: `w = (1 + log1p(likes + reposts + 0.1*views)) * (1 + log1p(followers))^0.5`, times an exponential time decay. Document and justify it.
- Exa: use the news category, `startPublishedDate` = 10 days back for the live window, queries in English plus local-language names, and use the contents/summary. Also pull a **longer news history (about 60-90 days)**, because Exa supports date filters. This gives a longer sentiment series for modelling than the 10-day social window.

## Sentiment and extraction (the creative part)
- `SentimentAgent` sends batches of posts and news to an LLM with a strict JSON schema (use whichever provider key is in `.env`, default OpenAI-compatible, configurable). Per post return: `sentiment [-1,1]`, `direction`, `stated_position (long/short/none)`, `price_levels_mentioned`, `is_spam`, `language`. Cache by content hash so reruns cost nothing.
- Offline fallback when no LLM key: multilingual model (e.g. `cardiffnlp/twitter-xlm-roberta-base-sentiment`) or a small lexicon, so `replay` works anywhere. Report which scorer was used.
- Aggregate per ticker: mention count, weighted mean sentiment, bull/bear ratio, sentiment momentum (last 2 days vs prior), dispersion (disagreement), % of authors stating long vs short, news sentiment separately from social.
- `position`: majority stated position among authors who explicitly state one, with the counts (e.g. "long 62% of 21").
- Support/resistance: combine (a) swing-high/low fractal clustering on 6-12 months of daily OHLC, (b) classic pivots from the last session, (c) round-number levels, (d) levels mentioned in posts (flag the crowd-sourced ones). Output the top 2 supports and 2 resistances nearest the current price, with a strength score.
- Optional LLM "analyst note" per ticker (2-3 sentences) summarising why sentiment is where it is, citing the top news item. Must not invent facts; pass only retrieved text.

## Prediction n+1 (be statistically honest, this is what will impress reviewers)
- **Target:** next-trading-day log return of close, converted back to price. Evaluate against the naive baselines: (1) random walk (price_{t+1} = price_t), (2) zero/mean return, (3) price-only model.
- **Features at t (only data available before close of t):** lagged returns, realised volatility, RSI, volume z-score, plus sentiment features (weighted social sentiment, mention volume, bull/bear ratio, news sentiment, momentum).
- **Models:** Ridge/ElasticNet and a small gradient-boosting model (LightGBM or sklearn). Keep it simple; pooled panel across the 5 tickers of an exchange with ticker fixed effects, and per-ticker variants.
- **Validation:** walk-forward / expanding-window only. No random splits. Include a unit test that proves no feature uses information from t+1. Report MAE, RMSE, MAPE on price, directional accuracy, and hit rate vs baseline, with bootstrap confidence intervals and a Diebold-Mariano (or paired bootstrap) test against the random walk.
- **Ablation:** price-only vs price+social vs price+news vs all. State plainly whether sentiment adds value.
- **Be honest in the README:** the social window is only 10 days, so sample size is tiny and results are very likely NOT statistically significant. Say so, show the confidence intervals, and describe how you would scale it (longer scraping history, intraday bars, more tickers). Never overclaim.
- **Live forward test:** `predict` writes a timestamped, immutable prediction file for the next session (`predictions/<exchange>_<date>.json`) and commits it BEFORE the market opens; `evaluate` fills in the actual close afterwards and appends to `predictions/results.csv`. Include this in the README as the genuine out-of-sample check.

## Report (single self-contained HTML per exchange, plus an index page, committed under `reports/`)
- Ranked table: ticker, name, price, mentions, weighted sentiment, direction, position split, support/resistance, predicted n+1 price and % change, confidence note. Sortable and colour-coded.
- Charts (Plotly): mentions bar ranking, sentiment bar ranking (diverging colours), sentiment vs price overlay per ticker, candlestick with support/resistance lines, predicted vs actual (backtest + live), ablation chart with error bars.
- Short "How to read this / limitations" panel. Also render screenshots into `docs/img/` for the README.
- Must look professional (clean typography, consistent palette, readable on laptop and phone). Enable GitHub Pages or commit the HTML so it opens by double-click.

## Security and submission hygiene
- Never hard-code or commit keys. `.env.example` lists `APIFY_TOKEN`, `EXA_API_KEY`, `LLM_API_KEY` (optional). `.gitignore` covers `.env`, caches with personal data, and `data/raw` (commit only `data/sample`).
- Scraped posts are public but personal. Store only what the model needs: hash or drop author handles in committed samples.
- README sections: Overview, Architecture diagram (mermaid), Quick start (`replay` in 3 commands, live in 5), Actor IDs and inputs and costs, Methodology, Results with honest limitations, How to reproduce, Project structure, Next steps.
- A `Makefile` or `justfile`: `make setup`, `make replay`, `make live`, `make test`.
- Create `SUBMISSION.md` containing the repo link, the Apify actor IDs, and placeholders for tokens (the real tokens go only in the email, never in the repo).

## Milestones (work in this order; commit after each; stop and show me a summary at each)
1. Scaffold, config, models, CLI skeleton, tests infrastructure.
2. Step 0 feasibility results + HKEX collector for 2 sources + Exa news + market data. Run live for 5 HK tickers; cache raw data.
3. Sentiment/extraction, levels, per-ticker signal table.
4. Model + walk-forward evaluation + ablation + tests for leakage.
5. HTML report for HKEX; README draft; `replay` mode with sample data.
6. KRX through the same code path (2 sources), regenerate reports.
7. Live forward prediction committed before the open; evaluation after the close; final README polish.

Start with milestone 1 and Step 0 now. Ask me only if a decision is truly blocking; otherwise make a reasonable choice and note it in `docs/decisions.md`.

## Suggested HK ticker set (edit if data is thin)
0700.HK Tencent, 9988.HK Alibaba, 3690.HK Meituan, 1810.HK Xiaomi, 0005.HK HSBC (pick the 5 with the most discussion volume in your test run).
## Suggested KR ticker set
005930.KS Samsung Electronics, 000660.KS SK Hynix, 035420.KS NAVER, 035720.KS Kakao, 373220.KS LG Energy Solution.
