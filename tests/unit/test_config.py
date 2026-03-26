import json
from pathlib import Path
from unittest.mock import patch

import pytest

from config import Config


def _write_default_maps(base: Path) -> None:
    (base / "collections.json").write_text(json.dumps({"path/to": "id"}))
    (base / "gvars.json").write_text(json.dumps({"path/to.gvar": "gvar-id"}))


def test_ensure_file_exists_accepts_existing_file(tmp_path: Path):
    file_path = tmp_path / "collections.json"
    file_path.write_text("{}")

    Config._ensure_file_exists(str(file_path), "Collection map")


def test_ensure_file_exists_raises_for_missing_file(tmp_path: Path):
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError) as excinfo:
        Config._ensure_file_exists(str(missing_path), "Collection map")

    assert missing_path.as_posix() in str(excinfo.value)


def test_load_config_loads_defaults_and_changes_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_default_maps(tmp_path)
    monkeypatch.setenv("INPUT_AVRAE_TOKEN", "token")
    monkeypatch.setenv("INPUT_MODIFIED_FILES", json.dumps(["collections/path.alias"]))
    monkeypatch.delenv("INPUT_COLLECTIONS_ID_FILE_NAME", raising=False)
    monkeypatch.delenv("INPUT_GVARS_ID_FILE_NAME", raising=False)
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))

    with patch("config.load_dotenv") as mock_load_dotenv:
        config = Config()
        original_cwd = Path.cwd()
        try:
            config.load_config()
        finally:
            monkeypatch.chdir(original_cwd)

    assert config.collections_file_path == "collections.json"
    assert config.gvars_file_path == "gvars.json"
    assert config.modified_files == ["collections/path.alias"]
    mock_load_dotenv.assert_called_once_with(tmp_path / ".env")


def test_load_config_uses_explicit_paths_and_calls_chdir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    collections_path = tmp_path / "collections-map.json"
    gvars_path = tmp_path / "gvars-map.json"
    collections_path.write_text("{}")
    gvars_path.write_text("{}")
    monkeypatch.setenv("INPUT_AVRAE_TOKEN", "token")
    monkeypatch.setenv("INPUT_MODIFIED_FILES", json.dumps([]))
    monkeypatch.setenv("INPUT_COLLECTIONS_ID_FILE_NAME", str(collections_path))
    monkeypatch.setenv("INPUT_GVARS_ID_FILE_NAME", str(gvars_path))
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))

    with patch("config.os.chdir") as mock_chdir, patch("config.load_dotenv") as mock_load_dotenv:
        config = Config()
        config.load_config()

    mock_chdir.assert_called_once_with(str(tmp_path))
    mock_load_dotenv.assert_called_once_with(tmp_path / ".env")
    assert config.collections_file_path == str(collections_path)
    assert config.gvars_file_path == str(gvars_path)


def test_load_config_raises_when_token_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_default_maps(tmp_path)
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("INPUT_MODIFIED_FILES", json.dumps([]))
    monkeypatch.delenv("INPUT_AVRAE_TOKEN", raising=False)

    config = Config()
    original_cwd = Path.cwd()
    with pytest.raises(Exception, match="Avrae token not found"):
        try:
            config.load_config()
        finally:
            monkeypatch.chdir(original_cwd)


def test_load_config_raises_when_modified_files_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_default_maps(tmp_path)
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("INPUT_AVRAE_TOKEN", "token")
    monkeypatch.delenv("INPUT_MODIFIED_FILES", raising=False)

    config = Config()
    original_cwd = Path.cwd()
    with pytest.raises(Exception, match="Modified files ENV not found"):
        try:
            config.load_config()
        finally:
            monkeypatch.chdir(original_cwd)


def test_load_config_raises_when_modified_files_is_invalid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_default_maps(tmp_path)
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("INPUT_AVRAE_TOKEN", "token")
    monkeypatch.setenv("INPUT_MODIFIED_FILES", "not-json")

    config = Config()
    original_cwd = Path.cwd()
    with pytest.raises(ValueError, match="could not be parsed as JSON"):
        try:
            config.load_config()
        finally:
            monkeypatch.chdir(original_cwd)


def test_load_config_raises_when_modified_files_is_not_a_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _write_default_maps(tmp_path)
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("INPUT_AVRAE_TOKEN", "token")
    monkeypatch.setenv("INPUT_MODIFIED_FILES", json.dumps({"path": "value"}))

    config = Config()
    original_cwd = Path.cwd()
    with pytest.raises(ValueError, match="must be a JSON list"):
        try:
            config.load_config()
        finally:
            monkeypatch.chdir(original_cwd)
