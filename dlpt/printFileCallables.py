"""
Print a list of all callable objects (functions/classes) from a given python file.
See usage with "--help" argument.
"""
import argparse
import inspect
import os
from typing import Any, List, Optional

import dlpt

INDENT_STR = "    "  # \t can give a large offset.


def getCallableObjectsStr(filePath: str, includePrivate: bool = False) -> List[str]:
    """ Get a printable list of strings of all callable objects (functions, 
        classes, methods) from a given python file.

    NOTE: file must be syntactically correct - importable, since this function 
        performs a dynamic import.
    NOTE: this function is meant for test/code development, not for actual 
        production usage.

    Args:
        filePath: path to a file to check for object definitions.
        includePrivate: if True, object that starts with '_' are also added. 
            NOTE: '__' objects are always ignored.

    Returns:
        List of string representation of callable objects from a given file.
    """
    dlpt.pth.check(filePath)
    importer = dlpt.importer.ModuleImporter(filePath)
    module = importer.getModule()

    lines: List[str] = []

    def _getMembers(lines: List[str], reference: Any, modulePath: str, indent: Optional[str] = ""):
        for member in inspect.getmembers(reference):
            name, ref = member

            if name.startswith("__"):
                continue
            if name.startswith("_"):
                if not includePrivate:
                    continue

            isClass = False
            isMethod = False
            if inspect.isclass(ref):
                isClass = True
                # print(f"{indent}{name}()")  # what about derived classes?
                #_printMembers(ref, modulePath, indent + "\t")
                # continue
            elif inspect.isfunction(ref):
                pass
            elif inspect.ismethod(ref):
                isMethod = True
            else:
                continue

            try:
                refFilePath = inspect.getfile(ref)
                if not os.path.samefile(modulePath, refFilePath):
                    continue  # not a function from this file (might be from * import)
            except Exception as err:
                continue  # might fail for built-in types or type-stub items

            params = inspect.signature(ref)
            refStr = f"{name}{params}"

            if isMethod:
                refStr = INDENT_STR + refStr
            refStr = f"{indent}{refStr}"

            lines.append(refStr)

            if isClass:
                _getMembers(lines, ref, modulePath, indent + INDENT_STR)

    _getMembers(lines, module, filePath)

    return lines


def printCallableObjects(filePath: str, includePrivate: bool):
    """ Print a list of all callable objects (functions/classes) from a 
        given python file.

    NOTE: file must be syntactically correct - importable, since this function 
        performs a dynamic import.
    NOTE: this function is meant for test/code development, not for actual 
        production usage.

    Args:
        filePath: path to a file to check for object definitions.
        includePrivate: if True, object that starts with '_' are also added. 
            NOTE: '__' objects are always ignored.
    """
    lines = getCallableObjectsStr(filePath, includePrivate)
    for line in lines:
        print(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__file__, description="Development utility for file callable objects inspection")
    parser.add_argument("file", help="Path to Python file to analyse.")
    parser.add_argument("-p", "--includePrivate", required=False, help="Include private functions in output report.")
    args = parser.parse_args()

    printCallableObjects(args.file, args.includePrivate)
