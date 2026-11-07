from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from crowd_signal.models import Post, Prediction


def post(**overrides):
    return Post.model_validate(
        {
            "ticker": "0700.HK",
            "text": "Tencent fixture",
            "source": "lihkg",
            "url": "https://example.invalid/post/1",
            "timestamp": "2026-11-06T15:59:00+08:00",
            **overrides,
        }
    )


def test_normalizes_to_utc_preserves_original_offset_and_unknown_engagement():
    record = post()
    assert record.timestamp == datetime(2026, 11, 6, 7, 59, tzinfo=UTC)
    assert record.original_timezone == "UTC+08:00"
    assert record.likes is None
    assert post(likes=0).likes == 0


def test_rejects_naive_timestamps_negative_metrics_and_raw_author_handles():
    for values in (
        {"timestamp": "2026-11-06T15:59:00"},
        {"likes": -1},
        {"author_handle": "person"},
    ):
        with pytest.raises(ValidationError):
            post(**values)


def test_content_hash_stable_across_case_spacing_and_compatibility_characters():
    assert post(text="  TENCENT   ７００ ").content_hash == post(text="tencent 700").content_hash
    assert post(text="different").content_hash != post().content_hash


def prediction(**overrides):
    return Prediction.model_validate(
        {
            "exchange": "HKEX",
            "ticker": "0700.HK",
            "issued_at": "2026-11-06T08:05:00Z",
            "features_available_at": "2026-11-06T08:00:00Z",
            "target_open": "2026-11-09T01:30:00Z",
            "target_session": "2026-11-09",
            "current_price": 100,
            "predicted_price": 100,
            "model_name": "contract-test-only",
            "model_trained_through": "2026-11-05",
            "mode": "synthetic_fixture",
            "confidence_note": "Fixture, not a forecast",
            **overrides,
        }
    )


def test_prediction_contract_allows_a_causal_fixture():
    assert prediction().target_session == date(2026, 11, 9)


@pytest.mark.parametrize(
    "values",
    [
        {"features_available_at": "2026-11-07T00:00:00Z"},
        {"issued_at": "2026-11-09T01:30:00Z"},
        {"model_trained_through": "2026-11-09"},
        {"predicted_price": float("nan")},
    ],
)
def test_prediction_contract_rejects_future_features_late_issuance_and_invalid_prices(values):
    # Contract tests only. A feature-level leakage test belongs to model milestone 4.
    with pytest.raises(ValidationError):
        prediction(**values)
