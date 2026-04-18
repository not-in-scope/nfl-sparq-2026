"""Fetch 2026 NFL Draft prospect rankings from ESPN.

Returns a dict keyed by player fullName with draft_round, draft_pick, and
ESPN's position abbreviation. Used to populate mock round data since PFN
big board returns 403.

ESPN overall rank 1–32 → R1, 33–64 → R2, etc. Players ranked > 257 are
projected undrafted (round/pick = None).
"""
import requests
from typing import Optional

BASE_URL = (
    "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
    "/seasons/2026/draft/athletes"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}

ROUND_RANGES = [
    (1,   32,  1),
    (33,  64,  2),
    (65,  96,  3),
    (97,  128, 4),
    (129, 192, 5),
    (193, 224, 6),
    (225, 257, 7),
]


def _round_from_rank(rank: int):
    for lo, hi, rnd in ROUND_RANGES:
        if lo <= rank <= hi:
            return rnd, rank
    return None, None


def _fetch_refs(limit: int = 100) -> list[str]:
    """Paginate the draft athletes index and return all athlete $ref URLs."""
    refs = []
    page = 1
    while True:
        r = requests.get(BASE_URL, params={"limit": limit, "page": page},
                         headers=HEADERS, timeout=30)
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


def fetch_espn_draft_board() -> dict:
    """Return dict keyed by player fullName → {draft_round, draft_pick, espn_pos}.

    Only includes prospects with an 'overall' rank attribute (i.e. ESPN has
    them ranked). Players not in the board or ranked >257 get None for round/pick.
    """
    try:
        refs = _fetch_refs()
    except requests.RequestException:
        return {}

    result = {}
    for ref in refs:
        try:
            athlete = requests.get(ref, headers=HEADERS, timeout=15).json()
        except Exception:
            continue

        name = athlete.get("fullName", "").strip()
        if not name:
            continue

        overall = next(
            (int(a["value"]) for a in athlete.get("attributes", [])
             if a.get("name") == "overall"),
            None,
        )
        pos = (athlete.get("position") or {}).get("abbreviation", "") or ""

        rnd, pick = _round_from_rank(overall) if overall is not None else (None, None)
        result[name] = {"draft_round": rnd, "draft_pick": pick, "espn_pos": pos}

    return result
