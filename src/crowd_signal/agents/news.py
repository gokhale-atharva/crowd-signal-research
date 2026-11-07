"""Dated Exa news collection. Publication is distinct from point-in-time availability."""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx

from crowd_signal.config import AssetConfig, ExchangeConfig, Settings
from crowd_signal.models import NewsItem
from crowd_signal.processing import language_hint, parse_timestamp
from crowd_signal.storage import read_json, write_json


def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), "", ""))


class ExaNewsAgent:
    def __init__(self, settings: Settings):
        self.settings = settings

    def collect(self, exchange: ExchangeConfig, root: Path, as_of: datetime) -> list[NewsItem]:
        key = self.settings.require("exa_api_key")

        def collect_asset(asset: AssetConfig) -> list[NewsItem]:
            path = root / "data/raw" / as_of.date().isoformat() / "exa" / f"{asset.ticker}.json"
            if path.exists():
                payload = read_json(path)
            else:
                responses = []
                local = next(
                    (alias for alias in asset.aliases if any(ord(char) > 127 for char in alias)),
                    asset.asset_name,
                )
                for days in (10, self.settings.news_history_days):
                    for name in dict.fromkeys((asset.asset_name, local)):
                        query = {
                            "query": f"{name} {asset.ticker} stock company news",
                            "category": "news",
                            "type": "auto",
                            "numResults": 12,
                            "startPublishedDate": (as_of - timedelta(days=days)).isoformat(),
                            "endPublishedDate": as_of.isoformat(),
                            "contents": {"text": {"maxCharacters": 6000}, "summary": True},
                        }
                        for attempt in range(3):
                            try:
                                with httpx.Client(timeout=35) as client:
                                    response = client.post(
                                        "https://api.exa.ai/search",
                                        headers={"x-api-key": key},
                                        json=query,
                                    )
                                if response.status_code in (429, 500, 502, 503) and attempt < 2:
                                    time.sleep(2**attempt)
                                    continue
                                response.raise_for_status()
                                responses.append({"query": query, "response": response.json()})
                                # Persist each completed query, so a later failure does not lose paid work.
                                write_json(
                                    path,
                                    {
                                        "retrieved_at": as_of.isoformat(),
                                        "queries": responses,
                                        "complete": False,
                                    },
                                )
                                break
                            except httpx.HTTPStatusError as exc:
                                raise ValueError(
                                    f"Exa returned HTTP {exc.response.status_code} for {asset.ticker}"
                                ) from None
                            except httpx.RequestError:
                                if attempt == 2:
                                    raise ValueError(
                                        f"Exa network failure for {asset.ticker}; cached partial responses retained"
                                    ) from None
                                time.sleep(2**attempt)
                payload = {
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "queries": responses,
                    "complete": True,
                }
                write_json(path, payload)
            if not payload.get("complete", False):
                raise ValueError(
                    f"Partial Exa cache for {asset.ticker}; inspect it and explicitly remove or complete it before retrying"
                )
            seen = set()
            result = []
            for query in payload["queries"]:
                for row in query["response"].get("results", []):
                    url = row.get("url", "")
                    if not url or not row.get("publishedDate") or canonical_url(url) in seen:
                        continue
                    published = parse_timestamp(row["publishedDate"])
                    if (
                        not as_of - timedelta(days=self.settings.news_history_days)
                        <= published
                        <= as_of
                    ):
                        continue
                    text = (
                        row.get("text")
                        or row.get("summary")
                        or " ".join(row.get("highlights") or [])
                    )
                    if not text:
                        continue
                    result.append(
                        NewsItem(
                            ticker=asset.ticker,
                            timestamp=published,
                            retrieved_at=parse_timestamp(payload["retrieved_at"]),
                            title=row.get("title") or asset.asset_name,
                            text=text,
                            url=url,
                            language=language_hint(text),
                        )
                    )
                    seen.add(canonical_url(url))
            return result

        with ThreadPoolExecutor(max_workers=2) as pool:
            return [item for batch in pool.map(collect_asset, exchange.tickers) for item in batch]
