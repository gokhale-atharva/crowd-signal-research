import pytest

from crowd_signal.config import Settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    """Tests must never inherit developer secrets or perform a real billable run."""
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
