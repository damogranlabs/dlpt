import multiprocessing
import sys
import time
from typing import List, Optional


class TestDictClass():
    def __init__(self, one, two, three):
        self.one = one
        self.two = two
        self.three = three

        self._private = "asd"
        self.__superPrivate = "qwe"

    def normal(self):
        return "normalVal"

    @staticmethod
    def static():
        return "staticVal"

    def _hidden(self):
        pass

    def __veryHidden(self):
        pass


def sleep(sleepTime: float):
    time.sleep(sleepTime)


def sleepWithExitCode(sleepTime: float, sysExitCode: int):
    sleep(sleepTime)

    if sysExitCode:
        sys.exit(sysExitCode)


def sleepWithRetCode(sleepTime: float, returnCode: int):
    sleep(sleepTime)

    if returnCode:
        return returnCode


def mpChild(sleepTime: float):
    """
    This function is spawned by mpParent() and does nothing except wait.
    """
    time.sleep(sleepTime)


def mpParent(childNum: int, sleepTime: float = 3):
    """
    This function spawns other child processes mpChild() - 
    needed for PID and process control test functions.
    """
    childs = []
    # spawn child processes
    for child in range(childNum):
        proc = multiprocessing.Process(target=mpChild, args=(sleepTime, ))
        childs.append(proc)
        proc.start()

    # wait for spawned processes to finish
    for child in childs:
        child.join()

    time.sleep(1)


def getTestProcArgs(sleepTimeSec: Optional[float] = 10) -> List[str]:
    """ Return command line string necessary to spawn this file as a subprocess 
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
