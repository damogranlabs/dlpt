import json
import os
from unittest import mock

import pytest

import dlpt
import dlpt.log as log

from dlpt.tfix import *


def test_check(tmp_path):
    filePath = os.path.join(tmp_path, 'jsonTest.json')

    # empty file
    with open(filePath, 'w+') as fHandler:
        pass
    assert dlpt.json.check(filePath) is False

    # invalid syntax, missing \" in zxc
    dataStr = '{"asd": "qwe","zxc: 123}'
    with open(filePath, 'w+') as fHandler:
        fHandler.write(dataStr)
    assert dlpt.json.check(filePath) is False

    # valid syntax
    dataStr = '{"asd": "qwe","zxc": 123}'
    with open(filePath, 'w+') as fHandler:
        fHandler.write(dataStr)
    assert dlpt.json.check(filePath) is True


def test_removeComments(tmp_path):
    DATA_STR = """{"asd": /*inline comment with some special characters: !@/[]()/\\ */ "qwe",
    // comment in its own line
    "zxc": 123, // comment at the end of the line
    /* comment
    block 
    in multiple lines */
    "ert": {
        "fgh": 456
        }
    }"""
    DATA = {
        "asd": "qwe",
        "zxc": 123,
        "ert": {
            "fgh": 456
        }
    }
    dataStr = dlpt.json.removeComments(DATA_STR)
    data = json.loads(dataStr)

    assert data == DATA


def test_read(tmp_path):
    DATA_STR = '{"asd": "qwe","zxc": 123}'

    with mock.patch("builtins.open") as fFunc:
        fFunc.read = DATA_STR

        with mock.patch("dlpt.json.removeComments") as rmCommentsFunc:
            rmCommentsFunc.return_value = DATA_STR

            data = dlpt.json.read(tmp_path)
            assert isinstance(data, dict)

            assert len(data) == 2
            assert data["asd"] == "qwe"
            assert data["zxc"] == 123


def test_write(tmp_path):
    filePath = os.path.join(tmp_path, 'jsonTest.json')

    DATA = {
        "asd": "qwe",
        "zxc": 123,
        "ert": {
            "fgh": 456
        }
    }

    dlpt.json.write(DATA, filePath)
    data = dlpt.json.read(filePath)
    assert data == DATA


class _JsonTestClass():
    def __init__(self):
        self.public = 123
        self._private = '321'
        self.nested = [_JsonTestSubclass()]

    def someMethod(self):
        pass


class _JsonTestSubclass():
    def __init__(self):
        self.nestedPublic = 456
        self._nestedPrivate = '654'


def test_readWriteJsonpickle(tmp_path):
    filePath = os.path.join(tmp_path, 'jsonTest.json')

    wData = _JsonTestClass()
    dlpt.json.writeJsonpickle(wData, filePath)

    rData = dlpt.json.readJsonpickle(filePath)

    assert isinstance(rData, _JsonTestClass)
    assert rData.public == 123
    assert rData._private == '321'
    assert rData.nested[0].nestedPublic == 456
    assert rData.nested[0]._nestedPrivate == '654'
