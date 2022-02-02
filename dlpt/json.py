"""
Read and write JSON files, JSON files with comments and (un)picklable JSON data.
"""
import json
import jsonpickle
import re
from typing import Dict, Optional, Union, Any, List, cast

import dlpt


def check(file_path: str) -> bool:
    """Check if given file is a valid JSON file.

    Args:
        file_path: path to a file to check.

    Returns:
        True if file is a valid JSON file, False otherwise.
    """
    file_path = dlpt.pth.check(file_path)
    try:
        with open(file_path, "r") as f:
            json.load(f)
        return True
    except Exception as err:
        return False


def remove_comments(data_str: str) -> str:
    """Return given string with removed C/C++ style `comments`_.

    Args:
        data_str: string to remove comments from.

    Returns:
        Input string without C/C++ style comments.

    .. _comments:
        https://stackoverflow.com/a/241506
    """

    def replacer(match: re.match) -> str:
        s = match.group(0)
        if s.startswith("/"):
            return " "  # note: a space and not an empty string
        else:
            return s

    pattern = re.compile(r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"', re.DOTALL | re.MULTILINE)

    return re.sub(pattern, replacer, data_str)


def read(file_path: str) -> Dict[str, Any]:
    """Open the given JSON file, strip comments and return dictionary data.

    Args:
        file_path: path to a file that needs to be parsed.

    Returns:
        Data (dictionary) of a given JSON file.
    """
    file_path = dlpt.pth.check(file_path)
    with open(file_path, "r") as f:
        data_str = remove_comments(f.read())
        data = json.loads(data_str)

    return data


def write(data: Dict[str, Any], file_path: str, indent: int = 2, sort_keys: bool = True, *args):
    """Write given data to a file in a JSON format.

    Args:
        data: serializable object to store to a file in JSON format.
        file_path: destination file path.
        indent: number of spaces to use while building file line indentation.
        sort_keys: if True, data keys are sorted alphabetically, else
            left unchanged.
        *args: `json.dump()` additional arguments.
    """
    with open(file_path, "w+") as fHandler:
        json.dump(data, fHandler, sort_keys=sort_keys, indent=indent)


def read_jsonpickle(file_path: str, classes: Optional[Union[object, List[object]]] = None) -> Any:
    """Read given file and return unpicklable data - python objects with
    `jsonpickle`_ module.

    Args:
        file_path: path to a file that needs to be read.
        classes: see `jsonpickle`_ `decode()` docstring. TLDR: if un-picklable
            objects are from modules which are not globally available,
            use ``classes`` arg to specify them.

    Returns:
        Python object(s) of unpickled JSON data.

    .. _jsonpickle:
        https://pypi.org/project/jsonpickle/
    """
    dlpt.pth.check(file_path)
    with open(file_path, "r") as f:
        data_str = f.read()
    data = jsonpickle.decode(data_str, classes=classes)

    return data


def write_jsonpickle(data: Any, file_path: str, indent: int = 2):
    """Write given data to a file in a JSON format with `jsonpickle`_ module,
    which adds data type info for unpickling with :func:`read_jsonpickle()`.

    Args:
        data: serializable object to store to a file in JSON format.
        file_path: destination file path.
        indent: number of spaces for line indentation.

    .. _jsonpickle:
        https://pypi.org/project/jsonpickle/
    """
    data_str = cast(str, jsonpickle.encode(data, indent=indent))
    with open(file_path, "w+") as f:
        f.write(data_str)
