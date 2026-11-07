"""All social data is collected by capped Apify runs; no direct social scraping here."""

from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from pathlib import Path

from bs4 import BeautifulSoup

from crowd_signal.config import AssetConfig, ExchangeConfig, Settings
from crowd_signal.feasibility import probe
from crowd_signal.models import Post
from crowd_signal.processing import language_hint, parse_timestamp
from crowd_signal.storage import digest, event, read_json, write_json


def flatten_rows(rows: list[dict]) -> list[dict]:
    result = []
    for row in rows:
        children = []
        for key in ("posts", "replies", "comments"):
            if isinstance(row.get(key), list):
                children.extend({**row, **child} for child in row[key] if isinstance(child, dict))
        result.extend(children or [row])
    return result


def normalize_post(
    row: dict, asset: AssetConfig, source: str, exchange: ExchangeConfig, observed_at: datetime
) -> Post:
    text = next(
        (
            row[key]
            for key in ("text", "content", "msg", "message", "postText", "body")
            if row.get(key)
        ),
        None,
    )
    if not isinstance(text, str):
        raise ValueError("No post body; listing titles alone are not accepted")
    text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    timestamp = next(
        (
            row[key]
            for key in (
                "timestamp",
                "date",
                "createdAt",
                "created_at",
                "create_time",
                "post_time",
                "publishedAt",
            )
            if row.get(key) is not None
        ),
        None,
    )
    if timestamp is None:
        raise ValueError("No source timestamp")
    url = row.get("url") or row.get("postUrl") or row.get("link")
    if not url and source == "lihkg" and row.get("thread_id"):
        url = f"https://lihkg.com/thread/{row['thread_id']}/page/1"
    author = row.get("authorId") or row.get("user_id") or row.get("author") or row.get("user")
    if isinstance(author, dict):
        author = author.get("id") or author.get("user_id") or author.get("username")

    def number(*names):
        for name in names:
            value = row.get(name)
            if value is not None:
                try:
                    return max(0, int(str(value).replace(",", "")))
                except (ValueError, TypeError):
                    return None
        return None

    return Post(
        ticker=asset.ticker,
        timestamp=parse_timestamp(timestamp, exchange.timezone),
        observed_at=observed_at,
        text=text,
        source=source,
        url=url,
        author_hash=digest(f"{source}:{author}") if author else None,
        likes=number("likes", "like_count", "likeCount", "recommendCount"),
        reposts=number("reposts", "forwards", "shareCount"),
        views=number("views", "viewCount", "view_count"),
        author_followers=number("author_followers", "followerCount", "followers"),
        language=language_hint(text),
    )


class ApifyCollector:
    def __init__(self, settings: Settings):
        self.settings = settings

    def validate_sources(self, exchange: ExchangeConfig) -> None:
        self.settings.require("apify_token")
        unsupported = set(exchange.proposed_sources) - {"lihkg", "telegram", "naver_board"}
        if unsupported:
            raise ValueError(f"No reviewed input adapter for {', '.join(sorted(unsupported))}")
        missing = [
            source for source in exchange.proposed_sources if not exchange.actor_ids.get(source)
        ]
        if missing:
            raise ValueError(
                f"Configure actor_ids for {', '.join(missing)}. For Naver, deploy actors/naver_board and record its returned ID in YAML."
            )
        if "telegram" in exchange.proposed_sources and not exchange.telegram_channels:
            raise ValueError(
                "Set telegram_channels in exchange YAML to reviewed public investor channels before spending Apify credits"
            )

    def collect(
        self, exchange: ExchangeConfig, root: Path, as_of: datetime
    ) -> tuple[list[Post], list[dict]]:
        self.validate_sources(exchange)
        since = as_of - timedelta(days=10)
        jobs = [
            (asset, source, alias, channel)
            for asset in exchange.tickers
            for source in exchange.proposed_sources
            for alias in dict.fromkeys(asset.aliases)
            for channel in (exchange.telegram_channels if source == "telegram" else [None])
        ]
        # Reserve one extra call for each search hydration. Requested caps, not assumed bills.
        cap = min(
            self.settings.apify_max_total_charge_usd,
            (self.settings.apify_workflow_budget_usd / Decimal(len(jobs) * 2)).quantize(
                Decimal("0.001"), rounding=ROUND_DOWN
            ),
        )
        if cap < Decimal("0.01"):
            raise ValueError(
                "Configured sources/aliases exceed the workflow budget at a useful per-run cap. Reduce channel count or explicitly raise the workflow budget within available credit."
            )
        posts, coverage = [], []
        reserved = Decimal(0)
        for asset in exchange.tickers:
            for source in exchange.proposed_sources:
                target = (
                    root / "data/raw" / as_of.date().isoformat() / source / f"{asset.ticker}.json"
                )
                if target.exists():
                    cached = read_json(target)
                    posts.extend(Post.model_validate(row) for row in cached["normalized"])
                    coverage.append(cached["coverage"])
                    continue
                raw_runs, normalized, rejected = [], [], 0
                asset_jobs = [
                    job for job in jobs if job[0].ticker == asset.ticker and job[1] == source
                ]

                def run(
                    run_input: dict,
                    index: str,
                    target_path=target,
                    actor_id=exchange.actor_ids[source],
                    runs=raw_runs,
                ) -> list[dict]:
                    nonlocal reserved
                    if reserved + cap > self.settings.apify_workflow_budget_usd:
                        raise ValueError(
                            "Workflow requested-charge cap exhausted; cached completed runs are retained"
                        )
                    directory = target_path.with_suffix("") / index
                    if (directory / "manifest.json").exists() and not (
                        directory / "items.json"
                    ).exists():
                        raise ValueError(
                            "Prior paid run has no cached dataset; inspect its manifest instead of launching again"
                        )
                    if (directory / "manifest.json").exists() and (
                        directory / "items.json"
                    ).exists():
                        manifest = read_json(directory / "manifest.json")
                        if manifest["status"] != "SUCCEEDED":
                            raise ValueError(
                                "Prior incomplete actor run exists; inspect it before retrying"
                            )
                        rows = read_json(directory / "items.json")
                    else:
                        reserved += cap
                        directory.mkdir(parents=True, exist_ok=True)
                        input_path = directory / "input.json"
                        write_json(input_path, run_input)
                        settings = self.settings.model_copy(
                            update={"apify_max_total_charge_usd": cap}
                        )
                        manifest = probe(actor_id, input_path, settings, directory)
                        rows = read_json(directory / "items.json")
                    runs.append({"manifest": manifest, "items": rows})
                    return rows

                for index, (_, _, alias, channel) in enumerate(asset_jobs):
                    if source == "lihkg":
                        actor_input = {
                            "mode": "search",
                            "keywords": [alias],
                            "order": "desc_create_time",
                            "dateFrom": "10d",
                            "maxItems": self.settings.apify_max_items,
                            "aiLabels": False,
                        }
                    elif source == "telegram":
                        actor_input = {
                            "channels": [channel],
                            "resultsType": "messages",
                            "searchQuery": alias,
                            "oldestMessageDate": since.isoformat(),
                            "newestMessageDate": as_of.isoformat(),
                            "maxMessages": self.settings.apify_max_items,
                            "downloadMedia": False,
                        }
                    elif source == "naver_board":
                        actor_input = {
                            "ticker": asset.ticker.split(".")[0],
                            "keywords": [alias],
                            "dateFrom": since.isoformat(),
                            "maxItems": self.settings.apify_max_items,
                            "maxPages": 3,
                        }
                    else:
                        raise ValueError(
                            f"No input adapter for {source}; configure a supported source instead"
                        )
                    rows = run(actor_input, f"search-{index}")
                    bodies = flatten_rows(rows)
                    if source == "lihkg" and not any(
                        any(
                            row.get(field)
                            for field in ("text", "content", "msg", "message", "body")
                        )
                        for row in bodies
                    ):
                        first = next(
                            (row for row in rows if row.get("thread_id") or row.get("threadId")),
                            None,
                        )
                        if first:
                            thread_id = str(first.get("thread_id") or first.get("threadId"))
                            bodies = flatten_rows(
                                run(
                                    {
                                        "mode": "thread",
                                        "threadIds": [thread_id],
                                        "maxItems": 1,
                                        "maxReplies": self.settings.apify_max_items,
                                        "aiLabels": False,
                                    },
                                    f"thread-{index}",
                                )
                            )
                    for row in bodies:
                        try:
                            observed = parse_timestamp(raw_runs[-1]["manifest"]["checked_at"])
                            post = normalize_post(row, asset, source, exchange, observed)
                            if since <= post.timestamp <= as_of:
                                normalized.append(post)
                        except (ValueError, TypeError):
                            rejected += 1
                info = {
                    "ticker": asset.ticker,
                    "source": source,
                    "actor_id": exchange.actor_ids[source],
                    "usable_posts": len(normalized),
                    "rejected_rows": rejected,
                    "status": "verified_run" if normalized else "no_usable_posts",
                    "query_count": len(asset_jobs),
                    "max_event_charge_per_run_usd": str(cap),
                    "window_start": since.isoformat(),
                    "window_end": as_of.isoformat(),
                }
                write_json(
                    target,
                    {
                        "runs": raw_runs,
                        "coverage": info,
                        "normalized": [post.model_dump(mode="json") for post in normalized],
                    },
                )
                coverage.append(info)
                posts.extend(normalized)
                event("social", **info)
        missing = [
            f"{row['ticker']} / {row['source']}" for row in coverage if row["usable_posts"] == 0
        ]
        if missing:
            raise ValueError(
                f"Two-source acceptance failed: no usable posts for {', '.join(missing)}. Raw runs are cached; do not claim complete coverage."
            )
        return posts, coverage
