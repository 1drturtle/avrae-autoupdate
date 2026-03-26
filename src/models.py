from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ParsedAlias:
    """Local representation of one Avrae alias and its file layout."""

    name: str
    data: dict[str, Any]
    dir_path: Path
    file_path: Path
    docs_path: Path


@dataclass(frozen=True, slots=True)
class ParsedSnippet:
    """Local representation of one Avrae snippet and its file layout."""

    name: str
    data: dict[str, Any]
    file_path: Path
    docs_path: Path
