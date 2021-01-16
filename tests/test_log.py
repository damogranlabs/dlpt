import logging
import pathlib
import os
import time

import pytest

import dlpt
import dlpt.log as log

from dlpt.tfix import *

LOG_TEST_FOLDER_NAME = "logTestFolder_"
LOG_TEST_FILE_NAME = "testLogFile.log"

LOG_TEST_SOCKETSRV_FOLDER_NAME = "socketSrv_"
LOG_TEST_SOCKETSRV_FILE_NAME = "socketSrv.log"

EXTRA_LOGGER_NAME = 'extraLogger2'
DEFAULT_MSG = 'This is a default log entry message.'
EXTRA_MSG = 'This is an extra logger log entry message.'

CUSTOM_FORMATTER = "%(asctime)s.%(msecs)05d %(levelname)s: %(message)s"

THIS_FILE = str(pathlib.Path(__file__).resolve())


@pytest.mark.usefixtures("tmp_path", "closeAllLogHandlers")
def test_basic(tmp_path):
    # no existing logger
    with pytest.raises(Exception):
        log.warning("Will fail, no existing logger.")

    # use default logger and log to a console and file
    logger = log.LogHandler()
    logger.addConsoleHandler()
    logFilePath = logger.addFileHandler(LOG_TEST_FILE_NAME, tmp_path)
    rotLogFilePath = logger.addRotatingFileHandler(fileName="rotating", folderPath=tmp_path)
    # logger.addSocketHandler() # see socket server test for logging via socket server

    log.info("Something should be logged, files should be created.")

    timeout = time.time() + 2
    while(len(dlpt.pth.getFilesInFolder(tmp_path)) != 2):
        if time.time() > timeout:
            assert False, f"2 files are expected, but they were not generated in 2 seconds after log statement!"

    # already existing log handlers
    with pytest.raises(Exception):
        logger.addFileHandler()
    with pytest.raises(Exception):
        logger.addRotatingFileHandler()


@pytest.mark.usefixtures("tmp_path", "closeAllLogHandlers")
def test_logLevel(tmp_path):
    # use default logger and log to a console and file
    logger = log.LogHandler()
    logger.addConsoleHandler(logLevel=logging.WARNING)
    logFilePath = logger.addFileHandler(folderPath=tmp_path, logLevel=logging.WARNING)

    log.debug("This log statement should not be visible in console and file should not be created.")
    log.info("This log statement should not be visible in console and file should not be created.")
    with open(logFilePath, "r") as fHandler:
        assert len(fHandler.readlines()) == 0

    log.warning("This log statement should be visible in console and file should be created.")
    with open(logFilePath, "r") as fHandler:
        assert len(fHandler.readlines()) == 1


@pytest.mark.usefixtures("tmp_path", "closeAllLogHandlers")
def test_removeHandlers(tmp_path):
    logger = log.LogHandler()
    logger.addConsoleHandler()
    filePath = logger.addFileHandler(folderPath=tmp_path)
    log.info("Something should be logged, files should be created.")  # 1
    with open(filePath, 'r') as fHandler:
        assert len(fHandler.readlines()) == 1
    logger.removeFileHandlers()
    log.info("Another thing is logged, but only to console")
    with open(filePath, 'r') as fHandler:
        assert len(fHandler.readlines()) == 1

    # NOTE: no easy way to check console output
    logger.removeAllHanders()
    log.info("Another thing is logged, not visible anywhere (no handlers)")


@pytest.mark.usefixtures("tmp_path", "closeAllLogHandlers")
def test_fileMode(tmp_path):
    logger = log.LogHandler()
    logger.addConsoleHandler()
    # default mode
    filePath = logger.addFileHandler(folderPath=tmp_path)
    log.info("Something should be logged, files should be created.")  # 1
    logger.removeFileHandlers()
    log.info("Another thing is logged, but only to console")

    # reopen file in 'append' mode
    filePath = logger.addFileHandler(folderPath=tmp_path, mode='a')
    log.info("Another thing is logged, added also to the file")  # 2

    log.closeAllLoggers()
    with open(filePath, 'r') as fHandler:
        assert len(fHandler.readlines()) == 2


@pytest.mark.usefixtures("tmp_path", "closeAllLogHandlers")
def test_multipleLoggers(tmp_path):
    LOG_HANDLER_METHOD_STR = "LogHandler class method: "
    # use default logger and log to a console and file (custom formatter).
    defaultLogger = log.LogHandler()
    defaultLogger.addConsoleHandler()
    defaultLoggerFilePath = defaultLogger.addFileHandler(folderPath=tmp_path)

    # additional logger, only logs to file
    extraLogger = log.LogHandler(EXTRA_LOGGER_NAME, setAsDefault=False)
    extraLogger.addConsoleHandler()
    extraLoggerFilePath = extraLogger.addFileHandler(folderPath=tmp_path)

    assert defaultLogger.isDefaultLogHandler() is True
    assert extraLogger.isDefaultLogHandler() is False
    assert defaultLogger == log.getDefaultLogger()

    # log two predefined messages and check them by inspecting file
    log.debug(DEFAULT_MSG)
    extraLogger.error(EXTRA_MSG)
    # use LogHandler class methods
    defaultLogger.debug(LOG_HANDLER_METHOD_STR + DEFAULT_MSG)
    extraLogger.debug(LOG_HANDLER_METHOD_STR + EXTRA_MSG)

    with open(defaultLoggerFilePath, 'r') as fileHandler:
        defaultLoggerLines = fileHandler.readlines()
        assert len(defaultLoggerLines) == 2
        assert defaultLoggerLines[0].find(DEFAULT_MSG) != -1
        assert defaultLoggerLines[1].find(LOG_HANDLER_METHOD_STR) != -1

    with open(extraLoggerFilePath, 'r') as fileHandler:
        extraLoggerLines = fileHandler.readlines()
        assert len(extraLoggerLines) == 2
        assert extraLoggerLines[0].find(EXTRA_MSG) != -1
        assert extraLoggerLines[1].find(LOG_HANDLER_METHOD_STR) != -1

    # just check if any of the following calls accept all arguments
    log.info("infoMsg")
    log.warning("infoMsg")
    log.error("errorMsg", False)
    log.criticalError("criticalErrorMsg")
    with open(defaultLoggerFilePath, 'r') as fileHandler:
        defaultLoggerLines = fileHandler.readlines()
        assert len(defaultLoggerLines) == 6  # 2 at the beginning, 4 now: all levels


@pytest.mark.usefixtures("tmp_path", "closeAllLogHandlers")
def test_pathsNames(tmp_path):
    logFolder = log.getDefaultLogFolderPath()
    assert str(pathlib.Path(os.getcwd()).resolve()) in logFolder
    assert logFolder.endswith("log")

    logFolder = log.getDefaultLogFolderPath(__file__)
    assert os.path.join(os.path.dirname(THIS_FILE), "log") == logFolder

    logFolder = log.getDefaultLogFolderPath(os.getcwd())
    assert str(pathlib.Path(f"{os.getcwd()}/log").resolve()) == logFolder

    defaultLogFileName = log.getDefaultLogFileName()
    assert dlpt.pth.getExt(defaultLogFileName) == ".log"

    defaultLogger = log.LogHandler()
    assert defaultLogger.getName() == log.DEFAULT_NAME
    defaultLogger.addConsoleHandler()
    defaultLoggerFilePath = defaultLogger.addFileHandler(fileName="nameWithoutExtension", folderPath=tmp_path)
    assert defaultLoggerFilePath.startswith(str(tmp_path))
    filePath = defaultLogger.getLogFilePath()
    assert filePath is not None
    assert os.path.samefile(defaultLoggerFilePath, filePath)

    defaultLoggerRotFilePath = defaultLogger.addRotatingFileHandler(folderPath=tmp_path)
    assert defaultLoggerRotFilePath.startswith(str(tmp_path))

    # check default log file path (instead of specifying folder path)
    logger = log.LogHandler()
    defaultLogFilePath = None
    try:
        # default log file path
        defaultLogFilePath = logger.addFileHandler()

        assert 'log' in pathlib.Path(defaultLogFilePath).parts
        assert defaultLogFilePath.endswith('.log')
    except Exception as err:
        pass
    finally:
        log.closeAllLoggers()
        if defaultLogFilePath is not None:
            dlpt.pth.removeFolderTree(os.path.dirname(defaultLogFilePath))

    try:
        # default log file path
        defaultLogFilePath = logger.addRotatingFileHandler()

        assert 'log' in pathlib.Path(defaultLogFilePath).parts
        assert defaultLogFilePath.endswith('.log')
    except Exception as err:
        pass
    finally:
        log.closeAllLoggers()
        if defaultLogFilePath is not None:
            dlpt.pth.removeFolderTree(os.path.dirname(defaultLogFilePath))


@pytest.mark.usefixtures("tmp_path", "closeAllLogHandlers")
def test_customFormatter(tmp_path):
    CUSTOM_MSG = "MessageWithoutAnySpacesForParsing"
    TEST_FORMATTER = "%(levelname)s: %(message)s (%(asctime)s.%(msecs)05d)"

    # use default logger and log to a console and file with custom formatter
    defaultLogger = log.LogHandler()
    defaultLogger.addConsoleHandler()
    # msec digits specified in TEST_FORMATTER
    formatter = logging.Formatter(TEST_FORMATTER, datefmt=log.DEFAULT_FORMATTER_TIME)
    defaultLoggerFilePath = defaultLogger.addFileHandler(folderPath=tmp_path, formatter=formatter)

    log.debug(CUSTOM_MSG)

    # exception traceback location formattion
    try:
        raise Exception("Test exception!")
    except Exception as err:
        log.warning("warning msg with traceback", True)
        log.error("errorMsg with traceback")
        log.criticalError("criticalErrorMsg with traceback")

    currentTime = dlpt.time.getCurrentDateTime(dlpt.time.TIME_FORMAT, 5)
    currentTimeParts = currentTime.split(':')
    with open(defaultLoggerFilePath, 'r') as fileHandler:
        defaultLoggerLines = fileHandler.readlines()

        # first log statement, debug with custom formatter
        defaultLoggerLines[0] = defaultLoggerLines[0].strip()
        lineParts = defaultLoggerLines[0].split(' ')
        assert lineParts[0] == "DEBUG:"
        assert lineParts[1] == CUSTOM_MSG
        assert lineParts[2].startswith('(') and lineParts[2].endswith(')')
        timeParts = lineParts[2].strip('(').strip(')').split(':')
        assert timeParts[0] == currentTimeParts[0]
        assert timeParts[1] == currentTimeParts[1]
        assert timeParts[2].find('.') != -1
        sec = timeParts[2].split('.')
        assert len(sec[0]) == 2
        # NOTE: no simple way to check msec format

        # warning, error, critical error traceback
        assert defaultLoggerLines.count("Traceback (most recent call last):\n") == 3
        assert "WARNING: warning msg with traceback\n" in defaultLoggerLines
        assert "ERROR: errorMsg with traceback\n" in defaultLoggerLines
        assert "CRITICAL: criticalErrorMsg with traceback\n" in defaultLoggerLines

        # traceback message, check formatted location
        line = defaultLoggerLines[-1]
        assert f"{dlpt.pth.getName(__file__)}:" in line


@pytest.mark.usefixtures("tmp_path", "closeAllLogHandlers")
def test_rotatingLogHandler(tmp_path):
    # use default logger and log to a console and file.
    ROT_LOG_FILENAME = 'rotLogName.log'
    ROT_LOG_FILE_SIZE_MB = 0.05

    defaultLogger = log.LogHandler()
    formatter = logging.Formatter(CUSTOM_FORMATTER)  # msec digits specified in TEST_FORMATTER
    filePath = defaultLogger.addRotatingFileHandler(ROT_LOG_FILENAME, tmp_path,
                                                    maxSizeMb=ROT_LOG_FILE_SIZE_MB, backupCount=2,
                                                    formatter=formatter)
    assert filePath == defaultLogger.getRotatingLogFilePath()

    # write to log more than
    sizeBytes = int(ROT_LOG_FILE_SIZE_MB * 1e6)
    logStringSize = len("Write: ".ljust(15, ' '))
    numOfWrites = int(sizeBytes / logStringSize * 2.5)  # primary and two old log files should be present

    for byte in range(numOfWrites):
        log.info(f"Write: {byte}".ljust(15, ' '))

    logFiles = dlpt.pth.getFilesInFolder(tmp_path)
    assert len(logFiles) == 3

    assert filePath in logFiles
    assert f"{filePath}.1" in logFiles
    assert f"{filePath}.2" in logFiles

    logFileSize = os.path.getsize(f"{filePath}.1")
    assert logFileSize > 48 * 1e3
    assert logFileSize < 51 * 1e3


@pytest.mark.usefixtures("tmp_path", "closeAllLogHandlers", "dlptKillTestSubprocs")
def test_socketServer(tmp_path):
    log1 = log.LogHandler('logger1')
    log1.addSocketHandler()
    log2 = log.LogHandler('logger2', setAsDefault=False)
    log2.addSocketHandler()
    log3 = log.LogHandler('logger3', setAsDefault=False)
    log3.addConsoleHandler()

    logFilePath = os.path.join(tmp_path, LOG_TEST_SOCKETSRV_FILE_NAME)
    socketServerPid = log.createSocketServerProc(logFilePath)

    log.info('infoMsg')
    log2.info('infoMsg')
    time.sleep(0.5)
    log.error('errorMsg')
    log2.error('errorMsg')
    log3.warning('warningMsg, non-shared')
    time.sleep(1)

    with pytest.raises(Exception):
        log1.addSocketHandler()  # already existing socket handler

    # must be done manually, otherwise temp folder can't be deleted.
    log.closeAllLoggers()
    dlpt.proc.killTree(socketServerPid)

    dlpt.pth.check(logFilePath)
    with open(logFilePath) as fHandler:
        lines = fHandler.readlines()
    assert len(lines) == 4

    # socket server might not sort messages correctly (timestamps are valid, while line order might be wrong)
    assert ('infoMsg' in lines[0]) and ('infoMsg' in lines[1])
    assert ('logger1' in lines[0]) or ('logger1' in lines[1])
    assert ('logger2' in lines[0]) or ('logger2' in lines[1])

    assert ('errorMsg' in lines[2]) and ('errorMsg' in lines[3])
    assert ('logger1' in lines[2]) or ('logger1' in lines[3])
    assert ('logger2' in lines[2]) or ('logger2' in lines[3])

    assert dlpt.utils.searchStrInLines('warningMsg, non-shared', lines) is None
