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

## Spatial UI verification —2026-11-08

The report-generation smoke test passed with the new embedded resources; Ruff and JavaScript
syntax checks passed. Browser checks confirmed a real WebGL canvas, correct stock/exchange
and real/simulated mode changes, OHLC fallback, motion pause, rotation/reset and scene rebuilds.
Desktop1440, laptop1024, tablet768 and phone375px widths fit without horizontal page overflow.
No JavaScript errors were observed. Reduced-motion handling and non-WebGL fallback are
implemented; the OS motion preference was not changed during testing. The backend forecasts
and prior price data were not altered by this visual revision. Three.js/Motion notices are retained.

## Multi-page landing revision — 8 November 2026

- Added a dedicated landing page with original Three.js research layers and Motion entrance,
  separate/reassemble, reset, keyboard rotation and pause controls. Static links remain available.
- Added markets, ten company pages, crowd/news, model validation and methodology, using real
  file URLs. Main CTA opens a new tab; ordinary navigation keeps the research context.
- Rewrote headline, destination cards, page headings and notices in short product-specific copy.
- Checked the local render at1280×800,900×900 and390×844; no document overflow at the checked
  widths. Reviewed 3D separation, pause/reset, keyboard, browser back, company navigation,
  exchange switching, crowd selection, synthetic labels, OHLC and14-model results.
- Browser console had no application errors in the reviewed pages. The vendored classic
  Three.js build reports its known upstream deprecation warning.
- Python checks: portable link/asset/heading test and existing offline provenance replay test,
  **2 passed**. Initial test setup could not use the sandbox's system temp; rerun used a fresh
  workspace-local temporary directory. Both generated application scripts pass Node syntax checks.
- Proof: docs/img/landing-desktop.png, landing-mobile.png and model-page.png.
- Existing price data and immutable forecasts were preserved. No source credentials were added.

## Sentiment availability and completion audit — 8 November 2026

The full suite passed: **59 tests**, one upstream Apify deprecation warning. Node syntax checks
pass for generated research.js. Tests cover no observations versus an observed neutral score,
retrospective chart points versus causal features, repeat capture retention, failed-write stage
invalidation, preflight before any paid job, and all18 portable pages plus companion assets.
Browser checks exercised Kakao real-price sentiment fallback, one-click labelled simulated
sentiment, source coverage counts, exchange/mode/context navigation and owner setup. Console
had no application errors. Phone390px checks showed no document overflow; the source table
retains its own keyboard/touch scroll. Existing 3D and ordinary chart routes remain available.
Screenshots: sentiment-lab.png, source-status-desktop.png and source-status-mobile.png.

No Apify/Exa credentials exist locally or in the hosted environment. No social capture or live
source certification was performed. Prediction files were preserved. See pending_tasks.md for
external dependencies, including GitHub approval and the future target-session close.


## Submission release 13 November 2026

A fresh isolated Python 3.12.14 environment installed pyproject.toml successfully. Pip check found no broken requirements. All67 tests passed; Ruff passed for src/tests/scripts/actors. The full336-post, two-exchange keyless replay completed from a separate working directory with no provider keys. New tests cover rolling-window expiry, retained inspected imports and flagged vendor ranges that preserve model closes/volumes.

The original pre-open issues were evaluated against genuine9November closes without changing issue bytes. Updated real models use four causal sentiment/news feature sessions, with only two sentiment-informed held-out sessions; no predictive benefit is claimed. Both exchanges and every current asset have social observations, with uneven platform coverage. TVB replaces Xiaomi in the active watchlist; the original forward universe and results remain preserved.

The repository was made public after full-history credential/excluded-path checks. GitHub Pages deploys the report from committed source because the former hosting service currently rejects host-managed Git authentication. No API keys, raw captures, caches or author identifiers are published.
