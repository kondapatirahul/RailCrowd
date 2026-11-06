"""Clearly indicative fare bands for planning; never represented as official fares."""
from __future__ import annotations

FARE_MULTIPLIERS = {
    "sleeper": (1.25, 2.1),
    "3a": (2.2, 3.6),
    "3ac": (2.2, 3.6),
    "2a": (3.2, 5.1),
    "2ac": (3.2, 5.1),
    "1a": (5.0, 8.0),
    "cc": (1.8, 3.0),
    "chair car": (1.8, 3.0),
    "general": (0.65, 1.1),
    "unreserved": (0.65, 1.1),
}
BASE_RATE_PER_KM = 0.42
MINIMUM_FARE = 30


def estimate_leg_fare(duration_minutes: int, coach_preference: str | None = None,
                      distance_km: int | None = None) -> dict:
    """Return a broad planning estimate based on time when distance is absent.

    The estimator deliberately exposes its uncertainty and does not attempt to
    mimic an official railway tariff, concessions, dynamic pricing, or taxes.
    """
    distance = distance_km if distance_km and distance_km > 0 else max(20, round(duration_minutes * 0.72))
    key = (coach_preference or "sleeper").strip().lower()
    low_factor, high_factor = FARE_MULTIPLIERS.get(key, FARE_MULTIPLIERS["sleeper"])
    base = max(MINIMUM_FARE, distance * BASE_RATE_PER_KM)
    low = round(base * low_factor / 10) * 10
    high = max(low, round(base * high_factor / 10) * 10)
    return {
        "low": int(low), "high": int(high), "currency": "INR",
        "distance_basis_km": int(distance),
        "method": "indicative distance-and-coach planning band",
        "official": False,
        "disclaimer": "Not an official fare quote. Check the railway booking service for current fares, quotas, concessions and availability.",
    }


def estimate_journey_fare(legs: list[dict], passengers: int = 1,
                          coach_preference: str | None = None) -> dict:
    bands = [estimate_leg_fare(leg.get("duration_minutes", 0), coach_preference, leg.get("distance_km")) for leg in legs]
    low = sum(item["low"] for item in bands) * passengers
    high = sum(item["high"] for item in bands) * passengers
    return {
        "low": low, "high": high, "per_passenger_low": low // max(1, passengers),
        "per_passenger_high": high // max(1, passengers), "passengers": passengers,
        "currency": "INR", "official": False, "legs": bands,
        "disclaimer": "Planning estimate only; not an official railway fare or ticket quote.",
    }

