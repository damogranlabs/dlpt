import datetime
import time

import pytest

import dlpt

CUSTOM_DATE_TIME_FORMAT = "%d.%m.%Y, %H:%M:%S"


def _check_datetime_str_format(dt_str):
    # gets really complicated to check current time (hours are formatted with 0 if < 10, ...)
    # hence, only number of string parts is checked
    datum, clock_time = dt_str.split(",")

    datum = datum.strip()
    assert len(datum.split(".")) == 3

    clock_time = clock_time.strip()
    assert len(clock_time.split(":")) == 3


def test_get_current_datetime_str():
    date_time = dlpt.time.get_current_datetime_str(CUSTOM_DATE_TIME_FORMAT)
    _check_datetime_str_format(date_time)


def test_convert_sequence():
    start_time = datetime.datetime.now()
    current_time = time.time()
    dt = dlpt.time.timestamp_to_datetime(current_time)

    dt_str = dlpt.time.datetime_to_str(dt, CUSTOM_DATE_TIME_FORMAT)
    _check_datetime_str_format(dt_str)

    # milliseconds formatters
    dt_str = dlpt.time.timestamp_to_str(current_time, "%S", 1)
    assert ("." in dt_str) and (int(dt_str.split(".")[1]))
    with pytest.raises(Exception):
        dlpt.time.timestamp_to_str(current_time, "%M", 2)  # msec formatter without %S

    dt_str = dlpt.time.timestamp_to_str(current_time, CUSTOM_DATE_TIME_FORMAT)
    _check_datetime_str_format(dt_str)

    # seconds representation of a time
    assert dlpt.time.time_to_seconds() == 0.0
    assert dlpt.time.time_to_seconds(h=2) == float(2 * 60 * 60)
    assert dlpt.time.time_to_seconds(m=3) == float(3 * 60)
    assert dlpt.time.time_to_seconds(h=2, s=10) == float(2 * 60 * 60 + 10)
    duration_sec = 1 * 24 * 60 * 60 + 4 * 60 * 60 + 6 * 60 + 12  # 1 day, 4 hours, 6 mins, 12 sec
    assert dlpt.time.time_to_seconds(1, 4, 6, 12) == float(duration_sec)

    # timedelta
    time.sleep(0.2)
    end_time = datetime.datetime.now()
    hms_str = dlpt.time.timedelta_to_str(end_time - start_time)
    assert ("0 min " in hms_str) and (" 0." in hms_str) and (" sec" in hms_str)  # example: 0 min 0.21 sec


def test_sec_to_str():
    duration_sec = 30
    sec_str = dlpt.time.sec_to_str(duration_sec, "%S")
    assert sec_str == "30.00"

    # formatters, hide_zeroes
    duration_sec = 70
    hms_str = dlpt.time.sec_to_str(duration_sec)
    assert hms_str == "1 min 10.00 sec"
    hms_str = dlpt.time.sec_to_str(duration_sec, hide_zeroes=False)
    assert hms_str == "0 h 1 min 10.00 sec"

    hms_str = dlpt.time.sec_to_str(duration_sec, "%H:%M:%S")
    assert hms_str == "1:10.00"
    hms_str = dlpt.time.sec_to_str(duration_sec, "%H:%M:%S", False)
    assert hms_str == "0:1:10.00"

    sec_str = dlpt.time.sec_to_str(duration_sec, "%S")
    assert sec_str == "10.00"
    sec_str = dlpt.time.sec_to_str(duration_sec, "%S", False)
    assert sec_str == "10.00"

    # 2 days, 4 hours, 6 mins, 12 sec
    duration_sec = 2 * 24 * 60 * 60 + 4 * 60 * 60 + 6 * 60 + 12
    hms_str = dlpt.time.sec_to_str(duration_sec, dlpt.time.TIME_FORMAT_HMS_STRING)
    assert hms_str == "52 h 6 min 12.00 sec"

    # same time with additional milliseconds
    duration_sec = duration_sec + 0.33
    hms_str = dlpt.time.sec_to_str(duration_sec, dlpt.time.TIME_FORMAT_HMS_STRING)
    assert hms_str == "52 h 6 min 12.33 sec"
    hms_str = dlpt.time.sec_to_str(duration_sec, dlpt.time.TIME_FORMAT_HMS_STRING, False)
    assert hms_str == "52 h 6 min 12.33 sec"


def test_execution_time_helpers():
    SLEEP_TIME_SEC = 0.42
    FUNC_ARGS = "asd"
    RET_VAL = 42

    @dlpt.time.print_exec_time
    def test_function(args):
        assert args == FUNC_ARGS
        time.sleep(SLEEP_TIME_SEC)
        return RET_VAL

    time_test_func = dlpt.time.func_stopwatch(test_function)
    ret_val = time_test_func(FUNC_ARGS)
    assert ret_val == RET_VAL

    exec_time_sec = dlpt.time.get_last_measured_time_sec()
    assert (exec_time_sec < (SLEEP_TIME_SEC + 0.3)) and (exec_time_sec > (SLEEP_TIME_SEC - 0.3))
