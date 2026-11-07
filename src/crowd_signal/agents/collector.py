"""Social collection boundary. Feasibility probes live in crowd_signal.feasibility."""

from crowd_signal.agents.base import pending
from crowd_signal.config import ExchangeConfig
from crowd_signal.models import Post


class ApifyCollector:
    def collect(self, exchange: ExchangeConfig) -> list[Post]:
        pending("Live social normalization and collection", 2)
        return []  # Unreachable until the stage is implemented.
