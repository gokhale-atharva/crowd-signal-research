from crowd_signal.agents.base import pending
from crowd_signal.models import Extraction, NewsItem, Post


class SentimentAgent:
    def score(self, records: list[Post | NewsItem]) -> list[Extraction]:
        pending("Structured sentiment extraction and aggregation", 3)
        return []
