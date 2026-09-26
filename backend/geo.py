"""Offline US ZIP centroid lookup and straight-line distance (advisory only)."""
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt

import zipcodes


@lru_cache(maxsize=4096)
def zip_latlon(z: str) -> tuple[float, float] | None:
    z = (z or "").strip()[:5]
    if len(z) != 5 or not z.isdigit():
        return None
    hits = zipcodes.matching(z)
    if not hits or not hits[0].get("lat"):
        return None
    return float(hits[0]["lat"]), float(hits[0]["long"])


def zip_distance_miles(a: str, b: str) -> float | None:
    pa, pb = zip_latlon(a), zip_latlon(b)
    if not pa or not pb:
        return None
    lat1, lon1, lat2, lon2 = map(radians, (*pa, *pb))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return round(3958.8 * 2 * asin(sqrt(h)), 1)
