from crowd_signal.agents.base import pending
from crowd_signal.models import PriceLevel


def find_levels(ticker: str) -> tuple[list[PriceLevel], list[PriceLevel]]:
    pending("Swing, pivot, round-number and crowd price levels", 3)
    return [], []
