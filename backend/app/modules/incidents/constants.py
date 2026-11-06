"""Domain vocabulary and operational thresholds for disruption reports."""
CATEGORIES = {
 "delay": "Train delay", "cancellation": "Cancellation", "platform_change": "Platform change",
 "overcrowding": "Overcrowding", "safety": "Passenger safety", "cleanliness": "Cleanliness",
 "facility": "Station facility", "accessibility": "Accessibility", "security": "Security concern",
 "track": "Track or infrastructure", "other": "Other disruption",
}
SEVERITIES = {"information": 0, "minor": 1, "major": 2, "critical": 3}
STATUSES = {"pending", "under_review", "verified", "monitoring", "resolved", "rejected", "withdrawn", "stale"}
TRANSITIONS = {
 "pending": {"under_review", "verified", "rejected", "stale"},
 "under_review": {"verified", "monitoring", "resolved", "rejected", "stale"},
 "verified": {"monitoring", "resolved", "rejected", "stale"},
 "monitoring": {"verified", "resolved", "rejected", "stale"},
 "resolved": {"monitoring"},
 "rejected": set(),
 "withdrawn": set(),
 "stale": {"monitoring"},
}
VOTE_TYPES = {"confirm", "contradict"}
FRESHNESS_MINUTES = {"fresh": 15, "recent": 60, "aging": 240}
MAX_TITLE = 180
MAX_DESCRIPTION = 5000
MAX_SUMMARY = 500
MAX_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 20
CRITICAL_CATEGORIES = {"safety", "security", "track"}
PUBLIC_STATUSES = {"verified", "monitoring", "resolved", "stale"}
