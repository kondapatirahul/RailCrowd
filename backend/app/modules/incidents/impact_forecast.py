"""Historical disruption patterns presented as descriptive caution signals."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident

def train_history(train_number, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return db.session.execute(select(RailIncident).where(RailIncident.train_number == train_number,
        RailIncident.created_at >= cutoff, RailIncident.status.in_(["verified", "monitoring", "resolved"]))).scalars().all()

def category_frequency(rows):
    result = {}
    for incident in rows:
        result[incident.category] = result.get(incident.category, 0) + 1
    return sorted(({"category": key, "count": value} for key, value in result.items()), key=lambda item: item["count"], reverse=True)

def historical_signal(rows, days=30):
    if not rows:
        return {"level": "no history", "score": 0, "count": 0, "daily_average": 0.0}
    weighted = sum({"critical": 4, "major": 3, "minor": 2, "information": 1}.get(item.severity, 1) for item in rows)
    score = min(100, round(weighted * 100 / max(1, days * 2)))
    level = "elevated" if score >= 60 else "moderate" if score >= 30 else "low"
    return {"level": level, "score": score, "count": len(rows),
            "daily_average": round(len(rows) / max(1, days), 2),
            "categories": category_frequency(rows)}

def train_historical_signal(train_number, days=30):
    rows = train_history(train_number, days)
    return {"train_number": train_number, "window_days": days,
            "history": historical_signal(rows, days),
            "notice": "Historical community observations are descriptive and do not predict future delays or service conditions."}

def station_history(station_code, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.session.execute(select(RailIncident).where(RailIncident.station_code == station_code.upper(), RailIncident.created_at >= cutoff, RailIncident.status.in_(["verified", "monitoring", "resolved"]))).scalars().all()
    return historical_signal(rows, days)
