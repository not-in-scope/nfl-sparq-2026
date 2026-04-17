import re
import requests
from typing import Optional
from bs4 import BeautifulSoup

URL = "https://www.pff.com/news/draft-2026-nfl-draft-pro-day-schedule-results-tracker"
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; research-bot/1.0)'}

# Patterns applied to lowercased measurement text.
# broad patterns produce two capture groups → converted to inches via group1*12 + group2.
PATTERNS = {
    'forty':     [
        r'40[- ]yard dash:\s*(\d\.\d{2})',           # "40-yard dash: 4.48 seconds"
        r'(\d\.\d{2})\s*forty',
        r'forty[- ]yard dash[^0-9]*(\d\.\d{2})',
    ],
    'vertical':  [
        r'vertical jump:\s*(\d{2}(?:\.\d)?)\s*inches?',  # "Vertical jump: 33.5 inches"
        r'(\d{2}(?:\.\d)?)[- ]inch vertical',
        r'vertical[^0-9]{0,25}(\d{2}(?:\.\d)?)\s*(?:inch|in\.?)',
    ],
    'broad':     [
        r'broad jump:\s*(\d+)\s*feet,?\s*(\d+)\s*inches?',  # "Broad jump: 9 feet, 7 inches"
        r'(\d{1,2})-foot-(\d{1,2})\s*broad',
        r'broad jump[^0-9]*(\d{1,2})-foot-(\d{1,2})',
    ],
    'bench':     [
        r'bench:\s*(\d{1,2})\s*reps?',              # "Bench: 26 reps"
        r'(\d{1,2})\s*reps?\s*(?:on the\s*)?bench',
        r'bench press[^0-9]*(\d{1,2})\s*reps?',
    ],
    'cone':      [
        r'three[- ]cone[^0-9]{0,25}(\d\.\d{2})',
        r'3[- ]cone[^0-9]{0,25}(\d\.\d{2})',
        r'(\d\.\d{2})\s*(?:three|3)[- ]cone',
    ],
    'shuttle':   [
        r'short shuttle[^0-9]{0,25}(\d\.\d{2})',
        r'(\d\.\d{2})\s*short shuttle',
    ],
    'ten_split': [
        r'10[- ]yard split[^0-9]{0,25}(\d\.\d{2})',
        r'(\d\.\d{2})\s*10[- ]yard split',
    ],
}

# Regex to extract player name from "<POS> Name (PFF Predictive Big Board Rank: N)"
_NAME_RE = re.compile(
    r'^[A-Z]+\s+([A-Z][a-zA-Z\'\.\-]*(?:\s+[A-Z][a-zA-Z\'\-\.]+)+)\s*\('
)


def extract_metric_from_text(text: str, metric: str) -> Optional[float]:
    text_lower = text.lower()
    for pattern in PATTERNS.get(metric, []):
        m = re.search(pattern, text_lower)
        if m:
            if metric == 'broad' and len(m.groups()) == 2:
                return float(int(m.group(1)) * 12 + int(m.group(2)))
            return float(m.group(1))
    return None


def parse_pff_proday(html: str) -> dict:
    """Parse PFF pro day HTML; return dict keyed by player name.

    Page structure: each player appears as an <li> containing a <strong> tag
    with the format "POS Name (PFF Predictive Big Board Rank: N)". Individual
    measurements are in nested <li> children.
    """
    soup = BeautifulSoup(html, 'lxml')
    result = {}

    for li in soup.find_all('li'):
        strong = li.find('strong', recursive=False) or li.find('strong')
        if not strong:
            continue
        strong_text = strong.get_text(strip=True)
        m = _NAME_RE.match(strong_text)
        if not m:
            continue

        name = m.group(1).strip()
        result[name] = {}

        for child_li in li.find_all('li'):
            text = child_li.get_text(strip=True)
            for metric in PATTERNS:
                if metric not in result[name]:
                    val = extract_metric_from_text(text, metric)
                    if val is not None:
                        result[name][metric] = val
                        result[name][f'{metric}_source'] = 'pro_day'

    return result


def fetch_pff_proday() -> dict:
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return {}
    return parse_pff_proday(resp.text)
