from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from backend.app.modules.trains.services.crowd_scoring import (
    classify_crowd_index,
    confidence_label,
    weighted_crowd_index,
)


def test_crowd_index_classification_boundaries():
    assert classify_crowd_index(None) is None
    assert classify_crowd_index(20) == "Low"
    assert classify_crowd_index(45) == "Moderate"
    assert classify_crowd_index(70) == "High"
    assert classify_crowd_index(90) == "Very High"


def test_confidence_is_based_on_report_volume():
    assert confidence_label(0) == "No data"
    assert confidence_label(2) == "Limited"
    assert confidence_label(4) == "Moderate"
    assert confidence_label(8) == "Strong"


def test_weighted_index_ignores_pending_and_stale_reports():
    now = datetime.now(timezone.utc)
    reports = [
        SimpleNamespace(status="approved", crowd_level="Very High", observed_at=now - timedelta(minutes=5)),
        SimpleNamespace(status="approved", crowd_level="Low", observed_at=now - timedelta(minutes=300)),
        SimpleNamespace(status="pending", crowd_level="Low", observed_at=now),
    ]
    index, accepted, latest = weighted_crowd_index(reports, now, 180)
    assert index == 90.0
    assert len(accepted) == 1
    assert latest == now


def test_recent_report_has_more_weight_than_older_report():
    now = datetime.now(timezone.utc)
    reports = [
        SimpleNamespace(status="approved", crowd_level="Very High", observed_at=now - timedelta(minutes=2)),
        SimpleNamespace(status="approved", crowd_level="Low", observed_at=now - timedelta(minutes=150)),
    ]
    index, accepted, _ = weighted_crowd_index(reports, now, 180)
    assert len(accepted) == 2
    assert index > 55
