"""Read-only live setup checks. Configuration is never presented as source verification."""

from crowd_signal.config import ProjectConfig, Settings


def live_setup_checks(config: ProjectConfig, settings: Settings, exchanges: list[str]) -> list[dict]:
    checks = []
    for key in ("apify_token", "exa_api_key"):
        try:
            settings.require(key)
            ready = True
        except ValueError:
            ready = False
        checks.append({"check": key.upper(), "ready": ready,
                       "action": "Configured locally" if ready else f"Set {key.upper()} in the local .env file"})
    for name in exchanges:
        exchange = config.exchange(name)
        for source in exchange.proposed_sources:
            supported = source in {"lihkg", "telegram", "naver_board"}
            checks.append({"check": f"{name}/{source} adapter", "ready": supported,
                           "action": "Input adapter implemented; a capped run still needs verification" if supported
                           else "Choose a supported source or implement its input adapter"})
            configured = bool(exchange.actor_ids.get(source, "").strip())
            checks.append({"check": f"{name}/{source} actor", "ready": configured,
                           "action": "Actor ID configured, not verified" if configured else
                           "Deploy the included Naver actor and record its returned ID in exchange YAML"})
        if "telegram" in exchange.proposed_sources:
            configured = bool(exchange.telegram_channels)
            checks.append({"check": f"{name}/telegram channels", "ready": configured,
                           "action": "Channels configured; timestamped relevant posts still need verification" if configured
                           else "Set reviewed public investor channels in exchange YAML"})
    return checks


def require_live_setup(config: ProjectConfig, settings: Settings, exchanges: list[str]) -> None:
    missing = [row for row in live_setup_checks(config, settings, exchanges) if not row["ready"]]
    if missing:
        details = "\n".join(f"- {row['check']}: {row['action']}" for row in missing)
        raise ValueError(f"Live collection is not ready. No source jobs were launched.\n{details}")
