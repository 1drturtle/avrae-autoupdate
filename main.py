import collections
import json
import os
import pathlib

import requests


class MissingArgument(BaseException):
    pass


class RequestError(BaseException):
    pass

# utility functions


def contains_ending(files, endings):
    return any([file.endswith(endings) for file in files])


def scan_directories(scan_path: str = None, collections={}):
    cwd = scan_path or os.getcwd()
    active_dirs = []
    for dirpath, dirnames, filenames in os.walk(cwd):
        if not contains_ending(filenames, ('alias', 'snippet', 'gvar')):
            continue
        shared = os.path.commonprefix([dirpath, cwd])
        if (dirname := dirpath.lstrip(shared).replace('\\', '/')) in collections:
            active_dirs.append(dirname)
    return active_dirs


def files_in_actives(scan_path, modified):
    cwd = scan_path or os.getcwd()
    active_files = []
    for dirpath, dirnames, filenames in os.walk(cwd):
        for file in filenames:
            shared = os.path.commonprefix([cwd, dirpath])
            relative = os.path.join(os.path.relpath(dirpath, cwd), file)
            if '\\' in relative:
                relative = pathlib.PureWindowsPath(relative)
            else:
                relative = pathlib.PurePosixPath(relative)
            if (path := relative.as_posix()) in modified:
                active_files.append(path)
    return active_files


# take a collection's data and path
# and construct file paths based on
# alias name + parent names as folders
# if it's a base alias, there is an alias in it's own folder
# alias with sub-aliases in folder, alias with no sub-aliases by itself

ConstructedPath = collections.namedtuple('ConstructedPath', ['obj_name', 'rel_path', 'id', 'type', 'content'])


def construct_file_paths(collection_data, collection_path):
    logged_parents = {}
    file_paths = set()

    def parse_obj(obj_data, suffix='.alias', own_folder=True):
        folder_name = obj_data['name'].lower()
        obj_name = folder_name + suffix
        curpath, to_log = None, None
        try:
            pid = obj_data['parent_id']
        except KeyError:
            pid = None
        if pid:
            to_log = os.path.join(logged_parents[obj_data['parent_id']], folder_name)
            curpath = os.path.join(logged_parents[obj_data['parent_id']], obj_name)
        else:
            to_log = os.path.join(collection_path, folder_name)
            if own_folder:
                curpath = os.path.join(to_log, obj_name)
            else:
                curpath = os.path.join(collection_path, obj_name)

        if '\\' in curpath:
            curpath = pathlib.PureWindowsPath(curpath)
        else:
            curpath = pathlib.PurePosixPath(curpath)
        curpath = curpath.as_posix()

        logged_parents[obj_data['_id']] = to_log
        constructed = ConstructedPath(folder_name, curpath,
                                      obj_data['_id'], suffix.strip('.'), content=obj_data['code'])
        file_paths.add(constructed)
        try:
            for subalias in obj_data['subcommands']:
                parse_obj(subalias)
        except KeyError:
            pass

    for alias in collection_data['aliases']:
        parse_obj(alias)
    for snippet in collection_data['snippets']:
        parse_obj(snippet, '.snippet', own_folder=False)

    return file_paths


# Requests

def post_request(api_key, path, data):
    headers = {
        'Authorization': api_key
    }
    r = requests.post(
        url=path,
        headers=headers,
        json=data
    )
    return r.json()


def put_request(api_key, path, data):
    headers = {
        'Authorization': api_key
    }
    r = requests.put(
        url=path,
        headers=headers,
        json=data
    )
    return r.json()


def get_collection_info(api_key, collection_id):
    path = f'https://api.avrae.io/workshop/collection/{collection_id}/full'
    headers = {
        'Authorization': api_key
    }
    r = requests.get(
        url=path,
        headers=headers
    )
    data = r.json()
    if not data['success']:
        raise RequestError(f'{collection_id} collection data grab did not succeed.\n{json.dumps(data, indent=4)}')
    return r.json()


def update_workshop_obj(type: str, object_id, code: str, api_key):
    if type not in ['alias', 'snippet']:
        raise ValueError('Type must be alias or snippet')
    url = f'https://api.avrae.io/workshop/{type}/{object_id}/code'
    data = {
        'content': code
    }
    code_version = post_request(api_key, url, data)
    if not code_version['success']:
        raise RequestError(f'{type.title()} Code Version did not succeed.\n{json.dumps(code_version, indent=4)}')
    put_url = f'https://api.avrae.io/workshop/{type}/{object_id}/active-code'
    put_data = {
        'version': code_version['data']['version']
    }
    set_active = put_request(api_key, put_url, put_data)
    return code_version, set_active


def read_and_update(obj: ConstructedPath, api_key):
    new_content = None
    try:
        with open(obj.rel_path) as f:
            new_content = f.read()
    except FileNotFoundError:
        print(f'!! File {obj.rel_path} not found! skipping. !!')
    if new_content is None:
        return None
    print(f'- Updating {obj.type} {obj.obj_name} ({obj.id})')
    if new_content == obj.content:
        print('- No change in object code, skipping...')
        return -1
    return update_workshop_obj(obj.type, obj.id, new_content, api_key)


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

    # Grab directories that have files that end in .alias, .snippet, or .gvar
    active_directories = scan_directories(repo_path, collection_ids)

    # Go through our modified files and see if they are in active directories
    active_files = files_in_actives(repo_path, modified_files_list)

    # construct possible file paths from collections
    for collection in collection_ids:
        # get our collection's info
        data = get_collection_info(AVRAE_TOKEN, collection_ids[collection])
        # construct file paths based on collection data
        paths = construct_file_paths(data['data'], collection)
        # compare constructed paths to modified files
        modified_objects = {obj for obj in paths if obj.rel_path in modified_files_list}

        # update every modified file
        for obj in modified_objects:
            result = read_and_update(obj, AVRAE_TOKEN)
            if result is None:
                print('- File not found.')
            elif result == -1:
                continue
            print(f'- Updated {obj.type} {obj.obj_name} ({obj.id})'
                  f' - Updated? {result[0]["success"] and result[1]["success"]}'
                  f' - Version {result[0]["data"]["version"] if result[0]["success"] else "N/A"}')
