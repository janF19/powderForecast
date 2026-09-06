/**
 * Zdroj předpovědi. Data se stahují za běhu, nejsou zapečená v image.
 *
 * Proč: GitHub Actions aktualizují předpověď každou noc. Když se výsledek
 * commitoval do main, Coolify na každý takový commit přestavěl celou aplikaci
 * — kvůli jednomu JSON souboru, ve kterém se nezměnil ani řádek kódu. Build
 * cache pak na serveru rostla o ~1 GB za pár dní.
 *
 * Data teď žijí ve větvi `data`, kterou Coolify nesleduje. Aplikace si je
 * stáhne při startu a pak jednou za hodinu; drží je v paměti, takže se navíc
 * přestal číst 7MB soubor z disku při každém requestu.
 */

const fs = require('fs');
const path = require('path');

const DATA_URL = process.env.WEATHER_DATA_URL ||
    'https://raw.githubusercontent.com/janF19/powderForecast/data/weather_dataFull_7.json';
const REFRESH_MS = Number(process.env.WEATHER_REFRESH_MS || 60 * 60 * 1000);
const FALLBACK_PATH = path.join(__dirname, 'weather_dataFull_7.json');

let cache = null;
let cachedAt = 0;

/** Soubor v repu je záložní: aplikace musí nastartovat i bez sítě. */
function loadFallback() {
    try {
        return JSON.parse(fs.readFileSync(FALLBACK_PATH, 'utf-8'));
    } catch (err) {
        console.error('[weatherData] záložní soubor se nepodařilo načíst:', err.message);
        return null;
    }
}

async function refresh() {
    try {
        const res = await fetch(DATA_URL, { signal: AbortSignal.timeout(20000) });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        cache = data;
        cachedAt = Date.now();
        console.log(`[weatherData] staženo z ${DATA_URL}`);
    } catch (err) {
        // Stará data jsou pořád lepší než žádná — předpověď se mění po hodinách.
        console.error('[weatherData] stažení selhalo, držím dosavadní data:', err.message);
        if (!cache) cache = loadFallback();
    }
}

/** Vrací poslední známá data. Nikdy nesahá na disk mimo první start. */
function get() {
    if (!cache) cache = loadFallback();
    return cache;
}

function start() {
    refresh();
    const t = setInterval(refresh, REFRESH_MS);
    if (t.unref) t.unref();
}

module.exports = { get, refresh, start, DATA_URL, cachedAt: () => cachedAt };
