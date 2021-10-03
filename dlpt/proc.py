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

    def __init__(self,
                 cmd: str,
                 returncode: int,
                 stdout: Optional[str] = None,
                 stderr: Optional[str] = None):
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:  # pragma: no cover
        errorMsg = "Subprocess throw 'subprocess.CalledProcessError' exception."
        errorMsg += f"\n\tCommand: {self.cmd}"
        errorMsg += f"\n\tReturn code: {self.returncode}"

        # determine signal if possible
        if self.returncode and (self.returncode < 0):
            try:
                errorMsg += f" (signal: {signal.Signals(-self.returncode)})"
            except ValueError:
                errorMsg += f" (unknown signal: {-self.returncode})"
        # if self.stdout:
        #    errorMsg += f"\n\tStdout: {self.stdout.strip()}" # see note above.
        if self.stderr:
            errorMsg += f"\n\tStderr: {self.stderr.strip()}"

        return errorMsg


class SubprocTimeoutError(subprocess.SubprocessError):
    """
    Same as subprocess.TimeoutExpired, but does not swallow stderr.

    NOTE: stdout is silently swallowed (as with subprocess.SubprocessError),
        since processes stdout can be long and exception can be unreadable.
    """

    def __init__(self,
                 cmd: str,
                 timeoutSec: float,
                 stdout: Optional[str] = None,
                 stderr: Optional[str] = None):
        self.cmd = cmd
        self.timeoutSec = timeoutSec
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:  # pragma: no cover
        errorMsg = f"Subprocess throw 'subprocess.TimeoutExpired' exception."
        errorMsg += f"\n\tCommand: {self.cmd}"
        errorMsg += f"\n\tTimeout: {self.timeoutSec} sec"
        if self.stderr:
            errorMsg += f"\n\tStderr: {self.stderr.strip()}"

        return errorMsg


def getName(pid: T_STR_INT) -> str:
    """
    Get process name.

    NOTE: No PID existence check is performed.

    Args:
        pid: PID number.

    Return:
        Process name as string.
    """
    proc = psutil.Process(int(pid))
    name = proc.name()

    return name


def getExecutable(pid: T_STR_INT) -> str:
    """
    Get process executable path.

    NOTE: No PID existence check is performed.

    Args:
        pid: PID number.

    Return:
        Process executable as string.

    """
    proc = psutil.Process(int(pid))
    executablePath = os.path.normpath(proc.exe())

    return executablePath


def getCmdArgs(pid: T_STR_INT) -> List[str]:
    """
    Return a list of process command line arguments as it was intially spawned.

    NOTE: No PID existence check is performed.

    Args:
        pid: PID number.

    Return:
        A list of process command line spawn arguments.
    """
    proc = psutil.Process(int(pid))
    cmdline = proc.cmdline()
    cmdline[0] = proc.exe()

    return cmdline


def exist(pid: Optional[T_STR_INT]) -> bool:
    """
    Return True if PID exists, False otherwise.

    NOTE: Raise exception if given PID is None.

    Args:
        pid: PID number, string or integer.

    Return:
        True if given PID exists (is alive), False otherwise.
    """
    if pid is None:
        errorMsg = f"Unable to check PID - given 'pid' argument is None "
        errorMsg += f" (expecting string or int)."
        raise ValueError(errorMsg)

    return psutil.pid_exists(int(pid))


def getChilds(pid: T_STR_INT) -> List[int]:
    """
    Return a list of child processes PIDs.

    NOTE: No PID existence check is performed.

    Args:
        pid: PID number of a parent process, string or integer.


    Return:
        A list of process child processes PIDs.
    """
    childProcesses = []

    currentProcess = psutil.Process(int(pid))
    childProcs = currentProcess.children(recursive=True)
    for childProc in childProcs:
        childPid = childProc.pid
        childProcesses.append(childPid)

    return childProcesses


def kill(pid: T_STR_INT,
         raiseException: bool = True,
         timeoutSec: int = 3) -> bool:
    """
    Kill process with a given PID.

    Args:
        pid: PID number.
        raiseException: if True, exception is raised if process wasn't
            successfully killed. Otherwise return False.
        timeoutSec: wait for specified number of seconds for
            a process to be killed. If 0, return immediately.

    Return:
        True on successfully terminated process, False otherwise (or exception,
        based on ``raiseException`` input argument).
    """
    if exist(pid):
        proc = psutil.Process(int(pid))
        try:
            proc.terminate()
            if timeoutSec > 0:  # pragma: no cover
                try:
                    proc.wait(timeoutSec)
                except psutil.TimeoutExpired as err:
                    proc.kill()

            if exist(pid):
                if raiseException:
                    errorMsg = f"Unable to kill process with PID {pid} "
                    errorMsg += f"(alive even after {timeoutSec} sec)."
                    raise Exception(errorMsg)
                else:
                    return False
            else:
                return True

        except Exception as err:  # pragma: no cover
            if raiseException:
                errorMsg = f"Unable to kill process with PID: {pid}. "
                errorMsg += f"Error:\n{err}"
                raise Exception(errorMsg)
            else:
                return False
    else:
        return True


def killChilds(pid: T_STR_INT, raiseException: bool = True) -> List[int]:
    """
    Kill all child processes of a process with a given PID.

    Args:
        pid: PID number, string or integer. Raise Exception if None.
        raiseException: if True, exception is raised if any of child
            processes can't be killed.

    Return:
        A list of killed processes.
    """
    killedProcs: List[int] = []

    childProcs = getChilds(pid)
    for childProcPid in childProcs:
        kill(childProcPid, raiseException)
        killedProcs.append(childProcPid)

    return killedProcs


def killTree(pid: T_STR_INT, raiseException: bool = True) -> List[int]:
    """
    Kill parent process and all child processes.

    NOTE: First, child processes are killed, than parent process.

    Args:
        pid: PID number, string or integer. Raise Exception if None.
        raiseException: if True, exception is raised if any of processes
            can't be killed. Otherwise, False is returned.

    Return:
        A list of killed processes.
    """
    killedProcs = killChilds(pid, raiseException)  # child procs
    kill(pid, raiseException)  # parent proc
    killedProcs.append(int(pid))

    return killedProcs


def killTreeMultiple(pids: T_PROC_ARGS,
                     raiseException: bool = True) -> List[int]:
    """
    Iterate over pids and perform 'killTree()'.

    Args:
        pids: a list of PIDs - string or integer. Raise Exception if None.
        raiseException: if True, exception is raised if any of processes
            can't be killed.

    Return:
        A list of killed processes.
    """
    killedProcs = []
    for parentPid in pids:
        killedProcs.extend(killTree(parentPid, raiseException))

    return killedProcs


def getAlive(nameFilter: str) -> List[int]:
    """
    Return a list of currently alive process PIDs.

    Args:
        nameFilter: filter return list by finding ``nameFilter``
            in a process name (lower case string is compared).

    Example:
        >>> dlpt.proc.getAlive("python.exe")
        [26316, 33672, 73992] # pids of local running python.exe processes

    Return:
        A list of currently alive process PIDs.
    """
    nameFilter = nameFilter.lower()
    pids = []
    for proc in psutil.process_iter(attrs=["name", "pid"]):
        if proc.name().lower() == nameFilter:
            pids.append(proc.pid)

    return pids


def spawnNonBlockingSubproc(args: T_PROC_ARGS) -> int:
    """
    Spawn non-blockin subprocess with given command line arguments and
    return PID.

    NOTE: if spawned subprocess throw:
        "OSError: [WinError 740] The requested operation requires elevation"
        user does not have permission for executing them. Try to re-run script
        with admin permissions.

    Args:
        args: list of subprocess arguments.

    Example:
        >>> args = ['python.exe', 'proc.py']
        >>> dlpt.proc.spawnNonBlockingSubproc(args)
        1234

    Return:
        Spawned process PID.
    """
    args = _formatArgs(args)

    try:
        proc = subprocess.Popen(args)
        if proc.returncode in [None, 0]:
            # None: process is still executing
            # 0 - standard process success code
            return proc.pid
        else:  # pragma: no cover
            errorMsg = "Spawned non-blocking subprocess returned non-success "
            errorMsg += f"exit code: {proc.returncode}."
            errorMsg += f"\n\tCommand: {args}\n"
            raise Exception(errorMsg)
    except Exception as err:
        errorMsg = f"Exception while spawning non-blocking subprocess.\n"
        errorMsg += f"\tCommand: {args}\n"
        errorMsg += f"\tError: {err}"
        raise Exception(errorMsg) from err


def spawnSubproc(args: T_PROC_ARGS,
                 checkReturnCode: bool = True,
                 stdout: Optional[int] = subprocess.PIPE,
                 stderr: Optional[int] = subprocess.PIPE,
                 stdin: Optional[int] = subprocess.PIPE,
                 encoding: str = 'utf-8',
                 timeoutSec: Optional[float] = None,
                 **runArgs) -> subprocess.CompletedProcess:
    """
    Spawn subprocess and return CompletedProcess or raise exception. 
    By default, raise exception on timeout (if given) or if return code is not
    zero. With `**runArgs`, allow setting all :func:`subprocess.run()_` 
    arguments.

    NOTE: if spawned subprocess throw:
        "OSError: [WinError 740] The requested operation requires elevation"
        user does not have permission for executing them. Try to re-run script
        with admin permissions.

    Args:
        args: command line arguments with which process will be spawned.
            Can be shell commands, like ping. NOTE: all commandline arguments
            (specifically paths) must be properly encoded. For example, path
            containing tilde will throw error.
        checkReturnCode: if True, return code is checked by run() function.
            In case it is not zero, SubprocessReturncodeError() is raised.
            If False, CompletedProcess is returned.
        stdout: STDOUT routing specifier.
        stderr: STDERR routing specifier.
        stdin: STDIN routing specifier. Note: By default, 'stdin' is set to 
            subprocess.PIPE, which should raise exception if spawned subprocess 
            require user input.
        encoding: STDOUT/ERR string encoding
        timeoutSec: timeout in seconds. If None, no timeout is implemented.
            Else, if timeout is reached, process is killed and TimeoutExpired
            exception re-raised.
        runArgs: optional key-worded subprocess.run() arguments, that
            are added to `run()`_ call. NOTE: for the common, basic
            :func:`subprocess.run()` args, see :func:`spawnSubprocess()`

    Example:
        >>> args = ['python.exe', 'proc.py']
        >>> envVars = {**os.environ, 'TEST_KEY': 'testenvvar'} # optional kwarg
        >>> proc = dlpt.proc.spawnSubproc(args, timeoutSec: 3, env=envVars)
        >>> proc.pid
        1234
        >>> proc.returncode
        0

    Return:
        ``CompleteProcess`` object once process execution has finished or was
        terminated.

    .. _subprocess.run():
        https://docs.python.org/3.6/library/subprocess.html#popen-constructor
    """
    args = _formatArgs(args)

    proc = None
    try:
        proc = subprocess.run(args,
                              stdout=stdout,
                              stderr=stderr,
                              stdin=stdin,
                              encoding=encoding,
                              timeout=timeoutSec,
                              check=checkReturnCode,
                              **runArgs)
        return proc

    except subprocess.TimeoutExpired as err:
        raise SubprocTimeoutError(err.cmd,
                                  err.timeout,
                                  _decode(err.stdout, encoding),
                                  _decode(err.stderr, encoding)) from err

    except subprocess.CalledProcessError as err:
        # called if checkReturnCode is set to True
        raise SubprocError(err.cmd,
                           err.returncode,
                           _decode(err.stdout, encoding),
                           _decode(err.stderr, encoding)) from err

    except Exception as err:
        errorMsg = f"Unexpected exception while spawning subprocess:"
        errorMsg += f"\n\tCommand: {args}"
        if proc:  # pragma: no cover
            if proc.stdout:
                errorMsg += f"\n\tStdout: {_decode(proc.stdout, encoding),}"
            if proc.stderr:
                errorMsg += f"\n\tStderr: {_decode(proc.stdout, encoding),}"
        errorMsg += f"\n\tError: {err}"
        raise Exception(errorMsg)


def spawnShellCmd(args: T_PROC_ARGS,
                  checkReturnCode: bool = True,
                  encoding: str = 'utf-8',
                  timeoutSec: Optional[float] = None,
                  **runArgs) -> subprocess.CompletedProcess:
    """
    Similar to :func:`spawnSubproc()` but for shell commands. STDOUT/ERR is 
    hidden from user and only set in returned `proc.stdout/err`.

    NOTE: if spawned subprocess throw:
        "OSError: [WinError 740] The requested operation requires elevation"
        user does not have permission for executing them. Try to re-run script
        with admin permissions.

    Args:
        args: command line arguments with which process will be spawned.
            Can be shell commands, like ping. NOTE: all commandline arguments
            (specifically paths) must be properly encoded. For example, path
            containing tilde will throw error.
        checkReturnCode: if True, return code is checked by run() function.
            In case it is not zero, SubprocessReturncodeError() is raised.
            If False, CompletedProcess is returned.
        encoding: STDOUT/ERR string encoding
        timeoutSec: timeout in seconds. If None, no timeout is implemented.
            Else, if timeout is reached, process is killed and TimeoutExpired
            exception re-raised.
        runArgs: optional key-worded subprocess.run() arguments, that
            are added to `run()`_ call. NOTE: for the common, basic
            :func:`subprocess.run()` args, see :func:`spawnSubprocess()`

    Example:
        >>> args = ['dir']
        >>> dlpt.proc.spawnShellCmd(args)
        proc.py, pth.py, # ...

    Return:
        ``CompleteProcess`` object once process execution has finished or was
        terminated.
    """
    return spawnSubproc(args,
                        stdout=None,
                        stderr=None,
                        checkReturnCode=checkReturnCode,
                        encoding=encoding,
                        timeoutSec=timeoutSec,
                        capture_output=True,
                        shell=True,
                        **runArgs)


def _formatArgs(args: T_PROC_ARGS) -> List[str]:
    """
    Check if given 'args' is a list and raise exception if not.
    Cast any non-string items to string and return prepared arguments list.

    Args:
        args: argument variable to check (must be list)

    Return:
        List of arguments, where each item is a string.
    """
    if not isinstance(args, list):
        errorMsg = f"'args' parameter must be list, not '{type(args)}':{args}"
        raise Exception(errorMsg)

    newArgs = []
    for arg in args:
        if isinstance(arg, str):
            newArgs.append(arg)
        else:
            newArgs.append(str(arg))

    return newArgs


def _decode(data: Union[None, str, bytes], encoding: str) -> Optional[str]:
    """
    Encode given `data` with `encoding` format or return string|None.

    Args: 
        data: data to encode.
        encoding: selected encoding of the given `data`.

    Return:
        String representation of the given `data` or None.
    """
    if data is None:
        return None
    else:
        if isinstance(data, str):
            return data
        else:
            return str(data, encoding)
