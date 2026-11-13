"""One orchestrator for live, price-only and fully offline reproducible runs."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from crowd_signal.agents.collector import ApifyCollector
from crowd_signal.agents.market import MarketData, exchange_schedule, validate_bars
from crowd_signal.agents.model import NextSessionModel
from crowd_signal.agents.news import ExaNewsAgent
from crowd_signal.agents.report import ReportAgent
from crowd_signal.agents.sentiment import SentimentAgent
from crowd_signal.analytics import build_features, discussion_timeline, ticker_signals
from crowd_signal.captures import import_verified_probes
from crowd_signal.config import ProjectConfig, Settings
from crowd_signal.forward import evaluate_forecast, write_forecast
from crowd_signal.history import retain_first_observations
from crowd_signal.models import Extraction, NewsItem, Post
from crowd_signal.processing import clean_posts
from crowd_signal.replay_bundle import export_bundle
from crowd_signal.storage import event, read_json, records, write_frame, write_json

MODES = ("live", "price_only", "synthetic_fixture")


class Pipeline:
    def __init__(self, config: ProjectConfig, settings: Settings, root: Path | None = None):
        self.config, self.settings, self.root = config, settings, (root or Path.cwd()).resolve()

    def directory(self, exchange: str, mode: str | None = None) -> Path:
        self.config.exchange(exchange)
        base = self.root / "data/processed" / exchange.upper()
        if mode:
            if mode not in MODES:
                raise ValueError(f"Unknown dataset mode: {mode}")
            return base / mode
        for candidate in MODES:
            if (base / candidate / "run.json").exists():
                return base / candidate
        raise ValueError(f"No dataset for {exchange}. Run replay, market, or collect first.")

    def save_dataset(
        self,
        exchange: str,
        mode: str,
        bars: pd.DataFrame,
        posts: list[Post],
        news: list[NewsItem],
        schedule: list[dict],
        as_of: datetime,
        coverage: list[dict],
        capture: bool = True,
    ) -> Path:
        configured = self.config.exchange(exchange)
        validate_bars(bars)
        expected_provenance = "synthetic_fixture" if mode == "synthetic_fixture" else "live"
        if set(bars.provenance) != {expected_provenance} or any(
            item.provenance != expected_provenance for item in posts + news
        ):
            raise ValueError("Dataset evidence mode and record provenance disagree")
        if set(bars.ticker) != {asset.ticker for asset in configured.tickers}:
            raise ValueError("Dataset must contain exactly the configured five assets")
        destination = self.directory(exchange, mode)
        write_json(destination / "run.json", {
            "exchange": exchange.upper(), "mode": mode, "as_of": as_of.isoformat(),
            "coverage": coverage, "stages": {"collection": False, "analysis": False, "training": False},
            "bar_count": len(bars), "post_count": len(posts), "news_count": len(news),
        })
        write_frame(destination / "bars.parquet", bars)
        write_frame(destination / "posts.parquet", [post.model_dump(mode="json") for post in posts])
        write_frame(destination / "news.parquet", [item.model_dump(mode="json") for item in news])
        write_json(destination / "sessions.json", schedule)
        write_json(
            destination / "run.json",
            {
                "exchange": exchange.upper(),
                "mode": mode,
                "as_of": as_of.isoformat(),
                "coverage": coverage,
                "stages": {"collection": True, "analysis": False, "training": False},
                "bar_count": len(bars),
                "post_count": len(posts),
                "news_count": len(news),
                "ohlc_envelope_repairs": int(bars["ohlc_envelope_repaired"].sum()) if "ohlc_envelope_repaired" in bars else 0,
                "ohlc_range_note": "Flagged ranges use a minimal envelope containing provider open/high/low/close. Original high/low retained; closes and volumes unchanged.",
            },
        )
        if capture and mode != "synthetic_fixture":
            bundle = export_bundle(
                self.root / "data/raw" / as_of.date().isoformat() / "replay" / f"{exchange}_{mode}",
                exchange,
                mode,
                bars,
                posts,
                news,
                schedule,
                as_of.isoformat(),
                coverage,
            )
            event("replay_bundle", exchange=exchange, mode=mode, manifest=str(bundle))
        return destination

    def market(self, exchange: str) -> Path:
        configured = self.config.exchange(exchange)
        as_of = datetime.now(UTC)
        bars = MarketData().collect(configured, self.root, as_of)
        schedule = exchange_schedule(
            configured, pd.Timestamp(bars.session.min()).date(), (as_of + timedelta(days=20)).date()
        )
        calendar = [
            {
                "session": index.date().isoformat(),
                "open": row.market_open.isoformat(),
                "close": row.market_close.isoformat(),
            }
            for index, row in schedule.iterrows()
        ]
        return self.save_dataset(
            exchange,
            "price_only",
            bars,
            [],
            [],
            calendar,
            datetime.now(UTC),
            [
                {"source": source, "status": "not_collected", "usable_posts": 0}
                for source in configured.proposed_sources
            ],
        )

    def collect(self, exchange: str) -> Path:
        configured = self.config.exchange(exchange)
        self.settings.require("apify_token")
        self.settings.require("exa_api_key")
        collector = ApifyCollector(self.settings)
        collector.validate_sources(configured)
        as_of = datetime.now(UTC)
        posts, coverage = collector.collect(configured, self.root, as_of)
        news = ExaNewsAgent(self.settings).collect(configured, self.root, as_of)
        bars = MarketData().collect(configured, self.root, as_of)
        schedule = exchange_schedule(
            configured, pd.Timestamp(bars.session.min()).date(), (as_of + timedelta(days=20)).date()
        )
        calendar = [
            {
                "session": index.date().isoformat(),
                "open": row.market_open.isoformat(),
                "close": row.market_close.isoformat(),
            }
            for index, row in schedule.iterrows()
        ]
        captured_at = datetime.now(UTC)
        previous = self.directory(exchange, "live")
        if (previous / "run.json").exists():
            old_posts = [Post.model_validate(row) for row in records(pd.read_parquet(previous / "posts.parquet"))]
            old_news = [NewsItem.model_validate(row) for row in records(pd.read_parquet(previous / "news.parquet"))]
            posts = retain_first_observations(old_posts, posts, captured_at)
            news = retain_first_observations(old_news, news, captured_at)
        return self.save_dataset(
            exchange, "live", bars, posts, news, calendar, captured_at, coverage
        )

    def import_probes(self, exchange: str, selections: Path, allow_partial: bool = False) -> Path:
        configured = self.config.exchange(exchange)
        as_of = datetime.now(UTC)
        posts, coverage = import_verified_probes(configured, self.root, read_json(selections), as_of, allow_partial)
        news = ExaNewsAgent(self.settings).collect(configured, self.root, as_of)
        bars = MarketData().collect(configured, self.root, as_of)
        schedule = exchange_schedule(configured, pd.Timestamp(bars.session.min()).date(),
                                     (as_of + timedelta(days=20)).date())
        calendar = [{"session": index.date().isoformat(), "open": row.market_open.isoformat(),
                     "close": row.market_close.isoformat()} for index, row in schedule.iterrows()]
        captured_at = datetime.now(UTC)
        previous = self.directory(exchange, "live")
        if (previous / "run.json").exists():
            old_posts = [Post.model_validate(row) for row in records(pd.read_parquet(previous / "posts.parquet"))]
            old_news = [NewsItem.model_validate(row) for row in records(pd.read_parquet(previous / "news.parquet"))]
            posts = retain_first_observations(old_posts, posts, captured_at)
            news = retain_first_observations(old_news, news, captured_at)
        universe = {asset.ticker for asset in configured.tickers}
        posts = [post for post in posts if post.ticker in universe]
        news = [item for item in news if item.ticker in universe]
        destination = self.save_dataset(exchange, "live", bars, posts, news, calendar, captured_at, coverage)
        run = read_json(destination / "run.json")
        run["source_acceptance_complete"] = all(any(row["source"] == source and row["usable_posts"] > 0 for row in coverage) for source in configured.proposed_sources)
        run["capture_method"] = "Imported inspected Apify runs; no paid relaunch"
        write_json(destination / "run.json", run)
        return destination

    def analyse(self, exchange: str, mode: str | None = None, offline: bool = False) -> Path:
        directory = self.directory(exchange, mode)
        run = read_json(directory / "run.json")
        if not run["stages"]["collection"]:
            raise ValueError("Collection is incomplete; finish collection before analysis")
        run["stages"].update(analysis=False, training=False)
        write_json(directory / "run.json", run)
        bars = pd.read_parquet(directory / "bars.parquet")
        posts = [
            Post.model_validate(row)
            for row in records(pd.read_parquet(directory / "posts.parquet"))
        ]
        news = [
            NewsItem.model_validate(row)
            for row in records(pd.read_parquet(directory / "news.parquet"))
        ]
        posts, cleaning = clean_posts(posts)
        agent = SentimentAgent(
            self.settings,
            self.root / "data/cache/sentiment",
            offline=offline or run["mode"] == "synthetic_fixture",
            aliases={a.ticker: a.aliases for a in self.config.exchange(exchange).tickers},
        )
        post_scores, news_scores = agent.score(posts), agent.score(news)
        configured = self.config.exchange(exchange)
        as_of = datetime.fromisoformat(run["as_of"])
        signals = ticker_signals(
            configured,
            bars,
            posts,
            news,
            post_scores,
            news_scores,
            as_of,
            self.settings.sentiment_half_life_days,
        )
        features = build_features(
            bars, read_json(directory / "sessions.json"), posts, news, post_scores, news_scores
        )
        write_frame(
            directory / "clean_posts.parquet", [post.model_dump(mode="json") for post in posts]
        )
        write_frame(
            directory / "social_scores.parquet",
            [score.model_dump(mode="json") for score in post_scores],
        )
        write_frame(
            directory / "news_scores.parquet",
            [score.model_dump(mode="json") for score in news_scores],
        )
        write_frame(directory / "features.parquet", features)
        write_json(
            directory / "signals.json", [signal.model_dump(mode="json") for signal in signals]
        )
        run["stages"]["analysis"] = True
        run["cleaning"] = cleaning
        run["scorers"] = sorted({score.scorer for score in post_scores + news_scores})
        write_json(directory / "run.json", run)
        event("analysis", exchange=exchange, mode=run["mode"], features=len(features), **cleaning)
        return directory

    def train(self, exchange: str, mode: str | None = None) -> Path:
        directory = self.directory(exchange, mode)
        run = read_json(directory / "run.json")
        if not run["stages"].get("analysis") or not (directory / "features.parquet").exists():
            raise ValueError("Run analyse before train")
        run["stages"]["training"] = False
        write_json(directory / "run.json", run)
        result = NextSessionModel(self.settings.bootstrap_samples).train(
            pd.read_parquet(directory / "features.parquet")
        )
        write_frame(directory / "backtest.parquet", result.predictions)
        write_json(directory / "metrics.json", result.metrics)
        write_json(directory / "forecasts.json", result.forecast)
        write_json(directory / "folds.json", result.folds)
        run = read_json(directory / "run.json")
        run["stages"]["training"] = True
        run["forecast_model"] = result.forecast[0]["model_name"]
        write_json(directory / "run.json", run)
        event(
            "training",
            exchange=exchange,
            mode=run["mode"],
            test_sessions=result.metrics["random_walk"]["n_sessions"],
            models=len(result.metrics) - 1,
        )
        return directory

    def predict(self, exchange: str, mode: str | None = None, commit: bool = True) -> Path:
        directory = self.directory(exchange, mode)
        run = read_json(directory / "run.json")
        if not all(run["stages"].values()):
            raise ValueError("Complete collection, analysis and training before issuing a forecast")
        return write_forecast(
            self.root,
            exchange.upper(),
            read_json(directory / "forecasts.json"),
            read_json(directory / "sessions.json"),
            run["mode"],
            commit=commit,
        )

    def evaluate(self, exchange: str) -> int:
        configured = self.config.exchange(exchange)
        paths = sorted((self.root / "predictions").glob(f"{exchange.upper()}_*.json"))
        if not paths:
            raise ValueError("No immutable predictions found")
        bars = MarketData().collect(configured, self.root)
        schedule = exchange_schedule(
            configured,
            pd.Timestamp(bars.session.min()).date(),
            (datetime.now(UTC) + timedelta(days=20)).date(),
        )
        calendar = [
            {
                "session": index.date().isoformat(),
                "open": row.market_open.isoformat(),
                "close": row.market_close.isoformat(),
            }
            for index, row in schedule.iterrows()
        ]
        return sum(
            evaluate_forecast(path, bars, calendar, self.root / "predictions/results.csv")
            for path in paths
        )

    def report(self, output: Path) -> Path:
        datasets = {exchange: {} for exchange in self.config.exchanges}
        for exchange in self.config.exchanges:
            for mode in MODES:
                directory = self.directory(exchange, mode)
                if (directory / "forecasts.json").exists() and all(
                    read_json(directory / "run.json")["stages"].values()
                ):
                    datasets[exchange][mode] = self.report_packet(exchange, mode)
        return ReportAgent().render(self.config, output, datasets)

    def report_packet(self, exchange: str, mode: str) -> dict:
        directory = self.directory(exchange, mode)
        run = read_json(directory / "run.json")
        if not all(run["stages"].values()):
            raise ValueError("Dataset has incomplete stages; stale results cannot be reported")
        bars = pd.read_parquet(directory / "bars.parquet")
        features = pd.read_parquet(directory / "features.parquet")
        backtest = pd.read_parquet(directory / "backtest.parquet")
        signals = read_json(directory / "signals.json")
        cleaned = [Post.model_validate(row) for row in records(pd.read_parquet(directory / "clean_posts.parquet"))]
        scores = [Extraction.model_validate(row) for row in records(pd.read_parquet(directory / "social_scores.parquet"))]
        discussion = discussion_timeline(cleaned, scores, datetime.fromisoformat(run["as_of"]),
                                         self.config.exchange(exchange).timezone)
        news_records = records(pd.read_parquet(directory / "news.parquet"))
        for signal in signals:
            signal["news_record_count"] = sum(item["ticker"] == signal["ticker"] for item in news_records)
            refs = [(post, score) for post, score in zip(cleaned, scores, strict=True)
                    if post.ticker == signal["ticker"] and not score.is_spam
                    and datetime.fromisoformat(run["as_of"]) - timedelta(days=10) <= post.timestamp
                    <= datetime.fromisoformat(run["as_of"])]
            signal["social_evidence"] = [{"source": post.source, "timestamp": post.timestamp.isoformat(),
                "url": str(post.url), "sentiment": score.sentiment, "position": score.stated_position}
                for post, score in sorted(refs, key=lambda pair: pair[0].timestamp, reverse=True)[:12]]
            if signal["mentions"] == 0:
                signal.update(sentiment=None, direction=None, position=None)
        series = {}
        for ticker, frame in bars.groupby("ticker"):
            history = frame.sort_values("session").tail(252)
            daily = features[features.ticker == ticker][
                [
                    "session",
                    "social_sentiment",
                    "mention_volume",
                    "news_sentiment",
                    "social_available",
                    "news_available",
                ]
            ]
            series[ticker] = {
                "bars": history.to_dict("records"),
                "daily": daily.to_dict("records"),
                "discussion": discussion.get(ticker, []),
                "backtest": backtest[
                    (backtest.ticker == ticker)
                    & backtest.model.isin([run["forecast_model"], "random_walk"])
                ].to_dict("records"),
            }
        forward_tests = []
        results_path = self.root / "predictions/results.csv"
        results = (
            records(pd.read_csv(results_path, dtype={"ticker": str}))
            if results_path.exists()
            else []
        )
        if mode != "synthetic_fixture":
            for path in sorted((self.root / "predictions").glob(f"{exchange}_*.json")):
                record = read_json(path)
                if record.get("evidence_mode") == "synthetic_fixture":
                    continue
                for prediction in record["predictions"]:
                    actual = next(
                        (
                            row
                            for row in results
                            if row["exchange"] == exchange
                            and row["ticker"] == prediction["ticker"]
                            and row["target_session"] == prediction["target_session"]
                        ),
                        None,
                    )
                    forward_tests.append(
                        {
                            **prediction,
                            "actual_close": actual["actual_close"] if actual else None,
                            "absolute_error": actual["absolute_error"] if actual else None,
                            "random_walk_absolute_error": actual["random_walk_absolute_error"] if actual else None,
                            "evidence_mode": record.get("evidence_mode"),
                            "source_commit": record.get("source_commit"),
                        }
                    )
        return {
            "run": run,
            "forward_tests": forward_tests,
            "signals": signals,
            "forecasts": read_json(directory / "forecasts.json"),
            "metrics": read_json(directory / "metrics.json"),
            "series": series,
            "folds": read_json(directory / "folds.json"),
        }

    def replay(self, sample: Path, output: Path) -> tuple[int, Path]:
        payload = read_json(sample)
        if payload.get("provenance") not in {"synthetic_fixture", "live"}:
            raise ValueError(
                "Replay expects an explicitly marked synthetic fixture or a captured replay bundle"
            )
        if "files" not in payload:
            # Preserve the small parser fixture as a separate smoke-test input.
            posts = [Post.model_validate(item) for item in payload["posts"]]
            if any(post.provenance != "synthetic_fixture" for post in posts):
                raise ValueError("Every fixture record must be marked synthetic_fixture")
            return len(posts), ReportAgent().preview(self.config, output)
        mode = (
            "synthetic_fixture"
            if payload["provenance"] == "synthetic_fixture"
            else payload.get("evidence_mode", "live")
        )
        if mode not in MODES:
            raise ValueError("Unknown replay evidence mode")
        paths = {
            name: (sample.parent / relative).resolve()
            for name, relative in payload["files"].items()
        }
        if any(not path.is_relative_to(sample.parent.resolve()) for path in paths.values()):
            raise ValueError("Replay bundle paths must remain inside the bundle directory")
        if payload.get("sha256"):
            import hashlib

            for relative, expected in payload["sha256"].items():
                matched = next((path for path in paths.values() if path.name == relative), None)
                if matched is None or hashlib.sha256(matched.read_bytes()).hexdigest() != expected:
                    raise ValueError(f"Replay input integrity check failed: {relative}")
        bars = pd.read_csv(paths["bars"], dtype={"ticker": str, "session": str})
        posts = [
            Post.model_validate_json(line)
            for line in paths["posts"].read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        news = [
            NewsItem.model_validate_json(line)
            for line in paths["news"].read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if set(bars.provenance) != {payload["provenance"]} or any(
            item.provenance != payload["provenance"] for item in posts + news
        ):
            raise ValueError("Every record must match the replay bundle provenance")
        calendars = read_json(paths["sessions"])
        for exchange in payload["exchanges"]:
            configured = self.config.exchange(exchange)
            tickers = {asset.ticker for asset in configured.tickers}
            self.save_dataset(
                exchange,
                mode,
                bars[bars.ticker.isin(tickers)].copy(),
                [post for post in posts if post.ticker in tickers],
                [item for item in news if item.ticker in tickers],
                calendars[exchange],
                datetime.fromisoformat(payload["as_of"]),
                payload.get("coverage")
                or [
                    {
                        "source": source,
                        "status": "simulated",
                        "usable_posts": sum(
                            post.source == source and post.ticker in tickers for post in posts
                        ),
                    }
                    for source in configured.proposed_sources
                ],
                capture=False,
            )
            self.analyse(exchange, mode, offline=True)
            self.train(exchange, mode)
        return len(posts), self.report(output)
