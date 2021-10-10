"""
Read and write JSON files, JSON files with comments and (un)picklable JSON data.
"""
import json
import jsonpickle
import re
from typing import Dict, Optional, Union, Any, List, cast

import dlpt


def check(fPath: str) -> bool:
    """ Check if given file is a valid JSON file.

    Args:
        fPath: path to a file to check.

    Returns:
        True if file is a valid JSON file, False otherwise.
    """
    fPath = dlpt.pth.check(fPath)
    try:
        with open(fPath, 'r') as fHandler:
            json.load(fHandler)
        return True
    except Exception as err:
        return False


def removeComments(dataStr: str) -> str:
    """ Return given string with removed C/C++ style `comments`_.

    Args:
        dataStr: string to remove comments from.

    Returns:
        Input string without C/C++ style comments.

    .. _comments:
        https://stackoverflow.com/a/241506
    """
    def replacer(match: re.Match) -> str:
        s = match.group(0)
        if s.startswith("/"):
            return " "  # note: a space and not an empty string
        else:
            return s

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE)

    return re.sub(pattern, replacer, dataStr)


def read(fPath: str) -> Dict[str, Any]:
    """ Open the given JSON file, strip comments and return dictionary data.

    Args:
        fPath: path to a file that needs to be parsed.

    Returns:
        Data (dictionary) of a given JSON file.
    """
    fPath = dlpt.pth.check(fPath)
    with open(fPath, 'r') as fHandler:
        dataStr = removeComments(fHandler.read())
        data = json.loads(dataStr)

    return data


def write(data: Dict[str, Any],
          fPath: str,
          indent: int = 2,
          sortKeys: bool = True,
          *args):
    """ Write given data to a file in a JSON format.

    Args:
        data: serializable object to store to a file in JSON format. 
        fPath: destination file path.
        indent: number of spaces to use while building file line indentation.
        sortKeys: if True, data keys are sorted alphabetically, else 
            left unchanged.
        *args: `json.dump()` additional arguments.
    """
    with open(fPath, 'w+') as fHandler:
        json.dump(data, fHandler, sort_keys=sortKeys, indent=indent)


def readJsonpickle(fPath: str,
                   classes: Optional[Union[object, List[object]]] = None) -> Any:
    """Read given file and return unpicklable data - python objects with
    `jsonpickle`_ module.

    Args:
        fPath: path to a file that needs to be read.
        classes: see `jsonpickle`_ `decode()` docstring. TLDR: if un-picklable
            objects are from modules which are not globally available, 
            use ``classes`` arg to specify them.

    Returns:
        Python object(s) of unpickled JSON data.

    .. _jsonpickle:
        https://pypi.org/project/jsonpickle/
    """
    dlpt.pth.check(fPath)
    with open(fPath, "r") as fHandler:
        dataStr = fHandler.read()
    data = jsonpickle.decode(dataStr, classes=classes)

    return data


def writeJsonpickle(data: Any, fPath: str, indent: int = 2):
    """ Write given data to a file in a JSON format with `jsonpickle`_ module, 
    which adds data type info for unpickling with :func:`readJsonpickle()`.

    Args:
        data: serializable object to store to a file in JSON format.
        fPath: destination file path.
        indent: number of spaces for line indentation.

    .. _jsonpickle:
        https://pypi.org/project/jsonpickle/
    """
    dataStr = cast(str, jsonpickle.encode(data, indent=indent))
    with open(fPath, "w+") as fHandler:
        fHandler.write(dataStr)
