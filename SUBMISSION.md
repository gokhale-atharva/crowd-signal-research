# Submission status

Implemented: config-driven HKEX/KRX collection adapters, Exa news, real public market data,
multilingual extraction/fallback, causal features, levels,14 model/baseline comparisons,
walk-forward uncertainty, full offline replay, immutable forecasting/evaluation, and portable UI.

- Hosted report: https://crowd-signal-research-desk.chandrashekhargokh96.chatgpt.site
- Private GitHub repository: https://github.com/gokhale-atharva/crowd-signal-research
- Actual authenticated Apify actor runs: none (API key not supplied).
- Candidate IDs: `claude_code_reviewer/lihkg-scraper-en`, `scrapesage/telegram-scraper`.
- Custom private Naver actor: `actors/naver_board`, not deployed; ID assigned by Apify on deployment.
- Two-source live acceptance per exchange: pending actual capped runs and verified channels.
- Genuine price-only forward forecasts: target2026-11-09; see `predictions/` for issue records.
- Genuine forward outcomes: pending target close; do not substitute backtest or fixture outcomes.

Tokens are placeholders only; provide actual values privately, never in Git:

- Apify: `[PRIVATE — NOT IN REPOSITORY]`
- Exa: `[PRIVATE — NOT IN REPOSITORY]`
- Optional LLM: `[PRIVATE — NOT IN REPOSITORY]`

See README for actual results, reproduction, costs and limitations. No submission email was sent.

Revision2026-11-08: sentiment recovery, a source-status page, retained observations and setup/
stage guards are implemented. Full suite59 passed. Live sources remain uncertified without
credentials. See docs/pending_tasks.md for exact blockers.

Revision2026-11-09: the user approved private repository creation and source/report upload.
The source repository preserves the original pre-open forecast commit history. API keys, raw
captures and caches are excluded. Outcome evaluation remains pending today’s official closes.
