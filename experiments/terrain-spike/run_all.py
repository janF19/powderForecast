"""End-to-end: footprints -> DEM clips -> scores -> table + maps."""
import rasterio
from footprint import build_footprints
from dem_fetch import fetch_copernicus, load_lidar
from report import score_resort, save_map, save_histograms, write_table


def main():
    fps = build_footprints()
    rows = []
    for key, fp in fps.items():
        poly = fp["polygon"]
        center = poly.centroid.coords[0]
        tiers = {}
        tiers["cop30"] = fetch_copernicus(key, fp["bbox"], center)
        lidar = load_lidar(key)
        if lidar:
            tiers["lidar1m"] = lidar
        for tier, path in tiers.items():
            scores, (dem, slope, mask) = score_resort(path, poly)
            save_map(key, tier, dem, slope, mask)
            save_histograms(key, tier, slope, mask)
            rows.append({"resort": key, "tier": tier, **scores})
            print(f"{key:12s} {tier:8s} "
                  f"S={scores['S']:.3f} A={scores['A']:.3f} "
                  f"V={scores['V']:.3f} combined={scores['combined']:.1f}")
    write_table(rows)
    print("\nWrote output/results.csv, output/results.md and PNG maps.")


if __name__ == "__main__":
    main()
