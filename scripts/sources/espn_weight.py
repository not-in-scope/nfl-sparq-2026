"""Fetch player weight from ESPN college-football athlete profiles.

Used as a fallback when BigBoardLab has no weight for a player (e.g., players
who skipped the weigh-in at the combine but attended a pro day).
"""
import requests
from typing import Optional

SEARCH_URL = "https://site.api.espn.com/apis/common/v3/search"
ATHLETE_URL = (
    "https://sports.core.api.espn.com/v2/sports/football/leagues/"
    "college-football/seasons/2025/athletes/{athlete_id}"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}


def _search_athlete_id(name: str) -> Optional[str]:
    try:
        resp = requests.get(
            SEARCH_URL,
            params={"query": name, "type": "player", "sport": "football", "limit": 3},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None
    items = resp.json().get("items", [])
    for item in items:
        if item.get("league") == "college-football":
            return str(item["id"])
    return None


def fetch_weight(name: str) -> Optional[float]:
    """Return weight (lbs) for a college football player, or None if not found."""
    athlete_id = _search_athlete_id(name)
    if not athlete_id:
        return None
    try:
        resp = requests.get(
            ATHLETE_URL.format(athlete_id=athlete_id),
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException:
        return None
    return resp.json().get("weight") or None
