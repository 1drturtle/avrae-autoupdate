from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest
from requests import RequestException

from api import (
    Avrae,
    AvraeRequestError,
    AvraeResponseError,
    build_collection_outputs,
    get_collection_path,
)
from models import ParsedAlias


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "", json_data=None):
        self.status_code = status_code
        self.text = text
        self._json_data = {} if json_data is None else json_data

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


@pytest.fixture
def api() -> Avrae:
    return Avrae(SimpleNamespace(token="token"))


def test_request_returns_successful_response(api: Avrae):
    response = FakeResponse(200, json_data={"success": True})
    api.session.request = MagicMock(return_value=response)

    result = api._request("get", "http://example.com")

    assert result is response
    api.session.request.assert_called_once_with(
        "get",
        url="http://example.com",
        headers={"Authorization": "token"},
        json=None,
        timeout=10,
    )


def test_request_retries_after_server_error_and_succeeds(api: Avrae):
    api.session.request = MagicMock(
        side_effect=[
            FakeResponse(500, "server error"),
            FakeResponse(200, json_data={"success": True}),
        ]
    )

    with patch("api.sleep") as mock_sleep:
        result = api._request("get", "http://example.com")

    assert result.status_code == 200
    mock_sleep.assert_called_once_with(1)


def test_request_retries_after_request_exception_and_raises_when_exhausted(api: Avrae):
    api.session.request = MagicMock(side_effect=RequestException("boom"))

    with patch("api.sleep") as mock_sleep:
        with pytest.raises(RequestException, match="boom"):
            api._request("get", "http://example.com")

    assert mock_sleep.call_args_list == [call(1), call(2)]


def test_request_raises_immediately_for_client_error(api: Avrae):
    api.session.request = MagicMock(return_value=FakeResponse(404, "missing"))

    with patch("api.sleep") as mock_sleep:
        with pytest.raises(AvraeRequestError, match="Request failed 404: missing"):
            api._request("get", "http://example.com")

    mock_sleep.assert_not_called()


def test_post_request_returns_json_payload(api: Avrae):
    with patch.object(
        api.client,
        "request_json",
        return_value={"success": True, "data": "ok"},
    ) as mock_request:
        result = api.post_request("http://example.com", {"value": 1})

    assert result == {"success": True, "data": "ok"}
    mock_request.assert_called_once_with("post", "http://example.com", {"value": 1})


def test_post_request_raises_for_non_json_response(api: Avrae):
    with patch.object(
        api.client,
        "request_json",
        side_effect=AvraeResponseError("Non-JSON response from http://example.com"),
    ):
        with pytest.raises(AvraeResponseError, match="Non-JSON response from http://example.com"):
            api.post_request("http://example.com", {"value": 1})


def test_post_request_str_returns_response_text(api: Avrae):
    with patch.object(api.client, "request_text", return_value="body") as mock_request:
        result = api.post_request_str("http://example.com", {"value": 1})

    assert result == "body"
    mock_request.assert_called_once_with("post", "http://example.com", {"value": 1})


def test_put_request_returns_response_json(api: Avrae):
    with patch.object(api.client, "request_json", return_value={"success": True}) as mock_request:
        result = api.put_request("http://example.com", {"value": 1})

    assert result == {"success": True}
    mock_request.assert_called_once_with("put", "http://example.com", {"value": 1})


def test_patch_request_returns_response_json(api: Avrae):
    with patch.object(api.client, "request_json", return_value={"success": True}) as mock_request:
        result = api.patch_request("http://example.com", {"value": 1})

    assert result == {"success": True}
    mock_request.assert_called_once_with("patch", "http://example.com", {"value": 1})


def test_check_and_maybe_update_returns_negative_one_when_code_matches(api: Avrae):
    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "code": "same code", "docs": "docs"},
        Path("alias"),
        Path("alias.alias"),
        Path("alias.md"),
    )

    with (
        patch.object(api, "_read_text", return_value="same code"),
        patch.object(api, "post_request") as mock_post,
    ):
        result = api.check_and_maybe_update("alias", parsed_alias)

    assert result == -1
    mock_post.assert_not_called()


def test_check_and_maybe_update_updates_code_and_active_version(api: Avrae):
    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "code": "old code", "docs": "docs"},
        Path("alias"),
        Path("alias.alias"),
        Path("alias.md"),
    )

    with (
        patch.object(api, "_read_text", return_value="new code"),
        patch.object(
            api,
            "post_request",
            return_value={"success": True, "data": {"version": "v2"}},
        ) as mock_post,
        patch.object(api, "put_request", return_value={"success": True}) as mock_put,
    ):
        result = api.check_and_maybe_update("alias", parsed_alias)

    assert result == 0
    mock_post.assert_called_once_with(
        "https://api.avrae.io/workshop/alias/123/code",
        {"content": "new code"},
    )
    mock_put.assert_called_once_with(
        path="https://api.avrae.io/workshop/alias/123/active-code",
        request_data={"version": "v2"},
    )


def test_check_and_maybe_update_raises_when_update_response_fails(api: Avrae):
    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "code": "old code", "docs": "docs"},
        Path("alias"),
        Path("alias.alias"),
        Path("alias.md"),
    )

    with (
        patch.object(api, "_read_text", return_value="new code"),
        patch.object(api, "post_request", return_value={"success": False}),
    ):
        with pytest.raises(AvraeResponseError, match="Could not update"):
            api.check_and_maybe_update("alias", parsed_alias)


def test_check_and_maybe_update_raises_when_code_version_is_missing(api: Avrae):
    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "code": "old code", "docs": "docs"},
        Path("alias"),
        Path("alias.alias"),
        Path("alias.md"),
    )

    with (
        patch.object(api, "_read_text", return_value="new code"),
        patch.object(api, "post_request", return_value={"success": True, "data": {}}),
    ):
        with pytest.raises(AvraeResponseError, match="Could not read code version"):
            api.check_and_maybe_update("alias", parsed_alias)


def test_check_and_maybe_update_raises_when_active_code_update_fails(api: Avrae):
    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "code": "old code", "docs": "docs"},
        Path("alias"),
        Path("alias.alias"),
        Path("alias.md"),
    )

    with (
        patch.object(api, "_read_text", return_value="new code"),
        patch.object(
            api,
            "post_request",
            return_value={"success": True, "data": {"version": "v2"}},
        ),
        patch.object(api, "put_request", return_value={"success": False}),
    ):
        with pytest.raises(AvraeResponseError, match="Could not update code version"):
            api.check_and_maybe_update("alias", parsed_alias)


def test_check_and_maybe_update_docs_returns_negative_one_when_docs_match(api: Avrae):
    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "code": "code", "docs": "same docs"},
        Path("alias"),
        Path("alias.alias"),
        Path("alias.md"),
    )

    with (
        patch.object(api, "_read_text", return_value="same docs"),
        patch.object(api, "patch_request") as mock_patch,
    ):
        result = api.check_and_maybe_update_docs("alias", parsed_alias)

    assert result == -1
    mock_patch.assert_not_called()


def test_check_and_maybe_update_docs_updates_changed_docs(api: Avrae):
    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "code": "code", "docs": "old docs"},
        Path("alias"),
        Path("alias.alias"),
        Path("alias.md"),
    )

    with (
        patch.object(api, "_read_text", return_value="new docs"),
        patch.object(api, "patch_request", return_value={"success": True}) as mock_patch,
    ):
        result = api.check_and_maybe_update_docs("alias", parsed_alias)

    assert result == 0
    mock_patch.assert_called_once_with(
        "https://api.avrae.io/workshop/alias/123",
        {"name": "alias", "docs": "new docs"},
    )


def test_check_and_maybe_update_docs_raises_when_patch_fails(api: Avrae):
    parsed_alias = ParsedAlias(
        "alias",
        {"_id": "123", "code": "code", "docs": "old docs"},
        Path("alias"),
        Path("alias.alias"),
        Path("alias.md"),
    )

    with (
        patch.object(api, "_read_text", return_value="new docs"),
        patch.object(api, "patch_request", return_value={"success": False}),
    ):
        with pytest.raises(AvraeResponseError, match="Could not update docs"):
            api.check_and_maybe_update_docs("alias", parsed_alias)


def test_get_gvar_returns_payload(api: Avrae):
    with patch.object(api.client, "request_json", return_value={"value": "data"}) as mock_request:
        assert api.get_gvar("g1") == {"value": "data"}

    mock_request.assert_called_once_with("get", "https://api.avrae.io/customizations/gvars/g1")


def test_get_gvar_raises_for_unsuccessful_payload(api: Avrae):
    with patch.object(api.client, "request_json", return_value={"success": False}):
        with pytest.raises(AvraeResponseError, match="g1 GVAR data grab did not succeed"):
            api.get_gvar("g1")


def test_check_and_maybe_update_gvar_returns_negative_one_when_value_matches(
    api: Avrae,
):
    with (
        patch.object(api, "get_gvar", return_value={"value": "same"}),
        patch.object(api, "_read_text", return_value="same"),
        patch.object(api, "post_request_str") as mock_post,
    ):
        result = api.check_and_maybe_update_gvar(Path("one.gvar"), "g1")

    assert result == -1
    mock_post.assert_not_called()


def test_check_and_maybe_update_gvar_updates_changed_value(api: Avrae):
    with (
        patch.object(api, "get_gvar", return_value={"value": "old"}),
        patch.object(api, "_read_text", return_value="new"),
        patch.object(api, "post_request_str", return_value="Gvar updated.") as mock_post,
    ):
        result = api.check_and_maybe_update_gvar(Path("one.gvar"), "g1")

    assert result == 0
    mock_post.assert_called_once_with(
        "https://api.avrae.io/customizations/gvars/g1",
        {"value": "new"},
    )


def test_check_and_maybe_update_gvar_raises_for_missing_value_key(api: Avrae):
    with patch.object(api, "get_gvar", return_value={"success": True}):
        with pytest.raises(AvraeResponseError, match="Unexpected GVAR response"):
            api.check_and_maybe_update_gvar(Path("one.gvar"), "g1")


def test_check_and_maybe_update_gvar_raises_for_bad_update_response(api: Avrae):
    with (
        patch.object(api, "get_gvar", return_value={"value": "old"}),
        patch.object(api, "_read_text", return_value="new"),
        patch.object(api, "post_request_str", return_value="bad"),
    ):
        with pytest.raises(AvraeResponseError, match="Could not update GVAR g1"):
            api.check_and_maybe_update_gvar(Path("one.gvar"), "g1")


def test_get_collection_info_returns_data(api: Avrae):
    with patch.object(
        api.client,
        "request_json",
        return_value={"success": True, "data": {}},
    ) as mock_request:
        assert api.get_collection_info("col-1") == {"success": True, "data": {}}

    mock_request.assert_called_once_with("get", "https://api.avrae.io/workshop/collection/col-1/full")


def test_get_collection_info_raises_for_unsuccessful_payload(api: Avrae):
    with patch.object(api.client, "request_json", return_value={"success": False}):
        with pytest.raises(AvraeResponseError, match="col-1 collection data grab did not succeed"):
            api.get_collection_info("col-1")


def test_parse_collection_creates_alias_and_snippet_outputs(api: Avrae):
    parser = SimpleNamespace(collections={Path("collections/cool"): "col-1"})
    alias = {
        "name": "root",
        "_id": "a1",
        "collection_id": "col-1",
        "parent_id": None,
        "subcommands": [],
    }
    snippet = {"name": "spell", "_id": "s1"}

    with patch.object(
        api,
        "get_collection_info",
        return_value={"data": {"aliases": [alias], "snippets": [snippet]}},
    ):
        alias_outputs, snippet_outputs = api.parse_collection("col-1", parser)  # type: ignore[arg-type]

    assert Path("collections/cool/root/root.alias") in alias_outputs
    assert Path("collections/cool/spell.snippet") in snippet_outputs


def test_build_collection_outputs_creates_root_and_nested_alias_paths():
    parser = SimpleNamespace(collections={Path("collections/cool"): "col-1"})
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
                "subcommands": [],
            }
        ],
    }

    alias_outputs, snippet_outputs = build_collection_outputs(
        "col-1",
        parser,  # type: ignore[arg-type]
        {"aliases": [alias_tree], "snippets": []},
    )

    assert Path("collections/cool/root/root.alias") in alias_outputs
    assert Path("collections/cool/root/child/child.alias") in alias_outputs
    assert snippet_outputs == {}


def test_build_collection_outputs_creates_snippet_paths():
    parser = SimpleNamespace(collections={Path("collections/cool"): "col-1"})

    _, snippet_outputs = build_collection_outputs(
        "col-1",
        parser,  # type: ignore[arg-type]
        {"aliases": [], "snippets": [{"name": "spell", "_id": "s1"}]},
    )

    assert Path("collections/cool/spell.snippet") in snippet_outputs
    assert snippet_outputs[Path("collections/cool/spell.snippet")].docs_path == Path("collections/cool/spell.md")


def test_read_text_reads_file_contents(tmp_path: Path):
    file_path = tmp_path / "data.txt"
    file_path.write_text("hello")

    assert Avrae._read_text(file_path) == "hello"


def test_get_collection_path_returns_matching_collection_path():
    parser = SimpleNamespace(collections={Path("collections/cool"): "col-1"})

    assert get_collection_path(parser, "col-1") == Path("collections/cool")  # type: ignore[arg-type]


def test_get_collection_path_raises_for_unknown_collection_id():
    parser = SimpleNamespace(collections={Path("collections/cool"): "col-1"})

    with pytest.raises(AvraeResponseError, match="Unknown collection id: missing"):
        get_collection_path(parser, "missing")  # type: ignore[arg-type]
