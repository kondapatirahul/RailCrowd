"""Read-only passenger dashboard data assembly."""

from datetime import timezone


def build_passenger_dashboard(user):
    """Build a safe dashboard view model from the authenticated user.

    Contribution counts will be populated when the crowd-report module is
    introduced. Until then, the dashboard explicitly reports that no
    contribution data is available rather than inventing statistics.
    """
    created_at = getattr(user, "created_at", None)
    if created_at and created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return {
        "full_name": user.full_name,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_enabled": bool(user.is_enabled),
        "is_email_verified": bool(user.is_email_verified),
        "created_at": created_at,
        "contribution_count": None,
        "contribution_status": "Not available yet",
        "quick_actions": [
            {
                "title": "Report train crowd",
                "description": "Share a crowd update for your journey.",
                "status": "Coming soon",
            },
            {
                "title": "My contributions",
                "description": "Review the crowd updates you have submitted.",
                "status": "Coming soon",
            },
            {
                "title": "Saved trains",
                "description": "Keep frequently used trains close at hand.",
                "status": "Coming soon",
            },
        ],
    }
