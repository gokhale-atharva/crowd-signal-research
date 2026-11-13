"""Daily market bars and real exchange sessions, with explicit as-of boundaries."""

import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

from crowd_signal.config import ExchangeConfig
from crowd_signal.storage import event, read_json, write_frame, write_json


def exchange_schedule(exchange: ExchangeConfig, start: date, end: date) -> pd.DataFrame:
    import exchange_calendars as xcals

    calendar = xcals.get_calendar(exchange.calendar, start=start.isoformat(), end=end.isoformat())
    schedule = calendar.schedule.loc[start.isoformat() : end.isoformat()].copy()
    schedule = schedule.rename(columns={"open": "market_open", "close": "market_close"})
    return schedule


class MarketData:
    def collect(
        self, exchange: ExchangeConfig, root: Path, as_of: datetime | None = None
    ) -> pd.DataFrame:
        import yfinance as yf

        cache = root / "data/cache/yfinance"
        cache.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache))
        as_of = as_of or datetime.now(UTC)
        start = (as_of - timedelta(days=430)).date()
        schedule = exchange_schedule(exchange, start, (as_of + timedelta(days=20)).date())
        closed = schedule[pd.to_datetime(schedule["market_close"], utc=True) <= as_of]
        if closed.empty:
            raise ValueError("No completed session available in the market calendar")
        last_closed = closed.index[-1].date()
        frames = []
        for asset in exchange.tickers:
            path = root / "data/raw" / as_of.date().isoformat() / "market" / f"{asset.ticker}.json"
            if path.exists():
                rows = read_json(path)["bars"]
            else:
                error_type = "unknown"
                for attempt in range(3):
                    try:
                        history = yf.Ticker(asset.ticker).history(
                            start=start.isoformat(),
                            end=(last_closed + timedelta(days=1)).isoformat(),
                            auto_adjust=False,
                            actions=False,
                            raise_errors=True,
                        )
                        if history.empty:
                            raise ValueError("Empty market response")
                        rows = [
                            {
                                "ticker": asset.ticker,
                                "session": index.date().isoformat(),
                                "open": float(row.Open),
                                "high": float(row.High),
                                "low": float(row.Low),
                                "close": float(row.Close),
                                "volume": float(row.Volume),
                                "provenance": "live",
                            }
                            for index, row in history.iterrows()
                            if index.date() <= last_closed
                        ]
                        write_json(
                            path,
                            {
                                "provider": "yfinance",
                                "retrieved_at": as_of.isoformat(),
                                "adjustment": "unadjusted; corporate-action jumps must be audited",
                                "bars": rows,
                            },
                        )
                        break
                    except Exception as exc:
                        error_type = type(exc).__name__
                        if attempt < 2:
                            time.sleep(2**attempt)
                else:
                    raise ValueError(
                        f"Market download failed for {asset.ticker} ({error_type}); no sample fallback is allowed"
                    )
            frame = pd.DataFrame(rows)
            if frame.empty or frame.session.iloc[-1] != last_closed.isoformat():
                raise ValueError(f"Stale market bars for {asset.ticker}: expected {last_closed}")
            frame = normalize_price_envelope(frame)
            frames.append(frame)
        bars = pd.concat(frames, ignore_index=True)
        validate_bars(bars)
        write_frame(root / "data/processed" / exchange.calendar / "bars.parquet", bars)
        event("market", assets=len(frames), rows=len(bars), last_session=last_closed)
        return bars


def validate_bars(bars: pd.DataFrame) -> None:
    required = {"ticker", "session", "open", "high", "low", "close", "volume", "provenance"}
    if not required.issubset(bars):
        raise ValueError(f"Missing OHLCV columns: {sorted(required - set(bars))}")
    if bars.duplicated(["ticker", "session"]).any():
        raise ValueError("Duplicate ticker/session price bars")
    values = bars[["open", "high", "low", "close", "volume"]]
    if (
        values.isna().any().any()
        or (bars[["open", "high", "low", "close"]] <= 0).any().any()
        or (bars.volume < 0).any()
    ):
        raise ValueError("OHLCV contains missing, negative or non-positive prices")
    if (bars.high < bars[["open", "close", "low"]].max(axis=1)).any() or (
        bars.low > bars[["open", "close", "high"]].min(axis=1)
    ).any():
        raise ValueError("Invalid OHLC range")


def normalize_price_envelope(frame: pd.DataFrame) -> pd.DataFrame:
    """Retain provider values and flag a minimal range containing its open/close.

    Some vendor bars report opens outside their high/low range.
    Close and volume, the model inputs, are never changed. The derived envelope
    is explicitly distinguished from the preserved provider high/low.
    """
    result = frame.copy()
    values = result[["open", "high", "low", "close"]]
    if values.isna().any().any() or (values <= 0).any().any():
        return result  # Validation must reject invalid observed prices.
    result["provider_high"], result["provider_low"] = result.high, result.low
    result["high"] = values.max(axis=1)
    result["low"] = values.min(axis=1)
    result["ohlc_envelope_repaired"] = (result.high != result.provider_high) | (result.low != result.provider_low)
    return result
