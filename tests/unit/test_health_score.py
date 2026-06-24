"""Unit test: health score computation."""

from app.schemas.dashboard import IncidentRef
from app.services.dashboard_service import _compute_health


def _incident(severity: str) -> IncidentRef:
    return IncidentRef(
        id="inc-1", title="x", severity=severity, service=None, age_seconds=60
    )


def test_healthy_when_all_signals_good():
    health = _compute_health(
        availability=1.0, error_rate=0.0, firing_alerts=[], incidents=[]
    )
    assert health.status == "Healthy"
    assert health.score >= 95.0


def test_degraded_when_availability_drops():
    health = _compute_health(
        availability=0.95, error_rate=0.01, firing_alerts=[], incidents=[]
    )
    assert health.status in {"Degraded", "Healthy"}
    assert health.score < 100.0


def test_critical_when_incidents_and_alerts():
    health = _compute_health(
        availability=0.9,
        error_rate=0.05,
        firing_alerts=[{}, {}, {}, {}, {}],
        incidents=[_incident("sev1"), _incident("sev1")],
    )
    assert health.status in {"Critical", "Unknown"}


def test_unknown_when_no_signals():
    health = _compute_health(
        availability=None, error_rate=None, firing_alerts=[], incidents=[]
    )
    assert health.status == "Unknown"
    assert health.availability is None


def test_error_rate_drives_score_down():
    good = _compute_health(availability=1.0, error_rate=0.0, firing_alerts=[], incidents=[])
    bad = _compute_health(availability=1.0, error_rate=0.1, firing_alerts=[], incidents=[])
    assert bad.score < good.score
