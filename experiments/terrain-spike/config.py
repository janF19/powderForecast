"""Static configuration for the freeride terrain spike."""
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"
OUTPUT = BASE / "output"
OSM_DIR = DATA / "openskimap"
DEM_DIR = DATA / "dem"
LIDAR_DIR = DATA / "lidar"

OPENSKIMAP = {
    "ski_areas": "https://tiles.openskimap.org/geojson/ski_areas.geojson",
    "runs": "https://tiles.openskimap.org/geojson/runs.geojson",
    "lifts": "https://tiles.openskimap.org/geojson/lifts.geojson",
}

RESORTS = [
    {"key": "schladming",  "name_hints": ["Schladming", "Planai", "Hochwurzen"],
     "search_lonlat": (13.69, 47.39), "province": "Styria",
     "expected_freeride": "low"},
    {"key": "st_anton",    "name_hints": ["St. Anton", "Sankt Anton", "Arlberg"],
     "search_lonlat": (10.26, 47.13), "province": "Tyrol",
     "expected_freeride": "high"},
    {"key": "lech_zuers",  "name_hints": ["Lech", "Zürs", "Zuers"],
     "search_lonlat": (10.14, 47.21), "province": "Vorarlberg",
     "expected_freeride": "high"},
]

SLOPE_MIN, SLOPE_MAX = 30.0, 45.0
VERTICAL_CAP_M = 1500.0
WEIGHTS = {"S": 0.5, "A": 0.3, "V": 0.2}
ASPECT_FLOOR = 0.3

FREERIDE_TAGS = {"difficulty": "freeride", "grooming": "backcountry"}


def utm_epsg(lon: float, lat: float) -> int:
    """EPSG code of the UTM zone containing (lon, lat). Northern hemisphere."""
    zone = int((lon + 180) / 6) + 1
    return (32600 if lat >= 0 else 32700) + zone
