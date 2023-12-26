# Class that handles a majority of the file logic
from config import Config
from pathlib import Path
from json import load
from collections import namedtuple

ConnectedFile = namedtuple(
    "ConnectedFile", ["type", "path", "collection", "trimmed_path"]
)


class Parser:
    def __init__(self, config: Config):
        self.config = config
        self.collections = {}
        self.gvars = {}
        self.connected_files: list[ConnectedFile] = []

    def load_collections(self):
        with open(self.config.collections_file_path, "r") as fp:
            collections = load(fp)
        for k, v in collections.items():
            self.collections[Path(k)] = v

    def load_gvars(self):
        with open(self.config.gvars_file_path, "r") as fp:
            gvars = load(fp)
        for k, v in gvars.items():
            self.gvars[Path(k)] = v

    def find_connected_files(self, modified_files):
        connected_files = []
        # first handle aliases, snippets, and docs.
        # next, handle GVARS.
        for file in modified_files:
            file_type = str(file).rsplit(".", 1)[1]
            if str(file).endswith(".gvar"):
                if file in self.gvars.keys():
                    connected_files.append(ConnectedFile("gvar", file, None, None))
                continue
            for path, _id in self.collections.items():
                file_parents = list(file.parents)[
                    :-2
                ]  # we remove the base directory and `.`
                if path in file_parents:
                    # we found our collection for this file.
                    # Let's connect them
                    connected = ConnectedFile(
                        file_type,
                        file,
                        {"id": _id, "path": path},
                        file.relative_to(path),
                    )
                    connected_files.append(connected)
                    break

        self.connected_files = connected_files
