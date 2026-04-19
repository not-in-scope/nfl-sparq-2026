#!/usr/bin/env python3
"""
NFL SPARQ data pipeline.

Usage:
  python scripts/scrape.py                       # 2026 scrape, writes data/prospects_2026.json
  python scripts/scrape.py --year 2020           # Historical year
  python scripts/scrape.py --add-draft-results   # Post-draft: update from ESPN (2026 only)
"""
import json
import argparse
import sys
import os
from datetime import date
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from sparq import compute_psparq, compute_z_score, compute_nfl_percentile, estimate_ten_split
from sources.bigboardlab import fetch_combine_data
from sources.nflcombine import fetch_combine_data_historical
from sources.mockdraftable import enrich_players
from sources.pff import fetch_pff_proday
from sources.espn_draft import fetch_espn_draft_board
from sources.espn_weight import fetch_weight

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_PATH = os.path.join(DATA_DIR, 'prospects.json')   # legacy alias (2026)


def _count_real(player: dict) -> int:
    return sum(1 for v in player['metrics'].values()
               if v.get('source') in ('combine', 'pro_day'))


def _count_estimated(player: dict) -> int:
    return sum(1 for v in player['metrics'].values() if v.get('source') == 'estimated')


def _sparq_source_label(player: dict) -> str | None:
    if _count_real(player) == 0:
        return None
    return 'real' if _count_estimated(player) == 0 else 'estimated'


# Physical bounds for combine metrics — values outside these are data entry errors
_METRIC_BOUNDS = {
    'bench':     (1,    51),    # all-time record: 51 (Justin Ernest, 1999)
    'forty':     (4.20, 6.00),
    'ten_split': (1.30, 2.20),
    'vertical':  (15,   50),
    'broad':     (80,  160),    # inches; 8-10 foot values are a site error
    'shuttle':   (3.70, 5.50),
    'cone':      (6.00, 9.00),
    'weight':    (140,  390),   # Daniel Faalele was 384 lbs
}


def sanitize_metrics(players: list[dict]) -> list[dict]:
    """Null out metric values that are physically impossible (data entry errors)."""
    for player in players:
        m = player['metrics']
        for field, (lo, hi) in _METRIC_BOUNDS.items():
            entry = m.get(field, {})
            v = entry.get('value')
            if v is not None and (v < lo or v > hi):
                m[field] = {'value': None, 'source': None}
    return players


def apply_estimation(players: list[dict]) -> list[dict]:
    """Estimate missing inputs; mark source as 'estimated'."""
    for player in players:
        m = player['metrics']
        if m['ten_split'].get('value') is None and m['forty'].get('value') is not None:
            m['ten_split'] = {
                'value': round(estimate_ten_split(m['forty']['value']), 3),
                'source': 'estimated',
            }
    return players


def fetch_missing_weights(players: list[dict]) -> list[dict]:
    """Look up weight from ESPN college roster for players missing it with 3+ real metrics."""
    missing = [
        p for p in players
        if p['metrics']['weight']['value'] is None
        and sum(1 for k, v in p['metrics'].items()
                if k != 'weight' and v.get('source') in ('combine', 'pro_day')) >= 3
    ]
    if not missing:
        return players
    print(f"  Fetching ESPN weights for {len(missing)} players with missing weight...")
    for player in missing:
        wt = fetch_weight(player['name'])
        if wt is not None:
            player['metrics']['weight'] = {'value': wt, 'source': 'college_roster'}
            print(f"    {player['name']}: {wt} lbs")
        else:
            print(f"    {player['name']}: not found")
    return players


def compute_sparq_scores(players: list[dict]) -> list[dict]:
    for player in players:
        m = player['metrics']
        sparq = compute_psparq(
            weight=m['weight'].get('value'),
            vertical=m['vertical'].get('value'),
            broad=m['broad'].get('value'),
            bench=m['bench'].get('value'),
            forty=m['forty'].get('value'),
            ten_split=m['ten_split'].get('value'),
            shuttle=m['shuttle'].get('value'),
            cone=m['cone'].get('value'),
            pos=player.get('pos'),
        )
        player['sparq'] = sparq
        player['sparq_source'] = _sparq_source_label(player) if sparq else None
        if sparq:
            z = compute_z_score(sparq, player.get('pos', ''))
            player['z_score'] = z
            player['nfl_pct'] = compute_nfl_percentile(z)
        else:
            player['z_score'] = None
            player['nfl_pct'] = None
    return players


# Normalize non-standard position abbreviations to NFL standard
_POS_NORMALIZE = {
    'T':   'OT',    # ESPN: tackle
    'G':   'OG',    # ESPN: guard
    'DI':  'DT',    # ESPN: defensive interior
    'OLB': 'LB',
    'ILB': 'LB',
    'MLB': 'LB',
    'NT':  'DT',
    'SAF': 'S',
    'DE':  'EDGE',  # modern terminology; use EDGE stats for all edge rushers
}


def _normalize_pos(pos: str) -> str:
    return _POS_NORMALIZE.get(pos, pos)


import re as _re


def _norm_name(name: str) -> str:
    """Normalize player name for fuzzy matching.

    Strips name suffixes (Jr./Sr./II/III), removes periods (A.J. → AJ),
    and lowercases. Allows matching across data sources with different
    formatting conventions.
    """
    n = name.lower()
    n = _re.sub(r'\b(jr\.?|sr\.?|ii|iii|iv)\b', '', n)
    n = _re.sub(r'\.', '', n)
    n = _re.sub(r'\s+', ' ', n).strip()
    return n


def _school_matches(player_school: str, espn_college: Optional[str]) -> bool:
    """True if player's school is plausibly the same as ESPN's college name."""
    if not player_school or not espn_college:
        return False
    return player_school.lower().strip() == espn_college.lower().strip()


def apply_espn_data(players: list[dict], board: dict) -> list[dict]:
    """Apply ESPN draft board data: round/pick, height, and fine-grained position.

    When two combine players share a name, uses ESPN's college to assign draft
    data only to the player whose school matches (disambiguation).
    """
    # Build a normalized name → entry lookup for fuzzy fallback
    norm_board = {_norm_name(k): v for k, v in board.items()}

    # Detect duplicate names in combine data — they need school-based disambiguation
    name_counts: dict = {}
    for p in players:
        key = _norm_name(p['name'])
        name_counts[key] = name_counts.get(key, 0) + 1
    duplicate_norm_names = {k for k, c in name_counts.items() if c > 1}

    # Track which (round, pick) slots have been assigned to prevent double-assigns
    assigned_picks: set = set()

    for player in players:
        norm = _norm_name(player['name'])
        raw_entry = board.get(player['name']) or norm_board.get(norm)

        # Resolve list entries (ESPN has multiple players with same name, e.g. two Byron Youngs)
        if isinstance(raw_entry, list):
            player_school = player.get('school', '')
            # Pick the entry whose espn_college matches this player's school
            match = next(
                (e for e in raw_entry if _school_matches(player_school, e.get('espn_college'))),
                None
            )
            entry = match or {}
        else:
            entry = raw_entry or {}

        # When multiple combine players share a name (but ESPN only has one),
        # require school match to avoid assigning the pick to the wrong player
        if norm in duplicate_norm_names and entry and not isinstance(raw_entry, list):
            espn_college = entry.get('espn_college')
            player_school = player.get('school', '')
            if espn_college and not _school_matches(player_school, espn_college):
                entry = {}   # wrong player — don't apply draft data

        # Also guard against double-assigning the same pick to a second player
        rnd  = entry.get('draft_round')
        pick = entry.get('draft_pick')
        pick_key = (rnd, pick)
        if rnd is not None and pick_key in assigned_picks:
            entry = {}
            rnd, pick = None, None
        elif rnd is not None:
            assigned_picks.add(pick_key)

        player['draft_round']  = rnd
        player['draft_pick']   = pick
        player['round_source'] = entry.get('round_source')
        # Use ESPN team for historical (actual picks); preserve any existing team for 2026
        espn_team = entry.get('team')
        if espn_team:
            player['team'] = espn_team
        else:
            player.setdefault('team', None)

        # Height from ESPN if not already set
        espn_height = entry.get('height')
        if player.get('height') is None and espn_height is not None:
            player['height'] = espn_height

        espn_pos = entry.get('espn_pos', '')
        if espn_pos:
            is_actual = entry.get('round_source') == 'actual'
            if is_actual:
                # For historical data, ESPN's position is authoritative —
                # nflcombineresults.com can have wrong positions (e.g. Jacob Phillips as OT)
                player['pos'] = _normalize_pos(espn_pos)
            elif player.get('pos') in ('OL', 'DL', 'DB'):
                # For 2026 projected: only override coarse BBL position groups
                player['pos'] = _normalize_pos(espn_pos)

    return players


# Keep old name as alias for backward-compat with tests
def apply_mock_rounds(players: list[dict], board: dict) -> list[dict]:
    return apply_espn_data(players, board)


def merge_pff(players: list[dict], pff_data: dict) -> list[dict]:
    for player in players:
        pff = pff_data.get(player['name'], {})
        if not pff:
            continue
        pff_pos = pff.get('pff_pos')
        if pff_pos and player.get('pos') in ('OL', 'DL', 'DB'):
            player['pos'] = _normalize_pos(pff_pos)
        for field in ('forty', 'ten_split', 'vertical', 'broad', 'bench', 'cone', 'shuttle'):
            if field not in pff:
                continue
            existing = player['metrics'].get(field, {})
            if existing.get('source') in ('combine', 'pro_day'):
                continue
            if existing.get('value') is None:
                player['metrics'][field] = {'value': pff[field], 'source': 'pro_day'}
    return players


def rank_players(players: list[dict]) -> list[dict]:
    players.sort(key=lambda p: (p['z_score'] is None, -(p['z_score'] or 0)))
    for i, player in enumerate(players, 1):
        player['rank'] = i
    return players


def _ensure_height(player: dict) -> dict:
    """Ensure player has a 'height' key (None if unknown)."""
    player.setdefault('height', None)
    return player


def scrape_2026() -> list[dict]:
    print("Pass 1: Fetching BigBoardLab combine data...")
    players = fetch_combine_data()
    for p in players:
        p.setdefault('height', None)
    print(f"  {len(players)} players loaded.")

    print("Pass 2: Enriching from MockDraftable (pro day + 10-split)...")
    players = enrich_players(players, rate_limit=1.0)

    print("Pass 3: Fetching PFF pro day tracker...")
    pff_data = fetch_pff_proday()
    players = merge_pff(players, pff_data)
    print(f"  PFF matched {len(pff_data)} players.")

    print("Fetching ESPN draft board for mock round data + height...")
    board = fetch_espn_draft_board(year=2026)
    players = apply_espn_data(players, board)
    with_round = sum(1 for p in players if p['draft_round'] is not None)
    print(f"  {with_round} players with mock round data.")

    print("Pass 4: Fetching missing weights from ESPN college rosters...")
    players = fetch_missing_weights(players)

    print("Sanitizing out-of-range metric values...")
    players = sanitize_metrics(players)

    print("Applying estimation for missing inputs...")
    players = apply_estimation(players)

    print("Computing pSPARQ scores...")
    players = compute_sparq_scores(players)
    players = rank_players(players)

    scored = sum(1 for p in players if p['sparq'] is not None)
    print(f"  SPARQ computed for {scored}/{len(players)} players.")
    return players


def scrape_historical(year: int) -> list[dict]:
    print(f"Pass 1: Fetching combine data from nflcombineresults.com ({year})...")
    players = fetch_combine_data_historical(year)
    for p in players:
        p['pos'] = _normalize_pos(p['pos'])
    print(f"  {len(players)} players loaded.")

    print("Pass 2: Enriching from MockDraftable (pro day + 10-split)...")
    players = enrich_players(players, rate_limit=1.0)

    print(f"Fetching ESPN {year} draft board for actual picks + height...")
    board = fetch_espn_draft_board(year=year)
    players = apply_espn_data(players, board)
    with_round = sum(1 for p in players if p['draft_round'] is not None)
    print(f"  {with_round} players with actual draft round data.")

    print("Sanitizing out-of-range metric values...")
    players = sanitize_metrics(players)

    print("Applying estimation for missing inputs...")
    players = apply_estimation(players)

    print("Computing pSPARQ scores...")
    players = compute_sparq_scores(players)
    players = rank_players(players)

    scored = sum(1 for p in players if p['sparq'] is not None)
    print(f"  SPARQ computed for {scored}/{len(players)} players.")
    return players


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, default=2026,
                        help='Draft class year (default: 2026)')
    parser.add_argument('--add-draft-results', action='store_true',
                        help='Post-draft: update round/pick from ESPN (run after April 25)')
    args = parser.parse_args()

    if args.add_draft_results:
        print("Post-draft update: run after April 25, 2026. Not yet implemented.")
        return

    year = args.year
    if year == 2026:
        players = scrape_2026()
    else:
        players = scrape_historical(year)

    os.makedirs(DATA_DIR, exist_ok=True)
    year_path = os.path.join(DATA_DIR, f'prospects_{year}.json')
    payload = {'updated': date.today().isoformat(), 'count': len(players), 'prospects': players}

    paths = [year_path]
    if year == 2026:
        paths.append(OUTPUT_PATH)   # legacy alias

    for path in paths:
        with open(path, 'w') as f:
            json.dump(payload, f, indent=2)
        print(f"Written: {path}")


if __name__ == '__main__':
    main()
