"""Batch scorer: read resort_matches.json → fetch DEMs → write freeride_terrain.json."""
import json
from datetime import datetime, timezone
import numpy as np
import rasterio
from rasterio.features import rasterize
from shapely.ops import transform as shp_transform
from pyproj import Transformer
from freeride.config import MATCHES_JSON, TERRAIN_JSON
from freeride.footprint_prod import get_polygon
from freeride.dem_fetch import fetch_copernicus
from freeride.terrain import slope_aspect
from freeride.score import terrain_score


def _polygon_mask(poly_4326, src):
    epsg = src.crs.to_epsg()
    tf = Transformer.from_crs(4326, epsg, always_xy=True).transform
    poly_m = shp_transform(tf, poly_4326)
    return rasterize(
        [(poly_m, 1)],
        out_shape=(src.height, src.width),
        transform=src.transform,
        fill=0,
        dtype="uint8",
    ).astype(bool)


def score_from_dem(dem_path, poly_4326):
    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype("float64")
        nodata = src.nodata
        if nodata is not None:
            dem[dem == nodata] = np.nan
        px = abs(src.transform.a)
        mask = _polygon_mask(poly_4326, src)
    slope, aspect = slope_aspect(dem, px)
    return terrain_score(slope, aspect, dem, mask)


def run_batch(dry_run=False):
    with open(MATCHES_JSON, encoding="utf-8") as f:
        matches = json.load(f)

    output = {}
    skipped = []
    timestamp = datetime.now(timezone.utc).isoformat()

    for resort_name, match in matches.items():
        ski_area_name = match.get("ski_area_name")
        status = match.get("status")

        if not ski_area_name or status == "no_match":
            skipped.append((resort_name, "no_match"))
            continue

        poly, bbox = get_polygon(ski_area_name)
        if poly is None:
            skipped.append((resort_name, f"polygon not found: {ski_area_name!r}"))
            continue

        if dry_run:
            print(f"  [dry_run] would score {resort_name!r} -> {ski_area_name!r}")
            continue

        try:
            center = poly.centroid.coords[0]
            dem_path = fetch_copernicus(resort_name, bbox, center)
            scores = score_from_dem(dem_path, poly)
            output[resort_name] = {
                "combined": round(scores["combined"], 1),
                "S": round(scores["S"], 4),
                "A": round(scores["A"], 4),
                "V": round(scores["V"], 4),
                "n_pixels": scores["n_pixels"],
                "ski_area_name": ski_area_name,
                "computed_at": timestamp,
            }
            print(f"  {resort_name}: combined={scores['combined']:.1f} "
                  f"S={scores['S']:.3f} n={scores['n_pixels']}")
        except Exception as e:
            print(f"  ERROR {resort_name}: {e}")
            skipped.append((resort_name, str(e)))

    if not dry_run:
        with open(TERRAIN_JSON, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\nWrote {len(output)} resorts to {TERRAIN_JSON}")

    if skipped:
        print(f"\nSkipped {len(skipped)} resorts:")
        for name, reason in skipped:
            print(f"  {name!r}: {reason}")

    return output


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    run_batch(dry_run=dry_run)
