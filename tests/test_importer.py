import os

import pytest

import dlpt

MODULE_NAME = "myModule.py"

VARIABLE_DEFAULT_VALUE = 6
VARIABLE_ALTERED_VALUE = 42
VARIABLE_NAME = "variableToChange"
FUNCTION_NAME = "testFunc"
FUNCTION_RET_VAL = "retVal"


def create_tmp_py_file(file_path):
    lines = []
    lines.append("import sys")
    lines.append(f"\n")
    lines.append("# Test file with local variable and function.\n")
    lines.append(f"{VARIABLE_NAME} = {VARIABLE_DEFAULT_VALUE}\n")
    lines.append(f"\n")
    lines.append(f"def {FUNCTION_NAME}():\n")
    lines.append(f'     return "{FUNCTION_RET_VAL}"\n')

    with open(file_path, "w+") as fHandler:
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
    tmp_file_path = os.path.join(tmp_path, "test_basic.py")
    with pytest.raises(ValueError):
        dlpt.importer.ModuleImporter(tmp_path)

    create_tmp_py_file(tmp_file_path)
    importer = dlpt.importer.ModuleImporter(tmp_file_path)
    check_module(importer)

    # rel path
    base_dir_path = os.path.dirname(os.path.dirname(tmp_file_path))
    rel_path = str(os.path.relpath(tmp_file_path, base_dir_path))
    with dlpt.pth.ChangeDir(base_dir_path):
        with pytest.raises(ValueError):
            dlpt.importer.ModuleImporter(rel_path)

    # file is not inside base directory
    base_dir_path = os.path.dirname(os.path.dirname(tmp_file_path))
    with pytest.raises(ValueError):
        dlpt.importer.ModuleImporter(__file__, base_dir_path)

    # directory, not file
    with pytest.raises(ValueError):
        dlpt.importer.ModuleImporter(os.path.dirname(tmp_file_path))

    # non-existing path
    with pytest.raises(FileNotFoundError):
        dlpt.pth.remove_file(tmp_file_path)
        dlpt.importer.ModuleImporter(tmp_file_path)

    # non-valid python module
    with pytest.raises(Exception):
        with open(tmp_file_path, "w+") as f:
            f.write('123 = "not a valid py syntax"\n')
        dlpt.importer.ModuleImporter(tmp_file_path)


def test_custom_base_dir_same_dir(tmp_path):
    file_path = os.path.join(tmp_path, MODULE_NAME)
    create_tmp_py_file(file_path)

    importer = dlpt.importer.ModuleImporter(file_path, tmp_path)
    check_module(importer)


def test_custom_base_dir_subdir(tmp_path):
    dir_path = os.path.join(tmp_path, "root", "package", "subdir")
    dlpt.pth.create_dir(dir_path)
    file_path = os.path.join(dir_path, MODULE_NAME)
    create_tmp_py_file(file_path)

    importer = dlpt.importer.ModuleImporter(file_path, tmp_path)
    check_module(importer)


def test_custom_base_dir_invalid_dir(tmp_path):
    file_path = os.path.join(tmp_path, MODULE_NAME)
    create_tmp_py_file(file_path)

    with pytest.raises(ValueError):
        dlpt.importer.ModuleImporter(file_path, os.getcwd())
