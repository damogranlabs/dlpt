import logging
import os
import time

import pytest

import dlpt
import dlpt.log as log

from dlpt.tfix import *

LOG_TEST_SOCKETSRV_FILE_NAME = "socketSrv.log"

CUSTOM_FORMATTER = "%(asctime)s.%(msecs)05d %(levelname)s: %(message)s"


def test_LogFileHandlerData():
    folderPath = os.path.dirname(__file__)
    formatter = logging.Formatter(log.DEFAULT_FORMATTER,
                                  datefmt=log.DEFAULT_FORMATTER_TIME)

    data = log._LogFileHandlerData("fName.log",
                                   folderPath,
                                   formatter,
                                   logging.CRITICAL,
                                   "w+")

    assert data.getFileName() == "fName.log"
    assert data.getFolderPath() == folderPath
    assert data.getFilePath() == os.path.join(data.getFolderPath(), data.getFileName())

    data = log._LogRotatingFileHandlerData("rotFName.log",
                                           folderPath,
                                           formatter,
                                           logging.CRITICAL,
                                           10,
                                           3)

    assert data.getFileName() == "rotFName.log"
    assert data.getFolderPath() == folderPath
    assert data.getFilePath() == os.path.join(data.getFolderPath(), data.getFileName())


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_defaultNamesPaths():
    FOLDER_PATH = os.path.dirname(__file__)

    hdl = log.LogHandler()

    # log file naming
    assert "test.log" == hdl._getFileName("test")
    assert "test.log" == hdl._getFileName("test.log")
    assert f"{hdl.getName()}.log" == hdl._getFileName()

    # log folder path
    folderPath = os.path.join(os.getcwd(), log.DEFAULT_LOG_FOLDER_NAME)
    assert folderPath.lower() == hdl._getFolderPath().lower()

    assert FOLDER_PATH == hdl._getFolderPath(FOLDER_PATH)


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_LogHandler():
    with pytest.raises(Exception):
        log.error("Raise error, no default logger yet")

    hdl1 = log.LogHandler()
    assert hdl1.getName() == log.DEFAULT_NAME
    assert hdl1.isDefaultHandler() == True
    assert log.getDefaultLogger() == hdl1

    hdl2 = log.LogHandler("myNonDefault", False)
    assert hdl2.getName() == "myNonDefault"
    assert hdl2.isDefaultHandler() == False

    # new loghandler, but default is already existing
    with pytest.raises(Exception):
        log.LogHandler("newDefault")

    # new LogHandler, but logger with the same already exists
    with pytest.raises(Exception):
        log.LogHandler(setAsDefault=False)


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_addConsoleHandler():
    hdl = log.LogHandler()
    hdl.addConsoleHandler()

    log.info("Just log something.")


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_addFileHandler(tmp_path):
    hdl = log.LogHandler()
    hdl.addConsoleHandler()

    with pytest.raises(Exception):
        # file handler not yet set
        hdl.getLogFilePath()

    filePath = hdl.addFileHandler(folderPath=tmp_path)

    log.info("Just log something which will create file.")

    assert os.path.samefile(tmp_path, os.path.dirname(filePath))
    assert os.path.exists(filePath) is True
    assert os.path.samefile(hdl.getLogFilePath(), filePath) is True

    with pytest.raises(Exception):
        # already existing file handler
        hdl.addFileHandler()


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_addRotatingFileHandler(tmp_path):
    hdl = log.LogHandler()
    hdl.addConsoleHandler()

    with pytest.raises(Exception):
        # file handler not yet set
        hdl.getRotatingLogFilePath()

    filePath = hdl.addRotatingFileHandler(folderPath=tmp_path)

    log.info("Just log something which will create rotating file.")

    assert os.path.samefile(tmp_path, os.path.dirname(filePath))
    assert os.path.exists(filePath) is True
    assert os.path.samefile(hdl.getRotatingLogFilePath(), filePath) is True

    with pytest.raises(Exception):
        # already existing file handler
        hdl.addRotatingFileHandler()


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_addSocketHandler(tmp_path):
    filePath = os.path.join(tmp_path, LOG_TEST_SOCKETSRV_FILE_NAME)
    socketServerPid = log.createSocketServerProc(filePath)

    try:
        hdl = log.LogHandler()
        hdl.addConsoleHandler()
        hdl.addSocketHandler()

        log.info("Just log something which will create shared socket log file.")
        assert os.path.exists(filePath) is True

        with pytest.raises(Exception):
            # already existing socket handler
            hdl.addSocketHandler()

        with pytest.raises(Exception):
            # Already existing socket handler (used default port)
            log.createSocketServerProc(filePath)

        hdl2 = log.LogHandler("newLogger", False)
        hdl2.addConsoleHandler()
        hdl2.warning(f"Logged to console, but not to socket file handler.")

        time.sleep(1)
        with open(filePath, "r") as fHandler:
            assert len(fHandler.readlines()) == 1

    finally:
        dlpt.proc.killTree(socketServerPid)


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_logLevel(tmp_path):
    # use default logger and log to a console and file
    hdl = log.LogHandler()
    hdl.addConsoleHandler(logLevel=logging.INFO)
    filePath = hdl.addFileHandler(folderPath=tmp_path, logLevel=logging.WARNING)

    log.debug("Statement not added to any handler, file should not be created.")
    log.info("Statement visible in console handler, but not in file (will not be creat file).")
    with open(filePath, "r") as fHandler:
        assert len(fHandler.readlines()) == 0

    log.warning("Statement visible in all handlers, file should be created.")
    with open(filePath, "r") as fHandler:
        assert len(fHandler.readlines()) == 1


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_removeHandlers(tmp_path):
    hdl = log.LogHandler()
    hdl.addConsoleHandler()
    filePath = hdl.addFileHandler(folderPath=tmp_path)

    log.info("Just log something which will create file.")
    with open(filePath, 'r') as fHandler:
        assert len(fHandler.readlines()) == 1

    hdl.removeHandlers(True)
    log.info("Another thing is logged, but only to console")
    with open(filePath, 'r') as fHandler:
        assert len(fHandler.readlines()) == 1

    # NOTE: no easy way to check console output
    hdl.removeHandlers()
    log.info("Another thing is logged, not visible anywhere (no handlers)")


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_fileMode(tmp_path):
    FILE_NAME = "myLogger.log"
    logger = log.LogHandler()
    logger.addConsoleHandler()
    # default mode
    filePath = logger.addFileHandler(FILE_NAME, tmp_path)
    log.info("Just log something which will create file.")

    logger.removeHandlers(True)
    log.info("Another thing is logged, but only to console")

    # reopen file in 'append' mode
    filePath = logger.addFileHandler(FILE_NAME, tmp_path, mode='a')
    log.info("Another thing is logged, added also to the file")  # 2

    log.closeLogHandlers()
    with open(filePath, 'r') as fHandler:
        assert len(fHandler.readlines()) == 2


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_logLevelsFuncArgs(tmp_path):
    hdl = log.LogHandler()
    hdl.addConsoleHandler()
    filePath = hdl.addFileHandler(folderPath=tmp_path)

    log.debug("dMsg")
    log.info("iMsg")
    log.warning("wMsg")
    log.error("eMsg")
    log.criticalError("cMsg")

    log.debug("dMsg", hdl)
    log.info("iMsg", hdl)
    log.warning("wMsg", handler=hdl)
    log.error("eMsg", handler=hdl)
    log.criticalError("cMsg", hdl)

    log.warning("wMsg", True)
    log.error("eMsg", False, hdl, 3)
    log.criticalError("cMsg", hdl, 3)

    with open(filePath, 'r') as fileHandler:
        defaultLoggerLines = fileHandler.readlines()
        assert len(defaultLoggerLines) == 5 + 5 + 3


@pytest.mark.usefixtures("dlptCloseLogHandlers")
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


@pytest.mark.usefixtures("dlptCloseLogHandlers")
def test_rotatingLogHandlerFileCount(tmp_path):
    # use default logger and log to a console and file.
    ROT_LOG_FILENAME = 'rotLogName.log'
    ROT_LOG_FILE_SIZE_KB = 10

    defaultLogger = log.LogHandler()
    formatter = logging.Formatter(CUSTOM_FORMATTER)  # msec digits specified in CUSTOM_FORMATTER
    filePath = defaultLogger.addRotatingFileHandler(ROT_LOG_FILENAME, tmp_path,
                                                    maxSizeKb=ROT_LOG_FILE_SIZE_KB, backupCount=2,
                                                    formatter=formatter)
    assert filePath == defaultLogger.getRotatingLogFilePath()

    # write to log more than
    sizeBytes = int(ROT_LOG_FILE_SIZE_KB * 1e3)
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
    assert logFileSize > ((ROT_LOG_FILE_SIZE_KB - 1) * 1e3)
    assert logFileSize < ((ROT_LOG_FILE_SIZE_KB + 1) * 1e3)
