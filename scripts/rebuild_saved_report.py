"""Rebuild the public site from its committed, provenance-labelled snapshot."""

import json
from pathlib import Path

from crowd_signal.agents.report import ReportAgent
from crowd_signal.config import load_config


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    report_dir = root / "reports"
    data_file = report_dir / "assets" / "data.js"
    data_text = data_file.read_text(encoding="utf-8")
    prefix = "window.CROWD_DATA="
    if not data_text.startswith(prefix):
        raise ValueError("The committed report data has an unexpected format")
    datasets = json.loads(data_text[len(prefix):].rstrip(";\r\n "))
    if not all("live" in datasets.get(name, {}) for name in ("HKEX", "KRX")):
        raise ValueError("Both exchanges need a verified saved capture")
    ReportAgent().render(load_config(), report_dir, datasets)
    print(f"Rebuilt {report_dir / 'index.html'} from committed captured data")


if __name__ == "__main__":
    main()
