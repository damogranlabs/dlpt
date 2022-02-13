import datetime
import logging
import logging.handlers
import os
import shutil
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
    log._default_logger = None


def test_create_logger():
    logger = log.create_logger(set_as_default=False)
    assert logger.name == "root"

    logger = log.create_logger()  # set as default
    try:
        assert logger.name == "root"
        assert log._default_logger is not None
        assert log._default_logger.name == logger.name

        with pytest.raises(Exception):
            # can't set two loggers as a default
            log.create_logger()
    except Exception as err:
        raise
    finally:
        log._default_logger = None


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
    log._default_logger = None
    with pytest.raises(Exception):
        # no default logger
        log._determine_logger()


def test_add_console_hdlr(my_logger: logging.Logger):
    assert len(my_logger.handlers) == 0
    hdlr = log.add_console_hdlr(my_logger, CUSTOM_FMT, logging.WARNING)
    assert len(my_logger.handlers) == 1
    assert isinstance(hdlr, logging.StreamHandler)

    with mock.patch.object(hdlr, "handle") as func:
        my_logger.info(LOG_MSG_NOT_LOGGED)
        func.assert_not_called()

        my_logger.warning(LOG_MSG_OK)
        func.assert_called_once()
        _check_format(hdlr.formatter.format(func.call_args[0][0]))


def test_add_file_hdlr(my_logger: logging.Logger, tmp_path):
    assert len(my_logger.handlers) == 0
    hdlr, file_path = log.add_file_hdlr(my_logger, FILE_NAME, tmp_path, CUSTOM_FMT, logging.WARNING)
    assert os.path.join(tmp_path, FILE_NAME) == file_path
    assert len(my_logger.handlers) == 1
    assert isinstance(hdlr, logging.FileHandler)
    assert os.path.exists(file_path)  # log file path is not delayed

    my_logger.info(LOG_MSG_NOT_LOGGED)
    with open(file_path, "r") as f:
        assert len(f.readlines()) == 0

    my_logger.warning(LOG_MSG_OK)
    with open(file_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        _check_format(lines[0])

    file_paths = log.get_log_file_paths(my_logger)
    assert len(file_paths) == 1
    assert file_paths[0] == file_path


def test_add_file_hdlr_log_file(my_logger: logging.Logger, tmp_path):
    hdlr, file_path = log.add_file_hdlr(my_logger, FILE_NAME, tmp_path)
    my_logger.warning("original line")
    assert os.path.exists(file_path)

    # try to move log file, should fail
    new_dir = os.path.join(tmp_path, "newDir")
    dlpt.pth.create_dir(new_dir)

    with log.ReleaseFileLock(my_logger, file_path):
        # test move and copy operations
        dlpt.pth.copy_file(file_path, new_dir, "newFileName.txt")
        new_path = shutil.move(file_path, new_dir)
    assert os.path.exists(new_path)

    my_logger.warning("new line after copy")
    assert os.path.exists(file_path)

    with open(file_path, "r") as f:
        # original file, last log call
        lines = f.readlines()
        assert len(lines) == 1
        assert "new line after copy" in lines[0]
    with open(new_path, "r") as f:
        # moved file, first log call
        lines = f.readlines()
        assert len(lines) == 1
        assert "original line" in lines[0]


def test_add_rotating_file_hdlr(my_logger: logging.Logger, tmp_path):
    ROT_LOG_FILE_SIZE_KB = 50
    ROT_LOG_FILES_COUNT = 2.5  # should create 3 log files
    ROT_LOG_MSG = "write write write, writety write write write"

    assert len(my_logger.handlers) == 0
    hdlr, file_path = log.add_rotating_file_hdlr(
        my_logger, FILE_NAME, tmp_path, CUSTOM_FMT, logging.WARNING, ROT_LOG_FILE_SIZE_KB, 3
    )
    assert os.path.join(tmp_path, FILE_NAME) == file_path
    assert len(my_logger.handlers) == 1
    assert isinstance(hdlr, logging.handlers.RotatingFileHandler)
    assert os.path.exists(file_path)  # log file path is not delayed

    my_logger.info(LOG_MSG_NOT_LOGGED)
    with open(file_path, "r") as f:
        assert len(f.readlines()) == 0

    my_logger.warning(LOG_MSG_OK)
    with open(file_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        _check_format(lines[0])

    # check maz size and backup file creation
    size_bytes = int(ROT_LOG_FILE_SIZE_KB * 1e3)
    log_str_size = len(ROT_LOG_MSG) + 40  # 40 = msg header size
    # primary and two old log files should be present
    num_of_writes = int(size_bytes / log_str_size * ROT_LOG_FILES_COUNT)
    for _ in range(num_of_writes):
        my_logger.warning(ROT_LOG_MSG)

    log_files = dlpt.pth.get_files_in_dir(tmp_path)
    assert len(log_files) == 3

    assert file_path in log_files
    assert f"{file_path}.1" in log_files
    assert f"{file_path}.2" in log_files

    # file_path is current log file, not yet full
    for path in [f"{file_path}.1", f"{file_path}.2"]:
        size = os.path.getsize(path)
        assert size > ((ROT_LOG_FILE_SIZE_KB - 1) * 1e3)
        assert size < ((ROT_LOG_FILE_SIZE_KB + 1) * 1e3)

    file_paths = log.get_rotating_log_file_paths(my_logger)
    assert len(file_paths) == 1
    assert file_paths[0] == file_path


def test_log_server_proc(my_logger: logging.Logger, tmp_path):
    TIMEOUT_SEC = 3
    NUM_OF_TEST_PORTS = 10

    start_port = dlpt.log.DEFAULT_SERVER_SOCKET_PORT
    end_port = start_port + NUM_OF_TEST_PORTS
    for port in range(start_port, end_port):
        if dlpt.log._is_port_free(port):
            break
    else:
        pytest.fail(f"Unable to find free port to test logger socket server (range: {start_port} - {end_port})")
        return  # IDE does not understand `NoReturn`?

    my_logger2 = log.create_logger("my_logger2", False)
    my_logger3 = log.create_logger("my_logger3", False)

    try:
        file_path = os.path.join(tmp_path, FILE_NAME)
        pid = log.create_log_server_proc(file_path, port)
        assert dlpt.proc.is_alive(pid)

        with pytest.raises(Exception):
            # does not have logging server handler
            log.log_server_shutdown_request(my_logger, pid)

        try:
            end_time = time.time() + TIMEOUT_SEC
            while time.time() < end_time:
                if os.path.exists(file_path):
                    break
            else:
                pytest.fail(f"Logger server did not create a file in {TIMEOUT_SEC} sec.")

            assert len(my_logger.handlers) == 0
            log.add_console_hdlr(my_logger, fmt=CUSTOM_FMT, level=logging.DEBUG)
            hdlr = log.add_logging_server_hdlr(my_logger, fmt=CUSTOM_FMT, level=logging.WARNING)
            assert len(my_logger.handlers) == 2
            assert isinstance(hdlr, log._SocketHandler)
            hdlr2 = log.add_logging_server_hdlr(my_logger2, fmt=CUSTOM_FMT, level=logging.WARNING)
            log.add_console_hdlr(my_logger2, fmt=CUSTOM_FMT, level=logging.DEBUG)
            assert len(my_logger2.handlers) == 2
            assert isinstance(hdlr2, log._SocketHandler)
            log.add_console_hdlr(my_logger3, fmt=CUSTOM_FMT, level=logging.DEBUG)
            # my_logger3 does not add socket server logger handler
            assert len(my_logger3.handlers) == 1

            my_logger.info(LOG_MSG_NOT_LOGGED)
            my_logger.warning(LOG_MSG_OK)
            my_logger2.info(LOG_MSG_NOT_LOGGED)
            my_logger2.warning(LOG_MSG_OK)
            my_logger3.info(LOG_MSG_NOT_LOGGED)
            my_logger3.warning(LOG_MSG_OK)

            # wait some time until log records are propagated through socket
            time.sleep(1)
            assert log.log_server_shutdown_request(my_logger, pid) is True
            assert dlpt.proc.is_alive(pid) is False

            # wait some time until log content is really flushed to the file
            time.sleep(1)
            with open(file_path, "r") as f:
                lines = f.readlines()
                assert len(lines) == 3, lines  # 2 msg + shutdown msg
                _check_server_format(lines[0], my_logger.name)
                _check_server_format(lines[1], my_logger2.name)
                assert "shutdown" in lines[2]
        except Exception as err:
            raise
        finally:
            dlpt.proc.kill_tree(pid, raise_exception=False)
    finally:
        logging.Logger.manager.loggerDict.pop(my_logger2.name)
        logging.Logger.manager.loggerDict.pop(my_logger3.name)


def test_get_file_name(my_logger: logging.Logger):
    assert log.get_file_name(my_logger) == "test_get_file_name.log"
    assert log.get_file_name(my_logger.name) == "test_get_file_name.log"
    assert log.get_file_name(my_logger, "asd") == "asd.log"
    assert log.get_file_name(my_logger, "asd.txt") == "asd.txt"


def test_get_default_log_dir():
    assert log.get_default_log_dir().lower().startswith(os.getcwd().lower())


def test_default_log_functions():
    with pytest.raises(Exception):
        log.debug("debug")  # no default logger set

    non_default_logger = log.create_logger("nonDefaultLogger", False)
    non_default_hdlr = log.add_console_hdlr(non_default_logger)
    logger = log.create_logger("test_default_log_functions")
    hdlr = log.add_console_hdlr(logger)

    try:
        with mock.patch.object(logger, "_log") as func:
            with mock.patch.object(non_default_logger, "_log") as func2:
                log.debug("debug")
                log.info("info")
                log.warning("warning")
                log.error("error")
                log.error_with_traceback("error, no traceback (no exception)")
                log.critical("critical")
        assert func.call_count == 6
        assert func2.call_count == 0
    except Exception as err:
        raise
    finally:
        logging.Logger.manager.loggerDict.pop(non_default_logger.name)
        logging.Logger.manager.loggerDict.pop(logger.name)
        log._default_logger = None


def test_log_with_traceback(my_logger: logging.Logger):
    assert len(my_logger.handlers) == 0
    hdlr = log.add_console_hdlr(my_logger, CUSTOM_FMT, logging.WARNING)

    with mock.patch.object(log, "warning") as warn_func:
        with mock.patch.object(log, "error") as err_func:
            with mock.patch.object(log, "critical") as crit_func:
                log.warning_with_traceback("No error", my_logger)
                log.error_with_traceback("No error", my_logger)
                log.critical_with_traceback("No error", my_logger)

                assert "exc_info" not in str(warn_func.call_args)
                assert "exc_info" not in str(err_func.call_args)
                assert "exc_info" not in str(crit_func.call_args)

                try:
                    raise ValueError("just some error.")
                except Exception as err:
                    log.warning_with_traceback("Intended error", my_logger)
                    log.error_with_traceback("Intended error", my_logger)
                    log.critical_with_traceback("Intended error", my_logger)
                assert "exc_info" in str(warn_func.call_args)
                assert "exc_info" in str(err_func.call_args)
                assert "exc_info" in str(crit_func.call_args)


def _check_format(log_msg: str):
    # example: '2021-10-07 19:57:21,438.00438 WARNING: level-OK\n'
    dateStr, time_str, level, msg = log_msg.strip().split(" ")
    # example: 2021-10-07
    year, month, day = dateStr.split("-")
    assert int(year) == datetime.date.today().year
    assert int(month) == datetime.date.today().month
    assert int(day) == datetime.date.today().day

    # example: 19:38:47,412.00412
    assert time_str[2] == ":"
    assert time_str[5] == ":"
    assert time_str[8] == ","
    assert time_str[8] == ","
    assert time_str[12] == "."
    assert len(time_str) == 18

    # example: WARNING:
    assert level == "WARNING:"

    # example: level OK
    assert msg == LOG_MSG_OK


def _check_server_format(log_msg: str, logger_name: str):
    # example: 'test_log_server_proc 21:34:59.151  WARNING: level-OK\n'
    src, time_str, _, level, msg = log_msg.strip().split(" ")
    # example: WARNING:
    assert level == "WARNING:", log_msg

    # example: test_log_server_proc
    assert src == logger_name, log_msg

    # example: 21:34:59.151
    assert time_str[2] == ":", log_msg
    assert time_str[5] == ":", log_msg
    assert time_str[8] == ".", log_msg
    assert len(time_str) == 12, log_msg

    # example: level OK
    assert msg == LOG_MSG_OK, log_msg
