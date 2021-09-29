import multiprocessing
import time
from typing import Iterable

import pytest

import dlpt

from dlpt.tfix import *
from tests import helpers


@pytest.fixture
def spawnSubprocess() -> Iterable[int]:
    proc = multiprocessing.Process(target=helpers.sleep, args=(10,))
    proc.start()

    assert proc.pid is not None
    yield proc.pid

    dlpt.proc.kill(proc.pid)


@pytest.fixture
def spawnSubprocessWithChilds() -> Iterable[int]:
    proc = multiprocessing.Process(
        target=helpers.mpParent, args=(1, 10))  # 1 child wit 10 seconds sleep
    proc.start()

    assert proc.pid is not None
    yield proc.pid

    dlpt.proc.killTree(proc.pid)


def test_basic():
    with pytest.raises(ValueError):
        dlpt.wdg.Watchdog(os.getpid(), -100)

    wdg = dlpt.wdg.Watchdog(os.getpid(), 100)
    assert wdg.getTimeoutMin() == 1
    assert wdg.getTimeoutSec() == 100


def test_wdgDoesNotKillProcess(spawnSubprocess):
    # watchdog does not have to kill user PID
    timeoutSec = 3
    wdg = dlpt.wdg.Watchdog(spawnSubprocess, timeoutSec)

    wdg.start()
    time.sleep(1)
    assert wdg.isWdgAlive() is True
    assert wdg.isMyPidAlive() is True

    # TestProc and watchdog are alive - OK! Kill user pid, leave watchdog alive
    dlpt.proc.kill(spawnSubprocess)
    assert wdg.isWdgAlive() is True
    assert wdg.isMyPidAlive() is False
    assert wdg.isKilledByWdg() is False

    # OK: TestProc is not alive, watchdog is still alive! Kill watchdog
    wdg.stop()
    assert wdg.isWdgAlive() is False


def test_wdgKillsProcess(spawnSubprocess):
    # watchdog must kill user PID
    timeoutSec = 1
    wdg = dlpt.wdg.Watchdog(spawnSubprocess, timeoutSec)
    wdg.start()
    time.sleep(3)

    assert wdg.isWdgAlive() is False
    assert wdg.isMyPidAlive() is False
    assert wdg.isKilledByWdg() is True
