"""Fetch + clip + reproject DEMs to per-resort metric-CRS GeoTIFFs."""
import math
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.windows import from_bounds
from config import DEM_DIR, LIDAR_DIR, utm_epsg

COP_URL = ("https://copernicus-dem-30m.s3.amazonaws.com/"
           "Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM/"
           "Copernicus_DSM_COG_10_N{lat:02d}_00_E{lon:03d}_00_DEM.tif")


def _cop_tiles(bbox):
    """1-degree tile URLs covering bbox (minx,miny,maxx,maxy)."""
    minx, miny, maxx, maxy = bbox
    urls = []
    for lat in range(math.floor(miny), math.floor(maxy) + 1):
        for lon in range(math.floor(minx), math.floor(maxx) + 1):
            urls.append(COP_URL.format(lat=lat, lon=lon))
    return urls


def _read_clip_merge_4326(urls, bbox):
    """Windowed-read each COG tile, clip to bbox, merge into one array."""
    datasets = []
    for url in urls:
        try:
            ds = rasterio.open(f"/vsicurl/{url}")
            datasets.append(ds)
        except Exception as e:
            print(f"  warning: could not open {url}: {e}")
    if not datasets:
        raise RuntimeError("No Copernicus tiles could be opened")

    if len(datasets) == 1:
        ds = datasets[0]
        win = from_bounds(*bbox, transform=ds.transform)
        arr = ds.read(1, window=win)
        transform = ds.window_transform(win)
        profile = ds.profile.copy()
        ds.close()
    else:
        # Mosaic tiles, then clip
        merged_arr, merged_transform = merge(datasets, bounds=bbox)
        arr = merged_arr[0]
        transform = merged_transform
        profile = datasets[0].profile.copy()
        for ds in datasets:
            ds.close()

    profile.update(width=arr.shape[1], height=arr.shape[0], transform=transform)
    return arr, transform, profile


def _reproject_to_utm(arr, transform, src_profile, dst_epsg, dest):
    dst_crs = rasterio.crs.CRS.from_epsg(dst_epsg)
    h, w = arr.shape
    dst_transform, dw, dh = calculate_default_transform(
        src_profile["crs"], dst_crs, w, h,
        *rasterio.transform.array_bounds(h, w, transform))
    dst = np.empty((dh, dw), dtype="float32")
    reproject(arr.astype("float32"), dst,
              src_transform=transform, src_crs=src_profile["crs"],
              dst_transform=dst_transform, dst_crs=dst_crs,
              resampling=Resampling.bilinear)
    DEM_DIR.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dest, "w", driver="GTiff", height=dh, width=dw, count=1,
                       dtype="float32", crs=dst_crs, transform=dst_transform,
                       nodata=src_profile.get("nodata")) as out:
        out.write(dst, 1)
    return dest


def fetch_copernicus(resort_key, bbox, center_lonlat):
    """Clip Copernicus 30m to bbox, reproject to local UTM, save GeoTIFF."""
    dest = DEM_DIR / f"{resort_key}_cop30.tif"
    if dest.exists():
        print(f"  {resort_key}: using cached {dest.name}")
        return dest
    urls = _cop_tiles(bbox)
    print(f"  {resort_key}: fetching {len(urls)} Copernicus tile(s)...")
    arr, transform, profile = _read_clip_merge_4326(urls, bbox)
    epsg = utm_epsg(*center_lonlat)
    print(f"  {resort_key}: reprojecting to EPSG:{epsg}...")
    return _reproject_to_utm(arr, transform, profile, epsg, dest)


def load_lidar(resort_key):
    """Return path to pre-downloaded Austrian LiDAR clip if present, else None."""
    path = LIDAR_DIR / f"{resort_key}_lidar.tif"
    return path if path.exists() else None
