import pytest

from crowd_signal.config import Settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """Tests must never inherit developer secrets or perform a real billable run."""
    # Real provider keys may now exist locally; no test may load that .env.
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for key in (
        "APIFY_TOKEN",
        "EXA_API_KEY",
        "LLM_API_KEY",
        "APIFY_MAX_ITEMS",
        "APIFY_MAX_TOTAL_CHARGE_USD",
        "APIFY_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def settings():
    return Settings(_env_file=None)
