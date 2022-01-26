import multiprocessing
import sys
import time
from typing import List, Optional


def sleep(sleepTime: float):
    time.sleep(sleepTime)


def sleep_with_exit_code(sleepTime: float, sysExitCode: int):
    sleep(sleepTime)

    if sysExitCode:
        sys.exit(sysExitCode)


def sleep_with_return_code(sleepTime: float, returnCode: int):
    sleep(sleepTime)

    if returnCode:
        return returnCode


def multiprocess_child(sleepTime: float):
    """
    This function is spawned by multiprocess_parent() and does nothing except wait.
    """
    time.sleep(sleepTime)


def multiprocess_parent(childNum: int, sleepTime: float = 3):
    """
    This function spawns other child processes multiprocess_child() -
    needed for PID and process control test functions.
    """
    childs = []
    # spawn child processes
    for child in range(childNum):
        proc = multiprocessing.Process(target=multiprocess_child, args=(sleepTime,))
        childs.append(proc)
        proc.start()

    # wait for spawned processes to finish
    for child in childs:
        child.join()

    time.sleep(1)


def get_test_proc_args(sleepTimeSec: Optional[float] = 10) -> List[str]:
    """Return command line string necessary to spawn this file as a subprocess
    (and execute __main__).

    Args:
        sleepTimeSec: set the time spawned process should sleep.

    Returns:
        Command line arguments (list of strings) to spawn this file __main__.

    """
    args = [sys.executable, __file__, str(sleepTimeSec)]

    return args


if __name__ == "__main__":
    if len(sys.argv) == 2:
        sleepTime = float(sys.argv[1])
    else:
        sleepTime = 10
    sleep(sleepTime)

    sys.exit(0)
