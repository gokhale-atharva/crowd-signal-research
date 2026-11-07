"""Read-only Store discovery and a deliberately small, opt-in authenticated probe."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apify_client import ApifyClient

from crowd_signal.config import Settings

SEARCHES = {
    "lihkg": "LIHKG",
    "futu_moomoo": "Moomoo",
    "futu": "Futu",
    "aastocks": "AAStocks",
    "etnet": "ETNet",
    "naver_board": "Naver Finance",
    "naver_discussion": "Naver stock discussion",
    "daum": "Daum Finance",
    "telegram": "Telegram channel",
    "blind": "Blind Korea",
}


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )
    return path


def _items(page: Any) -> list[dict]:
    return page["items"] if isinstance(page, dict) else page.items


def discover(output: Path) -> dict:
    """Search via apify-client, never start actors. Public access may be denied."""

    def search(entry: tuple[str, str]) -> dict:
        source, query = entry
        try:
            client = ApifyClient(max_retries=1, timeout_secs=20)
            page = client.store().list(search=query, limit=8)
            selected = []
            for actor in _items(page):
                selected.append(
                    {
                        key: actor.get(key)
                        for key in (
                            "id",
                            "username",
                            "name",
                            "title",
                            "description",
                            "isDeprecated",
                            "pricingInfos",
                            "stats",
                            "modifiedAt",
                        )
                        if key in actor
                    }
                )
            return {"source": source, "query": query, "status": "catalog_only", "actors": selected}
        except Exception as exc:
            # API exceptions can embed request URLs. Never emit credential-bearing errors.
            return {
                "source": source,
                "query": query,
                "status": "unavailable",
                "error_type": type(exc).__name__,
                "actors": [],
            }

    with ThreadPoolExecutor(max_workers=3) as pool:
        searches = list(pool.map(search, SEARCHES.items()))
    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        "method": "apify-client StoreCollectionClient.list; unauthenticated, read-only",
        "actor_runs": 0,
        "note": "Catalog presence is not proof of output quality, finance coverage, or reliability.",
        "searches": searches,
    }
    write_json(output, result)
    return result


def probe(actor_id: str, input_file: Path, settings: Settings, output: Path) -> dict:
    """Run one caller-reviewed input. No automatic retries of billable actor launches.

    API charge caps apply according to the actor's billing model; compute/proxy
    costs may be separate. This command is a feasibility probe, not live collection.
    """
    token = settings.require("apify_token")
    run_input = json.loads(input_file.read_text(encoding="utf-8"))
    if not isinstance(run_input, dict):
        raise ValueError("Actor input must be a JSON object")
    configured_limits = [
        run_input.get(name) for name in ("maxItems", "maxMessages") if name in run_input
    ]
    if not configured_limits or any(
        type(value) is not int or not 1 <= value <= settings.apify_max_items
        for value in configured_limits
    ):
        raise ValueError(
            "Input must set maxItems or maxMessages to 1..APIFY_MAX_ITEMS (at most 20)"
        )
    for key in (
        "keywords",
        "channels",
        "startUrls",
        "urls",
        "searchTerms",
        "catIds",
        "threadIds",
        "threadUrls",
    ):
        if key in run_input and (not isinstance(run_input[key], list) or len(run_input[key]) > 1):
            raise ValueError(f"Probe accepts at most one {key} entry to bound per-query billing")
    if any(
        run_input.get(key) for key in ("bulkInput", "urlsFromFile", "downloadMedia", "aiLabels")
    ):
        raise ValueError(
            "Bulk imports, media downloads and actor-side AI labels are disabled for probes"
        )
    if run_input.get("mode") == "thread":
        reply_limit = run_input.get("maxReplies")
        if type(reply_limit) is not int or not 1 <= reply_limit <= settings.apify_max_items:
            raise ValueError("Thread probes require maxReplies from 1 to 20 as well as maxItems")
    if any("REPLACE_WITH" in value for value in run_input.get("channels", [])):
        raise ValueError("Replace the example channel with a reviewed public finance channel")
    client = ApifyClient(token, max_retries=0, timeout_secs=30)
    actor = client.actor(actor_id)
    try:
        metadata = actor.get()
    except Exception as exc:
        raise ValueError(f"Could not inspect Actor metadata ({type(exc).__name__})") from None
    if not metadata:
        raise ValueError("Actor was not found or is inaccessible")
    pricing = metadata.get("pricingInfos") or []
    if not pricing or pricing[-1].get("pricingModel") not in {
        "PAY_PER_EVENT",
        "PRICE_PER_DATASET_ITEM",
    }:
        raise ValueError(
            "Probe requires inspectable pay-per-event or pay-per-result pricing; review other billing manually"
        )
    try:
        run = actor.call(
            run_input=run_input,
            max_items=settings.apify_max_items,
            max_total_charge_usd=settings.apify_max_total_charge_usd,
            timeout_secs=settings.apify_timeout_seconds,
            wait_secs=settings.apify_timeout_seconds + 15,
            restart_on_error=False,
        )
    except Exception as exc:
        raise ValueError(
            f"Actor request failed ({type(exc).__name__}); inspect Apify Console before retrying to avoid duplicate charges"
        ) from None
    if not run:
        raise ValueError("No run result returned; inspect Apify Console before retrying")
    manifest = {
        "checked_at": datetime.now(UTC).isoformat(),
        "actor_id": actor_id,
        "run_id": run["id"],
        "status": run["status"],
        "input": run_input,
        "max_items": settings.apify_max_items,
        "max_total_charge_usd": str(settings.apify_max_total_charge_usd),
        "usage_total_usd": run.get("usageTotalUsd"),
        "charged_event_counts": run.get("chargedEventCounts"),
        "pricing": pricing,
        "note": "Catalog field lists and run samples require manual semantic review before source selection.",
    }
    # Persist run ID before a dataset fetch so errors never conceal a billable run.
    write_json(output / "manifest.json", manifest)
    dataset_id = run.get("defaultDatasetId")
    if dataset_id:
        try:
            rows = _items(
                client.dataset(dataset_id).list_items(limit=settings.apify_max_items, clean=True)
            )
        except Exception as exc:
            raise ValueError(
                f"Run manifest saved; dataset fetch failed ({type(exc).__name__})"
            ) from None
        write_json(output / "items.json", rows)
        manifest["returned_count"] = len(rows)
        manifest["returned_fields"] = sorted({key for row in rows for key in row})
        write_json(output / "manifest.json", manifest)
    if run["status"] != "SUCCEEDED":
        raise ValueError(
            f"Run {run['id']} ended {run['status']}; manifest saved. Review before retrying."
        )
    return manifest
