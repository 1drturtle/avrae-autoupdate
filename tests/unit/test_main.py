import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import main
from parsing import ConnectedFile


def test_topic_formatter_adds_uppercase_topic():
    formatter = main.TopicFormatter("%(topic)s %(message)s")
    record = logging.LogRecord("parser", logging.INFO, __file__, 1, "hello", (), None)

    rendered = formatter.format(record)

    assert rendered == "PARSER hello"


def test_setup_logging_configures_root_logger():
    with patch("main.logging.basicConfig") as mock_basic_config:
        main.setup_logging()

    kwargs = mock_basic_config.call_args.kwargs
    assert kwargs["level"] == logging.INFO
    assert kwargs["force"] is True
    assert len(kwargs["handlers"]) == 1


def test_update_collections_updates_aliases_and_snippets():
    parser = MagicMock()
    parser.collections = {Path("collections/cool"): "col-1"}
    avrae = MagicMock()
    parsed_alias = SimpleNamespace(docs_path=Path("collections/cool/root/root.md"))
    parsed_snippet = SimpleNamespace(docs_path=Path("collections/cool/spell.md"))
    avrae.alias_outputs = {"col-1": {Path("collections/cool/root/root.alias"): parsed_alias}}
    avrae.snippet_outputs = {"col-1": {Path("collections/cool/spell.snippet"): parsed_snippet}}
    modified_paths = {
        Path("collections/cool/root/root.alias"),
        Path("collections/cool/root/root.md"),
        Path("collections/cool/spell.snippet"),
        Path("collections/cool/spell.md"),
    }

    main.update_collections(avrae, parser, modified_paths)

    avrae.parse_collection.assert_called_once_with("col-1", parser)
    avrae.check_and_maybe_update.assert_any_call("alias", parsed_alias)
    avrae.check_and_maybe_update_docs.assert_any_call("alias", parsed_alias)
    avrae.check_and_maybe_update.assert_any_call("snippet", parsed_snippet)
    avrae.check_and_maybe_update_docs.assert_any_call("snippet", parsed_snippet)


def test_run_exits_when_modified_files_is_none():
    config = MagicMock()
    config.modified_files = None

    with patch("main.Config", return_value=config), patch(
        "main.exit", side_effect=SystemExit(1)
    ) as mock_exit:
        with pytest.raises(SystemExit):
            main.run()

    mock_exit.assert_called_once_with(1)


def test_run_exits_when_no_relevant_modified_files():
    config = MagicMock()
    config.modified_files = ["README.md"]

    with patch("main.Config", return_value=config), patch(
        "main.utils.parse_paths", return_value=[]
    ), patch("main.exit", side_effect=SystemExit(0)) as mock_exit:
        with pytest.raises(SystemExit):
            main.run()

    mock_exit.assert_called_once_with(0)


def test_run_exits_when_no_connected_files():
    config = MagicMock()
    config.modified_files = ["spell.alias"]
    parser = MagicMock()
    parser.connected_files = []

    with patch("main.Config", return_value=config), patch(
        "main.utils.parse_paths", return_value=[Path("spell.alias")]
    ), patch("main.Parser", return_value=parser), patch(
        "main.exit", side_effect=SystemExit(0)
    ) as mock_exit:
        with pytest.raises(SystemExit):
            main.run()

    parser.load_collections.assert_called_once_with()
    parser.load_gvars.assert_called_once_with()
    parser.find_connected_files.assert_called_once_with([Path("spell.alias")])
    mock_exit.assert_called_once_with(0)


def test_run_updates_aliases_docs_snippets_and_gvars():
    config = MagicMock()
    config.modified_files = ["items"]
    parser = MagicMock()
    parser.collections = {Path("collections/cool"): "col-1"}
    parser.gvars = {Path("gvars/one.gvar"): "g1"}
    parser.connected_files = [
        ConnectedFile("alias", Path("collections/cool/root/root.alias"), {"id": "col-1", "path": Path("collections/cool")}, Path("root/root.alias")),
        ConnectedFile("md", Path("collections/cool/root/root.md"), {"id": "col-1", "path": Path("collections/cool")}, Path("root/root.md")),
        ConnectedFile("snippet", Path("collections/cool/spell.snippet"), {"id": "col-1", "path": Path("collections/cool")}, Path("spell.snippet")),
        ConnectedFile("md", Path("collections/cool/spell.md"), {"id": "col-1", "path": Path("collections/cool")}, Path("spell.md")),
        ConnectedFile("gvar", Path("gvars/one.gvar"), None, None),
    ]
    avrae = MagicMock()
    parsed_alias = SimpleNamespace(docs_path=Path("collections/cool/root/root.md"))
    parsed_snippet = SimpleNamespace(docs_path=Path("collections/cool/spell.md"))
    avrae.alias_outputs = {"col-1": {Path("collections/cool/root/root.alias"): parsed_alias}}
    avrae.snippet_outputs = {"col-1": {Path("collections/cool/spell.snippet"): parsed_snippet}}

    with patch("main.Config", return_value=config), patch.object(config, "load_config"), patch(
        "main.utils.parse_paths", return_value=[Path("items")]
    ), patch("main.Parser", return_value=parser), patch("main.Avrae", return_value=avrae), patch(
        "main.update_collections"
    ) as mock_update_collections:
        main.run()

    mock_update_collections.assert_called_once_with(
        avrae,
        parser,
        {
            Path("collections/cool/root/root.alias"),
            Path("collections/cool/root/root.md"),
            Path("collections/cool/spell.snippet"),
            Path("collections/cool/spell.md"),
            Path("gvars/one.gvar"),
        },
    )
    avrae.check_and_maybe_update_gvar.assert_called_once_with(Path("gvars/one.gvar"), "g1")
