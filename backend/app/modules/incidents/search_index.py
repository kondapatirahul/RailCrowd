"""Small database-backed discovery index for incident keywords."""
from sqlalchemy import or_, select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident

SEARCH_FIELDS = (RailIncident.title, RailIncident.description, RailIncident.train_number,
                 RailIncident.train_name, RailIncident.station_code, RailIncident.station_name,
                 RailIncident.category)

def tokenize_query(value):
    tokens = []
    for token in (value or "").casefold().split():
        cleaned = "".join(char for char in token if char.isalnum())
        if len(cleaned) >= 2 and cleaned not in tokens:
            tokens.append(cleaned)
    return tokens[:8]

def build_search_statement(tokens, public_only=True):
    statement = select(RailIncident)
    if public_only:
        statement = statement.where(RailIncident.is_public.is_(True), RailIncident.status.in_(["verified", "monitoring", "resolved"]))
    for token in tokens:
        pattern = f"%{token}%"
        statement = statement.where(or_(*(field.ilike(pattern) for field in SEARCH_FIELDS)))
    return statement

def search_incidents(value, limit=30, public_only=True):
    tokens = tokenize_query(value)
    if not tokens:
        return []
    statement = build_search_statement(tokens, public_only)
    return db.session.execute(statement.order_by(RailIncident.is_pinned.desc(), RailIncident.created_at.desc()).limit(min(max(limit, 1), 100))).scalars().all()

def search_facets(value):
    rows = search_incidents(value, 100)
    return {"categories": sorted({item.category for item in rows}),
            "trains": sorted({item.train_number for item in rows if item.train_number}),
            "stations": sorted({item.station_code for item in rows if item.station_code}),
            "severities": sorted({item.severity for item in rows})}
