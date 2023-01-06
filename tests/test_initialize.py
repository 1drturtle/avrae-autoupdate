"""
Tests for initialize.py
"""

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from pytest import CaptureFixture
from autoupdate.avrae import AvraeClient, Collection, Gvar

from autoupdate.initialize import initialize

def test_initialize(tmp_path: Path, capsys: CaptureFixture[Any]):

    with patch('autoupdate.initialize.AvraeClient', autospec=True) as mock_client_class:
        mock_client = Mock(AvraeClient)
        mock_client.get_collections.return_value = [
            Collection(
                name='some collection',
                description='a test collection',
                image=None,
                owner='me',
                alias_ids=[],
                snippet_ids=[],
                publish_state='private',
                num_subscribers=0,
                num_guild_subscribers=0,
                last_edited='2022-01-01T01:00:00.000000Z',
                created_at='2022-01-01T01:00:00.000000Z',
                tags=[],
                id='collection1',
                aliases=[],
                snippets=[],
            ),
        ]
        mock_client.get_owned_collection_ids.return_value = ['collection1']
        mock_client.get_editable_collection_ids.return_value = []
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

        exit_code = initialize(
            repo_base_path=tmp_path,
            gvar_config_relative_path=Path('gvars.json'),
            collections_config_relative_path=Path('collections.json'),
            api_key='abc123'
        )

        captured = capsys.readouterr()
        assert captured.err == ""
        assert exit_code == 0

    # creates gvars config
    assert os.path.exists(tmp_path / 'gvars.json')
    with open((tmp_path / 'gvars.json'), mode='r', encoding='utf-8') as config_file:
        assert json.load(config_file) == {
            'gvar1': 'gvars/gvar1.gvar',
            'gvar2': 'gvars/gvar2.gvar'
        }

    # creates collections config
    assert os.path.exists(tmp_path / 'collections.json')
    with open((tmp_path / 'collections.json'), mode='r', encoding='utf-8') as config_file:
        assert json.load(config_file) == {
            'collection1': 'some collection'
        }

def test_initialize_updates_existing_configs(tmp_path: Path, capsys: CaptureFixture[Any]):
    (tmp_path / 'gvars.json').write_text(json.dumps({
        'gvar1': 'old gvars/gvar1.gvar',
        'missing': 'gvars/missing.gvar'
    }))

    (tmp_path / 'collections.json').write_text(json.dumps({
        'collection1': 'some collection',
        'missing': 'missing collection'
    }))

    with patch('autoupdate.initialize.AvraeClient', autospec=True) as mock_client_class:
        mock_client = Mock(AvraeClient)
        mock_client.get_collections.return_value = [
            Collection(
                name='some collection',
                description='a test collection',
                image=None,
                owner='me',
                alias_ids=[],
                snippet_ids=[],
                publish_state='private',
                num_subscribers=0,
                num_guild_subscribers=0,
                last_edited='2022-01-01T01:00:00.000000Z',
                created_at='2022-01-01T01:00:00.000000Z',
                tags=[],
                id='collection1',
                aliases=[],
                snippets=[],
            ),
            Collection(
                name='some other collection',
                description='a second test collection',
                image=None,
                owner='me',
                alias_ids=[],
                snippet_ids=[],
                publish_state='private',
                num_subscribers=0,
                num_guild_subscribers=0,
                last_edited='2022-01-01T01:00:00.000000Z',
                created_at='2022-01-01T01:00:00.000000Z',
                tags=[],
                id='collection2',
                aliases=[],
                snippets=[],
            ),
        ]
        mock_client.get_owned_collection_ids.return_value = ['collection1']
        mock_client.get_editable_collection_ids.return_value = []
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

        exit_code = initialize(
            repo_base_path=tmp_path,
            gvar_config_relative_path=Path('gvars.json'),
            collections_config_relative_path=Path('collections.json'),
            api_key='abc123'
        )

        captured = capsys.readouterr()
        assert captured.err == ""
        assert exit_code == 0

    # creates gvars config
    assert os.path.exists(tmp_path / 'gvars.json')
    with open((tmp_path / 'gvars.json'), mode='r', encoding='utf-8') as config_file:
        assert json.load(config_file) == {
            'gvar1': 'old gvars/gvar1.gvar',
            'gvar2': 'gvars/gvar2.gvar',
            'missing': 'gvars/missing.gvar'
        }

    # creates collections config
    assert os.path.exists(tmp_path / 'collections.json')
    with open((tmp_path / 'collections.json'), mode='r', encoding='utf-8') as config_file:
        assert json.load(config_file) == {
            'collection1': 'some collection',
            'collection2': 'some other collection',
            'missing': 'missing collection'
        }
