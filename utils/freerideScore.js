const fs = require('fs');
const path = require('path');

const TERRAIN_JSON = path.join(__dirname, '../freeride_terrain.json');

let _cache = null;

function _load() {
  if (!_cache) {
    try {
      _cache = JSON.parse(fs.readFileSync(TERRAIN_JSON, 'utf-8'));
    } catch {
      _cache = {};
    }
  }
  return _cache;
}

function getFreerideScore(resortName) {
  return _load()[resortName] || null;
}

function allFreerideScores() {
  return _load();
}

module.exports = { getFreerideScore, allFreerideScores };
