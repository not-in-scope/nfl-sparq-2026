import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import json
from unittest.mock import patch, MagicMock
from sources.mockdraftable import (
    parse_player_page, apply_proday_correction, merge_mockdraftable
)

MOCK_STATE = {
    "player": {
        "name": "Fernando Mendoza",
        "position": {"abbreviation": "QB"},
        "measurements": [
            {"measureable": {"slug": "forty"},    "measurement": 4.57, "source": "proDay"},
            {"measureable": {"slug": "ten"},      "measurement": 1.53, "source": "proDay"},
            {"measureable": {"slug": "vertical"}, "measurement": 36.0, "source": "proDay"},
            {"measureable": {"slug": "broad"},    "measurement": 117.0,"source": "proDay"},
        ]
    }
}
MOCK_HTML = f"<html><script>window.INITIAL_STATE = {json.dumps(MOCK_STATE)};</script></html>"


def test_parse_extracts_measurements():
    data = parse_player_page(MOCK_HTML)
    assert data is not None
    # Pro day forty gets +0.04 correction applied
    assert abs(data['forty'] - 4.61) < 0.001
    assert data['vertical'] == 36.0
    assert data['broad'] == 117.0


def test_parse_returns_sources():
    data = parse_player_page(MOCK_HTML)
    assert data['forty_source'] == 'pro_day'
    assert data['ten_split_source'] == 'pro_day'


def test_apply_proday_correction():
    assert abs(apply_proday_correction(4.57) - 4.61) < 0.001


def test_merge_fills_nulls():
    player = {
        'name': 'Fernando Mendoza', 'pos': 'QB', 'school': 'Indiana',
        'metrics': {
            'weight':    {'value': 236,  'source': 'combine'},
            'forty':     {'value': None, 'source': None},
            'ten_split': {'value': None, 'source': None},
            'vertical':  {'value': None, 'source': None},
            'broad':     {'value': None, 'source': None},
            'bench':     {'value': None, 'source': None},
            'cone':      {'value': None, 'source': None},
            'shuttle':   {'value': None, 'source': None},
        }
    }
    md = {'forty': 4.61, 'forty_source': 'pro_day',
          'ten_split': 1.57, 'ten_split_source': 'pro_day',
          'vertical': 36.0, 'vertical_source': 'pro_day'}
    result = merge_mockdraftable(player, md)
    assert result['metrics']['forty']['value'] == 4.61
    assert result['metrics']['forty']['source'] == 'pro_day'
    assert result['metrics']['ten_split']['value'] == 1.57


def test_merge_does_not_overwrite_combine():
    player = {
        'name': 'Spencer Fano', 'pos': 'OT', 'school': 'Alabama',
        'metrics': {'forty': {'value': 4.91, 'source': 'combine'},
                    'ten_split': {'value': None, 'source': None},
                    'weight': {'value': 311, 'source': 'combine'},
                    'vertical': {'value': 32, 'source': 'combine'},
                    'broad': {'value': 111, 'source': 'combine'},
                    'bench': {'value': 30, 'source': 'combine'},
                    'cone': {'value': 7.34, 'source': 'combine'},
                    'shuttle': {'value': 4.67, 'source': 'combine'}}
    }
    md = {'forty': 4.88, 'forty_source': 'pro_day'}
    result = merge_mockdraftable(player, md)
    assert result['metrics']['forty']['value'] == 4.91
    assert result['metrics']['forty']['source'] == 'combine'
