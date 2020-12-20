"""
Process watchdog utility functions, that can observe and kill watched process
on a timeout.
"""
import multiprocessing
import time

import dlpt


class Watchdog():
    def __init__(self,
                 userPid: int,
                 timeoutSec: int):
        """
        Class to initialise PID watchdog by creating new watchdog timer subprocess.
            @param userPid: pid to kill once watchdog is started and time has passed.
            @param timeoutSec: time after userPid is killed.
                NOTE: WARNING: while setting WDG timeout, use common 
                sense - very small timeouts can be problematic if observed 
                process will spawn child processes. In this case a race 
                condition can occur just between subprocess is spawned.
        """
        self.userPid: int = userPid

        if timeoutSec <= 0:
            errorMsg = f"Invalid WDG configuration, timeoutSec should be larger than 0!"
            raise ValueError(errorMsg)
        self.timeoutSec = int(timeoutSec)

        self._wdgPid: int = -1

    def getTimeoutSec(self) -> int:
        """
        Return previously set watchdog timeout in seconds
        """
        return int(self.timeoutSec)

    def getTimeoutMin(self) -> int:
        """
        Return previously set watchdog timeout in minutes (rounded).
        """
        minutes = int(self.timeoutSec / 60)
        return minutes

    def start(self):
        """
        Start configured process watchdog timer.
        """
        wdgProc = multiprocessing.Process(target=_wdgCountdownTimer, args=(self.userPid, self.timeoutSec))
        wdgProc.daemon = True
        wdgProc.start()
        assert wdgProc.pid is not None, "WDG process started, but its PID is None!"
        self._wdgPid = wdgProc.pid

    def stop(self):
        """
        Stop watchdog by killing watchdog sub-process.
        """
        if self._wdgPid != -1:
            dlpt.proc.kill(self._wdgPid, raiseException=False)
            # avoid killing other processes if this function is called more than once
            self._wdgPid = -1

    def isWdgAlive(self) -> bool:
        """
        Return bool status of internal watchdog subprocess.
        """
        if self._wdgPid == -1:
            status = False
        else:
            status = dlpt.proc.exist(self._wdgPid)

        return status

    def isMyPidAlive(self) -> bool:
        """
        Returns bool status of observed user PID.
        """
        status = dlpt.proc.exist(self.userPid)

        return status

    def isKilledByWdg(self) -> bool:
        """
        Return True if watchdog and user PID does not exist - meaning watchdog
        timeout has been reached and observed process was killed by watchdog.
        False otherwise.
        """
        if not self.isWdgAlive():
            if not self.isMyPidAlive():
                return True
        return False


def _wdgCountdownTimer(pidToKill: int, timeoutSec: int):
    """
    Private countdown timer, initiated as a sub-process from Watchdog().start().
        @param pidToKill: pid to kill after watchdog time passed
        @param timeoutSec: time in seconds after this function will kill process
            with pidToKill PID
        @param killChildProcs: If True, on timeout wdg try to kill all child 
            processes. Otherwise, only given process is killed.
    """
    while timeoutSec > 0:
        time.sleep(1)
        timeoutSec = timeoutSec - 1

    dlpt.proc.killTree(pidToKill)
