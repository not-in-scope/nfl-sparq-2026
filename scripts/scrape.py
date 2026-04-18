#!/usr/bin/env python3
"""
NFL SPARQ 2026 data pipeline.

Usage:
  python scripts/scrape.py                       # Full scrape, writes data/prospects.json
  python scripts/scrape.py --add-draft-results   # Post-draft: update from ESPN
"""
import json
import argparse
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from sparq import compute_psparq, compute_z_score, compute_nfl_percentile, estimate_ten_split
from sources.bigboardlab import fetch_combine_data
from sources.mockdraftable import enrich_players
from sources.pff import fetch_pff_proday
from sources.espn_draft import fetch_espn_draft_board
from sources.espn_weight import fetch_weight

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
OUTPUT_PATH = os.path.join(DATA_DIR, 'prospects.json')           # legacy alias
YEAR = 2026
YEAR_PATH = os.path.join(DATA_DIR, f'prospects_{YEAR}.json')    # canonical


def _count_real(player: dict) -> int:
    return sum(1 for v in player['metrics'].values()
               if v.get('source') in ('combine', 'pro_day'))


def _count_estimated(player: dict) -> int:
    return sum(1 for v in player['metrics'].values() if v.get('source') == 'estimated')


def _sparq_source_label(player: dict) -> str | None:
    if _count_real(player) == 0:
        return None
    return 'real' if _count_estimated(player) == 0 else 'estimated'


def apply_estimation(players: list[dict]) -> list[dict]:
    """Estimate missing inputs; mark source as 'estimated'."""
    for player in players:
        m = player['metrics']
        # Estimate 10-split from forty when missing
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
    'T':   'OT',   # ESPN: tackle
    'G':   'OG',   # ESPN: guard
    'DI':  'DT',   # ESPN: defensive interior
    'OLB': 'LB',
    'ILB': 'LB',
    'MLB': 'LB',
    'NT':  'DT',
    'SAF': 'S',
}


def _normalize_pos(pos: str) -> str:
    return _POS_NORMALIZE.get(pos, pos)


def apply_mock_rounds(players: list[dict], board: dict) -> list[dict]:
    """Apply ESPN draft board round/pick data. Also override pos from ESPN when
    BigBoardLab left a coarse group and PFF didn't match this player."""
    for player in players:
        entry = board.get(player['name'], {})
        rnd  = entry.get('draft_round')
        pick = entry.get('draft_pick')
        player['draft_round'] = rnd
        player['draft_pick']  = pick
        player['round_source'] = 'mock' if rnd is not None else None
        player.setdefault('team', None)   # filled in post-draft by --add-draft-results
        # Use ESPN fine-grained position if player still has a coarse BBL group
        espn_pos = entry.get('espn_pos', '')
        if espn_pos and player.get('pos') in ('OL', 'DL', 'DB'):
            player['pos'] = _normalize_pos(espn_pos)
    return players


def merge_pff(players: list[dict], pff_data: dict) -> list[dict]:
    for player in players:
        pff = pff_data.get(player['name'], {})
        if not pff:
            continue
        # Override coarse BigBoardLab position groups with PFF's fine-grained labels
        pff_pos = pff.get('pff_pos')
        if pff_pos and player.get('pos') in ('OL', 'DL', 'DB'):
            player['pos'] = _normalize_pos(pff_pos)
        for field in ('forty', 'ten_split', 'vertical', 'broad', 'bench', 'cone', 'shuttle'):
            if field not in pff:
                continue
            existing = player['metrics'].get(field, {})
            # MockDraftable (Pass 2) takes precedence over PFF (Pass 3) for pro_day values
            if existing.get('source') in ('combine', 'pro_day'):
                continue
            if existing.get('value') is None:
                player['metrics'][field] = {'value': pff[field], 'source': 'pro_day'}
    return players


def rank_players(players: list[dict]) -> list[dict]:
    # Rank by position-relative z_score (σ) so Styles +2.34σ > Burks +1.23σ.
    # Players without SPARQ sort to the bottom.
    players.sort(key=lambda p: (p['z_score'] is None, -(p['z_score'] or 0)))
    for i, player in enumerate(players, 1):
        player['rank'] = i
    return players


def scrape() -> list[dict]:
    print("Pass 1: Fetching BigBoardLab combine data...")
    players = fetch_combine_data()
    print(f"  {len(players)} players loaded.")

    print("Pass 2: Enriching from MockDraftable (pro day + 10-split)...")
    players = enrich_players(players, rate_limit=1.0)

    print("Pass 3: Fetching PFF pro day tracker...")
    pff_data = fetch_pff_proday()
    players = merge_pff(players, pff_data)
    print(f"  PFF matched {len(pff_data)} players.")

    print("Fetching ESPN draft board for mock round data...")
    board = fetch_espn_draft_board()
    players = apply_mock_rounds(players, board)
    with_round = sum(1 for p in players if p['draft_round'] is not None)
    print(f"  {with_round} players with mock round data.")

    print("Pass 4: Fetching missing weights from ESPN college rosters...")
    players = fetch_missing_weights(players)

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
    parser.add_argument('--add-draft-results', action='store_true',
                        help='Post-draft: update round/pick from ESPN (run after April 25)')
    args = parser.parse_args()

    if args.add_draft_results:
        print("Post-draft update: run after April 25, 2026. Not yet implemented.")
        return

    players = scrape()
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = {'updated': date.today().isoformat(), 'count': len(players), 'prospects': players}
    for path in (YEAR_PATH, OUTPUT_PATH):
        with open(path, 'w') as f:
            json.dump(payload, f, indent=2)
        print(f"Written: {path}")


if __name__ == '__main__':
    main()
