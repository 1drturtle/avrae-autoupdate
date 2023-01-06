"""
Tests for pull.py
"""

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from pytest import CaptureFixture
from autoupdate.avrae import Alias, AvraeClient, Collection, Gvar, Snippet
from autoupdate.pull import pull

def test_pull(tmp_path: Path, capsys: CaptureFixture[Any]):
    (tmp_path / 'gvars.json').write_text(json.dumps({
        'gvar1': 'gvars/missing.gvar',
        'gvar2': 'gvars/outdated.gvar',
    }))

    (tmp_path / 'collections.json').write_text(json.dumps({
        'collection1': 'some collection',
    }))

    with patch('autoupdate.pull.AvraeClient', autospec=True) as mock_client_class:
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

        alias2_dir = (tmp_path / 'some collection' / 'Alias 2')
        alias2_dir.mkdir(parents=True)
        (alias2_dir / 'Alias 2.alias').write_text('old code')
        (alias2_dir / 'Alias 2.md').write_text('old docs')

        snippet2_dir = (tmp_path / 'some collection' / 'snippets')
        snippet2_dir.mkdir(parents=True)
        (snippet2_dir / 'Snippet 2.snippet').write_text('old code')
        (snippet2_dir / 'Snippet 2.md').write_text('old docs')

        gvars_dir = (tmp_path / 'gvars')
        gvars_dir.mkdir(parents=True)
        (gvars_dir / 'outdated.gvar').write_text('outdated')

        exit_code = pull(
            repo_base_path=tmp_path,
            gvar_config_relative_path=Path('gvars.json'),
            collections_config_relative_path=Path('collections.json'),
            api_key='abc123'
        )

        captured = capsys.readouterr()
        assert captured.err == ""
        assert exit_code == 0
        mock_client_class.assert_called_once()
        mock_client.get_gvars.assert_called_once()
        mock_client.get_collections.assert_called_once()

        # Creates missing alias and docs

        alias1_path = (tmp_path / 'some collection' / 'Alias 1' / 'Alias 1.alias')
        assert os.path.exists(alias1_path)
        with open(alias1_path, mode='r', encoding='utf-8') as alias_file:
            assert alias_file.read() == 'echo 1'

        alias1_docs_path = (tmp_path / 'some collection' / 'Alias 1' / 'Alias 1.md')
        assert os.path.exists(alias1_docs_path)
        with open(alias1_docs_path, mode='r', encoding='utf-8') as docs_file:
            assert docs_file.read() == 'one'

        # Creats missing snippet and docs

        snippet1_path = (tmp_path / 'some collection' / 'snippets' / 'Snippet 1.snippet')
        assert os.path.exists(snippet1_path)
        with open(snippet1_path, mode='r', encoding='utf-8') as snippet_file:
            assert snippet_file.read() == 'echo snippet 1'

        snippet1_docs_path = (tmp_path / 'some collection' / 'snippets' / 'Snippet 1.md')
        assert os.path.exists(snippet1_docs_path)
        with open(snippet1_docs_path, mode='r', encoding='utf-8') as snippet_docs_file:
            assert snippet_docs_file.read() == 'snippet one'

        # Creates missing gvar

        gvar_path = (tmp_path / 'gvars' / 'missing.gvar')
        assert os.path.exists(gvar_path)
        with open(gvar_path, mode='r', encoding='utf-8') as gvar_file:
            assert gvar_file.read() == 'gvar code 1'
