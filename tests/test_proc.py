from unittest import mock
import os
import subprocess
import multiprocessing
import time
from typing import List

import pytest

import dlpt

from dlpt.tfix import *
from tests import helpers

thisPid = os.getpid()


def _waitForChildProcs(parentPid: int,
                       numOfChilds: int,
                       timeoutSec: float) -> List[int]:
    endTime = time.time() + timeoutSec
    childs = []
    while time.time() < endTime:
        childs = dlpt.proc.getChilds(parentPid)
        if len(childs) == numOfChilds:
            return childs

    assert False, f"During timeout ({timeoutSec} sec) {len(childs)} child " \
        f" processes are available but expecting {numOfChilds}"


def test_getName():
    name = dlpt.proc.getName(thisPid)
    assert ("python" in name) or ("pytest" in name)


def test_getExecutable():
    exeName = dlpt.proc.getExecutable(thisPid)
    assert ("python" in exeName) or ("pytest" in exeName)


def test_getCmdArgs():
    args = dlpt.proc.getCmdArgs(thisPid)
    assert len(args) > 1


def test_exist():
    assert dlpt.proc.exist(thisPid) is True
    assert dlpt.proc.exist(123456) is False

    with pytest.raises(ValueError):
        dlpt.proc.exist(None)


def test_getChilds():
    NUM_OF_CHILD_PROCS = 3
    TIMEOUT_SEC = 3

    # spawn parent process, which will spawn 3 subprocesses (childs)
    proc = multiprocessing.Process(target=helpers.mpParent,
                                   args=(NUM_OF_CHILD_PROCS, ))
    proc.start()
    assert proc.pid is not None

    endTime = time.time() + TIMEOUT_SEC
    childs = []
    while time.time() < endTime:
        childs = dlpt.proc.getChilds(proc.pid)
        if len(childs) == NUM_OF_CHILD_PROCS:
            return  # success

    assert False, f"During timeout ({TIMEOUT_SEC} sec) {len(childs)} " \
        f"child processes are available but expecting {NUM_OF_CHILD_PROCS}."


def test_kill():
    TIMEOUT_SEC = 3
    proc = multiprocessing.Process(target=helpers.sleep,
                                   args=(TIMEOUT_SEC, ))
    proc.start()
    assert proc.pid is not None
    assert dlpt.proc.kill(proc.pid) is True
    assert proc.is_alive() is False

    with mock.patch("dlpt.proc.exist") as existFunc:
        existFunc.return_value = False
        assert dlpt.proc.kill(123) is True


def test_killChilds():
    NUM_OF_CHILD_PROCS = 3
    TIMEOUT_SEC = 3
    # spawn parent process, which will spawn 3 subprocesses (childs)
    proc = multiprocessing.Process(target=helpers.mpParent,
                                   args=(NUM_OF_CHILD_PROCS, ))
    proc.start()
    assert proc.pid is not None
    childs = _waitForChildProcs(proc.pid, NUM_OF_CHILD_PROCS, TIMEOUT_SEC)

    with mock.patch("dlpt.proc.kill") as killFunc:
        killedChilds = dlpt.proc.killChilds(proc.pid)
        assert dlpt.utils.areListValuesEqual(childs, killedChilds)
        assert killFunc.call_count == NUM_OF_CHILD_PROCS


def test_killTree():
    NUM_OF_CHILD_PROCS = 3
    TIMEOUT_SEC = 3
    # spawn parent process, which will spawn 3 subprocesses (childs)
    proc = multiprocessing.Process(target=helpers.mpParent,
                                   args=(NUM_OF_CHILD_PROCS, ))
    proc.start()
    assert proc.pid is not None
    childs = _waitForChildProcs(proc.pid, NUM_OF_CHILD_PROCS, TIMEOUT_SEC)

    with mock.patch("dlpt.proc.kill") as killFunc:
        killedPids = dlpt.proc.killTree(proc.pid)
        assert dlpt.utils.areListValuesEqual(childs + [proc.pid], killedPids)
        assert killFunc.call_count == NUM_OF_CHILD_PROCS + 1  # childs + parent


def test_killTreeMultiple():
    with mock.patch("dlpt.proc.killTree") as killTreeFunc:
        killedPids = dlpt.proc.killTreeMultiple([1, 2, 3, 4])
        assert killTreeFunc.call_args_list == [
            mock.call(1, True),
            mock.call(2, True),
            mock.call(3, True),
            mock.call(4, True)
        ]


def test_getAlive():
    pyPids = dlpt.proc.getAlive(dlpt.proc.getName(thisPid))
    assert thisPid in pyPids


def test_spawnNonBlockingSubproc():
    # invalid args, subprocess throws exception
    with pytest.raises(Exception) as err:
        dlpt.proc.spawnNonBlockingSubproc(["qweasdzxc"])

    cmdStr = helpers.getTestProcArgs()
    procPid = dlpt.proc.spawnNonBlockingSubproc([cmdStr])
    assert dlpt.proc.exist(procPid) is True
    dlpt.proc.kill(procPid)


def test_spawnSubproc():
    with mock.patch("dlpt.proc.spawnSubprocWithRunArgs") as spawnFunc:
        dlpt.proc.spawnSubproc(["asd"])
        spawnFunc.assert_called_once()
        spawnFunc.call_args[0][0] == ["asd"]


def test_spawnSubprocWithRunArgs():
    # spawn a valid subprocess
    args = ["python", "-c", "\"import sys; sys.exit(0)\""]
    proc = dlpt.proc.spawnSubproc(args)
    assert proc.returncode == 0

    # spawn subprocess with non-zero return code,
    # but don't check its return code
    args = ["python", "-c", "\"import sys; sys.exit(1)\""]
    proc = dlpt.proc.spawnSubproc(args, checkReturnCode=False)
    assert proc.returncode == 1

    # spawn subprocess with non-zero return code,
    # check its return code and string representation
    with pytest.raises(dlpt.proc.SubprocError) as err:
        dlpt.proc.spawnSubproc(args)
    assert "throw 'subprocess.CalledProcessError'" in str(err.value)

    # spawn subprocess with non-zero return code, do not check its return code
    args = ["python", "-c", "\"invalidCommand = invalid command\""]
    proc = dlpt.proc.spawnSubproc(args, checkReturnCode=False)
    assert proc.returncode == 1
    assert "invalid command" in proc.stderr

    # spawn a subprocess with invalid command
    args = ["whateva"]
    with pytest.raises(Exception):
        dlpt.proc.spawnSubproc(args)


def test_spawnSubprocWithRunArgs_timeout():
    actionStr = "\"import time; import sys; "
    actionStr += "sys.stderr.write('errDesc'); "
    actionStr += "time.sleep(3)\""
    args = ["python", "-c", actionStr]

    startTime = time.time()
    with pytest.raises(dlpt.proc.SubprocTimeoutError) as err:
        dlpt.proc.spawnSubproc(args, timeoutSec=0.3)
    durationSec = time.time() - startTime
    assert 0.25 < durationSec < 0.35
    assert "throw 'subprocess.TimeoutExpired'" in str(err.value)
    assert "Stderr: errDesc" in str(err.value)


def test_spawnSubprocWithRunArgs_cusomArgs():
    """
    Spawn a subprocess with extra key-worded run() args.
    """
    args = ["python",
            "-c",
            "\"import os; import sys; print(list(os.environ));\""]

    # get default env vars
    proc = dlpt.proc.spawnSubprocWithRunArgs(args,
                                             stdout=subprocess.PIPE,
                                             encoding='utf-8')
    assert proc.returncode == 0
    defaultEnv = proc.stdout

    # get subproc env vars
    envVars = {**os.environ, 'TEST_SPAWNWITHRUNARGS': 'keyworded_proc_args'}
    proc = dlpt.proc.spawnSubprocWithRunArgs(args,
                                             stdout=subprocess.PIPE,
                                             encoding='utf-8',
                                             env=envVars)
    assert proc.returncode == 0
    newEnv = proc.stdout

    # compare
    assert newEnv != defaultEnv
    assert "TEST_SPAWNWITHRUNARGS" not in defaultEnv
    assert "TEST_SPAWNWITHRUNARGS" in newEnv


def test_spawnSubprocWithRunArgs_shellCommand():
    args = ["ping", "www.google.com", "-n 1", "-w 1000"]
    proc = dlpt.proc.spawnSubproc(args)
    assert proc.returncode == 0


def test_checkIfArgIsList():
    ARGS_LIST = ["a", "s", "d", 1, 2, 3]
    ARGS_STR = "a s d 1 2 3"

    dlpt.proc._checkIfArgIsList(ARGS_LIST)
    with pytest.raises(Exception):
        dlpt.proc._checkIfArgIsList(ARGS_STR)

    assert dlpt.proc.getCmdString(ARGS_LIST) == ARGS_STR
