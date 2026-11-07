"""Conservative text dedupe, timestamp parsing and language hints."""

import re
from datetime import UTC, datetime
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

from crowd_signal.models import Post


def parse_timestamp(value, timezone: str = "UTC") -> datetime:
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        number = float(value)
        return datetime.fromtimestamp(number / 1000 if number > 10**11 else number, UTC)
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00").replace(".", "-", 2)
            if re.match(r"^\d{4}\.\d{2}\.\d{2}", str(value))
            else str(value).replace("Z", "+00:00")
        )
    return parsed.replace(tzinfo=ZoneInfo(timezone)) if parsed.tzinfo is None else parsed


def language_hint(text: str) -> str:
    if re.search(r"[가-힣]", text):
        return "ko"
    if re.search(r"[\u3400-\u9fff]", text):
        return "zh"
    return "en"


def obvious_spam(text: str) -> bool:
    stripped = re.sub(r"https?://\S+", "", text).strip()
    if len(stripped) < 6:
        return True
    words = stripped.casefold().split()
    return (len(words) > 7 and len(set(words)) <= 2) or bool(
        re.search(r"(?:guaranteed profit|join my vip|保證獲利|수익 보장)", stripped, re.I)
    )


def clean_posts(posts: list[Post], threshold: float = 0.94) -> tuple[list[Post], dict]:
    kept: list[Post] = []
    by_ticker: dict[str, list[Post]] = {}
    exact: set[tuple[str, str]] = set()
    counts = {"input": len(posts), "spam_removed": 0, "duplicates_removed": 0}
    for post in sorted(posts, key=lambda item: item.timestamp):
        if obvious_spam(post.text):
            counts["spam_removed"] += 1
            continue
        key = (post.ticker, post.content_hash)
        prior = by_ticker.setdefault(post.ticker, [])
        duplicate = key in exact or any(
            abs((post.timestamp - other.timestamp).total_seconds()) <= 86400
            and len(post.text) > 35
            and SequenceMatcher(
                None, post.text.casefold(), other.text.casefold(), autojunk=False
            ).ratio()
            >= threshold
            for other in prior[-100:]
        )
        if duplicate:
            counts["duplicates_removed"] += 1
            continue
        if not post.language:
            post.language = language_hint(post.text)
        kept.append(post)
        prior.append(post)
        exact.add(key)
    counts["retained"] = len(kept)
    return kept, counts
