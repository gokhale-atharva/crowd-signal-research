"""Export self-contained analytical reports with explicit dataset provenance."""

from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, StrictUndefined, select_autoescape

from crowd_signal.config import ProjectConfig


class ReportAgent:
    def preview(self, config: ProjectConfig, output: Path) -> Path:
        return self.render(config, output, {})

    def render(self, config: ProjectConfig, output: Path, datasets: dict) -> Path:
        env = Environment(autoescape=select_autoescape(default=True), undefined=StrictUndefined)
        template = env.from_string(
            files("crowd_signal").joinpath("templates/report.html").read_text(encoding="utf-8")
        )
        exchanges = {
            key: exchange.model_dump(mode="json") for key, exchange in config.exchanges.items()
        }
        from plotly.offline import get_plotlyjs

        plotly_js = get_plotlyjs()
        motion_js = (
            files("crowd_signal")
            .joinpath("templates/vendor/motion-14.10.1.js")
            .read_text(encoding="utf-8")
        )
        template_root = files("crowd_signal").joinpath("templates")
        three_js = template_root.joinpath("vendor/three-0.160.1.min.js").read_text(encoding="utf-8")
        spatial_js = template_root.joinpath("spatial.js").read_text(encoding="utf-8")
        workspace_css = template_root.joinpath("workspace.css").read_text(encoding="utf-8")
        output.mkdir(parents=True, exist_ok=True)
        for key in ("index", *[name.lower() for name in config.exchanges]):
            initial = "HKEX" if key == "index" else key.upper()
            (output / f"{key}.html").write_text(
                template.render(
                    exchanges=exchanges,
                    initial_exchange=initial,
                    datasets=datasets,
                    plotly_js=plotly_js,
                    motion_js=motion_js,
                    three_js=three_js,
                    spatial_js=spatial_js,
                    workspace_css=workspace_css,
                ),
                encoding="utf-8",
            )
        return output / "index.html"
