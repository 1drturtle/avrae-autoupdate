import os
import json

from dotenv import load_dotenv


class Config:
    def __init__(self):
        self.token = None
        self.collections_file_path = None
        self.gvars_file_path = None
        self.modified_files = None

    def load_config(self):
        load_dotenv("../.env")
        print(" - [CONFIG]: Loading config...")

        # Allow us to be in the correct base path.
        repo_path = os.environ.get("GITHUB_WORKSPACE", None)
        if repo_path:
            os.chdir(repo_path)

        # Load Avrae Token
        self.token = os.environ.get("INPUT_AVRAE_TOKEN", None)
        if self.token is None:
            raise Exception("Avrae token not found. Exiting...")

        print(" - [CONFIG]: Loading file paths...")
        self.collections_file_path = os.environ.get(
            "INPUT_COLLECTIONS_ID_FILE_NAME", None
        )
        if self.collections_file_path is None:
            print(
                " - [CONFIG]: Warning: Collection file path not set. Defaulting to collections.json"
            )
            self.collections_file_path = "collections.json"
        self.gvars_file_path = os.environ.get("INPUT_GVARS_ID_FILE_NAME", None)
        if self.gvars_file_path is None:
            print(
                " - [CONFIG]: Warning: GVAR file path not set. Defaulting to gvars.json"
            )
            self.gvars_file_path = "gvars.json"
        self.modified_files = os.environ.get("INPUT_MODIFIED_FILES", None)
        if self.modified_files is None:
            raise Exception("Modified files ENV not found. Exiting...")
        self.modified_files = json.loads(self.modified_files)
        print(" - [CONFIG]: Config loaded.")
