"""
Read and write JSON files, JSON files with comments and (un)picklable JSON data.
"""
import json
import jsonpickle
import re
from typing import Dict, Optional, Union, Any, List

import dlpt


def check(filePath: str) -> bool:
    """
    Return True if file is a valid non-empty JSON file, False otherwise.
        filePath: path to a file to check.
    """
    filePath = dlpt.pth.check(filePath)
    try:
        with open(filePath, 'r') as fHandler:
            json.load(fHandler)
        return True
    except Exception as err:
        return False


def read(filePath: str) -> Dict[str, Any]:
    """
    Open given JSON file, strip comments and return dictionary data.
        filePath: path to a file that needs to be read and returned.
    """
    filePath = dlpt.pth.check(filePath)
    with open(filePath, 'r') as fHandler:
        dataStr = removeComments(fHandler.read())
        data = json.loads(dataStr)

    return data


def removeComments(dataStr: str) -> str:
    """
    Return given string with removed C/C++ style comments.
    https://stackoverflow.com/a/241506
        dataStr: string from where comments will be removed.
    """
    def replacer(match: re.Match) -> str:
        s = match.group(0)
        if s.startswith("/"):
            return " "  # note: a space and not an empty string
        else:
            return s

    pattern = re.compile(r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"', re.DOTALL | re.MULTILINE)

    return re.sub(pattern, replacer, dataStr)


def write(data: Dict[str, Any], filePath: str, indent: int = 2, sortKeys: bool = True):
    """
    Write given data to a file in a JSON format.
        : data: serializable object to store to a file in JSON format. 
        filePath: destination file path.
        indent: number of spaces to use while building file line indentation.
        sortKeys: if True, data keys are sorted alphabetically, else 
            left unchanged.
    """
    with open(filePath, 'w+') as fHandler:
        json.dump(data, fHandler, sort_keys=sortKeys, indent=indent)


def writeJsonpickle(data: Any, filePath: str, indent: int = 2):
    """
    Write given data to a file in a JSON format with 'jsonpickle' module, 
    which adds data type info for unpickling with readJsonpickle().
    jsonpickle: https://pypi.org/project/jsonpickle/
        : data: serializable object to store to a file in JSON format.
        filePath: destination file path.
        indent: number of spaces for line indentation.
    """
    dataStr = jsonpickle.encode(data, indent=indent)
    with open(filePath, "w+") as fHandler:
        fHandler.write(dataStr)


def readJsonpickle(filePath: str,
                   classes: Optional[Union[object, List[object]]] = None) -> Any:
    """
    Read given file and return unpicklable data - python objects
    jsonpickle: https://pypi.org/project/jsonpickle/
        filePath: path to a file that needs to be read and returned.
        classes: see jsonpickle decode() docstring. TLDR: if un-picklable
            objects are from modules which are not globally available, 
            use 'classes' arg to specify them.
    """
    dlpt.pth.check(filePath)
    with open(filePath, "r") as fHandler:
        dataStr = fHandler.read()
    data = jsonpickle.decode(dataStr, classes=classes)

    return data
