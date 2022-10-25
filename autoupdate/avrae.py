import json
import ntpath
import os
import requests
import collections
import pathlib


ConstructedPath = collections.namedtuple('ConstructedPath', ['obj_name', 'rel_path', 'id', 'type', 'content'])

class RequestError(BaseException):
    pass

# Requests

def post_request(api_key, path, request_data):
    headers = {
        'Authorization': api_key
    }
    r = requests.post(
        url=path,
        headers=headers,
        json=request_data
    )
    raw_data = r.content.decode('ascii')
    return r.json() if raw_data.startswith('{') else raw_data


def put_request(api_key, path, request_data):
    headers = {
        'Authorization': api_key
    }
    r = requests.put(
        url=path,
        headers=headers,
        json=request_data
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
    request_data = r.json()
    if not request_data['success']:
        raise RequestError(f'{collection_id} collection data grab did not succeed.\n'
                           f'{json.dumps(request_data, indent=4)}')
    return r.json()


def update_workshop_obj(type_: str, object_id, code: str, api_key):
    if type_ not in ['alias', 'snippet']:
        raise ValueError('Type must be alias or snippet')
    url = f'https://api.avrae.io/workshop/{type_}/{object_id}/code'
    request_data = {
        'content': code
    }
    code_version = post_request(api_key, url, request_data)
    if not code_version['success']:
        raise RequestError(f'{type_.title()} Code Version did not succeed.\n{json.dumps(code_version, indent=4)}')
    put_url = f'https://api.avrae.io/workshop/{type_}/{object_id}/active-code'
    put_data = {
        'version': code_version['data']['version']
    }
    set_active = put_request(api_key, put_url, put_data)
    return code_version, set_active


def update_gvar(obj: ConstructedPath, api_key):
    url = f'https://api.avrae.io/customizations/gvars/{obj.id}'
    request_data = {
        'value': obj.content
    }
    request_result = post_request(api_key, url, request_data)
    if request_result != 'Gvar updated.':
        raise RequestError(f'{obj.type.title()} update did not succeed.\n{request_result}')
    return request_result


def read_and_update(obj: ConstructedPath, api_key):
    new_content = None
    try:
        with open(obj.rel_path) as file:
            new_content = file.read()
    except FileNotFoundError:
        print(f'!! File {obj.rel_path} not found! skipping. !!')
    if new_content is None:
        return None
    print(f'- Updating {obj.type} {obj.obj_name} ({obj.id})')
    if new_content == obj.content:
        print('- No change in object code, skipping...')
        return -1
    return update_workshop_obj(obj.type, obj.id, new_content, api_key)

# utility functions


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)




# take a collection's data and path
# and construct file paths based on
# alias name + parent names as folders
# if it's a base alias, there is an alias in it's own folder
# alias with sub-aliases in folder, alias with no sub-aliases by itself



def construct_file_paths(collection_data, collection_path):
    logged_parents = {}
    file_paths = set()

    def parse_obj(obj_data, suffix='.alias', own_folder=True):
        folder_name = obj_data['name'].lower()
        obj_name = folder_name + suffix
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


def construct_gvars(ids, files):
    gvar_names = [path_leaf(x) for x in files]
    constructed = []
    for listed_gvar in ids:
        for i, gvar_name in enumerate(gvar_names):
            if gvar_name.startswith(listed_gvar):
                with open(files[i]) as read:
                    content = read.read()
                gvar_desc = gvar_name.strip(listed_gvar).strip()
                gvar = ConstructedPath(gvar_desc if gvar_desc else listed_gvar,
                                       files[i], listed_gvar, 'gvar', content)
                constructed.append(gvar)
    return constructed