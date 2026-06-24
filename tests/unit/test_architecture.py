"""Unit tests: env-var dependency detection + blast radius walk."""

from app.models import Dependency
from app.services.architecture_service import (
    _extract_host,
    _extract_service_target,
    _walk_downstream,
    _walk_upstream,
)


def _dep(from_s: str, to_s: str) -> Dependency:
    return Dependency(
        from_service=from_s,
        to_service=to_s,
        to_kind="service",
        detected_via="env_var",
    )


def test_extract_host_from_url():
    assert _extract_host("http://payment-api:8080") == "payment-api"
    assert _extract_host("https://db.internal:5432/path") == "db.internal"


def test_extract_host_bare():
    assert _extract_host("redis:6379") == "redis"
    assert _extract_host("postgres") == "postgres"


def test_extract_host_none_for_garbage():
    assert _extract_host("not a host") is None


def test_target_known_service():
    result = _extract_service_target("PAYMENT_URL", "http://payment-api", {"payment-api"})
    assert result == ("payment-api", "service")


def test_target_database_heuristic():
    result = _extract_service_target("DATABASE_URL", "postgres://db:5432", set())
    assert result is not None
    assert result[1] == "database"


def test_target_queue_heuristic():
    result = _extract_service_target("KAFKA_URL", "kafka://broker:9092", set())
    assert result is not None
    assert result[1] == "queue"


def test_target_none_for_random_value():
    assert _extract_service_target("LOG_LEVEL", "info", set()) is None


def test_walk_downstream_direct():
    deps = [_dep("frontend", "payment-api"), _dep("checkout", "payment-api")]
    result = _walk_downstream("payment-api", deps)
    assert sorted(result["direct"]) == ["checkout", "frontend"]


def test_walk_downstream_transitive():
    deps = [
        _dep("frontend", "api-gw"),
        _dep("api-gw", "auth"),
        _dep("auth", "redis"),
    ]
    result = _walk_downstream("redis", deps)
    # redis down → auth (depends on redis) → api-gw (depends on auth) → frontend (depends on api-gw)
    assert "auth" in result["all"]
    assert "api-gw" in result["all"]
    assert "frontend" in result["all"]


def test_walk_upstream():
    deps = [
        _dep("frontend", "api-gw"),
        _dep("frontend", "auth"),
    ]
    result = _walk_upstream("frontend", deps)
    assert sorted(result) == ["api-gw", "auth"]


def test_blast_radius_isolated_service():
    deps = [_dep("a", "b"), _dep("c", "d")]
    down = _walk_downstream("x", deps)
    up = _walk_upstream("x", deps)
    assert down["direct"] == []
    assert down["all"] == []
    assert up == []
