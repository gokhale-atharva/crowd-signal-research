# Implementation decisions

## 2026-11-07 · milestone 1

- Follow the brief's checkpoint order: scaffold plus Step 0 research now; stop for
  a milestone summary before live collection / later milestones.
- Put the standalone repository under `outputs/crowd-signal/` so it is an explicit,
  user-facing deliverable. Preserve the supplied brief in `docs/task_brief.md`.
- Use Python 3.11+ with a standard `src/crowd_signal/` package rather than making
  `src` itself the import namespace. Preserve the requested small-agent separation.
- Use Pydantic v2 contracts, Pydantic Settings, YAML, Typer, Jinja and the official
  Apify SDK. Heavy market/model libraries are a `pipeline` extra for later work.
- Both exchanges use one config contract; sources are proposals until actually
  tested. The ten configured assets are not an assertion of live coverage.
- The user confirmed API keys are not set up. No authenticated actor run, custom
  actor deployment, Exa call, live collection, model fit or forecast is claimed.
- The report at this checkpoint is a portable, interactive design preview. Replay
  validates four explicitly synthetic parser fixtures; it is not yet the full
  analytical replay required in milestone 5. Pending CLI stages exit with status 2.
- Timestamps must be timezone-aware. Preserve source timezone, normalize UTC, and
  use a supplied list of observed sessions. At-close posts map to the next session
  because features must be available strictly before close. Lunch stays on the same
  HK session. Never guess holidays from weekdays or beyond the calendar horizon.
- Store a separate retrieval timestamp for news. A historical publication timestamp
  alone cannot establish historical availability of later edits or engagement counts.
- Author-stated position is a separate enum from sentiment. Missing engagement is
  null, distinct from observed zero. No author handles exist in committed fixtures.
- Discover public Store metadata without credentials. Never automatically launch
  every candidate. A probe uses one reviewed input, 20 results, a $0.10 requested
  event-charge cap, and a run timeout. Do not automatically retry billable launches.
- Keep price results and sources genuinely empty until evidence exists. No stock
  price, forecast, sentiment score or backtest statistic is hardcoded into the UI.
- Local git checkpoints are appropriate; no GitHub remote or public deployment has
  been created. A before-open forecast commit will require actual model output and
  a suitable future session, not a retrospective synthetic file.

## Completion pass — 2026-11-07

- Continue beyond milestone boundaries under the user's explicit instruction to finish the work.
- Implement both exchanges through one code path. Preserve source feasibility as a real acceptance
  gate: a missing key, untested actor or empty source is not a verified live feed.
- Provide a complete generated fixture bundle for network-free end-to-end review, with permanent
  simulated provenance. Keep real public-price backtests in a different report mode.
- Do not backdate newly retrieved news/engagement into historical training windows. Long historical
  social/news features require contemporaneous snapshots. Use predetermined Ridge price-only
  forecasts when no such historical observations exist.
- Replace the earlier editorial preview with a data-driven observatory using the user's palette,
  Motion state transitions, Plotly OHLC and rankings. Preserve reduced-motion/keyboard behavior.
- GitHub connector is connected but exposes no repository-creation operation; local gh is not
  authenticated. Preserve the full local Git checkout and Sites source instead of claiming a
  GitHub deliverable exists. Do not upload into an unrelated existing repository.
- The next genuine forward session is2026-11-09. Issue audited price-only forecasts now and leave
  outcomes pending until the actual close. Do not start a fake evaluation or scheduled claim.
