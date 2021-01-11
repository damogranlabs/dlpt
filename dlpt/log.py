"""
Common LogHandler and LogSocketServer interface for general logging.

1. LogHandler if set, instance of such logger can log to:
 - console (terminal)
 - file
 - socket (client)

Note:
    As all handlers are optional, user must take care to manually configure logger.
    First instance of ``LogHandler`` is stored as a default log handler. Any 
    further ``dlpt.log`` log statement will, by default, use this logger instance.
    Optionally, modules can initialize custom logger instances and set ``setAsDefault``
    to False.

2. LogSocketServer is a subprocess that use rotation log file handler to log 
data from all configured logs to one place.

Note:
    LogSocketServer port number must be unique - this means that default 
    :func:`createSocketServerProc()` can be called only once. Further socket
    servers (of any process) must set ports manually.
"""
import functools
import logging
import logging.handlers
import os
import multiprocessing
import pickle
import socketserver
import struct
import sys
import socket
import time
import traceback
from typing import Optional

import dlpt

DEFAULT_LOG_FOLDER_NAME = "log"
DEFAULT_LOG_FILE_EXT = ".log"
DEFAULT_NAME = "root"
DEFAULT_MERGED_LOG_NAME = "sharedLog"
DEFAULT_MERGED_LOG_FILE_NAME = f"{DEFAULT_MERGED_LOG_NAME}{DEFAULT_LOG_FILE_EXT}"

# https://docs.python.org/3/library/logging.html#logrecord-attributes
# Numbers after log item (for example: '+8') specify item length and position: +=right -=left aligned
DEFAULT_FORMATTER = "%(name)-8s %(asctime)s.%(msecs)03d %(levelname)+8s: %(message)s"
DEFAULT_FORMATTER_TIME = "%H:%M:%S"

DEFAULT_SOCKET_FORMATTER = "%(name)-8s %(asctime)s.%(msecs)03d %(levelname)+8s: %(message)s"
DEFAULT_SOCKET_FORMATTER_TIME = DEFAULT_FORMATTER_TIME
DEFAULT_SOCKET_PORT = logging.handlers.DEFAULT_TCP_LOGGING_PORT

DEFAULT_ROTATING_LOG_FILE_SIZE_MB = 1
DEFAULT_ROTATING_LOG_FILE_COUNT = 1

# log location format
LOG_LOCATION_TITLE = "Log location:"
LOG_LOCATION_INDENT_STR = "  "  # \t can give a large offset.


# private, do not modify
_defaultLogger: Optional["LogHandler"] = None
_defaultSocketLogger: Optional["LogHandler"] = None


class LogHandler():
    def __init__(self, loggerName: str = DEFAULT_NAME, setAsDefault: bool = True):
        """ This class holds all settings to manage log handler.

        Args:
            loggerName: unique logger name.
                If logger with such name already exists, it is overwritten.
            setAsDefault: if True, created logger is set as default logger.
        """
        self._name: str = loggerName
        self._isDefaultLogHandler: bool = setAsDefault
        self._logFilePath: Optional[str] = None
        self._logRotatingFilePath: Optional[str] = None

        self.loggers = logging.getLogger(self._name)
        # NOTE: read logger docs 'setLevel()'. By default, root logger is created with level
        # WARNING, but here we manually set it to DEBUG.
        self.loggers.setLevel(logging.DEBUG)

        # remove all handlers, if this logger instance already exists
        self.removeAllHanders()

        if self._isDefaultLogHandler:
            setDefaultLogger(self)

        # create log function aliases with default parameters as this LogHandler instance
        self.debug = functools.partial(debug, handler=self)
        self.info = functools.partial(info, handler=self)
        self.warning = functools.partial(warning, handler=self)
        self.error = functools.partial(error, handler=self)
        self.criticalError = functools.partial(criticalError, handler=self)

    def addConsoleHandler(self, formatter: Optional[logging.Formatter] = None, logLevel: int = logging.DEBUG):
        """ Add console handler to this logger instance.

        Note:
            Create custom formatter with:
            ``logging.Formatter(<formatter string>, datefmt=<time formatter string>)``

        Args:
            formatter: if not None, override default formatter.
            logLevel: set log level for this specific handler. 
                By default, everything is logged (``DEBUG`` level).

        """
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(logLevel)

        if formatter is None:
            formatter = logging.Formatter(DEFAULT_FORMATTER, datefmt=DEFAULT_FORMATTER_TIME)
        consoleHandler.setFormatter(formatter)

        self.loggers.addHandler(consoleHandler)

    def addFileHandler(self,
                       fileName: Optional[str] = None,
                       folderPath: Optional[str] = None,
                       formatter: Optional[logging.Formatter] = None,
                       logLevel: int = logging.DEBUG,
                       mode: str = "w+") -> str:
        """ Add file handler to this logger instance and return a path to a log file.

        Note:
            Only single file handler per ``LogHandler`` can be added.

        Note:
            Create custom formatter with:
            ``logging.Formatter(<formatter string>, datefmt=<time formatter string>)``

        Args:
            fileName: name of a log file. If there is no file extension, default
                ``DEFAULT_LOG_FILE_EXT`` is appended. If ``None``, default 
                file name is fetched with :func:`getDefaultLogFileName()`.
            folderPath: path to a folder where logs will be stored. If ``None``,
                path is fetched with :func:`getDefaultLogFolderPath()`.If log
                folder does not exist, it is created.
            formatter: if not None, override default formatter.
            logLevel: set log level for this specific handler. By default,
                everything is logged (``DEBUG`` level).
            mode: file open mode ("w+", "a", ... See logging docs.).
        """
        if self._logFilePath is not None:
            errorMsg = f"Unable to add another log file handler - already configured to log to: {self._logFilePath}"
            raise Exception(errorMsg)

        if fileName is None:
            fileName = getDefaultLogFileName(self._name)
        else:
            _, ext = os.path.splitext(fileName)
            if ext == '':
                fileName = fileName + DEFAULT_LOG_FILE_EXT
        if folderPath is None:
            folderPath = getDefaultLogFolderPath()
        else:
            folderPath = os.path.normpath(folderPath)
        self._logFilePath = os.path.join(folderPath, fileName)
        dlpt.pth.createFolder(folderPath)

        fileHandler = logging.FileHandler(self._logFilePath, mode=mode, encoding='utf-8')
        fileHandler.setLevel(logLevel)

        if formatter is None:
            formatter = logging.Formatter(DEFAULT_FORMATTER, datefmt=DEFAULT_FORMATTER_TIME)
        fileHandler.setFormatter(formatter)

        self.loggers.addHandler(fileHandler)

        return self._logFilePath

    def addRotatingFileHandler(self,
                               fileName: Optional[str] = None,
                               folderPath: Optional[str] = None,
                               maxSizeMb: float = DEFAULT_ROTATING_LOG_FILE_SIZE_MB,
                               backupCount: int = DEFAULT_ROTATING_LOG_FILE_COUNT,
                               formatter: Optional[logging.Formatter] = None,
                               logLevel: int = logging.DEBUG) -> str:
        """ Add rotating file handler to this logger instance and return a path to a
        log file.

        Note:
            Only single rotation file handler per LogHandler can be added.

        Note:
            Create custom formatter with:
            ``logging.Formatter(<formatter string>, datefmt=<time formatter string>)``

        Args:
            fileName: name of a log file. If there is no file extension, default 
                ``DEFAULT_LOG_FILE_EXT`` is appended. If ``None``, default file
                name is fetched with :func:`getDefaultLogFileName()`.
            folderPath: path to a folder where logs will be stored. If ``None`,
                path is fetched with :func:`getDefaultLogFolderPath()`. If log
                folder does not exist, it is created.
            maxSizeMb: number of MB at which rollover is performed on a 
                current log file.
            backupCount: number of files to store (if file with given name already exists).
            formatter: if not None, override default formatter.
            logLevel: set log level for this specific handler. By default,
                everything is logged (``DEBUG`` level).
        """
        if self._logRotatingFilePath is not None:
            errorMsg = f"Unable to add another log rotating file handler - already configured to log to: "
            errorMsg += f"{self._logRotatingFilePath}"
            raise Exception(errorMsg)

        if fileName is None:
            fileName = getDefaultLogFileName(self._name)
        else:
            _, ext = os.path.splitext(fileName)
            if ext == '':
                fileName = fileName + DEFAULT_LOG_FILE_EXT
        if folderPath is None:
            folderPath = getDefaultLogFolderPath()
        else:
            folderPath = os.path.normpath(folderPath)
        self._logRotatingFilePath = os.path.join(folderPath, fileName)

        dlpt.pth.createFolder(folderPath)

        sizeMb = int(maxSizeMb * 1e6)
        rotFileHandler = logging.handlers.RotatingFileHandler(self._logRotatingFilePath,
                                                              mode='a+',
                                                              maxBytes=sizeMb,
                                                              backupCount=backupCount)
        rotFileHandler.setLevel(logLevel)

        if formatter is None:
            formatter = logging.Formatter(DEFAULT_FORMATTER, datefmt=DEFAULT_FORMATTER_TIME)
        rotFileHandler.setFormatter(formatter)

        self.loggers.addHandler(rotFileHandler)

        return self._logRotatingFilePath

    def addSocketHandler(self,
                         port: int = DEFAULT_SOCKET_PORT,
                         formatter: Optional[logging.Formatter] = None,
                         logLevel: int = logging.DEBUG):
        """ Add log socket handler to this logger instance.
        This function assume that log socket server is already initialized.

        Note:
            Create custom formatter with:
            ``logging.Formatter(<formatter string>, datefmt=<time formatter string>)``

        Args:
            port: socket port where logger writes data to.
            formatter: if not ``None``, override default formatter
            logLevel: set log level for this specific handler. By default,
                everything is logged (DEBUG level).
        """
        for handler in self.loggers.handlers:
            if isinstance(handler, _SocketHandler):
                errorMsg = f"Unable to add another log socket handler - already configured."
                raise Exception(errorMsg)

        socketHandler = _SocketHandler('localhost', port)

        if formatter is None:
            formatter = logging.Formatter(DEFAULT_SOCKET_FORMATTER,
                                          datefmt=DEFAULT_FORMATTER_TIME)
        socketHandler.setFormatter(formatter)
        socketHandler.setLevel(logLevel)

        self.loggers.addHandler(socketHandler)

    def removeAllHanders(self):
        """ Safely remove all enabled (example: console, file, ...) log handlers
        from this logger logHandler instance.

        Note:
            In contrast to :func:`removeFileHandlers()`, this function does not
            clear internal log file/folder paths variables data.
        """
        while len(self.loggers.handlers):
            self.loggers.removeHandler(self.loggers.handlers[0])

    def removeFileHandlers(self):
        """ Safely remove file and rotating file log handlers from this logger
        instance.
        """
        handlersCopy = self.loggers.handlers.copy()
        for handler in handlersCopy:
            if isinstance(
                    handler, logging.FileHandler) or isinstance(
                    handler, logging.handlers.RotatingFileHandler):
                self.loggers.removeHandler(handler)

        self._logFilePath = None

        self._logRotatingFileName = None
        self._logRotatingFilePath = None

    def isDefaultLogHandler(self) -> bool:
        """ Returns True if this logger instance is set as default log handler.
        """
        return self._isDefaultLogHandler

    def getName(self) -> str:
        """ Return this logger instance name.
        Source name is specified only at logger instance creation.
        """
        return self._name

    def getLogFilePath(self) -> Optional[str]:
        """ Return this logger instance log file path (if handler is set).
        """
        return self._logFilePath

    def getRotatingLogFilePath(self) -> Optional[str]:
        """ Return this logger instance rotating log file path (if handler is set).
        """
        return self._logRotatingFilePath


def _checkDefaultLogger():
    """ Check if default log handler already exists and raise exception if not.
    """
    if _defaultLogger is None:
        errorMsg = "No logger instance available."
        raise Exception(errorMsg)


def setDefaultLogger(handler: LogHandler):
    """ Set given handler as a default logger handler.

    Args:
        handler: new default log handler to set.
    """
    global _defaultLogger
    _defaultLogger = handler


def getDefaultLogger() -> Optional[LogHandler]:
    """ Get default logger handler instance.
    """
    return _defaultLogger


def closeAllLoggers():
    """ Close all created loggers and release file handlers, ...
    This is usually by default called on application exit.
    """
    global _defaultLogger

    if _defaultLogger is not None:
        _defaultLogger.removeAllHanders()
        _defaultLogger = None
    logging.shutdown()


def getDefaultLogFileName(loggerName: Optional[str] = None) -> str:
    """ Get default log file name: <logerName>_<DATE_TIME_FORMAT_FILE_NAME>.log.

    Args:
        loggerName: name of a logger. If ``None``, default log file name
            is datetime string + extension.
    """
    logFileName = dlpt.time.getCurrentDateTime(dlpt.time.DATE_TIME_FORMAT_FILE_NAME) + DEFAULT_LOG_FILE_EXT
    if loggerName is not None:
        logFileName = f"{loggerName}_{logFileName}"

    return logFileName


def getDefaultLogFolderPath(path: Optional[str] = None) -> str:
    """ Get default log folder path.

    Note:
        If ``path`` is set, it must exist (to be able to determine if given
        path is file or folder).

    Args:
        path: if ``None``, <cwd>/log folder is returned. Otherwise: if path is
            FILE: <file directory>/log folder is returned. If path is FOLDER:
            <path>/log folder is returned.
    """
    if path is None:
        path = os.path.join(os.getcwd(), DEFAULT_LOG_FOLDER_NAME)
    else:
        dlpt.pth.check(path)
        if os.path.isdir(path):
            path = os.path.join(path, DEFAULT_LOG_FOLDER_NAME)
        else:
            path = os.path.join(os.path.dirname(path), DEFAULT_LOG_FOLDER_NAME)

    return dlpt.pth.resolve(path)


def _formatExceptionLocation(tracebackStr: str) -> str:
    """Format traceback file/line format to a default editor format:
    * original format: <file>, line <lineNumber>, in <function>
    * new format: <file>:<lineNumber> in <function>

    Args:
        tracebackStr: traceback string in a default format.
    """
    tracebackStr = tracebackStr.replace("\", line ", ":")

    return tracebackStr


def getErrorTraceback() -> str:
    """Get a string of a beautified traceback data.

    Note:
        As it turned out, manually building stack data trace ``inspect.stack()``, 
        ``.trace()`` and ``sys.exc_info()`` is quite complicated, so current 
        implementation just analyze lines of traceback data, fetched with
        ``traceback.format_exc()``.
    """
    tracebackStr = ''

    tbData = sys.exc_info()[1]
    if tbData is not None:
        tracebackStr = traceback.format_exc()
        tracebackStr = _formatExceptionLocation(tracebackStr)

    return tracebackStr.rstrip()


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
            result = socket.create_connection(self.address, timeout=timeout)
        return result


class _SocketRecordDataHandler(socketserver.StreamRequestHandler):
    """ Socket server data handler - every received message is inspected and 
    data is sent to a file.
    Code base taken from `here`_.

    .. _here:
        https://docs.python.org/3/howto/logging-cookbook.html
    """

    def handle(self):  # pragma: no cover
        """ Handle multiple requests - each expected to be a 4-byte length, 
        followed by the ``LogRecord`` in pickle format. Calls 
        :func:`self.handleLogRecord()` for each successfully received data packet.
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
            record = logging.makeLogRecord(obj)
            self.handleLogRecord(record)

    def handleLogRecord(self, record):  # pragma: no cover
        """Handle unpickled received data.

        Args:
            record: unpickled received data in logging.LogRecord format.
        """
        _defaultSocketLogger.loggers.handle(record)


class LogSocketServer(socketserver.ThreadingTCPServer):  # Threading TCPServer so multiple connections can be created
    """ Simple TCP socket-based logging server (receiver).
    All messages are pickled at client TX side and un-pickled here.
    Any received message is than further handled by 'handleLogRecord()'

    Sets `Allow address reuse`_.

    .. _Allow address reuse:
        https://docs.python.org/3/library/socketserver.html?highlight=threadingtcpserver#socketserver.BaseServer.allow_reuse_address
    """
    allow_reuse_address = True

    def __init__(self, logger: LogHandler, port: int = DEFAULT_SOCKET_PORT):  # pragma: no cover
        """Init log socket server. By default, this server logs all received
        messages to file, optionally to console.

        Note:
            Socket handler must not be added to a given ``logger`` instance.

        Args:
            logger: log handler instance that already has configured log handlers.
            port: port where socket server reads data from.
        """
        global _defaultSocketLogger
        _defaultSocketLogger = logger

        # socketserver.ThreadingTCPServer arguments
        super().__init__(('localhost', port), _SocketRecordDataHandler)


def _isPortFree(port: int, host: str = 'localhost') -> bool:
    """Return True if port is free, False otherwise.

    Note:
        Only TCP IPv4 port is checked.

    Args:
        port: port number to check.
        host: IP address or 'localhost' where port is `checked`_.

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


def createSocketServerProc(logFilePath: str, port=DEFAULT_SOCKET_PORT) -> int:
    """Create socket server subprocess that use given ``socketServerLogger`` to
    log data to one place with file log handler. Return PID of spawned socket
    server process.
    Exception is raised if default timeout is reached while waiting for a socket
    server process PID.

    Args:
        logFilePath: absolute path to a log file, including extension.
        port: port where socket server will listen.
    """
    SPAWN_TIMEOUT_SEC = 4
    if not _isPortFree(port):  # pragma: no cover
        # port already in use.
        errorMsg = f"Unable to reuse port {port} for a logging (socket server) purposes."
        raise Exception(errorMsg)

    socketServerProc = multiprocessing.Process(target=_spawnSocketServerProc, args=(logFilePath, port,))
    socketServerProc.daemon = True
    socketServerProc.start()

    endTime = time.time() + SPAWN_TIMEOUT_SEC
    while time.time() < endTime:
        if socketServerProc.is_alive():
            if socketServerProc.pid is not None:
                return socketServerProc.pid

    errorMsg = f"Unable to initialize socket server subprocess in {SPAWN_TIMEOUT_SEC} sec"  # pragma: no cover
    raise Exception(errorMsg)  # pragma: no cover


def _spawnSocketServerProc(logFilePath: str, port: int):  # pragma: no cover
    """ Function that is spawned as subprocess (see ``createSocketServerProc()``)
    and  initialize log socket server and file log handler.

    Args:
        logFilePath: absolute path to a log file, including extension.
        port: port where socket server will listen.
    """
    socketServerLogger = LogHandler()
    formatter = logging.Formatter(DEFAULT_SOCKET_FORMATTER, datefmt=DEFAULT_SOCKET_FORMATTER_TIME)
    fileName = dlpt.pth.getName(logFilePath)
    folderPath = os.path.dirname(logFilePath)
    socketServerLogger.addFileHandler(fileName, folderPath, formatter=formatter)

    socketServer = LogSocketServer(socketServerLogger, port)

    socketServer.serve_forever()


def debug(msg: str, handler: Optional[LogHandler] = None):
    """Log with 'DEBUG' level.

    Args:
        msg: message to log.
        handler: use specific handler, otherwise use default log handler.
    """
    if handler is None:
        _checkDefaultLogger()
        handler = _defaultLogger

    handler.loggers.debug(msg)


def info(msg: str, handler: Optional[LogHandler] = None):
    """ Log with 'INFO' level.

    Args:
        msg: message to log.
        handler: use specific handler, otherwise use default log handler
    """
    if handler is None:
        _checkDefaultLogger()
        handler = _defaultLogger

    handler.loggers.info(msg)


def warning(msg: str,
            showTraceback: bool = False,
            handler: Optional[LogHandler] = None,
            ignoreCallerFuncDepth: int = 2):
    """ Log with 'WARNING' level.

    Args:
        msg: message to log.
        handler: use specific handler, otherwise use default log handler.
        ignoreCallerFuncDepth: number of stack traces to ignore when 
            getting log location.
    """
    if handler is None:
        _checkDefaultLogger()
        handler = _defaultLogger

    if showTraceback:
        tbStr = getErrorTraceback()
        if tbStr != '':
            locStr = dlpt.utils.getCallerLocation(ignoreCallerFuncDepth)
            msg = f"{msg}\n{tbStr}\n{LOG_LOCATION_INDENT_STR}{locStr}"

    handler.loggers.warning(msg)


def error(msg: str,
          showTraceback: bool = True,
          handler: Optional[LogHandler] = None,
          ignoreCallerFuncDepth: int = 2):
    """ Log with 'ERROR' level.

    Args:
        msg: message to log.
        showTraceback: if True, error traceback is added to message.
        handler: use specific handler, otherwise use default log handler.
        ignoreCallerFuncDepth: number of stack traces to ignore when 
            getting log location.
    """
    if handler is None:
        _checkDefaultLogger()
        handler = _defaultLogger

    if showTraceback:
        tbStr = getErrorTraceback()
        if tbStr != '':
            locStr = dlpt.utils.getCallerLocation(ignoreCallerFuncDepth)
            msg = f"{msg}\n{tbStr}\n{LOG_LOCATION_INDENT_STR}{locStr}"
    handler.loggers.error(msg)


def criticalError(msg: str,
                  handler: Optional[LogHandler] = None,
                  ignoreCallerFuncDepth: int = 2):
    """ Log with 'CRITICAL' level, always add error traceback

    Args:
        msg: message to log.
        handler: use specific handler, otherwise use default log handler.
        ignoreCallerFuncDepth: number of stack traces to ignore when 
            getting log location.
    """
    if handler is None:
        _checkDefaultLogger()
        handler = _defaultLogger

    tbStr = getErrorTraceback()
    if tbStr != '':
        locStr = dlpt.utils.getCallerLocation(ignoreCallerFuncDepth)
        msg = f"{msg}\n{tbStr}\n{LOG_LOCATION_INDENT_STR}{locStr}"

    handler.loggers.critical(msg)
