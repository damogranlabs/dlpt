"""
Test fixtures to be used with pytest for any project.
"""
import os
import uuid
import pathlib
import tempfile
from typing import Iterator, Tuple

import pytest

import dlpt
import dlpt.log as log


@pytest.fixture
def closeAllLogHandlers():
    """ Close all log handlers at the end of test case."""
    yield

    log.closeAllLoggers()


@pytest.fixture
def consoleLogger(request) -> Iterator[log.LogHandler]:
    """ Create default log handler with added console handler and pass it to test func.
    Name of created logger is the same as current test case function.
    Close all logs at the end.
    """
    logger = log.LogHandler(request.node.name)
    logger.addConsoleHandler()

    yield logger

    log.closeAllLoggers()


@pytest.fixture
def consoleFileLogger(request, tmp_path) -> Iterator[Tuple[log.LogHandler, str]]:
    """ Create a default log.LogHandler and add console and file handlers. 
    Return a tuple: (<log handler>, <log file path>)
    Name of created logger is the same as current test case function.
    Close all logs at the end.
    """
    folderPath = str(tmp_path)

    logger = log.LogHandler(request.node.name)
    logger.addConsoleHandler()
    filePath = logger.addFileHandler(request.node.name, folderPath)

    yield logger, filePath

    log.closeAllLoggers()
    dlpt.pth.removeFolderTree(folderPath)


@pytest.fixture
def killChildProcesses():
    """ Kill only test-spawned child processes. """
    processesBeforeTest = dlpt.proc.getChilds(os.getpid())

    yield

    # since socket server process might lock this files, kill any of test subprocess
    processesAfterTest = dlpt.proc.getChilds(os.getpid())
    pidsToKill = dlpt.utils.getListDifference(processesBeforeTest, processesAfterTest)
    dlpt.proc.killTreeMultiple(pidsToKill)
