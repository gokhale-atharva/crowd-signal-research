# Verification record — 2026-11-07

-52 tests collected. All passed across the release suite and the additional billing-guard subset.
- Ruff checks pass for src, tests, scripts and actors. Full bundle replay passed with socket
  connections denied, processing both exchanges, all14 model variants and HTML generation.
- Full45-session real price-only validation ran on HKEX and KRX:225 predictions per model per
  exchange, all ten assets through2026-11-06. This is historical validation, not a live outcome.
- Real price-only forward records for2026-11-09 were issued and committed on2026-11-07 UTC.
  Source and processed-input hashes are retained in each immutable file. No result exists yet.
- Browser: real/lab switches, both exchanges, company selection, search, sentiment sort, OHLC,
  sentiment overlay, backtest, ranking charts and JSON download passed; no console errors observed.
  Desktop and375px phone layouts fit without horizontal page overflow. Screenshots are in docs/img.
- Live Apify/Exa/LLM calls and custom actor deployment were not tested: credentials are absent.
  Telegram channels and two-source acceptance per exchange remain pending. No cost is invented.
- A clean installation on another operating system was not tested. The dependency snapshot records
  this workstation's installed project dependency closure. SDK actor create/build/call signatures
  were checked against installed apify-client2.5.1; billable launches are mocked in tests.
- GitHub repository creation remains unavailable: local gh has no authentication and the connected
  GitHub tool set has no repository-creation operation. No unrelated repository was modified.
