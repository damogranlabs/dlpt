import datetime
import time

import pytest

import dlpt

CUSTOM_DATE_TIME_FORMAT = "%d.%m.%Y, %H:%M:%S"


def _check_datetime_str_format(dtStr):
    # gets really complicated to check current time (hours are formatted with 0 if < 10, ...)
    # hence, only number of string parts is checked
    datum, clockTime = dtStr.split(",")

    datum = datum.strip()
    assert len(datum.split(".")) == 3

    clockTime = clockTime.strip()
    assert len(clockTime.split(":")) == 3


def test_get_current_datetime_str():
    dateTime = dlpt.time.get_current_datetime_str(CUSTOM_DATE_TIME_FORMAT)
    _check_datetime_str_format(dateTime)


def test_convert_sequence():
    startTime = datetime.datetime.now()
    currentTime = time.time()
    dt = dlpt.time.timestamp_to_datetime(currentTime)

    dtStr = dlpt.time.datetime_to_str(dt, CUSTOM_DATE_TIME_FORMAT)
    _check_datetime_str_format(dtStr)

    # milliseconds formatters
    dtStr = dlpt.time.timestamp_to_str(currentTime, "%S", 1)
    assert ("." in dtStr) and (int(dtStr.split(".")[1]))
    with pytest.raises(Exception):
        dlpt.time.timestamp_to_str(currentTime, "%M", 2)  # msec formatter without %S

    dtStr = dlpt.time.timestamp_to_str(currentTime, CUSTOM_DATE_TIME_FORMAT)
    _check_datetime_str_format(dtStr)

    # seconds representation of a time
    assert dlpt.time.time_to_seconds() == 0.0
    assert dlpt.time.time_to_seconds(h=2) == float(2 * 60 * 60)
    assert dlpt.time.time_to_seconds(m=3) == float(3 * 60)
    assert dlpt.time.time_to_seconds(h=2, s=10) == float(2 * 60 * 60 + 10)
    durationSec = 1 * 24 * 60 * 60 + 4 * 60 * 60 + 6 * 60 + 12  # 1 day, 4 hours, 6 mins, 12 sec
    assert dlpt.time.time_to_seconds(1, 4, 6, 12) == float(durationSec)

    # timedelta
    time.sleep(0.2)
    endTime = datetime.datetime.now()
    hmsStr = dlpt.time.timedelta_to_str(endTime - startTime)
    assert ("0 min " in hmsStr) and (" 0." in hmsStr) and (" sec" in hmsStr)  # example: 0 min 0.21 sec


def test_sec_to_str():
    durationSec = 30
    secStr = dlpt.time.sec_to_str(durationSec, "%S")
    assert secStr == "30.00"

    # formatters, hideZeroes
    durationSec = 70
    hmsStr = dlpt.time.sec_to_str(durationSec)
    assert hmsStr == "1 min 10.00 sec"
    hourhmsStr = dlpt.time.sec_to_str(durationSec, hideZeroes=False)
    assert hourhmsStr == "0 h 1 min 10.00 sec"

    hmsStr = dlpt.time.sec_to_str(durationSec, "%H:%M:%S")
    assert hmsStr == "1:10.00"
    hmsStr = dlpt.time.sec_to_str(durationSec, "%H:%M:%S", False)
    assert hmsStr == "0:1:10.00"

    secStr = dlpt.time.sec_to_str(durationSec, "%S")
    assert secStr == "10.00"
    secStr = dlpt.time.sec_to_str(durationSec, "%S", False)
    assert secStr == "10.00"

    # 2 days, 4 hours, 6 mins, 12 sec
    durationSec = 2 * 24 * 60 * 60 + 4 * 60 * 60 + 6 * 60 + 12
    hmsStr = dlpt.time.sec_to_str(durationSec, dlpt.time.TIME_FORMAT_HMS_STRING)
    assert hmsStr == "52 h 6 min 12.00 sec"

    # same time with additional milliseconds
    durationSec = durationSec + 0.33
    hmsStr = dlpt.time.sec_to_str(durationSec, dlpt.time.TIME_FORMAT_HMS_STRING)
    assert hmsStr == "52 h 6 min 12.33 sec"
    hmsStr = dlpt.time.sec_to_str(durationSec, dlpt.time.TIME_FORMAT_HMS_STRING, False)
    assert hmsStr == "52 h 6 min 12.33 sec"


def test_execution_time_helpers():
    SLEEP_TIME_SEC = 0.42
    FUNC_ARGS = "asd"
    RET_VAL = 42

    @dlpt.time.print_exec_time
    def testFunction(args):
        assert args == FUNC_ARGS
        time.sleep(SLEEP_TIME_SEC)
        return RET_VAL

    timeTestFunction = dlpt.time.func_stopwatch(testFunction)
    returnValue = timeTestFunction(FUNC_ARGS)
    assert returnValue == RET_VAL

    execTimeSec = dlpt.time.get_last_measured_time_sec()
    assert (execTimeSec < (SLEEP_TIME_SEC + 0.3)) and (execTimeSec > (SLEEP_TIME_SEC - 0.3))
