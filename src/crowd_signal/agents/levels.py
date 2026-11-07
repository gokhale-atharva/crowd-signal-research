"""Explainable swing/pivot/round/crowd levels, using only the supplied history."""

import math

import pandas as pd

from crowd_signal.models import PriceLevel


def find_levels(
    bars: pd.DataFrame, mentioned: list[float] | None = None
) -> tuple[list[PriceLevel], list[PriceLevel]]:
    if bars.empty:
        raise ValueError("Price levels require OHLC history")
    history = bars.sort_values("session").tail(252).reset_index(drop=True)
    price = float(history.close.iloc[-1])
    candidates: list[tuple[float, str, float]] = []
    for index in range(2, len(history) - 2):
        window = history.iloc[index - 2 : index + 3]
        recency = 0.5 + 0.5 * index / max(1, len(history) - 1)
        if history.high.iloc[index] == window.high.max():
            candidates.append((float(history.high.iloc[index]), "swing", recency))
        if history.low.iloc[index] == window.low.min():
            candidates.append((float(history.low.iloc[index]), "swing", recency))
    last = history.iloc[-1]
    pivot = (float(last.high) + float(last.low) + price) / 3
    for value in (
        2 * pivot - float(last.high),
        pivot - (float(last.high) - float(last.low)),
        2 * pivot - float(last.low),
        pivot + (float(last.high) - float(last.low)),
    ):
        if value > 0:
            candidates.append((value, "pivot", 1.5))
    step = 10 ** (math.floor(math.log10(price)) - 1)
    rounded = math.floor(price / step) * step
    for offset in range(-3, 5):
        value = rounded + offset * step
        if value > 0 and value != price:
            candidates.append((value, "round", 0.6))
    candidates.extend((float(value), "crowd", 1) for value in (mentioned or []) if value > 0)
    clusters: list[list[tuple[float, str, float]]] = []
    for candidate in sorted(candidates):
        if (
            clusters
            and candidate[0]
            - sum(row[0] * row[2] for row in clusters[-1]) / sum(row[2] for row in clusters[-1])
            < price * 0.006
        ):
            clusters[-1].append(candidate)
        else:
            clusters.append([candidate])
    levels = [
        PriceLevel(
            price=round(
                sum(value * weight for value, _, weight in cluster)
                / sum(weight for _, _, weight in cluster),
                4,
            ),
            strength=min(1, sum(weight for _, _, weight in cluster) / 8),
            methods=sorted({method for _, method, _ in cluster}),
        )
        for cluster in clusters
    ]
    support = sorted(
        (level for level in levels if level.price < price),
        key=lambda level: (price - level.price, -level.strength),
    )[:2]
    resistance = sorted(
        (level for level in levels if level.price > price),
        key=lambda level: (level.price - price, -level.strength),
    )[:2]
    return support, resistance
