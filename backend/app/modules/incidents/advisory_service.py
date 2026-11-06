"""Service advisory drafting, scheduling, publication, and expiry."""
from datetime import datetime, timezone
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.incident import ServiceAdvisory, IncidentUpdate
from backend.app.modules.incidents.validation import validate_advisory_payload, IncidentInputError

class AdvisoryError(ValueError):
    pass

def create_advisory(author_id, raw_payload, publish=False):
    data = validate_advisory_payload(raw_payload)
    advisory = ServiceAdvisory(author_id=author_id, **data)
    advisory.status = "published" if publish else "draft"
    if publish:
        advisory.published_at = datetime.now(timezone.utc)
    db.session.add(advisory)
    db.session.flush()
    return advisory

def update_advisory(advisory_id, raw_payload):
    advisory = db.session.execute(select(ServiceAdvisory).where(ServiceAdvisory.id == advisory_id).with_for_update()).scalar_one_or_none()
    if advisory is None:
        raise AdvisoryError("Advisory not found.")
    if advisory.status in {"withdrawn", "expired"}:
        raise AdvisoryError("Closed advisories cannot be edited.")
    data = validate_advisory_payload(raw_payload)
    for key, value in data.items():
        setattr(advisory, key, value)
    db.session.flush()
    return advisory

def publish_advisory(advisory_id):
    advisory = db.session.get(ServiceAdvisory, advisory_id)
    if advisory is None:
        raise AdvisoryError("Advisory not found.")
    if advisory.status not in {"draft", "scheduled"}:
        raise AdvisoryError("Only drafts and scheduled advisories can be published.")
    advisory.status = "published"
    advisory.published_at = datetime.now(timezone.utc)
    db.session.flush()
    return advisory

def withdraw_advisory(advisory_id, note=""):
    advisory = db.session.execute(select(ServiceAdvisory).where(ServiceAdvisory.id == advisory_id).with_for_update()).scalar_one_or_none()
    if advisory is None:
        raise AdvisoryError("Advisory not found.")
    if advisory.status in {"withdrawn", "expired"}:
        return advisory
    advisory.status = "withdrawn"
    advisory.withdrawn_at = datetime.now(timezone.utc)
    advisory.alternative_guidance = (advisory.alternative_guidance or "")[:2800]
    db.session.flush()
    return advisory

def expire_advisories(now=None):
    now = now or datetime.now(timezone.utc)
    rows = db.session.execute(select(ServiceAdvisory).where(ServiceAdvisory.status == "published", ServiceAdvisory.ends_at.is_not(None), ServiceAdvisory.ends_at < now).with_for_update()).scalars().all()
    for row in rows:
        row.status = "expired"
    db.session.flush()
    return len(rows)

def publish_due_advisories(now=None):
    now = now or datetime.now(timezone.utc)
    rows = db.session.execute(select(ServiceAdvisory).where(ServiceAdvisory.status == "scheduled", (ServiceAdvisory.starts_at.is_(None)) | (ServiceAdvisory.starts_at <= now)).with_for_update()).scalars().all()
    for row in rows:
        row.status = "published"
        row.published_at = now
    db.session.flush()
    return len(rows)
