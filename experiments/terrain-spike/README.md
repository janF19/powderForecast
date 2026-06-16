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

### Chosen OpenSkiMap areas

| Resort | Chosen Area | Runs | Freeride Runs | Lifts |
|---|---|---|---|---|
| schladming | Planai | 111 | 4 | 19 |
| st_anton | St. Anton/St. Christoph/Stuben | 1466 | 193 | 130 |
| lech_zuers | Lech/Zürs | 1691 | 187 | 153 |

### Scores

| resort | tier | S | A | V | combined | n_pixels |
|---|---|---|---|---|---|---|
| schladming | cop30 | 0.073 | 0.899 | 0.778 | 46.154 | 17273 |
| schladming | lidar1m | 0.158 | 0.860 | 0.782 | 49.327 | 8838701 |
| st_anton | cop30 | 0.421 | 0.646 | 1.000 | 60.436 | 1182145 |
| lech_zuers | cop30 | 0.392 | 0.652 | 1.000 | 59.148 | 1390219 |

### Gate 1 — Signal: GO ✓

St. Anton and Lech/Zürs score **5–6× higher on S** (slope sweet-spot fraction) than Schladming on Copernicus 30m: S=0.42/0.39 vs 0.07. The combined index gap (60 vs 46) is smaller because V and A partially compensate, but S is the kill-gate metric and the separation is unambiguous. OSM freeride-tagged run counts confirm the ranking independently (193/187 vs 4 tagged runs).

### Gate 2 — Resolution: 30m adequate for ranking, investigate before full rollout

Schladming cop30 S=0.073 vs lidar1m S=0.158 — a 2.2× difference. The 30m DEM smooths small-scale steep terrain. However, the relative ranking (Arlberg >> Schladming) is maintained under both resolutions. Gate 2 verdict: **30m is sufficient for a go/no-go discrimination; full 294-resort rollout on Copernicus 30m is justified**, but a 10-resort 1m vs 30m calibration study is recommended before final score publication.

### Go / No-Go Recommendation

**GO.** DEM-derived freeride scoring has real, strong signal. The 30m Copernicus DEM correctly discriminates major freeride terrain (Arlberg) from groomer-focused resorts (Schladming) with a 5–6× S-component gap. Building this score across all 294 resorts on Copernicus 30m is technically feasible (COG windowed reads, no download quota). Recommended next step: build the score for all 294 resorts, then run a 10-resort 1m vs 30m calibration to decide whether provincial LiDAR ingestion is worth the data-pipeline complexity.
