import re
import json
import time
import requests
from typing import Optional

SEARCH_URL = "https://www.mockdraftable.com/search"
PLAYER_URL = "https://www.mockdraftable.com/player/{player_id}"
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; research-bot/1.0)'}

SLUG_MAP = {
    'forty':    'forty',
    'ten':      'ten_split',
    'vertical': 'vertical',
    'broad':    'broad',
    'bench':    'bench',
    'cone':     'cone',
    'shuttle':  'shuttle',
}

PRO_DAY_CORRECTION = 0.04


def apply_proday_correction(time_val: float) -> float:
    """Add 0.04s to hand-timed pro day speed results."""
    return round(time_val + PRO_DAY_CORRECTION, 3)


def _parse_initial_state(html: str) -> Optional[dict]:
    match = re.search(r'window\.INITIAL_STATE\s*=\s*({.*?});\s*</script>', html, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def parse_player_page(html: str) -> Optional[dict]:
    """Extract measurements from a MockDraftable player page."""
    state = _parse_initial_state(html)
    if not state:
        return None

    result = {}
    for m in state.get('player', {}).get('measurements', []):
        slug = m.get('measureable', {}).get('slug')
        field = SLUG_MAP.get(slug)
        if not field:
            continue
        value = m.get('measurement')
        source = 'pro_day' if m.get('source') == 'proDay' else 'combine'
        if source == 'pro_day' and field in ('forty', 'ten_split') and value is not None:
            value = apply_proday_correction(value)
        result[field] = value
        result[f'{field}_source'] = source

    return result or None


def _search_player_id(name: str) -> Optional[str]:
    try:
        resp = requests.get(SEARCH_URL, params={'q': name}, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    state = _parse_initial_state(resp.text)
    if not state:
        return None
    players = state.get('players', {}).get('players', [])
    return str(players[0]['id']) if players else None


def fetch_player_data(name: str) -> Optional[dict]:
    player_id = _search_player_id(name)
    if not player_id:
        return None
    try:
        resp = requests.get(PLAYER_URL.format(player_id=player_id), headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    return parse_player_page(resp.text)


def merge_mockdraftable(player: dict, md_data: dict) -> dict:
    """Merge MockDraftable data into player record; never overwrite combine values."""
    for field in ('forty', 'ten_split', 'vertical', 'broad', 'bench', 'cone', 'shuttle'):
        if field not in md_data:
            continue
        existing = player['metrics'].get(field, {})
        if existing.get('source') == 'combine':
            continue
        if existing.get('value') is None and md_data.get(field) is not None:
            player['metrics'][field] = {
                'value': md_data[field],
                'source': md_data.get(f'{field}_source', 'pro_day'),
            }
    return player


def enrich_players(players: list[dict], rate_limit: float = 1.0) -> list[dict]:
    """Fetch MockDraftable data for players with any missing metrics."""
    for player in players:
        has_gaps = any(v.get('value') is None for v in player['metrics'].values())
        if not has_gaps:
            continue
        md_data = fetch_player_data(player['name'])
        if md_data:
            merge_mockdraftable(player, md_data)
            time.sleep(rate_limit)
    return players
