import numpy as np
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
from freeride.score import aspect_weight, terrain_score


def test_aspect_weight_north_is_one_south_is_floor():
    assert abs(aspect_weight(np.array([0.0]))[0] - 1.0) < 1e-9
    assert abs(aspect_weight(np.array([180.0]))[0] - 0.3) < 1e-9
    ew = aspect_weight(np.array([90.0]))[0]
    assert 0.3 < ew < 1.0


def test_terrain_score_all_in_sweet_spot_north_facing():
    slope = np.full((10, 10), 35.0)
    aspect = np.full((10, 10), 0.0)
    elev = np.zeros((10, 10))
    elev[0, 0] = 1500.0
    mask = np.ones((10, 10), dtype=bool)
    out = terrain_score(slope, aspect, elev, mask)
    assert abs(out["S"] - 1.0) < 1e-9
    assert abs(out["A"] - 1.0) < 1e-9
    assert abs(out["V"] - 1.0) < 1e-9
    assert abs(out["combined"] - 100.0) < 1e-6


def test_terrain_score_flat_terrain_scores_low():
    slope = np.full((10, 10), 5.0)
    aspect = np.full((10, 10), 180.0)
    elev = np.full((10, 10), 1000.0)
    mask = np.ones((10, 10), dtype=bool)
    out = terrain_score(slope, aspect, elev, mask)
    assert out["S"] == 0.0
    assert out["combined"] < 1.0


def test_terrain_score_empty_mask_returns_zeros():
    slope = np.full((5, 5), 35.0)
    aspect = np.full((5, 5), 0.0)
    elev = np.full((5, 5), 1000.0)
    mask = np.zeros((5, 5), dtype=bool)
    out = terrain_score(slope, aspect, elev, mask)
    assert out["S"] == 0.0
    assert out["combined"] == 0.0
    assert out["n_pixels"] == 0
