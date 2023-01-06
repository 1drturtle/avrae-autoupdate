"""
Push changes to Avrae, creating new code versions as needed.
"""

from itertools import chain
import json
import os
from pathlib import Path
import sys

from .avrae import AvraeClient
from .sources import ComparisonResult, DiffableResult, UpdatesAvrae, compare_repository_with_avrae

def push(
    repo_base_path: Path,
    gvar_config_relative_path: Path,
    collections_config_relative_path: Path,
    api_key: str,
    summary_file_path: Path | None = None,
) -> int:
    """
    Update Avrae with any changes in the local repo.
    """

    def apply_repository_changes(comparison_results: list[ComparisonResult], client: AvraeClient):
        """
        From the set of all ComparisonResults apply only those which update avrae.
        """
        sys.stdout.write(f"::debug:: Processing {len(comparison_results)} comparison results.\n")
        for result in comparison_results:
            summary = result.summary()
            if summary_file_path:
                with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
                    summary_file.writelines([
                        f"- {result.relative_path}\n",
                        f"  {summary}\n",
                    ])
            sys.stdout.write(f"::debug::{result.__class__.__name__}: {summary}\n")
            if isinstance(result, UpdatesAvrae):
                if summary_file_path:
                    with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
                        summary_file.writelines([
                            "  ⮤ Updating Avrae.\n",
                        ])
                result.apply(client=client)
            if isinstance(result, DiffableResult):
                diff = result.diff()
                sys.stdout.writelines([
                    f"::group::{summary}\n",
                    diff + '\n',
                    "::endgroup::\n"
                ])
                if summary_file_path:
                    with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
                        indent = '  '
                        summary_file.writelines(chain(
                            [
                                indent + "```\n",
                            ],
                            [(indent + line) for line in diff.splitlines(keepends=True)],
                            [
                                indent + "```\n",
                            ]
                        ))

    # Check for expected config files
    gvar_config_path = (repo_base_path / gvar_config_relative_path)
    if not os.path.exists(gvar_config_path):
        sys.stderr.write(
            f"::error title=Missing gvars config file.::Gvar config not found at " \
            f"{gvar_config_relative_path} create the file or specify a path using the 'gvars' " \
            "workflow input.\n"
        )
        return 1
    with open(gvar_config_path, mode='r', encoding='utf-8') as gvar_config_file:
        gvar_config = json.load(gvar_config_file)

    collections_config_path = (repo_base_path / collections_config_relative_path)
    if not os.path.exists(collections_config_path):
        sys.stderr.write(
            f"::error title=Missing collections config file.::Collections config not found at " \
            f"{collections_config_relative_path} create the file or specify a path using the " \
            "'collections' workflow input.\n"
        )
        return 1
    with open(collections_config_path, mode='r', encoding='utf-8') as collections_config_file:
        collections_config = json.load(collections_config_file)

    client = AvraeClient(api_key=api_key)
    sys.stdout.write("::debug:: Fetching data from Avrae...\n")
    collections = client.get_collections(collection_ids=collections_config.keys())
    gvars = client.get_gvars()
    results = compare_repository_with_avrae(
        collections=collections,
        gvars=gvars,
        gvar_config=gvar_config,
        base_path=repo_base_path
    )
    if summary_file_path:
        with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
            summary_file.writelines([
                "# Pushing to Avrae\n\n",
            ])
    sys.stdout.write(f"::debug:: Processing {len(collections)} collections.\n")
    for collection_result in results['collections']:
        sys.stdout.write("::debug:: Comparing aliases.\n")
        apply_repository_changes(collection_result['aliases'], client=client)
        sys.stdout.write("::debug:: Comparing snippets.\n")
        apply_repository_changes(collection_result['snippets'], client=client)
    sys.stdout.write("::debug:: Comparing gvars.\n")
    apply_repository_changes(results['gvars'], client=client)

    return 0
