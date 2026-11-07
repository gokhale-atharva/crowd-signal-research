"""Assign instants using actual, exchange-local session dates supplied by market data."""

from bisect import bisect_left
from datetime import date, datetime, time
from zoneinfo import ZoneInfo


def influence_session(
    timestamp: datetime, sessions: list[date], timezone: str, market_close: time
) -> date:
    """Before close maps to this session; at/after close maps to the next observed session.

    Lunch-break posts influence the afternoon session on the same date. The caller
    supplies price/calendar sessions, so holidays and weekends are never guessed.
    No inferred weekday fallback is allowed beyond the calendar's horizon.
    """
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("Timestamp must be timezone-aware")
    if sessions != sorted(set(sessions)):
        raise ValueError("Session dates must be sorted and unique")
    local = timestamp.astimezone(ZoneInfo(timezone))
    index = bisect_left(sessions, local.date())
    if index < len(sessions) and sessions[index] == local.date():
        if local.time() >= market_close:
            index += 1
    if index >= len(sessions):
        raise ValueError("No next session in supplied calendar; extend the calendar horizon")
    return sessions[index]
