"""
Functions for common path, file and folder manipulation.
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


FILE_FOLDER_REMOVE_RETRY_DELAY_SEC = 0.5


class ChangeDir:
    def __init__(self, path: str):
        """ Temporary change working directory of a block of code and revert to 
        an original on exit.

        Args:
            path: path to an existing local folder/file that is
                temporary set as working directory. If file path is given,
                its folder is taken as new working dir folder.

        Example:
            >>> with dlpt.pth.ChangeDir("C:/somePath"):
                    answer = 42 # do stuff with cwd changed to "C:/somePath"
        """
        self.path = resolve(path)
        self.originalWd = os.getcwd()

        if os.path.isfile(self.path):
            self.path = os.path.dirname(self.path)
        check(self.path)

    def __enter__(self):
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.originalWd)


def check(path: Optional[str]) -> str:
    """ Check if given path exists and return normalized path. Return normalized
    path (if valid) or raise exception.

    Note:
        Use standard ``os.path.exists()`` if you don't want to raise exception.

    Args:
        path: path to check
    """
    path = _pathValidationCheck(path)

    if os.path.exists(path):
        return os.path.normpath(path)

    callerLocation = dlpt.utils.getCallerLocation()
    errorMsg = f"Path does not exist: {path}\n\t{callerLocation}"
    raise FileNotFoundError(errorMsg)


def resolve(path: str) -> str:
    """ Resolve path with pathlib module. This will (for existing files) fix any 
    case mismatch, for example, drive letter. Return resolved path.

    Args:
        path: abs path to resolve
    """
    return str(pathlib.Path(path).resolve())


def _setWritePermissions(path: str):
    """ Set file/folder write permmissions.

    Args:
        path: absolute path to a file/folder to modify permissions.
    """
    os.chmod(path, stat.S_IWRITE)
    if not os.access(path, os.W_OK):  # pragma no cover
        errorMsg = f"Unable to modify write permission of a given path: {path}"
        raise Exception(errorMsg)


def copyFile(srcFilePath: str, dstFolderPath: str, dstFileName: Optional[str] = None) -> str:
    """ Copy given file to a new location, while dstFile is removed prior 
    copying. Any intermediate folders are created automatically. Return path to 
    a copied file.

    Args:
        srcFilePath: path to a file to be copied.
        dstFolderPath: absolute destination folder path.
        dstFileName: new destination file name. If None, original file
            name is used.
    """
    srcFilePath = check(srcFilePath)
    if not os.path.isfile(srcFilePath):
        errorMsg = f"'copyFile()' is designed to copy files, not folders/links: {srcFilePath}"
        raise ValueError(errorMsg)

    if dstFileName is None:
        dstFileName = getName(srcFilePath)
    dstFilePath = os.path.normpath(os.path.join(dstFolderPath, dstFileName))

    createFolder(dstFolderPath)
    removeFile(dstFilePath)
    shutil.copyfile(srcFilePath, dstFilePath)

    return dstFilePath


def copyFolder(srcFolderPath: str, dstFolderPath: str) -> str:
    """ Copy given folder to a new location, while dstFolder is removed prior 
    copying. Any intermediate folders are created automatically. Return a path
    to a copied folder.

    Args:
        srcFolderPath: path to a file to be copied.
        dstFolderPath: new destination path.
    """
    srcFolderPath = check(srcFolderPath)
    if not os.path.isdir(srcFolderPath):
        errorMsg = f"'copyFolder()' is designed to copy folders, not files/links: {srcFolderPath}"
        raise ValueError(errorMsg)

    _pathValidationCheck(dstFolderPath)
    dstFolderPath = os.path.normpath(dstFolderPath)
    removeFolderTree(dstFolderPath)

    shutil.copytree(srcFolderPath, dstFolderPath)

    return dstFolderPath


def removeFile(fPath: str, forceWritePermissions: bool = True, retry: int = 3):
    """ This function tries to remove file (FILE, not FOLDER) on a given path. 
    Optionally, write permissions are set to a file.

    Args:
        fPath: path to a file.
        forceWritePermissions: if True, write permissions are set to
            a file so it can be removed.
        retry: on failure, retry removal specified number of times.
    """
    _pathValidationCheck(fPath)

    if os.path.exists(fPath):
        if not os.path.isfile(fPath):
            errorMsg = f"Function 'removeFile()' is designed to remove files, not folders/links: {fPath}"
            raise ValueError(errorMsg)

        take = 0
        for take in range(retry):
            try:
                if forceWritePermissions:
                    _setWritePermissions(fPath)
                # else: don't force it, see what will happen - don't care about the
                # consequences. Might raise an exception.
                os.unlink(fPath)
            except Exception as err:
                time.sleep(FILE_FOLDER_REMOVE_RETRY_DELAY_SEC)
            else:
                break  # on success, escape retrying
        else:
            errorMsg = f"Unable to 'removeFile()' after {take+1} times: {fPath}"
            raise Exception(errorMsg)


def _removeFolderErrorHandler(function, path, exception):  # pragma: no cover
    """ This is a private function, which is called on shutil.rmtree() exception.
    If exception cause was permission error, write permissions are added,
    otherwise exception is re-raised.
    For arguments, see ``shutil.rmtree()`` docs.
    """
    excvalue = exception[1]
    if excvalue.errno == errno.EACCES:
        _setWritePermissions(path)
        function(path)
    else:  # pragma: no cover
        # re-raise exception (this function is exception callback)
        raise  # type: ignore


def removeFolderTree(dirPath: str, forceWritePermissions: bool = True, retry: int = 3):
    """ Remove folder (FOLDER, not FILE) and all its content on a given path.

    Args:
        dirPath: path of a folder to remove.
        forceWritePermissions: if True, shutil.rmtree() error callback 
            function is used to change permissions and retry.
        retry: on failure, retry removal specified number of times. Must be > 0.
            Sometimes file are locked with other processes, or a race
            condition occurred.
    """
    _pathValidationCheck(dirPath)

    if os.path.exists(dirPath):
        if not os.path.isdir(dirPath):
            errorMsg = f"'removeFolderTree()' is designed to remove folders, not files/links: {dirPath}"
            raise ValueError(errorMsg)

        take = 0
        for take in range(retry):
            try:
                if forceWritePermissions:
                    shutil.rmtree(dirPath, ignore_errors=False, onerror=_removeFolderErrorHandler)
                else:
                    shutil.rmtree(dirPath)
            except Exception as err:
                if take < (retry - 1):
                    time.sleep(FILE_FOLDER_REMOVE_RETRY_DELAY_SEC)
            else:
                break  # on success, escape retrying
        else:
            errorMsg = f"Unable to 'removeFolderTree()' after {take} times: {dirPath}"
            raise Exception(errorMsg)


def cleanFolder(dirPath: str, forceWritePermissions: bool = True):
    """ Delete all folder content (files, sub-folders) in a given folder, but 
    not the root folder.

    Args:
        dirPath: path to a folder to clean all its content
        forceWritePermissions: if True, write permissions are set to be
            able to delete files.
    """
    _pathValidationCheck(dirPath)

    allItems = os.listdir(dirPath)
    for item in allItems:
        itemPath = os.path.join(dirPath, item)
        if os.path.isfile(itemPath):
            removeFile(itemPath, forceWritePermissions)
        else:
            removeFolderTree(itemPath, forceWritePermissions)


def createFolder(dirPath: str):
    """ Create folder (or folder tree) on a given specified path.

    Args:
        dirPath: absolute path of a folder to create
    """
    _pathValidationCheck(dirPath)

    dirPath = os.path.normpath(dirPath)
    os.makedirs(dirPath, exist_ok=True)


def createCleanFolder(dirPath: str):
    """ Create new or clean existing folder on a given specified path.
    Path existence is checked with check() at the end.

    Args:    
        dirPath: absolute path of a folder to create
    """
    _pathValidationCheck(dirPath)

    if os.path.exists(dirPath):
        cleanFolder(dirPath)
    else:
        createFolder(dirPath)


def removeOldItems(dirPath: str, days: int) -> List[str]:
    """ Remove items (files, folders) inside the given folder that were modified 
    more than specified number of days ago. Return a list of removed items.

    Note:
        modification time and current time can be the same when this
        function is called after creation. Hence, decimal
        part (milliseconds) of current/modification timestamp is discarded.

    Args:
        dirPath: path to a folder with files/folders to remove.
        days: number of days file/folder must be old to be 
            removed (last modification time).
    """
    dirPath = check(dirPath)

    removedItems: List[str] = []
    daysInSeconds = dlpt.time.timeToSeconds(d=days)
    currentTime = int(time.time())  # see note about int()
    for item in os.listdir(dirPath):
        itemPath = os.path.join(dirPath, item)
        lastModTime = int(os.path.getmtime(itemPath))  # see note about int()
        if lastModTime < (currentTime - daysInSeconds):
            if os.path.isfile(itemPath):
                removeFile(itemPath)
            else:
                removeFolderTree(itemPath)
            removedItems.append(itemPath)

    return removedItems


def withFwSlashes(path: str) -> str:
    """ Convert path to use forward slashes.

    Note: 
        This function does not do ``os.path.normpath()`` so it is also
        usable for UNCs.

    Args:
        path: path to convert
    """
    _pathValidationCheck(path)

    path = path.replace("\\", "/")

    return path


def withDoubleBwSlashes(path: str) -> str:
    """ Convert and return path to use double back slashes.

    Args:
        path: path to convert
    """
    path = _pathValidationCheck(path)

    path = path.replace("\\", "\\\\")

    return path


def getName(fPath: str, withExt: bool = True) -> str:
    """ Return a file name from file path or raise exception. 

    Note:
        No file existence check is performed.

    Args:
        fPath: file path where file name will be fetched from
        withExt: if False, extension is striped from file name

    """
    _pathValidationCheck(fPath)

    fileName = os.path.basename(fPath)
    ext = getExt(fPath)

    if not withExt:
        fileName = fileName.replace(ext, "")

    return fileName


def getExt(fPath: str) -> str:
    """ Return file extension (with dot) from file path or raise exception.

    Note:
        No file existence check is performed.

    Args:
        fPath: file path where file name will be fetched from
    """
    _pathValidationCheck(fPath)

    _, ext = os.path.splitext(fPath)

    return ext


def getFilesInFolder(dirPath: str,
                     includeExt: Optional[List[str]] = None,
                     excludeExt: Optional[List[str]] = None) -> List[str]:
    """ Get a list of files in a given ``dirPath``. 
    If ``extensionFilter`` is set, only return files that has the same extension.

    Note:
        Only one of ``includeExt`` or ``excludeExt`` must be set, or exception 
        is raised. Lower case extension strings are compared.

    Args:
        dirPath: path to a folder to scan.
        includeExt: if set, only files with given extension(s) are returned.
        excludeExt: if set, files with given extension(s) are excluded 
            from return list.
    """
    _pathValidationCheck(dirPath)
    check(dirPath)
    dirPath = os.path.normpath(dirPath)

    if includeExt and excludeExt:
        errorMsg = "Set only 'includeExt' or 'excludeExt', not both!"
        raise Exception(errorMsg)

    _includeFilter: List[str] = []
    if includeExt:
        for ext in includeExt:
            _includeFilter.append(ext.lower())
    _excludeFilter: List[str] = []
    if excludeExt:
        for ext in excludeExt:
            _excludeFilter.append(ext.lower())

    files = []
    for item in os.listdir(dirPath):
        itemPath = os.path.join(dirPath, item)
        if os.path.isfile(itemPath):
            _, ext = os.path.splitext(item)
            ext = ext.lower()

            if excludeExt:
                if ext in _excludeFilter:
                    continue

            if includeExt:
                if ext in _includeFilter:
                    files.append(itemPath)
            else:
                files.append(itemPath)

    return files


def getFilesInFolderTree(folderTreePath: str,
                         includeExt: Optional[List[str]] = None,
                         excludeExt: Optional[List[str]] = None) -> List[str]:
    """ Same as :func:`getFilesInFolder()`, but scan through all files in 
    all folders.

    Note:
        Only one of ``includeExt`` or ``excludeExt`` must be set, or exception 
        is raised. Lower case extension strings are compared.

    Args:
        folderTreePath: path to a folder tree to scan.
        includeExt: if set, only files with given extension(s) are returned.
        excludeExt: if set, files with given extension(s) are excluded 
            from return list.
    """
    folderTreePath = check(folderTreePath)

    allFiles = []
    for (rootFolderPath, _, _) in os.walk(folderTreePath):
        thisFolderFiles = getFilesInFolder(rootFolderPath, includeExt, excludeExt)
        allFiles.extend(thisFolderFiles)

    return allFiles


def getFoldersInFolder(dirPath: str,
                       nameFilter: Optional[str] = None,
                       compareLowerCase: bool = True) -> List[str]:
    """ Get a list of folders in a given 'dirPath'.

    Args:
        dirPath: path to a folder to scan.
        nameFilter: if set, folders that contain this string are returned,
            based on compareLowerCase setting.
        compareLowerCase: if True, lower-cased nameFilter string (if set)
            is checked in lower case folder name.
    """
    _pathValidationCheck(dirPath)
    check(dirPath)
    dirPath = os.path.normpath(dirPath)

    if nameFilter is not None:
        if compareLowerCase:
            nameFilter = nameFilter.lower()

    folders = []
    for item in os.listdir(dirPath):
        itemPath = os.path.join(dirPath, item)
        if os.path.isdir(itemPath):
            if nameFilter is None:
                folders.append(itemPath)
            else:  # name filtering is in place
                if compareLowerCase:
                    if nameFilter in item.lower():
                        folders.append(itemPath)
                else:
                    if nameFilter in item:
                        folders.append(itemPath)

    return folders


def openWithDefaultBrowser(url: str):  # pragma: no cover
    """Open given address in a default web browser as a non-blocking subprocess.

    Args:
        url: web address to open.
    """
    webbrowser.open(url, new=2)  # 2 = new tab


def openWithDefaultApp(fPath: str):  # pragma: no cover
    """ Open given file with OS default application as a non-blocking subprocess.

    Args:    
        fPath: path to a file to open.
    """
    fPath = check(fPath)
    fPath = f"\"{fPath}\""

    args = []
    if os.name == "nt":
        # Windows
        os.startfile(fPath)
    else:
        # MacOS/X # NOTE: not tested!
        os.popen(f"open {fPath}")


def _pathValidationCheck(path: Optional[str]) -> str:
    """ Raise exception if given path is not a string or it is an empty string.

    Args:
        path: path to check.
    """
    if isinstance(path, str):
        if path.strip() != '':
            return path
    elif isinstance(path, pathlib.Path):
        return path

    # 0 - current frame  of getCallerLocation scope
    # 1 - frame of this _pathValidationCheck()
    # 2 - frame of the caller of this function (_pathValidationCheck() is a
    #   private function, should be only used inside pth.py)
    # 3 - frame of the caller of a function in paths, that further called
    # _pathValidationCheck() func
    callerLocation = dlpt.utils.getCallerLocation(3)
    errorMsg = f"Invalid path format - expected non-empty string: '{path}'\n\t{callerLocation}"
    raise ValueError(errorMsg)
