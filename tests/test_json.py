import json
import os
from unittest import mock

import pytest

import dlpt


def test_check(tmp_path):
    fPath = os.path.join(tmp_path, "jsonTest.json")

    # empty file
    with open(fPath, "w+") as fHandler:
        pass
    assert dlpt.json.check(fPath) is False

    # invalid syntax, missing \" in zxc
    dataStr = '{"asd": "qwe","zxc: 123}'
    with open(fPath, "w+") as fHandler:
        fHandler.write(dataStr)
    assert dlpt.json.check(fPath) is False

    # valid syntax
    dataStr = '{"asd": "qwe","zxc": 123}'
    with open(fPath, "w+") as fHandler:
        fHandler.write(dataStr)
    assert dlpt.json.check(fPath) is True


def test_remove_comments():
    DATA_STR = """{"asd": /*inline with special characters: !@/[]()/\\ */ "qwe",
    // comment in its own line
    "zxc": 123, // comment at the end of the line
    /* comment
    block 
    in multiple lines */
    "ert": {
        "fgh": 456
        }
    }"""
    DATA = {"asd": "qwe", "zxc": 123, "ert": {"fgh": 456}}
    dataStr = dlpt.json.remove_comments(DATA_STR)
    data = json.loads(dataStr)

    assert data == DATA


def test_read(tmp_path):
    DATA_STR = '{"asd": "qwe","zxc": 123}'

    with mock.patch("builtins.open") as fFunc:
        fFunc.read = DATA_STR

        with mock.patch("dlpt.json.remove_comments") as rmCommentsFunc:
            rmCommentsFunc.return_value = DATA_STR

            data = dlpt.json.read(tmp_path)
            assert isinstance(data, dict)

            assert len(data) == 2
            assert data["asd"] == "qwe"
            assert data["zxc"] == 123


def test_write(tmp_path):
    fPath = os.path.join(tmp_path, "jsonTest.json")

    DATA = {"asd": "qwe", "zxc": 123, "ert": {"fgh": 456}}

    dlpt.json.write(DATA, fPath)
    data = dlpt.json.read(fPath)
    assert data == DATA


class _JsonTestClass:
    def __init__(self):
        self.public = 123
        self._private = "321"
        self.nested = [_JsonTestSubclass()]

    def someMethod(self):
        pass


class _JsonTestSubclass:
    def __init__(self):
        self.nestedPublic = 456
        self._nestedPrivate = "654"


def test_rw_jsonpickle(tmp_path):
    fPath = os.path.join(tmp_path, "jsonTest.json")

    wData = _JsonTestClass()
    dlpt.json.write_jsonpickle(wData, fPath)

    rData = dlpt.json.read_jsonpickle(fPath)

    assert isinstance(rData, _JsonTestClass)
    assert rData._private == "321"
    assert rData.nested[0].nestedPublic == 456
    assert rData.nested[0]._nestedPrivate == "654"
