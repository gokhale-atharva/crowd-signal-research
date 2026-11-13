# Submission

Repository: https://github.com/gokhale-atharva/crowd-signal-research (public)
Current report: https://gokhale-atharva.github.io/crowd-signal-research/
Portable report: reports/index.html; self-contained exchange files: reports/hkex.html and reports/krx.html.

Actual Apify actors: claude_code_reviewer/lihkg-scraper-en and scrapesage/telegram-scraper.
Apify token: [PROVIDE PRIVATELY — NEVER COMMIT]
Exa token: [PROVIDE PRIVATELY — NEVER COMMIT]
Optional LLM: not configured; current scoring is the labelled multilingual lexicon fallback.

Current captures: 23 company-linked social records in the ten-day window, 505 retained Exa articles.
Both platforms returned relevant posts per exchange, and all ten current assets have at least one usable social match.
HKEX current watchlist replaces Xiaomi with TVB because of current-window coverage. Original Xiaomi issue/results remain unchanged.
Both current forecasts use causal social/news features. Four available feature sessions and two sentiment-informed test sessions do not establish predictive value.
Original pre-open9November forecasts now have genuine actual closes in predictions/results.csv. Random walk performed better overall in both exchanges.

Fresh isolated Python3.12 install,66 tests, lint and full offline replay passed. See README for remaining limits and the provider-range disclosure.
The repository is public; reviewer invitations are unnecessary. No email or token was sent automatically.
