import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from sources.mockdraft import parse_big_board, assign_mock_rounds

MOCK_HTML = """<html><body><table>
<tr><td>1</td><td>Fernando Mendoza</td><td>QB</td><td>Indiana</td></tr>
<tr><td>2</td><td>Arvell Reese</td><td>EDGE</td><td>Ohio State</td></tr>
<tr><td>33</td><td>Jacob Rodriguez</td><td>LB</td><td>Texas Tech</td></tr>
<tr><td>65</td><td>Chris Bell</td><td>WR</td><td>Georgia</td></tr>
</table></body></html>"""


def test_parse_big_board():
    board = parse_big_board(MOCK_HTML)
    assert board['Fernando Mendoza']['rank'] == 1
    assert board['Arvell Reese']['rank'] == 2
    assert board['Jacob Rodriguez']['rank'] == 33


def test_assign_round_1():
    board = {'Player A': {'rank': 1}, 'Player B': {'rank': 32}}
    result = assign_mock_rounds(board)
    assert result['Player A']['draft_round'] == 1
    assert result['Player B']['draft_round'] == 1


def test_assign_round_2():
    board = {'Player C': {'rank': 33}}
    result = assign_mock_rounds(board)
    assert result['Player C']['draft_round'] == 2


def test_assign_rounds_3_4():
    board = {'Player D': {'rank': 65}, 'Player E': {'rank': 128}}
    result = assign_mock_rounds(board)
    assert result['Player D']['draft_round'] == 3
    assert result['Player E']['draft_round'] == 4


def test_assign_rounds_5_7():
    board = {'Player F': {'rank': 129}, 'Player G': {'rank': 257}}
    result = assign_mock_rounds(board)
    assert result['Player F']['draft_round'] == 5
    assert result['Player G']['draft_round'] == 7
