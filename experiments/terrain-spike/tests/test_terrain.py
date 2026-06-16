import numpy as np
from terrain import slope_aspect

PX = 10.0  # metres per pixel

def test_flat_terrain_is_zero_slope():
    dem = np.full((20, 20), 1000.0)
    slope, aspect = slope_aspect(dem, PX)
    assert np.allclose(slope, 0.0, atol=1e-6)

def test_east_facing_30deg_ramp():
    # z rises toward the east (increasing column). Uphill = east, downhill = west.
    cols = np.arange(20)
    dem = np.tile(cols * PX * np.tan(np.radians(30)), (20, 1))
    slope, aspect = slope_aspect(dem, PX)
    inner = slope[1:-1, 1:-1]
    assert np.allclose(inner, 30.0, atol=0.5)
    assert np.allclose(aspect[1:-1, 1:-1], 270.0, atol=1.0)  # downhill = west

def test_north_facing_30deg_ramp():
    # z rises toward the north (row 0 = north, so z decreases with row index).
    rows = np.arange(20)
    col = (rows.max() - rows) * PX * np.tan(np.radians(30))
    dem = np.tile(col.reshape(-1, 1), (1, 20))
    slope, aspect = slope_aspect(dem, PX)
    inner = slope[1:-1, 1:-1]
    assert np.allclose(inner, 30.0, atol=0.5)
    assert np.allclose(aspect[1:-1, 1:-1], 180.0, atol=1.0)  # downhill = south
