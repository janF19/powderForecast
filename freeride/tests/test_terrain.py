import numpy as np
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
from freeride.terrain import slope_aspect


def test_flat_dem_gives_zero_slope():
    dem = np.ones((10, 10)) * 1000.0
    slope, aspect = slope_aspect(dem, 30.0)
    assert np.allclose(slope, 0.0, atol=1e-9)
    assert np.all(np.isnan(aspect))


def test_east_slope_aspect_is_90():
    dem = np.zeros((5, 10))
    for col in range(10):
        dem[:, col] = float(10 - col) * 30.0
    slope, aspect = slope_aspect(dem, 30.0)
    inner = aspect[1:-1, 1:-1]
    assert np.allclose(inner, 90.0, atol=2.0)


def test_north_slope_aspect_is_0():
    dem = np.zeros((10, 5))
    for row in range(10):
        dem[row, :] = float(10 - row) * 30.0
    slope, aspect = slope_aspect(dem, 30.0)
    inner = aspect[1:-1, 1:-1]
    assert np.allclose(inner, 180.0, atol=2.0)
