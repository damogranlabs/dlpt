import copy
import os
import sys

import pytest

import dlpt

THIS_MODULE = sys.modules[__name__]

TEST_VAR_PUBLIC = "aka public"
_TEST_VAR_PRIVATE = "aka private"


def publicFunc():
    pass


def _privateFunc():
    pass


class PublicClass():
    pass


class _PrivateClass():
    pass


@pytest.mark.parametrize("value,digits,expected", [
    (1234, None, "1234.00"),
    (1234, 0, "1234"),
    (1234, 2, "1234.00"),
    (987.1234, 4, "987.1234"),
    (987.1234, 4, "987.1234"),
    (-1234, None, "-1234.00"),
    (-987.1234, None, "-987.12"),
    (0x1234, None, "4660.00"),
    (-0x1234, None, "-4660.00")
])
def test_floatConversion(value, digits, expected):
    if digits is None:
        assert dlpt.utils.floatToStr(value) == expected
    else:
        assert dlpt.utils.floatToStr(value, digits) == expected


@pytest.mark.parametrize("value,expectedInt,expectedFloat", [
    ("1234", 1234, 1234.0),
    ("987.1234", 987, 987.1234),
    ("-1234", -1234, -1234.0),
    ("-987.1234", -987, -987.1234),
    (" 1234", 1234, 1234.0),
    ("  987.1234 ", 987, 987.1234),
    (" -1234", -1234, -1234),
    ("  -987.1234 ", -987, -987.1234),
    ("0x1234", 0x1234, 0x1234),
    (" 0x1234 ", 0x1234, 0x1234),
    ("-0x1234", -0x1234, -0x1234)
])
def test_getNumber(value, expectedInt, expectedFloat):
    assert dlpt.utils.getIntFromStr(value) == expectedInt
    assert dlpt.utils.getFloatFromStr(value) == expectedFloat


def test_getNumExceptions():
    with pytest.raises(Exception):
        assert dlpt.utils.getIntFromStr("a6")
    with pytest.raises(Exception):
        assert dlpt.utils.getFloatFromStr("-a6")


def test_listOperations():
    # NOTE: list operations does not necessary maintain items order
    listOne = [1, 3, 5]
    listTwo = [1, 3, 6, 9]
    listThree = copy.copy(listOne)
    listThree.append(10)
    expectedIntersection = [1, 3]
    expectedDiff = [5, 6, 9]

    assert dlpt.utils.getListStr(listOne) == "1, 3, 5"
    listStr = dlpt.utils.getListStr(listOne, "\n\t")
    assert listStr == "1\n\t3\n\t5"
    assert dlpt.utils.getListStr([]) == ""

    assert dlpt.utils.areListValuesEqual(listOne, listTwo) is False
    assert dlpt.utils.areListValuesEqual([], []) is True
    assert dlpt.utils.areListValuesEqual(listOne, listOne) is True
    assert dlpt.utils.areListValuesEqual(listOne, listThree) is False

    assert dlpt.utils.getListIntersection([], []) == []
    assert dlpt.utils.getListIntersection(listOne, []) == []
    assert dlpt.utils.areListValuesEqual(dlpt.utils.getListIntersection(listOne, listTwo), [1, 3]) is True

    assert dlpt.utils.getListDifference([], []) == []
    assert dlpt.utils.areListValuesEqual(dlpt.utils.getListDifference(listOne, []), listOne) is True
    assert dlpt.utils.areListValuesEqual(dlpt.utils.getListDifference([], listOne), listOne) is True
    assert dlpt.utils.areListValuesEqual(dlpt.utils.getListDifference(listOne, listTwo), expectedDiff) is True
    assert dlpt.utils.areListValuesEqual(dlpt.utils.getListDifference(listTwo, listOne), expectedDiff) is True

    listTwo = [3, 6, 1, 9]  # same list as listTwo before, but changed values order
    assert dlpt.utils.areListValuesEqual(dlpt.utils.getListIntersection(listOne, listTwo), expectedIntersection) is True
    assert dlpt.utils.areListValuesEqual(dlpt.utils.getListDifference(listOne, listTwo), expectedDiff) is True

    mergedLists = listOne + listTwo
    expectedItems = [1, 3, 5, 6, 9]
    assert dlpt.utils.removeListDuplicates([]) == []
    assert dlpt.utils.areListValuesEqual(dlpt.utils.removeListDuplicates(listOne), listOne) is True
    assert dlpt.utils.areListValuesEqual(dlpt.utils.removeListDuplicates(mergedLists), expectedItems) is True


def test_listStringSearch():
    testString = 'my test string'
    testStringsList = [
        f"asdsda{testString}qweqwe",
        f"asdsda123123",
        f"asdsda456{testString}",
        f"{testString}09-=qweqwe",
        f"{testString}"
    ]
    assert dlpt.utils.searchStrInLines(testString, testStringsList) == 0
    assert dlpt.utils.searchStrInLines(testString, testStringsList[1:]) == 1
    assert dlpt.utils.searchStrInLines(testString, testStringsList[2:]) == 0
    assert dlpt.utils.searchStrInLines(testString, testStringsList[3:]) == 0
    assert dlpt.utils.searchStrInLines(testString, testStringsList, True) == (len(testStringsList) - 1)
    assert dlpt.utils.searchStrInLines("asd", testStringsList, True) is None


def test_dictOperations():
    dictOne = {"1": "one", "2": 2, 3: 3.3}
    dictTwo = {"2": 2, "1": "one", 3: 3.3}
    assert dlpt.utils.areDictKeysEqual(dictOne, dictOne) is True
    assert dlpt.utils.areDictKeysEqual(dictOne, dictTwo) is True
    assert dlpt.utils.areDictValuesEqual(dictOne, dictOne) is True
    assert dlpt.utils.areDictValuesEqual(dictOne, dictTwo) is True

    dictTwo = {"2": 2, "1": "one", 3: 3.3, "four": " four"}
    assert dlpt.utils.areDictKeysEqual(dictOne, dictTwo) is False
    assert dlpt.utils.areDictValuesEqual(dictOne, dictTwo) is False

    # try with dicst that hold classes
    dictOne = {"1": TestDictClass(1, 2, 3), 3: TestDictClass(4, 5, 6)}
    dictTwo = {"100": TestDictClass(1, 2, 3), 300: TestDictClass(4, 5, 6)}
    assert dlpt.utils.areDictValuesEqual(dictOne, dictOne) is True
    assert dlpt.utils.areDictValuesEqual(dictOne, dictTwo) is False


def test_mapDictToClass():
    dInstance = TestDictClass(1, 2, 3)
    d = dInstance.__dict__.copy()

    cInstance = TestDictClass(4, 5, 6)
    c = dlpt.utils.mapDictToClass(cInstance, d)

    assert isinstance(c, TestDictClass)
    assert isinstance(cInstance, TestDictClass)

    assert c.two == dInstance.two


def test_getObjectVariables():
    cInstance = TestDictClass(1, 2, 3)
    publicVars = dlpt.utils.getObjPublicVars(cInstance)
    assert len(publicVars.keys()) == 3

    assert "one" in publicVars
    assert "two" in publicVars
    assert "_private" not in publicVars
    assert "__superPrivate" not in publicVars

    assert publicVars["one"] == 1


def test_getObjectMethods():
    # check class methods when instance is given
    cInstance = TestDictClass(1, 2, 3)
    methods = dlpt.utils.getObjPublicMethods(cInstance)
    assert ("one" not in methods) and ("_private" not in methods) and ("_superPrivate" not in methods)

    assert "normal" in methods
    assert callable(methods["normal"])
    assert methods["normal"]() == "normalVal"

    assert ("static" not in methods) and ("_hidden" not in methods) and ("__veryHidden" not in methods)


def test_getCallableObjectsFromModule():
    callableObj = dlpt.utils.getCallablesFromModule(THIS_MODULE)

    assert publicFunc.__name__ in callableObj
    assert id(publicFunc) == id(callableObj[publicFunc.__name__])
    assert PublicClass.__name__ in callableObj
    assert id(PublicClass) == id(callableObj[PublicClass.__name__])

    # variables, private funcs/classes
    assert TEST_VAR_PUBLIC not in callableObj
    assert _TEST_VAR_PRIVATE not in callableObj
    assert _privateFunc.__name__ not in callableObj
    assert _PrivateClass.__name__ not in callableObj


def test_getPublicClassesFromModule():
    classes = dlpt.utils.getPublicClassesFromModule(THIS_MODULE)

    assert PublicClass.__name__ in classes
    assert id(PublicClass) == id(classes[PublicClass.__name__])

    # variables, private funcs/classes
    assert TEST_VAR_PUBLIC not in classes
    assert _TEST_VAR_PRIVATE not in classes
    assert _privateFunc.__name__ not in classes
    assert _PrivateClass.__name__ not in classes


def test_getPublicFunctionsFromModule():
    functions = dlpt.utils.getPublicFunctionsFromModule(THIS_MODULE)

    assert publicFunc.__name__ in functions
    assert id(publicFunc) == id(functions[publicFunc.__name__])

    # variables, private funcs/classes
    assert TEST_VAR_PUBLIC not in functions
    assert _TEST_VAR_PRIVATE not in functions
    assert _privateFunc.__name__ not in functions
    assert PublicClass.__name__ not in functions
    assert _PrivateClass.__name__ not in functions


def test_callerLocation():
    def _testFunc1() -> str:
        return _testFunc2()

    def _testFunc2() -> str:
        caller = dlpt.utils.getCallerLocation()
        return caller

    def _testFunc3() -> str:
        caller = dlpt.utils.getCallerLocation()
        return caller

    caller = _testFunc1()
    assert "_testFunc1" in caller
    assert os.path.abspath(__file__).lower() in caller.lower()

    caller = _testFunc3()
    assert "test_callerLocation" in caller
    assert os.path.abspath(__file__).lower() in caller.lower()

    assert "unable to display" in dlpt.utils.getCallerLocation(100)

    assert "unable to display" in dlpt.utils.getCallerLocation(100)


class TestDictClass():
    def __init__(self, one, two, three):
        self.one = one
        self.two = two
        self.three = three

        self._private = "asd"
        self.__superPrivate = "qwe"

    def normal(self):
        return "normalVal"

    @staticmethod
    def static():
        return "staticVal"

    def _hidden(self):
        pass

    def __veryHidden(self):
        pass
