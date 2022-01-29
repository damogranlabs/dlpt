"""
Print a list of all callable objects (functions/classes) from a given python file.
See usage with "--help" argument.
"""
import argparse
import inspect
import os
from typing import Any, List

import dlpt

INDENT_STR = "    "  # \t can give a large offset.


def get_callable_objects_str(file_path: str, include_private: bool = False) -> List[str]:
    """Get a printable list of strings of all callable objects (functions,
        classes, methods) from a given python file.

    Note: file must be syntactically correct - importable, since this function
        performs a dynamic import.
    Note: this function is meant for test/code development, not for actual
        production usage.

    Args:
        file_path: path to a file to check for object definitions.
        include_private: if True, object that starts with '_' are also added.
            Note: '__' objects are always ignored.

    Returns:
        List of string representation of callable objects from a given file.
    """
    dlpt.pth.check(file_path)
    importer = dlpt.importer.ModuleImporter(file_path)
    module = importer.get_module()

    lines: List[str] = []

    def _get_members(lines: List[str], reference: Any, module_path: str, indent: str = ""):
        for member in inspect.getmembers(reference):
            name, ref = member

            if name.startswith("__"):
                continue
            if name.startswith("_"):
                if not include_private:
                    continue

            is_class = False
            is_method = False
            if inspect.isclass(ref):
                is_class = True
                # print(f"{indent}{name}()")  # what about derived classes?
                # _printMembers(ref, modulePath, indent + "\t")
                # continue
            elif inspect.isfunction(ref):
                pass
            elif inspect.ismethod(ref):
                is_method = True
            else:
                continue

            try:
                ref_file_path = inspect.getfile(ref)
                if not os.path.samefile(module_path, ref_file_path):
                    # not a function from this file (might be from * import)
                    continue
            except Exception as err:
                # might fail for built-in types or type-stub items
                continue

            params = inspect.signature(ref)
            ref_str = f"{name}{params}"

            if is_method:
                ref_str = INDENT_STR + ref_str
            ref_str = f"{indent}{ref_str}"

            lines.append(ref_str)

            if is_class:
                _get_members(lines, ref, module_path, indent + INDENT_STR)

    _get_members(lines, module, file_path)

    return lines


def print_callable_objects(file_path: str, include_private: bool):
    """Print a list of all callable objects (functions/classes) from a
        given python file.

    Note: file must be syntactically correct - importable, since this function
        performs a dynamic import.

    Note: this function is meant for test/code development, not for actual
        production usage.

    Args:
        file_path: path to a file to check for object definitions.
        include_private: if True, object that starts with '_' are also added.
            Note: '__' objects are always ignored.
    """
    lines = get_callable_objects_str(file_path, include_private)
    for line in lines:
        print(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__file__, description="Development utility for file callable objects inspection")
    parser.add_argument("file", help="Path to Python file to analyse.")
    parser.add_argument("-p", "--include_private", required=False, help="Include private functions in output report.")
    args = parser.parse_args()

    print_callable_objects(args.file, args.include_private)
