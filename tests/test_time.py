import datetime
import time

import pytest

import dlpt

from dlpt.tfix import *

CUSTOM_DATE_TIME_FORMAT = "%d.%m.%Y, %H:%M:%S"


def _checkDateTimeStringFormat(dtStr):
    # gets really complicated to check current time (hours are formatted with 0 if < 10, ...)
    # hence, only number of string parts is checked
    datum, clockTime = dtStr.split(',')

    datum = datum.strip()
    assert len(datum.split('.')) == 3

    clockTime = clockTime.strip()
    assert len(clockTime.split(':')) == 3


def test_getCurrentDateTime():
    dateTime = dlpt.time.getCurrentDateTimeStr(CUSTOM_DATE_TIME_FORMAT)
    _checkDateTimeStringFormat(dateTime)


def test_convertSequence():
    startTime = datetime.datetime.now()
    currentTime = time.time()
    dt = dlpt.time.timestampToDatetime(currentTime)

    dtStr = dlpt.time.datetimeToStr(dt, CUSTOM_DATE_TIME_FORMAT)
    _checkDateTimeStringFormat(dtStr)

    # milisecond formatters
    dtStr = dlpt.time.timestampToStr(currentTime, "%S", 1)
    assert ("." in dtStr) and (int(dtStr.split(".")[1]))
    with pytest.raises(Exception):
        dlpt.time.timestampToStr(currentTime, "%M", 2)  # msec formatter without %S

    dtStr = dlpt.time.timestampToStr(currentTime, CUSTOM_DATE_TIME_FORMAT)
    _checkDateTimeStringFormat(dtStr)

    # seconds representation of a time
    assert dlpt.time.timeToSeconds() == 0.0
    assert dlpt.time.timeToSeconds(h=2) == float(2 * 60 * 60)
    assert dlpt.time.timeToSeconds(m=3) == float(3 * 60)
    assert dlpt.time.timeToSeconds(h=2, s=10) == float(2 * 60 * 60 + 10)
    durationSec = 1 * 24 * 60 * 60 + 4 * 60 * 60 + 6 * 60 + 12  # 1 day, 4 hours, 6 mins, 12 sec
    assert dlpt.time.timeToSeconds(1, 4, 6, 12) == float(durationSec)

    # timedelta
    time.sleep(0.2)
    endTime = datetime.datetime.now()
    hmsStr = dlpt.time.timedeltaToStr(endTime - startTime)
    assert (
        "0 min " in hmsStr) and (
        " 0." in hmsStr) and (
            " sec" in hmsStr)  # example: 0 min 0.21 sec


def test_secondsToString():
    durationSec = 30
    secStr = dlpt.time.secToStr(durationSec, "%S")
    assert secStr == "30.00"

    # formatters, hideZeroes
    durationSec = 70
    hmsStr = dlpt.time.secToStr(durationSec)
    assert hmsStr == "1 min 10.00 sec"
    hourhmsStr = dlpt.time.secToStr(durationSec, hideZeroes=False)
    assert hourhmsStr == "0 h 1 min 10.00 sec"

    hmsStr = dlpt.time.secToStr(durationSec, "%H:%M:%S")
    assert hmsStr == "1:10.00"
    hmsStr = dlpt.time.secToStr(durationSec, "%H:%M:%S", False)
    assert hmsStr == "0:1:10.00"

    secStr = dlpt.time.secToStr(durationSec, "%S")
    assert secStr == "10.00"
    secStr = dlpt.time.secToStr(durationSec, "%S", False)
    assert secStr == "10.00"

    # 2 days, 4 hours, 6 mins, 12 sec
    durationSec = 2 * 24 * 60 * 60 + 4 * 60 * 60 + 6 * 60 + 12
    hmsStr = dlpt.time.secToStr(durationSec, dlpt.time.TIME_FORMAT_HMS_STRING)
    assert hmsStr == "52 h 6 min 12.00 sec"

    # same time with additional milliseconds
    durationSec = durationSec + 0.33
    hmsStr = dlpt.time.secToStr(durationSec, dlpt.time.TIME_FORMAT_HMS_STRING)
    assert hmsStr == "52 h 6 min 12.33 sec"
    hmsStr = dlpt.time.secToStr(
        durationSec, dlpt.time.TIME_FORMAT_HMS_STRING, False)
    assert hmsStr == "52 h 6 min 12.33 sec"


def test_executionTimeHelpers():
    SLEEP_TIME_SEC = 0.42
    FUNC_ARGS = "asd"
    RET_VAL = 42

    @dlpt.time.printExecTime
    def testFunction(args):
        assert args == FUNC_ARGS
        time.sleep(SLEEP_TIME_SEC)
        return RET_VAL

    timeTestFunction = dlpt.time.funcStopwatch(testFunction)
    returnValue = timeTestFunction(FUNC_ARGS)
    assert returnValue == RET_VAL

    execTimeSec = dlpt.time.getLastTimedFunctionDurationSec()
    assert (execTimeSec < (SLEEP_TIME_SEC + 0.3)) and (execTimeSec > (SLEEP_TIME_SEC - 0.3))
