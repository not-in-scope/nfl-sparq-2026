"""Fetch NFL Draft prospect data from ESPN.

For 2026 (upcoming draft): uses ESPN's 'overall' rank as projected pick order.
For historical years: parses the 'pick.$ref' URL on each athlete record, which
  encodes the actual round/pick (e.g. .../rounds/1/picks/2).
  Also fetches each pick's JSON to get the drafting NFL team abbreviation.

Also returns ESPN's height (inches) and position abbreviation for each athlete.
"""
import re
import requests
from typing import Optional

_TEAM_CACHE: dict = {}      # team_id → abbreviation
_COLLEGE_CACHE: dict = {}   # college_id → name
_TEAM_ID_RE    = re.compile(r'/teams/(\d+)')
_COLLEGE_ID_RE = re.compile(r'/colleges/(\d+)')

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


def _fetch_college_name(college_ref: str) -> Optional[str]:
    """Fetch college name from an ESPN college $ref URL, with caching."""
    m = _COLLEGE_ID_RE.search(college_ref)
    if not m:
        return None
    cid = m.group(1)
    if cid in _COLLEGE_CACHE:
        return _COLLEGE_CACHE[cid]
    try:
        r = requests.get(college_ref.split('?')[0], headers=_HEADERS, timeout=10)
        name = r.json().get('name')
        _COLLEGE_CACHE[cid] = name
        return name
    except Exception:
        return None


def _fetch_team_abbrev(team_ref: str) -> Optional[str]:
    """Fetch NFL team abbreviation from an ESPN team $ref URL, with caching."""
    m = _TEAM_ID_RE.search(team_ref)
    if not m:
        return None
    team_id = m.group(1)
    if team_id in _TEAM_CACHE:
        return _TEAM_CACHE[team_id]
    try:
        r = requests.get(team_ref.split('?')[0], headers=_HEADERS, timeout=10)
        abbrev = r.json().get('abbreviation')
        _TEAM_CACHE[team_id] = abbrev
        return abbrev
    except Exception:
        return None


_ROUND_STARTS = {1: 0, 2: 32, 3: 64, 4: 96, 5: 128, 6: 192, 7: 224}


def _round_from_rank(rank: int):
    """Return (round, within_round_pick) from an ESPN overall rank (2026 projected)."""
    for lo, hi, rnd in ROUND_RANGES:
        if lo <= rank <= hi:
            within = rank - _ROUND_STARTS[rnd]
            return rnd, within
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
    """Return dict keyed by player fullName → entry (or list of entries for name collisions).

    Each entry: {draft_round, draft_pick, espn_pos, height, round_source, team, espn_college}
      round_source = 'actual' (historical) | 'mock' (upcoming) | None (undrafted/unranked)
    height is in decimal inches (e.g. 76.875), or None.

    When ESPN has multiple players with the same fullName (e.g. two Byron Youngs in 2023),
    the value is a list of entries; apply_espn_data uses espn_college to pick the right one.
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

        college_ref = (athlete.get("college") or {}).get("$ref", "")
        espn_college = _fetch_college_name(college_ref) if college_ref else None

        pick_ref_url = (athlete.get("pick") or {}).get("$ref", "")
        m = _PICK_REF_RE.search(pick_ref_url)
        team_abbrev = None

        if m:
            # Actual pick — works for historical years and 2026 once picks are made
            rnd  = int(m.group(1))
            pick = int(m.group(2))
            round_source = 'actual'
            try:
                pick_data = requests.get(
                    pick_ref_url.split('?')[0], headers=_HEADERS, timeout=10
                ).json()
                team_ref = (pick_data.get("team") or {}).get("$ref", "")
                if team_ref:
                    team_abbrev = _fetch_team_abbrev(team_ref)
            except Exception:
                pass
        elif not is_historical:
            # 2026 prospect not yet drafted — fall back to overall rank for mock projection
            overall = next(
                (int(a["value"]) for a in athlete.get("attributes", [])
                 if a.get("name") == "overall"),
                None,
            )
            rnd, pick = _round_from_rank(overall) if overall is not None else (None, None)
            round_source = 'mock' if rnd is not None else None
        else:
            rnd, pick, round_source = None, None, None

        entry = {
            "draft_round":  rnd,
            "draft_pick":   pick,
            "espn_pos":     pos,
            "height":       height,
            "round_source": round_source,
            "team":         team_abbrev,
            "espn_college": espn_college,
        }
        if name in result:
            # Name collision — convert to list so apply_espn_data can pick by college
            existing = result[name]
            if isinstance(existing, list):
                existing.append(entry)
            else:
                result[name] = [existing, entry]
        else:
            result[name] = entry

    return result
