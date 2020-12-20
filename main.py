import os
import json
import requests


def get_modified_collections(modified_files, collections):
    out = {}
    for collection in collections:
        modifed = any([file for file in modified_files if file.startswith(collection)])
        if modifed:
            out[collection] = collections[collection]
    return out


def request_collection(collection_id, avrae_token):
    headers = {
        'Authorization': avrae_token,
        'User-Agent': 'AvraeAutoUpdateScript'
    }
    url = f'https://api.avrae.io/workshop/collection/{collection_id}/full'
    request = requests.get(
        headers=headers,
        url=url
    )
    return request


def post_alias(alias_id: str, avrae_token: str, code: str, type='alias', set_active=True):
    headers = {
        'Authorization': avrae_token,
        'User-Agent': 'AvraeAutoUpdateScript'
    }
    post_content = {
        'content': code
    }
    url = f'https://api.avrae.io/workshop/{type}/{alias_id}'
    request = requests.post(
        headers=headers,
        url=url,
        json=post_content
    )
    if set_active:
        request_result = request.json()
        if not 'data' in request_result:
            return request
        version = request_result['data']['version']
        active = set_alias_active(alias_id, avrae_token, version)
        return request, active
    return request


def set_alias_active(alias_id, avrae_token, version):
    headers = {
        'Authorization': avrae_token,
        'User-Agent': 'AvraeAutoUpdateScript'
    }
    post_content = {
        'version': version
    }
    url = f'https://api.avrae.io/workshop/{type}/{alias_id}'
    request = requests.put(
        headers=headers,
        url=url,
        json=post_content
    )
    return request


def main(collection_ids_file, path_to_files, avrae_token, modified_files):
    with open(collection_ids_file, 'r') as f:
        collections = json.loads(f.read())
    modified_collections = get_modified_collections(modified_files, collections)
    for modified_collection_dir in modified_collections:
        collection_id = modified_collections[modified_collection_dir]
        collection_content = request_collection(collection_id, avrae_token).json()
        if not 'data' in collection_content:
            print(f'Could not find collection data for collection at {modified_collection_dir}')
            continue


if __name__ == '__main__':

    # Collect Environmental Variables
    collection_ids = os.environ.get('INPUT_COLLECTION_IDS_FILE_NAME')
    repo_path = os.environ.get('GITHUB_WORKSPACE')
    AVRAE_TOKEN = os.getenv('INPUT_AVRAE-TOKEN', None)
    modified_files_list = json.loads(os.getenv('INPUT_MODIFIED-FILES', '[]'))

    # Let's exit if we don't have a token.
    if AVRAE_TOKEN is None:
        print('No Avrae Token Found, Exiting!')
        exit(1)

    main(collection_ids, repo_path, AVRAE_TOKEN, modified_files_list)
