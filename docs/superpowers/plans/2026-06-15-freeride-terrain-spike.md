# Freeride Terrain Spike Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a throwaway experiment that scores three Austrian resorts' freeride terrain from open DEM data and answers go/no-go on whether DEM-derived freeride scoring has real signal.

**Architecture:** Self-contained Python package under `experiments/terrain-spike/`. Pipeline: OpenSkiMap polygons (footprint) → clip Copernicus 30 m + Austrian 1 m LiDAR DEMs → compute slope/aspect/vertical → score (S/A/V + combined) → comparison table + validation maps. Nothing wires into the production app.

**Tech Stack:** Python 3, `rasterio`, `numpy`, `shapely`, `geopandas`, `pyproj`, `matplotlib`, `requests`, `ijson`. DEMs via Copernicus AWS COGs (`/vsicurl` windowed reads) and provincial Austrian LiDAR. Geometry via OpenSkiMap GeoJSON (ODbL).

**Spec:** `docs/superpowers/specs/2026-06-15-freeride-terrain-spike-design.md`

**Verified facts (probed 2026-06-15):**
- OpenSkiMap GeoJSON live at `https://tiles.openskimap.org/geojson/{ski_areas,runs,lifts}.geojson` (chunked; ski_areas is small, runs/lifts are large → stream-filter).
- Copernicus GLO-30 COGs live at `https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N{LAT}_00_E{LON}_00_DEM/Copernicus_DSM_COG_10_N{LAT}_00_E{LON}_00_DEM.tif` — Cloud-Optimized GeoTIFF, supports range/windowed reads, no auth.

---

## File Structure

All paths under `experiments/terrain-spike/`:

- `requirements.txt` — pinned spike dependencies
- `.gitignore` — ignore `data/` and `output/` (large/generated)
- `README.md` — what this is, how to run, results section (filled in last task)
- `config.py` — the 3 resorts (search coords + OSM name hints), constants (slope band, aspect weights, S/A/V weights, vertical cap, UTM helper), paths
- `footprint.py` — download + filter OpenSkiMap → per-resort polygon + runs/lifts + freeride-tagged run subset
- `terrain.py` — **pure**: slope + aspect from a DEM array (the one real TDD unit)
- `score.py` — **pure**: S/A/V + combined index from slope/aspect/elevation + mask
- `dem_fetch.py` — fetch + clip + reproject Copernicus and Austrian LiDAR DEMs per resort
- `report.py` — comparison table (CSV + markdown), histograms, hillshade/slope PNGs with freeride overlay
- `run_all.py` — orchestrator calling the pipeline end to end
- `tests/test_terrain.py` — synthetic-ramp sanity tests for `terrain.py`
- `tests/test_score.py` — synthetic-raster tests for `score.py`
- `data/` — gitignored cache (OpenSkiMap GeoJSON, DEM clips, LiDAR)
- `output/` — gitignored generated tables and PNGs

---

## Task 1: Scaffold the spike package

**Files:**
- Create: `experiments/terrain-spike/requirements.txt`
- Create: `experiments/terrain-spike/.gitignore`
- Create: `experiments/terrain-spike/config.py`
- Create: `experiments/terrain-spike/README.md`

- [ ] **Step 1: Create `requirements.txt`**

```
rasterio==1.3.10
numpy==1.26.4
shapely==2.0.4
geopandas==0.14.4
pyproj==3.6.1
matplotlib==3.8.4
requests==2.32.3
ijson==3.3.0
pytest==8.2.2
```

- [ ] **Step 2: Create `.gitignore`**

```
data/
output/
__pycache__/
*.pyc
.venv/
```

- [ ] **Step 3: Create `config.py`**

```python
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

# Resorts under test. search_lonlat seeds the nearest-area match;
# name_hints disambiguates by name. province drives the LiDAR source.
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

# Score constants (from spec).
SLOPE_MIN, SLOPE_MAX = 30.0, 45.0          # freeride sweet-spot band, degrees
VERTICAL_CAP_M = 1500.0                      # vertical drop normalization cap
WEIGHTS = {"S": 0.5, "A": 0.3, "V": 0.2}     # combined index weights
ASPECT_FLOOR = 0.3                            # south-facing aspect weight floor

# OSM tags that mark off-piste / freeride runs (validation overlay only).
FREERIDE_TAGS = {"difficulty": "freeride", "grooming": "backcountry"}


def utm_epsg(lon: float, lat: float) -> int:
    """EPSG code of the UTM zone containing (lon, lat). Northern hemisphere."""
    zone = int((lon + 180) / 6) + 1
    return (32600 if lat >= 0 else 32700) + zone
```

- [ ] **Step 4: Create `README.md` skeleton**

```markdown
# Freeride Terrain Spike

Throwaway feasibility experiment. See
`docs/superpowers/specs/2026-06-15-freeride-terrain-spike-design.md`.

## Run

    python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python run_all.py

Outputs land in `output/`.

## Results

_(filled in by the final task)_
```

- [ ] **Step 5: Verify the environment installs**

Run (from `experiments/terrain-spike/`):
```bash
python -m venv .venv && . .venv/Scripts/activate && pip install -r requirements.txt
```
Expected: all packages install without error; `python -c "import rasterio, geopandas, shapely, ijson"` prints nothing and exits 0.

- [ ] **Step 6: Commit**

```bash
git add experiments/terrain-spike/requirements.txt experiments/terrain-spike/.gitignore experiments/terrain-spike/config.py experiments/terrain-spike/README.md
git commit -m "chore(spike): scaffold freeride terrain spike package"
```

---

## Task 2: `terrain.py` — slope & aspect (the real TDD unit)

**Files:**
- Create: `experiments/terrain-spike/terrain.py`
- Test: `experiments/terrain-spike/tests/test_terrain.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_terrain.py`:
```python
import numpy as np
from terrain import slope_aspect

PX = 10.0  # metres per pixel

def test_flat_terrain_is_zero_slope():
    dem = np.full((20, 20), 1000.0)
    slope, aspect = slope_aspect(dem, PX)
    assert np.allclose(slope, 0.0, atol=1e-6)

def test_east_facing_30deg_ramp():
    # z rises toward the east (increasing column). Uphill = east, downhill = west.
    cols = np.arange(20)
    dem = np.tile(cols * PX * np.tan(np.radians(30)), (20, 1))
    slope, aspect = slope_aspect(dem, PX)
    inner = slope[1:-1, 1:-1]
    assert np.allclose(inner, 30.0, atol=0.5)
    assert np.allclose(aspect[1:-1, 1:-1], 270.0, atol=1.0)  # downhill = west

def test_north_facing_30deg_ramp():
    # z rises toward the north (row 0 = north, so z decreases with row index).
    rows = np.arange(20)
    col = (rows.max() - rows) * PX * np.tan(np.radians(30))
    dem = np.tile(col.reshape(-1, 1), (1, 20))
    slope, aspect = slope_aspect(dem, PX)
    inner = slope[1:-1, 1:-1]
    assert np.allclose(inner, 30.0, atol=0.5)
    assert np.allclose(aspect[1:-1, 1:-1], 180.0, atol=1.0)  # downhill = south
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd experiments/terrain-spike && python -m pytest tests/test_terrain.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'terrain'` (or `ImportError: slope_aspect`).

- [ ] **Step 3: Write `terrain.py`**

```python
"""Pure slope/aspect computation from a north-up DEM array."""
import numpy as np


def slope_aspect(dem, pixel_size_m):
    """Return (slope_deg, aspect_deg) for a north-up DEM.

    Array convention: axis 0 = rows north->south, axis 1 = cols west->east.
    Aspect is the compass bearing (0=N, 90=E, 180=S, 270=W) of the downhill
    (steepest-descent) direction; NaN where slope is ~0.
    """
    dem = np.asarray(dem, dtype="float64")
    d_drow, d_dcol = np.gradient(dem, pixel_size_m)
    dz_dx = d_dcol          # gradient toward east
    dz_dy = -d_drow         # gradient toward north (rows run north->south)

    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))

    # Downhill direction = -gradient. Bearing from north, clockwise.
    bearing = np.degrees(np.arctan2(-dz_dx, -dz_dy))  # atan2(east, north)
    aspect = (bearing + 360.0) % 360.0
    aspect = np.where(slope < 1e-9, np.nan, aspect)
    return slope, aspect
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd experiments/terrain-spike && python -m pytest tests/test_terrain.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add experiments/terrain-spike/terrain.py experiments/terrain-spike/tests/test_terrain.py
git commit -m "feat(spike): slope/aspect computation with synthetic-ramp tests"
```

---

## Task 3: `score.py` — S/A/V + combined index (pure, tested)

**Files:**
- Create: `experiments/terrain-spike/score.py`
- Test: `experiments/terrain-spike/tests/test_score.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_score.py`:
```python
import numpy as np
from score import aspect_weight, terrain_score

def test_aspect_weight_north_is_one_south_is_floor():
    assert abs(aspect_weight(np.array([0.0]))[0] - 1.0) < 1e-9
    assert abs(aspect_weight(np.array([180.0]))[0] - 0.3) < 1e-9
    # East/west sit between floor and 1.
    ew = aspect_weight(np.array([90.0]))[0]
    assert 0.3 < ew < 1.0

def test_terrain_score_all_in_sweet_spot_north_facing():
    slope = np.full((10, 10), 35.0)        # all in 30-45 band
    aspect = np.full((10, 10), 0.0)        # all north-facing -> A = 1.0
    elev = np.zeros((10, 10)); elev[0, 0] = 1500.0  # vertical = cap -> V = 1.0
    mask = np.ones((10, 10), dtype=bool)
    out = terrain_score(slope, aspect, elev, mask)
    assert abs(out["S"] - 1.0) < 1e-9
    assert abs(out["A"] - 1.0) < 1e-9
    assert abs(out["V"] - 1.0) < 1e-9
    assert abs(out["combined"] - 100.0) < 1e-6

def test_terrain_score_flat_terrain_scores_low():
    slope = np.full((10, 10), 5.0)         # nothing in sweet spot
    aspect = np.full((10, 10), 180.0)
    elev = np.full((10, 10), 1000.0)       # no vertical
    mask = np.ones((10, 10), dtype=bool)
    out = terrain_score(slope, aspect, elev, mask)
    assert out["S"] == 0.0
    assert out["combined"] < 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd experiments/terrain-spike && python -m pytest tests/test_score.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'score'`.

- [ ] **Step 3: Write `score.py`**

```python
"""Pure freeride score: slope sweet-spot share, aspect quality, vertical drop."""
import numpy as np
from config import SLOPE_MIN, SLOPE_MAX, VERTICAL_CAP_M, WEIGHTS, ASPECT_FLOOR


def aspect_weight(aspect_deg):
    """Powder-retention weight: N=1.0, S=floor, E/W between. NaN-safe."""
    rad = np.radians(aspect_deg)
    return ASPECT_FLOOR + (1.0 - ASPECT_FLOOR) * (1.0 + np.cos(rad)) / 2.0


def terrain_score(slope, aspect, elevation, mask):
    """Compute S, A, V and the combined index over masked pixels."""
    s = slope[mask]
    a = aspect[mask]
    e = elevation[mask]
    valid = ~np.isnan(s) & ~np.isnan(e)
    n = int(valid.sum())
    if n == 0:
        return {"S": 0.0, "A": 0.0, "V": 0.0, "combined": 0.0, "n_pixels": 0}

    sweet = valid & (s >= SLOPE_MIN) & (s <= SLOPE_MAX)
    S = float(sweet.sum()) / n

    if sweet.any():
        A = float(np.nanmean(aspect_weight(a[sweet])))
    else:
        A = 0.0

    drop = float(np.nanmax(e[valid]) - np.nanmin(e[valid]))
    V = min(drop / VERTICAL_CAP_M, 1.0)

    combined = 100.0 * (WEIGHTS["S"] * S + WEIGHTS["A"] * A + WEIGHTS["V"] * V)
    return {"S": S, "A": A, "V": V, "combined": combined, "n_pixels": n}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd experiments/terrain-spike && python -m pytest tests/test_score.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add experiments/terrain-spike/score.py experiments/terrain-spike/tests/test_score.py
git commit -m "feat(spike): S/A/V freeride score with unit tests"
```

---

## Task 4: `footprint.py` — OpenSkiMap polygons + runs/lifts

**Files:**
- Create: `experiments/terrain-spike/footprint.py`

This task is exploratory (external data), so it is verified by running and inspecting output, not by unit tests. The `ski_areas` file is small enough to load whole; `runs`/`lifts` are large, so stream-filter them by bounding box with `ijson`.

- [ ] **Step 1: Write `footprint.py`**

```python
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
        poly = shape(chosen["geometry"])
        bbox = poly.bounds
        runs = list(_stream_features_in_bbox("runs", bbox))
        freeride = [r for r in runs if _is_freeride(r.get("properties", {}))]
        lifts = list(_stream_features_in_bbox("lifts", bbox))
        print(f"   -> chose {chosen_name!r}: {len(runs)} runs "
              f"({len(freeride)} freeride), {len(lifts)} lifts")
        result[resort["key"]] = {
            "name": chosen_name, "polygon": poly, "bbox": bbox,
            "runs": runs, "freeride_runs": freeride, "lifts": lifts,
        }
    return result


if __name__ == "__main__":
    fps = build_footprints()
    for k, v in fps.items():
        print(f"{k}: {v['name']} bbox={tuple(round(b, 3) for b in v['bbox'])}")
```

- [ ] **Step 2: Run it and inspect the chosen areas**

Run: `cd experiments/terrain-spike && python footprint.py`
Expected: for each resort, a candidate list prints and the chosen area name is sensible — `schladming` → a Schladming/Planai area, `st_anton` → St. Anton am Arlberg, `lech_zuers` → Lech/Zürs. Each reports a non-zero run and lift count.

- [ ] **Step 3: If a wrong area is chosen, correct the hints**

If the printed choice is wrong (e.g. a neighboring area), tighten `name_hints` or narrow `search_lonlat` in `config.py` and re-run Step 2 until all three resolve correctly. Record the final chosen names in a comment at the top of `footprint.py`.

- [ ] **Step 4: Commit**

```bash
git add experiments/terrain-spike/footprint.py experiments/terrain-spike/config.py
git commit -m "feat(spike): resolve resort footprints + runs/lifts from OpenSkiMap"
```

---

## Task 5: `dem_fetch.py` — Copernicus GLO-30 clip & reproject

**Files:**
- Create: `experiments/terrain-spike/dem_fetch.py`

- [ ] **Step 1: Write `dem_fetch.py` (Copernicus path)**

```python
"""Fetch + clip + reproject DEMs to per-resort metric-CRS GeoTIFFs."""
import math
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.windows import from_bounds
from config import DEM_DIR, LIDAR_DIR, utm_epsg

COP_URL = ("https://copernicus-dem-30m.s3.amazonaws.com/"
           "Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM/"
           "Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM.tif")


def _cop_tiles(bbox):
    """1-degree tile URLs covering bbox (minx,miny,maxx,maxy)."""
    minx, miny, maxx, maxy = bbox
    urls = []
    for lat in range(math.floor(miny), math.floor(maxy) + 1):
        for lon in range(math.floor(minx), math.floor(maxx) + 1):
            urls.append(COP_URL.format(lat=lat, lon=lon))
    return urls


def _read_clip_4326(urls, bbox):
    """Windowed-read each COG over /vsicurl, mosaic into one array (EPSG:4326)."""
    arrays, transforms = [], []
    for url in urls:
        with rasterio.open(f"/vsicurl/{url}") as src:
            win = from_bounds(*bbox, transform=src.transform)
            data = src.read(1, window=win)
            transforms.append(src.window_transform(win))
            arrays.append(data)
            profile = src.profile
    # Single-tile common case: return directly. Multi-tile resorts here all fit
    # one tile (verified bboxes), so assert and use the first.
    assert len(arrays) == 1, f"multi-tile bbox not handled: {len(arrays)} tiles"
    return arrays[0], transforms[0], profile


def _reproject_to_utm(arr, transform, src_profile, dst_epsg, dest):
    dst_crs = rasterio.crs.CRS.from_epsg(dst_epsg)
    h, w = arr.shape
    dst_transform, dw, dh = calculate_default_transform(
        src_profile["crs"], dst_crs, w, h,
        *rasterio.transform.array_bounds(h, w, transform))
    dst = np.empty((dh, dw), dtype="float32")
    reproject(arr, dst, src_transform=transform, src_crs=src_profile["crs"],
              dst_transform=dst_transform, dst_crs=dst_crs,
              resampling=Resampling.bilinear)
    DEM_DIR.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dest, "w", driver="GTiff", height=dh, width=dw, count=1,
                       dtype="float32", crs=dst_crs, transform=dst_transform,
                       nodata=src_profile.get("nodata")) as out:
        out.write(dst, 1)
    return dest


def fetch_copernicus(resort_key, bbox, center_lonlat):
    """Clip Copernicus 30 m to bbox, reproject to local UTM, save GeoTIFF."""
    dest = DEM_DIR / f"{resort_key}_cop30.tif"
    if dest.exists():
        return dest
    arr, transform, profile = _read_clip_4326(_cop_tiles(bbox), bbox)
    epsg = utm_epsg(*center_lonlat)
    return _reproject_to_utm(arr, transform, profile, epsg, dest)


def load_lidar(resort_key):
    """Return a pre-downloaded Austrian LiDAR clip if present, else None.

    Expected file (manually placed, see README): data/lidar/<key>_lidar.tif,
    already in a metric CRS. Acquisition is documented in dem_fetch README notes.
    """
    path = LIDAR_DIR / f"{resort_key}_lidar.tif"
    return path if path.exists() else None
```

- [ ] **Step 2: Smoke-test the Copernicus fetch on one resort**

Run:
```bash
cd experiments/terrain-spike && python -c "
from footprint import build_footprints
from dem_fetch import fetch_copernicus
import rasterio
fps = build_footprints()
r = fps['schladming']
p = fetch_copernicus('schladming', r['bbox'], r['polygon'].centroid.coords[0])
with rasterio.open(p) as s:
    a = s.read(1); print(p.name, s.crs, a.shape, 'elev', float(a.min()), float(a.max()))
"
```
Expected: a GeoTIFF in a UTM CRS (EPSG:326xx); elevation min/max in a plausible alpine range (roughly 600–2800 m for Schladming). If `multi-tile bbox not handled` asserts, extend `_read_clip_4326` to mosaic — but the three verified bboxes each fit one tile.

- [ ] **Step 3: Commit**

```bash
git add experiments/terrain-spike/dem_fetch.py
git commit -m "feat(spike): Copernicus 30m clip + UTM reproject, LiDAR loader stub"
```

---

## Task 6: Austrian 1 m LiDAR acquisition (friction task)

**Files:**
- Modify: `experiments/terrain-spike/README.md` (add LiDAR sourcing notes)
- Create: `experiments/terrain-spike/data/lidar/<key>_lidar.tif` (manually placed, gitignored)

LiDAR is the spike's biggest risk (three provincial portals, no uniform API). This task acquires bare-earth 1 m DTM clips for each resort and drops them into `data/lidar/`. **Fallback:** if acquisition stalls for a province, leave that file absent — `load_lidar` returns `None`, the pipeline runs on Copernicus alone, and Gate 2 (resolution) is marked "not evaluated" for that resort rather than blocking the spike.

- [ ] **Step 1: Document the provincial sources in README**

Add to `README.md`:
```markdown
## Austrian 1 m LiDAR (bare-earth DTM) sources

Download a DTM tile covering each resort, clip to the footprint bbox, reproject
to the resort's UTM zone, and save as `data/lidar/<key>_lidar.tif`.

- Schladming (Styria): GIS Steiermark / data.gv.at — "ALS DGM 1 m"
  https://www.data.gv.at/  (search "Digitales Geländemodell Steiermark")
- St. Anton (Tyrol): data.tirol.gv.at — "DGM Tirol 1 m"
  https://www.data.gv.at/  (search "Geländemodell Tirol")
- Lech/Zürs (Vorarlberg): data.vorarlberg.gv.at — "DGM Vorarlberg 1 m"
  https://www.data.gv.at/  (search "Geländemodell Vorarlberg")

Aggregated fallback: Sonny's Alpine LiDAR DTMs — https://sonny.4lima.de/

If a province cannot be sourced quickly, skip it: the pipeline falls back to
Copernicus 30 m and Gate 2 is "not evaluated" for that resort.
```

- [ ] **Step 2: Acquire + clip at least one LiDAR DTM**

Download a DTM covering one resort (Schladming is the priority — it is the low-freeride control). Clip to the footprint bbox and reproject to its UTM zone using the same `_reproject_to_utm` helper, saving to `data/lidar/schladming_lidar.tif`. Attempt all three; record per-province status (acquired / skipped) in the README results section.

- [ ] **Step 3: Verify each acquired LiDAR clip**

Run:
```bash
cd experiments/terrain-spike && python -c "
import rasterio, glob
for p in sorted(glob.glob('data/lidar/*_lidar.tif')):
    with rasterio.open(p) as s:
        a = s.read(1); print(p, s.crs, a.shape, float(a.min()), float(a.max()))
"
```
Expected: each acquired file is in a UTM CRS with a plausible alpine elevation range and ~1 m pixel size (`s.res` ≈ (1, 1)).

- [ ] **Step 4: Commit the README notes (DTM files stay gitignored)**

```bash
git add experiments/terrain-spike/README.md
git commit -m "docs(spike): Austrian LiDAR sourcing notes + per-province status"
```

---

## Task 7: `report.py` — masking, scoring per tier, table + maps

**Files:**
- Create: `experiments/terrain-spike/report.py`

- [ ] **Step 1: Write `report.py`**

```python
"""Score each resort per DEM tier and emit table + validation maps."""
import csv
import numpy as np
import rasterio
from rasterio.features import rasterize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.ops import transform as shp_transform
from pyproj import Transformer
from shapely.geometry import shape
from config import OUTPUT, utm_epsg
from terrain import slope_aspect
from score import terrain_score


def _polygon_mask(poly_4326, src):
    """Rasterize a lon/lat polygon onto src's grid (src is metric/UTM)."""
    epsg = src.crs.to_epsg()
    tf = Transformer.from_crs(4326, epsg, always_xy=True).transform
    poly_m = shp_transform(tf, poly_4326)
    return rasterize([(poly_m, 1)], out_shape=(src.height, src.width),
                     transform=src.transform, fill=0, dtype="uint8").astype(bool)


def score_resort(dem_path, poly_4326):
    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype("float64")
        nodata = src.nodata
        if nodata is not None:
            dem[dem == nodata] = np.nan
        px = abs(src.transform.a)
        mask = _polygon_mask(poly_4326, src)
    slope, aspect = slope_aspect(dem, px)
    return terrain_score(slope, aspect, dem, mask), (dem, slope, mask)


def _hillshade(dem, px):
    dy, dx = np.gradient(dem, px)
    slope = np.pi / 2 - np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    az, alt = np.radians(315), np.radians(45)
    hs = (np.sin(alt) * np.sin(slope) +
          np.cos(alt) * np.cos(slope) * np.cos(az - aspect))
    return hs


def save_map(resort_key, tier, dem, slope, mask, freeride_runs, src_crs):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    px = 1.0
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.imshow(_hillshade(dem, px), cmap="gray")
    sweet = np.where(mask & (slope >= 30) & (slope <= 45), slope, np.nan)
    ax.imshow(sweet, cmap="autumn", alpha=0.6, vmin=30, vmax=45)
    ax.set_title(f"{resort_key} — {tier}\nred = 30-45° lift-served terrain")
    ax.axis("off")
    fig.savefig(OUTPUT / f"{resort_key}_{tier}_slopemap.png", dpi=120,
                bbox_inches="tight")
    plt.close(fig)


def save_histograms(resort_key, tier, slope, mask):
    vals = slope[mask & ~np.isnan(slope)]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(vals, bins=np.arange(0, 70, 2))
    ax.axvspan(30, 45, color="orange", alpha=0.3, label="sweet spot")
    ax.set_xlabel("slope (deg)"); ax.set_ylabel("pixels")
    ax.set_title(f"{resort_key} — {tier} slope distribution"); ax.legend()
    fig.savefig(OUTPUT / f"{resort_key}_{tier}_slopehist.png", dpi=120,
                bbox_inches="tight")
    plt.close(fig)


def write_table(rows):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fields = ["resort", "tier", "S", "A", "V", "combined", "n_pixels"]
    with open(OUTPUT / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})
    with open(OUTPUT / "results.md", "w") as f:
        f.write("| " + " | ".join(fields) + " |\n")
        f.write("|" + "|".join("---" for _ in fields) + "|\n")
        for r in rows:
            f.write("| " + " | ".join(
                f"{r[k]:.3f}" if isinstance(r[k], float) else str(r[k])
                for k in fields) + " |\n")
```

- [ ] **Step 2: Commit**

```bash
git add experiments/terrain-spike/report.py
git commit -m "feat(spike): scoring, comparison table, slope maps + histograms"
```

---

## Task 8: `run_all.py` — orchestrate the pipeline

**Files:**
- Create: `experiments/terrain-spike/run_all.py`

- [ ] **Step 1: Write `run_all.py`**

```python
"""End-to-end: footprints -> DEM clips -> scores -> table + maps."""
import rasterio
from footprint import build_footprints
from dem_fetch import fetch_copernicus, load_lidar
from report import score_resort, save_map, save_histograms, write_table


def main():
    fps = build_footprints()
    rows = []
    for key, fp in fps.items():
        poly = fp["polygon"]
        center = poly.centroid.coords[0]
        tiers = {}
        tiers["cop30"] = fetch_copernicus(key, fp["bbox"], center)
        lidar = load_lidar(key)
        if lidar:
            tiers["lidar1m"] = lidar
        for tier, path in tiers.items():
            scores, (dem, slope, mask) = score_resort(path, poly)
            with rasterio.open(path) as src:
                crs = src.crs
            save_map(key, tier, dem, slope, mask, fp["freeride_runs"], crs)
            save_histograms(key, tier, slope, mask)
            rows.append({"resort": key, "tier": tier, **scores})
            print(f"{key:12s} {tier:8s} "
                  f"S={scores['S']:.3f} A={scores['A']:.3f} "
                  f"V={scores['V']:.3f} combined={scores['combined']:.1f}")
    write_table(rows)
    print("\nWrote output/results.csv, output/results.md and PNG maps.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full pipeline**

Run: `cd experiments/terrain-spike && python run_all.py`
Expected: prints an S/A/V/combined line per resort per available tier; writes `output/results.csv`, `output/results.md`, and per-resort slope-map + histogram PNGs. No exceptions.

- [ ] **Step 3: Commit**

```bash
git add experiments/terrain-spike/run_all.py
git commit -m "feat(spike): end-to-end orchestrator for the terrain spike"
```

---

## Task 9: Interpret results & record the go/no-go

**Files:**
- Modify: `experiments/terrain-spike/README.md` (Results section)

- [ ] **Step 1: Inspect outputs against the two gates**

Open `output/results.md` and the PNGs. Evaluate:
- **Gate 1 (signal):** do St. Anton and Lech have a higher `combined` score — and especially higher `S` — than Schladming, on **every** tier present? Confirm the slope maps visually show more 30–45° terrain at the Arlberg resorts.
- **Gate 2 (cost):** where both `cop30` and `lidar1m` exist, how large is the per-component delta? Small delta → 30 m scales; large delta where only LiDAR ranks them correctly → high-res required.
- **OSM overlay cross-check:** confirm freeride-tagged runs (where present) fall on red sweet-spot terrain in the maps.

- [ ] **Step 2: Write the verdict into the README Results section**

Fill the `## Results` section with: the final results table (paste from `results.md`), which chosen OpenSkiMap area each resort resolved to, per-province LiDAR status, the Gate 1 verdict (signal: yes/no), the Gate 2 verdict (30 m good enough: yes/no/not-evaluated), and a one-paragraph **go / no-go recommendation** for building the freeride score across all 294 resorts.

- [ ] **Step 3: Run the full test suite once more**

Run: `cd experiments/terrain-spike && python -m pytest -v`
Expected: all `test_terrain.py` and `test_score.py` tests pass.

- [ ] **Step 4: Commit**

```bash
git add experiments/terrain-spike/README.md
git commit -m "docs(spike): record terrain spike results and go/no-go verdict"
```

---

## Self-Review Notes

- **Spec coverage:** footprint (Task 4), core S/A/V score with documented weights (Task 3), Copernicus + LiDAR tiers (Tasks 5–6), comparison table + histograms + hillshade maps (Task 7), Gate 1/Gate 2 sequential go/no-go (Task 9), OSM freeride-tag validation overlay (Tasks 4 + 7 + 9), one-sanity-test-not-full-TDD for terrain math plus a score unit test (Tasks 2–3), treeline explicitly deferred. All spec sections map to a task.
- **LiDAR friction** is isolated to Task 6 with an explicit fallback so it cannot block the spike.
- **Type consistency:** `slope_aspect(dem, pixel_size_m) -> (slope, aspect)` and `terrain_score(slope, aspect, elevation, mask) -> {S,A,V,combined,n_pixels}` are used consistently across `report.py` and `run_all.py`; `build_footprints()` returns the `{polygon,bbox,runs,freeride_runs,lifts,name}` shape consumed by `run_all.py`.
