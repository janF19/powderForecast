# Chosen area names (verified 2026-06-16):
#   schladming  -> "Planai" (polygon, 111 runs [4 freeride], 19 lifts)
#   st_anton    -> "St. Anton/St. Christoph/Stuben" (point → convex hull of 1466 runs, 193 freeride, 130 lifts)
#   lech_zuers  -> "Lech/Zürs" (point → convex hull of 1691 runs, 187 freeride, 153 lifts)
"""Download OpenSkiMap GeoJSON and extract per-resort footprint + runs/lifts."""
import json
import ijson
import requests
from shapely.geometry import shape, box
from shapely.ops import unary_union
from config import OPENSKIMAP, OSM_DIR, RESORTS, FREERIDE_TAGS


def _download(name):
    OSM_DIR.mkdir(parents=True, exist_ok=True)
    dest = OSM_DIR / f"{name}.geojson"
    if dest.exists():
        return dest
    print(f"downloading {name} ...")
    with requests.get(OPENSKIMAP[name], stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return dest


def _nearest_area(features, lonlat, hints):
    """Pick the ski-area feature nearest the seed whose name matches a hint."""
    lon, lat = lonlat
    seed = box(lon - 0.05, lat - 0.05, lon + 0.05, lat + 0.05).centroid
    candidates = []
    for feat in features:
        props = feat.get("properties", {})
        name = (props.get("name") or "")
        geom = shape(feat["geometry"])
        dist = geom.distance(seed)
        matches = any(h.lower() in name.lower() for h in hints)
        candidates.append((dist, matches, name, feat))
    # Prefer name-matching areas, then nearest.
    candidates.sort(key=lambda c: (not c[1], c[0]))
    return candidates[:5]


def load_areas():
    path = _download("ski_areas")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["features"]


def _stream_features_in_bbox(name, bbox):
    """Yield features from a large GeoJSON whose geometry intersects bbox."""
    path = _download(name)
    region = box(*bbox)
    with open(path, "rb") as f:
        for feat in ijson.items(f, "features.item"):
            try:
                geom = shape(feat["geometry"])
            except Exception:
                continue
            if geom.intersects(region):
                yield feat


def _is_freeride(props):
    return any(props.get(k) == v for k, v in FREERIDE_TAGS.items())


_SEARCH_RADIUS = 0.15  # degrees; used when ski-area geometry is a point


def _search_bbox(poly, lonlat):
    """Return the bounding box to search for runs/lifts.

    If the ski-area geometry is a single point (degenerate bbox), expand by
    _SEARCH_RADIUS degrees in each direction so the stream filter finds features.
    """
    minx, miny, maxx, maxy = poly.bounds
    if abs(maxx - minx) < 1e-6 and abs(maxy - miny) < 1e-6:
        lon, lat = lonlat
        return (lon - _SEARCH_RADIUS, lat - _SEARCH_RADIUS,
                lon + _SEARCH_RADIUS, lat + _SEARCH_RADIUS)
    return poly.bounds


def build_footprints():
    """Return {resort_key: {polygon, bbox, runs, freeride_runs, lifts, name}}."""
    areas = load_areas()
    result = {}
    for resort in RESORTS:
        top5 = _nearest_area(areas, resort["search_lonlat"], resort["name_hints"])
        print(f"\n[{resort['key']}] candidates:")
        for dist, matched, name, _ in top5:
            print(f"   match={matched} dist={dist:.3f} name={name!r}")
        _, _, chosen_name, chosen = top5[0]
        raw_poly = shape(chosen["geometry"])
        search_box = _search_bbox(raw_poly, resort["search_lonlat"])
        runs = list(_stream_features_in_bbox("runs", search_box))
        freeride = [r for r in runs if _is_freeride(r.get("properties", {}))]
        lifts = list(_stream_features_in_bbox("lifts", search_box))
        # If the ski-area record is a point, build footprint from run geometries.
        if raw_poly.geom_type == "Point" and runs:
            run_geoms = []
            for r in runs:
                try:
                    run_geoms.append(shape(r["geometry"]))
                except Exception:
                    pass
            poly = unary_union(run_geoms).convex_hull if run_geoms else raw_poly.buffer(_SEARCH_RADIUS)
        else:
            poly = raw_poly
        bbox = poly.bounds
        print(f"   -> chose {chosen_name!r}: {len(runs)} runs "
              f"({len(freeride)} freeride), {len(lifts)} lifts bbox={tuple(round(b,3) for b in bbox)}")
        result[resort["key"]] = {
            "name": chosen_name, "polygon": poly, "bbox": bbox,
            "runs": runs, "freeride_runs": freeride, "lifts": lifts,
        }
    return result


if __name__ == "__main__":
    fps = build_footprints()
    for k, v in fps.items():
        print(f"{k}: {v['name']} bbox={tuple(round(b, 3) for b in v['bbox'])}")
