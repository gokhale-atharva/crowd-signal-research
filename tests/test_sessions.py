from datetime import date, datetime, time

import pytest

from crowd_signal.sessions import influence_session

SESSIONS = [date(2026, 11, 6), date(2026, 11, 9), date(2026, 11, 11)]


@pytest.mark.parametrize(
    ("instant", "expected"),
    [
        ("2026-11-06T01:00:00Z", date(2026, 11, 6)),  # Before open
        ("2026-11-06T04:30:00Z", date(2026, 11, 6)),  # HK lunch break
        ("2026-11-06T07:59:59Z", date(2026, 11, 6)),
        ("2026-11-06T08:00:00Z", date(2026, 11, 9)),  # At close: not before close
        ("2026-11-07T08:00:00Z", date(2026, 11, 9)),  # Weekend
        ("2026-11-10T02:00:00Z", date(2026, 11, 11)),  # Synthetic calendar holiday
    ],
)
def test_hk_influence_uses_supplied_session_calendar(instant, expected):
    assert (
        influence_session(datetime.fromisoformat(instant), SESSIONS, "Asia/Hong_Kong", time(16))
        == expected
    )


def test_korean_close_is_not_hong_kong_close():
    instant = datetime.fromisoformat("2026-11-06T06:30:00Z")
    assert influence_session(instant, SESSIONS, "Asia/Seoul", time(15, 30)) == date(2026, 11, 9)
    assert influence_session(instant, SESSIONS, "Asia/Hong_Kong", time(16)) == date(2026, 11, 6)


def test_refuses_to_guess_beyond_calendar_or_accept_naive_time():
    with pytest.raises(ValueError, match="No next session"):
        influence_session(
            datetime.fromisoformat("2026-11-12T08:00:00Z"), SESSIONS, "Asia/Seoul", time(15, 30)
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        influence_session(datetime(2026, 11, 6), SESSIONS, "Asia/Seoul", time(15, 30))
