#!/usr/bin/env python3
"""
Real-time NFL Draft SPARQ tweet bot.

Polls ESPN during the draft and tweets each pick's SPARQ score + historical comp.
Skips players with no SPARQ score.

Usage:
  py -3 scripts/draft_bot.py            # live mode
  py -3 scripts/draft_bot.py --dry-run  # print tweets, don't post
  py -3 scripts/draft_bot.py --year 2025 --dry-run  # test against historical year
"""
import argparse
import json
import math
import os
import re
import sys
import time
from typing import Optional

import requests

sys.path.insert(0, os.path.dirname(__file__))
from scrape import _norm_name

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; nfl-sparq-bot/1.0)"}
_BASE = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{year}/draft/athletes"
_PICK_REF_RE = re.compile(r'/rounds/(\d+)/picks/(\d+)')

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
STATE_PATH = os.path.join(DATA_DIR, 'draft_bot_state.json')

SITE_URL = "not-in-scope.github.io/nfl-sparq/"
POLL_INTERVAL = 60  # seconds


# ── Sigma tier ────────────────────────────────────────────────────────────────

def sigma_tier(z: float) -> str:
    if z >= 2.0:  return 'ELITE'
    if z >= 1.0:  return 'GREAT'
    if z >= 0.0:  return 'GOOD'
    if z >= -1.0: return 'AVERAGE'
    if z >= -2.0: return 'BELOW AVG'
    return 'POOR'


# ── Data loading ──────────────────────────────────────────────────────────────

def load_prospects(year: int) -> dict:
    """Return norm_name → player dict for a given year."""
    path = os.path.join(DATA_DIR, f'prospects_{year}.json')
    d = json.load(open(path))
    return {_norm_name(p['name']): p for p in d['prospects']}


def build_historical_index() -> list:
    """Load 2010–2025 prospects with z_score for comp matching."""
    index = []
    for year in range(2010, 2026):
        path = os.path.join(DATA_DIR, f'prospects_{year}.json')
        if not os.path.exists(path):
            continue
        d = json.load(open(path))
        for p in d['prospects']:
            if p.get('z_score') is not None and p.get('pos'):
                index.append({
                    'name': p['name'],
                    'year': year,
                    'pos': p['pos'],
                    'z_score': p['z_score'],
                })
    return index


def find_comp(pos: str, z_score: float, index: list) -> Optional[dict]:
    """Find the historical player with the closest z_score at the same position."""
    candidates = [e for e in index if e['pos'] == pos]
    if not candidates:
        # fallback: skip position filter
        candidates = index
    if not candidates:
        return None
    return min(candidates, key=lambda e: abs(e['z_score'] - z_score))


# ── State persistence ─────────────────────────────────────────────────────────

def load_state() -> set:
    """Return set of already-tweeted (round, pick) tuples."""
    if not os.path.exists(STATE_PATH):
        return set()
    d = json.load(open(STATE_PATH))
    return {tuple(k) for k in d.get('seen', [])}


def save_state(seen: set):
    with open(STATE_PATH, 'w') as f:
        json.dump({'seen': [list(k) for k in seen]}, f)


# ── ESPN polling ──────────────────────────────────────────────────────────────

def poll_espn_picks(year: int) -> list:
    """Return list of all picks made so far: [{round, pick, name, team}]."""
    base = _BASE.format(year=year)
    refs = []
    page = 1
    while True:
        try:
            r = requests.get(base, params={'limit': 100, 'page': page},
                             headers=_HEADERS, timeout=20)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  ESPN fetch error: {e}")
            return []
        data = r.json()
        items = data.get('items', [])
        if not items:
            break
        refs.extend(item['$ref'] for item in items if '$ref' in item)
        if len(refs) >= data.get('count', 0):
            break
        page += 1

    picks = []
    for ref in refs:
        try:
            athlete = requests.get(ref, headers=_HEADERS, timeout=15).json()
        except requests.RequestException:
            continue

        pick_ref = athlete.get('pick', {}).get('$ref', '')
        if not pick_ref:
            continue  # not yet picked

        m = _PICK_REF_RE.search(pick_ref)
        if not m:
            continue
        rnd, pick = int(m.group(1)), int(m.group(2))
        name = athlete.get('fullName', '').strip()

        # Get drafting team from pick JSON
        team = None
        try:
            pick_data = requests.get(pick_ref.split('?')[0], headers=_HEADERS, timeout=10).json()
            team_ref = pick_data.get('team', {}).get('$ref', '')
            if team_ref:
                team_data = requests.get(team_ref.split('?')[0], headers=_HEADERS, timeout=10).json()
                team = team_data.get('abbreviation')
        except requests.RequestException:
            pass

        picks.append({'round': rnd, 'pick': pick, 'name': name, 'team': team or '???'})

    return picks


# ── Tweet builder ─────────────────────────────────────────────────────────────

def overall_pick_number(rnd: int, pick: int) -> int:
    round_starts = {1: 0, 2: 32, 3: 64, 4: 96, 5: 128, 6: 192, 7: 224}
    return round_starts.get(rnd, (rnd - 1) * 32) + pick


def build_tweet(player: dict, pick_info: dict, comp: Optional[dict]) -> str:
    z = player['z_score']
    tier = sigma_tier(z)
    pct = player.get('nfl_pct', 0)
    pos = player.get('pos', '???')
    sparq = player.get('sparq', 0)
    overall = overall_pick_number(pick_info['round'], pick_info['pick'])

    # Top X% — round to nearest whole number
    top_pct = round(100 - pct)
    if top_pct < 1:
        top_pct = 1
    pct_str = f"Top {top_pct}% of all-time {pos}s"

    comp_line = ''
    if comp:
        comp_line = f"\nAthletically, think {comp['name']} ({comp['year']})"

    tweet = (
        f"🚨 Pick {overall} is in. {tier} athlete.\n"
        f"\n"
        f"{player['name']}, {pos} — {pick_info['team']} select him R{pick_info['round']}.{pick_info['pick']}\n"
        f"More athletic than {min(pct, 99):.0f}% of {pos}s in NFL history"
        f"{comp_line}\n"
        f"See where he ranks all-time → {SITE_URL}"
    )
    return tweet


# ── Twitter client ────────────────────────────────────────────────────────────

def get_twitter_client():
    import tweepy
    return tweepy.Client(
        consumer_key=os.environ['TWITTER_API_KEY'],
        consumer_secret=os.environ['TWITTER_API_SECRET'],
        access_token=os.environ['TWITTER_ACCESS_TOKEN'],
        access_token_secret=os.environ['TWITTER_ACCESS_SECRET'],
    )


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                        help='Print tweets to console instead of posting')
    parser.add_argument('--year', type=int, default=2026,
                        help='Draft year to monitor (default: 2026)')
    args = parser.parse_args()

    print(f"Loading 2026 prospects...")
    prospects = load_prospects(2026)
    print(f"  {len(prospects)} prospects loaded.")

    print("Building historical comp index (2010–2025)...")
    hist_index = build_historical_index()
    print(f"  {len(hist_index)} historical players indexed.")

    seen = load_state()
    print(f"  {len(seen)} picks already seen from previous run.")

    twitter = None
    if not args.dry_run:
        twitter = get_twitter_client()
        print("Twitter client ready.")

    print(f"\nPolling ESPN for {args.year} draft picks every {POLL_INTERVAL}s... (Ctrl+C to stop)\n")

    while True:
        picks = poll_espn_picks(args.year)
        new_picks = [p for p in picks if (p['round'], p['pick']) not in seen]

        for pick_info in sorted(new_picks, key=lambda p: (p['round'], p['pick'])):
            key = (pick_info['round'], pick_info['pick'])
            norm = _norm_name(pick_info['name'])
            player = prospects.get(norm)

            if not player or not player.get('sparq') or not player.get('z_score'):
                print(f"  Skip R{pick_info['round']}.{pick_info['pick']} {pick_info['name']} — no SPARQ data")
                seen.add(key)
                save_state(seen)
                continue

            comp = find_comp(player['pos'], player['z_score'], hist_index)
            tweet = build_tweet(player, pick_info, comp)

            print(f"\n{'='*60}")
            print(tweet)
            print(f"{'='*60}")

            if not args.dry_run:
                try:
                    twitter.create_tweet(text=tweet)
                    print("  ✓ Tweeted.")
                except Exception as e:
                    print(f"  ✗ Tweet failed: {e}")

            seen.add(key)
            save_state(seen)
            time.sleep(2)  # brief pause between tweets

        if not new_picks:
            print(f"  [{time.strftime('%H:%M:%S')}] No new picks. {len(seen)} total seen.")

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
