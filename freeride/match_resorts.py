"""One-time script: match weather_dataFull_7.json resort names to OpenSkiMap ski areas."""
import json
import re
import unicodedata
import requests
from pathlib import Path
from freeride.config import OPENSKIMAP, OSM_DIR, WEATHER_JSON, MATCHES_JSON, OVERRIDES_JSON, DATA

AUTO_ACCEPT_THRESHOLD = 1  # hints that must match to auto-accept


def _download_ski_areas():
    OSM_DIR.mkdir(parents=True, exist_ok=True)
    dest = OSM_DIR / "ski_areas.geojson"
    if dest.exists():
        return dest
    print("Downloading ski_areas.geojson (~50 MB)...")
    with requests.get(OPENSKIMAP["ski_areas"], stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    print("Done.")
    return dest


def _normalize(text: str) -> str:
    # Strip all diacritics for fuzzy scoring
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


def extract_hints(resort_name: str) -> list[str]:
    """Extract searchable sub-strings from a resort name."""
    hints = set()
    hints.add(resort_name.strip())
    # Split out parenthetical parts: "Méribel (Les 3 Vallées)" → ["Méribel", "Les 3 Vallées"]
    paren = re.findall(r'\(([^)]+)\)', resort_name)
    base = re.sub(r'\s*\([^)]*\)', '', resort_name).strip()
    hints.add(base)
    for p in paren:
        hints.add(p.strip())
    # Split on dash/slash separators (common in linked ski areas)
    for part in re.split(r'[-/–]', base):
        part = part.strip()
        if len(part) > 2:
            hints.add(part)
    return [h for h in hints if h]


def score_name_match(ski_area_name: str, hints: list[str]) -> int:
    """Count how many hints appear (case-insensitive, diacritic-stripped) in ski_area_name."""
    norm_area = _normalize(ski_area_name)
    count = 0
    for hint in hints:
        if len(hint) < 3:
            continue
        if _normalize(hint) in norm_area:
            count += 1
    return count


def _load_ski_areas():
    path = _download_ski_areas()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["features"]


def run_matching():
    """Match all weather JSON resort names to OpenSkiMap ski areas. Write resort_matches.json."""
    with open(WEATHER_JSON, encoding="utf-8") as f:
        weather = json.load(f)
    resort_names = list(weather.keys())

    # Load overrides first — normalise keys to NFC so they match weather JSON keys
    overrides = {}
    if OVERRIDES_JSON.exists():
        with open(OVERRIDES_JSON, encoding="utf-8-sig") as f:
            raw_overrides = json.load(f)
        overrides = {unicodedata.normalize("NFC", k): v for k, v in raw_overrides.items()}

    features = _load_ski_areas()
    # Pre-extract all ski-area names
    area_names = [(feat.get("properties", {}).get("name") or "", feat) for feat in features]
    area_names = [(n, f) for n, f in area_names if n]

    results = {}
    flagged = []

    for resort in resort_names:
        # NFC normalizes precomposed/decomposed forms for override key lookup
        resort_nfc = unicodedata.normalize("NFC", resort)
        if resort_nfc in overrides:
            results[resort] = {
                "status": "override",
                "ski_area_name": overrides[resort_nfc],
                "confidence": "manual",
                "candidates": [],
            }
            continue

        hints = extract_hints(resort)
        scored = []
        for name, feat in area_names:
            s = score_name_match(name, hints)
            if s > 0:
                scored.append((s, name))
        scored.sort(key=lambda x: -x[0])
        top3 = scored[:3]

        if not top3:
            results[resort] = {"status": "no_match", "ski_area_name": None,
                                "confidence": "none", "candidates": []}
            flagged.append(resort)
        elif top3[0][0] >= AUTO_ACCEPT_THRESHOLD:
            results[resort] = {
                "status": "auto",
                "ski_area_name": top3[0][1],
                "confidence": "high" if top3[0][0] >= 2 else "medium",
                "candidates": [{"name": n, "score": s} for s, n in top3],
            }
        else:
            results[resort] = {
                "status": "flagged",
                "ski_area_name": top3[0][1],
                "confidence": "low",
                "candidates": [{"name": n, "score": s} for s, n in top3],
            }
            flagged.append(resort)

    DATA.mkdir(parents=True, exist_ok=True)
    with open(MATCHES_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nMatched {len(resort_names)} resorts.")
    print(f"  Auto-accepted: {sum(1 for v in results.values() if v['status'] == 'auto')}")
    print(f"  Overrides:     {sum(1 for v in results.values() if v['status'] == 'override')}")
    print(f"  Flagged/unmatched: {len(flagged)}")
    if flagged:
        print("\nFlagged resorts (add to resort_overrides.json or accept default):")
        for r in flagged:
            cands = results[r].get("candidates", [])
            best = cands[0]["name"] if cands else "none"
            print(f"  {r!r}  ->  best guess: {best!r}")

    return results


if __name__ == "__main__":
    run_matching()
