import json
import os
from unittest import mock

import pytest

import dlpt


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
    data_str = dlpt.json.remove_comments(DATA_STR)
    data = json.loads(data_str)

    assert data == DATA


def test_read(tmp_path):
    DATA_STR = '{"asd": "qwe","zxc": 123}'

    with mock.patch("builtins.open") as file_func:
        file_func.read = DATA_STR

        with mock.patch("dlpt.json.remove_comments") as rm_comments_func:
            rm_comments_func.return_value = DATA_STR

            data = dlpt.json.read(tmp_path)
            assert isinstance(data, dict)

            assert len(data) == 2
            assert data["asd"] == "qwe"
            assert data["zxc"] == 123


def test_write(tmp_path):
    file_path = os.path.join(tmp_path, "jsonTest.json")

    DATA = {"asd": "qwe", "zxc": 123, "ert": {"fgh": 456}}

    dlpt.json.write(DATA, file_path)
    data = dlpt.json.read(file_path)
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
        self.nested_public = 456
        self._nested_private = "654"


def test_rw_jsonpickle(tmp_path):
    file_path = os.path.join(tmp_path, "jsonTest.json")

    w_data = _JsonTestClass()
    dlpt.json.write_jsonpickle(w_data, file_path)

    r_data = dlpt.json.read_jsonpickle(file_path)

    assert isinstance(r_data, _JsonTestClass)
    assert r_data._private == "321"
    assert r_data.nested[0].nested_public == 456
    assert r_data.nested[0]._nested_private == "654"
