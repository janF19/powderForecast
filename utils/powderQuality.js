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
  const coldFactor = clamp((3 - t) / 11, 0.35, 1.0);   // floor 0.35 at >= ~-0.85C; 1.0 at <= -8C
  const windFactor = clamp(1 - (w - 15) / 70, 0.5, 1.0); // <15 -> 1.0 .. 50 -> 0.5
  const rainFactor = clamp(1 - r * 0.08, 0.2, 1.0);      // 0mm -> 1.0 .. 10mm -> 0.2

  return amount * coldFactor * windFactor * rainFactor;
}

// Compute PQI for each day of equal-length arrays, plus the peak and its offset.
function computePQISeries({ snowfall, tmax, wind, rain }) {
  const dailyPQI = snowfall.map((_, i) =>
    computeDayPQI(snowfall[i], tmax[i], wind[i], rain[i])
  );
  let peakPQI = 0;
  let peakOffset = 0;
  dailyPQI.forEach((v, i) => {
    if (v > peakPQI) {
      peakPQI = v;
      peakOffset = i;
    }
  });
  return { dailyPQI, peakPQI, peakOffset };
}

// Map a 0..100 PQI to a named band (drives badge/cell colors).
function pqiBand(pqi) {
  if (pqi >= 70) return 'epic';
  if (pqi >= 50) return 'great';
  if (pqi >= 30) return 'good';
  if (pqi >= 15) return 'ok';
  if (pqi > 0) return 'poor';
  return 'none';
}

// Slice the 7-day forecast window out of one elevation's 28-day arrays.
function elevationForecastSlice(elevationData) {
  const end = FORECAST_START + FORECAST_DAYS;
  return {
    snowfall: elevationData.snowfall_sum.slice(FORECAST_START, end),
    tmax: elevationData.temperature_2m_max.slice(FORECAST_START, end),
    wind: elevationData.wind_speed_10m_max.slice(FORECAST_START, end),
    rain: elevationData.rain_sum.slice(FORECAST_START, end),
  };
}

const LIFTS = ['Top Lift', 'Mid Lift', 'Bottom Lift'];

// Resort-level summary. Headline = Top Lift peak; detail = all 3 elevations.
function buildResortPQI(resortData) {
  const elevations = (resortData && resortData.elevations) || {};
  const perElevation = {};
  for (const lift of LIFTS) {
    const ed = elevations[lift];
    if (!ed || !Array.isArray(ed.snowfall_sum)) {
      perElevation[lift] = null;
      continue;
    }
    perElevation[lift] = computePQISeries(elevationForecastSlice(ed));
  }

  const top = perElevation['Top Lift'];
  const peakPQI = top ? top.peakPQI : 0;
  const peakOffset = top ? top.peakOffset : 0;

  let freshSnowOnPeakDay = 0;
  const topEd = elevations['Top Lift'];
  if (top && topEd && Array.isArray(topEd.snowfall_sum)) {
    const snowSlice = topEd.snowfall_sum.slice(FORECAST_START, FORECAST_START + FORECAST_DAYS);
    freshSnowOnPeakDay = Number(snowSlice[peakOffset]) || 0;
  }

  return { peakPQI, peakOffset, freshSnowOnPeakDay, perElevation };
}

module.exports = {
  FORECAST_START,
  FORECAST_DAYS,
  clamp,
  computeDayPQI,
  computePQISeries,
  pqiBand,
  buildResortPQI,
};
