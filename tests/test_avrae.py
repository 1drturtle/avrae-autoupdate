"""
Tests for avrae.py
"""

import os

from autoupdate.avrae import (
    AvraeClient,
    CodeVersion,
    Alias,
    Gvar,
    Snippet,
)

TEST_COLLECTION_RESPONSE_PATH = response_file = os.path.join(
    os.path.dirname(__file__),
    'test_collection_response.json'
)
EMPTY_COLLECTION_RESPONSE_PATH = response_file = os.path.join(
    os.path.dirname(__file__),
    'empty_collection_response.json'
)
GVAR_RESPONSE_PATH = os.path.join(os.path.dirname(__file__), 'gvars_response.json')
API_KEY = 'some-api-key-value'

def test_avrae_client_get_collections(requests_mock):
    collection_ids = ['5fa19a9814a62cb7e811c5c4', '637febd016eb2e36c2591b47']

    client = AvraeClient(api_key=API_KEY)
    with open(TEST_COLLECTION_RESPONSE_PATH, mode='rb') as collection_1_response, \
        open(TEST_COLLECTION_RESPONSE_PATH, mode='rb') as collection_2_response:
        requests_mock.get(
            f'https://api.avrae.io/workshop/collection/{collection_ids[0]}/full',
            request_headers={'Authorization': API_KEY},
            body=collection_1_response
        )
        requests_mock.get(
            f'https://api.avrae.io/workshop/collection/{collection_ids[1]}/full',
            request_headers={'Authorization': API_KEY},
            body=collection_2_response
        )

        assert len(client.get_collections(collection_ids=collection_ids)) == len(collection_ids)

        # collections should be cached and only requested once
        client.get_collections(collection_ids=collection_ids)
        assert len(requests_mock.request_history) == len(collection_ids)


def test_avrae_client_get_collection(requests_mock, collection_fixtures):
    collection_id = '5fa19a9814a62cb7e811c5c4'

    client = AvraeClient(api_key=API_KEY)
    with open(TEST_COLLECTION_RESPONSE_PATH, mode='rb') as collection_response:
        requests_mock.get(
            f'https://api.avrae.io/workshop/collection/{collection_id}/full',
            request_headers={'Authorization': API_KEY},
            body=collection_response
        )
        avrae_collection = client.get_collection(collection_id=collection_id)
        assert avrae_collection == collection_fixtures[collection_id]

        # collection should be cached and only requested once
        assert avrae_collection == client.get_collection(collection_id=collection_id)
        assert len(requests_mock.request_history) == 1

def test_avrae_client_gvars(requests_mock, gvars_fixture):
    client = AvraeClient(api_key=API_KEY)
    with open(GVAR_RESPONSE_PATH, mode='rb') as gvars_response:
        requests_mock.get(
            'https://api.avrae.io/customizations/gvars',
            request_headers={'Authorization': API_KEY},
            body=gvars_response
        )
        gvars = client.get_gvars()
        assert gvars == gvars_fixture

        # gvars should be cached and only requested once
        assert gvars == client.get_gvars()
        assert len(requests_mock.request_history) == 1

def test_get_owned_collection_ids(requests_mock):
    client = AvraeClient(api_key=API_KEY)
    requests_mock.get(
        'https://api.avrae.io/workshop/owned',
        request_headers={'Authorization': API_KEY},
        json={
            'success': True,
            'data': ['a', 'b', 'c']
        }
    )
    ids = client.get_owned_collection_ids()
    assert ids == ['a', 'b', 'c']
    assert len(requests_mock.request_history) == 1

def test_get_editable_collection_ids(requests_mock):
    client = AvraeClient(api_key=API_KEY)
    requests_mock.get(
        'https://api.avrae.io/workshop/editable',
        request_headers={'Authorization': API_KEY},
        json={
            'success': True,
            'data': ['a', 'b', 'c']
        }
    )
    ids = client.get_editable_collection_ids()
    assert ids == ['a', 'b', 'c']
    assert len(requests_mock.request_history) == 1

def test_avrae_client_recent_matching_version_aliases(requests_mock):
    collection_id = 'c011ec7104'
    alias_id = 'a11a5'

    client = AvraeClient(api_key=API_KEY)
    requests_mock.get(
        f'https://api.avrae.io/workshop/alias/{alias_id}/code?skip=0&limit=10',
        request_headers={'Authorization': API_KEY},
        json={
            'success': True,
            'data': [
                {
                    'version': 1,
                    'content': 'first try',
                    'created_at': '2022-01-01T01:00:00.000000Z',
                    'is_current': False,
                },
                {
                    'version': 2,
                    'content': 'second try',
                    'created_at': '2022-01-01T01:01:00.000000Z',
                    'is_current': True,
                },
            ],
        }
    )

    alias = Alias(
        name="test",
        code="second try",
        collection_id=collection_id,
        id=alias_id,
        docs="docs",
        versions=[],
        entitlements=[],
        subcommand_ids=[],
        subcommands=[],
        parent_id=None,
    )

    version = client.recent_matching_version(alias, code='second try')
    assert version.version == 2
    assert version.is_current is True

    version = client.recent_matching_version(alias, code='first try')
    assert version.version == 1
    assert version.is_current is False

    version = client.recent_matching_version(alias, code='unpublished')
    assert version is None

def test_avrae_client_recent_matching_version_aliases_with_long_history(requests_mock):
    collection_id = 'c011ec7104'
    alias_id = 'a11a5'

    client = AvraeClient(api_key=API_KEY)
    for page in range(0, 7):
        requests_mock.get(
            f'https://api.avrae.io/workshop/alias/{alias_id}/code?skip={page * 10}&limit=10',
            request_headers={'Authorization': API_KEY},
            json={
                'success': True,
                'data': [{
                    'version': version,
                    'content': str(version),
                    'created_at': '2022-01-01T01:01:00.000000Z',
                    'is_current': False
                } for version in range(1 + page * 10, 10 + page * 10 + 1)]
            }
        )

    alias = Alias(
        name="test",
        code="1",
        collection_id=collection_id,
        id=alias_id,
        docs="docs",
        versions=[],
        entitlements=[],
        subcommand_ids=[],
        subcommands=[],
        parent_id=None,
    )

    version = client.recent_matching_version(alias, code='unpublished')
    assert version is None

    version = client.recent_matching_version(alias, code='22')
    assert version.version == 22

def test_avrae_client_recent_matching_version_snippet(requests_mock):
    collection_id = 'c011ec7104'
    snippet_id = '54188e7'

    client = AvraeClient(api_key=API_KEY)
    requests_mock.get(
        f'https://api.avrae.io/workshop/snippet/{snippet_id}/code?skip=0&limit=10',
        request_headers={'Authorization': API_KEY},
        json={
            'success': True,
            'data': [
                {
                    'version': 1,
                    'content': 'first try',
                    'created_at': '2022-01-01T01:00:00.000000Z',
                    'is_current': False,
                },
                {
                    'version': 2,
                    'content': 'second try',
                    'created_at': '2022-01-01T01:01:00.000000Z',
                    'is_current': True,
                },
            ],
        }
    )

    snippet = Snippet(
        name="test",
        code="second try",
        collection_id=collection_id,
        id=snippet_id,
        docs="docs",
        versions=[],
        entitlements=[],
    )

    version = client.recent_matching_version(snippet, code='second try')
    assert version.version == 2
    assert version.is_current is True

    version = client.recent_matching_version(snippet, code='first try')
    assert version.version == 1
    assert version.is_current is False

    version = client.recent_matching_version(snippet, code='unpublished')
    assert version is None

def test_avrae_client_create_new_code_version(requests_mock):
    client = AvraeClient(api_key=API_KEY)
    alias = Alias(
        name="test-alias",
        code="old code",
        collection_id='c011ec7104',
        id='a11a5',
        docs="docs",
        versions=[],
        entitlements=[],
        subcommand_ids=[],
        subcommands=[],
        parent_id=None,
    )
    requests_mock.post(
        f'https://api.avrae.io/workshop/alias/{alias.id}/code',
        request_headers={'Authorization': API_KEY},
        json={
            'success': True,
            'data': {
                'version': 2,
                'content': 'new code',
                'created_at': '2022-12-14T20:27:00.000000Z',
                'is_current': False,
            }
        }
    )
    version = client.create_new_code_version(item=alias, code='new code')
    assert len(requests_mock.request_history) == 1
    assert version == CodeVersion(
        version=2,
        content='new code',
        created_at='2022-12-14T20:27:00.000000Z',
        is_current=False,
    )

def test_avrae_client_set_active_code_version(requests_mock):
    client = AvraeClient(api_key=API_KEY)
    alias = Alias(
        name="test-alias",
        code="current code",
        collection_id='c011ec7104',
        id='a11a5',
        docs="docs",
        versions=[],
        entitlements=[],
        subcommand_ids=[],
        subcommands=[],
        parent_id=None,
    )
    requests_mock.put(
        f'https://api.avrae.io/workshop/alias/{alias.id}/active-code',
        request_headers={'Authorization': API_KEY},
        json={
            'success': True,
            'data': {
                "name": "test-alias",
                "code": "older code",
                "versions": [
                    {
                        "version": 1,
                        "content": "older code",
                        "created_at": "2022-12-14T20:27:00.000000Z",
                        "is_current": True,
                    },
                    {
                        "version": 2,
                        "content": "newer code",
                        "created_at": "2022-12-14T21:30:00.000000Z",
                        "is_current": False,
                    }
                ],
                "docs": "docs",
                "entitlements": [],
                "collection_id": "c011ec7104",
                "_id": "a11a5",
                "subcommand_ids": [],
                "parent_id": None,
            }
        }
    )
    client.set_active_code_version(item=alias, version=1)
    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].json() == {
        'version': 1
    }

def test_avrae_client_update_gvar(requests_mock):
    client = AvraeClient(api_key=API_KEY)
    gvar = Gvar(
        owner='1234',
        key='123abc',
        owner_name='someone',
        value='gvar code',
        editors=[]
    )
    requests_mock.post(
        f'https://api.avrae.io/customizations/gvars/{gvar.key}',
        request_headers={'Authorization': API_KEY},
        text='Gvar updated.'
    )
    client.update_gvar(gvar, value='new code')
    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].json() == {
        'value': 'new code'
    }

def test_update_docs(requests_mock):
    client = AvraeClient(api_key=API_KEY)
    alias = Alias(
        name="test-alias",
        code="code",
        collection_id='c011ec7104',
        id='a11a5',
        docs="docs",
        versions=[],
        entitlements=[],
        subcommand_ids=[],
        subcommands=[],
        parent_id=None,
    )
    requests_mock.patch(
        f'https://api.avrae.io/workshop/alias/{alias.id}',
        request_headers={'Authorization': API_KEY},
        json={
            'success': True,
            'data': {
                "name": "test-alias",
                "code": "code",
                "versions": [
                    {
                        "version": 1,
                        "content": "code",
                        "created_at": "2022-12-14T20:27:00.000000Z",
                        "is_current": True,
                    },
                ],
                "docs": "docs",
                "entitlements": [],
                "collection_id": "c011ec7104",
                "_id": "a11a5",
                "subcommand_ids": [],
                "parent_id": None,
            }
        }
    )
    client.update_docs(item=alias, yaml='new docs')
    assert len(requests_mock.request_history) == 1
    assert requests_mock.request_history[0].json() == {
        'docs': 'new docs',
        'name': alias.name,
    }
