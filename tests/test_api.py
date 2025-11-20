from pathlib import Path
from types import SimpleNamespace
from typing import List
from unittest import mock

import pytest

from api import Avrae
from config import Config
from parsing import Parser
from models import ParsedAlias


class FakeResponse:
    def __init__(self, status_code: int, text: str = "", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data or {}
        self.content = text.encode("ascii", errors="ignore")

    def json(self):
        return self._json_data


def test_request_retries_and_succeeds(monkeypatch: pytest.MonkeyPatch):
    config = SimpleNamespace(token="token")
    api = Avrae(config)

    responses: List[FakeResponse] = [
        FakeResponse(500, "server error"),
        FakeResponse(200, '{"success": true}', {"success": True}),
    ]

    def fake_request(method, url, headers=None, json=None, timeout=None):
        return responses.pop(0)

    monkeypatch.setattr(api.session, "request", fake_request)
    monkeypatch.setattr("api.sleep", lambda _: None)

    response = api._request("get", "http://example.com")

    assert response.status_code == 200


def test_check_and_maybe_update_docs_uses_docs_field(tmp_path: Path):
    docs_path = tmp_path / "alias.md"
    docs_path.write_text("new docs content")

    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "docs": "old docs content", "code": "old code"},
        tmp_path,
        tmp_path / "alias.alias",
        docs_path,
    )

    config = SimpleNamespace(token="token")
    api = Avrae(config)
    with mock.patch.object(
        api, "patch_request", return_value={"success": True}
    ) as patched:
        api.check_and_maybe_update_docs("alias", parsed_alias)

    assert patched.called
    assert patched.call_args.args[1]["docs"] == "new docs content"


def test_check_and_maybe_update_docs_no_change(tmp_path: Path):
    docs_path = tmp_path / "alias.md"
    docs_path.write_text("existing docs")

    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "docs": "existing docs", "code": "old code"},
        tmp_path,
        tmp_path / "alias.alias",
        docs_path,
    )

    api = Avrae(SimpleNamespace(token="token"))
    with mock.patch.object(api, "patch_request") as patched:
        result = api.check_and_maybe_update_docs("alias", parsed_alias)

    assert result == -1
    patched.assert_not_called()


def test_check_and_maybe_update_skips_when_code_unchanged(tmp_path: Path):
    code_path = tmp_path / "alias.alias"
    code_path.write_text("same code")

    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "docs": "existing docs", "code": "same code"},
        tmp_path,
        code_path,
        tmp_path / "alias.md",
    )

    api = Avrae(SimpleNamespace(token="token"))
    with mock.patch.object(api, "post_request") as patched_post:
        result = api.check_and_maybe_update("alias", parsed_alias)

    assert result == -1
    patched_post.assert_not_called()


def test_request_retries_and_raises_on_persistent_failure(monkeypatch: pytest.MonkeyPatch):
    config = SimpleNamespace(token="token")
    api = Avrae(config)

    responses: List[FakeResponse] = [
        FakeResponse(500, "server error"),
        FakeResponse(500, "server error"),
        FakeResponse(500, "server error"),
    ]

    def fake_request(method, url, headers=None, json=None, timeout=None):
        return responses.pop(0)

    sleeps: List[int] = []
    monkeypatch.setattr(api.session, "request", fake_request)
    monkeypatch.setattr("api.sleep", lambda seconds: sleeps.append(seconds))

    with pytest.raises(Exception):
        api._request("get", "http://example.com")

    assert sleeps == [1, 2]
    assert len(responses) == 0


def test_get_gvar_raises_on_unsuccessful_response(monkeypatch: pytest.MonkeyPatch):
    api = Avrae(SimpleNamespace(token="token"))

    def fake_request(method, url, headers=None, json=None, timeout=None):
        return FakeResponse(200, json_data={"success": False, "error": "bad"})

    monkeypatch.setattr(api.session, "request", fake_request)

    with pytest.raises(Exception) as excinfo:
        api.get_gvar("gvar-1")

    assert "gvar-1" in str(excinfo.value)


def test_check_and_maybe_update_gvar_missing_value(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    api = Avrae(SimpleNamespace(token="token"))
    gvar_file = tmp_path / "one.gvar"
    gvar_file.write_text("content")

    monkeypatch.setattr(api, "get_gvar", lambda _gid: {"success": True})

    with pytest.raises(Exception):
        api.check_and_maybe_update_gvar(gvar_file, "gvar-1")


def test_check_and_maybe_update_gvar_skips_when_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    api = Avrae(SimpleNamespace(token="token"))
    gvar_file = tmp_path / "one.gvar"
    gvar_file.write_text("same contents")

    monkeypatch.setattr(api, "get_gvar", lambda _gid: {"value": "same contents"})
    with mock.patch.object(api, "post_request") as patched_post:
        result = api.check_and_maybe_update_gvar(gvar_file, "gvar-1")

    assert result == -1
    patched_post.assert_not_called()


def test_parse_alias_recurses_subcommands(tmp_path: Path):
    api = Avrae(SimpleNamespace(token="token"))
    parser = Parser(Config())

    collection_path = tmp_path / "collections" / "cool"
    parser.collections = {collection_path: "col-1"}
    api.alias_outputs["col-1"] = {}

    alias_tree = {
        "name": "root",
        "_id": "a1",
        "collection_id": "col-1",
        "parent_id": None,
        "subcommands": [
            {
                "name": "child",
                "_id": "a2",
                "collection_id": "col-1",
                "parent_id": "a1",
                "subcommands": [
                    {
                        "name": "grand",
                        "_id": "a3",
                        "collection_id": "col-1",
                        "parent_id": "a2",
                        "subcommands": [],
                    }
                ],
            }
        ],
    }

    api.parse_alias(alias_tree, parser)

    # path_maps should track the hierarchical paths for each alias id
    col_map = api.path_maps["col-1"]
    assert col_map["a1"].endswith("/root")
    assert col_map["a2"].endswith("/root/child")
    assert col_map["a3"].endswith("/root/child/grand")

    # alias_outputs should contain file paths for each alias node
    outputs = api.alias_outputs["col-1"]
    paths = {p.as_posix() for p in outputs.keys()}
    assert collection_path.as_posix() + "/root/root.alias" in paths
    assert collection_path.as_posix() + "/root/child/child.alias" in paths
    assert collection_path.as_posix() + "/root/child/grand/grand.alias" in paths
