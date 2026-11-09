# Status — 9 November 2026

## Completed

- Both exchanges use the user's requested LIHKG + Telegram combination. Actual capped,
  authenticated runs returned relevant company bodies from both platforms in each exchange.
- HKEX:11 company-linked social records,163 Exa articles. KRX:14 records,136 Exa articles.
  News covers all ten companies. Social coverage is5/5 HKEX and4/5 KRX companies, with
  uneven platform coverage. These are small samples, not population measurements.
- Public-channel messages, source timestamps and stable URLs were inspected. Title-only
  listings, quote-only replies, device reviews and unrelated index replies are excluded.
  The source page shows counts for every company/platform; missing scores remain null.
- Company-specific sentiment scopes and caches prevent a multi-company message from sharing
  another company's score. Current scoring is the labelled lexicon fallback, not an LLM.
- The community page opens captured evidence, including old price-only bookmarks. Rankings,
  source citations and dated news are populated. The separate simulated mode remains labelled.
- Keys are saved only in ignored local.env. Tests explicitly disable.env loading. Reports
  contain aggregate signals and source URLs, excluding raw bodies and author identifiers.
- The approved private GitHub repository contains source, reports and original forecast history:
  https://github.com/gokhale-atharva/crowd-signal-research
-63 tests passed, including source acceptance, company relevance, credential isolation, point-in-time
  features, offline replay and report pages. Desktop and390px phone browser checks passed.

## Remaining limits

1. **Coverage:** no relevant LG Energy Solution social post was returned in tested channels or
   LIHKG searches. Some other companies have evidence from only one platform. Exa news is
   available for all ten. Do not fill missing samples with generated or unrelated posts.
2. **Historical sentiment:** current retrieval cannot be backdated. Social/news captured today
   were unavailable at older model cutoffs; the historical ablation cannot establish sentiment's
   predictive value. Accumulate first-seen observations before future sessions.
3. **Forward outcome:** original price-only predictions target9November2026. At this morning
   check, KRX closes at12:00IST and HKEX at13:30IST. Evaluate only after each target close
   and availability of genuine daily bars. Original issue records remain immutable.
4. **Hosting:** the site is a saved report, without automatic collection. Refresh locally and
   republish when a new capture is desired. No subscription or billing upgrade was enabled.

See feasibility/capture_summary.json for actual run IDs, observed usage and per-company coverage.
