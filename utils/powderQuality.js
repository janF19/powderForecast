'use strict';

// Index of "today" in the 28-day daily arrays (14 past days precede it).
const FORECAST_START = 14;
const FORECAST_DAYS = 7;

function clamp(x, lo, hi) {
  return Math.max(lo, Math.min(hi, x));
}

// Per-day Powder Quality Index (0..100). Balanced character:
// snow amount is the base, cold/wind/rain adjust it. No snow => 0.
function computeDayPQI(snow, tmax, wind, rain) {
  const s = Number(snow);
  if (!Number.isFinite(s) || s <= 0) return 0;
  const t = Number.isFinite(Number(tmax)) ? Number(tmax) : 0;
  const w = Number.isFinite(Number(wind)) ? Number(wind) : 0;
  const r = Number.isFinite(Number(rain)) ? Number(rain) : 0;

  const amount = 100 * (1 - Math.exp(-s / 15));
  const coldFactor = clamp((3 - t) / 11, 0.35, 1.0);   // +3C -> 0.35 .. -8C -> 1.0
  const windFactor = clamp(1 - (w - 15) / 70, 0.5, 1.0); // <15 -> 1.0 .. 50 -> 0.5
  const rainFactor = clamp(1 - r * 0.08, 0.2, 1.0);      // 0mm -> 1.0 .. 10mm -> 0.2

  return amount * coldFactor * windFactor * rainFactor;
}

module.exports = { FORECAST_START, FORECAST_DAYS, clamp, computeDayPQI };
