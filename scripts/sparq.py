import math
from typing import Optional

# pSPARQ coefficients — community approximation of Nike SPARQ formula
# Validate during implementation: spot-check known players vs 3sigmaathlete.com
# Note: the formula uses forty OR ten_split (not both simultaneously).
# ten_split is used only when forty is unavailable (estimate_ten_split provides it).
# Intercept calibrated so median WR ≈ 116, median OL ≈ 89 (matches POSITIONAL_STATS means).
COEFFS = {
    'weight':    0.0808,
    'vertical':  1.2796,
    'broad_ft':  1.5768,   # broad jump converted to feet
    'bench':     0.7616,
    'forty':   -26.728,    # forty OR ten_split (forty preferred when present)
    'shuttle':  -10.504,
    'cone':      -8.916,
    'intercept': 250.3,
}

# Historical NFL positional means and standard deviations
# Approximated from 3sigmaathlete methodology, 1999–2023 combine data
POSITIONAL_STATS = {
    'QB':   {'mean': 95.0,  'std': 14.5},
    'RB':   {'mean': 111.0, 'std': 12.0},
    'WR':   {'mean': 116.0, 'std': 14.0},
    'TE':   {'mean': 104.0, 'std': 11.5},
    'OL':   {'mean': 89.0,  'std': 10.0},
    'DL':   {'mean': 96.0,  'std': 11.5},
    'EDGE': {'mean': 106.0, 'std': 12.0},
    'LB':   {'mean': 106.0, 'std': 11.5},
    'CB':   {'mean': 116.0, 'std': 13.5},
    'S':    {'mean': 110.0, 'std': 12.5},
}

# Fallback positional medians for imputing missing drills
POSITIONAL_MEDIANS = {
    'QB':   {'bench': 22, 'cone': 7.10, 'shuttle': 4.30, 'vertical': 33.0, 'broad': 114, 'ten_split': 1.60},
    'RB':   {'bench': 21, 'cone': 7.00, 'shuttle': 4.15, 'vertical': 36.0, 'broad': 122, 'ten_split': 1.53},
    'WR':   {'bench': 12, 'cone': 6.80, 'shuttle': 4.10, 'vertical': 37.0, 'broad': 125, 'ten_split': 1.52},
    'TE':   {'bench': 22, 'cone': 7.05, 'shuttle': 4.25, 'vertical': 35.0, 'broad': 120, 'ten_split': 1.55},
    'OL':   {'bench': 27, 'cone': 7.60, 'shuttle': 4.65, 'vertical': 28.0, 'broad': 103, 'ten_split': 1.72},
    'DL':   {'bench': 26, 'cone': 7.40, 'shuttle': 4.50, 'vertical': 32.0, 'broad': 112, 'ten_split': 1.65},
    'EDGE': {'bench': 22, 'cone': 7.20, 'shuttle': 4.35, 'vertical': 34.0, 'broad': 118, 'ten_split': 1.58},
    'LB':   {'bench': 22, 'cone': 7.15, 'shuttle': 4.30, 'vertical': 35.0, 'broad': 119, 'ten_split': 1.57},
    'CB':   {'bench': 14, 'cone': 6.75, 'shuttle': 4.05, 'vertical': 37.5, 'broad': 126, 'ten_split': 1.51},
    'S':    {'bench': 16, 'cone': 6.90, 'shuttle': 4.15, 'vertical': 36.5, 'broad': 122, 'ten_split': 1.53},
}

MIN_REAL_INPUTS = 5


def estimate_ten_split(forty: float) -> float:
    """Estimate 10-yard split from 40-yard dash time."""
    return forty * 0.626


def compute_psparq(
    weight: Optional[float],
    vertical: Optional[float],
    broad: Optional[float],     # inches
    bench: Optional[float],
    forty: Optional[float],
    ten_split: Optional[float],
    shuttle: Optional[float],
    cone: Optional[float],
    pos: Optional[str] = None,
) -> Optional[float]:
    """
    Compute pSPARQ. Returns None if fewer than MIN_REAL_INPUTS are non-null
    before imputation. Missing values imputed from positional medians when pos
    is provided.
    """
    real_count = sum(1 for v in [weight, vertical, broad, bench, forty, ten_split, shuttle, cone]
                     if v is not None)
    if real_count < MIN_REAL_INPUTS:
        return None

    # Estimate ten_split from forty before falling back to medians
    if ten_split is None and forty is not None:
        ten_split = estimate_ten_split(forty)

    # Impute remaining missing from positional medians
    if pos and pos in POSITIONAL_MEDIANS:
        med = POSITIONAL_MEDIANS[pos]
        if vertical   is None: vertical   = med['vertical']
        if broad      is None: broad      = med['broad']
        if bench      is None: bench      = med['bench']
        if shuttle    is None: shuttle    = med['shuttle']
        if cone       is None: cone       = med['cone']
        if ten_split  is None: ten_split  = med['ten_split']

    # Use forty when available; fall back to ten_split as a speed proxy
    speed = forty if forty is not None else ten_split

    if any(v is None for v in [weight, vertical, broad, bench, speed, shuttle, cone]):
        return None

    score = (
        COEFFS['weight']    * weight
      + COEFFS['vertical']  * vertical
      + COEFFS['broad_ft']  * (broad / 12.0)
      + COEFFS['bench']     * bench
      + COEFFS['forty']     * speed
      + COEFFS['shuttle']   * shuttle
      + COEFFS['cone']      * cone
      + COEFFS['intercept']
    )
    return round(score, 2)


def compute_z_score(sparq: float, pos: str) -> float:
    """Z-score vs historical NFL positional average."""
    stats = POSITIONAL_STATS.get(pos, {'mean': 105.0, 'std': 12.0})
    return round((sparq - stats['mean']) / stats['std'], 2)


def compute_nfl_percentile(z_score: float) -> float:
    """Convert z-score to one-sided normal percentile."""
    return round(50.0 * (1.0 + math.erf(z_score / math.sqrt(2))), 1)
