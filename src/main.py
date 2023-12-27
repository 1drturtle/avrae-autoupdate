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

if __name__ == "__main__":
    print("Starting Avrae Auto-Updater!")

    # Step One: Validate our Environment & Load our config
    config = Config()
    config.load_config()

    # Step Two: Find our workspaces & check our modified files.
    print(" - [MAIN]: Parsing modified files.")
    modified_files = utils.parse_paths(config.modified_files)
    if len(modified_files) == 0:
        print("No modified files detected. Quitting...")
        exit(0)

    # Step Three: Parse our collections and gvars!
    print(" - [PARSER]: Loading data from configuration files...")
    parser = Parser(config)
    parser.load_collections()
    parser.load_gvars()
    parser.find_connected_files(modified_files)
    print(" - [PARSER]: Data loaded.")

    # Step Four: Download Collection Data from Avrae and find relevant files to update

    ## download full collection data
    ## parse alias/sub-alias recursively to create paths >Done
    ## for each path, check to see if file content is up to date
    ## if changed, push update and change active version
    ## snippets will reside in the collection directory
    avrae = Avrae(config)
    # TODO: removing testing
    avrae.parse_collection("5fa19a9814a62cb7e811c5c4", parser)
    online_paths = set(avrae.alias_outputs["5fa19a9814a62cb7e811c5c4"].keys())
    modified_paths = set(x.path for x in parser.connected_files)
    online_and_modified = list(online_paths & modified_paths)
    print(avrae.alias_outputs["5fa19a9814a62cb7e811c5c4"][online_and_modified[0]])

    # Step Five: Update GVARs
