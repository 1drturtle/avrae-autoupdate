####
# Avrae API Handler
###

import requests
import json
from pathlib import Path
from collections import namedtuple

ParsedAlias = namedtuple("ParsedAlias", ["name", "data", "dir_path", "file_path"])


class Avrae:
    def __init__(self, config):
        self.token = config.token
        self.path_maps = {}  # {collection_id: PathMap} PathMap: {alias_id: Path}
        self.alias_outputs = {}
        self.snippet_outputs = {}
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

    def get_collection_info(self, api_key, collection_id):
        path = f"https://api.avrae.io/workshop/collection/{collection_id}/full"
        headers = {"Authorization": api_key}
        r = requests.get(url=path, headers=headers)
        request_data = r.json()
        if not request_data["success"]:
            raise Exception(
                f"{collection_id} collection data grab did not succeed.\n"
                f"{json.dumps(request_data, indent=4)}"
            )
        return r.json()

    def parse_collection(self, collection_id, parser):
        collection_data = self.get_collection_info(self.token, collection_id)["data"]
        self.alias_outputs[collection_id] = {}
        self.snippet_outputs[collection_id] = {}
        for alias in collection_data["aliases"]:
            self.parse_alias(alias, parser)
        for snippet in collection_data["snippets"]:
            # TODO: Snippets

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
        )
        self.alias_outputs[collection_id][parsed_alias.file_path] = parsed_alias
        # handle sub-aliases
        for subalias in alias_data["subcommands"]:
            self.parse_alias(subalias, parser)
