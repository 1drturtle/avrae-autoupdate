from pathlib import Path


def is_important_path(path: str):
    for ending in (".alias", ".snippet", ".gvar", ".md"):
        if path.endswith(ending):
            return True
    return False


def parse_paths(paths: list[str]) -> list[Path]:
    return [Path(x) for x in paths if is_important_path(x)]
