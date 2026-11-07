from crowd_signal.agents.base import pending
from crowd_signal.models import Prediction


class NextSessionModel:
    def train(self, exchange: str) -> None:
        pending("Expanding-window models and ablation", 4)

    def predict(self, exchange: str) -> list[Prediction]:
        pending("Timestamped live forward predictions", 7)
        return []

    def evaluate(self, exchange: str) -> None:
        pending("Live prediction evaluation", 7)
