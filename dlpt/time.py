"""
Utility functions to convert time in/to various formats and track execution time
of a code.
"""
import datetime
import time
from typing import Any, Callable, TypeVar

import dlpt

# FORMATTERS:
#   datetime: https://docs.python.org/3.6/library/datetime.html#strftime-and-strptime-behavior
#   time: https://docs.python.org/3.6/library/time.html#time.strftime
DATE_FORMAT = "%d-%b-%Y"
TIME_FORMAT = "%H:%M:%S"
TIME_FORMAT_HMS_STRING = "%H h %M min %S sec"
TIME_FORMAT_MS_STRING = "%M min %S sec"
DATE_TIME_FORMAT = f"{DATE_FORMAT}_{TIME_FORMAT}"
DATE_TIME_FORMAT_FILE_NAME = f"{DATE_FORMAT}_%H-%M-%S"

_lastTimedFunctionTimeSec: float = 0


def timestampToDatetime(timestamp: float) -> datetime.datetime:
    """
    Return a datetime object for a given timestamp (as returned by time.time()).
        @param timestamp: timestamp as a number since the epoch (time.time()).
    """
    dt = datetime.datetime.fromtimestamp(timestamp)

    return dt


def timestampToString(timestamp: float, outputFormat: str = TIME_FORMAT, msecDigits: int = 0) -> str:
    """
    Return a string of converted timestamp (as returned by time.time()) by 
    following the given format.
        @param timestamp: timestamp as a number since the epoch (time.time()).
        @param outputFormat: output string format.
        @param msecDigits: check _msecFormatter()
    """
    dt = timestampToDatetime(timestamp)
    dtmStr = _msecFormatter(dt, outputFormat, msecDigits)

    return dtmStr


def secondsToString(seconds: float,
                    outputFormat: str = TIME_FORMAT_HMS_STRING,
                    hideZeroes: bool = True) -> str:
    """
    TODO simplify
    Return a string of a converted time in seconds by following the given format.
    NOTE: Only applicable for hours, minutes and seconds. Days and larger time
    units are silently ignored.
    NOTE: Seconds are always displayed as a 2 digit float, while hours and 
    numbers are integers. Example: 2 days and 4 hours -> 52 h 0 min 0.00 sec
        @param seconds: time (duration) as a number of seconds.
        @param outputFormat: output string format. 
            This function does not support setting float number of digits for seconds.
            Output format can be changed if 'hideZeroes' arg is True.
        @param hideZeroes: if True, leading parts (hours, minutes) can be 
        omitted (if zero), Otherwise, outputFormat is strictly respected.
            NOTE: this is applicable only in the most common use cases, where 
            time is displayed in order <hours> <minutes> <seconds>.
            If hideZeroes is True, leading zero-value parts are stripped to
                the first next time part: hours to minutes, minutes to seconds.
                361.5 sec  = 1 h 0 min 1.50 sec
                360 sec  = 1 h 0 min 0.00 sec
                359 sec  = 59 min 0.00 sec
                59 sec  = 59.00 sec
            Other special time formaters can be used by setting 'hideZeroes' 
            to False.
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    if hideZeroes:
        if h == 0:
            minPos = outputFormat.find("%M")
            if minPos != -1:
                outputFormat = outputFormat[minPos:]

            if m == 0:
                secPos = outputFormat.find("%S")
                if secPos != -1:
                    outputFormat = outputFormat[secPos:]

    timeStr = outputFormat.replace("%H", str(int(h))).replace("%M", str(int(m))).replace("%S", dlpt.utils.floatToStr(s))

    return timeStr


def timeToSeconds(d: int = 0, h: int = 0, m: int = 0, s: float = 0.0) -> float:
    """
    Return 'seconds' representation of a given time as defined by days, hours,
    minutes and seconds.
        @param d: number of days to add to returned seconds.
        @param h: number of hours to add to returned seconds.
        @param m: number of minutes to add to returned seconds.
        @param s: number of seconds to add to returned seconds.
    """
    sec = (d * 24 * 60 * 60) + (h * 60 * 60) + (m * 60) + s

    return sec


def datetimeToString(dt: datetime.datetime, outputFormat: str = TIME_FORMAT) -> str:
    """
    Return a string representation of a datetime object.
    NOTE: receives datetime object, not timedelta - check timedeltaToString().
        @param dt: datetime object to convert to string.
        @param outputFormat: output string format.
    """
    dtStr = datetime.datetime.strftime(dt, outputFormat)

    return dtStr


def timedeltaToString(td: datetime.timedelta, outputFormat: str = TIME_FORMAT_MS_STRING) -> str:
    """
    Return a string representation of a datetime timedelta object.
    NOTE: receives timedelta object, not datetime - check datetimeToString().
        @param td: datetime.timedelta object to convert to string.
        @param outputFormat: output string format. Respect output format - does
            not hide zeroes.
    """
    tdStr = secondsToString(td.total_seconds(), outputFormat, False)

    return tdStr


def getCurrentDateTime(outputFormat: str = DATE_TIME_FORMAT, msecDigits: int = 0) -> str:
    """
    Return a string of a current timestamp by following the given format.
        @param outputFormat: output string format.
        @param msecDigits: check _msecFormatter()
    """
    dt = datetime.datetime.now()
    dtmStr = _msecFormatter(dt, outputFormat, msecDigits)

    return dtmStr


def _msecFormatter(dateTimeObject: datetime.datetime, outputFormat: str, msecDigits: int) -> str:
    """
    Return a string of a formated date/time/msec.
        @param dateTimeObject: parsed datetime object as get with 
            datetime.datetime.now() or datetime.datetime.fromtimestamp(timestamp)
        @param outputFormat: date/time output formatter
        @param msecDigits: number of millisecond digits to display, in 
            a range of 0 - 3.
            NOTE: Only applicable to TIME_FORMAT or custom formatter that 
                ends with '%S'.
            NOTE: msecDigits only limit max number of displayed digits. It does
                not guarantee that output string will actually have this number
                of millisecond digits.
    """
    dtStr = dateTimeObject.strftime(outputFormat)
    if msecDigits > 0:
        if outputFormat.endswith('%S'):
            msecStr = str(int(dateTimeObject.microsecond / 1000))[:msecDigits]
            if msecStr != '':
                dtStr = f"{dtStr}.{msecStr}"
        else:
            errorMsg = f"Millisecond formatting supported only for formatters that ends with '%S': '{outputFormat}'"
            raise Exception(errorMsg)

    return dtStr


T_EXEC_TIME = TypeVar("T_EXEC_TIME")


def printExecTime(func: Callable[..., T_EXEC_TIME]) -> Callable[..., T_EXEC_TIME]:
    """
    Development decorator to get and print (to console) approximate execution time. 
    Additionally, user can get execution time with getLastTimedFunctionDurationSec().
        @param func: function 'pointer' to get execution time.
    Usage:
        `@dlpt.time.printExecTime`
        `def myFunction(<parameters>)`
        `...`
    """
    def _timed(*args, **kwargs) -> Any:
        startTime = time.perf_counter()
        result = func(*args, **kwargs)
        endTime = time.perf_counter()

        global _lastTimedFunctionTimeSec
        _lastTimedFunctionTimeSec = round(endTime - startTime, 3)

        msg = f"'{func.__name__}' execution time: {_lastTimedFunctionTimeSec} sec"
        print(msg)

        return result

    return _timed


def funcStopwatch(func: Callable[..., T_EXEC_TIME]) -> Callable[..., T_EXEC_TIME]:
    """
    Call function and track its execution time.
    Similar to 'printExecTime' decorator, but can be used with function with 
    arguments. Does not print time to console.
        @param function: function 'pointer' to get execution time.
    Usage:
        myFunction = funcStopwatch(<myFunctionName>)
        myFunction(<parameters>)

        execTime = getLastTimedFunctionDurationSec()
    """
    def _timed(*args, **kw):
        startTime = time.perf_counter()
        result = func(*args, **kw)
        endTime = time.perf_counter()

        global _lastTimedFunctionTimeSec
        _lastTimedFunctionTimeSec = round(endTime - startTime, 3)

        return result

    return _timed


def getLastTimedFunctionDurationSec() -> float:
    """
    Return execution time of the last function, that was timed by using 
    'printExecTime()' or 'funcStopwatch()' function.
    NOTE: only valid after function calls. Otherwise, return None or previous time.
    """
    return _lastTimedFunctionTimeSec
