import json
import os

from autoupdate.avrae import (
    get_collection_info,
    construct_file_paths,
    construct_gvars,
    ConstructedPath,
)

COLLECTION_RESPONSE_PATH = response_file = os.path.join(os.path.dirname(__file__), 'collection_response.json')

def test_get_collection_info(requests_mock):
    collection_id = '5fa19a9814a62cb7e811c5c4'
    api_key = 'abc'
    with open(COLLECTION_RESPONSE_PATH, mode='rb') as collection_response:
        requests_mock.get(f'https://api.avrae.io/workshop/collection/{collection_id}/full', request_headers={'Authorization': api_key}, body=collection_response)
        avrae_collection = get_collection_info(api_key=api_key, collection_id=collection_id)
        assert avrae_collection['data']['_id'] == collection_id

def test_construct_file_paths():
    with open(COLLECTION_RESPONSE_PATH, mode='rb') as collection_response:
        avrae_collection = json.load(collection_response)
        file_paths = construct_file_paths(avrae_collection['data'], 'prefix')
        assert sorted(file_paths) == sorted([
            ConstructedPath(
                obj_name='test-subalias',
                rel_path='prefix/test-alias/test-subalias/test-subalias.alias',
                id='60121c56a2be999cfcb21ff8',
                type='alias',
                content='echo The `test-subsubalias` alias does not have an active code version. Please contact the collection author, or if you are the author, create or select an active code version on the Alias Workshop.',
            ),
            ConstructedPath(
                obj_name='test123',
                rel_path='prefix/test123.snippet',
                id='6009f400052554a14d3978f3',
                type='snippet',
                content='-f "Test123|Snippet x123"',
            ),
            ConstructedPath(
                obj_name='test-alias',
                rel_path='prefix/test-alias/test-alias.alias',
                id='5fa19b4814a62cb7e811c5c5',
                type='alias',
                content='echo nano ftw x3\n',
            ),
            ConstructedPath(
                obj_name='test-subalias',
                rel_path='prefix/test-alias/test-subalias.alias',
                id='600e5927deab056568e69ac4',
                type='alias',
                content='echo test sub-alias! part 9',
            ),
        ])

# def test_construct_gvars():
#     ids = {'1': 'gvar a', '2': 'gvar b'}
#     files = ['gvars/1.gvar', 'gvars/2.gvar']
#     gvars = construct_gvars(ids=ids, files=files)
#     assert sorted(gvars) == sorted([
#         ConstructedPath(
#             obj_name='1',
#             rel_path='',
#             id='1',
#             type='gvar',
#             content='',
#         ),
#     ])
