import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from sources.pff import extract_metric_from_text, parse_pff_proday


def test_extract_forty():
    assert extract_metric_from_text("ran a 4.52 forty-yard dash", 'forty') == 4.52


def test_extract_vertical():
    assert extract_metric_from_text("posted a 38-inch vertical", 'vertical') == 38.0


def test_extract_broad_feet_inches():
    # 10-foot-3 = 123 inches
    assert extract_metric_from_text("10-foot-3 broad jump", 'broad') == 123.0


def test_extract_bench():
    assert extract_metric_from_text("completed 24 reps on the bench press", 'bench') == 24.0


def test_extract_cone():
    assert extract_metric_from_text("three-cone drill time of 7.18 seconds", 'cone') == 7.18


def test_extract_shuttle():
    assert extract_metric_from_text("short shuttle in 4.22", 'shuttle') == 4.22


def test_extract_returns_none():
    assert extract_metric_from_text("nothing useful here", 'forty') is None


# Mock HTML reflects actual PFF page structure: each player is an <li> with a
# <strong> tag in format "POS Name (PFF Predictive Big Board Rank: N)" and
# nested <li> children for individual measurements.
MOCK_HTML = """<html><body><ul>
<li><strong>QB Fernando Mendoza (PFF Predictive Big Board Rank: 1)</strong><ul>
  <li>40-yard dash: 4.61 seconds</li>
  <li>Vertical jump: 36.0 inches</li>
  <li>Short shuttle: 4.36 seconds</li>
</ul></li>
<li><strong>OT Spencer Fano (PFF Predictive Big Board Rank: 10)</strong><ul>
  <li>Vertical jump: 32.0 inches</li>
  <li>Broad jump: 10 feet, 3 inches</li>
  <li>40-yard dash: 4.91 seconds</li>
</ul></li>
</ul></body></html>"""


def test_parse_pff_keyed_by_name():
    result = parse_pff_proday(MOCK_HTML)
    assert 'Fernando Mendoza' in result
    assert result['Fernando Mendoza']['forty'] == 4.61
    assert result['Fernando Mendoza']['vertical'] == 36.0
    assert result['Fernando Mendoza']['shuttle'] == 4.36


def test_parse_pff_second_player():
    result = parse_pff_proday(MOCK_HTML)
    assert 'Spencer Fano' in result
    assert result['Spencer Fano']['broad'] == 123.0  # 10*12 + 3


def test_extract_camelcase_name():
    html = """<html><body><ul>
<li><strong>DE DeShawn Jones (PFF Predictive Big Board Rank: 50)</strong><ul>
  <li>40-yard dash: 4.45 seconds</li>
</ul></li></ul></body></html>"""
    result = parse_pff_proday(html)
    assert 'DeShawn Jones' in result
    assert result['DeShawn Jones']['forty'] == 4.45


def test_extract_initial_dot_name():
    html = """<html><body><ul>
<li><strong>CB D.J. Turner (PFF Predictive Big Board Rank: 75)</strong><ul>
  <li>Vertical jump: 38.0 inches</li>
</ul></li></ul></body></html>"""
    result = parse_pff_proday(html)
    assert 'D.J. Turner' in result


def test_extract_apostrophe_name():
    html = """<html><body><ul>
<li><strong>TE Ja'Tavion Sanders (PFF Predictive Big Board Rank: 80)</strong><ul>
  <li>40-yard dash: 4.52 seconds</li>
</ul></li></ul></body></html>"""
    result = parse_pff_proday(html)
    assert "Ja'Tavion Sanders" in result


def test_extract_source_fields_present():
    result = parse_pff_proday(MOCK_HTML)
    assert result['Fernando Mendoza'].get('forty_source') == 'pro_day'
    assert result['Fernando Mendoza'].get('vertical_source') == 'pro_day'
