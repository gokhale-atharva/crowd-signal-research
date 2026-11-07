import json
import socket
from pathlib import Path

import pytest
from typer.testing import CliRunner

from crowd_signal.cli import app
from crowd_signal.config import load_config
from crowd_signal.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]


def test_replay_does_not_access_network_and_never_renders_fixture_as_live(
    tmp_path, monkeypatch, settings
):
    def deny(*args, **kwargs):
        raise AssertionError("Replay attempted network access")

    monkeypatch.setattr(socket.socket, "connect", deny)
    count, report = Pipeline(load_config(), settings).replay(
        ROOT / "data/sample/posts.json", tmp_path
    )
    assert count == 4
    html = report.read_text(encoding="utf-8")
    assert "No live posts, prices, sentiment scores or forecasts" in html
    assert "SYNTHETIC FIXTURE:" not in html
    assert "prefers-reduced-motion" in html
    assert "<script src=" not in html and "@import" not in html
    assert (tmp_path / "hkex.html").is_file() and (tmp_path / "krx.html").is_file()


def test_replay_rejects_unmarked_fixture(tmp_path, settings):
    sample = tmp_path / "bad.json"
    sample.write_text(json.dumps({"posts": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="synthetic fixture"):
        Pipeline(load_config(), settings).replay(sample, tmp_path / "report")


def test_cli_commands_and_pending_stages_exit_honestly(tmp_path, monkeypatch):
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for name in (
        "collect",
        "analyse",
        "train",
        "predict",
        "evaluate",
        "report",
        "run-all",
        "replay",
    ):
        assert name in result.stdout
    result = runner.invoke(app, ["collect"])
    assert result.exit_code == 2 and "Missing APIFY_TOKEN" in result.stdout
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["train"])
    assert result.exit_code == 2 and "No dataset" in result.stdout
    assert runner.invoke(app, ["doctor"]).exit_code == 0


def test_full_bundle_runs_offline(tmp_path, monkeypatch, settings):
    import crowd_signal.pipeline as module
    from crowd_signal.agents.model import NextSessionModel
    from crowd_signal.storage import read_json

    def deny(*args, **kwargs):
        raise AssertionError("Full replay attempted network access")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(
        module,
        "NextSessionModel",
        lambda *args, **kw: NextSessionModel(bootstrap_samples=100, test_sessions=3),
    )
    count, report = Pipeline(load_config(), settings, root=tmp_path).replay(
        ROOT / "data/sample/bundle.json", tmp_path / "reports"
    )
    assert count == 336 and report.exists()
    for exchange in ("HKEX", "KRX"):
        directory = tmp_path / "data/processed" / exchange / "synthetic_fixture"
        run = read_json(directory / "run.json")
        assert all(run["stages"].values())
        forecasts = read_json(directory / "forecasts.json")
        assert len(forecasts) == 5
        metrics = read_json(directory / "metrics.json")
        assert metrics["random_walk"]["n_sessions"] == 3
    html = report.read_text(encoding="utf-8")
    assert "SIMULATED LAB" in html and "synthetic_fixture" in html
    assert "Conversation ranking" in html and "candlestick" in html
    assert not (tmp_path / "predictions").exists()
