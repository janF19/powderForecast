from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"
OSM_DIR = DATA / "openskimap"
DEM_DIR = DATA / "dem"

OPENSKIMAP = {
    "ski_areas": "https://tiles.openskimap.org/geojson/ski_areas.geojson",
    "runs": "https://tiles.openskimap.org/geojson/runs.geojson",
    "lifts": "https://tiles.openskimap.org/geojson/lifts.geojson",
}

SLOPE_MIN, SLOPE_MAX = 30.0, 45.0
VERTICAL_CAP_M = 1500.0
WEIGHTS = {"S": 0.5, "A": 0.3, "V": 0.2}
ASPECT_FLOOR = 0.3

WEATHER_JSON = BASE.parent / "weather_dataFull_7.json"
TERRAIN_JSON = BASE.parent / "freeride_terrain.json"
MATCHES_JSON = DATA / "resort_matches.json"
OVERRIDES_JSON = DATA / "resort_overrides.json"


def utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180) / 6) + 1
    return (32600 if lat >= 0 else 32700) + zone
