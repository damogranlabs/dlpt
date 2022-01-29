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
    "value,expected_int,expected_float",
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
def test_get_num_from_str(value, expected_int, expected_float):
    assert dlpt.utils.get_int_from_str(value) == expected_int
    assert dlpt.utils.get_float_from_str(value) == expected_float


def test_get_num_from_str_err():
    with pytest.raises(Exception):
        assert dlpt.utils.get_int_from_str("a6")
    with pytest.raises(Exception):
        assert dlpt.utils.get_float_from_str("-a6")


def test_list_operations():
    # NOTE: list operations does not necessary maintain items order
    l1 = [1, 3, 5]
    l2 = [1, 3, 6, 9]
    l3 = copy.copy(l1)
    l3.append(10)
    expected_intersection = [1, 3]
    expected_diff = [5, 6, 9]

    assert dlpt.utils.get_list_str(l1) == "1, 3, 5"
    list_str = dlpt.utils.get_list_str(l1, "\n\t")
    assert list_str == "1\n\t3\n\t5"
    assert dlpt.utils.get_list_str([]) == ""

    assert dlpt.utils.are_list_values_equal(l1, l2) is False
    assert dlpt.utils.are_list_values_equal([], []) is True
    assert dlpt.utils.are_list_values_equal(l1, l1) is True
    assert dlpt.utils.are_list_values_equal(l1, l3) is False

    assert dlpt.utils.get_list_intersection([], []) == []
    assert dlpt.utils.get_list_intersection(l1, []) == []
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_intersection(l1, l2), [1, 3]) is True

    assert dlpt.utils.get_list_difference([], []) == []
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_difference(l1, []), l1) is True
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_difference([], l1), l1) is True
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_difference(l1, l2), expected_diff) is True
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_difference(l2, l1), expected_diff) is True

    l2 = [3, 6, 1, 9]  # same list as l2 before, but changed values order
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_intersection(l1, l2), expected_intersection) is True
    assert dlpt.utils.are_list_values_equal(dlpt.utils.get_list_difference(l1, l2), expected_diff) is True

    merged_list = l1 + l2
    expected_items = [1, 3, 5, 6, 9]
    assert dlpt.utils.remove_list_duplicates([]) == []
    assert dlpt.utils.are_list_values_equal(dlpt.utils.remove_list_duplicates(l1), l1) is True
    assert dlpt.utils.are_list_values_equal(dlpt.utils.remove_list_duplicates(merged_list), expected_items) is True


def test_search_str_in_lines():
    test_string = "my test string"
    test_strings_list = [
        f"asdsda{test_string}qweqwe",
        f"asdsda123123",
        f"asdsda456{test_string}",
        f"{test_string}09-=qweqwe",
        f"{test_string}",
    ]
    assert dlpt.utils.search_str_in_lines(test_string, test_strings_list) == 0
    assert dlpt.utils.search_str_in_lines(test_string, test_strings_list[1:]) == 1
    assert dlpt.utils.search_str_in_lines(test_string, test_strings_list[2:]) == 0
    assert dlpt.utils.search_str_in_lines(test_string, test_strings_list[3:]) == 0
    assert dlpt.utils.search_str_in_lines(test_string, test_strings_list, True) == (len(test_strings_list) - 1)
    assert dlpt.utils.search_str_in_lines("asd", test_strings_list, True) is None


def test_dict_operations():
    d1 = {"1": "one", "2": 2, 3: 3.3}
    d2 = {"2": 2, "1": "one", 3: 3.3}
    assert dlpt.utils.are_dict_keys_equal(d1, d1) is True
    assert dlpt.utils.are_dict_keys_equal(d1, d2) is True
    assert dlpt.utils.are_dict_values_equal(d1, d1) is True
    assert dlpt.utils.are_dict_values_equal(d1, d2) is True

    d2 = {"2": 2, "1": "one", 3: 3.3, "four": " four"}
    assert dlpt.utils.are_dict_keys_equal(d1, d2) is False
    assert dlpt.utils.are_dict_values_equal(d1, d2) is False

    # try with dicst that hold classes
    d1 = {"1": SomeTestClass(1, 2, 3), 3: SomeTestClass(4, 5, 6)}
    d2 = {"100": SomeTestClass(1, 2, 3), 300: SomeTestClass(4, 5, 6)}
    assert dlpt.utils.are_dict_values_equal(d1, d1) is True
    assert dlpt.utils.are_dict_values_equal(d1, d2) is False


def test_map_dict_to_class():
    class_instance = SomeTestClass(1, 2, 3)
    d1 = class_instance.__dict__.copy()

    data2 = SomeTestClass(4, 5, 6)
    data2 = dlpt.utils.map_dict_to_class(data2, d1)

    assert isinstance(data2, SomeTestClass)
    assert isinstance(data2, SomeTestClass)

    assert data2.two == class_instance.two


def test_get_obj_public_vars():
    class_instance = SomeTestClass(1, 2, 3)
    public_vars = dlpt.utils.get_obj_public_vars(class_instance)
    assert len(public_vars.keys()) == 3

    assert "one" in public_vars
    assert "two" in public_vars
    assert "_private" not in public_vars
    assert "__super_private" not in public_vars

    assert public_vars["one"] == 1


def test_get_obj_public_methods():
    # check class methods when instance is given
    class_instance = SomeTestClass(1, 2, 3)
    methods = dlpt.utils.get_obj_public_methods(class_instance)
    assert ("one" not in methods) and ("_private" not in methods) and ("_superPrivate" not in methods)

    assert "normal" in methods
    assert callable(methods["normal"])
    assert methods["normal"]() == "normal_val"

    assert ("static" not in methods) and ("_hidden" not in methods) and ("__very_hidden" not in methods)


def test_get_module_callables():
    callable_obj = dlpt.utils.get_module_callables(THIS_MODULE)

    assert public_func.__name__ in callable_obj
    assert id(public_func) == id(callable_obj[public_func.__name__])
    assert PublicClass.__name__ in callable_obj
    assert id(PublicClass) == id(callable_obj[PublicClass.__name__])

    # variables, private funcs/classes
    assert TEST_VAR_PUBLIC not in callable_obj
    assert _TEST_VAR_PRIVATE not in callable_obj
    assert _private_func.__name__ not in callable_obj
    assert _PrivateClass.__name__ not in callable_obj


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
    def _test_func1() -> str:
        return _test_func2()

    def _test_func2() -> str:
        caller = dlpt.utils.get_caller_location()
        return caller

    def _test_func3() -> str:
        caller = dlpt.utils.get_caller_location()
        return caller

    caller = _test_func1()
    assert "_test_func1" in caller
    assert os.path.abspath(__file__).lower() in caller.lower()

    caller = _test_func3()
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
        self.__super_private = "qwe"

    def normal(self):
        return "normal_val"

    @staticmethod
    def static():
        return "static_val"

    def _hidden(self):
        pass

    def __very_hidden(self):
        pass
