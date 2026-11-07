import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from crowd_signal.agents.collector import normalize_post
from crowd_signal.agents.levels import find_levels
from crowd_signal.agents.model import NextSessionModel, causal_training_rows
from crowd_signal.agents.sentiment import engagement_weight, lexicon_extract
from crowd_signal.analytics import NEWS_FEATURES, PRICE_FEATURES, SOCIAL_FEATURES, build_features
from crowd_signal.config import load_config
from crowd_signal.forward import evaluate_forecast, write_forecast
from crowd_signal.models import NewsItem, Post
from crowd_signal.processing import clean_posts

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def market_fixture():
    bars = pd.read_csv(ROOT / "data/sample/bars.csv", dtype={"ticker": str, "session": str})
    bars = bars[bars.ticker == "0700.HK"].tail(100).copy()
    schedule = json.loads((ROOT / "data/sample/sessions.json").read_text())["HKEX"]
    return bars, schedule


def test_future_prices_cannot_change_past_features(market_fixture):
    bars, schedule = market_fixture
    original = build_features(bars, schedule, [], [], [], [])
    cutoff = original.session.iloc[-15]
    altered = bars.copy()
    altered.loc[altered.session > cutoff, ["open", "high", "low", "close"]] *= 1.8
    changed = build_features(altered, schedule, [], [], [], [])
    columns = ["session"] + PRICE_FEATURES + SOCIAL_FEATURES + NEWS_FEATURES
    assert_frame_equal(
        original.loc[original.session <= cutoff, columns],
        changed.loc[changed.session <= cutoff, columns],
    )


def test_retrieval_and_observation_times_are_not_backdated(market_fixture):
    bars, schedule = market_fixture
    feature_session = str(bars.session.iloc[-4])
    close = datetime.fromisoformat(
        next(s["close"] for s in schedule if s["session"] == feature_session)
    )
    published = close - timedelta(days=8)
    observed = close + timedelta(minutes=1)
    post = Post(
        ticker="0700.HK",
        text="Bullish growth",
        source="telegram",
        url="https://example.invalid/post",
        timestamp=published,
        observed_at=observed,
    )
    news = NewsItem(
        ticker="0700.HK",
        title="Growth",
        text="Bullish growth",
        url="https://example.invalid/news",
        timestamp=published,
        retrieved_at=observed,
    )
    features = build_features(
        bars, schedule, [post], [news], [lexicon_extract(post.text)], [lexicon_extract(news.text)]
    )
    assert (
        not features.loc[
            features.session <= feature_session, ["social_available", "news_available"]
        ]
        .to_numpy()
        .any()
    )
    next_session = next(
        s["session"] for s in schedule if datetime.fromisoformat(s["close"]) > observed
    )
    row = features[features.session == next_session].iloc[0]
    assert row.social_available == 1 and row.news_available == 1
    post.observed_at = None
    unknown = build_features(bars, schedule, [post], [], [lexicon_extract(post.text)], [])
    assert unknown.social_available.sum() == 0


def test_training_labels_are_known_at_each_test_close(market_fixture):
    bars, schedule = market_fixture
    features = build_features(bars, schedule, [], [], [], [])
    cutoff = features.session.iloc[-10]
    train = causal_training_rows(features, cutoff)
    assert (train.session < cutoff).all() and (train.target_session <= cutoff).all()
    result = NextSessionModel(bootstrap_samples=100, min_train_sessions=30, test_sessions=5).train(
        features
    )
    assert result.predictions.model.nunique() == 14
    assert result.predictions.session.nunique() == 5
    assert result.forecast[0]["model_name"] == "ridge_price_only"
    assert result.metrics["methodology"]["forecast_model"] == "ridge_price_only"
    for fold in result.folds:
        assert fold["max_label_session"] <= fold["test_start"]
        assert fold["max_feature_session"] < fold["test_start"]


@pytest.mark.parametrize(
    "text,language",
    [("Bullish growth buy", "en"), ("看好 增長 利好", "zh"), ("상승 호재 매수", "ko")],
)
def test_bullish_opinion_does_not_imply_position(text, language):
    score = lexicon_extract(text)
    assert score.sentiment > 0 and score.stated_position == "none" and score.language == language


def test_explicit_positions_levels_and_decay():
    assert lexicon_extract("I am short, resistance at 420").stated_position == "short"
    assert lexicon_extract("我持有，支撐 400").stated_position == "long"
    assert lexicon_extract("$0700 bullish growth").price_levels_mentioned == []
    assert lexicon_extract("support at 400").price_levels_mentioned == [400]
    now = datetime(2026, 11, 6, tzinfo=UTC)
    post = Post(
        ticker="0700.HK",
        text="I hold Tencent shares",
        source="telegram",
        url="https://example.invalid/p",
        timestamp=now,
    )
    assert engagement_weight(post, now + timedelta(days=3)) == pytest.approx(0.5)
    assert post.likes is None and post.views is None
    kept, counts = clean_posts([post, post.model_copy(update={"text": " I HOLD Tencent shares "})])
    assert len(kept) == 1 and sum(counts.values()) >= 1


def test_normalizer_rejects_listing_and_preserves_unknown_metrics():
    exchange = load_config().exchange("HKEX")
    observed = datetime(2026, 11, 6, 12, tzinfo=UTC)
    with pytest.raises(ValueError, match="body"):
        normalize_post(
            {"title": "Tencent discussion", "date": "2026-11-06"},
            exchange.tickers[0],
            "lihkg",
            exchange,
            observed,
        )
    post = normalize_post(
        {
            "content": "<p>I am long Tencent</p>",
            "date": "2026-11-06T10:00:00",
            "url": "https://lihkg.com/thread/1/page/1",
            "user_id": "private-handle",
        },
        exchange.tickers[0],
        "lihkg",
        exchange,
        observed,
    )
    assert post.timestamp.hour == 2 and post.likes is None and post.views is None
    assert post.author_hash != "private-handle" and "<p>" not in post.text


def test_levels_are_on_correct_side(market_fixture):
    bars, _ = market_fixture
    support, resistance = find_levels(bars, [300, 400])
    assert len(support) <= 2 and len(resistance) <= 2
    assert all(x.price < bars.close.iloc[-1] and 0 <= x.strength <= 1 for x in support)
    assert all(x.price > bars.close.iloc[-1] and 0 <= x.strength <= 1 for x in resistance)


def test_forward_record_is_immutable_and_evaluation_append_only(tmp_path):
    schedule = [
        {
            "session": "2026-11-06",
            "open": "2026-11-06T01:30:00+00:00",
            "close": "2026-11-06T08:00:00+00:00",
        },
        {
            "session": "2026-11-09",
            "open": "2026-11-09T01:30:00+00:00",
            "close": "2026-11-09T08:00:00+00:00",
        },
    ]
    forecasts = [
        {
            "ticker": "0700.HK",
            "feature_session": "2026-11-06",
            "target_session": "2026-11-09",
            "current_price": 420,
            "predicted_price": 421,
            "lower_price": 400,
            "upper_price": 440,
            "model_name": "ridge_price_only",
            "model_trained_through": "2026-11-06",
            "interval_note": "empirical band",
        }
    ]
    now = datetime(2026, 11, 7, tzinfo=UTC)
    with pytest.raises(ValueError, match="Synthetic"):
        write_forecast(tmp_path, "HKEX", forecasts, schedule, "synthetic_fixture", now, False)
    path = write_forecast(tmp_path, "HKEX", forecasts, schedule, "price_only", now, False)
    original = path.read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        write_forecast(tmp_path, "HKEX", forecasts, schedule, "price_only", now, False)
    actual = pd.DataFrame(
        [{"ticker": "0700.HK", "session": "2026-11-09", "close": 422, "provenance": "live"}]
    )
    results = tmp_path / "results.csv"
    with pytest.raises(ValueError, match="has not closed"):
        evaluate_forecast(path, actual, schedule, results, now)
    after = datetime(2026, 11, 9, 9, tzinfo=UTC)
    assert evaluate_forecast(path, actual, schedule, results, after) == 1
    content = results.read_bytes()
    assert evaluate_forecast(path, actual, schedule, results, after) == 0
    assert path.read_bytes() == original and results.read_bytes() == content
    with results.open() as stream:
        row = list(csv.DictReader(stream))[0]
    assert float(row["absolute_error"]) == 1


def test_incomplete_paid_run_is_not_launched_again(tmp_path, monkeypatch):
    from unittest.mock import Mock

    from crowd_signal.agents.collector import ApifyCollector
    from crowd_signal.config import Settings
    from crowd_signal.storage import write_json

    exchange = (
        load_config()
        .exchange("HKEX")
        .model_copy(update={"telegram_channels": ["reviewed-public-channel"]})
    )
    first = exchange.tickers[0].ticker
    cached = tmp_path / "data/raw/2026-11-06/lihkg" / first / "search-0"
    write_json(cached / "manifest.json", {"status": "SUCCEEDED", "run_id": "already-paid"})
    launch = Mock()
    monkeypatch.setattr("crowd_signal.agents.collector.probe", launch)
    with pytest.raises(ValueError, match="Prior paid run"):
        ApifyCollector(Settings(_env_file=None, apify_token="fake")).collect(
            exchange, tmp_path, datetime(2026, 11, 6, 12, tzinfo=UTC)
        )
    launch.assert_not_called()
