import json
import os
from pathlib import Path

import pytest

from config import Config


def _write_default_maps(base: Path):
    (base / "collections.json").write_text(json.dumps({"path/to": "id"}))
    (base / "gvars.json").write_text(json.dumps({"path/to.gvar": "gvar-id"}))


def test_config_loads_defaults_and_changes_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_default_maps(tmp_path)
    monkeypatch.setenv("INPUT_AVRAE_TOKEN", "token")
    monkeypatch.setenv("INPUT_MODIFIED_FILES", json.dumps(["collections/path.alias"]))
    monkeypatch.delenv("INPUT_COLLECTIONS_ID_FILE_NAME", raising=False)
    monkeypatch.delenv("INPUT_GVARS_ID_FILE_NAME", raising=False)
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))

    original_cwd = os.getcwd()
    try:
        config = Config()
        config.load_config()
    finally:
        os.chdir(original_cwd)

    assert config.collections_file_path == "collections.json"
    assert config.gvars_file_path == "gvars.json"
    assert config.modified_files == ["collections/path.alias"]
    assert (tmp_path / config.collections_file_path).is_file()


def test_config_requires_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_default_maps(tmp_path)
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("INPUT_MODIFIED_FILES", json.dumps([]))
    monkeypatch.delenv("INPUT_AVRAE_TOKEN", raising=False)

    config = Config()
    original_cwd = os.getcwd()
    with pytest.raises(Exception):
        try:
            config.load_config()
        finally:
            os.chdir(original_cwd)


def test_config_rejects_bad_modified_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_default_maps(tmp_path)
    monkeypatch.setenv("INPUT_AVRAE_TOKEN", "token")
    monkeypatch.setenv("INPUT_MODIFIED_FILES", "not-json")
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))

    config = Config()
    original_cwd = os.getcwd()
    with pytest.raises(ValueError):
        try:
            config.load_config()
        finally:
            os.chdir(original_cwd)
