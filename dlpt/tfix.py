"""
Test fixtures to be used with pytest for any project.
"""
import os
from typing import Iterator, Tuple

import pytest

import dlpt
import dlpt.log as log


@pytest.fixture
def dlptCloseLogHandlers():
    """ Close all log handlers at the end of test case."""
    yield

    log.closeAllLoggers()


@pytest.fixture
def dlptConsoleLogger(request) -> Iterator[log.LogHandler]:
    """ Create default log handler with added console handler and pass it to test func.
    Name of created logger is the same as current test case function.
    Close all logs at the end.
    """
    logger = log.LogHandler(request.node.name)
    logger.addConsoleHandler()

    yield logger

    log.closeAllLoggers()


@pytest.fixture
def dlptKillTestSubprocs():
    """ Kill only test-spawned child processes. """
    processesBeforeTest = dlpt.proc.getChilds(os.getpid())

    yield

    # since socket server process might lock this files, kill any of test subprocess
    processesAfterTest = dlpt.proc.getChilds(os.getpid())
    pidsToKill = dlpt.utils.getListDifference(processesBeforeTest, processesAfterTest)
    dlpt.proc.killTreeMultiple(pidsToKill)
