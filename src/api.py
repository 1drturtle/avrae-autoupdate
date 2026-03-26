####
# Avrae API Handler
###

import json
import logging
from pathlib import Path
from time import sleep
from typing import Any, Dict, Optional

from requests import RequestException, Response, Session

from models import ParsedAlias, ParsedSnippet
from parsing import Parser

logger = logging.getLogger("api")


class AvraeError(Exception):
    """Base class for Avrae API and response failures."""

    pass


class AvraeRequestError(AvraeError):
    """Raised when an HTTP request fails or returns a failing status code."""

    pass


class AvraeResponseError(AvraeError):
    """Raised when the API response body is malformed or unsuccessful."""

    pass


class AvraeHttpClient:
    """Small transport wrapper around requests with retry and decode helpers."""

    def __init__(self, token: str, session: Optional[Session] = None):
        self.token = token
        self.session: Session = session or Session()

    def request(
        self, method: str, path: str, request_data: Optional[Dict[str, Any]] = None
    ) -> Response:
        """Send a request, retrying only transient network and 5xx failures."""
        headers = {"Authorization": self.token}
        last_exc: Optional[Exception] = None
        for attempt in range(3):
            try:
                response = self.session.request(
                    method,
                    url=path,
                    headers=headers,
                    json=request_data,
                    timeout=10,
                )
            except RequestException as exc:
                last_exc = exc
                if attempt == 2:
                    break
                self._sleep_before_retry(exc, attempt)
                continue

            if response.status_code >= 500:
                last_exc = AvraeRequestError(
                    f"Server error {response.status_code}: {response.text}"
                )
                if attempt == 2:
                    break
                self._sleep_before_retry(last_exc, attempt)
                continue

            if response.status_code >= 400:
                raise AvraeRequestError(
                    f"Request failed {response.status_code}: {response.text}"
                )
            return response

        if last_exc:
            raise last_exc
        raise AvraeRequestError("Unknown request failure")

    @staticmethod
    def _sleep_before_retry(exc: Exception, attempt: int) -> None:
        sleep_seconds = 2**attempt
        logger.warning(f"Request failed ({exc}); retrying in {sleep_seconds}s...")
        sleep(sleep_seconds)

    def request_json(
        self, method: str, path: str, request_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send a request and require a JSON object response body."""
        response = self.request(method, path, request_data)
        try:
            payload = response.json()
        except ValueError as exc:
            raise AvraeResponseError(
                f"Non-JSON response from {path}: {response.text}"
            ) from exc
        if not isinstance(payload, dict):
            raise AvraeResponseError(
                f"Unexpected non-object JSON response from {path}: {payload!r}"
            )
        return payload

    def request_text(
        self, method: str, path: str, request_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send a request and return the raw text body."""
        return self.request(method, path, request_data).text


def _read_text(path: Path) -> str:
    """Read a UTF-8 text file from disk."""
    with open(path, "r") as fp:
        return fp.read()


def get_collection_path(parser: Parser, collection_id: str) -> Path:
    """Resolve a configured collection id back to its local base path."""
    for path, parser_collection_id in parser.collections.items():
        if parser_collection_id == collection_id:
            return path
    raise AvraeResponseError(f"Unknown collection id: {collection_id}")


def _build_alias_outputs(
    collection_path: Path,
    aliases: list[Dict[str, Any]],
) -> Dict[Path, ParsedAlias]:
    """Build alias file mappings from the nested Avrae alias payload."""
    alias_outputs: Dict[Path, ParsedAlias] = {}
    parent_paths: Dict[str, Path] = {}

    def visit(alias_data: Dict[str, Any]) -> None:
        parent_id = alias_data.get("parent_id")
        parent_path = (
            parent_paths.get(parent_id, collection_path)
            if isinstance(parent_id, str)
            else collection_path
        )
        alias_dir = parent_path / alias_data["name"]
        parsed_alias = ParsedAlias(
            alias_data["name"],
            alias_data,
            alias_dir,
            alias_dir / f"{alias_data['name']}.alias",
            alias_dir / f"{alias_data['name']}.md",
        )
        alias_outputs[parsed_alias.file_path] = parsed_alias
        parent_paths[alias_data["_id"]] = alias_dir

        for subalias in alias_data["subcommands"]:
            visit(subalias)

    for alias in aliases:
        visit(alias)

    return alias_outputs


def build_collection_outputs(
    collection_id: str, parser: Parser, collection_data: Dict[str, Any]
) -> tuple[Dict[Path, ParsedAlias], Dict[Path, ParsedSnippet]]:
    """Convert one collection payload into local alias and snippet file mappings."""
    collection_path = get_collection_path(parser, collection_id)
    alias_outputs = _build_alias_outputs(collection_path, collection_data["aliases"])
    snippet_outputs: Dict[Path, ParsedSnippet] = {}
    for snippet in collection_data["snippets"]:
        parsed_snippet = ParsedSnippet(
            snippet["name"],
            snippet,
            collection_path / f"{snippet['name']}.snippet",
            collection_path / f"{snippet['name']}.md",
        )
        snippet_outputs[parsed_snippet.file_path] = parsed_snippet
    return alias_outputs, snippet_outputs


class Avrae:
    """High-level Avrae client that preserves the current updater workflow."""

    def __init__(self, config):
        self.token = config.token
        self.client = AvraeHttpClient(self.token)
        self.session = self.client.session
        self.alias_outputs: Dict[
            str, Dict[Path, ParsedAlias]
        ] = {}  # collection_id: {alias_path: ParsedAlias}
        self.snippet_outputs: Dict[
            str, Dict[Path, ParsedSnippet]
        ] = {}  # collection_id: {snippet_path: ParsedSnippet}

    @staticmethod
    def _read_text(path: Path) -> str:
        return _read_text(path)

    @staticmethod
    def _get_collection_path(parser, collection_id: str) -> str:
        return get_collection_path(parser, collection_id).as_posix()

    def _request(
        self, method: str, path: str, request_data: Optional[Dict[str, Any]] = None
    ) -> Response:
        return self.client.request(method, path, request_data)

    def post_request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.request_json("post", path, request_data)

    def post_request_str(self, path: str, request_data: Dict[str, Any]) -> str:
        return self.client.request_text("post", path, request_data)

    def put_request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.request_json("put", path, request_data)

    def patch_request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.request_json("patch", path, request_data)

    @staticmethod
    def _require_success(payload: Dict[str, Any], error_message: str) -> Dict[str, Any]:
        """Require a payload-level success flag when the API uses one."""
        if payload.get("success") is False:
            raise AvraeResponseError(
                f"{error_message}\n{json.dumps(payload, indent=2)}"
            )
        return payload

    def check_and_maybe_update(
        self, type_: str, parsed_data: ParsedAlias | ParsedSnippet
    ) -> int:
        # load our file content and check for differences
        file_path = parsed_data.file_path
        file_contents = self._read_text(file_path)
        if file_contents == parsed_data.data["code"]:
            return -1
        # update file via POST request
        update_response = self.post_request(
            f"https://api.avrae.io/workshop/{type_}/{parsed_data.data['_id']}/code",
            {"content": file_contents},
        )
        self._require_success(update_response, f"Could not update {file_path}")
        logger.info(f"Updated {parsed_data.name}")
        try:
            code_version = update_response["data"]["version"]
        except KeyError as exc:
            raise AvraeResponseError(
                f"Could not read code version for {file_path}\n"
                f"{json.dumps(update_response, indent=2)}"
            ) from exc
        # update active code version
        update_code_version = self.put_request(
            path=f"https://api.avrae.io/workshop/{type_}/{parsed_data.data['_id']}/active-code",
            request_data={"version": code_version},
        )
        self._require_success(
            update_code_version, f"Could not update code version of {file_path}"
        )
        logger.info(f"Code version: {code_version}")
        return 0

    def check_and_maybe_update_docs(
        self, type_: str, parsed_data: ParsedAlias | ParsedSnippet
    ) -> int:
        # load our file content and check for differences
        file_path = parsed_data.docs_path
        file_contents = self._read_text(file_path)
        if file_contents == parsed_data.data.get("docs", ""):
            return -1
        # update file via POST request
        update_response = self.patch_request(
            f"https://api.avrae.io/workshop/{type_}/{parsed_data.data['_id']}",
            {"name": parsed_data.name, "docs": file_contents},
        )
        self._require_success(update_response, f"Could not update docs of {file_path}")
        logger.info(f"Docs updated ({parsed_data.name})")
        return 0

    def get_gvar(self, gvar_id: str) -> Dict[str, Any]:
        path = f"https://api.avrae.io/customizations/gvars/{gvar_id}"
        request_data = self.client.request_json("get", path)
        if request_data.get("success") is False:
            raise AvraeResponseError(
                f"{gvar_id} GVAR data grab did not succeed.\n"
                f"{json.dumps(request_data, indent=2)}"
            )
        return request_data

    def check_and_maybe_update_gvar(self, gvar_path: Path, gvar_id: str) -> int:
        # load existing data
        gvar_response = self.get_gvar(gvar_id)
        try:
            gvar_data = gvar_response["value"]
        except KeyError as exc:
            raise AvraeResponseError(
                f"Unexpected GVAR response for {gvar_id}\n{json.dumps(gvar_response, indent=2)}"
            ) from exc

        file_contents = self._read_text(gvar_path)
        if file_contents == gvar_data:
            return -1
        # update file via POST request
        logger.info(f"Updating GVAR {gvar_id} at {gvar_path.as_posix()}")
        update_response = self.post_request_str(
            f"https://api.avrae.io/customizations/gvars/{gvar_id}",
            {"value": file_contents},
        )
        if update_response != "Gvar updated.":
            raise AvraeResponseError(
                f"Could not update GVAR {gvar_id}\n{update_response}"
            )
        return 0

    def get_collection_info(self, collection_id: str) -> Dict[str, Any]:
        path = f"https://api.avrae.io/workshop/collection/{collection_id}/full"
        request_data = self.client.request_json("get", path)
        if request_data.get("success") is False:
            raise AvraeResponseError(
                f"{collection_id} collection data grab did not succeed.\n"
                f"{json.dumps(request_data, indent=2)}"
            )
        return request_data

    def parse_collection(self, collection_id: str, parser: Parser) -> None:
        collection_data = self.get_collection_info(collection_id)["data"]
        alias_outputs, snippet_outputs = build_collection_outputs(
            collection_id, parser, collection_data
        )
        self.alias_outputs[collection_id] = alias_outputs
        self.snippet_outputs[collection_id] = snippet_outputs
