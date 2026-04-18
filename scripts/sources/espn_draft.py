"""Fetch NFL Draft prospect data from ESPN.

For 2026 (upcoming draft): uses ESPN's 'overall' rank as projected pick order.
For historical years: parses the 'pick.$ref' URL on each athlete record, which
  encodes the actual round/pick (e.g. .../rounds/1/picks/2).

Also returns ESPN's height (inches) and position abbreviation for each athlete.
"""
import re
import requests
from typing import Optional

_BASE = (
    "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
    "/seasons/{year}/draft/athletes"
)
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}

# Maps overall rank 1–257 → (round, pick) for projected 2026 drafts
ROUND_RANGES = [
    (1,   32,  1),
    (33,  64,  2),
    (65,  96,  3),
    (97,  128, 4),
    (129, 192, 5),
    (193, 224, 6),
    (225, 257, 7),
]

_PICK_REF_RE = re.compile(r'/rounds/(\d+)/picks/(\d+)')


def _round_from_rank(rank: int):
    for lo, hi, rnd in ROUND_RANGES:
        if lo <= rank <= hi:
            return rnd, rank
    return None, None


def _fetch_refs(year: int, limit: int = 100) -> list[str]:
    url = _BASE.format(year=year)
    refs = []
    page = 1
    while True:
        r = requests.get(url, params={"limit": limit, "page": page},
                         headers=_HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        items = data.get("items", [])
        if not items:
            break
        refs.extend(item["$ref"] for item in items if "$ref" in item)
        if len(refs) >= (data.get("count") or 0):
            break
        page += 1
    return refs


def fetch_espn_draft_board(year: int = 2026) -> dict:
    """Return dict keyed by player fullName.

    Each value: {draft_round, draft_pick, espn_pos, height, round_source}
      round_source = 'actual' (historical) | 'mock' (upcoming) | None (undrafted/unranked)
    height is in decimal inches (e.g. 76.875), or None.
    """
    is_historical = year < 2026

    try:
        refs = _fetch_refs(year)
    except requests.RequestException:
        return {}

    result = {}
    for ref in refs:
        try:
            athlete = requests.get(ref, headers=_HEADERS, timeout=15).json()
        except Exception:
            continue

        name = athlete.get("fullName", "").strip()
        if not name:
            continue

        pos = (athlete.get("position") or {}).get("abbreviation", "") or ""
        height = athlete.get("height")   # decimal inches from ESPN, e.g. 76.875

        if is_historical:
            pick_ref = (athlete.get("pick") or {}).get("$ref", "")
            m = _PICK_REF_RE.search(pick_ref)
            if m:
                rnd  = int(m.group(1))
                pick = int(m.group(2))
                round_source = 'actual'
            else:
                rnd, pick, round_source = None, None, None
        else:
            overall = next(
                (int(a["value"]) for a in athlete.get("attributes", [])
                 if a.get("name") == "overall"),
                None,
            )
            rnd, pick = _round_from_rank(overall) if overall is not None else (None, None)
            round_source = 'mock' if rnd is not None else None

        result[name] = {
            "draft_round":  rnd,
            "draft_pick":   pick,
            "espn_pos":     pos,
            "height":       height,
            "round_source": round_source,
        }

    return result
