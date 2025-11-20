####
# Avrae API Handler
###

import json
from pathlib import Path
from time import sleep
from typing import Any, Dict, Optional

from requests import RequestException, Response, Session

from models import ParsedAlias, ParsedSnippet


class Avrae:
    def __init__(self, config):
        self.token = config.token
        self.session: Session = Session()
        self.path_maps: Dict[str, Dict[str, str]] = {}  # {collection_id: PathMap} PathMap: {alias_id: Path}
        self.alias_outputs: Dict[str, Dict[Path, ParsedAlias]] = {}  # collection_id: {alias_path: ParsedAlias}
        self.snippet_outputs: Dict[str, Dict[Path, ParsedSnippet]] = {}  # collection_id: {snippet_path: ParsedSnippet}
        self.objects: Dict[str, Dict[str, Any]] = {}  # {object_id: data}

    def _request(
        self, method: str, path: str, request_data: Optional[Dict[str, Any]] = None
    ) -> Response:
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
                if response.status_code >= 500:
                    raise RequestException(
                        f"Server error {response.status_code}: {response.text}"
                    )
                if response.status_code >= 400:
                    raise RequestException(
                        f"Request failed {response.status_code}: {response.text}"
                    )
                return response
            except RequestException as exc:
                last_exc = exc
                if attempt == 2:
                    break
                sleep_seconds = 2**attempt
                print(f" - [API]: Request failed ({exc}); retrying in {sleep_seconds}s...")
                sleep(sleep_seconds)
        if last_exc:
            raise last_exc
        raise RequestException("Unknown request failure")

    def post_request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        r = self._request("post", path, request_data)
        try:
            return r.json()
        except ValueError as exc:
            raise ValueError(f"Non-JSON response from {path}: {r.text}") from exc

    def put_request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        r = self._request("put", path, request_data)
        return r.json()

    def patch_request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        r = self._request("patch", path, request_data)
        return r.json()

    def check_and_maybe_update(self, type_: str, parsed_data: ParsedAlias | ParsedSnippet) -> int:
        # load our file content and check for differences
        file_path = parsed_data.file_path
        with open(file_path, "r") as fp:
            file_contents = fp.read()
            if file_contents == parsed_data.data["code"]:
                return -1
        # update file via POST request
        update_response = self.post_request(
            f"https://api.avrae.io/workshop/{type_}/{parsed_data.data['_id']}/code",
            {"content": file_contents},
        )
        if update_response["success"] == False:
            raise Exception(
                f"Could not update {file_path}\n{json.dumps(update_response, indent=2)}"
            )
        print(f" - [API]: Updated {parsed_data.name}")
        code_version = update_response["data"]["version"]
        # update active code version
        update_code_version = self.put_request(
            path=f"https://api.avrae.io/workshop/{type_}/{parsed_data.data['_id']}/active-code",
            request_data={"version": code_version},
        )
        if update_code_version["success"] == False:
            raise Exception(
                f"Could not update code version of {file_path}\n{json.dumps(update_code_version, indent=2)}"
            )
        print(f" - [API]:\tCode Version: {code_version}")
        return 0

    def check_and_maybe_update_docs(self, type_: str, parsed_data: ParsedAlias | ParsedSnippet) -> int:
        # load our file content and check for differences
        file_path = parsed_data.docs_path
        with open(file_path, "r") as fp:
            file_contents = fp.read()
            if file_contents == parsed_data.data.get("docs", ""):
                return -1
        # update file via POST request
        update_response = self.patch_request(
            f"https://api.avrae.io/workshop/{type_}/{parsed_data.data['_id']}",
            {"name": parsed_data.name, "docs": file_contents},
        )
        if update_response["success"] == False:
            raise Exception(
                f"Could not update docs of {file_path}\n{json.dumps(update_response, indent=2)}"
            )
        print(f" - [API]: \tDocs Updated ({parsed_data.name})")
        return 0

    def get_gvar(self, gvar_id: str) -> Dict[str, Any]:
        path = f"https://api.avrae.io/customizations/gvars/{gvar_id}"
        return self._request("get", path).json()

    def check_and_maybe_update_gvar(self, gvar_path: Path, gvar_id: str) -> int:
        # load existing data
        gvar_data = self.get_gvar(gvar_id)["value"]

        file_path = gvar_path
        with open(file_path, "r") as fp:
            file_contents = fp.read()
            if file_contents == gvar_data:
                return -1
        # update file via POST request
        print(f" - [API]: Updating GVAR {gvar_id} at {gvar_path.as_posix()}")
        update_response = self.post_request(
            f"https://api.avrae.io/customizations/gvars/{gvar_id}",
            {"value": file_contents},
        )
        if isinstance(update_response, dict) and update_response.get("success") is False:
            raise Exception(
                f"Could not update GVAR {gvar_id}\n{json.dumps(update_response, indent=2)}"
            )
        return 0

    def get_collection_info(self, collection_id: str) -> Dict[str, Any]:
        path = f"https://api.avrae.io/workshop/collection/{collection_id}/full"
        r = self._request("get", path)
        request_data = r.json()
        if not request_data["success"]:
            raise Exception(
                f"{collection_id} collection data grab did not succeed.\n"
                f"{json.dumps(request_data, indent=2)}"
            )
        return request_data

    def parse_collection(self, collection_id: str, parser) -> None:
        collection_data = self.get_collection_info(collection_id)["data"]
        self.alias_outputs[collection_id] = {}
        self.snippet_outputs[collection_id] = {}
        for alias in collection_data["aliases"]:
            self.parse_alias(alias, parser)
        for snippet in collection_data["snippets"]:
            collection_path = [
                k.as_posix()
                for k, v in parser.collections.items()
                if v == collection_id
            ][0]
            parsed_snippet = ParsedSnippet(
                snippet["name"],
                snippet,
                Path(collection_path + "/" + snippet["name"] + ".snippet"),
                Path(collection_path + "/" + snippet["name"] + ".md"),
            )
            self.snippet_outputs[collection_id][
                parsed_snippet.file_path
            ] = parsed_snippet

    def parse_alias(self, alias_data, parser):
        # Recursive function to map paths for aliases
        collection_id = alias_data["collection_id"]
        collection_path = [
            k.as_posix() for k, v in parser.collections.items() if v == collection_id
        ][0]
        self.path_maps[collection_id] = self.path_maps.get(collection_id, {})
        # update our data
        self.objects[alias_data["_id"]] = alias_data
        path = ""
        if alias_data.get("parent_id") in self.path_maps[collection_id]:
            path += self.path_maps[collection_id][alias_data.get("parent_id")]
        if path == "":
            path = collection_path
        path += "/" + alias_data["name"]

        self.path_maps[collection_id][alias_data["_id"]] = path
        parsed_alias = ParsedAlias(
            alias_data["name"],
            alias_data,
            path,
            Path(path + "/" + alias_data["name"] + ".alias"),
            Path(path + "/" + alias_data["name"] + ".md"),
        )
        self.alias_outputs[collection_id][parsed_alias.file_path] = parsed_alias
        # handle sub-aliases
        for subalias in alias_data["subcommands"]:
            self.parse_alias(subalias, parser)
