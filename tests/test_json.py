import json
import os

import pytest

import dlpt
import dlpt.log as log

from dlpt.tfix import *


def test_jsonFileValidation(tmp_path):
    filePath = os.path.join(tmp_path, 'jsonTest.json')

    # JSON file checking
    # create empty file
    with open(filePath, 'w+') as fHandler:
        pass
    dlpt.pth.check(filePath)
    assert dlpt.json.check(filePath) is False
    with pytest.raises(Exception):
        dlpt.json.read(filePath)

    # create fake json file with invalid syntax
    dataStr = "{\n\t\"asd\": \"qwe\",\n\t\"zxc: 123\n}"  # missing "" in zxc
    with open(filePath, 'w+') as fHandler:
        fHandler.truncate(0)
        fHandler.seek(0)
        fHandler.write(dataStr)
    assert dlpt.json.check(filePath) is False
    with pytest.raises(Exception):
        dlpt.json.read(filePath)


def test_rwDict(tmp_path):
    def _check(data: dict, originalData: dict):
        assert dlpt.utils.areDictKeysEqual(data, originalData)
        assert dlpt.utils.areDictValuesEqual(data, originalData)
        assert (data['asd'] == 'qwe') and (data['zxc'] == 123)

    filePath = os.path.join(tmp_path, 'jsonTest.json')

    # test data
    testData = {
        'asd': 'qwe',
        'zxc': 123
    }

    # create valid json file
    with open(filePath, 'w+') as fHandler:
        json.dump(testData, fHandler)
    assert dlpt.json.check(filePath) is True
    jsonData = dlpt.json.read(filePath)
    _check(jsonData, testData)

    # write Json file
    dlpt.pth.removeFile(filePath)
    dlpt.json.write(testData, filePath)
    assert dlpt.json.check(filePath) is True
    jsonData = dlpt.json.read(filePath)
    _check(jsonData, testData)

    # JSON with comments
    dataStr = """
    // comment at the beginning
    {
        // single line comment
        // single line comment with nested // (for example path separator)
        /* single line comment with * */
        /* single line comment with // inside */
        /* multiline
comment
        */
        "asd": "qwe", // comment on the line
        "zxc": 123 /* comment on the line */
    }
    /* end comment*/
    """
    with open(filePath, "w+") as fHandler:
        fHandler.write(dataStr)
    jsonData = dlpt.json.read(filePath)
    _check(jsonData, testData)


class JsonTestClass():
    def __init__(self):
        self.public = 123
        self._private = '321'
        self.nested = [JsonTestSubclass()]

    def someMethod(self):
        pass


class JsonTestSubclass():
    def __init__(self):
        self.nestedPublic = 456
        self._nestedPrivate = '654'


@pytest.mark.usefixtures("closeAllLogHandlers")
def test_rwJsonpickleClass(tmp_path):
    filePath = os.path.join(tmp_path, 'jsonTest.json')

    # object from globally available module
    data = log.LogHandler()
    dlpt.json.writeJsonpickle(data, filePath)
    jsonData = dlpt.json.readJsonpickle(filePath)
    assert isinstance(jsonData, log.LogHandler)

    # module from this file
    data = JsonTestClass()
    dlpt.json.writeJsonpickle(data, filePath)
    jsonData: JsonTestClass = dlpt.json.readJsonpickle(filePath, [JsonTestClass, JsonTestSubclass])
    assert isinstance(jsonData, JsonTestClass)
    assert isinstance(jsonData.public, int)
    assert jsonData.public == 123
    assert isinstance(jsonData.nested[0], JsonTestSubclass)
