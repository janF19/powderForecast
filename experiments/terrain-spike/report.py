"""Score each resort per DEM tier and emit table + validation maps."""
import csv
import numpy as np
import rasterio
from rasterio.features import rasterize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.ops import transform as shp_transform
from pyproj import Transformer
from shapely.geometry import shape
from config import OUTPUT, utm_epsg
from terrain import slope_aspect
from score import terrain_score


def _polygon_mask(poly_4326, src):
    """Rasterize a lon/lat polygon onto src's grid (src is metric/UTM)."""
    epsg = src.crs.to_epsg()
    tf = Transformer.from_crs(4326, epsg, always_xy=True).transform
    poly_m = shp_transform(tf, poly_4326)
    return rasterize([(poly_m, 1)], out_shape=(src.height, src.width),
                     transform=src.transform, fill=0, dtype="uint8").astype(bool)


def score_resort(dem_path, poly_4326):
    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype("float64")
        nodata = src.nodata
        if nodata is not None:
            dem[dem == nodata] = np.nan
        px = abs(src.transform.a)
        mask = _polygon_mask(poly_4326, src)
    slope, aspect = slope_aspect(dem, px)
    return terrain_score(slope, aspect, dem, mask), (dem, slope, mask)


def _hillshade(dem, px):
    dy, dx = np.gradient(dem, px)
    slope_r = np.pi / 2 - np.arctan(np.hypot(dx, dy))
    aspect_r = np.arctan2(-dx, dy)
    az, alt = np.radians(315), np.radians(45)
    hs = (np.sin(alt) * np.sin(slope_r) +
          np.cos(alt) * np.cos(slope_r) * np.cos(az - aspect_r))
    return hs


def save_map(resort_key, tier, dem, slope, mask):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    px = 1.0
    fig, ax = plt.subplots(figsize=(7, 7))
    hs = _hillshade(dem, px)
    ax.imshow(hs, cmap="gray")
    sweet = np.where(mask & (slope >= 30) & (slope <= 45), slope, np.nan)
    ax.imshow(sweet, cmap="autumn", alpha=0.6, vmin=30, vmax=45)
    ax.set_title(f"{resort_key} — {tier}\nred = 30-45° lift-served terrain")
    ax.axis("off")
    fig.savefig(OUTPUT / f"{resort_key}_{tier}_slopemap.png", dpi=120,
                bbox_inches="tight")
    plt.close(fig)


def save_histograms(resort_key, tier, slope, mask):
    vals = slope[mask & ~np.isnan(slope)]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(vals, bins=np.arange(0, 70, 2))
    ax.axvspan(30, 45, color="orange", alpha=0.3, label="sweet spot")
    ax.set_xlabel("slope (deg)")
    ax.set_ylabel("pixels")
    ax.set_title(f"{resort_key} — {tier} slope distribution")
    ax.legend()
    fig.savefig(OUTPUT / f"{resort_key}_{tier}_slopehist.png", dpi=120,
                bbox_inches="tight")
    plt.close(fig)


def write_table(rows):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fields = ["resort", "tier", "S", "A", "V", "combined", "n_pixels"]
    with open(OUTPUT / "results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})
    with open(OUTPUT / "results.md", "w") as f:
        f.write("| " + " | ".join(fields) + " |\n")
        f.write("|" + "|".join("---" for _ in fields) + "|\n")
        for r in rows:
            f.write("| " + " | ".join(
                f"{r[k]:.3f}" if isinstance(r[k], float) else str(r[k])
                for k in fields) + " |\n")
