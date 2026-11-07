"""One CLI for the project, including explicit milestone readiness errors."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from crowd_signal.agents.base import StagePendingError
from crowd_signal.config import Settings, load_config
from crowd_signal.feasibility import discover, probe
from crowd_signal.pipeline import Pipeline

app = typer.Typer(no_args_is_help=True, help="Crowd Signal · exchange sentiment research")
console = Console()


def pipeline(config: Path | None = None) -> Pipeline:
    return Pipeline(load_config(config), Settings())


def fail(exc: Exception) -> None:
    console.print(f"[red]Not ready:[/red] {exc}", markup=True)
    raise typer.Exit(2)


@app.command()
def doctor(config: Annotated[Path | None, typer.Option(help="Override exchange YAML")] = None):
    """Validate configuration and show credential presence without exposing values."""
    p = pipeline(config)
    table = Table(title="Crowd Signal · readiness")
    table.add_column("Check")
    table.add_column("State")
    for name, exchange in p.config.exchanges.items():
        table.add_row(
            name, f"{len(exchange.tickers)} assets · {exchange.timezone} · sources unverified"
        )
    for key in ("apify_token", "exa_api_key", "llm_api_key"):
        try:
            p.settings.require(key)
            state = "configured"
        except ValueError:
            state = "missing" + (" (optional)" if key == "llm_api_key" else "")
        table.add_row(key.upper(), state)
    table.add_row("Milestone", "1 · scaffold; live / modelling pending")
    console.print(table)


@app.command()
def feasibility(
    output: Annotated[Path, typer.Option()] = Path("docs/feasibility/store_discovery.json"),
):
    """Search candidate social sources in the public Apify Store. No actor runs."""
    result = discover(output)
    unavailable = sum(row["status"] == "unavailable" for row in result["searches"])
    console.print(
        f"Saved Store discovery to {output}; {unavailable} queries unavailable; 0 actor runs."
    )
    if unavailable:
        raise typer.Exit(1)


@app.command("probe")
def probe_actor(
    actor_id: Annotated[str, typer.Argument(help="Verified Store owner/actor identifier")],
    input_file: Annotated[Path, typer.Option("--input", exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option()] = Path("data/raw/feasibility"),
):
    """Run one capped, authenticated source test with a reviewed actor input."""
    try:
        manifest = probe(actor_id, input_file, Settings(), output)
        console.print(
            json.dumps(
                {
                    key: manifest.get(key)
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
def collect(exchange: str = "HKEX"):
    """Collect social posts, Exa news and market bars (milestone 2)."""
    try:
        pipeline().collect(exchange)
    except (ValueError, StagePendingError) as exc:
        fail(exc)


@app.command()
def analyse(exchange: str = "HKEX"):
    """Extract sentiment and price levels (milestone 3)."""
    try:
        pipeline().analyse(exchange)
    except (ValueError, StagePendingError) as exc:
        fail(exc)


@app.command()
def train(exchange: str = "HKEX"):
    """Fit expanding-window models and ablations (milestone 4)."""
    try:
        pipeline().train(exchange)
    except (ValueError, StagePendingError) as exc:
        fail(exc)


@app.command()
def predict(exchange: str = "HKEX"):
    """Issue a next-session forecast (milestone 7)."""
    try:
        pipeline().predict(exchange)
    except (ValueError, StagePendingError) as exc:
        fail(exc)


@app.command()
def evaluate(exchange: str = "HKEX"):
    """Evaluate previously issued live forecasts (milestone 7)."""
    try:
        pipeline().evaluate(exchange)
    except (ValueError, StagePendingError) as exc:
        fail(exc)


@app.command()
def report(output: Path = Path("reports")):
    """Export the self-contained, empty-state design preview. No analytical results yet."""
    console.print(f"Report preview: {pipeline().report(output)}")


@app.command("run-all")
def run_all(exchange: str = "HKEX"):
    """Execute all implemented stages; fail clearly at the first pending stage."""
    collect(exchange)
    analyse(exchange)
    train(exchange)
    report()


@app.command()
def replay(
    sample: Annotated[Path, typer.Option(exists=True, dir_okay=False)] = Path(
        "data/sample/posts.json"
    ),
    output: Path = Path("reports"),
):
    """Offline checkpoint: validate synthetic fixtures and render the design preview."""
    try:
        count, path = pipeline().replay(sample, output)
        console.print(f"Validated {count} synthetic fixture posts; design preview: {path}")
        console.print(
            "Scaffold checkpoint only. No sentiment, backtest, or forecast has been computed."
        )
    except (ValueError, KeyError) as exc:
        fail(exc)


if __name__ == "__main__":
    app()
