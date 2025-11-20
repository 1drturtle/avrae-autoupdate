from pathlib import Path
from types import SimpleNamespace
from typing import List
from unittest import mock

import pytest

from api import Avrae
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
