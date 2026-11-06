"""Health probes for incident subsystem dependencies and schema readiness."""
from sqlalchemy import inspect, text
from backend.app.extensions import db
EXPECTED_TABLES = {"rail_incidents", "incident_updates", "incident_votes", "incident_subscriptions", "service_advisories", "incident_read_receipts"}

def schema_health():
    inspector = inspect(db.engine)
    available = set(inspector.get_table_names())
    missing = sorted(EXPECTED_TABLES - available)
    return {"ok": not missing, "expected": sorted(EXPECTED_TABLES),
            "available": sorted(EXPECTED_TABLES & available), "missing": missing}

def database_round_trip():
    try:
        value = db.session.execute(text("SELECT 1")).scalar_one()
        return {"ok": value == 1, "value": value}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}

def subsystem_health():
    schema = schema_health()
    database = database_round_trip()
    return {"ok": schema["ok"] and database["ok"], "schema": schema, "database": database}
