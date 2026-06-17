import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
from freeride.match_resorts import extract_hints, score_name_match


def test_extract_hints_simple():
    assert "Schladming" in extract_hints("Schladming")


def test_extract_hints_strips_parenthetical():
    hints = extract_hints("Alpendorf (Ski amadé)")
    assert "Alpendorf" in hints
    assert "Ski amadé" in hints


def test_extract_hints_splits_dashes():
    hints = extract_hints("Zillertal Arena-Zell am Ziller-Gerlos")
    assert "Zillertal Arena" in hints
    assert "Zell am Ziller" in hints
    assert "Gerlos" in hints


def test_score_name_match_exact_match():
    assert score_name_match("Schladming", ["Schladming", "Planai"]) > 0


def test_score_name_match_no_match():
    assert score_name_match("Verbier", ["Schladming", "Planai"]) == 0


def test_score_name_match_partial():
    score = score_name_match("St. Anton/St. Christoph/Stuben", ["St. Anton", "Arlberg"])
    assert score > 0
