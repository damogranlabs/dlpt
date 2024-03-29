"""
Utility functions to convert time in/to/from various formats and track execution 
time of a code.
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

_last_measured_time_sec: float = 0


def timestamp_to_datetime(timestamp: float) -> datetime.datetime:
    """Return a datetime object for a given ``timestamp`` (as returned by `time.time()`).

    Args:
        timestamp: timestamp as a number since the epoch (`time.time()`).

    Returns:
        Datetime object of a ``timestamp``.
    """
    return datetime.datetime.fromtimestamp(timestamp)


def timestamp_to_str(timestamp: float, fmt: str = TIME_FORMAT, msec_digits: int = 0) -> str:
    """Return a string of converted timestamp (as returned by `time.time()`) by
    following the given format.

    Args:
        timestamp: timestamp as a number since the epoch (`time.time()`).
        fmt: output string format.
        msec_digits: See the docs check :func:`_format_msec()`

    Returns:
        Timestamp as a string, based on a given format.
    """
    dt = timestamp_to_datetime(timestamp)

    return _format_msec(dt, fmt, msec_digits)


def sec_to_str(seconds: float, fmt: str = TIME_FORMAT_HMS_STRING, hide_zeroes: bool = True) -> str:
    """Return a string of a converted time (in seconds) by following the given
    format.

    Note: Only applicable for hours, minutes and seconds. Days and larger time
        units are silently ignored (added to the hours).

    Note: Seconds are always displayed as a 2 digit float, while hours and
        numbers are integers. Example: 2 days and 4 hours -> 52 h 0 min 0.00 sec

    Args:
        seconds: time (duration) as a number of seconds.
        fmt: output string format. This function does not support setting float
            number of digits for seconds. Output format can be changed if
            ``hide_zeroes`` arg is True.
        hide_zeroes: if True, leading parts (hours, minutes) can be
            omitted (if zero), Otherwise, ``fmt`` is strictly respected. Note: this
            is applicable only in the most common use cases, where
            time is displayed in order <hours> <minutes> <seconds>.
            If ``hide_zeroes`` is True, leading zero-value parts are stripped to
            the first next time part: hours to minutes, minutes to seconds.
            361.5 sec  = 1 h 0 min 1.50 sec
            360 sec  = 1 h 0 min 0.00 sec
            359 sec  = 59 min 0.00 sec
            59 sec  = 59.00 sec
            Other special time formaters can be used by setting ``hide_zeroes``
            to False.

    Returns:
        Formatted string of a given seconds number.
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)

    if hide_zeroes:
        if h == 0:
            min_pos = fmt.find("%M")
            if min_pos != -1:
                fmt = fmt[min_pos:]

            if m == 0:
                sec_pos = fmt.find("%S")
                if sec_pos != -1:
                    fmt = fmt[sec_pos:]

    time_str = fmt.replace("%H", str(int(h))).replace("%M", str(int(m))).replace("%S", dlpt.utils.float_to_str(s))

    return time_str


def time_to_seconds(d: int = 0, h: int = 0, m: int = 0, s: float = 0.0) -> float:
    """Return 'seconds' representation of a given time as defined by days, hours,
    minutes and seconds.

    Args:
        d: number of days to add to returned seconds.
        h: number of hours to add to returned seconds.
        m: number of minutes to add to returned seconds.
        s: number of seconds to add to returned seconds.

    Returns:
        'Seconds' representation of a given time duration.
    """
    sec = (d * 24 * 60 * 60) + (h * 60 * 60) + (m * 60) + s

    return sec


def datetime_to_str(dt: datetime.datetime, fmt: str = TIME_FORMAT) -> str:
    """Return a string representation of a given ``dt`` datetime.datetime` object.

    Note: ``dt`` is `datetime.datetime` object, not `datetime.timedelta` -
        check :func:`timedelta_to_str()`.

    Args:
        dt: datetime object to convert to string.
        fmt: output string format.

    Returns:
        String representation of `datetime.datetime` object.
    """
    return datetime.datetime.strftime(dt, fmt)


def timedelta_to_str(td: datetime.timedelta, fmt: str = TIME_FORMAT_MS_STRING) -> str:
    """Return a string representation of a ``td`` `datetime.timedelta` object.

    Note: receives `datetime.timedelta` object, not `datetime.datetime` - check
        :func:`datetime_to_str()`.

    Args:
        td: datetime.timedelta object to convert to string.
        fmt: output string format. Respect output format - does
            not hide zeroes.

    Returns:
        String representation of `datetime.timedelta` object.
    """
    return sec_to_str(td.total_seconds(), fmt, False)


def get_current_datetime_str(fmt: str = DATE_TIME_FORMAT, msec_digits: int = 0) -> str:
    """Return a string of a current timestamp by following the given format.

    Args:
        fmt: output string format.
        msec_digits: check :func:`_format_msec()`.

    Returns:
        Formatted current date and time string.
    """
    dt = datetime.datetime.now()

    return _format_msec(dt, fmt, msec_digits)


def _format_msec(dt: datetime.datetime, fmt: str, msec_digits: int) -> str:
    """Return a string of a formated date/time/msec.

    Args:
        dt: parsed datetime object as get with `datetime.datetime.now()` or
            `datetime.datetime.fromtimestamp(timestamp)`.
        fmt: date/time output formatter.
        msec_digits: number of millisecond digits to display, in
            a range of 0 - 3. Note: Only applicable to `TIME_FORMAT` or a custom
            formatter that ends with '%S'. Note: msec_digits only limit max
            number of displayed digits. It does not guarantee that output string
            will actually have this number of millisecond digits.
    """
    dt_str = dt.strftime(fmt)
    if msec_digits > 0:
        if fmt.endswith("%S"):
            msec_str = str(int(dt.microsecond / 1000))[:msec_digits]
            if msec_str != "":
                dt_str = f"{dt_str}.{msec_str}"
        else:
            err_msg = f"Millisecond formatting supported only for formatters that ends with '%S': '{fmt}'"
            raise Exception(err_msg)

    return dt_str


T_EXEC_TIME = TypeVar("T_EXEC_TIME")


def print_exec_time(func: Callable[..., T_EXEC_TIME]) -> Callable[..., T_EXEC_TIME]:
    """Decorator to get and print (to console) approximate execution time.
    Additionally, user can get execution time with :func:`get_last_measured_time_sec()`.

    Args:
        func: function reference to get execution time.

    Example:
        >>> @dlpt.time.print_exec_time
            def my_function(*args, **kwargs):
                time.sleep(42)
        >>> my_function()
        "'my_function' execution time: 42.63 sec"
        >>> dlpt.time.get_last_measured_time_sec()
        42.63
    """

    def _timed(*args, **kwargs) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        global _last_measured_time_sec
        _last_measured_time_sec = round(end_time - start_time, 3)

        msg = f"'{func.__name__}' execution time: {_last_measured_time_sec} sec"
        print(msg)

        return result

    return _timed


def func_stopwatch(func: Callable[..., T_EXEC_TIME]) -> Callable[..., T_EXEC_TIME]:
    """Call function and track its execution time. Similar to
    a :func:`print_exec_time` decorator, but can be used with function with
    arguments. Does not print time to console.

    Args:
        func: function 'pointer' to track execution time.

    Example:
        >>> def my_function(*args, **kwargs):
                time.sleep(42)
        >>> my_function_timed = dlpt.time.func_stopwatch(my_function)
        >>> my_function_timed(arg1, arg2)
        >>> dlpt.time.get_last_measured_time_sec()
        42.63

    Returns:
        User function wrapped in :func:`func_stopwatch()`.
    """

    def _timed(*args, **kw):
        start_time = time.perf_counter()
        result = func(*args, **kw)
        end_time = time.perf_counter()

        global _last_measured_time_sec
        _last_measured_time_sec = round(end_time - start_time, 3)

        return result

    return _timed


def get_last_measured_time_sec() -> float:
    """Return execution time of the last function, that was timed by using
    :func:`print_exec_time()` or :func:`func_stopwatch()` function.

    Note: only valid after function calls. Otherwise, return None or a
        previous time.

    Returns:
        Last timed function or None (if no function was timed before).
    """
    return _last_measured_time_sec
