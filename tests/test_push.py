"""
Tests for push.py
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from pytest import CaptureFixture
from autoupdate.avrae import Alias, AvraeClient, Collection, Gvar, Snippet
from autoupdate.push import push

def test_push(tmp_path: Path, capsys: CaptureFixture[Any]):
    (tmp_path / 'gvars.json').write_text(json.dumps({
        'gvar1': 'gvars/modified.gvar',
        'gvar2': 'gvars/unchanged.gvar',
        'gvar3': 'gvars/new.gvar',
    }))

    (tmp_path / 'collections.json').write_text(json.dumps({
        'collection1': 'some collection',
        'collection2': 'new collection',
    }))

    with patch('autoupdate.push.AvraeClient', autospec=True) as mock_client_class:
        mock_client = Mock(AvraeClient)
        mock_client.get_collections.return_value = [
            Collection(
                name='some collection',
                description='a test collection',
                image=None,
                owner='me',
                alias_ids=['alias1', 'alias2'],
                snippet_ids=['snippet1', 'snippet2'],
                publish_state='private',
                num_subscribers=0,
                num_guild_subscribers=0,
                last_edited='2022-01-01T01:00:00.000000Z',
                created_at='2022-01-01T01:00:00.000000Z',
                tags=[],
                id='collection1',
                aliases=[
                    Alias(
                        name='Alias 1',
                        code='echo 1',
                        versions=[],
                        docs='one',
                        entitlements=[],
                        collection_id='collection1',
                        id='alias1',
                        subcommand_ids=[],
                        parent_id=None,
                        subcommands=[],
                    ),
                    Alias(
                        name='Alias 2',
                        code='echo 2',
                        versions=[],
                        docs='two',
                        entitlements=[],
                        collection_id='collection1',
                        id='alias2',
                        subcommand_ids=[],
                        parent_id=None,
                        subcommands=[],
                    ),
                ],
                snippets=[
                    Snippet(
                        name='Snippet 1',
                        code='echo snippet 1',
                        versions=[],
                        docs='snippet one',
                        entitlements=[],
                        collection_id='collection1',
                        id='alias1',
                    ),
                    Snippet(
                        name='Snippet 2',
                        code='echo snippet 2',
                        versions=[],
                        docs='snippet two',
                        entitlements=[],
                        collection_id='collection1',
                        id='alias2',
                    )
                ],
            ),
        ]
        mock_client.recent_matching_version.return_value = None
        mock_client.get_gvars.return_value = [
            Gvar(
                owner='me',
                key='gvar1',
                owner_name='me',
                value='gvar code 1',
                editors=[],
            ),
            Gvar(
                owner='me',
                key='gvar2',
                owner_name='me',
                value='gvar code 2',
                editors=[],
            ),
        ]
        mock_client_class.return_value = mock_client

        alias1_dir = (tmp_path / 'some collection' / 'Alias 1')
        alias1_dir.mkdir(parents=True)
        (alias1_dir / 'Alias 1.alias').write_text('echo 1')
        (alias1_dir / 'Alias 1.md').write_text('one')

        alias2_dir = (tmp_path / 'some collection' / 'Alias 2')
        alias2_dir.mkdir(parents=True)
        (alias2_dir / 'Alias 2.alias').write_text('modified')
        (alias2_dir / 'Alias 2.md').write_text('modified')

        alias3_dir = (tmp_path / 'some collection' / 'Alias 3')
        alias3_dir.mkdir(parents=True)
        (alias3_dir / 'Alias 3.alias').write_text('new')
        (alias3_dir / 'Alias 3.md').write_text('new')

        snippets_dir = (tmp_path / 'some collection' / 'snippets')
        snippets_dir.mkdir(parents=True)
        (snippets_dir / 'Snippet 1.snippet').write_text('echo snippet 1')
        (snippets_dir / 'Snippet 1.md').write_text('snippet one')

        (snippets_dir / 'Snippet 2.snippet').write_text('modified')
        (snippets_dir / 'Snippet 2.md').write_text('modified')

        (snippets_dir / 'Snippet 3.snippet').write_text('new')
        (snippets_dir / 'Snippet 3.md').write_text('new')

        gvars_dir = (tmp_path / 'gvars')
        gvars_dir.mkdir(parents=True)
        (gvars_dir / 'modified.gvar').write_text('modified')
        (gvars_dir / 'unchanged.gvar').write_text('gvar code 2')
        (gvars_dir / 'new.gvar').write_text('new var')

        exit_code = push(
            repo_base_path=tmp_path,
            gvar_config_relative_path=Path('gvars.json'),
            collections_config_relative_path=Path('collections.json'),
            api_key='abc123'
        )

        captured = capsys.readouterr()
        assert captured.err == ""
        assert exit_code == 0
        mock_client.create_new_code_version.assert_called()
        mock_client.set_active_code_version.assert_called()
        mock_client.update_docs.assert_called()
