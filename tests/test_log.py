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
def my_logger(request) -> Iterator[logging.Logger]:
    logger = log.create_logger(request.node.name)

    yield logger

    try:
        logging.Logger.manager.loggerDict.pop(logger.name)
    except Exception as err:
        pass
    log._defaultLogger = None


def test_create_logger():
    logger = log.create_logger(setAsDefault=False)
    assert logger.name == "root"

    logger = log.create_logger()  # set as default
    try:
        assert logger.name == "root"
        assert log._defaultLogger is not None
        assert log._defaultLogger.name == logger.name

        with pytest.raises(Exception):
            # can't set two loggers as a default
            log.create_logger()
    except Exception as err:
        raise
    finally:
        log._defaultLogger = None


def test_determine_logger(my_logger: logging.Logger):
    assert log._get_logger(my_logger) == my_logger
    assert log._get_logger(my_logger.name) == my_logger
    with pytest.raises(Exception):
        # non-existing default logger
        log._get_logger("qweasdzxcv")

    assert log._determine_logger() == my_logger
    assert log._determine_logger(my_logger) == my_logger
    assert log._determine_logger(my_logger.name) == my_logger

    # set/get default logger
    assert log.get_default_logger() == my_logger
    log.set_default_logger(logging.root)
    assert log.get_default_logger() == logging.root
    log._defaultLogger = None
    with pytest.raises(Exception):
        # no default logger
        log._determine_logger()


def test_add_console_hdlr(my_logger: logging.Logger):
    assert len(my_logger.handlers) == 0
    hdlr = log.add_console_hdlr(my_logger, CUSTOM_FMT, logging.WARNING)
    assert len(my_logger.handlers) == 1
    assert isinstance(hdlr, logging.StreamHandler)

    with mock.patch.object(hdlr.stream, "write") as func:
        my_logger.info(LOG_MSG_NOT_LOGGED)
        func.assert_not_called()

        my_logger.warning(LOG_MSG_OK)
        func.assert_called_once()
        _check_format(func.call_args[0][0])


def test_add_file_hdlr(my_logger: logging.Logger, tmp_path):
    assert len(my_logger.handlers) == 0
    hdlr, fPath = log.add_file_hdlr(my_logger, FILE_NAME, tmp_path, CUSTOM_FMT, logging.WARNING)
    assert os.path.join(tmp_path, FILE_NAME) == fPath
    assert len(my_logger.handlers) == 1
    assert isinstance(hdlr, logging.FileHandler)
    assert os.path.exists(fPath)  # log file path is not delayed

    my_logger.info(LOG_MSG_NOT_LOGGED)
    with open(fPath, "r") as f:
        assert len(f.readlines()) == 0

    my_logger.warning(LOG_MSG_OK)
    with open(fPath, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        _check_format(lines[0])

    fPaths = log.get_log_file_paths(my_logger)
    assert len(fPaths) == 1
    assert fPaths[0] == fPath


def test_add_file_hdlr_log_file(my_logger: logging.Logger, tmp_path):
    hdlr, fPath = log.add_file_hdlr(my_logger, FILE_NAME, tmp_path)
    my_logger.warning("original line")
    assert os.path.exists(fPath)

    # try to move log file, should fail
    newDir = os.path.join(tmp_path, "newDir")
    dlpt.pth.create_dir(newDir)

    with log.ReleaseFileLock(my_logger, fPath):
        # test move and copy operations
        dlpt.pth.copy_file(fPath, newDir, "newFileName.txt")
        newPath = shutil.move(fPath, newDir)
    assert os.path.exists(newPath)

    my_logger.warning("new line after copy")
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


def test_add_rotating_file_hdlr(my_logger: logging.Logger, tmp_path):
    ROT_LOG_FILE_SIZE_KB = 50
    ROT_LOG_FILES_COUNT = 2.5  # should create 3 log files
    ROT_LOG_MSG = "write write write, writety write write write"

    assert len(my_logger.handlers) == 0
    hdlr, fPath = log.add_rotating_file_hdlr(
        my_logger, FILE_NAME, tmp_path, CUSTOM_FMT, logging.WARNING, ROT_LOG_FILE_SIZE_KB, 3
    )
    assert os.path.join(tmp_path, FILE_NAME) == fPath
    assert len(my_logger.handlers) == 1
    assert isinstance(hdlr, logging.handlers.RotatingFileHandler)
    assert os.path.exists(fPath)  # log file path is not delayed

    my_logger.info(LOG_MSG_NOT_LOGGED)
    with open(fPath, "r") as f:
        assert len(f.readlines()) == 0

    my_logger.warning(LOG_MSG_OK)
    with open(fPath, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        _check_format(lines[0])

    # check maz size and backup file creation
    sizeBytes = int(ROT_LOG_FILE_SIZE_KB * 1e3)
    logStringSize = len(ROT_LOG_MSG) + 40  # 40 = msg header size
    # primary and two old log files should be present
    numOfWrites = int(sizeBytes / logStringSize * ROT_LOG_FILES_COUNT)
    for _ in range(numOfWrites):
        my_logger.warning(ROT_LOG_MSG)

    logFiles = dlpt.pth.get_files_in_dir(tmp_path)
    assert len(logFiles) == 3

    assert fPath in logFiles
    assert f"{fPath}.1" in logFiles
    assert f"{fPath}.2" in logFiles

    # fPath is current log file, not yet full
    for path in [f"{fPath}.1", f"{fPath}.2"]:
        size = os.path.getsize(path)
        assert size > ((ROT_LOG_FILE_SIZE_KB - 1) * 1e3)
        assert size < ((ROT_LOG_FILE_SIZE_KB + 1) * 1e3)

    fPaths = log.get_rotating_log_file_paths(my_logger)
    assert len(fPaths) == 1
    assert fPaths[0] == fPath


def test_log_server_proc(my_logger: logging.Logger, tmp_path):
    TIMEOUT_SEC = 3

    my_logger2 = log.create_logger("my_logger2", False)
    my_logger3 = log.create_logger("my_logger3", False)

    fPath = os.path.join(tmp_path, FILE_NAME)
    pid = log.create_log_server_proc(fPath)
    assert dlpt.proc.is_alive(pid)

    with pytest.raises(Exception):
        # does not have logging server handler
        log.log_server_shutdown_request(my_logger, pid)

    try:
        endTime = time.time() + TIMEOUT_SEC
        while time.time() < endTime:
            if os.path.exists(fPath):
                break
        else:
            assert False, f"Logger server did not create a file " f"in {TIMEOUT_SEC} sec."

        assert len(my_logger.handlers) == 0
        hdlr = log.add_logging_server_hdlr(my_logger, fmt=CUSTOM_FMT, level=logging.WARNING)
        assert len(my_logger.handlers) == 1
        assert isinstance(hdlr, log._SocketHandler)
        hdlr2 = log.add_logging_server_hdlr(my_logger2, fmt=CUSTOM_FMT, level=logging.WARNING)
        assert len(my_logger2.handlers) == 1
        assert isinstance(hdlr2, log._SocketHandler)
        # my_logger3 does is_aliveave server logger handler

        my_logger.info(LOG_MSG_NOT_LOGGED)
        my_logger.warning(LOG_MSG_OK)
        my_logger2.info(LOG_MSG_NOT_LOGGED)
        my_logger2.warning(LOG_MSG_OK)
        my_logger3.info(LOG_MSG_NOT_LOGGED)
        my_logger3.warning(LOG_MSG_OK)

        time.sleep(1)

        assert log.log_server_shutdown_request(my_logger, pid, 12) is True
        assert dlpt.proc.is_alive(pid) is False
        with open(fPath, "r") as f:
            lines = f.readlines()
            assert len(lines) == 3, lines  # 2 msg + shutdown msg
            _check_server_format(lines[0], my_logger.name)
            _check_server_format(lines[1], my_logger2.name)
            assert "shutdown" in lines[2]
    except Exception as err:
        raise
    finally:
        dlpt.proc.kill_tree(pid, raiseException=False)


def test_get_file_name(my_logger: logging.Logger):
    assert log.get_file_name(my_logger) == "test_get_file_name.log"
    assert log.get_file_name(my_logger.name) == "test_get_file_name.log"
    assert log.get_file_name(my_logger, "asd") == "asd.log"
    assert log.get_file_name(my_logger, "asd.txt") == "asd.txt"


def get_default_log_dir():
    assert log.get_default_log_dir().lower().startswith(os.getcwd().lower())


def test_default_log_functions():
    with pytest.raises(Exception):
        log.debug("debug")  # no default logger set

    nonDefaultLogger = log.create_logger("nonDefaultLogger", False)
    nonDefaultHdlr = log.add_console_hdlr(nonDefaultLogger)
    logger = log.create_logger("test_default_log_functions")
    hdlr = log.add_console_hdlr(logger)

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


def _check_format(logMsg: str):
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


def _check_server_format(logMsg: str, loggerName: str):
    # example: 'test_log_server_proc 21:34:59.151  WARNING: level-OK\n'
    src, timeStr, _, level, msg = logMsg.strip().split(" ")
    # example: WARNING:
    assert level == "WARNING:"

    # example: test_log_server_proc
    assert src == loggerName

    # example: 21:34:59.151
    assert timeStr[2] == ":"
    assert timeStr[5] == ":"
    assert timeStr[8] == "."
    assert len(timeStr) == 12

    # example: level OK
    assert msg == LOG_MSG_OK
