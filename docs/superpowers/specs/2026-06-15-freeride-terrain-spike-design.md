# Freeride Terrain Spike — Design

**Date:** 2026-06-15
**Status:** Approved (brainstorming complete, ready for implementation plan)
**Type:** Throwaway feasibility spike — nothing here ships to the 294-resort app.

## Goal & hypothesis

A throwaway experiment in `experiments/terrain-spike/` that answers one question:
**does DEM-derived freeride scoring have real signal?**

Concretely:

- **Signal:** does a score computed purely from open elevation data rank
  **St. Anton + Lech (big freeride)** clearly above **Schladming (groomer-focused)**,
  matching what a person sees by eye on the resort maps?
- **Cost:** is cheap **Copernicus GLO-30** (30 m) good enough to scale to all 294
  resorts, or do we only get usable scores where **1 m bare-earth LiDAR** exists?

This is a go/no-go probe. No code from here is wired into the production app.

## Background & prior decisions

This is sub-project 2 of the powderForecast roadmap (sub-project 1 = Powder Quality
Index, already specced/built). The vision: live conditions (PQI) × static terrain
(freeride score) = "best powder to drive to this weekend."

**Sourcing conclusion (researched 2026-06-14):** do NOT ingest crowd freeride tracks —
they are legal/technical dead ends. FATMAP shut down Oct 2024 (no API, not exportable).
Strava's Nov 2024 API terms ban AI/ML use and showing other users' data. AllTrails has
no public API. The buildable, legal stack is self-computed terrain from open DEMs +
OpenStreetMap-derived geometry. Fatmap/AllTrails/Strava are human eyeball validation
only — never in the pipeline.

**Prior art note:** [OpenSkiStats](https://github.com/dhimmel/openskistats) already
computes per-ski-area slope/aspect/vertical metrics from OSM + elevation. This
*de-risks* the pipeline (it demonstrably runs) and tells us to frame our novelty as the
**freeride-specific** angle — off-piste steep/aspect quality within the lift-served
envelope, paired with live PQI conditions — not "compute terrain stats" in general.

**Why not OSM freeride tags alone? (researched 2026-06-15)** We checked whether pulling
`piste:difficulty=freeride` tags directly would be simpler than computing terrain from a
DEM. It would be simpler — but it fails as a *primary* signal:

- `piste:difficulty=freeride` exists on only **~5,021 objects worldwide** (taginfo,
  2.25% of difficulty-tagged pistes), vs ~116,099 `piste:type=downhill` ways.
- It is a **subjective human label on specific named runs**, not a complete map of
  skiable steep terrain. A resort with zero freeride-tagged ways is not flat — it is
  *unmapped*. Across 294 resorts this produces **false zeros** and no basis for
  normalization (a well-tagged resort would beat a terrain-identical under-mapped one).

Conclusion: **the DEM computation stays the primary signal** (complete, normalizable, we
own it). The freeride / `grooming=backcountry` tags come free in the OpenSkiMap `runs`
layer, so they are used as a **near-zero-cost validation overlay** (see Outputs), not as
the score.

## The three test resorts

| Resort | Region | Province | Expected freeride character |
|---|---|---|---|
| St. Anton am Arlberg | Arlberg | Tyrol | High — major freeride terrain |
| Lech / Zürs | Arlberg | Vorarlberg | High — major freeride terrain |
| Schladming (Planai/Hochwurzen) | Ski amadé | Styria | Low/moderate — groomer-focused |

St. Anton and Lech are grouped as the freeride exemplar (both Arlberg); the test is
**Arlberg terrain ranks clearly above Schladming**. Their interconnection means we do
not depend on separating St. Anton from Lech.

## Footprint (settled)

Use **OpenSkiMap** `ski_areas` GeoJSON (ODbL — same license as raw OSM, but pre-assembled).
OpenSkiMap ingests OSM + Skimap.org and clusters lifts+runs into named ski areas with
boundary polygons, republished as daily GeoJSON (`ski_areas`, `runs`, `lifts` layers).

- Hand-select the 3 ski areas by name → one polygon per resort.
- Also pull their lifts/runs for the eyeball validation maps.
- This deletes the lift-clustering / neighbor-disambiguation problem that raw Overpass
  would force us to solve (the interconnected Arlberg areas make that hard).
- **Raw-Overpass lift hull is a documented fallback for the scale stage only**, in case
  OpenSkiMap coverage/matching is insufficient for some of the 294. Not built in the spike.

Resort centroids in `resorts_for_forecast.json` are only 2-decimal (~1 km) single points,
so they cannot define a footprint on their own — this is *why* we need polygon geometry,
not just better coordinates.

## The core score

Computed over DEM pixels inside the OpenSkiMap polygon, for **each DEM tier**.
**Reported as three separate components, not just a combined black box** — for a
feasibility spike we need to see *which* axis creates (or fails to create) the separation.

- **S — slope sweet-spot share:** fraction of pixels with slope in **30–45°**
  (the freeride / powder band; below 30° too flat, above 45° too steep/exposed).
- **A — aspect quality:** mean powder-retention weight over the sweet-spot pixels, where
  N = 1.0, NE/NW = high, E/W = mid, S ≈ 0.3 (north-facing holds powder longest).
- **V — vertical drop:** (max − min) elevation within the polygon, normalized (cap ~1500 m → 1.0).

**Combined index:** `100 · (0.5·S + 0.3·A + 0.2·V)`.

Weights are a transparent starting point; because components are reported separately, we
can see whether they need tuning. Combine S/A/V on a 0–1 normalized basis before weighting.

**Out of scope (stage-2 enrichment, not in this spike):** treeline / tree-cover (tree
skiing, bad-visibility days, avalanche framing) — needs a separate landcover raster, an
extra source and failure mode we deliberately keep out of the throwaway probe. Also out:
terrain roughness / cliff-band detection.

## Pipeline (5 small units)

Each unit has one clear purpose and a well-defined interface:

1. **`footprint.py`** — load OpenSkiMap `ski_areas` GeoJSON → select the 3 resorts →
   emit one polygon each (+ their lifts/runs for maps). Input: GeoJSON + resort names.
   Output: per-resort polygon (shapely) and lift/run geometry.

2. **`dem_fetch.py`** — fetch and clip both DEM tiers to each polygon's bbox:
   - **Copernicus GLO-30** (30 m) via AWS open data (`s3://copernicus-dem-30m/`) or
     OpenTopography API. Free, global. Note: it is a DSM (includes canopy), which can
     inflate slope below treeline — relevant to interpreting results.
   - **Austrian 1 m LiDAR bare-earth DTM** per province open data: Styria (Schladming),
     Tyrol (St. Anton), Vorarlberg (Lech/Zürs). **This is the spike's main friction /
     biggest risk** — three provincial sources, acquisition may be slow or awkward.
   Output: clipped GeoTIFF per resort per tier.

3. **`terrain.py`** — pure function on a raster: compute slope + aspect rasters via
   gradient, plus elevation min/max. No I/O dependencies beyond the array.

4. **`score.py`** — given slope/aspect/elevation rasters + polygon mask → compute
   S, A, V and the combined index.

5. **`report.py`** — produce the outputs below.

All under `experiments/terrain-spike/`, outputs to `experiments/terrain-spike/output/`.

## Outputs → the go/no-go (sequential)

1. **Comparison table:** 3 resorts × 2 DEM tiers × {S, A, V, combined}.

2. **Gate 1 — signal (the kill gate):** does the combined score, and **S** especially,
   rank Arlberg (St. Anton, Lech) above Schladming on **both** DEM tiers? No separation →
   kill the project.

3. **Gate 2 — cost (scaling decision, only if Gate 1 passes):** how close are 30 m vs 1 m
   per-component? Delta table / scatter → "30 m good enough → global rollout to all 294"
   vs "only 1 m works → freeride scores limited to LiDAR-covered regions."

4. **Eyeball validation:** hillshade + slope-overlay PNGs and slope/aspect histograms per
   resort, sanity-checked against the known reality of each mountain (using Fatmap/resort
   maps by eye — they never touch the pipeline, so no ToS applies).

5. **OSM freeride-tag overlay (free validation leg):** filter the OpenSkiMap `runs` layer
   for `piste:difficulty=freeride` / `piste:grooming=backcountry` and overlay those run
   geometries on the slope-overlay PNGs. Where such tags exist, our DEM-computed 30–45°
   sweet-spot terrain should coincide with them — a cheap cross-check that the slope
   computation points at the right places. Absence of tags is treated as "unmapped," never
   as "no freeride terrain" (see "Why not OSM freeride tags alone?").

## Stack & testing

- **Python** (the repo already uses it). Libraries: `rasterio`, `numpy`,
  `shapely`/`geopandas`, `matplotlib`, `requests`.
- Self-contained under `experiments/terrain-spike/` with its own `requirements.txt`.
- Because this is exploratory data analysis, **full TDD is skipped**, with **one sanity
  test**: `terrain.py` slope/aspect against a synthetic known ramp (a 30° tilted plane
  must read slope ≈ 30° and the correct aspect). Everything else is throwaway.

## Explicitly out of scope

- Wiring any of this into the production Express/EJS app or the 294-resort pipeline.
- Treeline / landcover, roughness / cliff detection (stage-2).
- Separating St. Anton from Lech.
- Building the raw-Overpass lift-hull path (fallback documented, not implemented).
- Automated matching of all 294 resorts to OpenSkiMap (a scale-stage concern).
