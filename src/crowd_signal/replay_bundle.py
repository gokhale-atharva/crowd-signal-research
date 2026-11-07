"""Portable, integrity-checked normalized input bundles for network-free replays."""

import hashlib
from pathlib import Path

import pandas as pd

from crowd_signal.models import NewsItem, Post
from crowd_signal.storage import write_json


def export_bundle(
    destination: Path,
    exchange: str,
    mode: str,
    bars: pd.DataFrame,
    posts: list[Post],
    news: list[NewsItem],
    schedule: list[dict],
    as_of: str,
    coverage: list[dict],
) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    bars.to_csv(destination / "bars.csv", index=False)
    for name, items in (("social.jsonl", posts), ("news.jsonl", news)):
        (destination / name).write_text(
            "".join(item.model_dump_json() + "\n" for item in items), encoding="utf-8"
        )
    write_json(destination / "sessions.json", {exchange: schedule})
    files = {
        "bars": "bars.csv",
        "posts": "social.jsonl",
        "news": "news.jsonl",
        "sessions": "sessions.json",
    }
    hashes = {
        name: hashlib.sha256((destination / name).read_bytes()).hexdigest()
        for name in files.values()
    }
    return write_json(
        destination / "bundle.json",
        {
            "schema_version": 2,
            "provenance": "live",
            "evidence_mode": mode,
            "as_of": as_of,
            "exchanges": [exchange],
            "files": files,
            "sha256": hashes,
            "coverage": coverage,
            "description": "Captured normalized observations; integrity hashes do not attest provider authenticity. Offline rescoring uses the disclosed lexicon fallback.",
        },
    )
