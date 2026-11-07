"""Small, transparent stage persistence. Never deserialize untrusted model pickles."""

import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def write_json(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_frame(path: Path, rows: list[dict] | pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    frame.to_parquet(path, index=False)
    return path


def records(frame: pd.DataFrame) -> list[dict]:
    return frame.astype(object).where(pd.notna(frame), None).to_dict("records")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def event(stage: str, **fields) -> None:
    logging.getLogger("crowd_signal").info(
        json.dumps(
            {"timestamp": datetime.now(UTC).isoformat(), "stage": stage, **fields}, default=str
        )
    )
