"""
Utility functions to convert time in/to various formats and track execution time
of a code.
"""
import datetime
import time
from typing import Any, Callable, TypeVar

import dlpt

# FORMATTERS:
#   datetime:
# https://docs.python.org/3.6/library/datetime.html#strftime-and-strptime-behavior
#   time:
# https://docs.python.org/3.6/library/time.html#time.strftime
DATE_FORMAT = "%d-%b-%Y"
TIME_FORMAT = "%H:%M:%S"
TIME_FORMAT_HMS_STRING = "%H h %M min %S sec"
TIME_FORMAT_MS_STRING = "%M min %S sec"
DATE_TIME_FORMAT = f"{DATE_FORMAT}_{TIME_FORMAT}"
DATE_TIME_FORMAT_FILE_NAME = f"{DATE_FORMAT}_%H-%M-%S"

_lastTimedFunctionTimeSec: float = 0


def timestampToDatetime(timestamp: float) -> datetime.datetime:
    """ Return a datetime object for a given timestamp (as returned by
    `time.time()`).

    Args:
        timestamp: timestamp as a number since the epoch (`time.time()`).

    Returns:
        Datetime object of a timestamp.
    """
    dt = datetime.datetime.fromtimestamp(timestamp)

    return dt


def timestampToStr(timestamp: float,
                   fmt: str = TIME_FORMAT,
                   msecDigits: int = 0) -> str:
    """ Return a string of converted timestamp (as returned by `time.time()`) by 
    following the given format.

    Args:
        timestamp: timestamp as a number since the epoch (time.time()).
        fmt: output string format.
        msecDigits: check _msecFormatter()

    Returns:
        Timestamp as a string, based on a given format.
    """
    dt = timestampToDatetime(timestamp)
    dtmStr = _msecFormatter(dt, fmt, msecDigits)

    return dtmStr


def secToStr(seconds: float,
             fmt: str = TIME_FORMAT_HMS_STRING,
             hideZeroes: bool = True) -> str:
    """ Return a string of a converted time (in seconds) by following the given
    format.

    Note: Only applicable for hours, minutes and seconds. Days and larger time
        units are silently ignored.

    Note: Seconds are always displayed as a 2 digit float, while hours and 
        numbers are integers. Example: 2 days and 4 hours -> 52 h 0 min 0.00 sec

    Args:
        seconds: time (duration) as a number of seconds.
        fmt: output string format. This function does not support setting float 
            number of digits for seconds. Output format can be changed if 
            ``hideZeroes`` arg is True.
        hideZeroes: if True, leading parts (hours, minutes) can be 
            omitted (if zero), Otherwise, fmt is strictly respected. Note: this
            is applicable only in the most common use cases, where 
            time is displayed in order <hours> <minutes> <seconds>.
            If ``hideZeroes`` is True, leading zero-value parts are stripped to
            the first next time part: hours to minutes, minutes to seconds.
            361.5 sec  = 1 h 0 min 1.50 sec
            360 sec  = 1 h 0 min 0.00 sec
            359 sec  = 59 min 0.00 sec
            59 sec  = 59.00 sec
            Other special time formaters can be used by setting ``hideZeroes``
            to False.

    Returns:
        Formatted string of a given seconds number.
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    if hideZeroes:
        if h == 0:
            minPos = fmt.find("%M")
            if minPos != -1:
                fmt = fmt[minPos:]

            if m == 0:
                secPos = fmt.find("%S")
                if secPos != -1:
                    fmt = fmt[secPos:]

    timeStr = fmt.replace("%H", str(int(h))) \
        .replace("%M", str(int(m))) \
        .replace("%S", dlpt.utils.floatToStr(s))

    return timeStr


def timeToSeconds(d: int = 0, h: int = 0, m: int = 0, s: float = 0.0) -> float:
    """ Return 'seconds' representation of a given time as defined by days, hours,
    minutes and seconds.

    Args:
        d: number of days to add to returned seconds.
        h: number of hours to add to returned seconds.
        m: number of minutes to add to returned seconds.
        s: number of seconds to add to returned seconds.

    Retuns:
        'Seconds' representation of a given time duration.
    """
    sec = (d * 24 * 60 * 60) + (h * 60 * 60) + (m * 60) + s

    return sec


def datetimeToStr(dt: datetime.datetime, fmt: str = TIME_FORMAT) -> str:
    """ Return a string representation of a datetime object.

    Note: receives datetime object, not timedelta - check 
        :func:`timedeltaToStr()`.

    Args:
        dt: datetime object to convert to string.
        fmt: output string format.

    Returns:
        String representation of `datetime.datetime` object.
    """
    dtStr = datetime.datetime.strftime(dt, fmt)

    return dtStr


def timedeltaToStr(td: datetime.timedelta,
                   fmt: str = TIME_FORMAT_MS_STRING) -> str:
    """ Return a string representation of a datetime timedelta object.

    Note: receives timedelta object, not datetime - check 
        :func:`datetimeToStr()`.

    Args:
        td: datetime.timedelta object to convert to string.
        fmt: output string format. Respect output format - does
            not hide zeroes.

    Returns:
        String representation of `datetime.timedelta` object.
    """
    tdStr = secToStr(td.total_seconds(), fmt, False)

    return tdStr


def getCurrentDateTimeStr(fmt: str = DATE_TIME_FORMAT,
                          msecDigits: int = 0) -> str:
    """ Return a string of a current timestamp by following the given format.

    Args: 
        fmt: output string format.
        msecDigits: check :func:`_msecFormatter()`.

    Returns:
        Formatted current date and time string.
    """
    dt = datetime.datetime.now()
    dtmStr = _msecFormatter(dt, fmt, msecDigits)

    return dtmStr


def _msecFormatter(dt: datetime.datetime, fmt: str, msecDigits: int) -> str:
    """ Return a string of a formated date/time/msec.

    Args:
        dt: parsed datetime object as get with `datetime.datetime.now()` or 
            `datetime.datetime.fromtimestamp(timestamp)`
        fmt: date/time output formatter
        msecDigits: number of millisecond digits to display, in 
            a range of 0 - 3. Note: Only applicable to `TIME_FORMAT` or a custom
            formatter that ends with '%S'. Note: msecDigits only limit max
            number of displayed digits. It does not guarantee that output string
            will actually have this number of millisecond digits.
    """
    dtStr = dt.strftime(fmt)
    if msecDigits > 0:
        if fmt.endswith('%S'):
            msecStr = str(int(dt.microsecond / 1000))[:msecDigits]
            if msecStr != '':
                dtStr = f"{dtStr}.{msecStr}"
        else:
            errorMsg = "Millisecond formatting supported only for formatters "
            errorMsg += f"that ends with '%S': '{fmt}'"
            raise Exception(errorMsg)

    return dtStr


T_EXEC_TIME = TypeVar("T_EXEC_TIME")


def printExecTime(func: Callable[..., T_EXEC_TIME]) -> Callable[..., T_EXEC_TIME]:
    """ Development decorator to get and print (to console) approximate 
    execution time. Additionally, user can get execution time with 
    :func:`getLastTimedFunctionDurationSec()`.

    Args:
        func: function 'pointer' to get execution time.

    Example:
        >>> @dlpt.time.printExecTime
            def myFunction(<parameters>):
                pass
        >>> myFunction(args)
        >>> dlpt.time.getLastTimedFunctionDurationSec()
        42.6
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
    """ Call function and track its execution time. Similar to 
    a :func:`printExecTime` decorator, but can be used with function with 
    arguments. Does not print time to console.

    Args:
        func: function 'pointer' to track execution time.

    Example:
        >>> myFunction = dlpt.time.funcStopwatch(<myFunctionName>)
        >>> myFunction(<parameters>)
        >>> dlpt.time.getLastTimedFunctionDurationSec()
        42.6

    Returns:
        User function wrapped in :func:`funcStopwatch()`.
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
    """ Return execution time of the last function, that was timed by using 
    :func:`printExecTime()` or :func:`funcStopwatch()` function.

    Note: only valid after function calls. Otherwise, return None or a 
        previous time.

    Returns: 
        Last timed function or None (if no function was timed before).
    """
    return _lastTimedFunctionTimeSec
