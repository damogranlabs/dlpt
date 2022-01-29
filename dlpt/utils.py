"""
Various utility functions that simplify everyday code. Example:
- converting numbers from/to string
- comparing lists, dictionaries
- code inspection
- strings operations, 
- ...
"""
import inspect
from typing import Optional, Callable, Dict, Any, List
from types import ModuleType

import dlpt


def float_to_str(number: float, show_num_of_digits: int = 2) -> str:
    """Convert float number with any number of decimal digits and return string
    with ``showNumbOfDigits`` places after ``.``.

    Args:
        number: float number to convert to string.
        show_num_of_digits: number of decimal places (characters) that are
            added/stripped after ``.``.
    """
    number = round(number, show_num_of_digits)
    if show_num_of_digits == 0:
        number_str = str(int(number))
    else:
        number_str = "{:.{}f}".format(number, show_num_of_digits)

    return number_str


def get_int_from_str(number: str) -> int:
    """Return integer representation of a given number string.
    HEX number strings must start with ``0x``. Negative numbers are also supported.

    Args:
        number_str: int/float string representation of a given number.
    """
    num = int(get_float_from_str(number))

    return num


def get_float_from_str(number: str) -> float:
    """Return float representation of a given number string.
    HEX number strings must start with ``0x``.

    Args:
        number_str: int/float/string representation of a given number.
    """
    number_str = number.strip()
    is_negative = False
    if "-" in number_str:
        number_str = number_str.replace("-", "")
        is_negative = True

    if number_str.lower().startswith("0x"):
        num = float(int(number_str, 16))
    else:
        num = float(number_str)

    if is_negative:
        num = -num

    return num


def get_list_intersection(l1: List[Any], l2: List[Any]) -> List[Any]:
    """Return intersection of a given lists.

    Note:
        Operation does not necessary maintain items order!

    Note:
        Only applicable for a lists with primitive types - nested lists will
        fail - can't set().

    Args:
        l1: first list to compare.
        l2: second list to compare.
    """
    intersection = list(set(l1) & set(l2))

    return intersection


def get_list_str(data: List[Any], separator: str = ", ") -> str:
    """Return a human readable list string (for printing purposes).

    Args:
        data: list to transform to string.
        separator: separator to join list items with.
    """
    data_str: List[str] = []
    for item in data:
        data_str.append(str(item))
    readable_str = separator.join(data_str)

    return readable_str


def get_list_difference(l1: List[Any], l2: List[Any]) -> List[Any]:
    """Return difference (items that are unique just to a one of given lists)
    of a given lists.

    Note:
        Operation does not necessary maintain items order!

    Args:
        l1: first list to compare.
        l2: second list to compare.
    """
    difference = list(set(l1).symmetric_difference(set(l2)))

    return difference


def remove_list_duplicates(data: List[Any]) -> List[Any]:
    """Return a list of items without any duplicates.

    Note:
        Operation does not necessary maintain items order!

    Args:
        data: list with possibly duplicated items.
    """
    data = list(set(data))

    return data


def search_str_in_lines(str_to_search: str, lines: List[str], exact_match: bool = False) -> Optional[int]:
    """Return index of a first line where ``str_to_search`` string can be found.
        Otherwise, return None.

    Args:
        str_to_search: string to search in lines.
        lines: list of strings, where 'str_to_search' is searched.
        exact_match: if True, only exact 'str_to_search' string is
            compared in lines. Otherwise, only string presence is checked.
    """
    for idx, line in enumerate(lines):
        if exact_match:
            if str_to_search == line:
                return idx
        else:
            if str_to_search in line:
                return idx

    return None


def are_list_values_equal(l1: List[Any], l2: List[Any]) -> bool:
    """Return True if lists have the same values, False otherwise.

    Note:
        Items order is not respected. If order must also be respected,
        just use list comparison: ``l1 == l2``

    Note:
        List items must be `hashable`_.

    Args:
        l1: first list to compare.
        l2: second list to compare.

    .. _hashable:
        https://docs.python.org/3.6/library/collections.html#collections.Counter
    """
    if set(l1) == set(l2):
        return True
    else:
        return False


def are_dict_keys_equal(d1: Dict[Any, Any], d2: Dict[Any, Any]) -> bool:
    """Return True if dicts have the same keys, False otherwise.

    Args:
        d1: first dict to compare
        d2: second dict to compare
    """
    if len(d1) == len(d2):
        d1Keys = list(d1.keys())
        d2Keys = list(d2.keys())
        haveSameKeys = are_list_values_equal(d1Keys, d2Keys)

        return haveSameKeys
    else:
        return False


def are_dict_values_equal(d1: Dict[Any, Any], d2: Dict[Any, Any]) -> bool:
    """Return True if dicts have the same values, False otherwise.

    Note:
        When comparing dict items that are not simple types (int, str, ...),
        function might return False if comparing different instances, regardles
        if object type is the same.

    Args:
        d1: first dict to compare
        d2: second dict to compare
    """
    d1Values = list(d1.values())
    d2Values = list(d2.values())
    haveSameValues = are_list_values_equal(d1Values, d2Values)

    return haveSameValues


def map_dict_to_class(obj: object, data: Dict[str, Any]) -> object:
    """Return an object ``obj`` updated by the values of data dictionary.

    Note:
        Only data keys, that match obj variable names are updated.
        Others are silently ignored.

    Args:
        obj: object instance (class) whose values must be updated.
    """
    for key, value in data.items():
        if hasattr(obj, key):
            setattr(obj, key, value)

    return obj


def get_obj_public_vars(obj: object) -> Dict[str, Any]:
    """Return a dictionary of class variables that does not start with '_' or '__'.
        Each item represents: 'name': <value>

    Note:
        If given ``obj`` is a class reference, only 'public' static variables
        are returned. If given ``obj`` is a class instance, 'public' static and
        instance variables are returned.

    Args
        obj: object (class) to inspect.
    """
    relevant_vars = {}

    for key in dir(obj):
        if not key.startswith("_"):
            value = getattr(obj, key)
            if not callable(value):
                relevant_vars[key] = value

    return relevant_vars


def get_obj_public_methods(obj: object) -> Dict[str, Callable[..., Any]]:
    """Return a dictionary of object public methods that does not start
    with '_' or '__'. Each item represents: 'name': <reference to a method>

    Note:
        Only class 'public' methods are returned, without ``@staticmethod``.
        They are of type '<bound method...>'

    Args:
        obj: object to inspect.
    """
    functions = inspect.getmembers(obj, inspect.ismethod)

    relevant_methods = {}
    for func in functions:
        name, reference = func
        if not name.startswith("_"):
            relevant_methods[name] = reference

    return relevant_methods


def get_module_callables(module_instance: ModuleType) -> Dict[str, Callable[..., Any]]:
    """Return a dictionary of public methods that does not start with '_' or '__'.
    Each item represents: 'name': <reference to a callable object>

    Args:
        module_instance: module object to inspect.
    """
    callable_objects = {}
    for name, value in module_instance.__dict__.items():
        if callable(value):
            if not name.startswith("_"):
                callable_objects[name] = value

    return callable_objects


def get_module_public_classes(module_instance: ModuleType) -> Dict[str, Callable[..., Any]]:
    """Return a dictionary of public classes that does not start with '_' or '__'.
    Each item represents: 'name': <reference to a callable class>

    Args:
        module_instance: module object to inspect.
    """
    relevant_methods = {}
    objects = get_module_callables(module_instance)
    for name, value in objects.items():
        if inspect.isclass(value):
            relevant_methods[name] = value

    return relevant_methods


def get_module_public_functions(module_instance: ModuleType) -> Dict[str, Callable[..., Any]]:
    """Get a list of references to all callable objects from a given module
    handler.

    Args:
        module_instance: module object to inspect.
    """
    relevant_methods = {}
    objects = get_module_callables(module_instance)
    for name, value in objects.items():
        if inspect.isfunction(value):
            relevant_methods[name] = value

    return relevant_methods


def get_caller_location(depth: int = 2) -> str:
    """Return a function/location/line number of a caller function.
    Return string format: "<function()> @ <absolute file path>:<line number>"

    Note:
        Using inspect module can be slow -> ``inspect.getouterframes()`` call
        ``inspect.stack()`` which `actually read files`_.

    Warning:
        While steping through code in a debug session, stack can be full of
        a debugger (example: ptvsd) entries.

    Args:
        depth: stack frame depth inspection. The first (index = 0) entry in the
            returned list represents current frame; the last entry represents
            the outermost call on frame’s stack.

    .. _actually read files:
        https://stackoverflow.com/questions/17407119/python-inspect-stack-is-slow
    """
    current_depth = 0
    location_str = f"<unable to display caller function (depth = {depth})>"

    frame = inspect.currentframe()
    while frame:
        if current_depth == depth:
            file_path = frame.f_code.co_filename
            line_num = frame.f_lineno
            func_fame = frame.f_code.co_name
            location_str = f"{func_fame}() @ {file_path}:{line_num}"
            break
        elif frame.f_back:
            frame = frame.f_back
            current_depth = current_depth + 1
        else:
            break  # pragma: no cover

    return location_str
