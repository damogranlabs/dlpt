import multiprocessing
import sys
import time
from typing import List, Optional


def sleep(sleep_time: float):
    time.sleep(sleep_time)


def sleep_with_exit_code(sleep_time: float, sys_exit_code: int):
    sleep(sleep_time)

    if sys_exit_code:
        sys.exit(sys_exit_code)


def sleep_with_return_code(sleep_time: float, return_code: int):
    sleep(sleep_time)

    if return_code:
        return return_code


def multiprocess_child(sleep_time: float):
    """
    This function is spawned by multiprocess_parent() and does nothing except wait.
    """
    time.sleep(sleep_time)


def multiprocess_parent(child_num: int, sleep_time: float = 3):
    """
    This function spawns other child processes multiprocess_child() -
    needed for PID and process control test functions.
    """
    childs = []
    # spawn child processes
    for child in range(child_num):
        proc = multiprocessing.Process(target=multiprocess_child, args=(sleep_time,))
        childs.append(proc)
        proc.start()

    # wait for spawned processes to finish
    for child in childs:
        child.join()

    time.sleep(1)


def get_test_proc_args(sleep_time: Optional[float] = 10) -> List[str]:
    """Return command line string necessary to spawn this file as a subprocess
    (and execute __main__).

    Args:
        sleepTimeSec: set the time spawned process should sleep.

    Returns:
        Command line arguments (list of strings) to spawn this file __main__.

    """
    args = [sys.executable, __file__, str(sleep_time)]

    return args


if __name__ == "__main__":
    if len(sys.argv) == 2:
        sleep_time = float(sys.argv[1])
    else:
        sleep_time = 10
    sleep(sleep_time)

    sys.exit(0)
