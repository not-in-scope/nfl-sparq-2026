"""Regression tests for the NFL SPARQ data pipeline.

These tests validate against known-good data from the 2020 draft class,
covering every bug that was caught and fixed during development.

Run against pre-generated data files (does not re-scrape):
  py -3 -m pytest tests/test_pipeline_regression.py -v
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


@pytest.fixture(scope='module')
def prospects_2020():
    path = os.path.join(DATA_DIR, 'prospects_2020.json')
    if not os.path.exists(path):
        pytest.skip('prospects_2020.json not found — run: py -3 scripts/scrape.py --year 2020')
    return json.load(open(path))['prospects']


@pytest.fixture(scope='module')
def by_name_2020(prospects_2020):
    return {p['name']: p for p in prospects_2020}


# ---------------------------------------------------------------------------
# Position correctness (regression: nflcombineresults.com has wrong positions;
# ESPN override is authoritative for historical data)
# ---------------------------------------------------------------------------

def test_jacob_phillips_is_lb_not_ot(by_name_2020):
    """Jacob Phillips was listed as OT on nflcombineresults.com. ESPN override must fix this."""
    p = by_name_2020.get('Jacob Phillips')
    assert p is not None, 'Jacob Phillips not found'
    assert p['pos'] == 'LB', f"Expected LB, got {p['pos']}"


def test_chase_young_is_edge(by_name_2020):
    """DE should be normalized to EDGE via _POS_NORMALIZE."""
    p = by_name_2020.get('Chase Young')
    assert p is not None, 'Chase Young not found'
    assert p['pos'] == 'EDGE', f"Expected EDGE, got {p['pos']}"


def test_jedrick_wills_is_ot(by_name_2020):
    p = by_name_2020.get('Jedrick Wills')
    assert p is not None, 'Jedrick Wills not found'
    assert p['pos'] == 'OT', f"Expected OT, got {p['pos']}"


# ---------------------------------------------------------------------------
# Draft pick data (regression: all known 2020 picks must be present and non-negative)
# ---------------------------------------------------------------------------

KNOWN_PICKS_2020 = [
    # (name, round, within_round_pick, team)
    ('Chase Young',     1,  2,  'WSH'),
    ('Jedrick Wills',   1, 10,  'CLE'),
    ('Henry Ruggs',     1, 12,  'LV'),
    ('A.J. Dillon',     2, 30,  'GB'),
    ('Willie Gay',      2, 31,  'KC'),
    ('Jacob Phillips',  3, 33,  'CLE'),
]


@pytest.mark.parametrize('name,expected_round,expected_pick,expected_team', KNOWN_PICKS_2020)
def test_known_pick_present(by_name_2020, name, expected_round, expected_pick, expected_team):
    """Every named 2020 pick must appear with correct round, pick, and team."""
    # Try exact name first, then normalized (handles suffixes like Jr./III)
    p = by_name_2020.get(name)
    if p is None:
        # Try case-insensitive substring match
        matches = [v for k, v in by_name_2020.items() if name.lower() in k.lower()]
        assert matches, f'{name!r} not found in prospects_2020'
        p = matches[0]

    assert p['draft_round'] == expected_round, (
        f"{name}: expected R{expected_round}, got R{p['draft_round']}"
    )
    assert p['draft_pick'] == expected_pick, (
        f"{name}: expected pick {expected_pick}, got {p['draft_pick']}"
    )
    assert p['team'] == expected_team, (
        f"{name}: expected team {expected_team}, got {p['team']}"
    )


def test_no_negative_pick_numbers(prospects_2020):
    """No player should have a negative draft pick number (regression: ROUND_STARTS bug)."""
    bad = [
        p for p in prospects_2020
        if p.get('draft_pick') is not None and p['draft_pick'] < 0
    ]
    assert not bad, f"Players with negative pick numbers: {[(p['name'], p['draft_pick']) for p in bad]}"


def test_no_pick_above_round_max(prospects_2020):
    """Within-round pick number should never exceed 50 (NFL rounds max ~36 with comp picks)."""
    bad = [
        p for p in prospects_2020
        if p.get('draft_pick') is not None and p['draft_pick'] > 50
    ]
    assert not bad, f"Suspiciously large pick numbers: {[(p['name'], p['draft_round'], p['draft_pick']) for p in bad]}"


# ---------------------------------------------------------------------------
# Name matching (regression: A.J. Dillon, Henry Ruggs III, Willie Gay Jr.)
# ---------------------------------------------------------------------------

def test_aj_dillon_matched(by_name_2020):
    """A.J. Dillon (with periods) must be matched via _norm_name fuzzy lookup."""
    # Could be stored as 'A.J. Dillon' or 'AJ Dillon' depending on combine source
    names = [k for k in by_name_2020 if 'dillon' in k.lower()]
    assert names, 'No player with "dillon" in name found'
    p = by_name_2020[names[0]]
    assert p['draft_round'] is not None, f"A.J. Dillon ({names[0]}) has no draft round"
    assert p['team'] == 'GB'


def test_henry_ruggs_matched(by_name_2020):
    """Henry Ruggs III must be matched despite 'III' suffix in ESPN vs combine source."""
    names = [k for k in by_name_2020 if 'ruggs' in k.lower()]
    assert names, 'No player with "ruggs" in name found'
    p = by_name_2020[names[0]]
    assert p['draft_round'] == 1
    assert p['team'] == 'LV'


def test_willie_gay_matched(by_name_2020):
    """Willie Gay Jr. must be matched despite Jr. suffix difference."""
    names = [k for k in by_name_2020 if 'gay' in k.lower()]
    assert names, 'No player with "gay" in name found'
    p = by_name_2020[names[0]]
    assert p['draft_round'] == 2
    assert p['team'] == 'KC'


# ---------------------------------------------------------------------------
# Team data (regression: team was always None for historical data)
# ---------------------------------------------------------------------------

def test_drafted_players_have_teams(prospects_2020):
    """Every player with round_source='actual' must have a team abbreviation."""
    actual_picks = [p for p in prospects_2020 if p.get('round_source') == 'actual']
    missing_team = [p for p in actual_picks if not p.get('team')]
    # Allow a small tolerance (a few picks may fail ESPN lookup due to network)
    pct_missing = len(missing_team) / len(actual_picks) if actual_picks else 0
    assert pct_missing < 0.05, (
        f"{len(missing_team)}/{len(actual_picks)} drafted players missing team: "
        f"{[p['name'] for p in missing_team[:10]]}"
    )


def test_undrafted_players_have_no_team(prospects_2020):
    """Players with no draft round should have team=None."""
    undrafted = [p for p in prospects_2020 if p.get('draft_round') is None]
    with_team = [p for p in undrafted if p.get('team')]
    assert not with_team, f"Undrafted players incorrectly have team: {[p['name'] for p in with_team[:5]]}"


# ---------------------------------------------------------------------------
# SPARQ coverage (regression: too few players scored due to MIN_REAL_INPUTS bug)
# ---------------------------------------------------------------------------

def test_sparq_coverage_above_threshold(prospects_2020):
    """At least 65% of 2020 prospects should have a SPARQ score (was blocked at ~37%)."""
    scored = sum(1 for p in prospects_2020 if p.get('sparq') is not None)
    pct = scored / len(prospects_2020)
    assert pct >= 0.65, f"Only {pct:.0%} scored ({scored}/{len(prospects_2020)})"


def test_sparq_scores_are_positive(prospects_2020):
    """All SPARQ scores should be positive (formula intercept ensures this for valid inputs)."""
    bad = [p for p in prospects_2020 if p.get('sparq') is not None and p['sparq'] <= 0]
    assert not bad, f"Non-positive SPARQ scores: {[(p['name'], p['sparq']) for p in bad]}"


# ---------------------------------------------------------------------------
# Height (regression: displayed as "6'3.6" — decimal inches are stored correctly
# in data; frontend uses Math.round before feet/inches split)
# ---------------------------------------------------------------------------

def test_height_is_reasonable_range(prospects_2020):
    """Heights in inches should be in a plausible NFL player range (60–84 inches = 5'0"–7'0")."""
    bad = [
        p for p in prospects_2020
        if p.get('height') is not None and not (60 <= p['height'] <= 84)
    ]
    assert not bad, f"Heights outside plausible range: {[(p['name'], p['height']) for p in bad]}"


# ---------------------------------------------------------------------------
# Position normalization (regression: DE must map to EDGE, no bare 'DE' in output)
# ---------------------------------------------------------------------------

def test_no_bare_de_position(prospects_2020):
    """'DE' should be normalized to 'EDGE' — no player should have pos='DE'."""
    bad = [p for p in prospects_2020 if p.get('pos') == 'DE']
    assert not bad, f"Players still have pos='DE': {[p['name'] for p in bad]}"


def test_round_source_values(prospects_2020):
    """round_source must be 'actual', 'mock', or None — no other values."""
    valid = {'actual', 'mock', None}
    bad = [p for p in prospects_2020 if p.get('round_source') not in valid]
    assert not bad, f"Invalid round_source values: {[(p['name'], p['round_source']) for p in bad[:5]]}"
