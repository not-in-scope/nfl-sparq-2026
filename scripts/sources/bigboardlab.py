import re
import json
import requests
from typing import Optional

URL = "https://bigboardlab.com/blog/2026-nfl-combine-results.html"
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; research-bot/1.0)'}


def _metric(value, source: Optional[str]) -> dict:
    return {'value': value, 'source': source if value is not None else None}


def _js_to_json(js: str) -> str:
    """Convert JavaScript object literal (unquoted keys) to valid JSON.

    Handles both multi-line (`  key:`) and inline (`{key:`, `,key:`) formats.
    """
    # Quote unquoted keys appearing after { or , (with optional surrounding whitespace)
    return re.sub(r'([{,]\s*)([A-Za-z_]\w*)(\s*:)', r'\1"\2"\3', js)


def parse_combine_data(html: str) -> list[dict]:
    """Regex-extract COMBINE_DATA JS array and return structured player list."""
    match = re.search(r'const COMBINE_DATA\s*=\s*(\[.*?\]);', html, re.DOTALL)
    if not match:
        raise ValueError("COMBINE_DATA not found in page source")

    raw = match.group(1)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Page uses JS object literal notation (unquoted keys) — convert first
        parsed = json.loads(_js_to_json(raw))

    players = []
    for p in parsed:
        players.append({
            'name':   p.get('name', '').strip(),
            'pos':    p.get('pos',  '').strip().upper(),
            'school': p.get('school', '').strip(),
            'metrics': {
                'weight':    _metric(p.get('weight'),   'combine'),
                'forty':     _metric(p.get('forty'),    'combine'),
                'vertical':  _metric(p.get('vertical'), 'combine'),
                'broad':     _metric(p.get('broad'),    'combine'),
                'bench':     _metric(p.get('bench'),    'combine'),
                'cone':      _metric(p.get('cone'),     'combine'),
                'shuttle':   _metric(p.get('shuttle'),  'combine'),
                'ten_split': _metric(None, None),  # not in BigBoardLab data
            },
        })
    return players


def fetch_combine_data() -> list[dict]:
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch BigBoardLab combine data: {e}") from e
    return parse_combine_data(resp.text)
