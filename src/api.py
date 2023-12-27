####
# Avrae API Handler
###

import requests
import json
from pathlib import Path

from models import *


class Avrae:
    def __init__(self, config):
        self.token = config.token
        self.path_maps = {}  # {collection_id: PathMap} PathMap: {alias_id: Path}
        self.alias_outputs = {}  # collection_id: {alias_path: ParsedAlias}
        self.snippet_outputs = {}  # collection_id: {snippet_path: ParsedSnippet}
        self.objects = {}  # {object_id: data}

    def post_request(self, api_key, path, request_data):
        headers = {"Authorization": api_key}
        r = requests.post(url=path, headers=headers, json=request_data)
        raw_data = r.content.decode("ascii")
        return r.json() if raw_data.startswith("{") else raw_data

    def put_request(self, api_key, path, request_data):
        headers = {"Authorization": api_key}
        r = requests.put(url=path, headers=headers, json=request_data)
        return r.json()

    def patch_request(self, api_key, path, request_data):
        headers = {"Authorization": api_key}
        r = requests.patch(url=path, headers=headers, json=request_data)
        return r.json()

    def check_and_maybe_update(self, type_: str, parsed_data):
        # load our file content and check for differences
        file_path = parsed_data.file_path
        with open(file_path, "r") as fp:
            file_contents = fp.read()
            if file_contents == parsed_data.data["code"]:
                return -1
        # update file via POST request
        update_response = self.post_request(
            self.token,
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
            api_key=self.token,
            path=f"https://api.avrae.io/workshop/{parsed_data.data['_id']}/active-code",
            request_data=json.dumps({"version": code_version}),
        )
        if update_response["success"] == False:
            raise Exception(
                f"Could not update code version of {file_path}\n{json.dumps(update_response, indent=2)}"
            )
        print(f" - [API]:\tCode Version: {code_version}")
        return 0

    def check_and_maybe_update_docs(self, type_: str, parsed_data):
        # load our file content and check for differences
        file_path = parsed_data.docs_path
        with open(file_path, "r") as fp:
            file_contents = fp.read()
            if file_contents == parsed_data.data["code"]:
                return -1
        # update file via POST request
        # TODO: Capture and log
        update_response = self.patch_request(
            self.token,
            f"https://api.avrae.io/workshop/{type_}/{parsed_data.data['_id']}",
            {"name": parsed_data.name, "docs": file_contents},
        )
        if update_response["success"] == False:
            raise Exception(
                f"Could not update docs of {file_path}\n{json.dumps(update_response, indent=2)}"
            )
        print(f" - [API]: \tDocs Updated ({parsed_data.name})")

    def get_gvar(self, gvar_id):
        path = f"https://api.avrae.io/customizations/gvars/{gvar_id}"
        headers = {"Authorization": self.token}
        r = requests.get(url=path, headers=headers)
        return r.json()

    def check_and_maybe_update_gvar(self, gvar_path, gvar_id):
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
            self.token,
            f"https://api.avrae.io/customizations/gvars/{gvar_id}",
            {"value": file_contents},
        )

    def get_collection_info(self, api_key, collection_id):
        path = f"https://api.avrae.io/workshop/collection/{collection_id}/full"
        headers = {"Authorization": api_key}
        r = requests.get(url=path, headers=headers)
        request_data = r.json()
        if not request_data["success"]:
            raise Exception(
                f"{collection_id} collection data grab did not succeed.\n"
                f"{json.dumps(request_data, indent=2)}"
            )
        return r.json()

    def parse_collection(self, collection_id, parser):
        collection_data = self.get_collection_info(self.token, collection_id)["data"]
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
