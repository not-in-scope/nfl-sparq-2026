import re
import requests
from typing import Optional
from bs4 import BeautifulSoup

URL = "https://www.pff.com/news/draft-2026-nfl-draft-pro-day-schedule-results-tracker"
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; research-bot/1.0)'}

PATTERNS = {
    'forty':     [r'(\d\.\d{2})\s*forty', r'forty[- ]yard dash[^0-9]*(\d\.\d{2})'],
    'vertical':  [r'(\d{2}(?:\.\d)?)[- ]inch vertical', r'vertical[^0-9]*(\d{2}(?:\.\d)?)'],
    'broad':     [r'(\d{1,2})-foot-(\d{1,2})\s*broad', r'broad jump[^0-9]*(\d{1,2})-foot-(\d{1,2})'],
    'bench':     [r'(\d{1,2})\s*reps?\s*(?:on the\s*)?bench', r'bench press[^0-9]*(\d{1,2})\s*reps?'],
    'cone':      [r'three[- ]cone[^0-9]*(\d\.\d{2})', r'3[- ]cone[^0-9]*(\d\.\d{2})'],
    'shuttle':   [r'short shuttle[^0-9]*(\d\.\d{2})', r'(\d\.\d{2})\s*short shuttle'],
    'ten_split': [r'10[- ]yard split[^0-9]*(\d\.\d{2})', r'(\d\.\d{2})\s*10[- ]yard split'],
}


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
    """Parse PFF pro day HTML; return dict keyed by player name."""
    soup = BeautifulSoup(html, 'lxml')
    result = {}
    current_name = None

    for tag in soup.find_all(['h2', 'h3', 'h4', 'p', 'li']):
        text = tag.get_text(separator=' ', strip=True)
        if tag.name in ('h2', 'h3', 'h4'):
            m = re.match(r'^([A-Z][a-z]+ [A-Z][a-zA-Z\s\-\']+),\s*\w+', text)
            if m:
                current_name = m.group(1).strip()
                result[current_name] = {}

        if current_name and tag.name in ('p', 'li'):
            for metric in PATTERNS:
                if metric not in result[current_name]:
                    val = extract_metric_from_text(text, metric)
                    if val is not None:
                        result[current_name][metric] = val
                        result[current_name][f'{metric}_source'] = 'pro_day'

    return result


def fetch_pff_proday() -> dict:
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException:
        return {}
    return parse_pff_proday(resp.text)
