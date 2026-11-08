"""Keep the first captured version of an observation across repeated collections."""

from datetime import datetime
from typing import TypeVar

from crowd_signal.models import NewsItem, Post

Observation = TypeVar("Observation", Post, NewsItem)


def retain_first_observations(
    previous: list[Observation], current: list[Observation], as_of: datetime,
) -> list[Observation]:
    """Freeze first-seen text and engagement; later snapshots must not rewrite the past."""
    selected = {}
    for item in previous + current:
        observed = item.retrieved_at if isinstance(item, NewsItem) else item.observed_at
        if observed is None or observed > as_of or item.timestamp > as_of:
            raise ValueError("Captured history requires an observation time at or before as_of")
        key = (item.ticker, getattr(item, "source", "exa"), str(item.url), item.timestamp)
        prior = selected.get(key)
        prior_time = None if prior is None else (
            prior.retrieved_at if isinstance(prior, NewsItem) else prior.observed_at
        )
        if prior_time is None or observed < prior_time:
            selected[key] = item
    return sorted(selected.values(), key=lambda item: (item.timestamp, item.ticker, str(item.url)))
