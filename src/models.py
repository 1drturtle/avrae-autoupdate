from collections import namedtuple

ParsedAlias = namedtuple(
    "ParsedAlias", ["name", "data", "dir_path", "file_path", "docs_path"]
)
ParsedSnippet = namedtuple("ParsedSnippet", ["name", "data", "file_path", "docs_path"])
