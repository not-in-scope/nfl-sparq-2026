"""Scrape NFL combine results from nflcombineresults.com.

Used for historical years (pre-2026) as the primary combine data source.
The site requires POST even for GET-style queries.
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional

_URL = "https://nflcombineresults.com/nflcombinedata.php"
_HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; research-bot/1.0)'}

# nflcombineresults column headers (in order):
# Year, Name, College, POS, Height(in), Weight(lbs), Wonderlic,
# 40Yard, Bench Press, Vert Leap(in), Broad Jump(in), Shuttle, 3Cone

_COLS = [
    'year', 'name', 'college', 'pos', 'height', 'weight', 'wonderlic',
    'forty', 'bench', 'vertical', 'broad', 'shuttle', 'cone',
]


def _float_or_none(val: str) -> Optional[float]:
    s = val.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _metric(value, source: Optional[str]) -> dict:
    return {'value': value, 'source': source if value is not None else None}


def fetch_combine_data_historical(year: int) -> list[dict]:
    """Fetch combine data for a historical year. Returns player list."""
    resp = requests.get(
        _URL,
        params={'year': str(year), 'pos': '', 'college': ''},
        headers=_HEADERS,
        timeout=30,
    )
    # Site returns HTTP 404 but body is valid HTML with the table
    soup = BeautifulSoup(resp.text, 'lxml')
    table = soup.find('table')
    if not table:
        raise RuntimeError(f"No table found in nflcombineresults.com response for {year}")

    rows = table.find_all('tr')
    players = []
    for row in rows[1:]:   # skip header row
        cells = [td.get_text(strip=True) for td in row.find_all('td')]
        if len(cells) < len(_COLS):
            continue
        data = dict(zip(_COLS, cells))

        name = data['name'].strip()
        if not name:
            continue

        height = _float_or_none(data['height'])   # decimal inches, e.g. 76.38
        weight = _float_or_none(data['weight'])
        forty  = _float_or_none(data['forty'])
        bench  = _float_or_none(data['bench'])
        vert   = _float_or_none(data['vertical'])
        broad  = _float_or_none(data['broad'])
        shuttle = _float_or_none(data['shuttle'])
        cone   = _float_or_none(data['cone'])

        pos = data.get('pos', '').strip().upper()

        players.append({
            'name':   name,
            'pos':    pos,
            'school': data.get('college', '').strip(),
            'height': height,
            'metrics': {
                'weight':    _metric(weight, 'combine'),
                'forty':     _metric(forty,  'combine'),
                'vertical':  _metric(vert,   'combine'),
                'broad':     _metric(broad,  'combine'),
                'bench':     _metric(bench,  'combine'),
                'cone':      _metric(cone,   'combine'),
                'shuttle':   _metric(shuttle,'combine'),
                'ten_split': _metric(None, None),
            },
        })
    return players
