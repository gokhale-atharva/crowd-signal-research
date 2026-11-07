import json
from types import SimpleNamespace
from unittest.mock import Mock, create_autospec

import pytest
from apify_client import ApifyClient

from crowd_signal.config import Settings
from crowd_signal.feasibility import probe


def test_probe_requires_key_before_calling_sdk(tmp_path):
    with pytest.raises(ValueError, match="Missing APIFY_TOKEN"):
        probe("test/actor", tmp_path / "does-not-exist.json", Settings(_env_file=None), tmp_path)


@pytest.mark.parametrize(
    "inputs",
    [
        {"maxItems": 21},
        {},
        {"maxItems": 20, "keywords": ["a", "b"]},
        {"maxItems": 20, "bulkInput": "one\ntwo\nthree"},
        {"maxItems": 1, "mode": "thread"},
        {"maxMessages": 20, "channels": ["REPLACE_WITH_REVIEWED_PUBLIC_FINANCE_CHANNEL"]},
        {"maxMessages": 20, "downloadMedia": True},
        {"maxItems": 20, "aiLabels": True},
    ],
)
def test_probe_rejects_unbounded_input_before_starting_actor(tmp_path, monkeypatch, inputs):
    factory = Mock()
    monkeypatch.setattr("crowd_signal.feasibility.ApifyClient", factory)
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(inputs), encoding="utf-8")
    with pytest.raises(ValueError):
        probe("test/actor", input_file, Settings(_env_file=None, apify_token="fake"), tmp_path)
    factory.assert_not_called()


def test_probe_sets_both_limits_caches_run_and_fields_without_retry(tmp_path, monkeypatch):
    # Use the real installed SDK signature, so API drift cannot hide behind a loose mock.
    actor = create_autospec(type(ApifyClient().actor("test/actor")), instance=True)
    actor.get.return_value = {"pricingInfos": [{"pricingModel": "PAY_PER_EVENT"}]}
    actor.call.return_value = {
        "id": "run-fixture",
        "status": "SUCCEEDED",
        "defaultDatasetId": "dataset-fixture",
        "usageTotalUsd": 0.01,
    }
    client = Mock()
    client.actor.return_value = actor
    client.dataset.return_value.list_items.return_value = SimpleNamespace(
        items=[{"text": "fixture", "date": "2026-11-06"}]
    )
    factory = Mock(return_value=client)
    monkeypatch.setattr("crowd_signal.feasibility.ApifyClient", factory)
    input_file = tmp_path / "input.json"
    input_file.write_text('{"maxItems":20,"keywords":["騰訊"]}', encoding="utf-8")
    manifest = probe(
        "test/actor", input_file, Settings(_env_file=None, apify_token="fake"), tmp_path / "raw"
    )
    kwargs = actor.call.call_args.kwargs
    assert kwargs["max_items"] == 20
    assert str(kwargs["max_total_charge_usd"]) == "0.10"
    assert kwargs["restart_on_error"] is False
    assert factory.call_args.kwargs["max_retries"] == 0
    assert manifest["returned_fields"] == ["date", "text"]
    assert (tmp_path / "raw/manifest.json").is_file()
    assert (tmp_path / "raw/items.json").is_file()
