# Freeride Terrain Spike

Throwaway feasibility experiment. See
`docs/superpowers/specs/2026-06-15-freeride-terrain-spike-design.md`.

## Run

    python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    python run_all.py

Outputs land in `output/`.

## Austrian 1m LiDAR (bare-earth DTM) sources

Download a DTM tile covering each resort, clip to the footprint bbox, reproject
to the resort's UTM zone, and save as `data/lidar/<key>_lidar.tif`.

- Schladming (Styria): GIS Steiermark / data.gv.at — "ALS DGM 1m"
  https://www.data.gv.at/  (search "Digitales Geländemodell Steiermark")
- St. Anton (Tyrol): data.tirol.gv.at — "DGM Tirol 1m"
  https://www.data.gv.at/  (search "Geländemodell Tirol")
- Lech/Zürs (Vorarlberg): data.vorarlberg.gv.at — "DGM Vorarlberg 1m"
  https://www.data.gv.at/  (search "Geländemodell Vorarlberg")

Aggregated fallback: Sonny's Alpine LiDAR DTMs — https://sonny.4lima.de/

If a province cannot be sourced quickly, skip it: the pipeline falls back to
Copernicus 30m and Gate 2 is "not evaluated" for that resort.

## LiDAR Status (per-province)

| Province | Resort | Status | Reason |
|---|---|---|---|
| Styria | schladming | skipped | data.gv.at requires manual tile selection; no direct API for bounding-box download |
| Tyrol | st_anton | skipped | data.tirol.gv.at requires manual tile selection; files >500 MB each |
| Vorarlberg | lech_zuers | skipped | data.vorarlberg.gv.at requires manual download form |

Gate 2 (resolution comparison) is **not evaluated** — pipeline runs on Copernicus 30m only.

## Results

_(filled in by the final task)_
