

"""Geolocation helpers (geocoding + distance) for PepeBooking.

Usage:
    from services.geo import geocode_address, haversine_km

Notes:
- Uses OpenStreetMap Nominatim for geocoding ("search" endpoint).
- Provide a proper User-Agent via Flask config GEO_USER_AGENT to respect the API policy.
- Returns (lat, lon) as floats or None if not found.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

import requests
from flask import current_app


def _user_agent() -> str:
    """Return a polite User-Agent for Nominatim requests."""
    # Allow override via Flask config; otherwise use a sensible default.
    ua = current_app.config.get(
        "GEO_USER_AGENT",
        "PepeBooking/1.0 (+mailto:info@pepeshows.de)",
    )
    return ua


def geocode_address(address: str, *, timeout: float = 8.0) -> Optional[Tuple[float, float]]:
    """Geocode a free-form address to (lat, lon) using Nominatim.

    Returns None if the address is empty, not found, or the request fails.
    """
    if not address:
        return None

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": address,
                "format": "json",
                "limit": 1,
                "addressdetails": 0,
            },
            headers={"User-Agent": _user_agent()},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            current_app.logger.info(f"Geocode not found: {address}")
            return None
        lat = float(data[0]["lat"])  # type: ignore[index]
        lon = float(data[0]["lon"])  # type: ignore[index]
        return (lat, lon)
    except Exception as e:
        current_app.logger.warning(f"Geocode failed for '{address}': {e}")
        return None


def haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """Great-circle distance between two (lat, lon) points in kilometers."""
    lat1, lon1 = a
    lat2, lon2 = b
    R = 6371.0  # km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    s = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(s), math.sqrt(1 - s))


__all__ = ["geocode_address", "haversine_km"]