"""
Compares local repository source files to avrae API responses objects.
Identifies differences and constructs a set of recommended actions to bring avrae in sync
with the local repository.
"""

from abc import ABC, abstractmethod
from difflib import Differ
from itertools import chain
import os
from pathlib import Path

from .avrae import (
    Alias,
    AvraeClient,
    Collection,
    Gvar,
    Snippet,
)

class ComparisonResult(ABC):
    """
    The result of a comparison between a single resource in the current repository and the avrae API
    each result can report differences between the two locations.
    """

    def __init__(self, path: os.PathLike, base_path: os.PathLike) -> None:
        super().__init__()
        self.path = path
        self.base_path = base_path
        self.relative_path = path.relative_to(base_path)

    @abstractmethod
    def summary(self) -> str:
        """
        Returns a description of the difference between the local repository and avrae API.
        """

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and self.__dict__ == other.__dict__)

class UpdatesAvrae(ABC):
    """
    A comparison result which can be resolved by applying changes to Avrae
    """

    @abstractmethod
    def apply(self, client: AvraeClient):
        """
        Resolves a mismatch between local and avrae state by applying changes to avrae
        """

class UpdatesRepository(ABC):
    """
    A comparison result which can be resolved by applying changes to the local repository
    """

    @abstractmethod
    def apply(self):
        """
        Resolves a mismatch between local and avrae sat by applying changes to the local repository
        """

class DiffableResult(ABC):
    """
    A comparison result able to produce a diff (via Differ) between the local and Avrae versions
    of a resource.
    """

    @abstractmethod
    def diff(self) -> str:
        """
        Returns a string containing the Differ output
        """

# Aliases

class _AliasComparisonResult(ComparisonResult):
    pass

class LocalAliasNotFoundInAvrae(_AliasComparisonResult):
    """
    A .alias file is present in the collection directory
    but was not found in the matching avrae collection.
    """

    def summary(self) -> str:
        return f"Alias {self.relative_path} does not exist in Avrae."


class _AliasComparisonResultWithAlias(_AliasComparisonResult):
    def __init__(self, path: os.PathLike, base_path: os.PathLike, alias: Alias) -> None:
        super().__init__(path=path, base_path=base_path)
        self.alias = alias


class LocalAliasMatchesAvrae(_AliasComparisonResultWithAlias):
    """
    The local .alias file matches the current active version code in the avrae collection.
    """

    def summary(self) -> str:
        return f"Alias {self.relative_path} matches Avrae."

class LocalAliasDocsMatchAvrae(_AliasComparisonResultWithAlias):
    """
    The local doc markdown file matches the current docs for the alias in the avrae collection.
    """

    def summary(self) -> str:
        return f"Alias docs file {self.relative_path} matches Avrae."


class LocalAliasMissing(_AliasComparisonResultWithAlias, UpdatesRepository):
    """
    An alias was found in the avrae collection which has no corresponding .alias file
    in the repository at its expected location.
    """

    def summary(self) -> str:
        return f"Alias {self.alias.name}({self.alias.id}) has no matching .alias file at " \
            f"{self.relative_path}."

    def apply(self):
        Path(os.path.dirname(self.path)).mkdir(parents=True, exist_ok=True)
        with open(self.path, mode='w', encoding='utf-8') as alias_file:
            alias_file.write(self.alias.code)

class LocalAliasDocsMissing(_AliasComparisonResultWithAlias, UpdatesRepository):
    """
    No corresponding markdown file was found for the alias.
    """

    def summary(self) -> str:
        return f"Alias {self.alias.name}({self.alias.id}) has no matching .md file at " \
            f"{self.relative_path}."

    def apply(self):
        Path(os.path.dirname(self.path)).mkdir(parents=True, exist_ok=True)
        with open(self.path, mode='w', encoding='utf-8') as alias_file:
            alias_file.write(self.alias.docs)


class LocalAliasDoesNotMatchAvrae(_AliasComparisonResultWithAlias, UpdatesAvrae, DiffableResult):
    """
    The local .alias file contains code which does not match the active version on avrae.
    """

    def summary(self) -> str:
        return f"{self.relative_path} does not match the active version of " \
                f"{self.alias.name}({self.alias.id})"

    def diff(self) -> str:
        differ = Differ()
        with open(self.path, mode='r', encoding='utf-8') as alias_file:
            diff = differ.compare(
                self.alias.code.splitlines(keepends=True),
                alias_file.readlines()
            )
            return '\n'.join(diff)

    def apply(self, client: AvraeClient):
        with open(self.path, mode='r', encoding='utf-8') as alias_file:
            code = alias_file.read()
            matching_version = client.recent_matching_version(item=self.alias, code=code)
            if not matching_version:
                new_version = client.create_new_code_version(
                    item=self.alias,
                    code=code
                )
                client.set_active_code_version(item=self.alias, version=new_version.version)

class LocalAliasDocsDoNotMatchAvrae(_AliasComparisonResultWithAlias, UpdatesAvrae, DiffableResult):
    """
    The local doc markdown file does not match the current docs in the avrae collection.
    """

    def summary(self) -> str:
        return f"{self.relative_path} does not match the current docs for " \
            f"{self.alias.name}({self.alias.id})"

    def diff(self) -> str:
        differ = Differ()
        with open(self.path, mode='r', encoding='utf-8') as docs_file:
            diff = differ.compare(
                self.alias.docs.splitlines(keepends=True),
                docs_file.readlines()
            )
            return '\n'.join(diff)

    def apply(self, client: AvraeClient):
        with open(self.path, mode='r', encoding='utf-8') as docs_file:
            client.update_docs(item=self.alias, yaml=docs_file.read())


# Snippets

class _SnippetComparisonResult(ComparisonResult):
    pass

class LocalSnippetNotFoundInAvrae(_SnippetComparisonResult):
    """
    A .snippet file is present in the collection directory
    but wad not found in the matching avrae collection.
    """

    def summary(self) -> str:
        return f"Snippet {self.relative_path} does not exist in Avrae."


class _SnippetComparisonResultWithSnippet(_SnippetComparisonResult):
    def __init__(
        self,
        path: os.PathLike,
        base_path: os.PathLike,
        snippet: Snippet
    ) -> None:
        super().__init__(path=path, base_path=base_path)
        self.snippet = snippet


class LocalSnippetMatchesAvrae(_SnippetComparisonResultWithSnippet):
    """
    The local .snippet file matches the current active version code in the avrae collection.
    """

    def summary(self) -> str:
        return f"Snippet {self.relative_path} matches Avrae."


class LocalSnippetDocsMatchAvrae(_SnippetComparisonResultWithSnippet):
    """
    The local doc markdown file matches the current docs for the snippet in the avrae collection.
    """

    def summary(self) -> str:
        return f"Snippet docs file {self.relative_path} matches Avrae."


class LocalSnippetMissing(_SnippetComparisonResultWithSnippet, UpdatesRepository):
    """
    A snippet was found in the avrae collection which has no corresponding .snippet file
    in the repository at its expected location.
    """

    def summary(self) -> str:
        return f"Snippet {self.snippet.name}({self.snippet.id}) has no matching .snippet file " \
            f"at {self.relative_path}."

    def apply(self):
        Path(os.path.dirname(self.path)).mkdir(parents=True, exist_ok=True)
        with open(self.path, mode='w', encoding='utf-8') as snippet_file:
            snippet_file.write(self.snippet.code)

class LocalSnippetDocsMissing(_SnippetComparisonResultWithSnippet, UpdatesRepository):
    """
    No corresponding markdown file was found for the alias.
    """

    def summary(self) -> str:
        return f"Snippet {self.snippet.name}({self.snippet.id}) has no matching .md file " \
            f"at {self.relative_path}."

    def apply(self):
        Path(os.path.dirname(self.path)).mkdir(parents=True, exist_ok=True)
        with open(self.path, mode='w', encoding='utf-8') as snippet_file:
            snippet_file.write(self.snippet.docs)


class LocalSnippetDoesNotMatchAvrae(
    _SnippetComparisonResultWithSnippet,
    UpdatesAvrae,
    DiffableResult
):
    """
    The local .snippet file contains code which does not match the active version on avrae.
    """

    def summary(self) -> str:
        return f"{self.relative_path} does not match the active version of " \
            f"{self.snippet.name}({self.snippet.id})"

    def diff(self) -> str:
        differ = Differ()
        with open(self.path, mode='r', encoding='utf-8') as snippet_file:
            diff = differ.compare(
                self.snippet.code.splitlines(keepends=True),
                snippet_file.readlines()
            )
            return '\n'.join(diff)

    def apply(self, client: AvraeClient):
        with open(self.path, mode='r', encoding='utf-8') as snippet_file:
            code = snippet_file.read()
            matching_version = client.recent_matching_version(item=self.snippet, code=code)
            if not matching_version:
                new_version = client.create_new_code_version(
                    item=self.snippet,
                    code=code
                )
                client.set_active_code_version(item=self.snippet, version=new_version.version)

class LocalSnippetDocsDoNotMatchAvrae(
    _SnippetComparisonResultWithSnippet,
    UpdatesAvrae,
    DiffableResult
):
    """
    The local doc markdown file does not match the current docs in the avrae collection.
    """

    def summary(self) -> str:
        return f"{self.relative_path} does not match the current docs for " \
            f"{self.snippet.name}({self.snippet.id})"

    def diff(self) -> str:
        differ = Differ()
        with open(self.path, mode='r', encoding='utf-8') as docs_file:
            diff = differ.compare(
                self.snippet.docs.splitlines(keepends=True),
                docs_file.readlines()
            )
            return '\n'.join(diff)

    def apply(self, client: AvraeClient):
        with open(self.path, mode='r', encoding='utf-8') as docs_file:
            client.update_docs(item=self.snippet, yaml=docs_file.read())

# GVars

class _GvarComparisonResult(ComparisonResult):
    pass

class LocalGvarNotFoundInAvrae(_GvarComparisonResult):
    """
    A .gvar file is present in the configuration
    but wad not found in the matching avrae collection.
    """

    def summary(self) -> str:
        return f"Gvar {self.relative_path} is not mapped to an existing gvar in Avrae."


class _GvarComparisonResultWithGvar(_GvarComparisonResult):
    def __init__(self, path: os.PathLike, base_path: os.PathLike, gvar: Gvar) -> None:
        super().__init__(path=path, base_path=base_path)
        self.gvar = gvar


class LocalGvarMatchesAvrae(_GvarComparisonResultWithGvar):
    """
    The local .gvar file contents match the gvar in the avrae collection.
    """

    def summary(self) -> str:
        return f"Gvar {self.relative_path} matches {self.gvar.key} in Avrae."


class LocalGvarMissing(_GvarComparisonResultWithGvar, UpdatesRepository):
    """
    A .gvar file is present in the configuration and avrae
    but was not found on disk at the expected location.
    """

    def summary(self) -> str:
        return f"Gvar {self.gvar.key} has no matching .gvar file at " \
            f"{self.relative_path}"

    def apply(self):
        Path(os.path.dirname(self.path)).mkdir(parents=True, exist_ok=True)
        with open(self.path, mode='w', encoding='utf-8') as gvar_file:
            gvar_file.write(self.gvar.value)

class LocalGvarDoesNotMatchAvrae(_GvarComparisonResultWithGvar, UpdatesAvrae, DiffableResult):
    """
    The local .gvar file contents do not match the gvar in the avrae collection.
    """

    def summary(self) -> str:
        return f"{self.relative_path} does not match {self.gvar.key} in Avrae."

    def diff(self) -> str:
        differ = Differ()
        with open(self.path, mode='r', encoding='utf-8') as gvar_file:
            diff = differ.compare(
                self.gvar.value.splitlines(keepends=True),
                gvar_file.readlines()
            )
            return '\n'.join(diff)

    def apply(self, client: AvraeClient):
        with open(self.path, mode='r', encoding='utf-8') as gvar_file:
            client.update_gvar(gvar=self.gvar, value=gvar_file.read())

def _compare_aliases(
    collection: Collection,
    base_path: os.PathLike
) -> list[_AliasComparisonResult]:
    """
    Generate AliasComparisonResults for the given Collection
    """
    def build_alias_map(path_segments: list, alias: Alias) -> dict[str: Alias]:
        alias_map = {}
        file_name = alias.name
        alias_map[os.path.join(*path_segments, alias.name, file_name)] = alias
        for subalias in alias.subcommands or []:
            alias_map.update(build_alias_map(
                path_segments + [alias.name], subalias))
        return alias_map

    def build_alias_comparison(
        alias_base_file_path: str,
        alias: Alias
    ) -> list[_AliasComparisonResult]:
        results: list[_AliasComparisonResult] = []

        # Check the alias code
        alias_file_path = alias_base_file_path + '.alias'
        if not os.path.exists(alias_file_path):
            results.append(LocalAliasMissing(
                path=Path(alias_file_path),
                base_path=base_path,
                alias=alias
            ))
        else:
            with open(alias_file_path, mode='r', encoding='utf-8') as alias_file:
                local_code = alias_file.read()
                if local_code == alias.code:
                    results.append(LocalAliasMatchesAvrae(
                        path=Path(alias_file_path),
                        base_path=base_path,
                        alias=alias
                    ))
                else:
                    results.append(LocalAliasDoesNotMatchAvrae(
                        path=Path(alias_file_path),
                        base_path=base_path,
                        alias=alias
                    ))

        # Check the alias docs
        valid_doc_files = [
            alias_base_file_path + '.md',
            alias_base_file_path + '.markdown',
            alias_base_file_path + '.MARKDOWN'
        ]
        alias_doc_path = next(filter(os.path.exists, valid_doc_files), None)
        if not alias_doc_path:
            results.append(LocalAliasDocsMissing(
                path=Path(valid_doc_files[0]),
                base_path=base_path,
                alias=alias
            ))
        else:
            with open(alias_doc_path, mode='r', encoding='utf-8') as doc_file:
                local_docs = doc_file.read()
                if local_docs == alias.docs:
                    results.append(LocalAliasDocsMatchAvrae(
                        path=Path(alias_doc_path),
                        base_path=base_path,
                        alias=alias
                    ))
                else:
                    results.append(LocalAliasDocsDoNotMatchAvrae(
                        path=Path(alias_doc_path),
                        base_path=base_path,
                        alias=alias
                    ))

        return results

    def find_aliases(base_path: os.PathLike) -> list[os.PathLike]:
        found_aliases = []
        for dirpath, _, filenames in os.walk(base_path):
            shared = os.path.commonprefix([dirpath, base_path])
            dirname = os.path.relpath(dirpath, shared)
            found_aliases += [os.path.join(dirname, filename)
                              for filename in filenames if filename.endswith('.alias')]
        return found_aliases

    path_segments = [base_path, collection.name]
    aliases_map: dict[str, Alias] = {}
    # Build a map of file base paths to existing avrae aliases
    for alias in collection.aliases or []:
        aliases_map.update(build_alias_map(path_segments, alias))
    # Compare local sources to the avrae aliases
    comparison_results = list(
        chain(*[
            build_alias_comparison(alias_path, alias) for (alias_path, alias) in aliases_map.items()
            ])
    )

    # Find all '.alias' files in the current collection in the local filesystem
    local_aliases = find_aliases(base_path=os.path.join(*path_segments))
    full_local_aliases = (
        os.path.join(*path_segments, local_alias) for local_alias in local_aliases
    )
    # Build a list of expected '.alias' files from the avrae collection
    avrae_alias_files = [alias + '.alias' for alias in aliases_map]
    # Report any local aliases not known to avrae
    for alias in full_local_aliases:
        if not alias in avrae_alias_files:
            comparison_results.append(LocalAliasNotFoundInAvrae(
                path=Path(alias),
                base_path=base_path,
            ))

    return comparison_results


def _compare_snippets(
    collection: Collection,
    base_path: os.PathLike
) -> list[_SnippetComparisonResult]:
    """
    Generate SnippetComparisonResults for the given Collection
    """
    def build_snippet_comparison(
        snippet_base_file_path: str,
        snippet: Snippet
    ) -> list[_SnippetComparisonResult]:
        results: list[_SnippetComparisonResult] = []

        # Check snippet code
        snippet_path = snippet_base_file_path + '.snippet'
        if not os.path.exists(snippet_path):
            results.append(LocalSnippetMissing(
                path=Path(snippet_path),
                base_path=base_path,
                snippet=snippet
            ))
        else:
            with open(snippet_path, mode='r', encoding='utf-8') as snippet_file:
                local_code = snippet_file.read()
                if local_code == snippet.code:
                    results.append(LocalSnippetMatchesAvrae(
                        path=Path(snippet_path),
                        base_path=base_path,
                        snippet=snippet
                    ))
                else:
                    results.append(LocalSnippetDoesNotMatchAvrae(
                        path=Path(snippet_path),
                        base_path=base_path,
                        snippet=snippet
                    ))

        # Check snippet docs
        valid_doc_files = [
            snippet_base_file_path + '.md',
            snippet_base_file_path + '.markdown',
            snippet_base_file_path + '.MARKDOWN'
        ]
        snippet_doc_path = next(filter(os.path.exists, valid_doc_files), None)
        if not snippet_doc_path:
            results.append(LocalSnippetDocsMissing(
                path=Path(valid_doc_files[0]),
                base_path=base_path,
                snippet=snippet
            ))
        else:
            with open(snippet_doc_path, mode='r', encoding='utf-8') as doc_file:
                local_docs = doc_file.read()
                if local_docs == snippet.docs:
                    results.append(LocalSnippetDocsMatchAvrae(
                        path=Path(snippet_doc_path),
                        base_path=base_path,
                        snippet=snippet
                    ))
                else:
                    results.append(LocalSnippetDocsDoNotMatchAvrae(
                        path=Path(snippet_doc_path),
                        base_path=base_path,
                        snippet=snippet
                    ))

        return results

    def find_snippets(base_path: os.PathLike) -> list[os.PathLike]:
        found_snippets = []
        for dirpath, _, filenames in os.walk(base_path):
            shared = os.path.commonprefix([dirpath, base_path])
            dirname = os.path.relpath(dirpath, shared)
            found_snippets += [os.path.join(dirname, filename)
                               for filename in filenames if filename.endswith('.snippet')]
        return found_snippets

    # Build a map of file base paths to existing avrae snippets
    snippets_directory = (base_path / collection.name / 'snippets')
    snippet_base_file_paths = (
        (os.path.join(snippets_directory, snippet.name), snippet) for snippet in collection.snippets
    )
    snippets_map = {snippet_path: snippet for (snippet_path, snippet) in snippet_base_file_paths}
    # Compare local sources to the avrae snippets
    comparision_results = list(
        chain(*[
            build_snippet_comparison(snippet_path, snippet) \
                for (snippet_path, snippet) in snippets_map.items()
            ]
        )
    )

    # Find all '.snippet' files in the current collection in the local filesystem
    local_snippets = find_snippets(base_path=snippets_directory)
    full_local_snippets = (
        os.path.normpath(os.path.join(snippets_directory, local_snippet)) \
            for local_snippet in local_snippets
    )
    # Build a list of expected '.snippet' files from the avrae collection
    avrae_snippet_files = [snippet + '.snippet' for snippet in snippets_map]
    # Report any local aliases not known to avrae
    for snippet in full_local_snippets:
        if not snippet in avrae_snippet_files:
            comparision_results.append(LocalSnippetNotFoundInAvrae(
                path=Path(snippet),
                base_path=base_path
            ))

    return comparision_results


def _compare_gvars(
    gvars: list[Gvar],
    config: dict[str: os.PathLike],
    base_path: os.PathLike
) -> list[_GvarComparisonResult]:
    """
    Generate GvarComparisonResults for defined Gvars

    Returns results for any gvar defined in the gvars config file,
    does not report gvars found on avrae but not present in the repo as multiple repos may be used
    to update a single avrae account so we cannot assume that all visible gvars should be included.
    """
    def build_gvar_comparison(gvar_key: str, gvar_path: os.PathLike):
        gvar: Gvar | None = next(
            filter(lambda gvar: gvar.key == gvar_key, gvars), None)
        if not gvar:
            return LocalGvarNotFoundInAvrae(
                path=Path(gvar_path),
                base_path=base_path
            )
        elif not os.path.exists(gvar_path):
            return LocalGvarMissing(
                path=Path(gvar_path),
                base_path=base_path,
                gvar=gvar
            )
        else:
            with open(gvar_path, mode='r', encoding='utf-8') as gvar_file:
                local_code = gvar_file.read()
                if local_code == gvar.value:
                    return LocalGvarMatchesAvrae(
                        path=Path(gvar_path),
                        base_path=base_path,
                        gvar=gvar
                    )
                else:
                    return LocalGvarDoesNotMatchAvrae(
                        path=Path(gvar_path),
                        base_path=base_path,
                        gvar=gvar
                    )

    gvars_map = ((gvar_key, (base_path / relative_path))
                 for (gvar_key, relative_path) in config.items())
    return [build_gvar_comparison(gvar_key, gvar_path) for (gvar_key, gvar_path) in gvars_map]


def compare_repository_collection_with_avrae(collection: Collection, base_path: os.PathLike):
    """
    Compare a single Collection with the source files in the repository.
    """
    return {
        'aliases': _compare_aliases(collection=collection, base_path=base_path),
        'snippets': _compare_snippets(collection=collection, base_path=base_path),
    }


def compare_repository_with_avrae(
    collections: list[Collection],
    gvars: list[Gvar],
    gvar_config: dict[str: os.PathLike],
    base_path: os.PathLike
):
    """
    Compare all Collections and Gvars with the local repository
    """
    collection_results = [compare_repository_collection_with_avrae(
        collection=collection, base_path=base_path) for collection in collections]
    return {
        'collections': collection_results,
        'gvars': _compare_gvars(gvars=gvars, config=gvar_config, base_path=base_path)
    }
