from autoupdate.sources import (
    files_in_actives,
    scan_directories
)

def test_scan_directories(tmp_path):
    FILE_CONTENTS = {
        'test.alias': 'alias',
        'test.txt': 'text',
        'test': 'anything',
        'test.gvar': 'gvar',
        'test.snippet': 'snippet',
        'test.md': 'markdown',
    }

    # directories containing all example files
    for dir_name in ['collection', 'not a collection']:
        current_path = tmp_path / dir_name
        current_path.mkdir()
        for (file_name, contents) in FILE_CONTENTS.items():
            (current_path / file_name).write_text(contents)

    # directories containing each example file in isolation
    collections = { 'collection': 'collection id'}
    for (file_name, contents) in FILE_CONTENTS.items():
        collection_name = f'{file_name} only collection'
        current_path = tmp_path / collection_name
        current_path.mkdir()
        (current_path / file_name).write_text(contents)
        collections[collection_name] = f'{collection_name} id'

    source_dirs = scan_directories(scan_path=tmp_path, to_scan=collections)
    assert sorted(source_dirs) == sorted([
        'collection',
        'test.alias only collection',
        'test.gvar only collection',
        'test.snippet only collection',
    ])

def test_files_in_actives(tmp_path):
    (tmp_path / 'file').write_text('file')
    (tmp_path / 'modified_file').write_text('file')
    (tmp_path / 'subdir').mkdir()
    (tmp_path / 'subdir' / 'file').write_text('file')
    (tmp_path / 'subdir' / 'modified_file').write_text('file')
    files = files_in_actives(tmp_path, modified=[
        'modified_file', 'subdir/modified_file', 'deleted_file'
    ])
    assert sorted(files) == sorted(['modified_file', 'subdir/modified_file'])
