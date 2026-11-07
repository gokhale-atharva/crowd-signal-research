"""Immutable pre-open forecasts and append-only, idempotent post-close results."""

import csv
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from crowd_signal.models import Prediction
from crowd_signal.storage import read_json


def write_forecast(
    root: Path,
    exchange: str,
    forecasts: list[dict],
    schedule: list[dict],
    mode: str,
    now: datetime | None = None,
    commit: bool = True,
) -> Path:
    if mode == "synthetic_fixture":
        raise ValueError("Synthetic data cannot be issued as a genuine live forecast")
    now = now or datetime.now(UTC)
    if len({row["target_session"] for row in forecasts}) != 1:
        raise ValueError("Forecasts must agree on the target session")
    sessions = {row["session"]: row for row in schedule}
    completed = [row["session"] for row in schedule if datetime.fromisoformat(row["close"]) <= now]
    if not completed or any(row["feature_session"] != max(completed) for row in forecasts):
        raise ValueError(
            "Forecast features are stale; refresh market data through the latest completed session"
        )
    predictions = []
    for row in forecasts:
        target = sessions.get(row["target_session"])
        if not target:
            raise ValueError("Target session missing from the exchange calendar")
        predictions.append(
            Prediction(
                exchange=exchange,
                ticker=row["ticker"],
                issued_at=now,
                features_available_at=datetime.fromisoformat(
                    sessions[row["feature_session"]]["close"]
                ),
                target_open=datetime.fromisoformat(target["open"]),
                target_session=row["target_session"],
                current_price=row["current_price"],
                predicted_price=row["predicted_price"],
                lower_price=row["lower_price"],
                upper_price=row["upper_price"],
                model_name=row["model_name"],
                model_trained_through=row["model_trained_through"],
                mode="live",
                confidence_note=f"{mode} dataset. {row['interval_note']}. Sentiment unavailable when source history is absent.",
            )
        )
    path = root / "predictions" / f"{exchange}_{predictions[0].target_session}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    source_commit = None
    if commit:
        try:
            source_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip()
            dirty = subprocess.run(
                ["git", "status", "--porcelain", "--", "src", "pyproject.toml"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            if dirty:
                raise ValueError("Commit model source changes before issuing an audited forecast")
        except subprocess.CalledProcessError:
            raise ValueError(
                "A committed source repository is required for forecast issuance"
            ) from None
    dataset = root / "data/processed" / exchange / mode
    hashes = {
        name: hashlib.sha256((dataset / name).read_bytes()).hexdigest()
        for name in (
            "bars.parquet",
            "features.parquet",
            "forecasts.json",
            "run.json",
            "sessions.json",
        )
        if (dataset / name).exists()
    }
    payload = {
        "schema_version": 1,
        "evidence_mode": mode,
        "issued_at": now.isoformat(),
        "exchange": exchange,
        "source_commit": source_commit,
        "dataset_sha256": hashes,
        "predictions": [prediction.model_dump(mode="json") for prediction in predictions],
    }
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        raise ValueError(
            f"Immutable prediction already exists: {path}; it will not be overwritten"
        ) from None
    if commit:
        if datetime.now(UTC) >= min(prediction.target_open for prediction in predictions):
            raise ValueError(
                f"Forecast saved at {path}, but market open passed before commit; do not claim a pre-open git record"
            )
        relative = str(path.relative_to(root))
        try:
            subprocess.run(
                ["git", "add", "--", relative], cwd=root, check=True, capture_output=True
            )
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    f"Record {exchange} pre-open forecast for {predictions[0].target_session}",
                    "--",
                    relative,
                ],
                cwd=root,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            raise ValueError(
                f"Immutable forecast saved at {path}; git commit failed. Commit it before open to establish the audit trail."
            ) from None
    return path


def evaluate_forecast(
    path: Path,
    actual_bars: pd.DataFrame,
    schedule: list[dict],
    results: Path,
    now: datetime | None = None,
) -> int:
    now = now or datetime.now(UTC)
    content = path.read_bytes()
    prediction_hash = hashlib.sha256(content).hexdigest()
    payload = read_json(path)
    if payload.get("evidence_mode") == "synthetic_fixture":
        raise ValueError("Cannot evaluate a synthetic fixture as a live test")
    closes = {row["session"]: datetime.fromisoformat(row["close"]) for row in schedule}
    rows = []
    for raw in payload["predictions"]:
        prediction = Prediction.model_validate(raw)
        session = prediction.target_session.isoformat()
        if session not in closes or now < closes[session]:
            raise ValueError(f"Target session {session} has not closed; evaluation must wait")
        actual = actual_bars[
            (actual_bars.ticker == prediction.ticker) & (actual_bars.session == session)
        ]
        if len(actual) != 1 or actual.provenance.iloc[0] != "live":
            raise ValueError(f"No genuine observed close for {prediction.ticker} / {session}")
        price = float(actual.close.iloc[0])
        rows.append(
            {
                "exchange": prediction.exchange,
                "ticker": prediction.ticker,
                "target_session": session,
                "issued_at": prediction.issued_at.isoformat(),
                "evaluated_at": now.isoformat(),
                "predicted_price": prediction.predicted_price,
                "actual_close": price,
                "random_walk_price": prediction.current_price,
                "absolute_error": abs(prediction.predicted_price - price),
                "random_walk_absolute_error": abs(prediction.current_price - price),
                "prediction_sha256": prediction_hash,
            }
        )
    results.parent.mkdir(parents=True, exist_ok=True)
    lock = results.with_suffix(".csv.lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError(
            "Another evaluation is writing results; retry after it completes"
        ) from None
    try:
        os.close(descriptor)
        existing = []
        if results.exists():
            with results.open(encoding="utf-8", newline="") as stream:
                existing = list(csv.DictReader(stream))
        keys = {(row["exchange"], row["ticker"], row["target_session"]) for row in existing}
        fresh = [
            row
            for row in rows
            if (row["exchange"], row["ticker"], row["target_session"]) not in keys
        ]
        if fresh:
            with results.open("a", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                if not existing:
                    writer.writeheader()
                writer.writerows(fresh)
                stream.flush()
                os.fsync(stream.fileno())
        if path.read_bytes() != content:
            raise ValueError("Prediction file changed during evaluation")
        return len(fresh)
    finally:
        lock.unlink(missing_ok=True)
