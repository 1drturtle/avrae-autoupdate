import pytest

from autoupdate.avrae import (
    Alias,
    Collection,
    Gvar,
    Snippet,
)

COLLECTIONS = {
    '5fa19a9814a62cb7e811c5c4': Collection(
        name='API Collection Test',
        description='Has my test aliases from the API',
        image=None,
        owner='175386962364989440',
        alias_ids=['5fa19b4814a62cb7e811c5c5'],
        snippet_ids=['6009f400052554a14d3978f3'],
        publish_state='UNLISTED',
        num_subscribers=1,
        num_guild_subscribers=1,
        last_edited='2022-09-20T17:35:03Z',
        created_at='2020-11-03T17:59:52.868000Z',
        tags=[],
        id='5fa19a9814a62cb7e811c5c4',
        aliases=[
            Alias(
                name='test-alias',
                code='echo nano ftw x3\n',
                versions=[],
                docs='docs for the test alias',
                entitlements=[],
                collection_id='5fa19a9814a62cb7e811c5c4',
                id='5fa19b4814a62cb7e811c5c5',
                subcommand_ids=['600e5927deab056568e69ac4'],
                parent_id=None,
                subcommands=[
                    Alias(
                        name='test-subalias',
                        code='echo test sub-alias! part 9',
                        versions=[],
                        docs='a e i o u',
                        entitlements=[],
                        collection_id='5fa19a9814a62cb7e811c5c4',
                        id='600e5927deab056568e69ac4',
                        subcommand_ids=['60121c56a2be999cfcb21ff8'],
                        parent_id='5fa19b4814a62cb7e811c5c5',
                        subcommands=[
                            Alias(
                                name='test-subalias',
                                code='echo The `test-subsubalias` alias does not have an active code version. Please contact the collection author, or if you are the author, create or select an active code version on the Alias Workshop.',
                                versions=[],
                                docs='asb',
                                entitlements=[],
                                collection_id='5fa19a9814a62cb7e811c5c4',
                                id='60121c56a2be999cfcb21ff8',
                                subcommand_ids=[],
                                parent_id='600e5927deab056568e69ac4',
                                subcommands=[],
                            ),
                        ],
                    ),
                ],
            ),
        ],
        snippets=[
            Snippet(
                name='test123',
                code='-f \"Test123|Snippet x123\"',
                versions=[],
                docs='snippet docs',
                entitlements=[],
                collection_id='5fa19a9814a62cb7e811c5c4',
                id='6009f400052554a14d3978f3',
            ),
        ],
    )
}

@pytest.fixture
def collection_fixtures() -> dict[str, Collection]:
    """
    Collections test fixtures, a dict mapping ids to Collections
    """
    return COLLECTIONS

@pytest.fixture
def gvars_fixture() -> list[Gvar]:
    """
    Gvars fixture, a list of Gvars
    """
    return [
        Gvar(
            owner='308324091675271060',
            key='5aec63f9-8fb4-42e2-95fe-6ca0dcb4b24e',
            owner_name='Someone',
            value='some code',
            editors=[]
        )
    ]
