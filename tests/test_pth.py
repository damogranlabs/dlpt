import os
import pathlib
import stat
import time
from unittest import mock
from unittest.mock import call

import pytest

import dlpt

thisFile = str(pathlib.Path(__file__).resolve())
thisFolder = os.path.dirname(thisFile)

urlPath = "https://xkcd.com/"
uncPath = r"\\root\rootFolder\folder1\folder2\folder3\folder4"


@pytest.mark.parametrize("isFile", [False, True])
def test_changeDir(isFile):
    cwd = os.getcwd()
    if isFile:
        path = __file__
        newCwd = os.path.dirname(path)
    else:
        path = os.path.dirname(__file__)
        newCwd = path

    with mock.patch("dlpt.pth.check"):
        with mock.patch("dlpt.pth.resolve") as resolveFunc:
            resolveFunc.return_value = path

            with mock.patch("os.chdir") as osChdirFunc:

                with dlpt.pth.ChangeDir(path):
                    pass  # do whatever here

    assert osChdirFunc.call_count == 2
    assert osChdirFunc.call_args_list == [call(newCwd), call(cwd)]
    assert cwd == os.getcwd()


def test_pathValidationCheck():
    assert dlpt.pth._pathValidationCheck(__file__) == __file__

    with pytest.raises(Exception):
        dlpt.pth._pathValidationCheck(None)

    with pytest.raises(Exception):
        dlpt.pth._pathValidationCheck(' ')


@pytest.mark.parametrize("validPath", [False, True])
def test_check(validPath):
    if validPath:
        path = __file__
    else:
        path = __file__ + "asd"

    with mock.patch("dlpt.pth._pathValidationCheck") as checkFunc:
        checkFunc.return_value = path

        with mock.patch("os.path.exists") as existsFunc:
            existsFunc.return_value = validPath

        if validPath:
            assert dlpt.pth.check(path) == path
        else:
            with pytest.raises(Exception):
                dlpt.pth.check(path)


def test_resolve():
    path = dlpt.pth.resolve(__file__)
    assert isinstance(path, str)
    assert path.lower() == __file__.lower()
    assert os.path.samefile(path, __file__)


@pytest.mark.parametrize("succes", [False, True])
def test_setWritePermissions(tmp_path, succes):
    fPath = os.path.join(tmp_path, 'testFile.txt')

    with mock.patch("os.chmod") as modFunc:
        with mock.patch("os.access") as accessFunc:
            if succes:
                accessFunc.return_value = True
                dlpt.pth._setWritePermissions(fPath)
            else:
                accessFunc.return_value = False

                with pytest.raises(Exception):
                    dlpt.pth._setWritePermissions(fPath)

            assert modFunc.call_count == 1
            assert modFunc.call_args[0][0] == fPath
            assert modFunc.call_args[0][1] == stat.S_IWRITE

            assert accessFunc.call_count == 1
            assert accessFunc.call_args[0][0] == fPath
            assert accessFunc.call_args[0][1] == os.W_OK


def test_copyFile_checks():
    with pytest.raises(Exception):
        dlpt.pth.copyFile(__file__, __file__)  # non-existing path (dstFolderPath == __file__)

    with mock.patch("dlpt.pth.check"):
        with mock.patch("os.path.isfile") as isFileFunc:
            isFileFunc.return_value = False

            with pytest.raises(ValueError):
                dlpt.pth.copyFile(__file__, __file__)  # folder, not file


@pytest.mark.parametrize("dstFileName", [None, "newFileName.txt"])
def test_copyFile(tmp_path, dstFileName):
    FILE_NAME = "testFile.txt"
    srcFilePath = os.path.join(tmp_path, FILE_NAME)
    dstFolderPath = os.path.join(tmp_path, "dst")
    if dstFileName:
        dstFilePath = os.path.join(tmp_path, "dst", dstFileName)
    else:
        dstFilePath = os.path.join(tmp_path, "dst", FILE_NAME)

    with mock.patch("dlpt.pth.check") as checkFunc:
        checkFunc.return_value = srcFilePath
        with mock.patch("os.path.isfile") as isFileFunc:
            isFileFunc.return_value = True

            with mock.patch("dlpt.pth.getName") as nameFunc:
                if dstFileName is None:
                    nameFunc.return_value = FILE_NAME

                with mock.patch("dlpt.pth.createFolder") as createFunc:
                    with mock.patch("dlpt.pth.removeFile") as rmFileFunc:
                        with mock.patch("shutil.copyfile") as copyFunc:

                            path = dlpt.pth.copyFile(srcFilePath, dstFolderPath, dstFileName)
                            assert path == dstFilePath

                            if dstFileName is None:
                                assert nameFunc.call_count == 1
                                assert nameFunc.call_args[0][0] == srcFilePath
                            else:
                                assert nameFunc.call_count == 0

                            assert createFunc.call_count == 1
                            assert createFunc.call_args[0][0] == dstFolderPath

                            assert rmFileFunc.call_count == 1
                            assert rmFileFunc.call_args[0][0] == dstFilePath

                            assert copyFunc.call_count == 1
                            assert copyFunc.call_args[0][0] == srcFilePath
                            assert copyFunc.call_args[0][1] == dstFilePath


def test_copyFolder_checks():
    with pytest.raises(Exception):
        dlpt.pth.copyFile(__file__, __file__)  # non-existing path

    with mock.patch("dlpt.pth.check"):
        with mock.patch("os.path.isdir") as isDirFunc:
            isDirFunc.return_value = False

            with pytest.raises(ValueError):
                dlpt.pth.copyFolder(__file__, __file__)  # file, not folder


def test_copyFolder(tmp_path):
    dstFolderPath = os.path.join(tmp_path, "dst")

    with mock.patch("dlpt.pth.check") as checkFunc:
        checkFunc.return_value = tmp_path
        with mock.patch("os.path.isdir") as isDirFunc:
            isDirFunc.return_value = True

            with mock.patch("dlpt.pth._pathValidationCheck"):

                with mock.patch("dlpt.pth.removeFolderTree") as rmFolderFunc:
                    with mock.patch("shutil.copytree") as copyFunc:

                        path = dlpt.pth.copyFolder(tmp_path, dstFolderPath)
                        assert path == dstFolderPath

                        assert rmFolderFunc.call_count == 1
                        assert rmFolderFunc.call_args[0][0] == dstFolderPath

                        assert copyFunc.call_count == 1
                        assert copyFunc.call_args[0][0] == tmp_path
                        assert copyFunc.call_args[0][1] == dstFolderPath


def test_removeFile_checks(tmp_path):
    with pytest.raises(Exception):
        dlpt.pth.removeFile(tmp_path)  # non-existing path

    with mock.patch("os.path.isfile") as isFileFunc:
        isFileFunc.return_value = False

        with pytest.raises(ValueError):
            dlpt.pth.removeFile(tmp_path)  # folder, not file


@pytest.mark.parametrize("forceWritePermissions", [False, True])
def test_removeFile(forceWritePermissions):
    with mock.patch("os.path.exists") as isFileFunc:
        isFileFunc.return_value = True
        with mock.patch("os.path.isfile") as isFileFunc:
            isFileFunc.return_value = True

            with mock.patch("dlpt.pth._setWritePermissions") as fwpFunc:
                with mock.patch("os.unlink") as rmFunc:

                    dlpt.pth.removeFile(__file__, forceWritePermissions)

                    assert rmFunc.call_count == 1
                    assert rmFunc.call_args[0][0] == __file__

                    if forceWritePermissions:
                        assert fwpFunc.call_count == 1
                        assert fwpFunc.call_args[0][0] == __file__
                    else:
                        assert fwpFunc.call_count == 0


@pytest.mark.parametrize("success", [False, True])
def test_removeFile_retry(success):
    with mock.patch("os.path.exists") as isFileFunc:
        isFileFunc.return_value = True
        with mock.patch("os.path.isfile") as isFileFunc:
            isFileFunc.return_value = True

            with mock.patch("dlpt.pth._setWritePermissions"):
                with mock.patch("os.unlink") as rmFunc:
                    rmFunc.side_effect = [Exception("1"), Exception("2"), None]

                    if success:
                        dlpt.pth.removeFile(__file__)

                        assert rmFunc.call_count == 3
                        assert rmFunc.call_args_list == [call(__file__)] * 3
                    else:
                        with pytest.raises(Exception):
                            dlpt.pth.removeFile(__file__, retry=1)


def test_removeFolderTree_checks():
    with mock.patch("os.path.exists") as existsFunc:
        existsFunc.return_value = True
        with mock.patch("os.path.isdir") as isDirFunc:
            isDirFunc.return_value = False

            with pytest.raises(ValueError):
                dlpt.pth.removeFolderTree(__file__)


@pytest.mark.parametrize("forceWritePermissions", [False, True])
def test_removeFolderTree(forceWritePermissions):
    with mock.patch("os.path.exists") as existsFunc:
        existsFunc.return_value = True
        with mock.patch("os.path.isdir") as isDirFunc:
            isDirFunc.return_value = True

            with mock.patch("shutil.rmtree") as rmFunc:

                dlpt.pth.removeFolderTree(__file__)

                assert rmFunc.call_count == 1
                assert rmFunc.call_args[0][0] == __file__
                if forceWritePermissions:
                    # keyword args
                    kwArgs = {
                        "ignore_errors": False,
                        "onerror": dlpt.pth._removeFolderErrorHandler
                    }
                    assert rmFunc.call_args[1] == kwArgs


@pytest.mark.parametrize("success, forceWritePermissions", [(False, True),
                                                            (True, True),
                                                            (True, False)])
def test_removeFolderTree_retry(success, forceWritePermissions):
    with mock.patch("os.path.exists") as existsFunc:
        existsFunc.return_value = True
        with mock.patch("os.path.isdir") as isDirFunc:
            isDirFunc.return_value = True
            with mock.patch("time.sleep") as sleepFunc:

                with mock.patch("shutil.rmtree") as rmFunc:
                    if success:
                        rmFunc.side_effect = [Exception("1"), Exception("2"), None]
                        dlpt.pth.removeFolderTree(__file__, forceWritePermissions)
                        assert rmFunc.call_count == 3
                        assert sleepFunc.call_count == 2

                    else:
                        rmFunc.side_effect = [Exception("1"), Exception("2"), None]
                        with pytest.raises(Exception):
                            dlpt.pth.removeFolderTree(__file__, forceWritePermissions, retry=1)

                        assert rmFunc.call_count == 1
                        assert sleepFunc.call_count == 0


def test_cleanFolder(tmp_path):
    items = ["file1", "folder1", "file2", "file3"]
    isFile = [True, False, True, True]

    with mock.patch("os.listdir") as listFunc:
        listFunc.return_value = items
        with mock.patch("os.path.isfile") as isFileFunc:
            isFileFunc.side_effect = isFile

            with mock.patch("dlpt.pth.removeFile") as rmFileFunc:
                with mock.patch("dlpt.pth.removeFolderTree") as rmFolderFunc:

                    dlpt.pth.cleanFolder(tmp_path)

                    assert rmFileFunc.call_count == 3
                    assert rmFolderFunc.call_count == 1


def test_createFolder(tmp_path):
    with mock.patch("os.makedirs") as mkFunc:
        dlpt.pth.createFolder(tmp_path)
        assert mkFunc.call_count == 1
        assert os.path.samefile(mkFunc.call_args[0][0], tmp_path)


@pytest.mark.parametrize("isExisting", [False, True])
def test_createCleanFolder(tmp_path, isExisting):

    with mock.patch("os.path.exists") as existsFunc:
        existsFunc.return_value = isExisting

        with mock.patch("dlpt.pth.cleanFolder") as cleanFunc:
            with mock.patch("dlpt.pth.createFolder") as createFunc:

                dlpt.pth.createCleanFolder(tmp_path)

                if isExisting:
                    assert cleanFunc.call_count == 1
                    assert createFunc.call_count == 0
                else:
                    assert cleanFunc.call_count == 0
                    assert createFunc.call_count == 1


def test_removeOldItems(tmp_path):
    DAY_IN_SEC = 24 * 60 * 60
    currentTime = time.time()

    items = [
        "now.txt", "dayOld.txt", "dayOldFolder",
        "sameAsDaysArgument.txt",
        "oldFile.txt", "oldFolder"
    ]
    modTime = [
        currentTime - 0, currentTime - 1 * DAY_IN_SEC, currentTime - 1 * DAY_IN_SEC,
        currentTime - 3 * DAY_IN_SEC,
        currentTime - 10 * DAY_IN_SEC, currentTime - 10 * DAY_IN_SEC
    ]
    isFile = [
        # True, True, False,  # not called
        # True,               # not called
        True, False
    ]

    with mock.patch("time.time") as timeFunc:
        timeFunc.return_value = currentTime
        with mock.patch("os.listdir") as listFunc:
            listFunc.return_value = items
            with mock.patch("os.path.getmtime") as mTimeFunc:
                mTimeFunc.side_effect = modTime
                with mock.patch("os.path.isfile") as isFileFunc:
                    isFileFunc.side_effect = isFile

                    with mock.patch("dlpt.pth.removeFile") as rmFileFunc:
                        with mock.patch("dlpt.pth.removeFolderTree") as rmFolderFunc:

                            removedItems = dlpt.pth.removeOldItems(tmp_path, 3)
                            assert len(removedItems) == 2
                            assert os.path.join(tmp_path, items[-1]) in removedItems
                            assert os.path.join(tmp_path, items[-2]) in removedItems

                            assert rmFileFunc.call_count == 1
                            assert rmFolderFunc.call_count == 1


def test_withFwSlashes():
    pth = r"My/path\with\\slashes"
    assert dlpt.pth.withFwSlashes(pth) == r"My/path/with//slashes"


def test_withDoubleBwSlashes():
    pth = r"My/path\with\\slashes"
    assert dlpt.pth.withDoubleBwSlashes(pth) == r"My/path\\with\\\\slashes"


def test_getName():
    pth = r"some/path/with/fileName.txt"
    assert dlpt.pth.getName(pth) == "fileName.txt"
    assert dlpt.pth.getName(pth, False) == "fileName"

    pth = r"some/path/with/fileName"
    assert dlpt.pth.getName(pth) == "fileName"
    assert dlpt.pth.getName(pth, False) == "fileName"


def test_getExt():
    pth = r"some/path/with/fileName.txt"
    assert dlpt.pth.getExt(pth) == ".txt"

    pth = r"some/path/with/fileName"
    assert dlpt.pth.getExt(pth) == ""


def test_getFilesInFolder(tmp_path):
    items = ["file1.txt", "folder1", "file3.png", "folder2", "file4.jpg"]
    isFile = [True, False, True, False, True]

    with mock.patch("os.listdir") as listFunc:
        listFunc.return_value = items

        with mock.patch("os.path.isfile") as isFileFunc:
            isFileFunc.side_effect = isFile
            files = dlpt.pth.getFilesInFolder(tmp_path)
            assert len(files) == 3
            assert os.path.join(tmp_path, items[0]) in files
            assert os.path.join(tmp_path, items[2]) in files
            assert os.path.join(tmp_path, items[4]) in files

            isFileFunc.side_effect = isFile
            files = dlpt.pth.getFilesInFolder(tmp_path, [".txt"])
            assert len(files) == 1

            isFileFunc.side_effect = isFile
            assert os.path.join(tmp_path, items[0]) in files
            files = dlpt.pth.getFilesInFolder(tmp_path, includeExt=[".txt", ".jpg"])
            assert len(files) == 2
            assert os.path.join(tmp_path, items[0]) in files
            assert os.path.join(tmp_path, items[4]) in files

            isFileFunc.side_effect = isFile
            files = dlpt.pth.getFilesInFolder(tmp_path, excludeExt=[".png"])
            assert len(files) == 2
            assert os.path.join(tmp_path, items[0]) in files
            assert os.path.join(tmp_path, items[4]) in files

            with pytest.raises(Exception):
                dlpt.pth.getFilesInFolder(tmp_path, [".jpg"], [".png"])


def test_getFilesInFolderTree(tmp_path):
    txt1 = dlpt.pth.copyFile(__file__, tmp_path, "file1.txt")
    png1 = dlpt.pth.copyFile(__file__, tmp_path, "file2.png")
    jpg1 = dlpt.pth.copyFile(__file__, tmp_path, "file3.jpg")
    folder1 = os.path.join(tmp_path, "folder1")
    dlpt.pth.createFolder(folder1)
    txt2 = dlpt.pth.copyFile(__file__, folder1, "file11.txt")
    png2 = dlpt.pth.copyFile(__file__, folder1, "file12.png")
    subfolder = os.path.join(folder1, "subfolder")
    txt3 = dlpt.pth.copyFile(__file__, subfolder, "file21.txt")
    jpg3 = dlpt.pth.copyFile(__file__, subfolder, "file22.jpg")

    files = dlpt.pth.getFilesInFolderTree(tmp_path)
    assert len(files) == 7

    files = dlpt.pth.getFilesInFolderTree(tmp_path, includeExt=[".txt"])
    assert len(files) == 3
    assert txt1 in files
    assert txt2 in files
    assert txt3 in files

    files = dlpt.pth.getFilesInFolderTree(tmp_path, excludeExt=[".txt"])
    assert len(files) == 4
    assert png1 in files
    assert jpg1 in files
    assert png2 in files
    assert jpg3 in files

    with pytest.raises(Exception):
        dlpt.pth.getFilesInFolderTree(tmp_path, [".jpg"], [".png"])


def test_getFoldersInFolder(tmp_path):
    items = ["file1.txt", "folder", "file3.png", "Folder", "file4.jpg"]
    isFolder = [False, True, False, True, False]

    with mock.patch("os.listdir") as listFunc:
        listFunc.return_value = items

        with mock.patch("os.path.isdir") as isDirFunc:
            isDirFunc.side_effect = isFolder
            files = dlpt.pth.getFoldersInFolder(tmp_path)
            assert len(files) == 2
            assert os.path.join(tmp_path, items[1]) in files
            assert os.path.join(tmp_path, items[3]) in files

            isDirFunc.side_effect = isFolder
            files = dlpt.pth.getFoldersInFolder(tmp_path, "older")
            assert len(files) == 2

            isDirFunc.side_effect = isFolder
            files = dlpt.pth.getFoldersInFolder(tmp_path, "folder", True)  # compare lower case
            assert len(files) == 2
            assert os.path.join(tmp_path, items[1]) in files
            assert os.path.join(tmp_path, items[3]) in files

            isDirFunc.side_effect = isFolder
            files = dlpt.pth.getFoldersInFolder(tmp_path, "folder", False)
            assert len(files) == 1
            assert os.path.join(tmp_path, items[1]) in files

            isDirFunc.side_effect = isFolder
            files = dlpt.pth.getFoldersInFolder(tmp_path, "asd")
            assert len(files) == 0
