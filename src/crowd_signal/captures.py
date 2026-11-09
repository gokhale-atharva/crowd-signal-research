"""Import inspected, cached Apify probes without relaunching paid jobs."""

import re
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

from crowd_signal.agents.collector import flatten_rows, normalize_post
from crowd_signal.config import ExchangeConfig
from crowd_signal.models import Post
from crowd_signal.processing import clean_posts, parse_timestamp
from crowd_signal.storage import read_json


def mentions_asset(text: str, aliases: list[str]) -> bool:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    for alias in aliases:
        term = unicodedata.normalize("NFKC", alias).casefold()
        if term.isascii():
            pattern = "0?" + re.escape(term) if term.isdigit() and len(term) == 4 else re.escape(term)
            if re.search(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", normalized):
                return True
        elif term in normalized:
            return True
    return False


def import_verified_probes(
    exchange: ExchangeConfig, root: Path, selections: list[dict], as_of: datetime,
    allow_partial: bool = False,
) -> tuple[list[Post], list[dict]]:
    """Each selection identifies a source and its locally inspected probe directory.

    Titles alone are rejected. Each retained body must mention its target company.
    An explicit partial import can show genuine observations while preserving the
    unfulfilled two-source acceptance gate in its coverage records.
    """
    raw_root = (root / "data/raw").resolve()
    captured, runs, failures, attempted = [], {}, {}, {}
    for selection in selections:
        source = selection["source"]
        if source not in exchange.proposed_sources:
            raise ValueError(f"Source {source} is not configured for this exchange")
        folder = (root / selection["directory"]).resolve()
        if not folder.is_relative_to(raw_root):
            raise ValueError("Probe directories must stay inside data/raw")
        manifest = read_json(folder / "manifest.json")
        if manifest.get("status") != "SUCCEEDED":
            raise ValueError("Only completed inspected Apify runs can be imported")
        if manifest.get("actor_id") != exchange.actor_ids.get(source):
            raise ValueError("Probe actor does not match the configured source actor")
        observed = parse_timestamp(manifest["checked_at"])
        if observed > as_of:
            raise ValueError("Probe observation time cannot be later than the capture")
        rows = flatten_rows(read_json(folder / "items.json"))
        query = " ".join(str(manifest.get("input", {}).get(k) or "") for k in ("keywords", "searchQuery"))
        attempted.setdefault(source, set()).update(selection.get("tickers", []))
        attempted[source].update(a.ticker for a in exchange.tickers if mentions_asset(query, a.aliases))
        if source == "telegram" and not manifest.get("input", {}).get("searchQuery"):
            attempted[source].update(a.ticker for a in exchange.tickers)
        runs.setdefault(source, set()).add(manifest["run_id"])
        # Consumer-device threads and index-only replies are not company sentiment.
        finance_threads = set()
        if source == "lihkg":
            for row in rows:
                context = " ".join(str(row.get(k) or "") for k in ("title", "own_text"))
                if re.search(r"股|財報|盈利|營收|業績|投資|手持|持有|KOSPI|KRX|shares|earnings|주가|주식|매수|매도|코스피", context, re.I):
                    finance_threads.add(str(row.get("thread_id") or ""))
        for row in rows:
            if source == "lihkg" and str(row.get("thread_id") or "") not in finance_threads:
                continue
            # Do not assign every reply in a multi-company/index thread to each stock.
            # Quoted text is another author's evidence, not this author's opinion.
            context = str(row.get("own_text") or "") if source == "lihkg" else " ".join(
                str(row.get(key) or "") for key in ("text", "content", "body"))
            targets = {a.ticker for a in exchange.tickers if mentions_asset(context, a.aliases)}
            for asset in exchange.tickers:
                if asset.ticker not in targets:
                    continue
                try:
                    post = normalize_post(row, asset, source, exchange, observed)
                    if as_of - timedelta(days=10) <= post.timestamp <= as_of:
                        captured.append(post)
                except (TypeError, ValueError):
                    failures[source] = failures.get(source, 0) + 1
    captured, _ = clean_posts(captured)
    coverage = []
    for source in exchange.proposed_sources:
        for asset in exchange.tickers:
            count = sum(p.ticker == asset.ticker and p.source == source for p in captured)
            coverage.append({
                "source": source, "ticker": asset.ticker,
                "actor_id": exchange.actor_ids.get(source),
                "run_ids": sorted(runs.get(source, set())), "usable_posts": count,
                "rejected_rows": failures.get(source, 0),
                "status": "verified_run" if count else "no_usable_posts" if asset.ticker in attempted.get(source, set()) else "not_queried" if source in runs else "not_collected",
                "window_start": (as_of - timedelta(days=10)).isoformat(),
                "window_end": as_of.isoformat(),
            })
    if not allow_partial and any(not any(row["source"] == source and row["usable_posts"] for row in coverage) for source in exchange.proposed_sources):
        raise ValueError("Two-source acceptance is incomplete; explicit allow_partial is required to display this capture")
    return captured, coverage
