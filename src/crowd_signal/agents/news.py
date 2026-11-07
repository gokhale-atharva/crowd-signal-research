from crowd_signal.agents.base import pending
from crowd_signal.config import ExchangeConfig
from crowd_signal.models import NewsItem


class ExaNewsAgent:
    def collect(self, exchange: ExchangeConfig) -> list[NewsItem]:
        pending("Exa news collection", 2)
        return []
