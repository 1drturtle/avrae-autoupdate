from pathlib import Path

from utils import is_important_path, parse_paths


def test_is_important_path_accepts_supported_extensions():
    assert is_important_path("spell.alias") is True
    assert is_important_path("snippet.snippet") is True
    assert is_important_path("note.md") is True
    assert is_important_path("state.gvar") is True


def test_is_important_path_rejects_other_extensions():
    assert is_important_path("README.txt") is False
    assert is_important_path("tool.py") is False


def test_parse_paths_filters_and_converts_to_path_instances():
    paths = ["a.txt", "spell.alias", "note.md", "script.py", "tool.snippet"]

    result = parse_paths(paths)

    assert result == [Path("spell.alias"), Path("note.md"), Path("tool.snippet")]

