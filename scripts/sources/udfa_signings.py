"""Fetch UDFA signing teams from nflverse roster data.

nflverse publishes per-season rosters with entry_year, draft_number, and team.
Rookies with entry_year == season and no draft_number are UDFAs.
We take week 1 as the first signing team.
"""
import io
import csv
import requests
from typing import Optional

_BASE_URL = "https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_{year}.csv"
_HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; nfl-sparq-bot/1.0)'}


def fetch_udfa_signings(year: int) -> dict[str, str]:
    """Return {normalized_name: team_abbrev} for UDFA signings in a given year.

    Matches week 1 roster entries where entry_year == year and draft_number is empty.
    """
    url = _BASE_URL.format(year=year)
    try:
        r = requests.get(url, headers=_HEADERS, timeout=20, allow_redirects=True)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"  Warning: could not fetch nflverse roster {year}: {e}")
        return {}

    reader = csv.DictReader(io.StringIO(r.text))

    # Collect all appearances for each UDFA (any week); keep earliest week's team
    from collections import defaultdict
    appearances: dict[str, list] = defaultdict(list)

    for row in reader:
        if row.get('entry_year') != str(year):
            continue
        if row.get('draft_number'):
            continue
        name = row.get('full_name', '').strip()
        team = row.get('team', '').strip()
        college = row.get('college', '').strip()
        week_raw = row.get('week', '0')
        try:
            week = int(week_raw)
        except ValueError:
            week = 99
        if name and team:
            appearances[name].append({'team': team, 'college': college, 'week': week})

    # Take the earliest-week team for each player
    result: dict[str, dict] = {}
    for name, entries in appearances.items():
        entries.sort(key=lambda e: e['week'])
        result[name] = {'team': entries[0]['team'], 'college': entries[0]['college']}

    return result
