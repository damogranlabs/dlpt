import os
import sys
import subprocess
import multiprocessing
import time
from typing import Union

import pytest

import dlpt

from dlpt.tfix import *
from tests import helpers

currentPid = os.getpid()
# print("currentPid", currentPid)
# print(f"This process child PIDs: {dlpt.proc.getChildProcesses(currentPid)}")  # for debugging purposes.


def _waitForChildProcesses(parentPid: Union[None, str, int], numOfChilds: int, timeoutSec: float):
    assert parentPid is not None
    endTime = time.time() + timeoutSec
    childs = []
    while time.time() < endTime:
        childs = dlpt.proc.getChilds(parentPid)
        if len(childs) == numOfChilds:
            return

    assert False, f"During timeout ({timeoutSec} sec) {len(childs)} child processes are available" \
        f" but expecting {numOfChilds}"


def test_getProcData():
    assert "python" in dlpt.proc.getName(currentPid)

    assert "python" in dlpt.proc.getExecutable(currentPid)

    assert dlpt.proc.getCmdArgs(currentPid) != []


@pytest.mark.usefixtures("dlptKillTestSubprocs")
def test_spawnSetting():
    # spawn a valid subprocess
    args: dlpt.proc.T_PROC_ARGS = [sys.executable, "-c", "\"import sys; sys.exit(0)\""]
    proc = dlpt.proc.spawnSubproc(args)
    assert proc.returncode == 0

    # spawn subprocess with non-zero return code, but don't check its return code
    args = [sys.executable, "-c", "\"import sys; sys.exit(1)\""]
    proc = dlpt.proc.spawnSubproc(args, checkReturnCode=False)
    assert proc.returncode == 1

    # spawn subprocess with non-zero return code, check its return code and string representation
    with pytest.raises(dlpt.proc.SubprocError) as err:
        dlpt.proc.spawnSubproc(args)
    assert "Spawned subprocess throw 'subprocess.CalledProcessError'" in str(err.value)

    # spawn subprocess with non-zero return code, do not check its return code
    args = [sys.executable, "-c", "\"invalidCommand = invalid command\""]
    proc = dlpt.proc.spawnSubproc(args, checkReturnCode=False)
    assert proc.returncode == 1
    assert "invalid command" in proc.stderr

    # spawn a subprocess with invalid command
    args = ["whateva"]
    with pytest.raises(Exception):
        dlpt.proc.spawnSubproc(args)

    # what if argument is a list of one string, which already combines all cmd args
    argsStr = f"{sys.executable} {os.path.join(os.path.dirname(__file__), 'helpers.py')}"
    with pytest.raises(Exception):
        proc = dlpt.proc.spawnSubproc(argsStr)
    args = [argsStr]
    proc = dlpt.proc.spawnSubproc(args)


@pytest.mark.usefixtures("dlptKillTestSubprocs")
def test_spawnWithRunArgs():
    """
    Spawn a subprocess with extra key-worded run() args.
    """
    args = [sys.executable, "-c", "\"import sys; import os; print(list(os.environ)); sys.exit(0)\""]
    proc = dlpt.proc.spawnSubprocWithRunArgs(args, stdout=subprocess.PIPE, encoding='utf-8')
    assert proc.returncode == 0
    defaultEnv = proc.stdout

    envVars = {**os.environ, 'TEST_SPAWNWITHRUNARGS': 'testing_keyworded_proc_args'}
    proc = dlpt.proc.spawnSubprocWithRunArgs(args, stdout=subprocess.PIPE, encoding='utf-8', env=envVars)
    assert proc.returncode == 0
    newEnv = proc.stdout

    assert newEnv != defaultEnv
    assert "TEST_SPAWNWITHRUNARGS" not in defaultEnv
    assert "TEST_SPAWNWITHRUNARGS" in newEnv

    with pytest.raises(Exception):
        dlpt.proc.spawnSubprocWithRunArgs(["čšž"])


@pytest.mark.usefixtures("dlptKillTestSubprocs")
def test_spawnAndKillProcess():
    """
    Spawn one parent subprocess, which spawns another NUMBER_OF_CHILD_PROCESSES child processes. 
    Manipulate child processes and check states.
    """
    NUMBER_OF_CHILD_PROCESSES = 3

    with pytest.raises(ValueError):
        dlpt.proc.exist(None)

    # spawn and manually kill parent (parent proc tree)
    proc = multiprocessing.Process(target=helpers.mpParent, args=(NUMBER_OF_CHILD_PROCESSES, ))
    proc.start()
    assert proc.pid is not None
    assert dlpt.proc.exist(proc.pid) is True
    time.sleep(0.5)
    assert dlpt.proc.exist(proc.pid) is True
    dlpt.proc.killTree(proc.pid)
    assert dlpt.proc.exist(proc.pid) is False
    proc.join(2)

    # controlled killing of child processes
    proc = multiprocessing.Process(target=helpers.mpParent, args=(NUMBER_OF_CHILD_PROCESSES, ))
    proc.start()
    assert proc.pid is not None
    assert dlpt.proc.exist(proc.pid) is True
    _waitForChildProcesses(proc.pid, NUMBER_OF_CHILD_PROCESSES, 1.5)
    killedChilds = dlpt.proc.killChilds(proc.pid)
    assert dlpt.proc.exist(proc.pid) is True
    assert len(killedChilds) == NUMBER_OF_CHILD_PROCESSES
    proc.join(2)

    # spawn multiple parents with multiple child processes, kill all
    proc1 = multiprocessing.Process(target=helpers.mpParent, args=(NUMBER_OF_CHILD_PROCESSES, ))
    proc2 = multiprocessing.Process(target=helpers.mpParent, args=(NUMBER_OF_CHILD_PROCESSES, ))
    proc1.start()
    proc2.start()
    assert proc1.pid is not None
    assert proc2.pid is not None
    _waitForChildProcesses(proc1.pid, NUMBER_OF_CHILD_PROCESSES, 1.2)
    _waitForChildProcesses(proc2.pid, NUMBER_OF_CHILD_PROCESSES, 1.2)
    killedPids = dlpt.proc.killTreeMultiple([proc1.pid, proc2.pid])
    assert len(killedPids) == (2 + 2 * NUMBER_OF_CHILD_PROCESSES)

    assert dlpt.proc.kill(123456789) is True


def test_getAlive():
    alivePids = dlpt.proc.getAlive()
    assert len(alivePids) > 1  # obviously

    pyPids = dlpt.proc.getAlive("python")
    assert currentPid in pyPids


@pytest.mark.usefixtures("dlptKillTestSubprocs")
def test_nonBlockingProcess():
    cmdStr = helpers.getTestProcArgs()
    with pytest.raises(Exception) as err:
        dlpt.proc.spawnNonBlockingSubproc(["qweasdzxc"])

    procPid = dlpt.proc.spawnNonBlockingSubproc([cmdStr])
    assert dlpt.proc.exist(procPid) is True
    dlpt.proc.kill(procPid)


@pytest.mark.usefixtures("dlptKillTestSubprocs")
def test_shellCommand():
    args = ["ping", "www.google.com", "-n 1", "-w 1000"]
    proc = dlpt.proc.spawnSubproc(args)
    assert proc.returncode == 0


@pytest.mark.usefixtures("dlptKillTestSubprocs")
def test_timeout():
    args = ["ping", "127.255.255.255"]
    startTime = time.time()

    with pytest.raises(dlpt.proc.SubprocTimeoutError) as err:
        dlpt.proc.spawnSubproc(args, timeoutSec=0.2)
    durationSec = time.time() - startTime
    assert 0.15 < durationSec < 0.25
    assert "Spawned subprocess throw 'subprocess.TimeoutExpired'" in str(err.value)  # ... and string representation

    args = ["ping", "127.255.255.255"]
    startTime = time.time()
    with pytest.raises(dlpt.proc.SubprocTimeoutError):
        dlpt.proc.spawnSubproc(args, timeoutSec=2)
    durationSec = time.time() - startTime
    assert 1.5 < durationSec < 2.5

    args = [sys.executable, "-c", "\"import time; import sys; sys.stderr.write('errDesc'); time.sleep(3)\""]
    startTime = time.time()
    with pytest.raises(dlpt.proc.SubprocTimeoutError) as err:
        dlpt.proc.spawnSubproc(args, timeoutSec=2)
    durationSec = time.time() - startTime
    assert 1.75 < durationSec < 2.25
    assert "Stderr: errDesc" in str(err.value)  # ... and string representation
