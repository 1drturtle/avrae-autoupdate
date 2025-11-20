import json
from pathlib import Path

from config import Config
from parsing import Parser
from utils import parse_paths


def test_parse_paths_filters_supported_extensions():
    paths = ["a.txt", "spell.alias", "note.md", "script.py", "tool.snippet"]

    result = parse_paths(paths)

    assert {p.name for p in result} == {"spell.alias", "note.md", "tool.snippet"}


def test_parser_connects_files_to_collections_and_gvars(tmp_path: Path):
    collections_dir = tmp_path / "collections" / "cool-collection"
    alias_dir = collections_dir / "my-alias"
    alias_dir.mkdir(parents=True)
    alias_file = alias_dir / "my-alias.alias"
    alias_file.write_text("code")
    docs_file = alias_dir / "my-alias.md"
    docs_file.write_text("docs")

    gvars_dir = tmp_path / "gvars"
    gvars_dir.mkdir()
    gvar_file = gvars_dir / "one.gvar"
    gvar_file.write_text("gvar data")

    collections_json = tmp_path / "collections.json"
    collections_json.write_text(json.dumps({collections_dir.as_posix(): "col-1"}))
    gvars_json = tmp_path / "gvars.json"
    gvars_json.write_text(json.dumps({gvar_file.as_posix(): "gvar-1"}))

    config = Config()
    config.collections_file_path = str(collections_json)
    config.gvars_file_path = str(gvars_json)
    parser = Parser(config)
    parser.load_collections()
    parser.load_gvars()

    parser.find_connected_files([alias_file, docs_file, gvar_file])

    types = {cf.type for cf in parser.connected_files}
    assert {"alias", "md", "gvar"} <= types

    alias_entry = next(cf for cf in parser.connected_files if cf.type == "alias")
    assert alias_entry.collection["id"] == "col-1"
    assert alias_entry.trimmed_path == Path("my-alias") / "my-alias.alias"


def test_parser_ignores_files_outside_configured_collections(tmp_path: Path):
    other_collection = tmp_path / "collections" / "other"
    other_alias = other_collection / "x.alias"
    other_alias.parent.mkdir(parents=True)
    other_alias.write_text("code")

    collections_json = tmp_path / "collections.json"
    collections_json.write_text(json.dumps({(tmp_path / "collections" / "cool").as_posix(): "col-1"}))
    gvars_json = tmp_path / "gvars.json"
    gvars_json.write_text(json.dumps({}))

    config = Config()
    config.collections_file_path = str(collections_json)
    config.gvars_file_path = str(gvars_json)
    parser = Parser(config)
    parser.load_collections()
    parser.load_gvars()

    parser.find_connected_files([other_alias])

    assert parser.connected_files == []
