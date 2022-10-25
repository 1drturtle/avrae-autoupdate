import json
import os

from autoupdate.sources import (
    scan_directories,
    files_in_actives,
)
from autoupdate.avrae import (
    get_collection_info,
    read_and_update,
    update_gvar,
    construct_file_paths,
    construct_gvars,
)

class MissingArgument(BaseException):
    pass

if __name__ == '__main__':

    # Collect Environmental Variables
    repo_path = os.environ.get('GITHUB_WORKSPACE', None)
    if repo_path:
        os.chdir(repo_path)
    collection_ids_file = os.environ.get('INPUT_COLLECTIONS_ID_FILE_NAME')
    gvar_ids_file_name = os.getenv('INPUT_GVARS_ID_FILE_NAME', None)
    print(f'loading collections from {collection_ids_file}')
    with open(collection_ids_file) as f:
        collection_ids = json.loads(f.read())
    AVRAE_TOKEN = os.getenv('INPUT_AVRAE-TOKEN', None)
    modified_files_list = json.loads(os.getenv('INPUT_MODIFIED-FILES', '[]'))

    # Let's exit if we don't have a token.
    if AVRAE_TOKEN is None:
        raise MissingArgument('No Avrae Token Found.')

    # Grab directories that have files that end in .alias, .snippet, or .gvar
    print("Loading directories")
    active_directories = scan_directories(repo_path, collection_ids)
    print(f'{active_directories}')
    
    # Go through our modified files and see if they are in active directories
    print("loading files from directories")
    active_files = files_in_actives(repo_path, modified_files_list)
    print(f'{active_files}')

    # construct possible file paths from collections
    for collection in collection_ids:
        print("Looking at " + collection) 
        # get our collection's info
        data = get_collection_info(AVRAE_TOKEN, collection_ids[collection])
        # construct file paths based on collection data
        paths = construct_file_paths(data['data'], collection)
        # compare constructed paths to modified files
        modified_objects = {obj for obj in paths if obj.rel_path in modified_files_list}
        print(f"Found {modified_objects}") 

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

    # update our global variables
    if gvar_ids_file_name:
        with open(gvar_ids_file_name) as f:
            gvar_ids = json.loads(f.read())
        gvar_files = [file for file in active_files if file.endswith('gvar')]
        constructed_gvars = construct_gvars(gvar_ids, gvar_files)
        for gvar in constructed_gvars:
            rq = update_gvar(gvar, AVRAE_TOKEN)
            print(f'- Updated GVAR {gvar.id}')
