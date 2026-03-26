###
# Avrae Auto-Update
# Goals:
# Full Support for previous version
# Full Support for aliases and sub-aliases
# Full support for snippets
# Full support for updating documentation
###

import logging
import sys

from config import Config
from parsing import Parser
from api import Avrae
import utils as utils
from sys import exit

logger = logging.getLogger("main")
parser_logger = logging.getLogger("parser")
api_logger = logging.getLogger("api")


class TopicFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.topic = record.name.rsplit(".", maxsplit=1)[-1].upper()
        return super().format(record)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(TopicFormatter(" - [%(topic)s]: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


def update_collections(avrae: Avrae, parser: Parser, modified_paths: set) -> None:
    api_logger.info("Checking collections...")
    for path, collection_id in parser.collections.items():
        api_logger.info(f"Checking Collection {collection_id} at {path.as_posix()}")
        avrae.parse_collection(collection_id, parser)
        for alias_path, parsed_alias in avrae.alias_outputs[collection_id].items():
            if alias_path in modified_paths:
                avrae.check_and_maybe_update("alias", parsed_alias)
            if parsed_alias.docs_path in modified_paths:
                avrae.check_and_maybe_update_docs("alias", parsed_alias)
        for snippet_path, parsed_snippet in avrae.snippet_outputs[
            collection_id
        ].items():
            if snippet_path in modified_paths:
                avrae.check_and_maybe_update("snippet", parsed_snippet)
            if parsed_snippet.docs_path in modified_paths:
                avrae.check_and_maybe_update_docs("snippet", parsed_snippet)


def run() -> None:
    logger.info("Starting Avrae Auto-Updater!")

    # Step One: Validate our Environment & Load our config
    config = Config()
    config.load_config()

    # Step Two: Find our workspaces & check our modified files.
    logger.info("Parsing modified files.")
    if config.modified_files is None:
        logger.info("No modified files provided. Quitting...")
        exit(1)
    modified_files = utils.parse_paths(config.modified_files)
    if len(modified_files) == 0:
        logger.info("No modified Avrae files detected. Quitting...")
        exit(0)

    logger.info(f"Found {len(modified_files)} relevant modified files.")

    # Step Three: Parse our collections and gvars!
    parser_logger.info("Loading data from configuration files...")
    parser = Parser(config)
    parser.load_collections()
    parser.load_gvars()
    parser.find_connected_files(modified_files)
    if len(parser.connected_files) == 0:
        parser_logger.info(
            "No modified files matched configured collections or GVARs. Quitting..."
        )
        exit(0)

    modified_paths = set(x.path for x in parser.connected_files)
    parser_logger.info("Data loaded.")

    avrae = Avrae(config)
    update_collections(avrae, parser, modified_paths)

    # Step Five: Update GVARs
    api_logger.info("Checking GVARs...")
    for gvar_path, gvar_id in parser.gvars.items():
        if gvar_path in modified_paths:
            avrae.check_and_maybe_update_gvar(gvar_path, gvar_id)


if __name__ == "__main__":
    setup_logging()
    run()
