"""
Pull available collections and gvars from Avrae, creating config files for this repo.
"""

import json
import os
from pathlib import Path
import sys

from autoupdate.avrae import AvraeClient

def initialize(
    repo_base_path: Path,
    gvar_config_relative_path: Path,
    collections_config_relative_path: Path,
    api_key: str,
    summary_file_path: Path | None = None,
) -> int:
    """
    Generate config files containing all available collections and gvars in Avrae.
    """

    # Load existing config files
    gvar_config_path = (repo_base_path / gvar_config_relative_path)
    if not os.path.exists(gvar_config_path):
        gvar_config = {}
    else:
        with open(gvar_config_path, mode='r', encoding='utf-8') as gvar_config_file:
            gvar_config = json.load(gvar_config_file)

    collections_config_path = (repo_base_path / collections_config_relative_path)
    if not os.path.exists(collections_config_path):
        collections_config = {}
    else:
        with open(collections_config_path, mode='r', encoding='utf-8') as collections_config_file:
            collections_config = json.load(collections_config_file)

    # Fetch data from Avrae
    client = AvraeClient(api_key=api_key)
    sys.stdout.write("::debug:: Fetching data from Avrae...\n")
    collection_ids = client.get_editable_collection_ids() + client.get_owned_collection_ids()
    collections = client.get_collections(collection_ids=collection_ids)
    gvars = client.get_gvars()

    if summary_file_path:
        with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
            summary_file.writelines([
                "# Initializing config files\n\n",
            ])

    # Update collections

    for collection_id, relative_path in collections_config.items():
        if not collection_id in collection_ids:
            sys.stdout.write(
                f"::debug:: Collection {collection_id}({relative_path}) not found in Avrae."
            )
            if summary_file_path:
                with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
                    summary_file.writelines([
                        f"- Collection {collection_id}({relative_path}) did not appear in Avrae " \
                            "responses.\n",
                    ])

    for collection in collections:
        if not collection.id in collections_config:
            sys.stdout.write(f"::debug:: Adding collection {collection.name}({collection.id}).\n")
            collections_config[collection.id] = collection.name
        else:
            sys.stdout.write(
                f"::debug:: Skipping collection {collection.name}({collection.id}), " \
                "already in config file.\n"
            )
    with open(collections_config_path, mode='w', encoding='utf-8') as collections_config_file:
        json.dump(collections_config, fp=collections_config_file, indent=2, sort_keys=True)

    # Update gvars

    gvar_keys = [gvar.key for gvar in gvars]
    for gvar_key, relative_path in gvar_config.items():
        if not gvar_key in gvar_keys:
            sys.stdout.write(
                f"::debug:: Gvar {gvar_key}({relative_path}) not found in Avrae."
            )
            if summary_file_path:
                with open(summary_file_path, 'a', encoding='utf-8') as summary_file:
                    summary_file.writelines([
                        f"- Gvar {gvar_key}({relative_path}) did not appear in Avrae responses.\n",
                    ])

    for gvar in gvars:
        if not gvar.key in gvar_config:
            sys.stdout.write(f"::debug:: Adding gvar {gvar.key}.\n")
            gvar_config[gvar.key] = f"gvars/{gvar.key}.gvar"
        else:
            sys.stdout.write(f"::debug:: Skipping gvar {gvar.key}, already in config file.\n")
    with open(gvar_config_path, mode='w', encoding='utf-8') as gvar_config_file:
        json.dump(gvar_config, fp=gvar_config_file, indent=2, sort_keys=True)

    return 0
