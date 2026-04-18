import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from sparq import compute_psparq, compute_nfl_percentile, compute_z_score, estimate_ten_split


def test_compute_psparq_all_inputs():
    # Prototypical fast WR: weight=169, vert=38.5, broad=131in, bench=7,
    # forty=4.35, ten_split=1.50, shuttle=3.87, cone=6.70
    result = compute_psparq(
        weight=169, vertical=38.5, broad=131,
        bench=7, forty=4.35, ten_split=1.50,
        shuttle=3.87, cone=6.70
    )
    assert result is not None
    assert 100 < result < 160, f"Expected 100–160 for elite WR, got {result:.1f}"


def test_compute_psparq_missing_bench():
    result = compute_psparq(
        weight=210, vertical=36.0, broad=120,
        bench=None, forty=4.55, ten_split=1.55,
        shuttle=4.10, cone=7.10, pos='RB'
    )
    assert result is not None


def test_compute_psparq_too_few_inputs():
    # Only 2 real inputs (weight + forty) — below MIN_REAL_INPUTS threshold
    result = compute_psparq(
        weight=210, vertical=None, broad=None,
        bench=None, forty=4.55, ten_split=None,
        shuttle=None, cone=None
    )
    assert result is None


def test_estimate_ten_split():
    # Real NFL ratio: ten_split ≈ forty × 0.346 (e.g., 4.55 → 1.57)
    assert abs(estimate_ten_split(4.40) - 4.40 * 0.346) < 0.001


def test_compute_z_score():
    z = compute_z_score(sparq=120.0, pos='WR')
    assert isinstance(z, float)
    assert z > 0  # 120 is above WR mean (~116)


def test_compute_nfl_percentile_at_mean():
    pct = compute_nfl_percentile(z_score=0.0)
    assert abs(pct - 50.0) < 0.5


def test_compute_nfl_percentile_above_mean():
    pct = compute_nfl_percentile(z_score=1.0)
    assert 80 < pct < 90


def test_compute_psparq_exactly_min_inputs():
    # Exactly 4 real inputs (weight + forty + vertical + broad) — should compute (MIN_REAL_INPUTS = 4)
    result = compute_psparq(
        weight=210, vertical=36.0, broad=120,
        bench=None, forty=4.55, ten_split=None,
        shuttle=None, cone=None, pos='RB'
    )
    assert result is not None


def test_compute_psparq_below_min_inputs():
    # Only 3 real inputs — should return None (MIN_REAL_INPUTS = 4)
    result = compute_psparq(
        weight=210, vertical=36.0, broad=None,
        bench=None, forty=4.55, ten_split=None,
        shuttle=None, cone=None, pos='RB'
    )
    assert result is None


def test_compute_psparq_ten_split_only_speed():
    # No forty provided — ten_split used as speed fallback
    result = compute_psparq(
        weight=210, vertical=36.0, broad=120,
        bench=21, forty=None, ten_split=1.55,
        shuttle=4.10, cone=7.10, pos='RB'
    )
    assert result is not None
