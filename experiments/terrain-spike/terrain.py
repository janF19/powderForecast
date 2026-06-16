"""Pure slope/aspect computation from a north-up DEM array."""
import numpy as np


def slope_aspect(dem, pixel_size_m):
    """Return (slope_deg, aspect_deg) for a north-up DEM.

    Array convention: axis 0 = rows north->south, axis 1 = cols west->east.
    Aspect is the compass bearing (0=N, 90=E, 180=S, 270=W) of the downhill
    (steepest-descent) direction; NaN where slope is ~0.
    """
    dem = np.asarray(dem, dtype="float64")
    d_drow, d_dcol = np.gradient(dem, pixel_size_m)
    dz_dx = d_dcol          # gradient toward east
    dz_dy = -d_drow         # gradient toward north (rows run north->south)

    slope = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))

    # Downhill direction = -gradient. Bearing from north, clockwise.
    bearing = np.degrees(np.arctan2(-dz_dx, -dz_dy))  # atan2(east, north)
    aspect = (bearing + 360.0) % 360.0
    aspect = np.where(slope < 1e-9, np.nan, aspect)
    return slope, aspect
