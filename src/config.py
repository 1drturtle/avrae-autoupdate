import json
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv


class Config:
    def __init__(self):
        self.token: Optional[str] = None
        self.collections_file_path: Optional[str] = None
        self.gvars_file_path: Optional[str] = None
        self.modified_files: Optional[List[str]] = None

    @staticmethod
    def _ensure_file_exists(path_str: str, label: str) -> None:
        path = Path(path_str)
        if not path.is_file():
            raise FileNotFoundError(
                f"{label} file not found at {path.as_posix()}. Please verify your workflow inputs."
            )

    def load_config(self):
        print(" - [CONFIG]: Loading config...")

        # Allow us to be in the correct base path.
        repo_path = os.environ.get("GITHUB_WORKSPACE", None)
        if repo_path:
            os.chdir(repo_path)
            load_dotenv(Path(repo_path) / ".env")
        else:
            load_dotenv(".env")

        # Load Avrae Token
        self.token = os.environ.get("INPUT_AVRAE_TOKEN", None)
        if self.token is None:
            raise Exception(
                "Avrae token not found. Please see README.md in the project repo for help with setup. Exiting..."
            )

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
        self._ensure_file_exists(self.collections_file_path, "Collection map")
        self._ensure_file_exists(self.gvars_file_path, "GVAR map")

        modified_files_raw = os.environ.get("INPUT_MODIFIED_FILES", None)
        if modified_files_raw is None:
            raise Exception("Modified files ENV not found. Exiting...")
        try:
            self.modified_files = json.loads(modified_files_raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Modified files ENV could not be parsed as JSON. Ensure the workflow passes a JSON list."
            ) from exc
        if not isinstance(self.modified_files, list):
            raise ValueError("Modified files ENV must be a JSON list.")
        print(" - [CONFIG]: Config loaded.")
