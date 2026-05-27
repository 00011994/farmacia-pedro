import math


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns great-circle distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calc_eta(
    driver_lat: float,
    driver_lon: float,
    dest_lat: float,
    dest_lon: float,
    avg_speed_kmh: float = 30.0,
) -> "tuple[float, int]":
    """Returns (distance_km, eta_minutes) using straight-line Haversine distance."""
    distance_km = haversine(driver_lat, driver_lon, dest_lat, dest_lon)
    eta_minutes = math.ceil((distance_km / avg_speed_kmh) * 60)
    return round(distance_km, 2), eta_minutes
