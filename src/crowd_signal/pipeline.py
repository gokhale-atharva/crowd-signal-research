"""One orchestration point; no implicit network during offline preview/replay."""

import json
from pathlib import Path

from crowd_signal.agents.base import pending
from crowd_signal.agents.collector import ApifyCollector
from crowd_signal.agents.market import MarketData
from crowd_signal.agents.model import NextSessionModel
from crowd_signal.agents.news import ExaNewsAgent
from crowd_signal.agents.report import ReportAgent
from crowd_signal.config import ProjectConfig, Settings
from crowd_signal.models import Post


class Pipeline:
    def __init__(self, config: ProjectConfig, settings: Settings):
        self.config, self.settings = config, settings

    def collect(self, exchange: str) -> None:
        configured = self.config.exchange(exchange)
        self.settings.require("apify_token")
        self.settings.require("exa_api_key")
        ApifyCollector().collect(configured)
        ExaNewsAgent().collect(configured)
        MarketData().collect(configured)

    def analyse(self, exchange: str) -> None:
        self.config.exchange(exchange)
        pending("Signal analysis", 3)

    def train(self, exchange: str) -> None:
        self.config.exchange(exchange)
        NextSessionModel().train(exchange)

    def predict(self, exchange: str) -> None:
        self.config.exchange(exchange)
        NextSessionModel().predict(exchange)

    def evaluate(self, exchange: str) -> None:
        self.config.exchange(exchange)
        NextSessionModel().evaluate(exchange)

    def report(self, output: Path) -> Path:
        return ReportAgent().preview(self.config, output)

    def replay(self, sample: Path, output: Path) -> tuple[int, Path]:
        payload = json.loads(sample.read_text(encoding="utf-8"))
        if payload.get("provenance") != "synthetic_fixture":
            raise ValueError("Milestone 1 replay expects an explicitly marked synthetic fixture")
        posts = [Post.model_validate(item) for item in payload["posts"]]
        if any(post.provenance != "synthetic_fixture" for post in posts):
            raise ValueError("Every fixture record must be marked synthetic_fixture")
        configured = {asset.ticker for ex in self.config.exchanges.values() for asset in ex.tickers}
        if any(post.ticker not in configured for post in posts):
            raise ValueError("Fixture contains a ticker outside the configured universe")
        return len(posts), self.report(output)
