"""Deploy the reviewed private source actor through the official Python client."""

import json
from pathlib import Path

from apify_client import ApifyClient

from crowd_signal.config import Settings
from crowd_signal.storage import write_json


def deploy_naver_actor(settings: Settings, name: str, root: Path | None = None) -> dict:
    root = root or Path.cwd()
    token = settings.require("apify_token")
    source = root / "actors/naver_board"
    manifest = root / "data/cache/deployed_naver_actor.json"
    if manifest.exists():
        return json.loads(manifest.read_text(encoding="utf-8"))
    files = [
        {
            "name": path.relative_to(source).as_posix(),
            "format": "TEXT",
            "content": path.read_text(encoding="utf-8"),
        }
        for path in sorted(source.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]
    client = ApifyClient(token, max_retries=0, timeout_secs=30)
    try:
        actor = client.actors().create(
            name=name,
            title="Crowd Signal Naver discussion board",
            is_public=False,
            default_run_memory_mbytes=256,
            default_run_timeout_secs=120,
            versions=[{"versionNumber": "0.1", "sourceType": "SOURCE_FILES", "sourceFiles": files}],
        )
        result = {
            "actor_id": actor["id"],
            "name": name,
            "source_path": "actors/naver_board",
            "build_status": "not_started",
        }
        write_json(manifest, result)
        build = client.actor(actor["id"]).build(
            version_number="0.1", tag="latest", wait_for_finish=60
        )
        result.update(build_id=build["id"], build_status=build["status"])
        write_json(manifest, result)
        return result
    except Exception as exc:
        raise ValueError(
            f"Actor deployment failed ({type(exc).__name__}); inspect Apify Console and the local deployment manifest before retrying"
        ) from None
