"""One CLI for collection, analysis, validation, reports, replay and forward tests."""

import json
import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from crowd_signal.config import Settings, load_config
from crowd_signal.feasibility import discover, probe
from crowd_signal.pipeline import MODES, Pipeline
from crowd_signal.readiness import live_setup_checks, require_live_setup

app = typer.Typer(no_args_is_help=True, help="Crowd Signal · reproducible exchange research")
console = Console()


@app.callback()
def configure_logging():
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def pipeline(config: Path | None = None) -> Pipeline:
    return Pipeline(load_config(config), Settings())


def fail(exc: Exception) -> None:
    console.print(f"Error: {exc}", style="red", markup=False)
    raise typer.Exit(2)


def perform(stage: str, exchange: str, mode: str | None = None):
    try:
        p = pipeline()
        function = getattr(p, stage)
        result = function(exchange, mode) if stage in {"analyse", "train"} else function(exchange)
        console.print(f"{stage}: {result}")
        return result
    except (ValueError, FileNotFoundError) as exc:
        fail(exc)


@app.command()
def doctor(
    config: Annotated[Path | None, typer.Option(help="Override exchange YAML")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print redacted setup checks as JSON")] = False,
    strict: Annotated[bool, typer.Option(help="Exit 2 when live setup has blockers")] = False,
):
    """Validate configuration and show credential presence without exposing values."""
    p = pipeline(config)
    checks = live_setup_checks(p.config, p.settings, list(p.config.exchanges))
    if as_json:
        console.print_json(json.dumps({"ready_for_live_collection": all(row["ready"] for row in checks),
                                       "verification": "Configuration check only; inspect captured run manifests for source acceptance", "checks": checks}))
        if strict and not all(row["ready"] for row in checks):
            raise typer.Exit(2)
        return
    table = Table(title="Crowd Signal · readiness")
    table.add_column("Check")
    table.add_column("State")
    for name, exchange in p.config.exchanges.items():
        available = [mode for mode in MODES if (p.directory(name, mode) / "run.json").exists()]
        table.add_row(
            name, f"{len(exchange.tickers)} assets · datasets: {', '.join(available) or 'none'}"
        )
    for key in ("apify_token", "exa_api_key", "llm_api_key"):
        try:
            p.settings.require(key)
            state = "configured"
        except ValueError:
            state = "missing" + (" (optional; lexicon fallback)" if key == "llm_api_key" else "")
        table.add_row(key.upper(), state)
    table.add_row(
        "Live source setup", "Configure actor_ids and reviewed Telegram channels in exchange YAML"
    )
    table.add_row(
        "Keyless workflows", "replay (simulated) / run-all --mode price_only (real public prices)"
    )
    for row in checks:
        if not row["ready"]:
            table.add_row(row["check"], row["action"])
    console.print(table)
    if strict and not all(row["ready"] for row in checks):
        raise typer.Exit(2)


@app.command()
def feasibility(
    output: Annotated[Path, typer.Option()] = Path("docs/feasibility/store_discovery.json"),
):
    """Read-only Apify Store search. No actor runs or credit use."""
    result = discover(output)
    unavailable = sum(row["status"] == "unavailable" for row in result["searches"])
    console.print(f"Saved {output}; {unavailable} queries unavailable; 0 actor runs.")
    if unavailable:
        raise typer.Exit(1)


@app.command("probe")
def probe_actor(
    actor_id: Annotated[str, typer.Argument()],
    input_file: Annotated[Path, typer.Option("--input", exists=True, dir_okay=False)],
    output: Path = Path("data/raw/feasibility"),
):
    """Run one capped, authenticated source test with a reviewed actor input."""
    try:
        result = probe(actor_id, input_file, Settings(), output)
        console.print(
            json.dumps(
                {
                    key: result.get(key)
                    for key in (
                        "actor_id",
                        "run_id",
                        "status",
                        "returned_count",
                        "returned_fields",
                        "usage_total_usd",
                    )
                },
                indent=2,
            )
        )
    except ValueError as exc:
        fail(exc)


@app.command()
def market(exchange: str = "HKEX"):
    """Collect real public OHLCV without Apify/Exa keys."""
    perform("market", exchange)


@app.command()
def collect(exchange: str = "HKEX"):
    """Collect two social sources through Apify, dated Exa news, and market prices."""
    perform("collect", exchange)


@app.command("import-probes")
def import_probes(
    selections: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    exchange: str = "HKEX", allow_partial: bool = False,
):
    """Import inspected Apify captures; partial coverage must be explicitly acknowledged."""
    try:
        console.print(pipeline().import_probes(exchange, selections, allow_partial))
    except (ValueError, FileNotFoundError) as exc:
        fail(exc)


@app.command()
def analyse(exchange: str = "HKEX", mode: str | None = None):
    """Clean data; extract sentiment/levels; write strictly causal features."""
    perform("analyse", exchange, mode)


@app.command()
def train(exchange: str = "HKEX", mode: str | None = None):
    """Expanding-window Ridge/boosted models, baselines, ablations and uncertainty."""
    perform("train", exchange, mode)


@app.command()
def predict(exchange: str = "HKEX", mode: str | None = None, commit: bool = True):
    """Write an immutable real-data forecast and commit before target market open."""
    try:
        console.print(pipeline().predict(exchange, mode, commit))
    except (ValueError, FileNotFoundError) as exc:
        fail(exc)


@app.command()
def evaluate(exchange: str = "HKEX"):
    """After the target close, append genuine outcomes without modifying forecasts."""
    perform("evaluate", exchange)


@app.command()
def report(output: Path = Path("reports")):
    """Export the latest completed datasets as self-contained interactive reports."""
    console.print(f"Report: {pipeline().report(output)}")


@app.command("run-all")
def run_all(
    exchange: str = "HKEX",
    mode: str = "live",
    output: Path = Path("reports"),
    issue_prediction: bool = False,
):
    """Run complete real-data analysis. Mode live requires source keys; price_only does not."""
    try:
        if mode not in {"live", "price_only"}:
            raise ValueError(
                "run-all mode must be live or price_only; use replay for simulated data"
            )
        p = pipeline()
        names = list(p.config.exchanges) if exchange.upper() == "ALL" else [exchange.upper()]
        if mode == "live":
            require_live_setup(p.config, p.settings, names)
        for name in names:
            p.collect(name) if mode == "live" else p.market(name)
            p.analyse(name, mode)
            p.train(name, mode)
            if issue_prediction:
                console.print(p.predict(name, mode))
        console.print(f"Report: {p.report(output)}")
    except (ValueError, FileNotFoundError) as exc:
        fail(exc)


@app.command()
def replay(
    sample: Annotated[Path, typer.Option(exists=True, dir_okay=False)] = Path(
        "data/sample/bundle.json"
    ),
    output: Path = Path("reports"),
):
    """Run the complete pipeline offline: extraction, levels, models, tests and report."""
    try:
        count, path = pipeline().replay(sample, output)
        console.print(f"Offline replay: {count} posts · provenance retained in report · {path}")
        if json.loads(sample.read_text(encoding="utf-8"))["provenance"] == "synthetic_fixture":
            console.print(
                "SIMULATED DATA: results demonstrate the software, not real trading performance."
            )
    except (ValueError, FileNotFoundError) as exc:
        fail(exc)


@app.command("deploy-actor")
def deploy_actor(name: str = "crowd-signal-naver-board"):
    """Deploy the included private Python Naver discussion-board actor to your account."""
    from crowd_signal.actor_deploy import deploy_naver_actor

    try:
        console.print(json.dumps(deploy_naver_actor(Settings(), name), indent=2))
    except ValueError as exc:
        fail(exc)


if __name__ == "__main__":
    app()
