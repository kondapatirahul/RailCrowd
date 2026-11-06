"""Trend analysis across daily, weekly, and severity-weighted incident volumes."""
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import func, select
from backend.app.extensions import db
from backend.app.models.incident import RailIncident

SEVERITY_VALUE = {"information": 1, "minor": 2, "major": 4, "critical": 7}

def _start_date(days, now=None):
    now = now or datetime.now(timezone.utc)
    return (now - timedelta(days=days)).date()

def daily_incident_volume(days=30, now=None):
    cutoff = _start_date(days, now)
    rows = db.session.execute(select(func.date(RailIncident.created_at), func.count(RailIncident.id)).where(RailIncident.created_at >= cutoff).group_by(func.date(RailIncident.created_at)).order_by(func.date(RailIncident.created_at))).all()
    values = {str(day): count for day, count in rows}
    series = []
    for offset in range(days - 1, -1, -1):
        day = (now or datetime.now(timezone.utc)).date() - timedelta(days=offset)
        series.append({"date": day.isoformat(), "count": values.get(day.isoformat(), 0)})
    return series

def severity_weighted_volume(days=30):
    cutoff = _start_date(days)
    rows = db.session.execute(select(RailIncident.severity, func.count(RailIncident.id)).where(RailIncident.created_at >= cutoff).group_by(RailIncident.severity)).all()
    distribution = {severity: count for severity, count in rows}
    score = sum(SEVERITY_VALUE.get(severity, 1) * count for severity, count in distribution.items())
    return {"score": score, "distribution": distribution,
            "average_per_day": round(score / max(1, days), 2)}

def compare_periods(current_days=7):
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=current_days)
    previous_start = current_start - timedelta(days=current_days)
    current = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.created_at >= current_start)).scalar_one()
    previous = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.created_at >= previous_start, RailIncident.created_at < current_start)).scalar_one()
    if previous == 0:
        change = 100.0 if current else 0.0
    else:
        change = round((current - previous) * 100 / previous, 1)
    return {"current": current, "previous": previous, "change_percent": change,
            "direction": "up" if change > 0 else "down" if change < 0 else "flat",
            "period_days": current_days}

def category_trends(days=30):
    cutoff = _start_date(days)
    rows = db.session.execute(select(RailIncident.category, func.count(RailIncident.id)).where(RailIncident.created_at >= cutoff).group_by(RailIncident.category).order_by(func.count(RailIncident.id).desc())).all()
    total = sum(count for _, count in rows)
    return [{"category": category, "count": count,
             "share_percent": round(count * 100 / total, 1) if total else 0}
            for category, count in rows]

def status_resolution_rate(days=30):
    cutoff = _start_date(days)
    total = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.created_at >= cutoff)).scalar_one()
    resolved = db.session.execute(select(func.count(RailIncident.id)).where(RailIncident.created_at >= cutoff, RailIncident.status == "resolved")).scalar_one()
    return {"total": total, "resolved": resolved,
            "rate_percent": round(resolved * 100 / total, 1) if total else 0}

def build_trend_report(days=30):
    days = max(7, min(int(days), 90))
    return {"window_days": days, "daily_volume": daily_incident_volume(days),
            "severity_weighted": severity_weighted_volume(days),
            "period_comparison": compare_periods(min(days // 2, 30)),
            "categories": category_trends(days), "resolution": status_resolution_rate(days),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "notice": "These trends describe RailCrowd community reports and are not official railway performance statistics."}
