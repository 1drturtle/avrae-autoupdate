"""
Tests for sources.py
"""

import os
from unittest.mock import Mock
from autoupdate.avrae import Alias, AvraeClient, CodeVersion, Collection, Gvar, Snippet
from autoupdate.sources import (LocalAliasDoesNotMatchAvrae,
                                LocalAliasDocsDoNotMatchAvrae,
                                LocalAliasMatchesAvrae,
                                LocalAliasDocsMatchAvrae,
                                LocalAliasMissing,
                                LocalAliasDocsMissing,
                                LocalAliasNotFoundInAvrae,
                                LocalGvarDoesNotMatchAvrae,
                                LocalGvarMatchesAvrae,
                                LocalGvarMissing,
                                LocalGvarNotFoundInAvrae,
                                LocalSnippetDoesNotMatchAvrae,
                                LocalSnippetDocsDoNotMatchAvrae,
                                LocalSnippetMatchesAvrae,
                                LocalSnippetDocsMatchAvrae,
                                LocalSnippetMissing,
                                LocalSnippetDocsMissing,
                                LocalSnippetNotFoundInAvrae,
                                _compare_aliases, _compare_gvars, _compare_snippets)

def test_compare_aliases(collection_fixtures: dict[str, Collection], tmp_path):
    collection_id = '5fa19a9814a62cb7e811c5c4'
    collection = collection_fixtures[collection_id]

    (tmp_path / 'API Collection Test').mkdir()

    (tmp_path / 'API Collection Test' / 'test-alias').mkdir()
    (tmp_path / 'API Collection Test' / 'test-alias' /
     'test-alias.alias').write_text(collection.aliases[0].code)
    (tmp_path / 'API Collection Test' / 'test-alias' /
     'test-alias.md').write_text(collection.aliases[0].docs)

    (tmp_path / 'API Collection Test' / 'test-alias' / 'test-subalias').mkdir()
    (tmp_path / 'API Collection Test' / 'test-alias' /
     'test-subalias' / 'test-subalias.alias').write_text('changed')
    (tmp_path / 'API Collection Test' / 'test-alias' /
     'test-subalias' / 'test-subalias.md').write_text('changed')

    (tmp_path / 'API Collection Test' / 'new-alias').mkdir()
    (tmp_path / 'API Collection Test' / 'new-alias' /
     'new-alias.alias').write_text('new addition')

    (tmp_path / 'Some other collection').mkdir()
    (tmp_path / 'Some other collection' / 'new-alias').mkdir()
    (tmp_path / 'Some other collection' / 'new-alias' /
     'new-alias.alias').write_text('should be ignored')

    (tmp_path / 'some-alias-file.alias').write_text('should be ignored')

    comparison = _compare_aliases(collection=collection, base_path=tmp_path)
    expected = [
        LocalAliasMatchesAvrae(
            (tmp_path / 'API Collection Test' /
             'test-alias' / 'test-alias.alias'),
            tmp_path,
            collection.aliases[0]
        ),
        LocalAliasDocsMatchAvrae(
            (tmp_path / 'API Collection Test' /
             'test-alias' / 'test-alias.md'),
            tmp_path,
            collection.aliases[0]
        ),
        LocalAliasDoesNotMatchAvrae(
            (tmp_path / 'API Collection Test' / 'test-alias' /
             'test-subalias' / 'test-subalias.alias'),
            tmp_path,
            collection.aliases[0].subcommands[0]
        ),
        LocalAliasDocsDoNotMatchAvrae(
            (tmp_path / 'API Collection Test' / 'test-alias' /
             'test-subalias' / 'test-subalias.md'),
            tmp_path,
            collection.aliases[0].subcommands[0]
        ),
        LocalAliasMissing(
            (tmp_path / 'API Collection Test' / 'test-alias' / 'test-subalias' /
             'test-subalias' / 'test-subalias.alias'),
            tmp_path,
            collection.aliases[0].subcommands[0].subcommands[0]
        ),
        LocalAliasDocsMissing(
            (tmp_path / 'API Collection Test' / 'test-alias' / 'test-subalias' /
             'test-subalias' / 'test-subalias.md'),
            tmp_path,
            collection.aliases[0].subcommands[0].subcommands[0]
        ),
        LocalAliasNotFoundInAvrae(
            (tmp_path / 'API Collection Test' /
             'new-alias' / 'new-alias.alias'),
            tmp_path,
        ),
    ]
    for result in expected:
        assert result in comparison, 'Expected ComparisonResult missing.'
    assert len(expected) == len(comparison)


def test_compare_snippets(collection_fixtures: dict[str, Collection], tmp_path):
    collection_id = '5fa19a9814a62cb7e811c5c4'
    collection = collection_fixtures[collection_id]
    (tmp_path / 'API Collection Test').mkdir()
    (tmp_path / 'API Collection Test' / 'snippets').mkdir()
    (tmp_path / 'API Collection Test' / 'snippets' /
     'test123.snippet').write_text(collection.snippets[0].code)
    (tmp_path / 'API Collection Test' / 'snippets' /
     'test123.md').write_text(collection.snippets[0].docs)

    # When local files match avrae
    assert _compare_snippets(collection=collection, base_path=tmp_path) == [
        LocalSnippetMatchesAvrae(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.snippet'),
            tmp_path,
            collection.snippets[0]
        ),
        LocalSnippetDocsMatchAvrae(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.md'),
            tmp_path,
            collection.snippets[0]
        ),
    ]

    # When local files differ from avrae
    (tmp_path / 'API Collection Test' / 'snippets' / 'test123.snippet').write_text('modified')
    (tmp_path / 'API Collection Test' / 'snippets' / 'test123.md').write_text('modified')
    assert _compare_snippets(collection=collection, base_path=tmp_path) == [
        LocalSnippetDoesNotMatchAvrae(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.snippet'),
            tmp_path,
            collection.snippets[0]
        ),
        LocalSnippetDocsDoNotMatchAvrae(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.md'),
            tmp_path,
            collection.snippets[0]
        ),
    ]

    # When local files do not exist in avrae and avrae files do not exist locally
    (tmp_path / 'API Collection Test' / 'snippets' / 'new.snippet').write_text('new addition')
    (tmp_path / 'API Collection Test' / 'snippets' / 'test123.snippet').unlink()
    (tmp_path / 'API Collection Test' / 'snippets' / 'test123.md').unlink()
    assert _compare_snippets(collection=collection, base_path=tmp_path) == [
        LocalSnippetMissing(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.snippet'),
            tmp_path,
            collection.snippets[0]
        ),
        LocalSnippetDocsMissing(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.md'),
            tmp_path,
            collection.snippets[0]
        ),
        LocalSnippetNotFoundInAvrae(
            (tmp_path / 'API Collection Test' / 'snippets' / 'new.snippet'),
            tmp_path,
        ),
    ]


def test_compare_gvars(tmp_path):
    (tmp_path / 'up-to-date.gvar').write_text('gvar content')
    (tmp_path / 'gvars').mkdir()
    (tmp_path / 'gvars' / 'modified-var.gvar').write_text('more gvar content')
    (tmp_path / 'gvars' / 'new-var.gvar').write_text('more gvar content')

    config = {
        "abc123": "up-to-date.gvar",
        "def456": "gvars/modified-var.gvar",
        "cba789": "gvars/new-var.gvar",
        "fed321": "gvars/not-found.gvar",
    }

    gvars = [
        Gvar(owner='999', key='abc123', owner_name='my name',
             value='gvar content', editors=[]),
        Gvar(owner='999', key='def456', owner_name='my name',
             value='current gvar content', editors=[]),
        Gvar(owner='999', key='fed321', owner_name='my name',
             value='current gvar content', editors=[]),
    ]

    comparison = _compare_gvars(gvars=gvars, config=config, base_path=tmp_path)
    assert comparison == [
        LocalGvarMatchesAvrae(
            (tmp_path / 'up-to-date.gvar'),
            tmp_path,
            gvars[0]
        ),
        LocalGvarDoesNotMatchAvrae(
            (tmp_path / 'gvars' / 'modified-var.gvar'),
            tmp_path,
            gvars[1]
        ),
        LocalGvarNotFoundInAvrae(
            (tmp_path / 'gvars' / 'new-var.gvar'),
            tmp_path,
        ),
        LocalGvarMissing(
            (tmp_path / 'gvars' / 'not-found.gvar'),
            tmp_path,
            gvars[2]
        ),
    ]

# ComparisonResults

# Aliases

def test_local_alias_not_found_in_avrae(tmp_path):
    alias_path = tmp_path / 'test.alias'
    result = LocalAliasNotFoundInAvrae(
        alias_path,
        tmp_path,
    )
    assert 'test.alias does not exist in Avrae.' in result.summary()

def test_local_alias_matches_avrae(tmp_path):
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
    alias_path = tmp_path / 'test-alias.alias'
    result = LocalAliasMatchesAvrae(
        alias_path,
        tmp_path,
        alias
    )
    assert 'test-alias.alias matches Avrae.' in result.summary()

def test_local_alias_docs_match_avrae(tmp_path):
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
    docs_path = tmp_path / 'test-alias.md'
    result = LocalAliasDocsMatchAvrae(
        docs_path,
        tmp_path,
        alias
    )
    assert 'test-alias.md matches Avrae.' in result.summary()

def test_local_alias_missing(tmp_path):
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
    alias_path = tmp_path / 'test-alias.alias'
    result = LocalAliasMissing(
        alias_path,
        tmp_path,
        alias
    )
    assert 'test-alias(a11a5) has no matching .alias file' in result.summary()

    assert not os.path.exists(alias_path)
    result.apply()
    assert os.path.exists(alias_path)
    with open(alias_path, mode='r', encoding='utf-8') as alias_file:
        assert alias_file.read() == alias.code

def test_local_alias_docs_missing(tmp_path):
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
    docs_path = tmp_path / 'test-alias.md'
    result = LocalAliasDocsMissing(
        docs_path,
        tmp_path,
        alias
    )
    assert 'test-alias(a11a5) has no matching .md file' in result.summary()

    assert not os.path.exists(docs_path)
    result.apply()
    assert os.path.exists(docs_path)
    with open(docs_path, mode='r', encoding='utf-8') as alias_file:
        assert alias_file.read() == alias.docs

def test_local_alias_does_not_match_avrae(tmp_path):
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
    alias_path = tmp_path / 'test-alias.alias'
    alias_path.write_text('new code')

    result = LocalAliasDoesNotMatchAvrae(
        alias_path,
        tmp_path,
        alias
    )
    assert 'test-alias.alias does not match the active version of test-alias(a11a5)' \
        in result.summary()
    assert '\n'.join(['- current code', '+ new code']) == result.diff()

    # When local changes have introduced new code
    client = Mock(AvraeClient)
    client.recent_matching_version.return_value = None
    client.create_new_code_version.return_value = CodeVersion(
        version=2, content=alias.code, created_at='', is_current=True
    )
    result.apply(client)
    client.create_new_code_version.assert_called_once_with(item=alias, code='new code')
    client.set_active_code_version.assert_called_once_with(item=alias, version=2)

    # When avrae has been rolled back
    client = Mock(AvraeClient)
    client.recent_matching_version.return_value = CodeVersion(
        content='new code',
        version=1,
        is_current=True,
        created_at='2022-12-14T20:27:00.000000Z')
    result.apply(client)
    client.create_new_code_version.assert_not_called()

def test_local_alias_docs_do_not_match_avrae(tmp_path):
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
    docs_path = tmp_path / 'test-alias.md'
    docs_path.write_text('new docs')

    result = LocalAliasDocsDoNotMatchAvrae(
        docs_path,
        tmp_path,
        alias
    )
    assert 'test-alias.md does not match the current docs for test-alias(a11a5)' in result.summary()
    assert '\n'.join(['- docs', '+ new docs']) == result.diff()

    client = Mock(AvraeClient)
    result.apply(client)
    client.update_docs.assert_called_once_with(item=alias, yaml='new docs')

# Snippets

def test_local_snippet_not_found_in_avrae(tmp_path):
    snippet_path = tmp_path / 'test.snippet'
    result = LocalSnippetNotFoundInAvrae(
        snippet_path,
        tmp_path,
    )
    assert 'test.snippet does not exist in Avrae.' in result.summary()

def test_local_snippet_matches_avrae(tmp_path):
    snippet = Snippet(
        name="test",
        code="snippet code",
        collection_id='c011ec7104',
        id='54177e7',
        docs="docs",
        versions=[],
        entitlements=[],
    )
    snippet_path = tmp_path / 'test.snippet'
    result = LocalSnippetMatchesAvrae(
        snippet_path,
        tmp_path,
        snippet
    )
    assert 'test.snippet matches Avrae.' in result.summary()

def test_local_snippet_docs_match_avrae(tmp_path):
    snippet = Snippet(
        name="test",
        code="snippet code",
        collection_id='c011ec7104',
        id='54177e7',
        docs="docs",
        versions=[],
        entitlements=[],
    )
    snippet_path = tmp_path / 'test.md'
    result = LocalSnippetDocsMatchAvrae(
        snippet_path,
        tmp_path,
        snippet
    )
    assert 'test.md matches Avrae.' in result.summary()

def test_local_snippet_missing(tmp_path):
    snippet = Snippet(
        name="test",
        code="snippet code",
        collection_id='c011ec7104',
        id='54177e7',
        docs="docs",
        versions=[],
        entitlements=[],
    )
    snippet_path = tmp_path / 'test.snippet'
    result = LocalSnippetMissing(
        snippet_path,
        tmp_path,
        snippet
    )
    assert 'test(54177e7) has no matching .snippet file' in result.summary()

    assert not os.path.exists(snippet_path)
    result.apply()
    assert os.path.exists(snippet_path)
    with open(snippet_path, mode='r', encoding='utf-8') as alias_file:
        assert alias_file.read() == snippet.code

def test_local_snippet_docs_missing(tmp_path):
    snippet = Snippet(
        name="test",
        code="snippet code",
        collection_id='c011ec7104',
        id='54177e7',
        docs="docs",
        versions=[],
        entitlements=[],
    )
    docs_path = tmp_path / 'test.md'
    result = LocalSnippetDocsMissing(
        docs_path,
        tmp_path,
        snippet
    )
    assert 'test(54177e7) has no matching .md file' in result.summary()

    assert not os.path.exists(docs_path)
    result.apply()
    assert os.path.exists(docs_path)
    with open(docs_path, mode='r', encoding='utf-8') as alias_file:
        assert alias_file.read() == snippet.docs

def test_local_snippet_does_not_match_avrae(tmp_path):
    snippet = Snippet(
        name="test",
        code="snippet code",
        collection_id='c011ec7104',
        id='54177e7',
        docs="docs",
        versions=[],
        entitlements=[],
    )
    snippet_path = tmp_path / 'test.snippet'
    snippet_path.write_text('new code')

    result = LocalSnippetDoesNotMatchAvrae(
        snippet_path,
        tmp_path,
        snippet
    )
    assert 'test.snippet does not match the active version of test(54177e7)' \
        in result.summary()
    assert '\n'.join(['- snippet code', '+ new code']) == result.diff()

    # When local changes have introduced new code
    client = Mock(AvraeClient)
    client.recent_matching_version.return_value = None
    client.create_new_code_version.return_value = CodeVersion(
        version=2, content=snippet.code, created_at='', is_current=True
    )
    result.apply(client)
    client.create_new_code_version.assert_called_once_with(item=snippet, code='new code')
    client.set_active_code_version.assert_called_once_with(item=snippet, version=2)

    # When avrae has been rolled back
    client = Mock(AvraeClient)
    client.recent_matching_version.return_value = CodeVersion(
        content='new code',
        version=1,
        is_current=True,
        created_at='2022-12-14T20:27:00.000000Z')
    result.apply(client)
    client.create_new_code_version.assert_not_called()

def test_local_snippet_docs_do_not_match_avrae(tmp_path):
    snippet = Snippet(
        name="test",
        code="snippet code",
        collection_id='c011ec7104',
        id='54177e7',
        docs="docs",
        versions=[],
        entitlements=[],
    )
    docs_path = tmp_path / 'test.md'
    docs_path.write_text('new docs')

    result = LocalSnippetDocsDoNotMatchAvrae(
        docs_path,
        tmp_path,
        snippet
    )
    assert 'test.md does not match the current docs for test(54177e7)' in result.summary()
    assert '\n'.join(['- docs', '+ new docs']) == result.diff()

    client = Mock(AvraeClient)
    result.apply(client)
    client.update_docs.assert_called_once_with(item=snippet, yaml='new docs')

# Gvars

def test_local_gvar_not_found_in_avrae(tmp_path):
    gvar_path = tmp_path / 'test.gvar'
    result = LocalGvarNotFoundInAvrae(
        gvar_path,
        tmp_path,
    )
    assert 'test.gvar is not mapped to an existing gvar in Avrae.' in result.summary()

def test_local_gvar_matches_avrae(tmp_path):
    gvar = Gvar(
        owner='1234',
        key='123abc',
        owner_name='someone',
        value='gvar code',
        editors=[]
    )
    gvar_path = tmp_path / 'test.gvar'
    result = LocalGvarMatchesAvrae(
        gvar_path,
        tmp_path,
        gvar
    )
    assert 'test.gvar matches 123abc in Avrae.' in result.summary()

def test_local_gvar_missing(tmp_path):
    gvar = Gvar(
        owner='1234',
        key='123abc',
        owner_name='someone',
        value='gvar code',
        editors=[]
    )
    gvar_path = tmp_path / 'test.gvar'
    result = LocalGvarMissing(
        gvar_path,
        tmp_path,
        gvar
    )
    assert 'Gvar 123abc has no matching .gvar file' in result.summary()

    assert not os.path.exists(gvar_path)
    result.apply()
    assert os.path.exists(gvar_path)
    with open(gvar_path, mode='r', encoding='utf-8') as gvar_file:
        assert gvar_file.read() == gvar.value


def test_local_gvar_does_not_match_avrae(tmp_path):
    gvar = Gvar(
        owner='1234',
        key='123abc',
        owner_name='someone',
        value='gvar code',
        editors=[]
    )
    gvar_path = tmp_path / 'test.gvar'
    gvar_path.write_text('new gvar code')
    result = LocalGvarDoesNotMatchAvrae(
        gvar_path,
        tmp_path,
        gvar
    )
    assert 'test.gvar does not match 123abc in Avrae' in result.summary()
    assert '\n'.join(['- gvar code', '+ new gvar code', '? ++++\n']) == result.diff()

    client = Mock(AvraeClient)
    result.apply(client)
    client.update_gvar.assert_called_once_with(gvar=gvar, value='new gvar code')
