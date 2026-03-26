import json
from pathlib import Path

import pytest

from config import Config
from parsing import Parser


def _build_parser(tmp_path: Path, collections: dict[str, str], gvars: dict[str, str]) -> Parser:
    collections_json = tmp_path / "collections.json"
    gvars_json = tmp_path / "gvars.json"
    collections_json.write_text(json.dumps(collections))
    gvars_json.write_text(json.dumps(gvars))

    config = Config()
    config.collections_file_path = str(collections_json)
    config.gvars_file_path = str(gvars_json)
    return Parser(config)


def test_load_collections_loads_mapping(tmp_path: Path):
    collection_path = tmp_path / "collections" / "cool"
    parser = _build_parser(tmp_path, {collection_path.as_posix(): "col-1"}, {})

    parser.load_collections()

    assert parser.collections == {collection_path: "col-1"}


def test_load_collections_raises_for_missing_config_path():
    config = Config()
    parser = Parser(config)

    with pytest.raises(ValueError, match="not configured"):
        parser.load_collections()


def test_load_collections_raises_for_missing_file(tmp_path: Path):
    config = Config()
    config.collections_file_path = str(tmp_path / "missing.json")
    parser = Parser(config)

    with pytest.raises(FileNotFoundError, match="Collection map file not found"):
        parser.load_collections()


def test_load_gvars_loads_mapping(tmp_path: Path):
    gvar_path = tmp_path / "gvars" / "one.gvar"
    parser = _build_parser(tmp_path, {}, {gvar_path.as_posix(): "gvar-1"})

    parser.load_gvars()

    assert parser.gvars == {gvar_path: "gvar-1"}


def test_load_gvars_raises_for_missing_config_path():
    config = Config()
    parser = Parser(config)

    with pytest.raises(ValueError, match="not configured"):
        parser.load_gvars()


def test_load_gvars_raises_for_missing_file(tmp_path: Path):
    config = Config()
    config.gvars_file_path = str(tmp_path / "missing.json")
    parser = Parser(config)

    with pytest.raises(FileNotFoundError, match="GVAR map file not found"):
        parser.load_gvars()


def test_find_connected_files_matches_alias_docs_snippets_and_gvars(tmp_path: Path):
    collection_path = tmp_path / "collections" / "cool-collection"
    alias_path = collection_path / "my-alias" / "my-alias.alias"
    docs_path = collection_path / "my-alias" / "my-alias.md"
    snippet_path = collection_path / "spell.snippet"
    gvar_path = tmp_path / "gvars" / "one.gvar"

    parser = _build_parser(
        tmp_path,
        {collection_path.as_posix(): "col-1"},
        {gvar_path.as_posix(): "gvar-1"},
    )
    parser.load_collections()
    parser.load_gvars()

    parser.find_connected_files([alias_path, docs_path, snippet_path, gvar_path])

    types = {connected.type for connected in parser.connected_files}
    assert types == {"alias", "md", "snippet", "gvar"}


def test_find_connected_files_preserves_collection_metadata(tmp_path: Path):
    collection_path = tmp_path / "collections" / "cool-collection"
    nested_alias = collection_path / "parent" / "child.alias"

    parser = _build_parser(tmp_path, {collection_path.as_posix(): "col-1"}, {})
    parser.load_collections()
    parser.load_gvars()

    parser.find_connected_files([nested_alias])

    [connected] = parser.connected_files
    assert connected.collection == {"id": "col-1", "path": collection_path}
    assert connected.trimmed_path == Path("parent") / "child.alias"


def test_find_connected_files_ignores_files_outside_configured_collections(tmp_path: Path):
    configured_collection = tmp_path / "collections" / "cool"
    other_alias = tmp_path / "collections" / "other" / "x.alias"

    parser = _build_parser(tmp_path, {configured_collection.as_posix(): "col-1"}, {})
    parser.load_collections()
    parser.load_gvars()

    parser.find_connected_files([other_alias])

    assert parser.connected_files == []


def test_find_connected_files_ignores_unknown_gvars(tmp_path: Path):
    parser = _build_parser(tmp_path, {}, {})
    parser.load_collections()
    parser.load_gvars()

    parser.find_connected_files([tmp_path / "gvars" / "missing.gvar"])

    assert parser.connected_files == []

