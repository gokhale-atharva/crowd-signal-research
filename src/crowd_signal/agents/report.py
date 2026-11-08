"""Export a portable, multi-page research site with explicit dataset provenance."""

import json
import re
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, StrictUndefined, select_autoescape

from crowd_signal.config import ProjectConfig


def company_filename(ticker: str) -> str:
    return f"company-{re.sub(r'[^a-z0-9]+', '-', ticker.lower())}.html"


class ReportAgent:
    def preview(self, config: ProjectConfig, output: Path) -> Path:
        return self.render(config, output, {})

    def render(self, config: ProjectConfig, output: Path, datasets: dict) -> Path:
        from plotly.offline import get_plotlyjs

        env = Environment(autoescape=select_autoescape(default=True), undefined=StrictUndefined)
        root = files("crowd_signal").joinpath("templates")

        def read(name: str) -> str:
            return root.joinpath(name).read_text(encoding="utf-8")

        exchanges = {
            key: exchange.model_dump(mode="json") for key, exchange in config.exchanges.items()
        }
        initial = next(iter(exchanges))
        template = env.from_string(read("report.html"))
        application_js = env.from_string(read("research.js.j2")).render(
            spatial_js=read("spatial.js"), routes_js=read("routes.js")
        )
        common = dict(
            exchanges=exchanges,
            datasets=datasets,
            base_css=read("report-base.css"),
            workspace_css=read("workspace.css"),
            pages_css=read("pages.css"),
            motion_js=read("vendor/motion-14.10.1.js"),
            three_js=read("vendor/three-0.160.1.min.js"),
            plotly_js=get_plotlyjs(),
            application_js=application_js,
        )
        output.mkdir(parents=True, exist_ok=True)
        assets = output / "assets"
        assets.mkdir(exist_ok=True)
        asset_contents = {
            "config.js": "window.CROWD_CONFIG=" + json.dumps(exchanges, ensure_ascii=False) + ";",
            "data.js": "window.CROWD_DATA=" + json.dumps(datasets, ensure_ascii=False, allow_nan=False) + ";",
            "research.js": application_js,
            "research.css": common["base_css"] + common["workspace_css"] + common["pages_css"],
            "motion.js": common["motion_js"],
            "three.js": common["three_js"],
            "plotly.js": common["plotly_js"],
        }
        for name, content in asset_contents.items():
            (assets / name).write_text(content, encoding="utf-8")

        def page(name, kind, title, description, exchange=initial, ticker=None, standalone=False):
            (output / name).write_text(
                template.render(
                    **common, page_kind=kind, page_title=title, page_description=description,
                    initial_exchange=exchange, initial_ticker=ticker, standalone=standalone,
                ), encoding="utf-8",
            )

        pages = {
            "markets": ("Pick a market. Find your angle.", "Hong Kong and South Korea. Open a company for prices, forecasts and source evidence."),
            "community": ("What is behind the move?", "Crowd positions, source coverage and news. Choose a company to look closer."),
            "validation": ("Does the model earn its place?", "Compare forecast errors with a simple baseline. Inspect the uncertainty."),
            "methodology": ("The working, in full.", "Where the data comes from, how the tests run and what the results can tell you."),
        }
        for kind, (title, description) in pages.items():
            page(f"{kind}.html", kind, title, description)
        companies = []
        for key, exchange in exchanges.items():
            page(f"{key.lower()}.html", "markets", pages["markets"][0], pages["markets"][1], key, standalone=True)
            for asset in exchange["tickers"]:
                filename = company_filename(asset["ticker"])
                companies.append(dict(name=asset["asset_name"], ticker=asset["ticker"], file=filename))
                page(filename, "company", asset["asset_name"],
                     f"{asset['ticker']} · {exchange['name']} · Price, next-session estimate and source evidence.",
                     key, asset["ticker"])

        # Synthetic fixtures must never become an unlabelled market preview.
        packet = datasets.get(initial, {}).get("live") or datasets.get(initial, {}).get("price_only")
        summary = dict.fromkeys(("sessions", "as_of", "company", "price_text", "ticker", "spark",
                                 "mape", "baseline_mape", "model_width", "baseline_width"))
        if packet:
            asset = exchanges[initial]["tickers"][0]
            ticker = asset["ticker"]
            bars = packet.get("series", {}).get(ticker, {}).get("bars", [])[-30:]
            metric = packet.get("metrics", {}).get("ridge_price_only", {})
            baseline = packet.get("metrics", {}).get("random_walk", {})
            summary.update(sessions=metric.get("n_sessions"), as_of=packet["run"]["as_of"],
                           company=asset["asset_name"], ticker=ticker)
            if bars:
                values = [row["close"] for row in bars]
                low, high = min(values), max(values)
                summary["price_text"] = f"{exchanges[initial]['currency']} {values[-1]:,.2f}"
                summary["spark"] = " ".join(
                    f"{i / max(len(values) - 1, 1) * 200:.1f},{78 - (value - low) / (high - low or 1) * 66:.1f}"
                    for i, value in enumerate(values)
                )
            if metric.get("mape") is not None and baseline.get("mape") is not None:
                ceiling = max(metric["mape"], baseline["mape"], 0.01)
                summary.update(mape=f"{metric['mape']:.2f}", baseline_mape=f"{baseline['mape']:.2f}",
                               model_width=round(metric["mape"] / ceiling * 86),
                               baseline_width=round(baseline["mape"] / ceiling * 86))
        (output / "index.html").write_text(
            env.from_string(read("landing.html")).render(
                summary=summary, companies=companies, landing_css=read("landing.css"),
                motion_js=common["motion_js"], three_js=common["three_js"],
                landing_js=read("landing.js"),
            ), encoding="utf-8",
        )
        return output / "index.html"
