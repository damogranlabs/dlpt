"""
Functions for common path, file and directory manipulation.
"""
import errno
import os
import pathlib
import shutil
import stat
import time
import webbrowser
from typing import Optional, List

import dlpt


FILE_DIR_REMOVE_RETRY_DELAY_SEC = 0.5


class ChangeDir:
    def __init__(self, path: str):
        """Temporary change working directory of a block of code and revert to
        an original on exit.

        Args:
            path: path to an existing local directory/file that is
                temporary set as working directory. If file path is given,
                its directory is taken as new temporary working dir.

        Example:
            >>> with dlpt.pth.ChangeDir("C:/somePath"):
                    func("that does something in CWD")
        """
        self.path = resolve(path)
        self.original_wd = os.getcwd()

        if os.path.isfile(self.path):
            self.path = os.path.dirname(self.path)
        check(self.path)

    def __enter__(self):
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.original_wd)


def check(path: Optional[str]) -> str:
    """Check if given path exists and return normalized path.

    Note:
        Use standard ``os.path.exists()`` if you don't want to raise exception.

    Args:
        path: path to check

    Returns:
        Normalized path (if valid) or raise exception.
    """
    path = _validate_path(path)

    if os.path.exists(path):
        return os.path.normpath(path)

    caller_location = dlpt.utils.get_caller_location()
    err_msg = f"Path does not exist: {path}\n\t{caller_location}"
    raise FileNotFoundError(err_msg)


def resolve(path: str) -> str:
    """Resolve path with pathlib module. This will (for existing files) fix any
    case mismatch, for example, drive letter.

    Args:
        path: abs path to resolve

    Returns:
        Resolved path according to the OS.
    """
    return str(pathlib.Path(path).resolve())


def _set_w_permissions(path: str):
    """Set file/directory write permmissions.

    Args:
        path: absolute path to a file/directory to modify permissions.
    """
    os.chmod(path, stat.S_IWRITE)
    if not os.access(path, os.W_OK):  # pragma no cover
        err_msg = f"Unable to modify write permission of a given path: {path}"
        raise Exception(err_msg)


def copy_file(src_file_path: str, dst_dir_path: str, dst_file_name: Optional[str] = None) -> str:
    """Copy given file to a new location, while dstFile is removed prior
    copying. Any intermediate directories are created automatically.

    Args:
        src_file_path: path to a file to be copied.
        dst_dir_path: absolute destination directory path.
        dst_file_name: new destination file name. If None, original file
            name is used.

    Returns:
        A path to a copied file.
    """
    src_file_path = check(src_file_path)
    if not os.path.isfile(src_file_path):
        err_msg = f"'copy_file()' is designed to copy files, "
        err_msg += f"not directories/links: {src_file_path}"
        raise ValueError(err_msg)

    if dst_file_name is None:
        dst_file_name = get_name(src_file_path)
    dst_file_path = os.path.normpath(os.path.join(dst_dir_path, dst_file_name))

    create_dir(dst_dir_path)
    remove_file(dst_file_path)
    shutil.copyfile(src_file_path, dst_file_path)

    return dst_file_path


def copy_dir(src_dir_path: str, dst_dir_path: str) -> str:
    """Copy given directory to a new location, while `dst_dir_path` is removed
    prior copying. Any intermediate directories are created automatically.

    Args:
        src_dir_path: path to a file to be copied.
        dst_dir_path: new destination path.

    Returns:
        A path to a copied directory.
    """
    src_dir_path = check(src_dir_path)
    if not os.path.isdir(src_dir_path):
        err_msg = "'copy_dir()' is designed to copy directories, "
        err_msg += f"not files/links: {src_dir_path}"
        raise ValueError(err_msg)

    _validate_path(dst_dir_path)
    dst_dir_path = os.path.normpath(dst_dir_path)
    remove_dir_tree(dst_dir_path)

    shutil.copytree(src_dir_path, dst_dir_path)

    return dst_dir_path


def remove_file(file_path: str, force_write_permissions: bool = True, retry: int = 3):
    """This function tries to remove file (FILE, not DIRECTORY) on a given path.
    Optionally, write permissions are set to a file.

    Args:
        file_path: path to a file.
        force_write_permissions: if True, write permissions are set to
            a file so it can be removed.
        retry: on failure, retry removal specified number of times.
    """
    _validate_path(file_path)

    if os.path.exists(file_path):
        if not os.path.isfile(file_path):
            err_msg = "Function 'remove_file()' is designed to remove files, "
            err_msg += f"not directories/links: {file_path}"
            raise ValueError(err_msg)

        take = 0
        for take in range(retry):
            try:
                if force_write_permissions:
                    _set_w_permissions(file_path)
                # else: don't force it, see what will happen - don't care
                # about the consequences. Might raise an exception.
                os.unlink(file_path)
            except Exception as err:
                time.sleep(FILE_DIR_REMOVE_RETRY_DELAY_SEC)
            else:
                break  # on success, escape retrying
        else:
            err_msg = f"Unable to 'remove_file()' after {take+1} times: {file_path}"
            raise Exception(err_msg)


def _on_remove_dir_err(function, path, exception):  # pragma: no cover
    """This is a private function, which is called on shutil.rmtree() exception.
    If exception cause was permission error, write permissions are added,
    otherwise exception is re-raised.
    For arguments, see ``shutil.rmtree()`` docs.
    """
    excvalue = exception[1]
    if excvalue.errno == errno.EACCES:
        _set_w_permissions(path)
        function(path)
    else:  # pragma: no cover
        # re-raise exception (this function is exception callback)
        raise  # type: ignore


def remove_dir_tree(dir_path: str, force_write_permissions: bool = True, retry: int = 3):
    """Remove directory (DIRECTORY, not FILE) and all its content on a given path.

    Args:
        dir_path: path of a directory to remove.
        force_write_permissions: if True, shutil.rmtree() error callback
            function is used to change permissions and retry.
        retry: on failure, retry removal specified number of times. Must be > 0.
            Sometimes file are locked with other processes, or a race
            condition occurred.
    """
    _validate_path(dir_path)

    if os.path.exists(dir_path):
        if not os.path.isdir(dir_path):
            err_msg = f"'remove_dir_tree()' is designed to remove directories, not files/links: {dir_path}"
            raise ValueError(err_msg)

        take = 0
        for take in range(retry):
            try:
                if force_write_permissions:
                    shutil.rmtree(dir_path, ignore_errors=False, onerror=_on_remove_dir_err)
                else:
                    shutil.rmtree(dir_path)
            except Exception as err:
                if take < (retry - 1):
                    time.sleep(FILE_DIR_REMOVE_RETRY_DELAY_SEC)
            else:
                break  # on success, escape retrying
        else:
            err_msg = f"Unable to 'remove_dir_tree()' after {take} times: {dir_path}"
            raise Exception(err_msg)


def clean_dir(dir_path: str, force_write_permissions: bool = True):
    """Delete all directory content (files, sub-dirs) in a given directory, but
    not the root directory itself.

    Args:
        dir_path: path to a directory to clean all its content
        force_write_permissions: if True, write permissions are set to be
            able to delete files.
    """
    _validate_path(dir_path)

    items = os.listdir(dir_path)
    for item in items:
        item_path = os.path.join(dir_path, item)
        if os.path.isfile(item_path):
            remove_file(item_path, force_write_permissions)
        else:
            remove_dir_tree(item_path, force_write_permissions)


def create_dir(dir_path: str):
    """Create directory (or directory tree) on a given specified path.

    Args:
        dir_path: absolute path of a directory to create
    """
    _validate_path(dir_path)

    dir_path = os.path.normpath(dir_path)
    os.makedirs(dir_path, exist_ok=True)


def create_clean_dir(dir_path: str):
    """Create new or clean existing directory on a given specified path.
    Path existence is checked with check() at the end.

    Args:
        dir_path: absolute path of a directory to create
    """
    _validate_path(dir_path)

    if os.path.exists(dir_path):
        clean_dir(dir_path)
    else:
        create_dir(dir_path)


def remove_old_items(dir_path: str, days: int) -> List[str]:
    """Remove items (files, directories) inside the given directory that were
    modified more than specified number of days ago.

    Note:
        modification time and current time can be the same when this
        function is called after creation. Hence, decimal
        part (milliseconds) of current/modification timestamp is discarded.

    Args:
        dir_path: path to a directory with files/directories to remove.
        days: number of days file/directory must be old to be
            removed (last modification time).

    Returns:
        A list of removed items.
    """
    dir_path = check(dir_path)

    removed_items: List[str] = []
    days_in_seconds = dlpt.time.time_to_seconds(d=days)
    current_time = int(time.time())  # see note about int()
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        last_mod_time = int(os.path.getmtime(item_path))  # see note about int()
        if last_mod_time < (current_time - days_in_seconds):
            if os.path.isfile(item_path):
                remove_file(item_path)
            else:
                remove_dir_tree(item_path)
            removed_items.append(item_path)

    return removed_items


def with_fw_slashes(path: str) -> str:
    """Convert path to use forward slashes.

    Note:
        This function does not do ``os.path.normpath()`` so it is also
        usable for UNCs.

    Args:
        path: path to convert

    Returns:
        A path with converted back slashes to forward slashes.
    """
    _validate_path(path)

    return path.replace("\\", "/")


def with_double_bw_slashes(path: str) -> str:
    """Convert and return path to use double back slashes.

    Args:
        path: path to convert

    Returns:
        A converted path with double back slashes.
    """
    path = _validate_path(path)

    return path.replace("\\", "\\\\")


def get_name(file_path: str, with_ext: bool = True) -> str:
    """Return a file name from file path or raise exception.

    Note:
        No file existence check is performed.

    Args:
        file_path: file path where file name will be fetched from
        with_ext: if False, extension is striped from file name

    Returns:
        A file name with/without extension.
    """
    _validate_path(file_path)

    file_name = os.path.basename(file_path)
    ext = get_ext(file_path)

    if not with_ext:
        file_name = file_name.replace(ext, "")

    return file_name


def get_ext(file_path: str) -> str:
    """Return file extension (with dot) from file path or raise exception.

    Note:
        No file existence check is performed.

    Args:
        file_path: file path where file name will be fetched from

    Returns:
        A file extension.
    """
    _validate_path(file_path)

    return os.path.splitext(file_path)[1]


def get_files_in_dir(
    dir_path: str, include_ext: Optional[List[str]] = None, exclude_ext: Optional[List[str]] = None
) -> List[str]:
    """Get a list of files in a given ``dir_path``.
    If ``extensionFilter`` is set, only return files that has the same extension.

    Note:
        Only one of ``include_ext`` or ``exclude_ext`` must be set, or exception
        is raised. Lower case extension strings are compared.

    Args:
        dir_path: path to a directory to scan.
        include_ext: if set, only files with given extension(s) are returned.
        exclude_ext: if set, files with given extension(s) are excluded
            from return list.

    Returns:
        List of matching files from `dir_path``.
    """
    _validate_path(dir_path)
    check(dir_path)
    dir_path = os.path.normpath(dir_path)

    if include_ext and exclude_ext:
        err_msg = "Set only 'include_ext' or 'exclude_ext', not both!"
        raise Exception(err_msg)

    _include_filter: List[str] = []
    if include_ext:
        for ext in include_ext:
            _include_filter.append(ext.lower())
    _exclude_filter: List[str] = []
    if exclude_ext:
        for ext in exclude_ext:
            _exclude_filter.append(ext.lower())

    files = []
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        if os.path.isfile(item_path):
            _, ext = os.path.splitext(item)
            ext = ext.lower()

            if exclude_ext:
                if ext in _exclude_filter:
                    continue

            if include_ext:
                if ext in _include_filter:
                    files.append(item_path)
            else:
                files.append(item_path)

    return files


def get_files_in_dir_tree(
    dir_tree_path: str, include_ext: Optional[List[str]] = None, exclude_ext: Optional[List[str]] = None
) -> List[str]:
    """Same as :func:`get_files_in_dir()`, but scan through all files in
    all directories.

    Note:
        Only one of ``include_ext`` or ``exclude_ext`` must be set, or exception
        is raised. Lower case extension strings are compared.

    Args:
        dir_tree_path: path to a directory tree to scan.
        include_ext: if set, only files with given extension(s) are returned.
        exclude_ext: if set, files with given extension(s) are excluded
            from return list.

    Returns:
        List of matching files from `dir_path`` and all its sub-directories.
    """
    dir_tree_path = check(dir_tree_path)

    all_files = []
    for (root_dir_path, _, _) in os.walk(dir_tree_path):
        this_dir_files = get_files_in_dir(root_dir_path, include_ext, exclude_ext)
        all_files.extend(this_dir_files)

    return all_files


def get_dirs_in_dir(dir_path: str, name_filter: Optional[str] = None, case_insensitive: bool = True) -> List[str]:
    """Get a list of directories in a given 'dir_path'.

    Args:
        dir_path: path to a directory to scan.
        name_filter: if set, directories that contain this string are returned,
            based on `case_insensitive` setting.
        case_insensitive: if True, lower-cased name_filter string (if set)
            is checked in lower case directory name.

    Returns:
        List of matching directories from `dir_path``.
    """
    _validate_path(dir_path)
    check(dir_path)
    dir_path = os.path.normpath(dir_path)

    if name_filter is not None:
        if case_insensitive:
            name_filter = name_filter.lower()

    dirs = []
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        if os.path.isdir(item_path):
            if name_filter is None:
                dirs.append(item_path)
            else:  # name filtering is in place
                if case_insensitive:
                    if name_filter in item.lower():
                        dirs.append(item_path)
                else:
                    if name_filter in item:
                        dirs.append(item_path)

    return dirs


def open_in_web_browser(url: str):  # pragma: no cover
    """Open given address in a default web browser as a non-blocking subprocess.

    Args:
        url: web address to open.
    """
    webbrowser.open(url, new=2)  # 2 = new tab


def open_with_default_app(file_path: str):  # pragma: no cover
    """Open given file with OS default application as a non-blocking subprocess.

    Args:
        file_path: path to a file to open.
    """
    file_path = check(file_path)
    file_path = f'"{file_path}"'

    if os.name == "nt":
        # Windows
        os.startfile(file_path)
    else:
        # MacOS/X # NOTE: not tested!
        os.popen(f"open {file_path}")


def _validate_path(path: Optional[str]) -> str:
    """Raise exception if given path is not a string or it is an empty string.

    Args:
        path: path to check.

    Returns:
        Given path.
    """
    if isinstance(path, str):
        if path.strip() != "":
            return path
    elif isinstance(path, pathlib.Path):
        return path

    # 0 - current frame  of get_caller_location scope
    # 1 - frame of this _validate_path()
    # 2 - frame of the caller of this function (_validate_path() is a
    #   private function, should be only used inside pth.py)
    # 3 - frame of the caller of a function in paths, that further called
    # _validate_path() func
    caller_location = dlpt.utils.get_caller_location(3)
    err_msg = f"Invalid path format - expected non-empty string: '{path}'\n\t{caller_location}"
    raise ValueError(err_msg)
