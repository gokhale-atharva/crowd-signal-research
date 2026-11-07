"""Record only this project's installed core + dev dependency closure, without paths or secrets."""

from importlib.metadata import distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

pending = [("crowd-signal", ("", "dev"))]
seen: dict[str, str] = {}
while pending:
    name, extras = pending.pop()
    key = canonicalize_name(name)
    if key in seen:
        continue
    installed = distribution(name)
    seen[key] = installed.version
    for raw in installed.requires or []:
        requirement = Requirement(raw)
        if requirement.marker is None or any(
            requirement.marker.evaluate({"extra": extra}) for extra in extras
        ):
            pending.append((requirement.name, tuple(requirement.extras) or ("",)))
seen.pop("crowd-signal")
Path("requirements-dev.lock").write_text(
    "# Tested dependency snapshot: Windows / Python 3.13.5.\n"
    "# Install in a clean virtual environment: pip install -r requirements-dev.lock\n"
    "# Use pyproject.toml for unpinned cross-platform resolution.\n"
    + "".join(f"{name}=={version}\n" for name, version in sorted(seen.items()))
    + "-e .\n",
    encoding="utf-8",
)
print(f"Recorded {len(seen)} dependency versions")
