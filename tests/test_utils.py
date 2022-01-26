import copy
import os
import sys

import pytest

import dlpt

THIS_MODULE = sys.modules[__name__]

TEST_VAR_PUBLIC = "aka public"
_TEST_VAR_PRIVATE = "aka private"


def public_func():
    pass


def _private_func():
    pass


class PublicClass:
    pass


class _PrivateClass:
    pass


@pytest.mark.parametrize(
    "value,digits,expected",
    [
        (1234, None, "1234.00"),
        (1234, 0, "1234"),
        (1234, 2, "1234.00"),
        (987.1234, 4, "987.1234"),
        (987.1234, 4, "987.1234"),
        (-1234, None, "-1234.00"),
        (-987.1234, None, "-987.12"),
        (0x1234, None, "4660.00"),
        (-0x1234, None, "-4660.00"),
    ],
)
def test_float_to_str(value, digits, expected):
    if digits is None:
        assert dlpt.utils.float_to_str(value) == expected
    else:
        assert dlpt.utils.float_to_str(value, digits) == expected


@pytest.mark.parametrize(
    "value,expectedInt,expectedFloat",
    [
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
        ("-0x1234", -0x1234, -0x1234),
    ],
)
def test_get_num_from_str(value, expectedInt, expectedFloat):
    assert dlpt.utils.get_int_from_str(value) == expectedInt
    assert dlpt.utils.get_float_from_str(value) == expectedFloat


def test_get_num_from_str_err():
    with pytest.raises(Exception):
        assert dlpt.utils.get_int_from_str("a6")
    with pytest.raises(Exception):
        assert dlpt.utils.get_float_from_str("-a6")


def test_list_operations():
    # NOTE: list operations does not necessary maintain items order
    listOne = [1, 3, 5]
    listTwo = [1, 3, 6, 9]
    listThree = copy.copy(listOne)
    listThree.append(10)
    expectedIntersection = [1, 3]
    expectedDiff = [5, 6, 9]

    assert dlpt.utils.get_list_str(listOne) == "1, 3, 5"
    listStr = dlpt.utils.get_list_str(listOne, "\n\t")
    assert listStr == "1\n\t3\n\t5"
    assert dlpt.utils.get_list_str([]) == ""

    assert dlpt.utils.are_list_values_equal(listOne, listTwo) is False
    assert dlpt.utils.are_list_values_equal([], []) is True
    assert dlpt.utils.are_list_values_equal(listOne, listOne) is True
    assert dlpt.utils.are_list_values_equal(listOne, listThree) is False

    assert dlpt.utils.get_list_intersection([], []) == []
    assert dlpt.utils.get_list_intersection(listOne, []) == []
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_intersection(listOne, listTwo), [1, 3]) is True

    assert dlpt.utils.get_list_difference([], []) == []
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_difference(listOne, []), listOne) is True
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_difference([], listOne), listOne) is True
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_difference(listOne, listTwo), expectedDiff) is True
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_difference(listTwo, listOne), expectedDiff) is True

    listTwo = [3, 6, 1, 9]  # same list as listTwo before, but changed values order
    assert (
        dlpt.utils.are_list_values_equal(dlpt.utils.get_list_intersection(listOne, listTwo), expectedIntersection)
        is True
    )
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_difference(listOne, listTwo), expectedDiff) is True

    mergedLists = listOne + listTwo
    expectedItems = [1, 3, 5, 6, 9]
    assert dlpt.utils.remove_list_duplicates([]) == []
    assert dlpt.utils.are_list_values_equal(dlpt.utils.remove_list_duplicates(listOne), listOne) is True
    assert dlpt.utils.are_list_values_equal(dlpt.utils.remove_list_duplicates(mergedLists), expectedItems) is True


def test_search_str_in_lines():
    testString = "my test string"
    testStringsList = [
        f"asdsda{testString}qweqwe",
        f"asdsda123123",
        f"asdsda456{testString}",
        f"{testString}09-=qweqwe",
        f"{testString}",
    ]
    assert dlpt.utils.search_str_in_lines(testString, testStringsList) == 0
    assert dlpt.utils.search_str_in_lines(testString, testStringsList[1:]) == 1
    assert dlpt.utils.search_str_in_lines(testString, testStringsList[2:]) == 0
    assert dlpt.utils.search_str_in_lines(testString, testStringsList[3:]) == 0
    assert dlpt.utils.search_str_in_lines(testString, testStringsList, True) == (len(testStringsList) - 1)
    assert dlpt.utils.search_str_in_lines("asd", testStringsList, True) is None


def test_dict_operations():
    dictOne = {"1": "one", "2": 2, 3: 3.3}
    dictTwo = {"2": 2, "1": "one", 3: 3.3}
    assert dlpt.utils.are_dict_keys_equal(dictOne, dictOne) is True
    assert dlpt.utils.are_dict_keys_equal(dictOne, dictTwo) is True
    assert dlpt.utils.are_dict_values_equal(dictOne, dictOne) is True
    assert dlpt.utils.are_dict_values_equal(dictOne, dictTwo) is True

    dictTwo = {"2": 2, "1": "one", 3: 3.3, "four": " four"}
    assert dlpt.utils.are_dict_keys_equal(dictOne, dictTwo) is False
    assert dlpt.utils.are_dict_values_equal(dictOne, dictTwo) is False

    # try with dicst that hold classes
    dictOne = {"1": SomeTestClass(1, 2, 3), 3: SomeTestClass(4, 5, 6)}
    dictTwo = {"100": SomeTestClass(1, 2, 3), 300: SomeTestClass(4, 5, 6)}
    assert dlpt.utils.are_dict_values_equal(dictOne, dictOne) is True
    assert dlpt.utils.are_dict_values_equal(dictOne, dictTwo) is False


def test_map_dict_to_class():
    dInstance = SomeTestClass(1, 2, 3)
    d = dInstance.__dict__.copy()

    cInstance = SomeTestClass(4, 5, 6)
    c = dlpt.utils.map_dict_to_class(cInstance, d)

    assert isinstance(c, SomeTestClass)
    assert isinstance(cInstance, SomeTestClass)

    assert c.two == dInstance.two


def test_get_obj_public_vars():
    cInstance = SomeTestClass(1, 2, 3)
    publicVars = dlpt.utils.get_obj_public_vars(cInstance)
    assert len(publicVars.keys()) == 3

    assert "one" in publicVars
    assert "two" in publicVars
    assert "_private" not in publicVars
    assert "__superPrivate" not in publicVars

    assert publicVars["one"] == 1


def test_get_obj_public_methods():
    # check class methods when instance is given
    cInstance = SomeTestClass(1, 2, 3)
    methods = dlpt.utils.get_obj_public_methods(cInstance)
    assert ("one" not in methods) and ("_private" not in methods) and ("_superPrivate" not in methods)

    assert "normal" in methods
    assert callable(methods["normal"])
    assert methods["normal"]() == "normalVal"

    assert ("static" not in methods) and ("_hidden" not in methods) and ("__veryHidden" not in methods)


def test_get_module_callables():
    callableObj = dlpt.utils.get_module_callables(THIS_MODULE)

    assert public_func.__name__ in callableObj
    assert id(public_func) == id(callableObj[public_func.__name__])
    assert PublicClass.__name__ in callableObj
    assert id(PublicClass) == id(callableObj[PublicClass.__name__])

    # variables, private funcs/classes
    assert TEST_VAR_PUBLIC not in callableObj
    assert _TEST_VAR_PRIVATE not in callableObj
    assert _private_func.__name__ not in callableObj
    assert _PrivateClass.__name__ not in callableObj


def test_get_module_public_classes():
    classes = dlpt.utils.get_module_public_classes(THIS_MODULE)

    assert PublicClass.__name__ in classes
    assert id(PublicClass) == id(classes[PublicClass.__name__])

    # variables, private funcs/classes
    assert TEST_VAR_PUBLIC not in classes
    assert _TEST_VAR_PRIVATE not in classes
    assert _private_func.__name__ not in classes
    assert _PrivateClass.__name__ not in classes


def test_get_module_public_functions():
    functions = dlpt.utils.get_module_public_functions(THIS_MODULE)

    assert public_func.__name__ in functions
    assert id(public_func) == id(functions[public_func.__name__])

    # variables, private funcs/classes
    assert TEST_VAR_PUBLIC not in functions
    assert _TEST_VAR_PRIVATE not in functions
    assert _private_func.__name__ not in functions
    assert PublicClass.__name__ not in functions
    assert _PrivateClass.__name__ not in functions


def test_get_caller_locations():
    def _testFunc1() -> str:
        return _testFunc2()

    def _testFunc2() -> str:
        caller = dlpt.utils.get_caller_location()
        return caller

    def _testFunc3() -> str:
        caller = dlpt.utils.get_caller_location()
        return caller

    caller = _testFunc1()
    assert "_testFunc1" in caller
    assert os.path.abspath(__file__).lower() in caller.lower()

    caller = _testFunc3()
    assert "test_get_caller_location" in caller
    assert os.path.abspath(__file__).lower() in caller.lower()

    assert "unable to display" in dlpt.utils.get_caller_location(100)

    assert "unable to display" in dlpt.utils.get_caller_location(100)


class SomeTestClass:
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
