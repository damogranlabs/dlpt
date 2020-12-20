import multiprocessing
import sys
import time


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
    sleepTime = float(sleepTime)
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
    This function spawns other child processes mpChild() - needed for PID and process control test functions.
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


if __name__ == "__main__":
    pass
