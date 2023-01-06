"""
Tools for interacting with Avrae's API
"""

from itertools import chain
import json
import typing
import requests

AVRAE_API_TIMEOUT = 10.0

class Alias(typing.NamedTuple):
    """
    Avrae Alias API response object
    """
    name: str
    code: str
    versions: list
    docs: str
    entitlements: list[str]
    collection_id: str
    id: str
    subcommand_ids: list[str]
    parent_id: str | None
    subcommands: list['Alias']

class Snippet(typing.NamedTuple):
    """
    Avrae Snippet API response object
    """
    name: str
    code: str
    versions: list
    docs: str
    entitlements: list[str]
    collection_id: str
    id: str

class Collection(typing.NamedTuple):
    """
    Avrae Collection API response object
    """
    name: str
    description: str
    image: str | None
    owner: str
    alias_ids: list[str]
    snippet_ids: list[str]
    publish_state: str
    num_subscribers: int
    num_guild_subscribers: int
    last_edited: str
    created_at: str
    tags: list[str]
    id: str
    aliases: list[Alias]
    snippets: list[Snippet]

class Gvar(typing.NamedTuple):
    """
    Avrae Gvar API response object
    """
    owner: str
    key: str
    owner_name: str
    value: str
    editors: list[str]

class CodeVersion(typing.NamedTuple):
    """
    Avrae API response for Alias/Snippet code versions
    """
    version: int
    content: str
    created_at: str
    is_current: bool

class ConstructedPath(typing.NamedTuple):
    """
    Associate repo files with Avrae collections
    """
    obj_name: str
    rel_path: str
    id: str
    type: str
    content: str

class RequestError(BaseException):
    """
    Wrapper for Avrae API response errors
    """

def _snippet_from_data(json_data) -> Snippet:
    """
    Extract a Snippet from an Avrae API response's JSON
    """
    return Snippet(
        name=json_data['name'],
        code=json_data['code'],
        versions=json_data.get('versions', []),
        docs=json_data.get('docs', ''),
        entitlements=json_data.get('entitlements', []),
        collection_id=json_data['collection_id'],
        id=json_data['_id'],
    )

def _alias_from_data(json_data) -> Alias:
    """
    Extract an Alias from an Avrae API response's JSON
    """
    return Alias(
        name=json_data['name'],
        code=json_data['code'],
        versions=json_data.get('versions', []),
        docs=json_data.get('docs', ''),
        entitlements=json_data.get('entitlements', []),
        collection_id=json_data['collection_id'],
        id=json_data['_id'],
        subcommand_ids=json_data.get('subcommand_ids', []),
        parent_id=json_data.get('parent_id', None),
        subcommands=[
            _alias_from_data(alias_data) for alias_data in json_data.get('subcommands', [])
        ],
    )

def _collection_from_data(json_data) -> Collection:
    """
    Extract a Collection from an Avrae API response's JSON
    """
    return Collection(
        name=json_data['name'],
        description=json_data['description'],
        image=json_data['image'],
        owner=json_data['owner'],
        alias_ids=json_data['alias_ids'],
        snippet_ids=json_data['snippet_ids'],
        publish_state=json_data['publish_state'],
        num_subscribers=json_data['num_subscribers'],
        num_guild_subscribers=json_data['num_guild_subscribers'],
        last_edited=json_data['last_edited'],
        created_at=json_data['created_at'],
        tags=json_data['tags'],
        id=json_data['_id'],
        aliases=[_alias_from_data(alias_data) for alias_data in json_data['aliases']],
        snippets=[_snippet_from_data(snippet_data) for snippet_data in json_data['snippets']],
    )

def _gvars_from_data(json_data) -> list[Gvar]:
    """
    Construct Gvars from an Avrae API response's JSON
    """
    def _gvar_from_data(gvar_json) -> Gvar:
        return Gvar(
            owner=gvar_json['owner'],
            key=gvar_json['key'],
            owner_name=gvar_json['owner_name'],
            value=gvar_json['value'],
            editors=gvar_json['editors']
        )
    owned_gvars = (_gvar_from_data(gvar_data) for gvar_data in json_data['owned'])
    editable_gvars = (_gvar_from_data(gvar_data) for gvar_data in json_data['editable'])
    return list(chain(owned_gvars, editable_gvars))

def _version_from_data(json_data) -> CodeVersion:
    """
    Construct a CodeVersion from an Avrae API response
    """
    return CodeVersion(
        version=json_data['version'],
        content=json_data['content'],
        created_at=json_data['created_at'],
        is_current=json_data['is_current']
    )

def _get_collection(session: requests.Session, collection_id: str) -> Collection:
    """
    Fetch a collection from Avrae
    """
    response = session.get(
        url=f'https://api.avrae.io/workshop/collection/{collection_id}/full',
        timeout=AVRAE_API_TIMEOUT,
    )
    response.raise_for_status()
    response_data = response.json()
    if not response_data['success']:
        raise RequestError(f'Fetching collection {collection_id} did not succeed.\n'
                           f'{json.dumps(response_data, indent=4)}')
    return _collection_from_data(response_data['data'])

def _get_gvars(session: requests.Session) -> list[Gvar]:
    """
    Fetch the set of all gvars the user can edit from avrae
    """
    response = session.get(
        url='https://api.avrae.io/customizations/gvars',
        timeout=AVRAE_API_TIMEOUT,
    )
    response.raise_for_status()
    response_data = response.json()
    return _gvars_from_data(response_data)

def _recent_matching_version(
    session: requests.Session,
    resource_type: typing.Literal['snippet'] | typing.Literal['alias'],
    item_id: str,
    code: str
    ) -> CodeVersion | None:
    item_limit = 10
    request_limit = 5 # better to skip the oldest versions than flood avrae with requests

    skip = 0
    page = 0
    fetch_next_page = True
    while fetch_next_page and page < request_limit:
        page += 1

        path = (
            f'https://api.avrae.io/workshop/{resource_type}/{item_id}/code'
            f'?skip={skip}&limit={item_limit}'
        )

        response = session.get(
            url=path,
            timeout=AVRAE_API_TIMEOUT,
        )
        response.raise_for_status()
        response_data = response.json()
        if not response_data['success']:
            raise RequestError(f'{resource_type}/{item_id} failed to fetch code versions.\n'
                           f'{json.dumps(response_data, indent=4)}')
        versions_data = response.json()['data']

        for version_data in versions_data:
            if version_data['content'] == code:
                return _version_from_data(version_data)

        skip += len(versions_data)
        fetch_next_page = len(versions_data) == item_limit
    return None

class AvraeClient():
    """
    An object for managing interactions with Avrae's API on behalf of a specific account.

    Caches collection and gvar responses to avoid repeated API calls when possible.
    """

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

        self._collections: dict[Collection] = {}
        self._gvars: list[Gvar] | None = None

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': self.api_key,
            'User-Agent': 'avrae-autoupdate',
        })

    def _clear_collection_from_cache(self, collection_id: str):
        if collection_id in self._collections:
            del self._collections[collection_id]

    def get_collections(self, collection_ids: list[str]) -> list[Collection]:
        """
        Return the set of collections registered with this client.
        """

        results: list[Collection] = []
        for collection_id in collection_ids:
            if collection_id in self._collections:
                results.append(self._collections[collection_id])
            else:
                collection = _get_collection(
                    session=self.session,
                    collection_id=collection_id
                )
                self._collections[collection_id] = collection
                results.append(collection)
        return results

    def get_collection(self, collection_id: str) -> Collection | None:
        """
        Return a specific collection registered with this client.
        """

        return self.get_collections(collection_ids=[collection_id])[0]

    def get_gvars(self) -> list[Gvar]:
        """
        Return the set of all gvars editable by client's account.
        """

        if not self._gvars:
            self._gvars = _get_gvars(session=self.session)
        return self._gvars

    def get_owned_collection_ids(self) -> list[str]:
        """
        Return a list of the ids of collections owned by this account.
        """
        response = self.session.get(
            url='https://api.avrae.io/workshop/owned',
            timeout=AVRAE_API_TIMEOUT,
        )
        response.raise_for_status()
        response_data = response.json()
        if not response_data['success']:
            raise RequestError(f'Fetching owned collections did not succeed.\n'
                           f'{json.dumps(response_data, indent=4)}')
        return response_data['data']

    def get_editable_collection_ids(self) -> list[str]:
        """
        Return a list of the ids of collections editable by but not owned by this account.
        """
        response = self.session.get(
            url='https://api.avrae.io/workshop/editable',
            timeout=AVRAE_API_TIMEOUT,
        )
        response.raise_for_status()
        response_data = response.json()
        if not response_data['success']:
            raise RequestError(f'Fetching editable collections did not succeed.\n'
                           f'{json.dumps(response_data, indent=4)}')
        return response_data['data']

    def recent_matching_version(self, item: Alias | Snippet, code: str) -> CodeVersion | None:
        """
        Return the most recent version of a snippet or alias with the same code as the given item.

        Used to identify if the current repository code exists in an avrae version but is out of
        date due to edits uploaded directly to avrae.
        """

        return _recent_matching_version(
            session=self.session,
            resource_type='alias' if isinstance(item, Alias) else 'snippet',
            item_id=item.id,
            code=code
        )

    def create_new_code_version(self, item: Alias | Snippet, code: str) -> CodeVersion:
        """
        Creates a new code version containing the item's current code.
        """

        resource_type='alias' if isinstance(item, Alias) else 'snippet'
        response = self.session.post(
            url=f'https://api.avrae.io/workshop/{resource_type}/{item.id}/code',
            timeout=AVRAE_API_TIMEOUT,
            json={
                'content': code
            }
        )
        response.raise_for_status()
        response_data = response.json()

        if not response_data['success']:
            raise RequestError(f'{resource_type}/{id} failed to create new code versions.\n'
                f'{json.dumps(response_data, indent=4)}')
        self._clear_collection_from_cache(item.collection_id)

        new_version = _version_from_data(response_data['data'])
        return new_version

    def set_active_code_version(self, item: Alias | Snippet, version: int) -> Alias | Snippet:
        """
        Sets a specific code version of an item to be active.
        """

        resource_type='alias' if isinstance(item, Alias) else 'snippet'
        response = self.session.put(
            url=f'https://api.avrae.io/workshop/{resource_type}/{item.id}/active-code',
            timeout=AVRAE_API_TIMEOUT,
            json={
                'version': version
            }
        )

        response.raise_for_status()
        response_data = response.json()
        if not response_data['success']:
            raise RequestError(f'{resource_type}/{id} failed to activate code version.\n'
                f'{response.request.body} returned {json.dumps(response_data, indent=4)}')
        self._clear_collection_from_cache(item.collection_id)

        if isinstance(item, Alias):
            return _alias_from_data(response_data['data'])
        return _snippet_from_data(response_data['data'])

    def update_docs(self, item: Alias | Snippet, yaml: str) -> Alias | Snippet:
        """
        Sets the yaml docs for a given item.

        Note: docs are not tied to a code version.
        """

        resource_type='alias' if isinstance(item, Alias) else 'snippet'
        response = self.session.patch(
            url=f'https://api.avrae.io/workshop/{resource_type}/{item.id}',
            timeout=AVRAE_API_TIMEOUT,
            json={
                'docs': yaml,
                'name': item.name,
            }
        )
        response.raise_for_status()
        response_data = response.json()
        if not response_data['success']:
            raise RequestError(f'{resource_type}/{id} failed to update docs.\n'
                f'{json.dumps(response_data, indent=4)}')
        self._clear_collection_from_cache(item.collection_id)

        if isinstance(item, Alias):
            return _alias_from_data(response_data['data'])
        return _snippet_from_data(response_data['data'])

    def update_gvar(self, gvar: Gvar, value: str):
        """
        Updates the contents of the given gvar.
        """

        response = self.session.post(
            url=f'https://api.avrae.io/customizations/gvars/{gvar.key}',
            timeout=AVRAE_API_TIMEOUT,
            json={
                'value': value
            }
        )
        response.raise_for_status()
        response_content = response.content.decode('ascii')
        if response_content != 'Gvar updated.':
            raise RequestError(f'Updating gvar {gvar.key} failed.\n{response_content}')
