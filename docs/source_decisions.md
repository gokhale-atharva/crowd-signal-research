# Step 0 · source feasibility

Reviewed 2026-11-07. **Public discovery only; zero authenticated actor runs.**
The user confirmed Apify and Exa credentials have not been configured. Store
listings describe intended behavior; they do not prove usable output or reliability.
The machine-readable SDK search result is recorded in `feasibility/store_discovery.json`.

All ten SDK Store searches completed successfully without credentials. Public
metadata and current build input schemas were also fetched for LIHKG, Telegram
and AAStocks, saved in `feasibility/candidate_metadata.json`. These are schemas and
catalog observations, not sampled social posts or test-run outputs.

| Exchange / source | Candidate | Decision at this checkpoint |
| --- | --- | --- |
| HKEX / LIHKG | `claude_code_reviewer/lihkg-scraper-en` | Public listing confirmed; first candidate to probe. Search results may be thread metadata rather than full post bodies; inspect before accepting. |
| HKEX / Futu/Moomoo | Not selected | Moomoo query returned zero; Futu query returned unrelated future/futures actors. |
| HKEX / AAStocks | `bovi/aastocks-scraper` | Public schema describes news feeds, not investor posts. Rejected as a social source. |
| HKEX / ETNet | Not selected | Query returned unrelated EONET/ELNET actors; no suitable match in the first eight results. |
| HKEX / Telegram | `scrapesage/telegram-scraper` | Candidate only; suitable public investor channels must be identified. Search is within a supplied channel, not global discovery. |
| KRX / Naver board | No suitable actor verified | `parseforge/naver-finance-scraper` is a price/fundamental-data listing and does not establish discussion-board support. Do not count it as a social source. |
| KRX / Daum | Not selected | Query returned unrelated finance actors; no suitable match in the first eight results. |
| KRX / Telegram | `scrapesage/telegram-scraper` | Candidate, not a second verified social source until Korean investor-channel coverage is tested. |
| KRX / Blind | Not selected | Blind Korea query returned zero results. |

## Candidate inputs and advertised costs

The [LIHKG listing](https://apify.com/claude_code_reviewer/lihkg-scraper-en) advertises
keyword search and threads/replies. The fetched build schema confirms `dateFrom`,
`maxItems` and `maxReplies`. The probe uses one keyword, `dateFrom: 10d`, 20 listings
and disabled actor AI labels. API pricing lists $0.002/listing, $0.008/thread content,
$0.003/reply and $0.005/start event per memory unit. Full text therefore costs more
than the headline $0.20 / 100 listings. Proxy costs are separate.
Returned fields and observed cost remain **unmeasured** until the test runs.

The [Telegram listing](https://apify.com/scrapesage/telegram-scraper) advertises a
starting message rate of $1.10 / 1,000, but fetched current API pricing gives
**FREE-tier $0.002/message ($0.20/100)**; $0.0011 is the GOLD tier. Its documented
example includes `date`, `text`, `url` and `views`; these are **documented fields,
not observed fields**. Subscriber metadata is separate from individual author
followers. The example input has an explicit channel placeholder; replace it with
one reviewed public finance channel before any run. Disable media downloads.

The [Naver listing](https://apify.com/parseforge/naver-finance-scraper) describes
prices, fundamentals and analyst data. Reject it for social-source acceptance
unless an actual board-output mode is documented and tested.

## Reproduce discovery and the first test

```powershell
crowd-signal feasibility
python scripts/inspect_sources.py
# After adding APIFY_TOKEN to local .env:
crowd-signal probe claude_code_reviewer/lihkg-scraper-en --input docs/inputs/lihkg_probe.json --output data/raw/feasibility/lihkg
```

The [official Python SDK](https://docs.apify.com/api/client/python/reference/class/StoreCollectionClient)
provides Store keyword search. The
[actor API](https://docs.apify.com/api/client/python/reference/class/ActorClient)
supports `max_items`, `max_total_charge_usd` and run timeouts. The total-charge
parameter applies to pay-per-event billing; the item cap bounds pay-per-result
events. These are not a guarantee that all account-level compute/proxy/rental
charges fit a global budget. The probe refuses uninspectable or unsupported billing
models and records the run ID before fetching a dataset. Review the account's
remaining credit before live collection.

The SDK code is checked against installed `apify-client 2.5.1`, whose Actor call
uses `timeout_secs` / `wait_secs` (not the newer documentation's duration names).
An SDK autospec test checks that call signature. Bulk imports, unbounded thread
replies, media downloads and actor-side AI labels are refused by the probe.

For each actual test, record the actor build, exact input, run ID, returned fields,
row count, timestamp/text completeness, 10-day coverage, ticker relevance, and
observed charges per 100 usable posts. Zero rows is not success. Manually inspect
public author text, retain only needed fields, and hash/drop author handles in any
future committed sample. Do not commit raw actor data.

## Acceptance gate and fallback

Milestone 2 requires **two tested social sources for HKEX** with relevant records
for five assets; milestone 6 applies the same gate to KRX. Each source must have
UTC-convertible timestamps, text, stable URLs, nulls for unavailable engagement,
and reproducible inputs. LIHKG listing-only output may need thread hydration.
Telegram channel output needs investor relevance and adequate historical coverage.

If no Store actor meets a source's contract, implement a small custom Python Apify
actor in a later milestone and deploy it after credentials exist, or test another
allowed source. Do not mark this fallback deployed or billable tests completed now.

## Exa

The [Exa search API](https://exa.ai/docs/reference/search) supports news-category
search with publication date filters and contents. Milestone 2 will issue English
and local-language queries for 10 days of current news and 60–90 days of history,
deduplicate URLs, and preserve publication plus retrieval times. No Exa request
was made at this checkpoint. Exa pricing is separate from Apify credit.

## Implementation update — 2026-11-07

Both exchange adapters and the full downstream pipeline now exist. Source verification remains
pending because no keys were supplied. The included private `actors/naver_board` source can be
deployed with `crowd-signal deploy-actor`; this is not a claim that its endpoints or robots rules
have passed a live test. A disallowed endpoint fails explicitly; use another permitted source.
Set the returned actor ID and reviewed Telegram channels in the exchange YAML before collection.
LIHKG listing-only results trigger a bounded first-thread hydration. Every source/ticker must
produce usable timestamped body text before collection passes. Actor inputs and run IDs are cached.

The probe permits a private actor with unknown billing only after verifying account ownership;
its256MB/timeout bounds constrain compute, but event-charge limits do not cap compute/build bills.
The default collector reserves at most$2 requested event charges per exchange. No measured cost
per100 usable posts is available until a real run. See README for the current cost model.

Exa's10/90-day English/local queries are implemented, preserving retrieval times. Current retrieval
is not backdated for model features. Captured replay bundles let reviewers rerun privately offline.
Real public price-only runs completed for all ten configured assets through2026-11-06; these do
not satisfy the two-social-source acceptance gate. The report states this distinction visibly.

## Channel review — 8 November 2026

Public discovery was reviewed without treating it as an authenticated source run. The
[StockIntelligence profile](https://t.me/s/StockIntelligence) mainly exposes automated quote/ranking
messages; that alone does not establish retail opinion and was not activated as a sentiment
source. Its linked discussion group needs an actual permitted, reproducible collection test.
The [Corevalue profile](https://t.me/s/corevalue) describes a Korean research/disclosure channel;
it is a discovery candidate only, with asset coverage, original opinion versus reposts, recent
history and actor compatibility still unverified. Neither profile was copied into a live dataset
or counted toward the required two-source acceptance. Raw post collection remains through Apify.

## Authenticated capture — 9 November 2026

This update supersedes the earlier untested-source checkpoint above. The user explicitly
requested LIHKG + Telegram for **both** exchanges, changing the original KRX source selection.
Naver and Daum were not deployed or bypassed. Source metadata alone was not counted.

28 capped Apify runs were inspected. Recorded run usage totals$0.084 at capture time;
this is observed API usage, not a guarantee of the final account invoice or all platform costs.
Limits remained20 items /$0.10 requested event charge per launch, timeout120s and no actor AI labels.
Some searches returned zero records or an actor request-failure message despite SUCCEEDED;
these are retained as coverage gaps. Raw captures and credentials remain ignored locally.

After relevance/time/deduplication checks, HKEX has11 company-linked records: LIHKG3 and
Telegram8. KRX has14: LIHKG2 and Telegram12. A multi-company body can count against multiple
assets. Each retained body explicitly mentions its target company. LIHKG titles alone,
quote-only replies, consumer-device threads and unrelated index replies are rejected.
Examples of successful inspected runs include LIHKG aS96MoFfruYMPQOG6 and
kqub8bTHVoji3kDa6; Telegram qkaOqw2bdjm0GQ4yv, Y733dAe78fk5M3vwJ,
TJSRvyxZbVkvx8MVB and wKZuGAyLaitqXnZE5. Exact inputs and all run IDs are recorded in
[the public-safe capture summary](feasibility/capture_summary.json).

HK Telegram uses theartoftrade; KR uses h_zonstock and meritz_research. These public channels
include publisher/broker research and reposts, so they are not treated as a representative
retail population. No personal author identity or ownership is inferred from a channel name.
LIHKG supplies community/forum evidence. Both platforms have relevant records per exchange,
but individual company/platform gaps remain visible. LG Energy Solution has no usable social
match in this sample. The displayed rule-based lexicon scores have no calibrated accuracy claim.

Exa authenticated search and contents returned299 deduplicated-per-ticker articles:163 HKEX,
136 KRX. Publication and retrieval times are separate. Current social/news retrieval is not
backdated into historical features. New observations cannot prove historical predictive value.
The original pre-open price-only issue records remain unchanged and await actual target closes.


## Submission refresh 13 November 2026

The ten-day capture was refreshed and original first-observed9November records retained for causal modelling. All five Korean assets now have relevant social records, including LG Energy Solution. Xiaomi searches returned stale/irrelevant bodies or actor failures, so none were fabricated or counted. The original prompt permits choosing assets with better coverage: TVB0511.HK now occupies that current HKEX slot and has a verified financial LIHKG body. The original Xiaomi pre-open issue and actual outcome remain immutable historical evidence.

Both exchanges still use LIHKG + Telegram at the user's explicit later request. These are two platforms per exchange, not two guaranteed matches per company. Small publisher/broker Telegram samples are disclosed. Full run IDs, inputs, observed costs and current coverage are in feasibility/capture_summary.json. Unsupported, zero-row and irrelevant results do not count.
