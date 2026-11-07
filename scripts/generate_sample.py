"""Generate deterministic simulated observations. These are NEVER real market evidence."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from crowd_signal.agents.market import exchange_schedule
from crowd_signal.config import load_config
from crowd_signal.storage import write_json


def generate(destination: Path = Path("data/sample")) -> None:
    random = np.random.default_rng(4217)
    destination.mkdir(parents=True, exist_ok=True)
    bars, posts, news, calendars = [], [], [], {}
    config = load_config()
    for exchange_name, exchange in config.exchanges.items():
        schedule = exchange_schedule(exchange, date(2025, 7, 1), date(2026, 11, 20))
        observed = schedule.loc[:"2026-11-06"].tail(280)
        calendars[exchange_name] = [
            {
                "session": index.date().isoformat(),
                "open": row.market_open.isoformat(),
                "close": row.market_close.isoformat(),
            }
            for index, row in schedule.iterrows()
            if index.date() >= observed.index[0].date()
        ]
        common = random.normal(0, 0.007, len(observed))
        for index, asset in enumerate(exchange.tickers):
            price = (
                [320.0, 95.0, 105.0, 28.0, 62.0][index]
                if exchange.currency == "HKD"
                else [61000.0, 150000.0, 180000.0, 39000.0, 310000.0][index]
            )
            for day_index, (session, row) in enumerate(observed.iterrows()):
                open_price = price * np.exp(random.normal(0, 0.003))
                close = open_price * np.exp(common[day_index] + random.normal(0.00015, 0.013))
                high = max(open_price, close) * (1 + random.uniform(0.001, 0.02))
                low = min(open_price, close) * (1 - random.uniform(0.001, 0.02))
                bars.append(
                    {
                        "ticker": asset.ticker,
                        "session": session.date().isoformat(),
                        "open": round(open_price, 4),
                        "high": round(high, 4),
                        "low": round(low, 4),
                        "close": round(close, 4),
                        "volume": int(random.lognormal(15.2, 0.45)),
                        "provenance": "synthetic_fixture",
                    }
                )
                price = close
                close_at = row.market_close.to_pydatetime()
                if session.date() >= date(2026, 10, 28):
                    for count in range(int(random.integers(2, 7))):
                        positive = bool(random.random() < [0.7, 0.4, 0.25, 0.65, 0.5][index])
                        language = (count + index) % 3
                        support, resistance = round(close * 0.96, 1), round(close * 1.04, 1)
                        if language == 0:
                            text = f"{asset.asset_name}: {'strong growth, bullish outlook. I am long.' if positive else 'weak outlook, downside risk. I am short.'} Support {support}; resistance {resistance}. Scenario {session.date()}-{count}."
                        elif exchange_name == "HKEX":
                            text = f"{asset.aliases[-1]}：{'看好，利好增長。我持有。' if positive else '看淡，下跌風險。我做空。'} 支撐 {support}，阻力 {resistance}。討論 {session.date()}-{count}。"
                        else:
                            text = f"{asset.aliases[-1]} {'성장 호재 상승. 저는 보유.' if positive else '하락 악재 위험. 저는 공매도.'} 지지 {support} 저항 {resistance}. 토론 {session.date()}-{count}."
                        stamp = close_at - timedelta(minutes=35 + count * 27)
                        posts.append(
                            {
                                "ticker": asset.ticker,
                                "timestamp": stamp.isoformat(),
                                "observed_at": (stamp + timedelta(minutes=1)).isoformat(),
                                "text": text,
                                "source": exchange.proposed_sources[count % 2],
                                "url": f"https://example.invalid/simulated/{asset.ticker}/{session.date()}/{count}",
                                "likes": int(random.integers(0, 90)) if count % 4 else None,
                                "reposts": int(random.integers(0, 8)),
                                "views": int(random.integers(80, 5000)),
                                "author_followers": int(random.integers(0, 1000))
                                if count % 3
                                else None,
                                "author_hash": hashlib.sha256(
                                    f"synthetic:{asset.ticker}:author-{count}".encode()
                                ).hexdigest(),
                                "language": "en"
                                if language == 0
                                else "zh"
                                if exchange_name == "HKEX"
                                else "ko",
                                "provenance": "synthetic_fixture",
                            }
                        )
                if session.date() >= date(2026, 8, 10) and day_index % 2 == 0:
                    stamp = close_at - timedelta(hours=3)
                    positive = bool(random.random() > 0.45)
                    news.append(
                        {
                            "ticker": asset.ticker,
                            "timestamp": stamp.isoformat(),
                            "retrieved_at": (stamp + timedelta(minutes=2)).isoformat(),
                            "title": f"Simulated {asset.asset_name} research bulletin · {session.date()}",
                            "text": f"Simulated article for pipeline testing: {asset.asset_name} {'reports strong profit growth, beating expectations' if positive else 'faces weak demand and downside risks'}. This is not a real news story.",
                            "url": f"https://example.invalid/simulated-news/{asset.ticker}/{session.date()}",
                            "language": "en",
                            "provenance": "synthetic_fixture",
                        }
                    )
    pd.DataFrame(bars).to_csv(destination / "bars.csv", index=False)
    for name, records in (("social.jsonl", posts), ("news.jsonl", news)):
        (destination / name).write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8"
        )
    write_json(destination / "sessions.json", calendars)
    write_json(
        destination / "bundle.json",
        {
            "schema_version": 2,
            "provenance": "synthetic_fixture",
            "as_of": datetime(2026, 11, 6, 8, 5, tzinfo=UTC).isoformat(),
            "description": "Deterministic simulated prices, posts and news. For software demonstration only; no claim about real trading performance.",
            "files": {
                "bars": "bars.csv",
                "posts": "social.jsonl",
                "news": "news.jsonl",
                "sessions": "sessions.json",
            },
            "exchanges": list(config.exchanges),
            "seed": 4217,
        },
    )
    print(f"Generated {len(bars)} simulated bars, {len(posts)} posts and {len(news)} news items")


if __name__ == "__main__":
    generate()
