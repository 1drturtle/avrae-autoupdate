from pathlib import Path
from typing import Iterable, List


def is_important_path(path: str) -> bool:
    for ending in (".alias", ".snippet", ".gvar", ".md"):
        if path.endswith(ending):
            return True
    return False


def parse_paths(paths: Iterable[str]) -> List[Path]:
    return [Path(x) for x in paths if is_important_path(x)]
