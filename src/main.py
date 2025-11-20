###
# Avrae Auto-Update
# Goals:
# Full Support for previous version
# Full Support for aliases and sub-aliases
# Full support for snippets
# Full support for updating documentation
###

from config import Config
from parsing import Parser
from api import Avrae
import utils as utils
from sys import exit
from models import *


if __name__ == "__main__":
    print("Starting Avrae Auto-Updater!")

    # Step One: Validate our Environment & Load our config
    config = Config()
    config.load_config()

    # Step Two: Find our workspaces & check our modified files.
    print(" - [MAIN]: Parsing modified files.")
    if config.modified_files is None:
        print(" - [MAIN]: No modified files provided. Quitting...")
        exit(1)
    modified_files = utils.parse_paths(config.modified_files)
    if len(modified_files) == 0:
        print("No modified Avrae files detected. Quitting...")
        exit(0)

    print(f" - [MAIN]: Found {len(modified_files)} relevant modified files.")

    # Step Three: Parse our collections and gvars!
    print(" - [PARSER]: Loading data from configuration files...")
    parser = Parser(config)
    parser.load_collections()
    parser.load_gvars()
    parser.find_connected_files(modified_files)
    if len(parser.connected_files) == 0:
        print(
            " - [PARSER]: No modified files matched configured collections or GVARs. Quitting..."
        )
        exit(0)

    modified_paths = set(x.path for x in parser.connected_files)
    print(" - [PARSER]: Data loaded.")

    # Step Four: Download Collection Data from Avrae and find relevant files to update

    ## for each path, check to see if file content is up to date
    ## also check for the markdown
    ## if changed, push update and change active version
    ## snippets will reside in the collection directory
    print(" - [API]: Checking collections...")
    avrae = Avrae(config)
    for path, collection_id in parser.collections.items():
        print(f" - [API]: Checking Collection {collection_id} at {path.as_posix()}")
        avrae.parse_collection(collection_id, parser)
        # update aliases
        for alias_path, parsed_alias in avrae.alias_outputs[collection_id].items():
            if alias_path in modified_paths:
                avrae.check_and_maybe_update("alias", parsed_alias)
            if parsed_alias.docs_path in modified_paths:
                avrae.check_and_maybe_update_docs("alias", parsed_alias)
        # update snippets
        for snippet_path, parsed_snippet in avrae.snippet_outputs[
            collection_id
        ].items():
            if snippet_path in modified_paths:
                avrae.check_and_maybe_update("snippet", parsed_snippet)
            if parsed_snippet.docs_path in modified_paths:
                avrae.check_and_maybe_update_docs("snippet", parsed_snippet)

    # Step Five: Update GVARs
    print(" - [API] Checking GVARs...")
    for gvar_path, gvar_id in parser.gvars.items():
        if gvar_path in modified_paths:
            avrae.check_and_maybe_update_gvar(gvar_path, gvar_id)
