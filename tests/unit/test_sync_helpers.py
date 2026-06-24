"""Unit test: sync service config-event parsing helpers."""

from datetime import datetime, timezone

from app.services.sync_service import (
    _change_type,
    _config_kind,
    _config_name,
    _is_config_event,
    _parse_event_time,
)


def test_is_config_event_true_for_updated_configmap():
    e = {"reason": "Updated", "message": "ConfigMap my-config updated", "namespace": "prod"}
    assert _is_config_event(e) is True


def test_is_config_event_false_for_pod_event():
    e = {"reason": "Started", "message": "Pod my-app started", "namespace": "prod"}
    assert _is_config_event(e) is False


def test_config_kind_detects_configmap():
    assert _config_kind({"message": "ConfigMap my-config updated"}) == "ConfigMap"


def test_config_kind_detects_secret():
    assert _config_kind({"message": "Secret db-creds updated"}) == "Secret"


def test_config_kind_none_for_other():
    assert _config_kind({"message": "Pod started"}) is None


def test_config_name_extracts_after_kind():
    assert _config_name({"message": "ConfigMap my-config updated"}) == "my-config"


def test_config_name_fallback_to_event_name():
    assert _config_name({"message": "no kind here", "name": "event-123"}) == "event-123"


def test_change_type_mapping():
    assert _change_type({"reason": "Created"}) == "created"
    assert _change_type({"reason": "Deleted"}) == "deleted"
    assert _change_type({"reason": "Updated"}) == "updated"
    assert _change_type({"reason": ""}) == "updated"


def test_parse_event_time_iso():
    ts = "2026-06-24T12:00:00Z"
    parsed = _parse_event_time({"last_timestamp": ts})
    assert parsed is not None
    assert parsed.year == 2026


def test_parse_event_time_none():
    assert _parse_event_time({"last_timestamp": None}) is None


def test_parse_event_time_datetime_passthrough():
    dt = datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc)
    assert _parse_event_time({"last_timestamp": dt}) == dt
