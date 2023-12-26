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
import utils as utils
from sys import exit

if __name__ == "__main__":
    print("Starting Avrae Auto-Updater.")

    # Step One: Validate our Environment & Load our config
    config = Config()
    config.load_config()

    # Step Two: Find our workspaces & check our modified files.
    print("Parsing modified files.")
    modified_files = utils.parse_paths(config.modified_files)
    if len(modified_files) == 0:
        print("No modified files detected. Quitting...")
        exit(0)

    # Step Three: Parse our collections and gvars!
    parser = Parser(config)
    parser.load_collections()
    parser.load_gvars()
    parser.find_connected_files(modified_files)

    # Step Four: Download Collection Data from Avrae and find relevant files to update
