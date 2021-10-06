import os

import pytest

import dlpt

from dlpt.tfix import *

MODULE_NAME = "myModule.py"

VARIABLE_DEFAULT_VALUE = 6
VARIABLE_ALTERED_VALUE = 42
VARIABLE_NAME = "variableToChange"
FUNCTION_NAME = "testFunc"
FUNCTION_RET_VAL = "retVal"


def createTempPyFile(filePath):
    lines = []
    lines.append("import sys")
    lines.append(f"\n")
    lines.append("# Test file with local variable and function.\n")
    lines.append(f"{VARIABLE_NAME} = {VARIABLE_DEFAULT_VALUE}\n")
    lines.append(f"\n")
    lines.append(f"def {FUNCTION_NAME}():\n")
    lines.append(f"     return \"{FUNCTION_RET_VAL}\"\n")

    with open(filePath, 'w+') as fHandler:
        fHandler.writelines(lines)


def checkModule(importer: "dlpt.importer.ModuleImporter"):
    module = importer.getModule()

    assert importer.hasObject(VARIABLE_NAME) is True
    assert importer.hasObject(FUNCTION_NAME) is True
    assert callable(getattr(module, FUNCTION_NAME)) is True

    with pytest.raises(Exception):
        importer.hasObject("qweasdxzc")
    assert importer.hasObject("qweasdxzc", False) is False

    assert VARIABLE_NAME == "variableToChange"
    assert module.variableToChange == VARIABLE_DEFAULT_VALUE  # type: ignore


def test_basic(tmp_path):
    tmpFilePath = os.path.join(tmp_path, "test_basic.py")
    with pytest.raises(ValueError):
        dlpt.importer.ModuleImporter(tmp_path)

    createTempPyFile(tmpFilePath)
    importer = dlpt.importer.ModuleImporter(tmpFilePath)
    checkModule(importer)

    # rel path
    baseFolder = os.path.dirname(os.path.dirname(tmpFilePath))
    relPath = str(os.path.relpath(tmpFilePath, baseFolder))
    with dlpt.pth.ChangeDir(baseFolder):
        with pytest.raises(ValueError):
            dlpt.importer.ModuleImporter(relPath)

    # file is not inside base folder
    baseFolder = os.path.dirname(os.path.dirname(tmpFilePath))
    with pytest.raises(ValueError):
        dlpt.importer.ModuleImporter(__file__, baseFolder)

    # folder, not file
    with pytest.raises(ValueError):
        dlpt.importer.ModuleImporter(os.path.dirname(tmpFilePath))

    # non-existing path
    with pytest.raises(FileNotFoundError):
        dlpt.pth.removeFile(tmpFilePath)
        dlpt.importer.ModuleImporter(tmpFilePath)

    # non-valid python module
    with pytest.raises(Exception):
        with open(tmpFilePath, "w+") as fHandler:
            fHandler.write("123 = \"not a valid py syntax\"\n")
        dlpt.importer.ModuleImporter(tmpFilePath)


def test_customBaseFolder_sameFolder(tmp_path):
    filePath = os.path.join(tmp_path, MODULE_NAME)
    createTempPyFile(filePath)

    importer = dlpt.importer.ModuleImporter(filePath, tmp_path)
    checkModule(importer)


def test_customBaseFolder_subFolder(tmp_path):
    folderPath = os.path.join(tmp_path, "root", "package", "subFolder")
    dlpt.pth.createFolder(folderPath)
    filePath = os.path.join(folderPath, MODULE_NAME)
    createTempPyFile(filePath)

    importer = dlpt.importer.ModuleImporter(filePath, tmp_path)
    checkModule(importer)


def test_customBaseFolder_invalidFolder(tmp_path):
    filePath = os.path.join(tmp_path, MODULE_NAME)
    createTempPyFile(filePath)

    with pytest.raises(ValueError):
        dlpt.importer.ModuleImporter(filePath, os.getcwd())
