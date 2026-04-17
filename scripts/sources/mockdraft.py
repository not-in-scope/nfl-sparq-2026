import requests
from bs4 import BeautifulSoup

URL = "https://www.profootballnetwork.com/nfl-draft-hq/industry-consensus-big-board"
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; research-bot/1.0)'}

# Must remain in ascending rank order — assign_mock_rounds breaks on first match
ROUND_RANGES = [
    (1,   32,  1),
    (33,  64,  2),
    (65,  96,  3),
    (97,  128, 4),
    (129, 192, 5),
    (193, 224, 6),
    (225, 257, 7),
]


def assign_mock_rounds(board: dict) -> dict:
    for name, data in board.items():
        rank = data.get('rank')
        data['draft_round'] = None
        data['draft_pick'] = None
        if rank is None:
            continue
        for lo, hi, rnd in ROUND_RANGES:
            if lo <= rank <= hi:
                data['draft_round'] = rnd
                data['draft_pick'] = rank
                break
    return board


def parse_big_board(html: str) -> dict:
    soup = BeautifulSoup(html, 'lxml')
    result = {}
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 2:
            continue
        rank_text = cells[0].get_text(strip=True)
        name_text = cells[1].get_text(strip=True)
        if not rank_text.isdigit():
            continue
        result[name_text] = {'rank': int(rank_text)}
    return result


def fetch_big_board() -> dict:
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return {}
    return assign_mock_rounds(parse_big_board(resp.text))
