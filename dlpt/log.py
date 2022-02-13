""" Common wrappers and helper functions to simplify most common use cases of
builtin 'logging' module.

1. Create logger and (optionally) set it as a default `dlpt` logger. 
    Note: 
        'Default' logger means that (once initialized), any `dlpt` log 
        functions, such as :func:`info()` and :func:`warning()` will log to 
        this *default* logger. Once initialized as default logger, any other
        file can simply use `dlpt` log functions without setting up logger.
    Example:
        >>> #file1.py
        >>> logger = dlpt.log.create_logger("my_logger")
        >>> dlpt.log.add_file_hdlr(logger, "dlpt_example.log")
        >>> dlpt.log.info("Log from file1.")
        >>>
        >>> #file2.py
        >>> dlpt.log.info("Log from file2.")

2. Use `dlpt.log.add_*()` functions to add common handlers to any 
    ``logging.Logger`` instance: console (terminal) handler, file handler, 
    rotating file handler, server socket handler (for logs when multiple 
    processes are used).

## Logging server
To unify logs from multiple processes, user can create logging server via 
function :func:`create_log_server_proc()`. This process will create a custom 
logger with file handler and open a socket connection on a designated port.  
Any logger (from any process) that has configured logging server handler (via 
:func:`add_logging_server_hdlr()`) will push logs to this logging server and 
therefore to a shared log file.   
Note that log statements order might not be exactly the same as this is OS-dependant.
"""
import atexit
import logging
import logging.handlers
import multiprocessing
import os
import pickle
import psutil
import socketserver
import struct
import socket
import sys
import threading
from typing import List, Optional, Tuple, Union

import dlpt

DEFAULT_LOG_DIR_NAME = "log"
DEFAULT_LOG_FILE_EXT = ".log"
DEFAULT_LOG_SERVER_NAME = "logging_server"
DEFAULT_LOG_SERVER_FILE_NAME = f"{DEFAULT_LOG_SERVER_NAME}{DEFAULT_LOG_FILE_EXT}"

# https://docs.python.org/3/library/logging.html#logrecord-attributes
# Numbers after log item (for example: '+8') specify item length
# and position: +=right -=left aligned
DEFAULT_FMT = "%(name)-8s %(asctime)s.%(msecs)03d %(levelname)+8s: %(message)s"
DEFAULT_FMT_TIME = "%H:%M:%S"

DEFAULT_SERVER_FMT = "%(name)-8s %(asctime)s.%(msecs)03d %(levelname)+8s: %(message)s"
DEFAULT_SERVER_FMT_TIME = DEFAULT_FMT_TIME
DEFAULT_SERVER_SOCKET_PORT = logging.handlers.DEFAULT_TCP_LOGGING_PORT

DEFAULT_ROT_LOG_FILE_SIZE_KB = 100
DEFAULT_ROT_LOG_FILE_COUNT = 1

# private, do not modify
_default_logger: Optional[logging.Logger] = None
_SERVER_SHUTDOWN_KEY = "dlptLogServerShutdown"


def create_logger(
    name: Optional[str] = None, set_as_default: bool = True, level: Optional[int] = logging.DEBUG
) -> logging.Logger:
    """Create new logger instance with the given 'name' and optionally
    set it as a default logger whenever `dlpt.log.*` log functions are invoked.

    Args:
        name: Optional name of the new logger instance or root by default.
        set_as_default: If True, created logger instance will be set as a
            default logger whenewer `dlpt.log.*` log functions are invoked.
        level: log level for this specific logger. If None,
            everything is logged (``logging.DEBUG`` level).
    """
    global _default_logger
    if set_as_default:
        if _default_logger is not None:
            err_msg = f"Unable to create new default logger instance, default already set: {_default_logger.name}"
            raise Exception(err_msg)

    logger = logging.getLogger(name)
    if level:
        logger.setLevel(level)

    if set_as_default:
        _default_logger = logger

    return logger


def _get_logger(logger: Union[logging.Logger, str]) -> logging.Logger:
    """Allow user to specify logger by passing exact instance or logger name.
    Private function.

    Args:
        logger: logger instance or logger name.

    Returns:
        Logger instance object.
    """
    if isinstance(logger, str):
        if logger in logging.Logger.manager.loggerDict:
            return logging.getLogger(logger)
        else:
            err_msg = f"Logger with name '{logger}' does not exist. "
            err_msg += "Use `dlpt.log.create_logger()` or manually create new `logging.Logger` instance."
            raise ValueError(err_msg)
    else:
        return logger


def add_console_hdlr(
    logger: Union[logging.Logger, str], fmt: Optional[logging.Formatter] = None, level: int = logging.DEBUG
) -> logging.StreamHandler:
    """Add console handler to logger instance.

    Note:
        Create custom formatter with:
        ``logging.Formatter(<formatter>, datefmt=<time formatter>)``

    Args:
        logger: logger instance or logger name.
        fmt: Optional custom formatter for created handler. By default,
            DEFAULT_FORMATTER and DEFAULT_FORMATTER_TIME is used.
        level: set log level for this specific handler.
            By default, everything is logged (``DEBUG`` level).

    Returns:
        Created console (stream) handler object.
    """
    logger = _get_logger(logger)

    if fmt is None:  # pragma: no cover
        fmt = logging.Formatter(DEFAULT_FMT, datefmt=DEFAULT_FMT_TIME)

    hdlr = logging.StreamHandler()
    hdlr.setLevel(level)
    hdlr.setFormatter(fmt)

    logger.addHandler(hdlr)

    return hdlr


def add_file_hdlr(
    logger: Union[logging.Logger, str],
    file_name: Optional[str] = None,
    dir_path: Optional[str] = None,
    fmt: Optional[logging.Formatter] = None,
    level: int = logging.DEBUG,
    mode: str = "w",
) -> Tuple[logging.FileHandler, str]:
    """Add file handler to logger instance.

    Args:
        logger: logger instance or logger name.
        file_name: name of a log file. If there is no file extension, default
            ``DEFAULT_LOG_FILE_EXT`` is appended. If ``None``, logger name
            is used as a file name.
        dir_path: path to a directory where logs will be stored. If ``None``,
            path is fetched with :func:`get_default_log_dir()`.If log
            directory does not exist, it is created.
        fmt: Optional custom formatter for created handler. By default,
            DEFAULT_FORMATTER and DEFAULT_FORMATTER_TIME is used.
        level: Log level for this specific handler. By default,
            everything is logged (``DEBUG`` level).
        mode: file open mode (`"w`", "a", ... See logging docs.).

    Returns:
        A tuple: (created file handler, file path).
    """
    logger = _get_logger(logger)

    file_name = get_file_name(logger, file_name)
    if dir_path is None:
        dir_path = get_default_log_dir()  # pragma: no cover
    else:
        dir_path = os.path.normpath(dir_path)
    dlpt.pth.create_dir(dir_path)
    file_path = os.path.join(dir_path, file_name)

    if fmt is None:  # pragma: no cover
        fmt = logging.Formatter(DEFAULT_FMT, datefmt=DEFAULT_FMT_TIME)

    hdlr = logging.FileHandler(file_path, mode=mode, encoding="utf-8")
    hdlr.setLevel(level)
    hdlr.setFormatter(fmt)

    logger.addHandler(hdlr)

    return (hdlr, file_path)


def add_rotating_file_hdlr(
    logger: Union[logging.Logger, str],
    file_name: Optional[str] = None,
    dir_path: Optional[str] = None,
    fmt: Optional[logging.Formatter] = None,
    level: int = logging.DEBUG,
    max_size_kb: int = DEFAULT_ROT_LOG_FILE_SIZE_KB,
    backup_count: int = DEFAULT_ROT_LOG_FILE_COUNT,
) -> Tuple[logging.handlers.RotatingFileHandler, str]:
    """Add rotating file handler to logger instance.

    Args:
        logger: logger instance or logger name.
        file_name: name of a log file. If there is no file extension, default
            ``DEFAULT_LOG_FILE_EXT`` is appended. If ``None``, logger name
            is used as a file name.
        dir_path: path to a directory where logs will be stored. If ``None``,
            path is fetched with :func:`get_default_log_dir()`. If log
            directory does not exist, it is created.
        max_size_kb: number of KB at which rollover is performed on a
            current log file.
        backup_count: number of files to store (if file with given name
            already exists).
        fmt: Optional custom formatter for created handler. By default,
            DEFAULT_FORMATTER and DEFAULT_FORMATTER_TIME is used.
        level: Log level for this specific handler. By default,
            everything is logged (``DEBUG`` level).

    Returns:
        A tuple: (created rotating file handler, file path).
    """
    logger = _get_logger(logger)

    file_name = get_file_name(logger, file_name)
    if dir_path is None:
        dir_path = get_default_log_dir()  # pragma: no cover
    else:
        dir_path = os.path.normpath(dir_path)
    dlpt.pth.create_dir(dir_path)
    file_path = os.path.join(dir_path, file_name)

    if fmt is None:  # pragma: no cover
        fmt = logging.Formatter(DEFAULT_FMT, datefmt=DEFAULT_FMT_TIME)

    hdlr = logging.handlers.RotatingFileHandler(file_path, maxBytes=int(max_size_kb * 1e3), backupCount=backup_count)
    hdlr.setLevel(level)
    hdlr.setFormatter(fmt)

    logger.addHandler(hdlr)

    return (hdlr, file_path)


def add_logging_server_hdlr(
    logger: Union[logging.Logger, str],
    port: int = DEFAULT_SERVER_SOCKET_PORT,
    fmt: Optional[logging.Formatter] = None,
    level: int = logging.DEBUG,
) -> "_SocketHandler":
    """Add log socket handler to this logger instance.
    This function assume that log socket server is already initialized.

    Args:
        logger: logger instance or logger name.
        port: socket port where logger writes data to.
        fmt: Optional custom formatter for created handler. By default,
            ``DEFAULT_FORMATTER`` and ``DEFAULT_FORMATTER_TIME`` is used.
        level: Log level for this specific handler. By default,
            everything is logged (``DEBUG`` level).
    """
    logger = _get_logger(logger)

    if fmt is None:  # pragma: no cover
        fmt = logging.Formatter(DEFAULT_SERVER_FMT, datefmt=DEFAULT_FMT_TIME)

    hdlr = _SocketHandler("localhost", port)
    hdlr.setFormatter(fmt)
    hdlr.setLevel(level)

    logger.addHandler(hdlr)

    return hdlr


def get_log_file_paths(logger: Union[logging.Logger, str]) -> List[str]:
    """Return log file paths of `logging.FileHandler(s)` of a given logger instance.

    Args:
        logger: logger instance or logger name.

    Returns:
        List of loggers file handlers file paths.
    """
    logger = _get_logger(logger)

    file_paths = []
    for hdlr in logger.handlers:
        if isinstance(hdlr, logging.FileHandler):
            file_paths.append(os.path.normpath(hdlr.baseFilename))

    return file_paths


def get_rotating_log_file_paths(logger: Union[logging.Logger, str]) -> List[str]:
    """Return log file paths of `logging.RotatingFileHandler(s)` of a given
    logger instance.

    Args:
        logger: logger instance or logger name.

    Returns:
        List of loggers rotating file handlers file paths.
    """
    logger = _get_logger(logger)

    file_paths = []
    for hdlr in logger.handlers:
        if isinstance(hdlr, logging.handlers.RotatingFileHandler):
            file_paths.append(os.path.normpath(hdlr.baseFilename))

    return file_paths


def get_default_logger() -> Optional[logging.Logger]:
    """Get default logger instance object (if set).

    Returns:
        Current logger instance when `dlpt.log.*` log functions are invoked.
    """
    return _default_logger


def set_default_logger(logger: logging.Logger):
    """Set default logger instance.

    Args:
        logger: logger instance or logger name.

    Returns:
        Current logger instance object.
    """
    global _default_logger

    _default_logger = logger


def get_file_name(logger: Union[logging.Logger, str], file_name: Optional[str] = None) -> str:
    """Determine log file name, based on a current logger name or given `file_name`.

    Args:
        logger: logger instance or logger name.
        file_name: if given, this name is checked (for extension) or default
            file name is created from logger name.

    Returns:
        File name with extension.
    """
    logger = _get_logger(logger)

    if file_name is None:
        file_name = f"{logger.name}{DEFAULT_LOG_FILE_EXT}"
    else:
        if dlpt.pth.get_ext(file_name) == "":
            file_name = f"{file_name}{DEFAULT_LOG_FILE_EXT}"

    return file_name


def get_default_log_dir() -> str:
    """Get default log directory path: <cwd>/DEFAULT_LOG_DIR_NAME.

    Returns:
        Path to a directory where logs are usually created.
    """
    dir_path = os.path.join(os.getcwd(), DEFAULT_LOG_DIR_NAME)

    return dlpt.pth.resolve(dir_path)


def _check_default_logger() -> logging.Logger:
    """Check if default logger already exists and raise exception if not.

    Returns:
        Logger instance object.
    """
    if _default_logger is None:
        raise Exception("No default `dlpt.log` logger instance available.")
    else:
        return _default_logger


class ReleaseFileLock:
    def __init__(self, logger: Union[logging.Logger, str], file_path: str):
        """Temporary release file handler of logging file streams to be able
        to copy file (for example, log file is locked by logger on Windows.) Use
        as a context manager.

        Args:
            logger: logger instance or logger name.
            file_path: logging file path

        Example:
            >>> with dlpt.log.ReleaseFileLock(logger, file_path):
            >>>     shutil.move(file_path, tmp_path)
        """
        self.logger = _get_logger(logger)
        self.file_path = dlpt.pth.resolve(file_path)

        self.hdlrs: List[logging.FileHandler] = []

    def __enter__(self):
        """Flush and close file stream for all handlers derived from
        `logging.FileHandler` class.
        """
        for hdlr in self.logger.handlers:
            if isinstance(hdlr, logging.FileHandler):
                if dlpt.pth.resolve(hdlr.baseFilename) == self.file_path:
                    self.hdlrs.append(hdlr)
                    hdlr.flush()
                    hdlr.stream.close()
                    return

    def __exit__(self, exc_type, exc_value, traceback):
        """Re-open file handler stream with 'append' mode."""
        for hdlr in self.hdlrs:
            mode = hdlr.mode
            try:
                hdlr.mode = "a"
                hdlr.stream = hdlr._open()
            finally:
                hdlr.mode = mode


class _SocketHandler(logging.handlers.SocketHandler):
    def __init__(self, host: str, port: Optional[int] = None):
        super().__init__(host, port)

    # override internal makeSocket function (disable IPV6 by use of AF_INET)
    def makeSocket(self, timeout: int = 1):  # pragma: no cover
        if self.port is None:
            result = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result.settimeout(timeout)
            try:
                result.connect(self.address)
            except OSError:
                result.close()  # Issue 19182
                raise
        else:
            result = socket.create_connection(self.address, timeout=timeout)  # type: ignore
        return result


class _SocketRecordDataHandler(socketserver.StreamRequestHandler):
    """Socket server data handler - every received message is inspected and
    data is sent to a file. Code base taken from `here`_.

    .. _here:
        https://docs.python.org/3/howto/logging-cookbook.html
    """

    class ShutdownException(Exception):
        pass

    def handle(self):  # pragma: no cover
        """Handle multiple requests - each expected to be a 4-byte length,
        followed by the :class:`LogRecord` in pickle format. Calls
        :func:`handleLogRecord()` for each successfully received data packet.
        """
        while True:
            # receive data
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break

            # build and unpickle each received message (log record)
            slen = struct.unpack(">L", chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = pickle.loads(chunk)  # Un-pickle received data

            # handle message
            rec = logging.makeLogRecord(obj)
            if _SERVER_SHUTDOWN_KEY in rec.__dict__:
                msg = f"Logging server shutdown request by: {rec.processName}"
                logging.debug(msg)
                raise _SocketRecordDataHandler.ShutdownException(msg)
            else:
                logging.root.handle(rec)


class LoggingServer(socketserver.ThreadingTCPServer):
    """Simple TCP socket-based logging server (receiver).
    All messages are pickled at client TX side and un-pickled here.
    Any received message is than further handled by :func:`handleLogRecord()`.

    Sets `Allow address reuse`_.

    .. _Allow address reuse:
        https://docs.python.org/3/library/socketserver.html?highlight=threadingtcpserver#socketserver.BaseServer.allow_reuse_address
    """

    # Threading TCPServer so multiple connections can be created
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, port: int = DEFAULT_SERVER_SOCKET_PORT):
        """Init log socket server. By default, this server logs all received
        messages to a root logger as configured.

        Note:
            Use :func:`add_logging_server_hdlr()` function to add socket
            handler to any logger instance and logs will be
            automatically pushed to the created :class:`LoggingServer`
            process. Note that ports must be properly configured for logging
            to work.

        Args:
            port: port where socket server reads data from.
        """
        # socketserver.ThreadingTCPServer arguments
        super().__init__(("localhost", port), _SocketRecordDataHandler)

        # # Let's try and shutdown automatically on application exit...
        # atexit.register(self.server_close)

    def handle_error(self, request, client_address):
        exc_type, value, tb = sys.exc_info()
        if exc_type == _SocketRecordDataHandler.ShutdownException:
            self.shutdown()
            return
        else:
            self.handle_error(request, client_address)  # pragma: no cover


def create_log_server_proc(file_path: str, port: int = DEFAULT_SERVER_SOCKET_PORT) -> int:
    """Create socket server logger subprocess that logs all received messages
    on a given ``port`` socket to a log file handler.

    Args:
        file_path: absolute path to a log file, including extension.
        port: port where socket server will listen.

    Note:
        `port` number must be unique - this means that the default
        :func:`create_log_server_proc()` can be called only once. Further
        socket servers (of any process) and logger handlers must set ports
        manually.

    Returns:
        PID of created socket server subprocess.
    """
    if not _is_port_free(port):  # pragma: no cover
        raise Exception(f"Unable to reuse port {port} for a logging (socket server) purposes. Port in use?")

    socket_server_proc = multiprocessing.Process(
        target=_spawn_log_server_proc,
        args=(
            file_path,
            port,
        ),
        daemon=True,
    )

    socket_server_proc.start()
    assert socket_server_proc.pid is not None
    # Let's try and shutdown automatically on application exit...
    atexit.register(dlpt.proc.kill_tree, socket_server_proc.pid, False)

    return socket_server_proc.pid


def _is_port_free(port: int, host: str = "localhost") -> bool:
    """Return True if port is free, False otherwise.

    Note:
        Only TCP IPv4 port is checked.

    Args:
        port: port number to check.
        host: IP address or 'localhost' where port is `checked`_.

    Returns:
        ``True`` if selected TCP port is free, ``False`` otherwise.

    .. _checked:
        https://stackoverflow.com/questions/2470971/fast-way-to-test-if-a-port-is-in-use-using-python
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_hdlr:
        socket_hdlr.settimeout(0.2)
        is_free = False
        try:
            socket_hdlr.bind((host, port))
            is_free = True
        except Exception as err:  # pragma: no cover
            pass

        return is_free


def _spawn_log_server_proc(file_path: str, port: int):  # pragma: no cover
    """Function that is spawned as subprocess (see
    :func:`create_log_server_proc()`) and initialize log socket server and
    file log handler.

    Args:
        file_path: absolute path to a log file, including extension.
        port: port where socket server will listen.
    """
    logger = create_logger(set_as_default=False)
    fmt = logging.Formatter(DEFAULT_SERVER_FMT, datefmt=DEFAULT_SERVER_FMT_TIME)
    file_name = dlpt.pth.get_name(file_path)
    dir_path = os.path.dirname(file_path)
    add_file_hdlr(logger, file_name, dir_path, fmt)

    server = LoggingServer(port)

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    t.join()

    logging.shutdown()


def log_server_shutdown_request(logger: Union[logging.Logger, str], pid: int, timeout_sec: int = 3) -> bool:
    """Send 'unique' log message that indicates to server to perform
    shutdown - close all connections and finish process.

    Args:
        logger: logger instance or logger name. Note that logging server
            handler must be available in this logger.
        pid: logging server PID.
        timeout_sec: time to wait until logging server PID is checked for status.
            In case of 0, function return value is not relevant.

    Returns:
        True if server was successfully stopped (PID not alive anymore), False
        otherwise.
    """
    logger = _get_logger(logger)

    for hdlr in logger.handlers:
        if isinstance(hdlr, _SocketHandler):
            record = logging.makeLogRecord(
                {
                    _SERVER_SHUTDOWN_KEY: True,
                    "levelno": logging.DEBUG,
                }
            )
            hdlr.handle(record)

            try:
                proc = psutil.Process(pid)
                proc.wait(timeout_sec)
                return True
            except psutil.TimeoutExpired:  # pragma: no cover
                return False
    else:
        err_msg = "Given logger does not have 'logging server handler' added, unable to send server shutdown request."
        raise Exception(err_msg)


def _determine_logger(logger: Union[None, logging.Logger, str] = None) -> logging.Logger:
    """Determine logger instance when `dlpt.log.debug/info/...` functions are
    used. If `logger` is None, try to use the default logger else try to fetch
    existing logger instance based on a given name. Raise exception if logger
    instance can't be determined.

    Args:
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`create_logger()`) if exists, or exception
            is raised.

    Returns:
        Logger instance object.
    """
    if logger is None:
        logger = _check_default_logger()
    else:
        logger = _get_logger(logger)

    return logger


def debug(msg: str, logger: Union[logging.Logger, str] = None, *args, **kwargs):
    """Log to a given or default logger (if available) with 'DEBUG' level.

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`create_logger()`).
    """
    logger = _determine_logger()

    logger.debug(msg, *args, **kwargs)


def info(msg: str, logger: Union[logging.Logger, str] = None, *args, **kwargs):
    """Log to a given or default logger (if available) with 'INFO' level.

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`create_logger()`).
    """
    logger = _determine_logger()

    logger.info(msg, *args, **kwargs)


def warning(msg: str, logger: Union[logging.Logger, str] = None, *args, **kwargs):
    """Log to a given or default logger (if available) with 'WARNING' level.

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`create_logger()`).
    """
    logger = _determine_logger()

    logger.warning(msg, *args, **kwargs)


def warning_with_traceback(msg: str, logger: Union[logging.Logger, str] = None, *args, **kwargs):
    """Log to a given or default logger (if available) with 'WARNING' level
    and append exception info traceback at the end (if available).

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`create_logger()`).
    """
    _, _, tb = sys.exc_info()
    if tb is not None:
        kwargs["exc_info"] = True
    warning(msg, logger, *args, **kwargs)


def error(msg: str, logger: Union[logging.Logger, str] = None, *args, **kwargs):
    """Log to a given or default logger (if available) with 'ERROR' level.

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`create_logger()`).
    """
    logger = _determine_logger()

    logger.error(msg, *args, **kwargs)


def error_with_traceback(msg: str, logger: Union[logging.Logger, str] = None, *args, **kwargs):
    """Log to a given or default logger (if available) with 'ERROR' level
    and append exception info traceback at the end (if available).

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`create_logger()`).
    """
    _, _, tb = sys.exc_info()
    if tb is not None:
        kwargs["exc_info"] = True
    error(msg, logger, *args, **kwargs)


def critical(msg: str, logger: Union[logging.Logger, str] = None, *args, **kwargs):
    """Log to a given or default logger (if available) with 'CRITICAL' level.

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`create_logger()`).
    """
    logger = _determine_logger()

    logger.critical(msg, *args, **kwargs)


def critical_with_traceback(msg: str, logger: Union[logging.Logger, str] = None, *args, **kwargs):
    """Log to a given or default logger (if available) with 'CRITICAL' level
    and append exception info traceback at the end (if available).

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`create_logger()`).
    """
    _, _, tb = sys.exc_info()
    if tb is not None:
        kwargs["exc_info"] = True
    critical(msg, logger, *args, **kwargs)
