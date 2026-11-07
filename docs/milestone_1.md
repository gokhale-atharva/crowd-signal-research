# Milestone 1 checkpoint · 2026-11-07

## Completed

- Installable Python package and Typer CLI with every requested command registered.
- Shared YAML configuration for five HKEX and five KRX assets, including local-language aliases.
- Typed Post, NewsItem, extraction, price-level, ticker-signal and prediction contracts.
- UTC/source-timezone preservation, price-calendar session assignment, stable content hashes,
  null engagement fields, and basic causal prediction timing checks.
- Small agent boundaries and one pipeline orchestrator; pending stages fail explicitly.
- Read-only official Apify SDK discovery: ten queries completed, zero Actor runs.
- Public input schemas, default build identifiers and event prices fetched for three candidates.
- Probe tool with 20-item / $0.10 requested event caps, timeout, no launch retries,
  raw run-manifest cache, and refusal of bulk imports/unbounded replies/extra paid features.
- Four marked synthetic parser fixtures; offline validation and preview export.
- Original report design using the requested midnight/cobalt/lime palette; three portable HTML files.
- Exchange switching, Chinese/Korean/English alias search, sorting, asset details,
  CSV export, accessible methodology dialog and reduced-motion CSS.
- README, environment example, security ignores, design/source decisions, dependency
  version snapshot, Makefile, submission status and desktop/mobile screenshots.

## Validation

- **36 pytest tests passed.** Tests cover config validation, key redaction/missing keys,
  timestamp parsing, exact content-hash equivalence, session boundaries, supplied-calendar
  holidays/weekends, timing contracts, probe budget inputs, real SDK call signatures,
  offline replay and honest CLI failure states.
- Ruff lint passed; Python files were formatted with Ruff.
- `doctor`, `replay`, CLI help and probe help ran successfully.
- Browser checks passed for exchange selection, Korean alias search, name sorting,
  empty searches, details, dialog Escape dismissal and CSV download. The downloaded
  CSV header and configured-only status were inspected.
- Responsive checks at requested 375, 768, 1024 and 1440px widths found no page-wide
  horizontal overflow after fixing the small-screen grid and navigation. The wide
  table scrolls within its labeled region. Browser console reported no JS errors.
- Desktop/mobile screenshots are in `docs/img/`.

The local validation environment is Python 3.13.5 on Windows. Registry downloads
were slow and sandbox temporary-directory permissions required workspace-local
temporary paths. The project virtual environment reused available host packages
for base dependencies; missing packages were installed locally. This is **not** a
claim that a fresh isolated install was tested. `requirements-dev.lock` records
the actual core/dev versions. The SDK imports an upstream deprecated `apify-shared`
package and produces one warning; it did not affect the checks.

## Step 0 findings

LIHKG and Telegram have public candidate listings with usable-looking schemas, but
no sampled posts have been inspected. LIHKG search returns listings and may need
separately billed content/replies. AAStocks' discovered actor is a news scraper,
not a social source. The Naver/KRX actors inspected describe prices/news rather
than the required discussion boards. Telegram still needs suitable finance channels.
Public API pricing shows the FREE-tier Telegram message rate exceeds its Store
headline starting price; documentation uses the FREE-tier figure.

## Still pending

User confirmed Apify and Exa keys are not set up. Authenticated source probes,
two-source acceptance for each exchange, custom-actor deployment if needed, Exa
queries and live market collection are pending. All statistical modelling,
sentiment/levels, charted results, full analytical replay and real live forward
prediction/evaluation belong to later milestones. No real forecasts or performance
claims exist. GitHub remote/publishing is pending; this is a local checkpoint.

The brief explicitly requests stopping for a milestone summary here. The next
milestone begins with authenticated, capped HKEX source tests after local keys exist.
