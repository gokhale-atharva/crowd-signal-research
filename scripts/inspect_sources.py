"""Read public Actor metadata and input schemas. No credentials or Actor runs."""

from datetime import UTC, datetime
from pathlib import Path

from apify_client import ApifyClient

from crowd_signal.feasibility import write_json

client = ApifyClient(max_retries=1, timeout_secs=20)
records = []
for actor_id in (
    "claude_code_reviewer/lihkg-scraper-en",
    "scrapesage/telegram-scraper",
    "bovi/aastocks-scraper",
):
    row = {"actor_id": actor_id, "observed_posts": 0, "run_performed": False}
    try:
        actor = client.actor(actor_id)
        metadata = actor.get()
        if metadata:
            row["metadata"] = {
                key: metadata.get(key)
                for key in (
                    "id",
                    "name",
                    "username",
                    "title",
                    "description",
                    "pricingInfos",
                    "defaultRunOptions",
                    "modifiedAt",
                )
            }
            build = actor.default_build().get() or {}
            definition = build.get("actorDefinition") or {}
            row["build_id"] = build.get("id")
            row["build_number"] = build.get("buildNumber")
            row["input_schema"] = definition.get("input") or build.get("inputSchema")
        else:
            row["status"] = "metadata_unavailable"
    except Exception as exc:
        row["error_type"] = type(exc).__name__
    records.append(row)
target = Path("docs/feasibility/candidate_metadata.json")
write_json(
    target,
    {
        "checked_at": datetime.now(UTC).isoformat(),
        "method": "apify-client public metadata/default build; no actor runs",
        "candidates": records,
    },
)
print(f"Saved {len(records)} candidate inspections to {target}. No Actors started.")
