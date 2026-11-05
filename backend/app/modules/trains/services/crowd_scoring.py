"""Pure scoring helpers for community crowd observations."""

CROWD_LEVEL_SCORES = {
    "Low": 20.0,
    "Moderate": 45.0,
    "High": 70.0,
    "Very High": 90.0,
}


def classify_crowd_index(index):
    """Map a weighted 0-100 community index to a readable crowd label."""
    if index is None:
        return None
    value = float(index)
    if value < 35:
        return "Low"
    if value < 55:
        return "Moderate"
    if value < 75:
        return "High"
    return "Very High"


def confidence_label(report_count):
    """Describe evidence volume without implying statistical certainty."""
    count = int(report_count or 0)
    if count <= 0:
        return "No data"
    if count <= 2:
        return "Limited"
    if count <= 5:
        return "Moderate"
    return "Strong"


def weighted_crowd_index(reports, now, max_age_minutes=180):
    """Return (index, accepted_reports, latest_timestamp) for fresh reports.

    Recent reports receive more weight. Reports outside the freshness window,
    unapproved reports, and unknown crowd labels are ignored.
    """
    from datetime import timezone

    accepted = []
    latest = None
    total_weight = 0.0
    weighted_total = 0.0
    max_age_seconds = max(1, int(max_age_minutes)) * 60

    for report in reports:
        if getattr(report, "status", None) != "approved":
            continue
        score = CROWD_LEVEL_SCORES.get(getattr(report, "crowd_level", None))
        observed = getattr(report, "observed_at", None)
        if score is None or observed is None:
            continue
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        else:
            observed = observed.astimezone(timezone.utc)
        current = now
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        else:
            current = current.astimezone(timezone.utc)
        age_seconds = max(0.0, (current - observed).total_seconds())
        if age_seconds > max_age_seconds:
            continue
        # Linear decay: newest observations approach weight 1; the freshness
        # boundary retains a small non-zero weight to avoid divide-by-zero.
        weight = max(0.05, 1.0 - (age_seconds / max_age_seconds))
        weighted_total += score * weight
        total_weight += weight
        accepted.append(report)
        if latest is None or observed > latest:
            latest = observed

    if not accepted or total_weight <= 0:
        return None, [], None
    return round(weighted_total / total_weight, 1), accepted, latest
