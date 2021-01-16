"""
Functions for spawning, killing and getting process info.
"""
import os
import signal
import subprocess
from typing import Optional, List, Union, Sequence

import psutil

T_STR_INT = Union[str, int]
T_PROC_ARGS = Sequence[T_STR_INT]

# here are just a couple of most common windows process exit codes
# https://docs.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-
P_EXIT_CODE_SUCCESS = 0  # default success exit code
P_EXIT_CODE_TERMINATED = 15  # process was terminated (killed by OS or user)
P_EXIT_CODE_NOT_FOUND = 127  # process PID not found


class SubprocError(subprocess.SubprocessError):
    """
    Same as subprocess.CalledProcessError, but does not swallow stderr.
    NOTE: stdout is silently swallowed (as with subprocess.SubprocessError), 
        since processes stdout can be long and exception can be unreadable.
    """

    def __init__(self, cmd: str, returncode: int, stdout: Optional[str] = None, stderr: Optional[str] = None):
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:
        errorMsg = f"Spawned subprocess throw 'subprocess.CalledProcessError' exception."
        errorMsg += f"\n\tCommand: {self.cmd}"

        errorMsg += f"\n\tReturn code: {self.returncode}"
        # determine signal if possible
        if self.returncode and (self.returncode < 0):   # pragma: no cover
            try:
                errorMsg += f" (signal: {signal.Signals(-self.returncode)})"
            except ValueError:
                errorMsg += f" (unknown signal: {-self.returncode})"

        # errorMsg += f"\n\tStdout: {self.stdout.strip()}" # see note above.
        errorMsg += f"\n\tStderr: {self.stderr.strip()}"

        return errorMsg


class SubprocTimeoutError(subprocess.SubprocessError):
    """
    Same as subprocess.TimeoutExpired, but does not swallow stderr.
    NOTE: stdout is silently swallowed (as with subprocess.SubprocessError), 
        since processes stdout can be long and exception can be unreadable.
    """

    def __init__(self, cmd: str, timeoutSec: float, stdout: Optional[str] = None, stderr: Optional[str] = None):
        self.cmd = cmd
        self.timeoutSec = timeoutSec
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:
        errorMsg = f"Spawned subprocess throw 'subprocess.TimeoutExpired' exception."
        errorMsg += f"\n\tCommand: {self.cmd}"
        errorMsg += f"\n\tTimeout: {self.timeoutSec} sec"
        if self.stderr:
            errorMsg += f"\n\tStderr: {self.stderr.strip()}"

        return errorMsg


def getName(pid: T_STR_INT) -> str:
    """
    Return process name. Raise Exception on error.
        pid: PID number.
    NOTE: No PID existence check is performed.
    """
    pid = int(pid)
    proc = psutil.Process(pid)
    name = proc.name()

    return name


def getExecutable(pid: T_STR_INT) -> str:
    """
    Return process executable path. Raise Exception on error.
        pid: PID number.
    NOTE: No PID existence check is performed.
    """
    pid = int(pid)
    proc = psutil.Process(pid)
    executablePath = proc.exe()
    executablePath = os.path.normpath(executablePath)

    return executablePath


def getCmdArgs(pid: T_STR_INT) -> List[str]:
    """
    Return a list of process command line arguments as it was intially spawned.
    Raise Exception on error. 
        pid: PID number.
    NOTE: First item on the list is always process executable.
    NOTE: No PID existence check is performed.
    """
    pid = int(pid)
    proc = psutil.Process(pid)
    cmdline = proc.cmdline()
    cmdline[0] = proc.exe()

    return cmdline


def exist(pid: Optional[T_STR_INT]) -> bool:
    """
    Return True if PID exists, False otherwise.
        pid: PID number, string or integer. 
            Raise exception if given PID is None.
    """
    if pid is None:
        errorMsg = f"Unable to check PID - given 'pid' argument is None (expecting string or int)."
        raise ValueError(errorMsg)

    pid = int(pid)

    return psutil.pid_exists(pid)


def getChilds(pid: T_STR_INT) -> List[int]:
    """
    Return a list of child processes PIDs.
        pid: PID number of a parent process, string or integer. 
            Raise Exception if None.
    NOTE: No PID existence check is performed.
    """
    childProcesses = []

    pid = int(pid)
    currentProcess = psutil.Process(pid)
    childProcs = currentProcess.children(recursive=True)
    for childProc in childProcs:
        childPid = childProc.pid
        childProcesses.append(childPid)

    return childProcesses


def kill(pid: T_STR_INT, raiseException: bool = True, waitUntilKilledSec: int = 3) -> bool:
    """
    Kill process with a given PID. Return True if process does not exist,
    Exception or False otherwise.
        pid: PID number.
        raiseException: if True, exception is raised if process wasn't 
            successfully killed. Otherwise return False.
        waitUntilKilledSec: wait for specified number of seconds for
            a process to be killed. If 0, return immediately.
    """
    if exist(pid):
        pid = int(pid)
        proc = psutil.Process(pid)
        try:
            proc.kill()

            if exist(pid):
                if waitUntilKilledSec > 0:
                    gone, alive = psutil.wait_procs([proc], timeout=waitUntilKilledSec)
                    if pid in alive:  # pragma: no cover
                        if raiseException:
                            errorMsg = f"Unable to kill process with PID {pid} "
                            errorMsg += f"(alive even after {waitUntilKilledSec} sec wait)."
                            raise Exception(errorMsg)
                        else:
                            return False
            return True
        except Exception as err:  # pragma: no cover
            if raiseException:
                errorMsg = f"Unable to kill process with PID: {pid}. Error:\n{err}"
                raise Exception(errorMsg)
            else:
                return False
    else:
        return True


def killChilds(pid: T_STR_INT, raiseException: bool = True) -> List[int]:
    """
    Kill all child processes of a process with a given PID. Return a list of
    killed processes.
        pid: PID number, string or integer. Raise Exception if None. 
        raiseException: if True, exception is raised if any of child
            processes can't be killed.
    """
    killedProcs: List[int] = []

    childProcs = getChilds(pid)
    for childProcPid in childProcs:
        kill(childProcPid, raiseException)
        killedProcs.append(childProcPid)

    return killedProcs


def killTree(pid: T_STR_INT, raiseException: bool = True) -> List[int]:
    """
    Kill parent process and all child processes. Return a list of 
    killed processes. 
    NOTE: First, child processes are killed, than parent process.
        pid: PID number, string or integer. Raise Exception if None.
        raiseException: if True, exception is raised if any of processes
            can't be killed. Otherwise, False is returned.
    """
    killedProcs = killChilds(pid, raiseException)  # child procs
    kill(pid, raiseException)  # parent proc
    killedProcs.append(int(pid))

    return killedProcs


def killTreeMultiple(pids: T_PROC_ARGS, raiseException: bool = True) -> List[int]:
    """
    Iterate over pids and perform 'killProcessTree()'. Return a list of 
    killed processes.
        pids: a list of PIDs - string or integer. Raise Exception if None.
        raiseException: if True, exception is raised if any of processes can't be killed.
    """
    killedProcs = []
    for parentPid in pids:
        killedProcs.extend(killTree(parentPid, raiseException))

    return killedProcs


def killByName(nameFilter: str) -> List[int]: # pragma: no cover
    """
    Kill parent process and all child processes. Return a list of killed processes. 
    First child processes are killed, than parent process.
        nameFilter: filter processes by finding nameFilter in a process
            name (lower case string is compared). 
    NOTE: exceptions are silently ignored since function doesn't check how
        processes are related to each other
    """
    killedProcs = []
    for proc in psutil.process_iter():
        try:
            name = proc.name()
            if name.lower() == nameFilter.lower():
                if proc.pid is not None:
                    killedProcs.extend(killTree(proc.pid, False))
        except Exception as err:
            pass  # silently ignore failed attempts

    return killedProcs


def getAlive(nameFilter: Optional[str] = None) -> List[int]:
    """
    Return a list of currently alive process PIDs. 
        nameFilter: if specified, filter return list by finding nameFilter
            in a process name (lower case string is compared). 
    """
    if nameFilter is not None:
        nameFilter = nameFilter.lower()

    pids = []
    for proc in psutil.process_iter():
        try:
            if nameFilter is None:
                pids.append(proc.pid)
            elif nameFilter in proc.name().lower():
                pids.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    return pids


def spawnNonBlockingSubproc(args: T_PROC_ARGS) -> int:
    """
    Spawn non-blockin subprocess with given command line arguments and return PID.
        args: list of subprocess arguments.
            Example: ['python.exe', 'proc.py']

    NOTE: if spawned subprocess throw:
        "OSError: [WinError 740] The requested operation requires elevation" 
        user does not have permission for executing them. Try to re-run script
        with admin permissions.
    """
    _checkIfArgIsList(args)

    command = _getCmdString(args)

    try:
        proc = subprocess.Popen(command)
        if proc.returncode not in [None, 0]:  # pragma: no cover
            # None: process is still executing, 0 - standard process success code
            errorMsg = f"Spawned non-blocking subprocess returned non-success exit code: {proc.returncode}.\n"
            errorMsg += f"\tCommand: {command}\n"
            raise Exception(errorMsg)
        else:
            return proc.pid
    except Exception as err:
        errorMsg = f"Exception while spawning non-blocking subprocess.\n"
        errorMsg += f"\tCommand: {command}\n"
        errorMsg += f"\tError: {err}"
        raise Exception(errorMsg)


def spawnSubproc(args: T_PROC_ARGS,
                 cwd: Optional[str] = None,
                 timeoutSec: Optional[float] = None,
                 checkReturnCode: bool = True) -> subprocess.CompletedProcess:
    """
    Spawn subprocess and return CompletedProcess or raise exception.
    By default, raise exception on timeout (if given) or if return code is not zero.
        args: command line arguments with which process will be spawned. 
            Can be shell commands, like ping.
            NOTE: all commandline arguments (specifically paths) must be 
                properly encoded.
                For example, path containing tilde will throw error.
        cwd: root directory from where subprocess will be executed.
        timeoutSec: timeout in seconds. If None, no timeout is implemented. 
            Else, if timeout is reached, process is killed and TimeoutExpired 
            exception re-raised.
        checkReturnCode: if True, return code is checked by run() function.
            In case it is not zero, SubprocessReturncodeError() is raised. 
            If False, CompletedProcess is returned.

    NOTE: 'stdin' is set to subprocess.PIPE, which should raise exception if
        spawned subprocess require user input.
    NOTE: if spawned subprocess throw:
        "OSError: [WinError 740] The requested operation requires elevation" 
        user does not have permission for executing them. Try to re-run script
        with admin permissions.
    """
    proc = spawnSubprocWithRunArgs(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, encoding='utf-8', cwd=cwd,
        timeout=timeoutSec, check=checkReturnCode)

    return proc


def spawnSubprocWithRunArgs(args: T_PROC_ARGS, **runArgs) -> subprocess.CompletedProcess:
    """
    Same as spawnSubprocess(), but enable user to specify all run() arguments. 
    Return CompletedProcess or raise exception on timeout (if given) or
    non-zero return code.
        args: command line arguments with which process will be spawned.
            NOTE: all commandline arguments (specifically paths) must be 
            properly encoded. 
            For example, path containing: tilde will throw error.
        *runArgs: optional key-worded subprocess.run() arguments, that 
            are added to run() call.
            https://docs.python.org/3.6/library/subprocess.html#popen-constructor
            NOTE: for the common, basic run() args, see spawnSubprocess()

    NOTE: built-in subprocess exceptions are re-defined, since their default 
        __str__ method does not show stderr.
    NOTE: if spawned subprocess throw 
        "OSError: [WinError 740] The requested operation requires elevation"
        user does not have permission for executing them. Try to re-run script
        with admin permissions.
    """
    _checkIfArgIsList(args)

    command = _getCmdString(args)
    proc = None
    try:
        proc = subprocess.run(command, **runArgs)
        return proc
    except subprocess.TimeoutExpired as err:
        raise SubprocTimeoutError(err.cmd, err.timeout, err.stdout, err.stderr)

    except subprocess.CalledProcessError as err:
        # called if checkReturnCode is set to True
        raise SubprocError(err.cmd, err.returncode, err.output, err.stderr)

    except Exception as err:
        errorMsg = f"Unexpected exception while spawning subprocess:"
        errorMsg += f"\n\tCommand: {command}"
        if proc:  # pragma: no cover
            errorMsg += f"\n\tStdout: {proc.stdout.strip()}"
            errorMsg += f"\n\tStderr: {proc.stderr.strip()}"
        errorMsg += f"\n\tError: {err}"
        raise Exception(errorMsg)


def _checkIfArgIsList(args: T_PROC_ARGS):
    """
    Check if given 'args' is a list and raise exception if not.
    Used for all subprocess spawning functions.
        args: argument variable to check (must be list)
    """
    if not isinstance(args, list):
        errorMsg = f"'args' parameter must be list, not '{type(args)}':{args}"
        raise Exception(errorMsg)


def _getCmdString(args: T_PROC_ARGS) -> str:
    """
    Cast all list items (args) to string and return joined string. 
        args: list of arguments to convert to string
    """
    cmdString = ""
    for arg in args:
        cmdString += f"{arg} "

    cmdString = cmdString.strip()

    return cmdString
