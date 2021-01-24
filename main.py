import os
import json


class MissingArgument(BaseException):
    pass


def contains_ending(files, endings):
    return any([file.endswith(endings) for file in files])


def scan_directories(scan_path: str = None, collections={}):
    cwd = scan_path or os.getcwd()
    active_dirs = []
    for dirpath, dirnames, filenames in os.walk(cwd):
        if not contains_ending(filenames, ('alias', 'snippet', 'gvar')):
            continue
        shared = os.path.commonprefix([dirpath, cwd])
        dirname = dirpath.lstrip(shared).replace('\\', '/')
        if dirname in collections:
            active_dirs.append(dirpath.lstrip(shared))
    return active_dirs


if __name__ == '__main__':

    # Collect Environmental Variables
    collection_ids_file = os.environ.get('INPUT_COLLECTION_IDS_FILE_NAME')
    with open(collection_ids_file) as f:
        collection_ids = json.loads(f.read())
    repo_path = os.environ.get('GITHUB_WORKSPACE', None)
    AVRAE_TOKEN = os.getenv('INPUT_AVRAE-TOKEN', None)
    modified_files_list = json.loads(os.getenv('INPUT_MODIFIED-FILES', '[]'))

    # Let's exit if we don't have a token.
    if AVRAE_TOKEN is None:
        raise MissingArgument('No Avrae Token Found.')

    active_directories = scan_directories(repo_path, collection_ids)
