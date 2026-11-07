from crowd_signal.agents.base import pending
from crowd_signal.config import ExchangeConfig


class MarketData:
    def collect(self, exchange: ExchangeConfig) -> None:
        pending("OHLCV collection and exchange calendar", 2)
