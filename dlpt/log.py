""" Common wrappers and helper functions to simplify most common use cases of
builtin 'logging' module.

1. Create logger and (optionally) set it as a default `dlpt` logger. 
    Note: 
        'Default' logger means that (once initialized), any `dlpt` log 
        functions, such as  :func:`info()` and :func:`warning()` will log to 
        created logger. It is therefore possible to initialize logger in one 
        place and use it in all other project files just by importing `dlpt.log`
        and use the default logger.
2. Use `add*()` functions to add common handlers to created logger instance:
    console (terminal) handler, file handler, rotating file handler, server 
    socket handler (for logs when multiple processes are used).

## Logging server
To unify logs from multiple processes, user can create logging server via 
function :func:`createLoggingServerProc()`. This process will create a custom 
logger with file handler and open a socket connection on a designated port.
Any logger (from process), that has configured logging server handler (via 
:func:`addLoggingServerHandler()`) will push logs to this logging server and to
a file. Note that log statements order might not be exactly the same as this is
OS-dependant.
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
DEFAULT_LOG_SERVER_NAME = "loggingServer"
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
_defaultLogger: Optional[logging.Logger] = None
_SERVER_SHUTDOWN_KEY = "dlptLogServerShutdown"


def createLogger(name: Optional[str] = None,
                 setAsDefault: bool = True,
                 level: Optional[int] = logging.DEBUG) -> logging.Logger:
    """ Create new logger instance with the given 'name' and optionally
    set it as a default logger whenever `dlpt.log.*` log functions are invoked.

    Args:
        name: Optional name of the new logger instance or root by default.
        setAsDefault: If True, created logger instance will be set as a
            default logger whenewer `dlpt.log.*` log functions are invoked..
        logLevel: set log level for this specific logger.
            By default, everything is logged (``DEBUG`` level).
        logLevel: set log level for this specific logger. If None, do not
            change log level. By default, everything is logged (``DEBUG`` level).
    """
    global _defaultLogger
    if setAsDefault:
        if _defaultLogger is not None:
            errorMsg = f"Unable to create new default logger instance, "
            errorMsg += f"default already set: {_defaultLogger.name}"
            raise Exception(errorMsg)

    logger = logging.getLogger(name)
    if level:
        logger.setLevel(level)

    if setAsDefault:
        _defaultLogger = logger

    return logger


def _getLogger(logger: Union[logging.Logger, str]) -> logging.Logger:
    """ Allow user to specify logger by passing exact instance or logger name.
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
            errorMsg = f"Logger with name '{logger}' does not exist. Use "
            errorMsg += "`dlpt.log.createLogger()` or manually create new "
            errorMsg += "logging.Logger instance."
            raise ValueError(errorMsg)
    else:
        return logger


def addConsoleHandler(logger: Union[logging.Logger, str],
                      fmt: Optional[logging.Formatter] = None,
                      level: int = logging.DEBUG) -> logging.StreamHandler:
    """ Add console handler to logger instance.

    Note:
        Create custom formatter with:
        ``logging.Formatter(<formatter>, datefmt=<time formatter>)``

    Args:
        logger: logger instance or logger name.
        fmt: Optional custom formatter for created handler. By default,
            DEFAULT_FORMATTER and DEFAULT_FORMATTER_TIME is used.
        logLevel: set log level for this specific handler.
            By default, everything is logged (``DEBUG`` level).

    Returns:
        Created console (stream) handler object.
    """
    logger = _getLogger(logger)

    if fmt is None:  # pragma: no cover
        fmt = logging.Formatter(DEFAULT_FMT,
                                datefmt=DEFAULT_FMT_TIME)

    hdlr = logging.StreamHandler()
    hdlr.setLevel(level)
    hdlr.setFormatter(fmt)

    logger.addHandler(hdlr)

    return hdlr


def addFileHandler(logger: Union[logging.Logger, str],
                   fName: Optional[str] = None,
                   dirPath: Optional[str] = None,
                   fmt: Optional[logging.Formatter] = None,
                   level: int = logging.DEBUG,
                   mode: str = "w") -> Tuple[logging.FileHandler, str]:
    """ Add file handler to logger instance.

    Args:
        logger: logger instance or logger name.
        fName: name of a log file. If there is no file extension, default
            ``DEFAULT_LOG_FILE_EXT`` is appended. If ``None``, logger name
            is used as a file name.
        dirPath: path to a folder where logs will be stored. If ``None``,
            path is fetched with :func:`getDefaultLogDirPath()`.If log
            folder does not exist, it is created.
        fmt: Optional custom formatter for created handler. By default,
            DEFAULT_FORMATTER and DEFAULT_FORMATTER_TIME is used.
        level: Log level for this specific handler. By default,
            everything is logged (``DEBUG`` level).
        mode: file open mode (`"w`", "a", ... See logging docs.).

    Returns:
        A tuple: (created file handler, file path).
    """
    logger = _getLogger(logger)

    fName = getFileName(logger, fName)
    if dirPath is None:
        dirPath = getDefaultLogDirPath()  # pragma: no cover
    else:
        dirPath = os.path.normpath(dirPath)
    dlpt.pth.createFolder(dirPath)
    fPath = os.path.join(dirPath, fName)

    if fmt is None:  # pragma: no cover
        fmt = logging.Formatter(DEFAULT_FMT,
                                datefmt=DEFAULT_FMT_TIME)

    hdlr = logging.FileHandler(fPath,
                               mode=mode,
                               encoding='utf-8')
    hdlr.setLevel(level)
    hdlr.setFormatter(fmt)

    logger.addHandler(hdlr)

    return (hdlr, fPath)


def addRotatingFileHandler(logger: Union[logging.Logger, str],
                           fName: Optional[str] = None,
                           dirPath: Optional[str] = None,
                           fmt: Optional[logging.Formatter] = None,
                           level: int = logging.DEBUG,
                           maxSizeKb: int = DEFAULT_ROT_LOG_FILE_SIZE_KB,
                           backupCount: int = DEFAULT_ROT_LOG_FILE_COUNT) -> Tuple[
                               logging.handlers.RotatingFileHandler,
                               str]:
    """ Add rotating file handler to logger instance.

    Args:
        logger: logger instance or logger name.
        fName: name of a log file. If there is no file extension, default
            ``DEFAULT_LOG_FILE_EXT`` is appended. If ``None``, logger name
            is used as a file name.
        dirPath: path to a folder where logs will be stored. If ``None``,
            path is fetched with :func:`getDefaultLogDirPath()`. If log
            folder does not exist, it is created.
        maxSizeKb: number of KB at which rollover is performed on a
            current log file.
        backupCount: number of files to store (if file with given name
            already exists).
        fmt: Optional custom formatter for created handler. By default,
            DEFAULT_FORMATTER and DEFAULT_FORMATTER_TIME is used.
        level: Log level for this specific handler. By default,
            everything is logged (``DEBUG`` level).

    Returns:
        A tuple: (created rotating file handler, file path).
    """
    logger = _getLogger(logger)

    fName = getFileName(logger, fName)
    if dirPath is None:
        dirPath = getDefaultLogDirPath()  # pragma: no cover
    else:
        dirPath = os.path.normpath(dirPath)
    dlpt.pth.createFolder(dirPath)
    fPath = os.path.join(dirPath, fName)

    if fmt is None:  # pragma: no cover
        fmt = logging.Formatter(DEFAULT_FMT,
                                datefmt=DEFAULT_FMT_TIME)

    hdlr = logging.handlers.RotatingFileHandler(
        fPath,
        maxBytes=int(maxSizeKb * 1e3),
        backupCount=backupCount)
    hdlr.setLevel(level)
    hdlr.setFormatter(fmt)

    logger.addHandler(hdlr)

    return (hdlr, fPath)


def addLoggingServerHandler(logger: Union[logging.Logger, str],
                            port: int = DEFAULT_SERVER_SOCKET_PORT,
                            fmt: Optional[logging.Formatter] = None,
                            level: int = logging.DEBUG) -> "_SocketHandler":
    """ Add log socket handler to this logger instance.
    This function assume that log socket server is already initialized.

    Args:
        logger: logger instance or logger name.
        port: socket port where logger writes data to.
        fmt: Optional custom formatter for created handler. By default,
            DEFAULT_FORMATTER and DEFAULT_FORMATTER_TIME is used.
        level: Log level for this specific handler. By default,
            everything is logged (``DEBUG`` level).
    """
    logger = _getLogger(logger)

    if fmt is None:  # pragma: no cover
        fmt = logging.Formatter(DEFAULT_SERVER_FMT,
                                datefmt=DEFAULT_FMT_TIME)

    hdlr = _SocketHandler('localhost', port)
    hdlr.setFormatter(fmt)
    hdlr.setLevel(level)

    logger.addHandler(hdlr)

    return hdlr


def getLogFilePaths(logger: Union[logging.Logger, str]) -> List[str]:
    """ Return log file paths of `FileHandler(s)` of a given logger instance.

    Args:
        logger: logger instance or logger name.

    Returns:
        List of loggers file handlers file paths.
    """
    logger = _getLogger(logger)

    fPaths = []
    for hdlr in logger.handlers:
        if isinstance(hdlr, logging.FileHandler):
            fPaths.append(os.path.normpath(hdlr.baseFilename))

    return fPaths


def getRotatingLogFilePaths(logger: Union[logging.Logger, str]) -> List[str]:
    """ Return log file paths of `RotatingFileHandler(s)` of a given logger
    instance.

    Args:
        logger: logger instance or logger name.

    Returns:
        List of loggers rotating file handlers file paths.
    """
    logger = _getLogger(logger)

    fPaths = []
    for hdlr in logger.handlers:
        if isinstance(hdlr, logging.handlers.RotatingFileHandler):
            fPaths.append(os.path.normpath(hdlr.baseFilename))

    return fPaths


def getDefaultLogger() -> Optional[logging.Logger]:
    """ Get default logger instance object (if set).

    Returns:
        Current logger instance when `dlpt.log.*` log functions are
        invoked.
    """
    return _defaultLogger


def setDefaultLogger(logger: logging.Logger):
    """ Set default logger instance.

    Args:
        Logger 
    Returns:
        Current logger instance object.
    """
    global _defaultLogger

    _defaultLogger = logger


def getFileName(logger: Union[logging.Logger, str],
                fName: Optional[str] = None) -> str:
    """ Determine log file name, based on a current logger
    name or given `fName`.

    Args:
        logger: logger instance or logger name.
        fName: if given, this name is checked (for extension) or default
            file name is created from logger name.

    Returns:
        File name with extension.
    """
    logger = _getLogger(logger)

    if fName is None:
        fName = f"{logger.name}{DEFAULT_LOG_FILE_EXT}"
    else:
        if dlpt.pth.getExt(fName) == "":
            fName = f"{fName}{DEFAULT_LOG_FILE_EXT}"

    return fName


def getDefaultLogDirPath() -> str:
    """ Get default log folder path: <cwd>/log folder.

    Returns:
        Path to a folder where logs are usually created.
    """
    dirPath = os.path.join(os.getcwd(), DEFAULT_LOG_DIR_NAME)

    return dlpt.pth.resolve(dirPath)


def _checkDefaultLogger() -> logging.Logger:
    """ Check if default logger already exists and raise exception
    if not.

    Returns:
        Logger instance object.
    """
    if _defaultLogger is None:
        errorMsg = "No default logger instance available."
        raise Exception(errorMsg)
    else:
        return _defaultLogger


class ReleaseFileLock():
    def __init__(self,
                 logger: Union[logging.Logger, str],
                 fPath: str):
        """ Temporary release file handler of logging file streams to be able 
        to copy file (for example, log file is locked by logger on Windows.) Use
        as a context manager.

        Args:
            logger: logger instance or logger name.
            fPath: logging file path

        Example:
            >>> with dlpt.log.ReleaseFileLock(logger, fPath):
            >>>     shutil.move(fPath, tmp_path)
        """
        self.logger = _getLogger(logger)
        self.fPath = dlpt.pth.resolve(fPath)

        self.hdlrs: List[logging.FileHandler] = []

    def __enter__(self):
        """ Flush and close file stream for all handlers derived from 
        `logging.FileHandler` class.
        """
        for hdlr in self.logger.handlers:
            if isinstance(hdlr, logging.FileHandler):
                if dlpt.pth.resolve(hdlr.baseFilename) == self.fPath:
                    self.hdlrs.append(hdlr)
                    hdlr.flush()
                    hdlr.stream.close()
                    return

    def __exit__(self, exc_type, exc_value, traceback):
        """ Re-open file handler stream with 'append' mode.
        """
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
            result = socket.create_connection(self.address,  # type: ignore
                                              timeout=timeout)
        return result


class _SocketRecordDataHandler(socketserver.StreamRequestHandler):
    """ Socket server data handler - every received message is inspected and
    data is sent to a file. Code base taken from `here`_.

    .. _here:
        https://docs.python.org/3/howto/logging-cookbook.html
    """
    class ShutdownException(Exception):
        pass

    def handle(self):  # pragma: no cover
        """ Handle multiple requests - each expected to be a 4-byte length,
        followed by the :class:`LogRecord` in pickle format. Calls
        :func:`handleLogRecord()` for each successfully received data packet.
        """
        while True:
            # receive data
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break

            # build and unpickle each received message (log record)
            slen = struct.unpack('>L', chunk)[0]
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
    """ Simple TCP socket-based logging server (receiver).
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
        """ Init log socket server. By default, this server logs all received
        messages to a root logger as configured.

        Note:
            Use :func:`addLoggingServerHandler()` function to add socket
            handler to any logger instance and logs will be
            automatically pushed to the created :class:`LoggingServer`
            process. Note that ports must be properly configured for logging
            to work.

        Args:
            port: port where socket server reads data from.
        """
        # socketserver.ThreadingTCPServer arguments
        super().__init__(('localhost', port), _SocketRecordDataHandler)

        # # Let's try and shutdown automatically on application exit...
        # atexit.register(self.server_close)

    def handle_error(self, request, client_address):
        exc_type, value, tb = sys.exc_info()
        if exc_type == _SocketRecordDataHandler.ShutdownException:
            self.shutdown()
            return
        else:
            self.handle_error(request, client_address)  # pragma: no cover


def createLoggingServerProc(fPath: str,
                            port: int = DEFAULT_SERVER_SOCKET_PORT) -> int:
    """ Create socket server logger subprocess that logs all received messages
    on a given ``port`` socket to a log file handler.

    Args:
        fPath: absolute path to a log file, including extension.
        port: port where socket server will listen.

    Note:
        `port` number must be unique - this means that the default 
        :func:`createLoggingServerProc()` can be called only once. Further
        socket servers (of any process) and logger handlers must set ports 
        manually.

    Returns:
        PID of created socket server subprocess.
    """
    if not _isPortFree(port):  # pragma: no cover
        errorMsg = f"Unable to reuse port {port} for a logging "
        errorMsg += "(socket server) purposes. Port in use?"
        raise Exception(errorMsg)

    socketServerProc = multiprocessing.Process(target=_spawnLoggingServerProc,
                                               args=(fPath, port,),
                                               daemon=True)

    socketServerProc.start()
    assert socketServerProc.pid is not None
    # Let's try and shutdown automatically on application exit...
    atexit.register(dlpt.proc.killTree,
                    socketServerProc.pid,
                    False)

    return socketServerProc.pid


def _isPortFree(port: int, host: str = "localhost") -> bool:
    """ Return True if port is free, False otherwise.

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
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socketHandler:
        socketHandler.settimeout(0.2)
        isFree = False
        try:
            socketHandler.bind((host, port))
            isFree = True
        except Exception as err:  # pragma: no cover
            pass

        return isFree


def _spawnLoggingServerProc(fPath: str, port: int):  # pragma: no cover
    """ Function that is spawned as subprocess (see
    :func:`createLoggingServerProc()`) and initialize log socket server and
    file log handler.

    Args:
        fPath: absolute path to a log file, including extension.
        port: port where socket server will listen.
    """
    logger = createLogger(setAsDefault=False)
    fmt = logging.Formatter(DEFAULT_SERVER_FMT,
                            datefmt=DEFAULT_SERVER_FMT_TIME)
    fName = dlpt.pth.getName(fPath)
    dirPath = os.path.dirname(fPath)
    addFileHandler(logger, fName, dirPath, fmt)

    server = LoggingServer(port)

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    t.join()


def loggingServerShutdownRequest(logger: Union[logging.Logger, str],
                                 pid: int,
                                 timeoutSec: int = 3) -> bool:
    """ Send 'unique' log message that indicates to server to perform 
    shutdown - close all connections and finish process.

    Args:
        logger: logger instance or logger name. Note that logging server 
            handler must be available in this logger.
        pid: logging server PID.
        timeoutSec: time to wait until logging server PID is checked for status.
            In case of 0, function return value is not relevant.

    Returns:
        True if server was successfully stopped (PID not alive anymore), False 
        otherwise.
    """
    logger = _getLogger(logger)

    for hdlr in logger.handlers:
        if isinstance(hdlr, _SocketHandler):
            record = logging.makeLogRecord({_SERVER_SHUTDOWN_KEY: True,
                                            "levelno": logging.DEBUG,
                                            })
            hdlr.handle(record)

            try:
                proc = psutil.Process(pid)
                proc.wait(timeoutSec)
                return True
            except psutil.TimeoutExpired:  # pragma: no cover
                return False
    else:
        errorMsg = "Given logger does not have 'logging server handler' added, "
        errorMsg += "unable to send server shutdown request."
        raise Exception(errorMsg)


def _determineLogger(logger: Union[None,
                                   logging.Logger,
                                   str] = None) -> logging.Logger:
    """ Determine logger instance when `dlpt.log.debug/info/...` functions are 
    used. If `logger` is None, try to use the default logger else try to fetch 
    existing logger instance based on a given name. Raise exception if logger 
    instance can't be determined.

    Args:
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`createLogger()`) if exists, or exception 
            is raised.

    Returns:
        Logger instance object.
    """
    if logger is None:
        logger = _checkDefaultLogger()
    else:
        logger = _getLogger(logger)

    return logger


def debug(msg: str,
          logger: Union[logging.Logger, str] = None,
          *args, **kwargs):
    """ Log to a given or default logger (if available) with 'DEBUG' level.

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`createLogger()`).
    """
    logger = _determineLogger()

    logger.debug(msg, *args, **kwargs)


def info(msg: str,
         logger: Union[logging.Logger, str] = None,
         *args, **kwargs):
    """ Log to a given or default logger (if available) with 'INFO' level.

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`createLogger()`).
    """
    logger = _determineLogger()

    logger.info(msg, *args, **kwargs)


def warning(msg: str,
            logger: Union[logging.Logger, str] = None,
            *args, **kwargs):
    """ Log to a given or default logger (if available) with 'WARNING' level.

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`createLogger()`).
    """
    logger = _determineLogger()

    logger.warning(msg, *args, **kwargs)


def error(msg: str,
          logger: Union[logging.Logger, str] = None,
          *args, **kwargs):
    """ Log to a given or default logger (if available) with 'ERROR' level.

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`createLogger()`).
    """
    logger = _determineLogger()

    logger.error(msg, *args, **kwargs)


def critical(msg: str,
             logger: Union[logging.Logger, str] = None,
             *args, **kwargs):
    """ Log to a given or default logger (if available) with 'CRITICAL' level.

    Args:
        msg: message to log.
        logger: logger instance or logger name. If not set, default logger
            is used (as set by :func:`createLogger()`).
    """
    logger = _determineLogger()

    logger.critical(msg, *args, **kwargs)
