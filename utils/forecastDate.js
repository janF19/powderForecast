'use strict';

// Turn a forecast day offset (0 = today) into a short label like "Thu 15 Jan".
function forecastDayLabel(offset, now = new Date()) {
  const d = new Date(now);
  d.setDate(d.getDate() + offset);
  return d.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  });
}

module.exports = { forecastDayLabel };
