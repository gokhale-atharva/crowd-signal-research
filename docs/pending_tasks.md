# Remaining work — 9 November 2026

## Completed in this revision

- Sentiment no longer replaces the chart with a dead-end placeholder. A real-price chart stays
  visible with an explicit missing-data explanation, a working simulated-analysis action and
  a link to source status. Mode, company, chart view and range survive page navigation.
- Added the Data sources page, capture counts, provider states and a downloadable owner guide.
- No-observation sentiment/direction/position are null in analytical output. An observed neutral
  score remains zero. Missing values are never converted into fabricated neutral evidence.
- Recent captured posts can be charted descriptively by publication day without being backdated
  into model features. The retrospective basis is labelled. At-session histories retain causal cutoffs.
- Repeated live collection retains first-seen text, engagement and observation time. Collection
  and recomputation invalidate downstream stage flags; incomplete runs cannot reuse stale forecasts.
- Live run-all preflights both exchanges before the first paid job. Doctor lists all setup blockers
  and supports --json / --strict. Provider secrets are never included in its output.
- Full test suite: 59 passed, including offline replay, causality, retained observations,
  interrupted-run protection, source preflight and portable page links.

## External dependencies still outstanding

1. **Real social/news capture:** no local .env or environment keys; hosted environment also empty.
   APIFY_TOKEN and EXA_API_KEY are required. The LLM key is optional. Real source certification
   requires capped runs, relevant timestamped bodies, reviewed public investor Telegram channels
   for both exchanges, and deployment/inspection of the included Naver board actor. A channel
   profile or a Store listing is not enough. No paid calls or actor deployment was claimed.
2. **GitHub delivery completed:** private repository https://github.com/gokhale-atharva/crowd-signal-research
   was approved by the user and created on 9 November. Source, reports and original Git history
   are supplied. Credential-pattern and excluded-path checks passed for the current tree and
   all345 original history objects before upload. No raw capture, .env or cache path was tracked.
3. **Forward outcome:** issued predictions target 9 November 2026. Their actual close cannot be
   evaluated before the target close. At the 9 November morning check, both sessions were still open.
   KRX closes at12:00 IST and HKEX at13:30 IST. Original prediction files stay immutable. Run evaluate after the
   relevant target close; no synthetic/backtest outcome may substitute for a genuine close.

These dependencies prevent claiming that the complete live assessment is finished.
