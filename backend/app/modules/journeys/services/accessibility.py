"""Accessibility-oriented station readiness context for a journey itinerary."""
from __future__ import annotations
from sqlalchemy import select
from backend.app.extensions import db
from backend.app.models.journey import StationFacility

RELEVANT_ACCESSIBILITY = {
    "step_free", "wheelchair_access", "tactile_path", "audio_assistance",
    "priority_queue", "accessible_restroom", "ramp", "lift_access",
}


def station_accessibility_context(station_code: str) -> dict:
    """Summarize verified and unverified community accessibility listings."""
    facilities = db.session.execute(select(StationFacility).where(
        StationFacility.station_code == station_code.upper(),
        StationFacility.is_visible.is_(True),
    )).scalars().all()
    available_tags = set()
    limited_tags = set()
    unavailable_tags = set()
    listing_count = 0
    for facility in facilities:
        tags = set(facility.accessibility_tags or []) & RELEVANT_ACCESSIBILITY
        if not tags:
            continue
        listing_count += 1
        if facility.status == "available":
            available_tags.update(tags)
        elif facility.status == "limited":
            limited_tags.update(tags)
        elif facility.status == "unavailable":
            unavailable_tags.update(tags)
    all_tags = available_tags | limited_tags | unavailable_tags
    return {
        "station_code": station_code.upper(),
        "listing_count": listing_count,
        "available_tags": sorted(available_tags),
        "limited_tags": sorted(limited_tags),
        "unavailable_tags": sorted(unavailable_tags),
        "coverage": round(len(available_tags) / len(RELEVANT_ACCESSIBILITY) * 100),
        "has_any_listing": bool(all_tags),
        "status": "community_listings_present" if all_tags else "no_accessibility_listing",
        "disclaimer": "This is not an accessibility certification. Contact the station or railway assistance service to confirm arrangements.",
    }


def itinerary_accessibility_summary(legs: list[dict], context_cache: dict | None = None) -> dict:
    station_codes = []
    for leg in legs:
        for code in (leg.get("origin_code"), leg.get("destination_code")):
            if code and code not in station_codes:
                station_codes.append(code)
    cache = context_cache if context_cache is not None else {}
    for code in station_codes:
        if code not in cache:
            cache[code] = station_accessibility_context(code)
    contexts = [cache[code] for code in station_codes]
    listed = sum(1 for item in contexts if item["has_any_listing"])
    return {
        "stations": contexts,
        "station_count": len(contexts),
        "stations_with_listings": listed,
        "coverage_percent": round(listed / len(contexts) * 100) if contexts else 0,
        "notice": "Missing listings do not mean a station is inaccessible; they mean RailCrowd has no current community information.",
    }


def accessibility_reminders(context: dict) -> list[str]:
    reminders = []
    if not context.get("has_any_listing"):
        reminders.append("Contact the station to confirm step-free access and assistance options.")
    if "lift_access" not in context.get("available_tags", []):
        reminders.append("Confirm lift availability before relying on a step-free route between platforms.")
    if "wheelchair_access" not in context.get("available_tags", []):
        reminders.append("Ask the railway assistance service about wheelchair access and boarding support.")
    if "accessible_restroom" not in context.get("available_tags", []):
        reminders.append("Check accessible restroom availability directly with station staff.")
    return reminders
