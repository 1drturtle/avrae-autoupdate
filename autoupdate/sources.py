import os
import pathlib

def contains_ending(files, endings):
    return any([file.endswith(endings) for file in files])

def scan_directories(scan_path: str, to_scan=None):
    cwd = scan_path or os.getcwd()
    active_dirs = []
    for dirpath, dirnames, filenames in os.walk(cwd):
        if not contains_ending(filenames, ('alias', 'snippet', 'gvar')):
            continue
        shared = os.path.commonprefix([dirpath, cwd])
        dirname = os.path.relpath(dirpath, shared).replace('\\', '/')
        if to_scan:
            if dirname in to_scan:
                active_dirs.append(dirname)
        else:
            active_dirs.append(dirname)
    return active_dirs

def files_in_actives(scan_path, modified):
    cwd = scan_path or os.getcwd()
    files = []
    for dirpath, dirnames, filenames in os.walk(cwd):
        for file in filenames:
            relative = os.path.join(os.path.relpath(dirpath, cwd), file)
            if '\\' in relative:
                relative = pathlib.PureWindowsPath(relative)
            else:
                relative = pathlib.PurePosixPath(relative)
            path = relative.as_posix()
            if path in modified:
                files.append(path)
    return files

