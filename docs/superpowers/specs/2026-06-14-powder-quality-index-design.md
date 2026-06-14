# Powder Quality Index (PQI) — Design

**Date:** 2026-06-14
**Status:** Approved, ready for implementation plan
**Sub-project:** 1 of 2 (the other is the Freeride Terrain feasibility spike)

## Problem

The site currently ranks resorts by raw `snowfall_sum` over 3/7/14 days. A snow total is a
crude proxy for powder quality: 30 cm of wet snow at +1 °C with 50 km/h wind is garbage,
while 15 cm of cold dry snow in calm air is a face-shot day. The forecast pipeline already
fetches temperature, wind, and rain per resort/elevation/day but throws them away.

PQI turns those already-fetched inputs into a 0–100 powder-quality score, **added alongside**
the existing snow-sum forecast (the 7-day forecast is kept, not replaced).

## Scope

**In scope:**
- A pure scoring module that converts daily weather arrays into a PQI.
- A new "Powder Quality" page: ranked leaderboard + per-resort daily timeline.
- A "Top powder right now" panel on the existing home page.

**Out of scope (separate follow-ups, not this spec):**
- Deleting dead `ml_prediction.py`.
- Fixing the broken `calculateHistory.py` route (`resortController.js:297`).
- The Freeride Terrain Score and its feasibility spike (sub-project 2).

## Design decisions (locked)

| Decision | Choice |
|---|---|
| Score shape | **Peak day** in the next 7 days = headline (for ranking); **daily timeline** on click |
| Character | **Balanced** — snow amount is the base, quality (cold/wind/rain) adjusts it meaningfully |
| Elevation | **Top lift** drives the ranking; per-resort detail shows all three elevations |
| Placement | **New "Powder Quality" page + home-page badge panel**; existing views untouched |
| Compute location | **Node controller at render time** (not the Python cron) — data is already in the JSON; lets us tune the formula without re-running the cron |

## Architecture

One isolated, testable unit plus thin wiring:

- **`utils/powderQuality.js`** — a pure function. Input: a resort's daily arrays
  (`snowfall_sum`, `temperature_2m_max`, `wind_speed_10m_max`, `rain_sum`) for one elevation.
  Output: `{ dailyPQI: number[], peakPQI: number, peakDayIndex: number }`.
  A second helper computes the per-resort summary across the three elevations:
  `{ peakPQI, peakDayIndex, freshSnowOnPeakDay, perElevation: { 'Top Lift': {...}, 'Mid Lift': {...}, 'Bottom Lift': {...} } }`.
  No I/O, no Express — just math. This is the only place the formula lives.
- **`controllers/resortController.js`** — a new `getPowderQuality` handler reads
  `weather_dataFull_7.json`, calls the module per resort, sorts by `peakPQI` (top lift),
  renders `powderQuality`. The existing `getSnowfallForResorts` (home) additionally computes
  the top-5 PQI for the home badge panel.
- **`routes/resorts.js`** — add `GET /powder-quality`.
- **`views/powderQuality.ejs`** — leaderboard + expandable per-resort timeline.
- **`views/partials/navbar.ejs`** — add the nav link.
- **`views/index.ejs`** — add the "Top powder right now" panel.

### Data window

`weather_dataFull_7.json` stores 28-day daily arrays per elevation: indices `[0:14]` are the
past 14 days, `[14:28]` are the next 14 forecast days. PQI uses the **7-day forecast window =
indices `[14:21]`**. The peak is the max `PQI_day` over that window.

## The formula (v1, "Balanced")

Computed per day, per elevation. Let `snow` = `snowfall_sum` (cm), `tmax` =
`temperature_2m_max` (°C), `wind` = `wind_speed_10m_max` (km/h), `rain` = `rain_sum` (mm).

```
amount     = 100 * (1 - exp(-snow / 15))          // diminishing returns
coldFactor = clamp( (3 - tmax) / (3 - (-8)), 0.35, 1.0 )   // +3°C→0.35 .. -8°C→1.0
windFactor = clamp( 1 - (wind - 15) / 70, 0.5, 1.0 )      // <15→1.0 .. 50→0.5
rainFactor = clamp( 1 - rain * 0.08,        0.2, 1.0 )    // 0mm→1.0 .. 10mm→0.2

PQI_day = amount * coldFactor * windFactor * rainFactor   // 0..100
```

Reference points the curve must hit (used as test cases):
- `snow=30, tmax=-10, wind=5, rain=0` → high (~86, cold dump, near-ideal).
- `snow=30, tmax=+1, wind=50, rain=0` → clearly lower (warm + windy big dump).
- `snow=15, tmax=-12, wind=5, rain=0` → solid (~63, cold smaller dump).
- `snow=0` → 0 (no snow, no powder), regardless of other factors.
- `snow=30, rain=8` → strongly penalized (rain ruins it).

Notes:
- Open-Meteo provides **daily** values, not hourly, so `coldFactor` uses the day's max temp as a
  density proxy. This is a deliberate v1 approximation, documented, not a bug.
- Days-since-last-snow / freshness is intentionally omitted from v1: in a peak-day-in-7 model the
  best day is usually a day snow actually falls, so freshness is largely captured already.
- Thresholds are the v1 starting point. Tests pin them; tuning is a one-line change.

## UI

**Powder Quality page (`/powder-quality`):**
- Ranked leaderboard, sorted by top-lift `peakPQI` descending.
- Each row: resort name (links to its forecast URL), country, a **color-graded 0–100 PQI badge**,
  the **peak day** (date/day-of-week), and the **fresh snow (cm)** on that day.
- Color grading: red/grey (low) → blue → bright (high). Exact palette decided during build.
- Click a row → expand the **7-day PQI timeline** showing daily PQI for Top / Mid / Bottom lift,
  so users see how far down the good snow reaches.

**Home page panel:**
- A compact **"Top powder right now"** panel (top 5 by PQI) with badge + peak day, linking to the
  full page. Existing home rankings (7-day, 14-day) are unchanged.

## Testing

TDD on `utils/powderQuality.js`:
- The five reference cases above.
- Boundary cases: `tmax` exactly 0, `wind` exactly 15 and 50, `rain` exactly 10 (floor).
- Peak selection: an array where the max PQI is not the max snowfall day (quality flips the winner)
  — verifies we rank by quality, not amount.
- Clamp behavior: extreme inputs (very warm, very windy, huge rain) never push factors past their
  floors or above 1.0.

A light integration check: `getPowderQuality` produces a sorted list and never throws on a resort
with missing/`null` elevation data (the JSON has nulls when a fetch failed).

## Risks / open questions

- **Missing data:** some resorts have `null` sums when a fetch failed — the module must treat
  missing/`null` as "no contribution" and the controller must not crash.
- **Formula trust:** "Balanced" weights are a judgement call; expect one or two tuning passes after
  seeing real rankings against a storm. The isolated module makes this cheap.
