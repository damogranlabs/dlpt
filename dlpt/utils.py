"""
Various utility functions that simplify everyday code. Example:
- converting numbers from/to string
- comparing lists, dictionaries
- code inspection
- strings operations, 
- ...
"""
import inspect
import sys
from typing import Optional, Callable, Dict, Any, List
from types import ModuleType

import dlpt


def floatToStr(number: float, showNumOfDigits: int = 2) -> str:
    """
    Convert float number with any number of decimal digits and return string 
    with 'showNumbOfDigits' places after '.'.
        @param number: float number to convert to string.
        @param showNumOfDigits: number of decimal places (characters) that are 
            added/stripped after '.'.
    """
    number = round(number, showNumOfDigits)
    if showNumOfDigits == 0:
        numberStr = str(int(number))
    else:
        numberStr = "{:.{}f}".format(number, showNumOfDigits)

    return numberStr


def getIntFromStr(number: str) -> int:
    """
    Return int representation of a given number string. 
    HEX number strings must start with '0x'.
    Negative numbers are also supported.
        @param numberStr: int/float string representation of a given number.
    """
    num = int(getFloatFromStr(number))

    return num


def getFloatFromStr(number: str) -> float:
    """
    Return float representation of a given number string.
    HEX number strings must start with '0x'.
    Raise exception if unable to convert.
        @param numberStr: int/float/string representation of a given number.
    """
    numberStr = number.strip()
    isNegative = False
    if "-" in numberStr:
        numberStr = numberStr.replace("-", "")
        isNegative = True

    if numberStr.lower().startswith("0x"):
        num = float(int(numberStr, 16))
    else:
        num = float(numberStr)

    if isNegative:
        num = 0 - num

    return num


def getListIntersection(listOne: List[Any], listTwo: List[Any]) -> List[Any]:
    """
    Return intersection of a given lists.
    NOTE: operation does not necessary maintain items order!
    NOTE: only applicable for a lists with primitive types - nested lists will
        fail - can't set().
        @param listOne: first list to compare.
        @param listTwo: second list to compare.
    """
    intersection = list(set(listOne) & set(listTwo))

    return intersection


def getListStr(data: List[Any], separator: str = ', ') -> str:
    """
    Return a human readable list string (for printing purposes).
        @param data: list to transform to string.
        @param separator: separator to join list items with.
    """
    dataStr: List[str] = []
    for item in data:
        dataStr.append(str(item))
    readableStr = separator.join(dataStr)

    return readableStr


def getListDifference(listOne: List[Any], listTwo: List[Any]) -> List[Any]:
    """
    Return difference (items that are unique just to a one of given lists)
    of a given lists.
    NOTE: operation does not necessary maintain items order!
        @param listOne: first list to compare.
        @param listTwo: second list to compare.
    """
    difference = list(set(listOne).symmetric_difference(set(listTwo)))

    return difference


def removeListDuplicates(data: List[Any]) -> List[Any]:
    """
    Return a list of items without any duplicates.
    NOTE: operation does not necessary maintain items order!
        @param data: list with possibly duplicated items.
    """
    data = list(set(data))

    return data


def searchStrInLines(stringToSearch: str, lines: List[str], exactMatch: bool = False) -> Optional[int]:
    """
    Return index of a first line where 'stringToSearch' string can be found.
    Otherwise, return None.
        @param stringToSearch: string to search in lines.
        @param lines: list of strings, where 'stringToSearch' is searched.
        @param exactMatch: if True, only exact 'stringToSearch' string is 
            compared in lines. Otherwise, only string presence is checked.
    """
    for lineIndex, line in enumerate(lines):
        if exactMatch:
            if stringToSearch == line:
                return lineIndex
        else:
            if stringToSearch in line:
                return lineIndex

    return None


def areListValuesEqual(listOne: List[Any], listTwo: List[Any]) -> bool:
    """
    Return True if lists have the same values, False otherwise.
    NOTE: Items order is not respected. If order must also be respected,
        just use list comparison: `listOne == listTwo`
    NOTE: List items must be hashable, see:
        https://docs.python.org/3.6/library/collections.html#collections.Counter
        @param listOne: first list to compare.
        @param listTwo: second list to compare.
    """
    if set(listOne) == set(listTwo):
        return True
    else:
        return False


def areDictKeysEqual(d1: Dict[Any, Any], d2: Dict[Any, Any]) -> bool:
    """
    Return True if dicts have the same keys, False otherwise.
        @param d1: first dict to compare
        @param d2: second dict to compare
    """
    if len(d1) == len(d2):
        d1Keys = list(d1.keys())
        d2Keys = list(d2.keys())
        haveSameKeys = areListValuesEqual(d1Keys, d2Keys)

        return haveSameKeys
    else:
        return False


def areDictValuesEqual(d1: Dict[Any, Any], d2: Dict[Any, Any]) -> bool:
    """
    Return True if dicts have the same values, False otherwise.
        @param d1: first dict to compare
        @param d2: second dict to compare
    NOTE: when comparing dict items that are not simple types (int, str, ...), 
        function might return False if comparing different instances, regardles 
        if object type is the same.
    """
    d1Values = list(d1.values())
    d2Values = list(d2.values())
    haveSameValues = areListValuesEqual(d1Values, d2Values)

    return haveSameValues


def mapDictToClass(obj: object, data: Dict[str, Any]) -> object:
    """
    Return an object 'obj' updated by the values of data dictionary.
        @param obj: object instance (class) whose values must be updated.
    NOTE: only data keys, that match obj variable names are updated. 
        Others are silently ignored.
    """
    for key, value in data.items():
        if hasattr(obj, key):
            setattr(obj, key, value)

    return obj


def getObjPublicVars(obj: object) -> Dict[str, Any]:
    """
    Return a dictionary of class variables that does not start with '_' or '__'.
    Each item represents: 'name': <value>
        @param obj: object (class) to inspect.
            If given 'obj' is a class reference, only 'public' static variables
            are returned.
            If given 'obj' is a class instance, 'public' static and instance
            variables are returned.
    """
    relevantVariables = {}

    for key in dir(obj):
        if not key.startswith('_'):
            value = getattr(obj, key)
            if not callable(value):
                relevantVariables[key] = value

    return relevantVariables


def getObjPublicMethods(obj: object) -> Dict[str, Callable[..., Any]]:
    """
    Return a dictionary of object public methods that does not start with '_' or '__'.
    Each item represents: 'name': <reference to a method>
        @param obj: object to inspect.
    NOTE: Only class 'public' methods are returned, without @staticmethod. 
        They are of type '<bound method...>'
    """
    functions = inspect.getmembers(obj, inspect.ismethod)

    relevantMethods = {}
    for func in functions:
        name, reference = func
        if not name.startswith('_'):
            relevantMethods[name] = reference

    return relevantMethods


def getCallablesFromModule(moduleInstance: ModuleType) -> Dict[str, Callable[..., Any]]:
    """
    Return a dictionary of public methods that does not start with '_' or '__'.
    Each item represents: 'name': <reference to a callable object>
        @param moduleInstance: module object to inspect.
    """
    callableObjects = {}
    for name, value in moduleInstance.__dict__.items():
        if callable(value):
            if not name.startswith('_'):
                callableObjects[name] = value

    return callableObjects


def getPublicClassesFromModule(moduleInstance: ModuleType) -> Dict[str, Callable[..., Any]]:
    """
    Return a dictionary of public classes that does not start with '_' or '__'.
    Each item represents: 'name': <reference to a callable class>
        @param moduleInstance: module object to inspect.
    """
    relevantMethods = {}
    objects = getCallablesFromModule(moduleInstance)
    for name, value in objects.items():
        if inspect.isclass(value):
            relevantMethods[name] = value

    return relevantMethods


def getPublicFunctionsFromModule(moduleInstance) -> Dict[str, Callable[..., Any]]:
    """
    Get a list of references to  all callable objects from a given module handler.
        @param moduleInstance: module object to inspect.
    """
    relevantMethods = {}
    objects = getCallablesFromModule(moduleInstance)
    for name, value in objects.items():
        if inspect.isfunction(value):
            relevantMethods[name] = value

    return relevantMethods


def getCallerLocation(depth: int = 2) -> str:
    """
    Return a function/location/line number of a caller function.
    Return string format: "<function()> @ <absolute file path>:<line number>"
        @param depth: stack frame depth inspection.
            The first (index = 0) entry in the returned list represents current 
            frame; the last entry represents the outermost call on frame’s stack.
    NOTE: using inspect module can be slow -> inspect.getouterframes() call 
        inspect.stack() which actually read files:
        https://stackoverflow.com/questions/17407119/python-inspect-stack-is-slow
    WARNING: while steping through code in a debug session, stack can be full of
        a debugger (example: ptvsd) entries.
    """
    currentDepth = 0
    locationStr = f"<unable to display caller function (depth = {depth})>"

    frame = inspect.currentframe()
    while frame:
        if currentDepth == depth:
            filePath = frame.f_code.co_filename
            lineNum = frame.f_lineno
            funcName = frame.f_code.co_name
            locationStr = f"{funcName}() @ {filePath}:{lineNum}"
            break
        elif frame.f_back:
            frame = frame.f_back
            currentDepth = currentDepth + 1
        else:
            break  # pragma: no cover

    return locationStr


def pingAddress(ip: str, timeoutSec: float = 1) -> bool:
    """
    Ping given IP address with specified timeout for 'count' times and return 
    True on success, False otherwise.
        @param ip: ip address to ping.
        @param timeoutSec: max time that response from ping command is waited.

    NOTE: there is no 'count' parameter. This is due win10 'ping' timeout issues, 
        which can yield unpredictable times when using timeouts. Therefore, to
        wait for a specific state with pingAddress(), implement custom  for...loop.
        Ping timeout ('-w') is always set to a larger value than needed, while 
        subprocess is killed after given timeoutSec.
    """
    args = ["ping", ip, "-n", 1]

    # ping timeout issues, see comment note
    args.append("-w")
    args.append(int((timeoutSec + 1) * 1000))  # -w accepts msec

    try:
        proc = dlpt.proc.spawnSubproc(args, timeoutSec=timeoutSec, checkReturnCode=False)
    except dlpt.proc.SubprocTimeoutError as err:
        return False

    return not bool(proc.returncode)


def isDbgSession() -> bool:  # pragma: no cover
    """
    Return True if current process is executed in a debug session, False otherwise.
    """
    if sys.gettrace() is None:
        return False
    else:
        return True
