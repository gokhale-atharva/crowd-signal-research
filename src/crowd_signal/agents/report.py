"""Export a portable design preview with no remote assets or fabricated results."""

from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, StrictUndefined, select_autoescape

from crowd_signal.config import ProjectConfig


class ReportAgent:
    def preview(self, config: ProjectConfig, output: Path) -> Path:
        env = Environment(autoescape=select_autoescape(default=True), undefined=StrictUndefined)
        template = env.from_string(
            files("crowd_signal").joinpath("templates/report.html").read_text(encoding="utf-8")
        )
        exchanges = {
            key: exchange.model_dump(mode="json") for key, exchange in config.exchanges.items()
        }
        output.mkdir(parents=True, exist_ok=True)
        for key in ("index", *[name.lower() for name in config.exchanges]):
            initial = "HKEX" if key == "index" else key.upper()
            (output / f"{key}.html").write_text(
                template.render(exchanges=exchanges, initial_exchange=initial), encoding="utf-8"
            )
        return output / "index.html"
