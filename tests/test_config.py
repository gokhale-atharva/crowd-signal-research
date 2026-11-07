from decimal import Decimal

import pytest
from pydantic import ValidationError

from crowd_signal.config import Settings, load_config


def test_two_exchanges_share_the_same_config_contract():
    config = load_config()
    assert set(config.exchanges) == {"HKEX", "KRX"}
    for exchange in config.exchanges.values():
        assert len(exchange.tickers) == 5
        assert len(set(exchange.proposed_sources)) >= 2
        assert all(asset.aliases for asset in exchange.tickers)
    assert config.exchange("hkex").currency == "HKD"
    with pytest.raises(ValueError, match="Unknown exchange"):
        config.exchange("INVALID")


def test_missing_keys_and_safe_defaults(settings):
    assert settings.apify_max_items == 20
    assert settings.apify_max_total_charge_usd == Decimal("0.10")
    with pytest.raises(ValueError, match="Missing APIFY_TOKEN"):
        settings.require("apify_token")


@pytest.mark.parametrize(
    "values",
    [
        {"apify_max_items": 0},
        {"apify_max_items": 21},
        {"apify_max_total_charge_usd": "0"},
        {"apify_max_total_charge_usd": "0.11"},
    ],
)
def test_budget_settings_fail_closed(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)


def test_secrets_do_not_appear_in_settings_repr():
    settings = Settings(_env_file=None, apify_token="fake-test-secret")
    assert "fake-test-secret" not in repr(settings)
    assert Settings(_env_file=None, apify_token="").apify_token is None
