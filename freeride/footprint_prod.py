"""Load OpenSkiMap ski-area polygon by exact name match (production, no seed coords)."""
import json
import requests
from shapely.geometry import shape
from freeride.config import OPENSKIMAP, OSM_DIR


def _download(name):
    OSM_DIR.mkdir(parents=True, exist_ok=True)
    dest = OSM_DIR / f"{name}.geojson"
    if dest.exists():
        return dest
    print(f"Downloading {name}.geojson ...")
    with requests.get(OPENSKIMAP[name], stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return dest


def _load_ski_areas():
    path = _download("ski_areas")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {
        feat["properties"].get("name"): feat
        for feat in data["features"]
        if feat.get("properties", {}).get("name")
    }


_AREAS_CACHE = None


def get_polygon(ski_area_name: str):
    """Return (shapely_polygon, bbox) for the named ski area, or (None, None)."""
    global _AREAS_CACHE
    if _AREAS_CACHE is None:
        _AREAS_CACHE = _load_ski_areas()
    feat = _AREAS_CACHE.get(ski_area_name)
    if feat is None:
        return None, None
    poly = shape(feat["geometry"])
    if poly.geom_type == "Point":
        poly = poly.buffer(0.1)
    return poly, poly.bounds
