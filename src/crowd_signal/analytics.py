"""Signal aggregation and strictly point-in-time session features."""

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from crowd_signal.agents.levels import find_levels
from crowd_signal.agents.sentiment import engagement_weight
from crowd_signal.config import ExchangeConfig
from crowd_signal.models import Direction, Extraction, NewsItem, Position, Post, TickerSignal

PRICE_FEATURES = ["return_1", "return_2", "return_5", "volatility_10", "rsi_14", "volume_z"]
SOCIAL_FEATURES = [
    "social_sentiment",
    "mention_volume",
    "bull_bear",
    "sentiment_momentum",
    "social_available",
]
NEWS_FEATURES = ["news_sentiment", "news_volume", "news_available"]


def available_at(record: Post | NewsItem) -> datetime:
    observed = record.retrieved_at if isinstance(record, NewsItem) else record.observed_at
    # Unknown retrieval/engagement snapshots are not usable for historical model features.
    return max(record.timestamp, observed) if observed else datetime.max.replace(tzinfo=UTC)


def summarize(records: list[tuple[Post, Extraction]], as_of: datetime, half_life: float) -> dict:
    usable = [
        (post, score)
        for post, score in records
        if not score.is_spam
        and post.timestamp <= as_of
        and (post.observed_at is None or post.observed_at <= as_of)
    ]
    if not usable:
        return {
            "mentions": 0,
            "sentiment": 0.0,
            "bull_bear_ratio": None,
            "disagreement": None,
            "momentum": None,
            "long_authors": 0,
            "short_authors": 0,
            "position": Position.NONE,
            "explicit_authors": 0,
            "unknown_positions": 0,
            "source_counts": {},
        }
    weights = np.array([engagement_weight(post, as_of, half_life) for post, _ in usable])
    values = np.array([score.sentiment for _, score in usable])
    mean = float(np.average(values, weights=weights))
    bullish = sum(score.direction == Direction.BULLISH for _, score in usable)
    bearish = sum(score.direction == Direction.BEARISH for _, score in usable)
    recent = [
        score.sentiment for post, score in usable if post.timestamp > as_of - timedelta(days=2)
    ]
    prior = [
        score.sentiment for post, score in usable if post.timestamp <= as_of - timedelta(days=2)
    ]
    authors = {}
    unknown = 0
    for post, score in sorted(usable, key=lambda pair: pair[0].timestamp):
        if score.stated_position != Position.NONE:
            if post.author_hash:
                authors[post.author_hash] = score.stated_position
            else:
                unknown += 1
    long_count = sum(position == Position.LONG for position in authors.values())
    short_count = sum(position == Position.SHORT for position in authors.values())
    sources = {}
    for post, _ in usable:
        sources[post.source] = sources.get(post.source, 0) + 1
    return {
        "mentions": len(usable),
        "sentiment": mean,
        "bull_bear_ratio": bullish / bearish if bearish else None,
        "disagreement": min(1.0, float(np.sqrt(np.average((values - mean) ** 2, weights=weights)))),
        "momentum": float(np.mean(recent) - np.mean(prior)) if recent and prior else None,
        "long_authors": long_count,
        "short_authors": short_count,
        "explicit_authors": len(authors),
        "position": Position.LONG
        if long_count > short_count
        else Position.SHORT
        if short_count > long_count
        else Position.NONE,
        "unknown_positions": unknown,
        "source_counts": sources,
    }


def ticker_signals(
    exchange: ExchangeConfig,
    bars: pd.DataFrame,
    posts: list[Post],
    news: list[NewsItem],
    post_scores: list[Extraction],
    news_scores: list[Extraction],
    as_of: datetime,
    half_life: float,
) -> list[TickerSignal]:
    result = []
    for asset in exchange.tickers:
        history = bars[bars.ticker == asset.ticker].sort_values("session")
        social = [
            (post, score)
            for post, score in zip(posts, post_scores, strict=True)
            if post.ticker == asset.ticker and as_of - timedelta(days=10) <= post.timestamp <= as_of
        ]
        stats = summarize(social, as_of, half_life)
        articles = [
            (item, score)
            for item, score in zip(news, news_scores, strict=True)
            if item.ticker == asset.ticker
            and as_of - timedelta(days=10) <= item.timestamp <= as_of
            and item.retrieved_at <= as_of
            and not score.is_spam
        ]
        mentions = [
            value
            for _, score in social
            if not score.is_spam
            for value in score.price_levels_mentioned
        ]
        support, resistance = find_levels(history, mentions)
        score = stats["sentiment"]
        result.append(
            TickerSignal(
                ticker=asset.ticker,
                asset_name=asset.asset_name,
                as_of=as_of,
                current_price=float(history.close.iloc[-1]),
                mentions=stats["mentions"],
                sentiment=score,
                direction=Direction.BULLISH
                if score > 0.15
                else Direction.BEARISH
                if score < -0.15
                else Direction.NEUTRAL,
                position=stats["position"],
                long_authors=stats["long_authors"],
                short_authors=stats["short_authors"],
                support_levels=support,
                resistance_levels=resistance,
                news_sentiment=float(np.mean([score.sentiment for _, score in articles]))
                if articles
                else None,
                sentiment_momentum=stats["momentum"],
                disagreement=stats["disagreement"],
                scorer=", ".join(sorted({score.scorer for _, score in social}))
                or "no social observations",
                bull_bear_ratio=stats["bull_bear_ratio"],
                explicit_authors=stats["explicit_authors"],
                unidentified_position_posts=stats["unknown_positions"],
                source_counts=stats["source_counts"],
                latest_news=[
                    {
                        "title": item.title,
                        "url": str(item.url),
                        "published_at": item.timestamp.isoformat(),
                        "sentiment": score.sentiment,
                    }
                    for item, score in sorted(
                        articles, key=lambda pair: pair[0].timestamp, reverse=True
                    )[:3]
                ],
                evidence_mode="synthetic_fixture"
                if set(history.provenance) == {"synthetic_fixture"}
                else "live",
            )
        )
    return result


def build_features(
    bars: pd.DataFrame,
    schedule: list[dict],
    posts: list[Post],
    news: list[NewsItem],
    post_scores: list[Extraction],
    news_scores: list[Extraction],
) -> pd.DataFrame:
    """Features at close t; labels use close t+1 and are explicitly kept separate.

    No present-day engagement or retro-retrieved article is backdated to publication.
    A daily social observation needs both its publication and snapshot before close t.
    OHLCV at t is consumed after the official close; predictions are issued afterwards.
    """
    closes = {str(row["session"]): pd.Timestamp(row["close"]).to_pydatetime() for row in schedule}
    sessions = sorted(closes)
    all_rows = []
    for ticker, group in bars.groupby("ticker", sort=True):
        frame = group.sort_values("session").copy().reset_index(drop=True)
        returns = np.log(frame.close / frame.close.shift(1))
        frame["return_1"] = returns
        frame["return_2"] = returns.shift(1)
        frame["return_5"] = np.log(frame.close / frame.close.shift(5))
        frame["volatility_10"] = returns.rolling(10, min_periods=10).std()
        change = frame.close.diff()
        gain = change.clip(lower=0).rolling(14, min_periods=14).mean()
        loss = -change.clip(upper=0).rolling(14, min_periods=14).mean()
        frame["rsi_14"] = (
            (100 - 100 / (1 + gain / loss.replace(0, np.nan)))
            .where(loss != 0, 100)
            .where(gain + loss != 0, 50)
        )
        frame["volume_z"] = (frame.volume - frame.volume.rolling(20).mean()) / frame.volume.rolling(
            20
        ).std().replace(0, np.nan)
        frame["volume_z"] = frame.volume_z.fillna(0)
        frame["target_log_return"] = np.log(frame.close.shift(-1) / frame.close)
        frame["actual_price"] = frame.close.shift(-1)
        frame["target_session"] = frame.session.shift(-1)
        if str(frame.session.iloc[-1]) in sessions:
            next_index = sessions.index(str(frame.session.iloc[-1])) + 1
            if next_index < len(sessions):
                frame.loc[frame.index[-1], "target_session"] = sessions[next_index]
        social = [
            (post, score)
            for post, score in zip(posts, post_scores, strict=True)
            if post.ticker == ticker and not score.is_spam
        ]
        articles = [
            (item, score)
            for item, score in zip(news, news_scores, strict=True)
            if item.ticker == ticker and not score.is_spam
        ]
        daily = []
        for session in frame.session:
            cutoff = closes[str(session)]
            prior_cutoff = (
                closes[sessions[sessions.index(str(session)) - 1]]
                if sessions.index(str(session))
                else cutoff - timedelta(days=1)
            )
            selected = [
                (post, score)
                for post, score in social
                if prior_cutoff <= available_at(post) < cutoff and post.timestamp < cutoff
            ]
            selected_news = [
                (item, score)
                for item, score in articles
                if prior_cutoff <= available_at(item) < cutoff and item.timestamp < cutoff
            ]
            values = [score.sentiment for _, score in selected]
            weights = [engagement_weight(post, cutoff) for post, _ in selected]
            bullish = sum(value > 0.15 for value in values)
            bearish = sum(value < -0.15 for value in values)
            daily.append(
                {
                    "social_sentiment": float(np.average(values, weights=weights))
                    if values
                    else 0.0,
                    "mention_volume": math.log1p(len(values)),
                    "bull_bear": (bullish + 1) / (bearish + 1) if values else 1.0,
                    "social_available": int(bool(values)),
                    "news_sentiment": float(
                        np.mean([score.sentiment for _, score in selected_news])
                    )
                    if selected_news
                    else 0.0,
                    "news_volume": math.log1p(len(selected_news)),
                    "news_available": int(bool(selected_news)),
                    "feature_cutoff": cutoff.isoformat(),
                    "latest_social_available_at": max(
                        (available_at(post).isoformat() for post, _ in selected), default=None
                    ),
                    "latest_news_available_at": max(
                        (available_at(item).isoformat() for item, _ in selected_news), default=None
                    ),
                }
            )
        frame = pd.concat([frame, pd.DataFrame(daily)], axis=1)
        frame["sentiment_momentum"] = frame.social_sentiment.rolling(
            2, min_periods=1
        ).mean() - frame.social_sentiment.shift(2).rolling(5, min_periods=1).mean().fillna(0)
        all_rows.append(frame)
    result = (
        pd.concat(all_rows, ignore_index=True)
        .sort_values(["session", "ticker"])
        .reset_index(drop=True)
    )
    return result.dropna(subset=PRICE_FEATURES).reset_index(drop=True)
