import numpy as np
from freeride.config import SLOPE_MIN, SLOPE_MAX, VERTICAL_CAP_M, WEIGHTS, ASPECT_FLOOR


def aspect_weight(aspect_deg):
    """Powder-retention weight: N=1.0, S=ASPECT_FLOOR, E/W between. NaN-safe."""
    rad = np.radians(aspect_deg)
    return ASPECT_FLOOR + (1.0 - ASPECT_FLOOR) * (1.0 + np.cos(rad)) / 2.0


def terrain_score(slope, aspect, elevation, mask):
    """Compute S, A, V and combined index over masked pixels."""
    s = slope[mask]
    a = aspect[mask]
    e = elevation[mask]
    valid = ~np.isnan(s) & ~np.isnan(e)
    n = int(valid.sum())
    if n == 0:
        return {"S": 0.0, "A": 0.0, "V": 0.0, "combined": 0.0, "n_pixels": 0}

    sweet = valid & (s >= SLOPE_MIN) & (s <= SLOPE_MAX)
    S = float(sweet.sum()) / n

    if sweet.any():
        A = float(np.nanmean(aspect_weight(a[sweet])))
    else:
        A = 0.0

    drop = float(np.nanmax(e[valid]) - np.nanmin(e[valid]))
    V = min(drop / VERTICAL_CAP_M, 1.0)

    combined = 100.0 * (WEIGHTS["S"] * S + WEIGHTS["A"] * A + WEIGHTS["V"] * V)
    return {"S": S, "A": A, "V": V, "combined": combined, "n_pixels": n}
