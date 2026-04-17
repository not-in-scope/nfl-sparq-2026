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


MOCK_HTML = """<html><body>
<h3>Fernando Mendoza, QB, Indiana</h3>
<p>Mendoza ran a 4.61 forty-yard dash with a 36-inch vertical. Short shuttle in 4.36.</p>
<h3>Spencer Fano, OT, Alabama</h3>
<p>Fano posted a 32-inch vertical and 10-foot-3 broad jump. Ran a 4.91 forty-yard dash.</p>
</body></html>"""


def test_parse_pff_keyed_by_name():
    result = parse_pff_proday(MOCK_HTML)
    assert 'Fernando Mendoza' in result
    assert result['Fernando Mendoza']['forty'] == 4.61
    assert result['Fernando Mendoza']['vertical'] == 36.0
    assert result['Fernando Mendoza']['shuttle'] == 4.36


def test_parse_pff_second_player():
    result = parse_pff_proday(MOCK_HTML)
    assert 'Spencer Fano' in result
    assert result['Spencer Fano']['broad'] == 123.0
