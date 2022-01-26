import os

import pytest

import dlpt

MODULE_NAME = "myModule.py"

VARIABLE_DEFAULT_VALUE = 6
VARIABLE_ALTERED_VALUE = 42
VARIABLE_NAME = "variableToChange"
FUNCTION_NAME = "testFunc"
FUNCTION_RET_VAL = "retVal"


def create_tmp_py_file(fPath):
    lines = []
    lines.append("import sys")
    lines.append(f"\n")
    lines.append("# Test file with local variable and function.\n")
    lines.append(f"{VARIABLE_NAME} = {VARIABLE_DEFAULT_VALUE}\n")
    lines.append(f"\n")
    lines.append(f"def {FUNCTION_NAME}():\n")
    lines.append(f'     return "{FUNCTION_RET_VAL}"\n')

    with open(fPath, "w+") as fHandler:
        fHandler.writelines(lines)


def check_module(importer: "dlpt.importer.ModuleImporter"):
    module = importer.get_module()

    assert importer.has_object(VARIABLE_NAME) is True
    assert importer.has_object(FUNCTION_NAME) is True
    assert callable(getattr(module, FUNCTION_NAME)) is True

    with pytest.raises(Exception):
        importer.has_object("qweasdxzc")
    assert importer.has_object("qweasdxzc", False) is False

    assert VARIABLE_NAME == "variableToChange"
    assert module.variableToChange == VARIABLE_DEFAULT_VALUE  # type: ignore


def test_basic(tmp_path):
    tmpFilePath = os.path.join(tmp_path, "test_basic.py")
    with pytest.raises(ValueError):
        dlpt.importer.ModuleImporter(tmp_path)

    create_tmp_py_file(tmpFilePath)
    importer = dlpt.importer.ModuleImporter(tmpFilePath)
    check_module(importer)

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
        dlpt.pth.remove_file(tmpFilePath)
        dlpt.importer.ModuleImporter(tmpFilePath)

    # non-valid python module
    with pytest.raises(Exception):
        with open(tmpFilePath, "w+") as fHandler:
            fHandler.write('123 = "not a valid py syntax"\n')
        dlpt.importer.ModuleImporter(tmpFilePath)


def test_custom_base_dir_same_dir(tmp_path):
    fPath = os.path.join(tmp_path, MODULE_NAME)
    create_tmp_py_file(fPath)

    importer = dlpt.importer.ModuleImporter(fPath, tmp_path)
    check_module(importer)


def test_custom_base_dir_subdir(tmp_path):
    dirPath = os.path.join(tmp_path, "root", "package", "subFolder")
    dlpt.pth.create_dir(dirPath)
    fPath = os.path.join(dirPath, MODULE_NAME)
    create_tmp_py_file(fPath)

    importer = dlpt.importer.ModuleImporter(fPath, tmp_path)
    check_module(importer)


def test_custom_base_dir_invalid_dir(tmp_path):
    fPath = os.path.join(tmp_path, MODULE_NAME)
    create_tmp_py_file(fPath)

    with pytest.raises(ValueError):
        dlpt.importer.ModuleImporter(fPath, os.getcwd())
