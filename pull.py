"""
Script to run pull
"""

import os
from pathlib import Path
import sys

from autoupdate.pull import pull

if __name__ == '__main__':
    # The repository checkout path
    repo_base_path = Path(os.getenv('GITHUB_WORKSPACE'))
    # Config paths, relative to repo_base_path
    gvar_config_path = Path(os.getenv('GVARS_CONFIG'))
    collections_config_path = Path(os.getenv('COLLECTIONS_CONFIG'))
    # The Avrae API token
    api_key=os.getenv('AVRAE_TOKEN')

    summary_path=Path(os.getenv('GITHUB_STEP_SUMMARY'))

    sys.exit(pull(
        repo_base_path=repo_base_path,
        gvar_config_relative_path=gvar_config_path,
        collections_config_relative_path=collections_config_path,
        api_key=api_key,
        summary_file_path=summary_path
    ))
