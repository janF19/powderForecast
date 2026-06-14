const { test } = require('node:test');
const assert = require('node:assert/strict');
const { computeDayPQI } = require('../utils/powderQuality');

const near = (actual, expected, tol = 0.05) =>
  assert.ok(Math.abs(actual - expected) <= tol, `expected ~${expected}, got ${actual}`);

test('cold calm big dump scores high', () => {
  near(computeDayPQI(30, -10, 5, 0), 86.5);
});

test('warm windy big dump scores much lower than the same dump cold and calm', () => {
  const warmWindy = computeDayPQI(30, 1, 50, 0);
  near(warmWindy, 15.1);
  assert.ok(warmWindy < computeDayPQI(30, -10, 5, 0));
});

test('cold smaller dump is solid', () => {
  near(computeDayPQI(15, -12, 5, 0), 63.2);
});

test('no snow is always zero regardless of other factors', () => {
  assert.equal(computeDayPQI(0, -20, 0, 0), 0);
});

test('rain strongly penalizes an otherwise great dump', () => {
  const rained = computeDayPQI(30, -10, 5, 8);
  assert.ok(rained > 0 && rained < 40, `expected ruined-but-positive, got ${rained}`);
});

test('coldFactor floors at temperatures above ~-1C (0C and +5C give the same score)', () => {
  assert.equal(computeDayPQI(20, 0, 5, 0), computeDayPQI(20, 5, 5, 0));
});

test('windFactor floors at 50km/h (50 and 85 score the same)', () => {
  assert.equal(computeDayPQI(20, -10, 50, 0), computeDayPQI(20, -10, 85, 0));
});

test('null inputs are treated as no-contribution, not NaN', () => {
  assert.equal(computeDayPQI(null, -10, 5, 0), 0);
  assert.ok(Number.isFinite(computeDayPQI(20, null, null, null)));
});

const { computePQISeries } = require('../utils/powderQuality');

test('series returns one PQI per day and finds the peak', () => {
  const out = computePQISeries({
    snowfall: [30, 10],
    tmax:     [2, -15],   // day 0 warm, day 1 cold
    wind:     [50, 2],    // day 0 windy, day 1 calm
    rain:     [0, 0],
  });
  assert.equal(out.dailyPQI.length, 2);
  // Day 1 (cold, calm, smaller) beats day 0 (warm, windy, bigger dump).
  assert.equal(out.peakOffset, 1);
  assert.ok(out.peakPQI > out.dailyPQI[0]);
});

test('series of all-zero snow has peak 0 at offset 0', () => {
  const out = computePQISeries({
    snowfall: [0, 0, 0], tmax: [-5, -5, -5], wind: [0, 0, 0], rain: [0, 0, 0],
  });
  assert.equal(out.peakPQI, 0);
  assert.equal(out.peakOffset, 0);
});
