import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from unittest.mock import patch, MagicMock
from sources.bigboardlab import fetch_combine_data, parse_combine_data

MOCK_HTML = """<html><body><script>
const COMBINE_DATA = [
  {"name":"Spencer Fano","pos":"OT","school":"Alabama","weight":311,
   "forty":4.91,"vertical":32,"broad":111,"bench":30,"cone":7.34,"shuttle":4.67},
  {"name":"Jeremiyah Love","pos":"RB","school":"Notre Dame","weight":212,
   "forty":4.36,"vertical":null,"broad":null,"bench":null,"cone":null,"shuttle":null},
  {"name":"Fernando Mendoza","pos":"QB","school":"Indiana","weight":236,
   "forty":null,"vertical":null,"broad":null,"bench":null,"cone":null,"shuttle":null}
];
</script></body></html>"""


def test_parse_returns_all_players():
    players = parse_combine_data(MOCK_HTML)
    assert len(players) == 3


def test_parse_populated_fields():
    players = parse_combine_data(MOCK_HTML)
    fano = next(p for p in players if p['name'] == 'Spencer Fano')
    assert fano['pos'] == 'OT'
    assert fano['school'] == 'Alabama'
    assert fano['metrics']['weight']['value'] == 311
    assert fano['metrics']['weight']['source'] == 'combine'
    assert fano['metrics']['forty']['value'] == 4.91
    assert fano['metrics']['bench']['value'] == 30


def test_parse_null_fields():
    players = parse_combine_data(MOCK_HTML)
    mendoza = next(p for p in players if p['name'] == 'Fernando Mendoza')
    assert mendoza['metrics']['forty']['value'] is None
    assert mendoza['metrics']['forty']['source'] is None


def test_parse_partial_fields():
    players = parse_combine_data(MOCK_HTML)
    love = next(p for p in players if p['name'] == 'Jeremiyah Love')
    assert love['metrics']['forty']['value'] == 4.36
    assert love['metrics']['forty']['source'] == 'combine'
    assert love['metrics']['vertical']['value'] is None


def test_fetch_calls_url():
    with patch('sources.bigboardlab.requests.get') as mock_get:
        mock_get.return_value = MagicMock(text=MOCK_HTML, status_code=200)
        players = fetch_combine_data()
        mock_get.assert_called_once()
        assert len(players) == 3
