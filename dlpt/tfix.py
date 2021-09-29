"""
Test fixtures to be used with pytest for any project.
"""
import os
import pytest

import dlpt
import dlpt.log as log


@pytest.fixture
def dlptCloseLogHandlers():
    """ Close all log handlers at the end of test case."""
    yield

    log.closeLogHandlers()
