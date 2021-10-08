import datetime
import logging
import logging.handlers
import os
import shutil
import socket
import time
from unittest import mock
from typing import Iterator

import pytest

import dlpt
import dlpt.log as log


FMT_STR = "%(asctime)s.%(msecs)05d %(levelname)s: %(message)s"
CUSTOM_FMT = logging.Formatter(FMT_STR)
LOG_MSG_OK = "level-OK"
LOG_MSG_NOT_LOGGED = "level<warning"

FILE_NAME = "logFile.log"


@pytest.fixture
def myLogger(request) -> Iterator[logging.Logger]:
    logger = log.createLogger(request.node.name)

    yield logger

    try:
        logging.Logger.manager.loggerDict.pop(logger.name)
    except Exception as err:
        pass
    log._defaultLogger = None


def test_createLogger():
    logger = log.createLogger(setAsDefault=False)
    assert logger.name == "root"

    logger = log.createLogger()  # set as default
    try:
        assert logger.name == "root"
        assert log._defaultLogger is not None
        assert log._defaultLogger.name == logger.name

        with pytest.raises(Exception):
            # can't set two loggers as a default
            log.createLogger()
    except Exception as err:
        raise
    finally:
        log._defaultLogger = None


def test_addConsoleHandler(myLogger: logging.Logger):
    assert len(myLogger.handlers) == 0
    hdlr = log.addConsoleHandler(myLogger, CUSTOM_FMT, logging.WARNING)
    assert len(myLogger.handlers) == 1
    assert isinstance(hdlr, logging.StreamHandler)

    with mock.patch.object(hdlr.stream, "write") as func:
        myLogger.info(LOG_MSG_NOT_LOGGED)
        func.assert_not_called()

        myLogger.warning(LOG_MSG_OK)
        func.assert_called_once()
        _checkFormat(func.call_args[0][0])


def test_addFileHandler(myLogger: logging.Logger, tmp_path):
    assert len(myLogger.handlers) == 0
    hdlr, fPath = log.addFileHandler(myLogger,
                                     FILE_NAME, tmp_path,
                                     CUSTOM_FMT,
                                     logging.WARNING)
    assert os.path.join(tmp_path, FILE_NAME) == fPath
    assert len(myLogger.handlers) == 1
    assert isinstance(hdlr, logging.FileHandler)
    assert os.path.exists(fPath)  # log file path is not delayed

    myLogger.info(LOG_MSG_NOT_LOGGED)
    with open(fPath, "r") as f:
        assert len(f.readlines()) == 0

    myLogger.warning(LOG_MSG_OK)
    with open(fPath, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        _checkFormat(lines[0])

    fPaths = log.getLogFilePaths(myLogger)
    assert len(fPaths) == 1
    assert fPaths[0] == fPath


def test_fileHandlerLogFile(myLogger: logging.Logger, tmp_path):
    hdlr, fPath = log.addFileHandler(myLogger,
                                     FILE_NAME, tmp_path)
    myLogger.warning("original line")
    assert os.path.exists(fPath)

    # try to move log file, should fail
    newDir = os.path.join(tmp_path, "newDir")
    dlpt.pth.createFolder(newDir)

    with log.ReleaseFileLock(myLogger, fPath):
        # test move and copy operations
        dlpt.pth.copyFile(fPath, newDir, "newFileName.txt")
        newPath = shutil.move(fPath, newDir)
    assert os.path.exists(newPath)

    myLogger.warning("new line after copy")
    assert os.path.exists(fPath)

    with open(fPath, "r") as f:
        # original file, last log call
        lines = f.readlines()
        assert len(lines) == 1
        assert "new line after copy" in lines[0]
    with open(newPath, "r") as f:
        # moved file, first log call
        lines = f.readlines()
        assert len(lines) == 1
        assert "original line" in lines[0]


def test_addRotatingFileHandler(myLogger: logging.Logger, tmp_path):
    ROT_LOG_FILE_SIZE_KB = 50
    ROT_LOG_FILES_COUNT = 2.5  # should create 3 log files
    ROT_LOG_MSG = "write write write, writety write write write"

    assert len(myLogger.handlers) == 0
    hdlr, fPath = log.addRotatingFileHandler(myLogger,
                                             FILE_NAME, tmp_path,
                                             CUSTOM_FMT,
                                             logging.WARNING,
                                             ROT_LOG_FILE_SIZE_KB,
                                             3)
    assert os.path.join(tmp_path, FILE_NAME) == fPath
    assert len(myLogger.handlers) == 1
    assert isinstance(hdlr, logging.handlers.RotatingFileHandler)
    assert os.path.exists(fPath)  # log file path is not delayed

    myLogger.info(LOG_MSG_NOT_LOGGED)
    with open(fPath, "r") as f:
        assert len(f.readlines()) == 0

    myLogger.warning(LOG_MSG_OK)
    with open(fPath, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        _checkFormat(lines[0])

    # check maz size and backup file creation
    sizeBytes = int(ROT_LOG_FILE_SIZE_KB * 1e3)
    logStringSize = len(ROT_LOG_MSG) + 40  # 40 = msg header size
    # primary and two old log files should be present
    numOfWrites = int(sizeBytes / logStringSize * ROT_LOG_FILES_COUNT)
    for _ in range(numOfWrites):
        myLogger.warning(ROT_LOG_MSG)

    logFiles = dlpt.pth.getFilesInFolder(tmp_path)
    assert len(logFiles) == 3

    assert fPath in logFiles
    assert f"{fPath}.1" in logFiles
    assert f"{fPath}.2" in logFiles

    # fPath is current log file, not yet full
    for path in [f"{fPath}.1", f"{fPath}.2"]:
        size = os.path.getsize(path)
        assert size > ((ROT_LOG_FILE_SIZE_KB - 1) * 1e3)
        assert size < ((ROT_LOG_FILE_SIZE_KB + 1) * 1e3)

    fPaths = log.getRotatingLogFilePaths(myLogger)
    assert len(fPaths) == 1
    assert fPaths[0] == fPath


def test_loggingServerProc(myLogger: logging.Logger, tmp_path):
    TIMEOUT_SEC = 3

    myLogger2 = log.createLogger("myLogger2", False)
    myLogger3 = log.createLogger("myLogger3", False)

    fPath = os.path.join(tmp_path, FILE_NAME)
    pid = log.createLoggingServerProc(fPath)
    assert dlpt.proc.alive(pid)

    try:
        endTime = time.time() + TIMEOUT_SEC
        while time.time() < endTime:
            if os.path.exists(fPath):
                break
        else:
            assert False, f"Logger server did not create a file " \
                f"in {TIMEOUT_SEC} sec."

        assert len(myLogger.handlers) == 0
        hdlr = log.addLoggingServerHandler(myLogger,
                                           fmt=CUSTOM_FMT,
                                           level=logging.WARNING)
        assert len(myLogger.handlers) == 1
        assert isinstance(hdlr, log._SocketHandler)
        hdlr2 = log.addLoggingServerHandler(myLogger2,
                                            fmt=CUSTOM_FMT,
                                            level=logging.WARNING)
        assert len(myLogger2.handlers) == 1
        assert isinstance(hdlr2, log._SocketHandler)
        # myLogger3 does not have server logger handler

        myLogger.info(LOG_MSG_NOT_LOGGED)
        myLogger.warning(LOG_MSG_OK)
        myLogger2.info(LOG_MSG_NOT_LOGGED)
        myLogger2.warning(LOG_MSG_OK)
        myLogger3.info(LOG_MSG_NOT_LOGGED)
        myLogger3.warning(LOG_MSG_OK)

        time.sleep(1)

        assert log.loggingServerShutdownRequest(myLogger, pid, 12) is True
        assert dlpt.proc.alive(pid) is False
        with open(fPath, "r") as f:
            lines = f.readlines()
            assert len(lines) == 3, lines  # 2 msg + shutdown msg
            _checkServerFormat(lines[0], myLogger.name)
            _checkServerFormat(lines[1], myLogger2.name)
            assert "shutdown" in lines[2]
    except Exception as err:
        raise
    finally:
        dlpt.proc.killTree(pid, raiseException=False)


def test_getFileName(myLogger: logging.Logger):
    assert log.getFileName(myLogger) == "test_getFileName.log"
    assert log.getFileName(myLogger.name) == "test_getFileName.log"
    assert log.getFileName(myLogger, "asd") == "asd.log"
    assert log.getFileName(myLogger, "asd.txt") == "asd.txt"


def test_getDefaultLogFolderPath():
    assert log.getDefaultLogFolderPath().lower().startswith(os.getcwd().lower())


def test_defaultLogFunctions():
    with pytest.raises(Exception):
        log.debug("debug")  # no default logger set

    nonDefaultLogger = log.createLogger("nonDefaultLogger", False)
    nonDefaultHdlr = log.addConsoleHandler(nonDefaultLogger)
    logger = log.createLogger("test_defaultLogFunctions")
    hdlr = log.addConsoleHandler(logger)

    try:
        with mock.patch.object(logger, "_log") as func:
            with mock.patch.object(nonDefaultLogger, "_log") as func2:
                log.debug("debug")
                log.info("info")
                log.warning("warning")
                log.error("error")
                log.critical("critical")
        assert func.call_count == 5
        assert func2.call_count == 0
    except Exception as err:
        raise
    finally:
        logging.Logger.manager.loggerDict.pop(nonDefaultLogger.name)
        logging.Logger.manager.loggerDict.pop(logger.name)


def _checkFormat(logMsg: str):
    # example: '2021-10-07 19:57:21,438.00438 WARNING: level-OK\n'
    dateStr, timeStr, level, msg = logMsg.strip().split(" ")
    # example: 2021-10-07
    year, month, day = dateStr.split("-")
    assert int(year) == datetime.date.today().year
    assert int(month) == datetime.date.today().month
    assert int(day) == datetime.date.today().day

    # example: 19:38:47,412.00412
    assert timeStr[2] == ":"
    assert timeStr[5] == ":"
    assert timeStr[8] == ","
    assert timeStr[8] == ","
    assert timeStr[12] == "."
    assert len(timeStr) == 18

    # example: WARNING:
    assert level == "WARNING:"

    # example: level OK
    assert msg == LOG_MSG_OK


def _checkServerFormat(logMsg: str, loggerName: str):
    # example: 'test_loggingServerProc 21:34:59.151  WARNING: level-OK\n'
    src, timeStr, _, level, msg = logMsg.strip().split(" ")
    # example: WARNING:
    assert level == "WARNING:"

    # example: test_loggingServerProc
    assert src == loggerName

    # example: 21:34:59.151
    assert timeStr[2] == ":"
    assert timeStr[5] == ":"
    assert timeStr[8] == "."
    assert len(timeStr) == 12

    # example: level OK
    assert msg == LOG_MSG_OK
