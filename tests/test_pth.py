import os
import pathlib
import shutil
import stat
import time

import pytest

import dlpt

from dlpt.tfix import *

thisFile = str(pathlib.Path(__file__).resolve())
thisFolder = os.path.dirname(thisFile)

urlPath = "https://xkcd.com/"
uncPath = r"\\root\rootFolder\folder1\folder2\folder3\folder4"


def test_pathManipulation():
    assert dlpt.pth.withFwSlashes(thisFile) == thisFile.replace("\\", "/")
    assert dlpt.pth.withDoubleBwSlashes(thisFile) == thisFile.replace("\\", "\\\\")


def test_fileFolderRemoval(tmp_path):
    # create files
    allFiles = [
        os.path.join(tmp_path, 'testFile1.txt'),
        os.path.join(tmp_path, 'testFile2.txt'),
        os.path.join(tmp_path, 'testFile3.txt'),
        os.path.join(tmp_path, 'testFile4.txt')
    ]
    for filePath in allFiles:
        with open(filePath, 'w+') as fHandler:
            fHandler.write('asdasdasdasd')
    for filePath in allFiles:
        dlpt.pth.removeFile(filePath)
    assert os.listdir(tmp_path) == []

    for filePath in allFiles:
        with open(filePath, 'w+') as fHandler:
            fHandler.write('qweqweqwe')
    dlpt.pth.cleanFolder(tmp_path)
    assert os.listdir(tmp_path) == []

    subFolder = os.path.join(tmp_path, 'subFolder')
    os.mkdir(subFolder)
    for filePath in allFiles:
        with open(filePath, 'w+') as fHandler:
            fHandler.write('qweqweqwe')
        filePath = filePath.replace(str(tmp_path), subFolder)
        with open(filePath, 'w+') as fHandler:
            fHandler.write('qweqweqwe')
    dlpt.pth.removeFolderTree(subFolder)
    assert dlpt.utils.areListValuesEqual(dlpt.pth.getFilesInFolder(tmp_path), allFiles)

    # what if file is locked?
    try:
        os.chmod(allFiles[0], stat.S_IREAD)
        with pytest.raises(Exception):
            dlpt.pth.removeFile(allFiles[0], forceWritePermissions=False)
        dlpt.pth.removeFile(allFiles[0])
        assert os.path.exists(allFiles[0]) is False
    except:
        os.chmod(allFiles[0], stat.S_IWRITE)

    dlpt.pth.createCleanFolder(tmp_path)
    assert os.path.exists(tmp_path) is True
    assert len(os.listdir(tmp_path)) == 0

    # what if folder is locked?
    try:
        os.chmod(tmp_path, stat.S_IREAD)
        with pytest.raises(Exception):
            dlpt.pth.removeFolderTree(tmp_path, forceWritePermissions=False)
        dlpt.pth.removeFolderTree(tmp_path)
        assert os.path.exists(tmp_path) is False
    except:
        os.chmod(tmp_path, stat.S_IWRITE)


def test_pathCheckers():
    def testFunc():
        # calls dlpt.pth._pathValidationCheck() which should raise exception
        dlpt.pth.getFilesInFolder(None)

    assert dlpt.pth._pathValidationCheck(thisFile) == thisFile
    with pytest.raises(Exception):
        dlpt.pth._pathValidationCheck(None)
    with pytest.raises(Exception):
        dlpt.pth._pathValidationCheck(' ')

    try:
        # will raise exception!
        testFunc()
    except Exception as err:
        splitErr = str(err).split('\n')
        assert "testFunc()" in splitErr[1]
        assert f"{os.path.abspath(__file__).lower()}" in splitErr[1].lower()

    dlpt.pth.check(thisFile)
    with pytest.raises(FileNotFoundError):
        dlpt.pth.check(thisFile + "asd")
    with pytest.raises(ValueError):
        dlpt.pth.check(" ")

    try:
        # will raise exception!
        dlpt.pth.check("asd")
    except Exception as err:
        splitErr = str(err).split('\n')
        assert "test_pathCheckers()" in splitErr[1]
        assert f"{os.path.abspath(__file__).lower()}" in splitErr[1].lower()


def test_fileFolderHandlers(tmp_path):
    # create a folder and clean it and delete it
    newSubFolder = os.path.join(tmp_path, "subOne")
    dlpt.pth.createFolder(newSubFolder)
    dlpt.pth.check(newSubFolder)

    # cleanup tmp folder
    assert os.listdir(tmp_path) != []
    dlpt.pth.cleanFolder(tmp_path)
    assert os.listdir(tmp_path) == []

    dlpt.pth.createFolder(newSubFolder)
    dlpt.pth.createFolder(os.path.join(newSubFolder, "subTwo"))

    # copy folder
    newSubFolderCopy = str(tmp_path) + "Copy"
    dlpt.pth.copyFolder(newSubFolder, newSubFolderCopy)
    dlpt.pth.check(newSubFolder)
    dlpt.pth.check(newSubFolderCopy)
    assert dlpt.utils.areListValuesEqual(os.listdir(newSubFolder), os.listdir(newSubFolderCopy))
    dlpt.pth.removeFolderTree(newSubFolderCopy)

    # remove folder
    dlpt.pth.removeFolderTree(newSubFolder)
    assert os.path.exists(newSubFolder) is False

    # create a copy of this file and delete it
    thisFileCopyName = dlpt.pth.getName(thisFile, False) + "Copy.py"
    dstFilePath = dlpt.pth.copyFile(thisFile, tmp_path, thisFileCopyName)
    assert os.path.exists(dstFilePath) is True
    with pytest.raises(ValueError):
        dlpt.pth.removeFolderTree(dstFilePath)
    dlpt.pth.removeFile(dstFilePath)
    assert os.path.exists(dstFilePath) is False
    # create intermediate folders
    dstFolderPath = os.path.join(tmp_path, "subOne", "subTwo")
    dstFilePath = dlpt.pth.copyFile(thisFile, dstFolderPath, thisFileCopyName)
    assert os.path.exists(dstFilePath) is True
    # check if copy will remove file before if already existing
    dstFilePath = dlpt.pth.copyFile(thisFile, dstFolderPath, thisFileCopyName)
    assert os.path.exists(dstFilePath) is True
    dlpt.pth.removeFile(dstFilePath)
    assert os.path.exists(dstFilePath) is False

    # copy to dst as folder (not file)
    dstFilePath = dlpt.pth.copyFile(thisFile, tmp_path)
    assert os.path.exists(dstFilePath) is True
    assert dstFilePath == os.path.join(tmp_path, dlpt.pth.getName(thisFile))

    with pytest.raises(ValueError):
        dlpt.pth.copyFile(tmp_path, tmp_path)

    with pytest.raises(ValueError):
        dlpt.pth.removeFile(tmp_path)


def test_fileFolderExplorer(tmp_path):
    # create a subfolder
    subFolderName = "subfolder"
    subfolderPath = os.path.join(tmp_path, subFolderName)
    dlpt.pth.createFolder(subfolderPath)
    # create test files in temp folder
    pyFileNames = ["file1.py", "file2.py", "file 3.py", "custom.py", "customPy.py"]
    txtFileNames = ["file4.txt", "custom.txt", "customText.txt"]
    rootPyFilePaths = []
    allPyFilePaths = []
    subfolderPyFilePaths = []
    rootTxtFilePaths = []
    subfolderTxtFilePaths = []
    allTxtFilePaths = []
    rootFiles = []
    allFiles = []
    # py files
    for fileName in pyFileNames:
        filePath = os.path.join(tmp_path, fileName)
        allFiles.append(filePath)
        rootFiles.append(filePath)
        rootPyFilePaths.append(filePath)
        allPyFilePaths.append(filePath)
        shutil.copyfile(thisFile, filePath)

        filePath = os.path.join(subfolderPath, fileName)
        allFiles.append(filePath)
        subfolderPyFilePaths.append(filePath)
        allPyFilePaths.append(filePath)
        shutil.copyfile(thisFile, filePath)
    # txt
    for fileName in txtFileNames:
        filePath = os.path.join(tmp_path, fileName)
        allFiles.append(filePath)
        rootFiles.append(filePath)
        rootTxtFilePaths.append(filePath)
        allTxtFilePaths.append(filePath)
        shutil.copyfile(thisFile, filePath)

        filePath = os.path.join(subfolderPath, fileName)
        allFiles.append(filePath)
        subfolderTxtFilePaths.append(filePath)
        allTxtFilePaths.append(filePath)
        shutil.copyfile(thisFile, filePath)

    # getAllFilesInFolder()
    fileList = dlpt.pth.getFilesInFolder(tmp_path)
    assert dlpt.utils.areListValuesEqual(fileList, rootFiles)
    fileList = dlpt.pth.getFilesInFolder(subfolderPath)
    assert dlpt.utils.areListValuesEqual(fileList, subfolderPyFilePaths + subfolderTxtFilePaths)

    # getAllFilesInFolderTree()
    fileList = dlpt.pth.getFilesInFolderTree(tmp_path)
    assert dlpt.utils.areListValuesEqual(fileList, (allPyFilePaths + allTxtFilePaths) * 2)
    fileList = dlpt.pth.getFilesInFolderTree(tmp_path, includeExt=[".py"])
    assert dlpt.utils.areListValuesEqual(fileList, allPyFilePaths)
    fileList = dlpt.pth.getFilesInFolderTree(tmp_path, includeExt=[".py"])
    assert dlpt.utils.areListValuesEqual(fileList, allPyFilePaths)
    fileList = dlpt.pth.getFilesInFolderTree(tmp_path, excludeExt=[".txt"])
    assert dlpt.utils.areListValuesEqual(fileList, allPyFilePaths)

    # getAllFoldersInFolder()
    folderList = dlpt.pth.getFoldersInFolder(tmp_path)
    assert folderList == [subfolderPath]
    folderList = dlpt.pth.getFoldersInFolder(tmp_path, nameFilter="sub")
    assert folderList == [subfolderPath]
    folderList = dlpt.pth.getFoldersInFolder(tmp_path, nameFilter="qwe")
    assert len(folderList) == 0


def test_changeDir(tmp_path):
    tmpFilePath = os.path.join(tmp_path, "test_changeDir.txt")
    with open(tmpFilePath, "w+") as fHandler:
        pass  # create actual empty file

    cwd = os.getcwd()
    with dlpt.pth.ChangeDir(tmpFilePath):
        assert os.getcwd() == os.path.dirname(tmpFilePath)
    assert os.getcwd() == cwd

    with dlpt.pth.ChangeDir(os.path.dirname(tmpFilePath)):
        assert os.getcwd() == os.path.dirname(tmpFilePath)
    assert os.getcwd() == cwd

    with pytest.raises(Exception):
        nonExistingPath = os.path.join(os.path.dirname(tmpFilePath), "asd")
        with dlpt.pth.ChangeDir(nonExistingPath):
            pass


def test_removeOldItems(tmp_path):
    subFolders = [  # path, days
        (os.path.join(tmp_path, "now"), 0),
        (os.path.join(tmp_path, "one"), 1),
        (os.path.join(tmp_path, "two"), 2),
        (os.path.join(tmp_path, "three"), 3),
        (os.path.join(tmp_path, "four"), 10)
    ]
    for fData in subFolders:
        path, daysAgo = fData
        dlpt.pth.createFolder(path)
        newTimestamp = time.time() - dlpt.time.timeToSeconds(d=daysAgo)
        os.utime(path, (newTimestamp, newTimestamp))
    for fData in subFolders:
        path, daysAgo = fData
        path = path + ".txt"
        with open(path, "w+") as fHandler:
            pass
        newTimestamp = time.time() - dlpt.time.timeToSeconds(d=daysAgo)
        os.utime(path, (newTimestamp, newTimestamp))

    dlpt.pth.removeOldItems(tmp_path, 1)
    assert dlpt.utils.areListValuesEqual(os.listdir(tmp_path), ["now", "one", "now.txt", "one.txt"])
