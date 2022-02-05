"""
Functions for spawning, killing and getting process info.
"""
import os
import signal
import subprocess
import sys
import traceback
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
    """Same as `subprocess.CalledProcessError`, but does not swallow stderr.

    Note:
        `stdout` is silently swallowed (as with `subprocess.SubprocessError`),
        since processes stdout can be long and exception can be unreadable.
    """

    def __init__(self, cmd: str, returncode: int, stdout: Optional[str] = None, stderr: Optional[str] = None):
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:  # pragma: no cover
        err_msg = "Subprocess throw `subprocess.CalledProcessError` exception."
        err_msg += f"\n\tCommand: {self.cmd}"
        err_msg += f"\n\tReturn code: {self.returncode}"

        # determine signal if possible
        if self.returncode and (self.returncode < 0):
            try:
                err_msg += f" (signal: {signal.Signals(-self.returncode)})"
            except ValueError:
                err_msg += f" (unknown signal: {-self.returncode})"
        # if self.stdout:
        #    err_msg += f"\n\tStdout: {self.stdout.strip()}" # see note above.
        if self.stderr:
            err_msg += f"\n\tStderr: {self.stderr.strip()}"

        return err_msg


class SubprocTimeoutError(subprocess.SubprocessError):
    """Same as `subprocess.TimeoutExpired`, but does not swallow stderr.

    Note:
        `stdout` is silently swallowed (as with `subprocess.SubprocessError`),
        since processes stdout can be long and exception can be unreadable.
    """

    def __init__(self, cmd: str, timeout_sec: float, stdout: Optional[str] = None, stderr: Optional[str] = None):
        self.cmd = cmd
        self.timeout_sec = timeout_sec
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:  # pragma: no cover
        err_msg = f"Subprocess throw 'subprocess.TimeoutExpired' exception."
        err_msg += f"\n\tCommand: {self.cmd}"
        err_msg += f"\n\tTimeout: {self.timeout_sec} sec"
        if self.stderr:
            err_msg += f"\n\tStderr: {self.stderr.strip()}"

        return err_msg


def get_name(pid: T_STR_INT) -> str:
    """Get process name.

    Note:
        No PID existence check is performed.

    Args:
        pid: PID number.

    Return:
        Process name as string.
    """
    return psutil.Process(int(pid)).name()


def get_executable(pid: T_STR_INT) -> str:
    """Get process executable path.

    Note:
        No PID existence check is performed.

    Args:
        pid: PID number.

    Return:
        Process executable as string.

    """
    proc = psutil.Process(int(pid))

    return os.path.normpath(proc.exe())


def get_cmd_args(pid: T_STR_INT) -> List[str]:
    """Return a list of process command line arguments as it was intially spawned.

    Note:
        No PID existence check is performed.

    Args:
        pid: PID number.

    Return:
        A list of process command line spawn arguments.
    """
    proc = psutil.Process(int(pid))
    cmd_line = proc.cmdline()
    # update first item with process executable (absolute path).
    cmd_line[0] = proc.exe()

    return cmd_line


def is_alive(pid: Optional[T_STR_INT]) -> bool:
    """Return True if PID exists and process is running, False otherwise.
    Raise exception if given PID is None.

    Args:
        pid: PID number, string or integer.

    Return:
        True if given PID exists and is running, False otherwise.
    """
    if pid is None:
        err_msg = f"Unable to check PID - given 'pid' argument is None (expecting string or int)."
        raise ValueError(err_msg)

    try:
        return psutil.Process(int(pid)).is_running()
    except Exception as err:
        return False


def get_childs(pid: T_STR_INT) -> List[int]:
    """Return a list of child processes PIDs.

    Note:
        No PID existence check is performed.

    Args:
        pid: PID number of a parent process, string or integer.

    Return:
        A list of process child processes PIDs.
    """
    child_processes = []

    currentProcess = psutil.Process(int(pid))
    child_procs = currentProcess.children(recursive=True)
    for childProc in child_procs:
        child_processes.append(childProc.pid)

    return child_processes


def kill(pid: T_STR_INT, raise_exception: bool = True, timeout_sec: Optional[int] = 3) -> bool:
    """Kill process with a given PID.

    Args:
        pid: PID number.
        raise_exception: if True, exception is raised if process wasn't
            successfully killed. Otherwise return False.
        timeout_sec: wait for specified number of seconds for
            a process to be killed. If None, return immediately.

    Return:
        True on successfully terminated process, False otherwise (or exception,
        based on ``raise_exception`` input argument).
    """
    try:
        proc = psutil.Process(int(pid))
        proc.kill()
        proc.wait(timeout_sec)

        return True

    except Exception as err:  # pragma: no cover
        if raise_exception:
            err_msg = f"Unexpected exception while killing process with PID: {pid}"
            raise Exception(err_msg) from err
        else:
            return False


def kill_childs(pid: T_STR_INT, raise_exception: bool = True) -> List[int]:
    """Kill all child processes of a process with a given PID.

    Args:
        pid: PID number, string or integer. Raise Exception if None.
        raise_exception: if True, exception is raised if any of child
            processes can't be killed.

    Return:
        A list of killed processes.
    """
    killed_procs: List[int] = []

    try:
        child_pids = get_childs(pid)
    except Exception as err:  # pragma: no cover
        if raise_exception:
            err_msg = f"Unexpected exception while getting child process of process with PID: {pid}"
            raise Exception(err_msg) from err
        else:
            return []
    else:
        for child_pid in child_pids:
            kill(child_pid, raise_exception)
            killed_procs.append(child_pid)

        return killed_procs


def kill_tree(pid: T_STR_INT, raise_exception: bool = True) -> List[int]:
    """Kill parent process and all child processes.

    Note:
        First, child processes are killed, than parent process.

    Args:
        pid: PID number, string or integer. Raise Exception if None.
        raise_exception: if True, exception is raised if any of processes
            can't be killed. Otherwise, False is returned.

    Return:
        A list of killed processes.
    """
    killed_procs = kill_childs(pid, raise_exception)  # child procs
    kill(pid, raise_exception)  # parent proc
    killed_procs.append(int(pid))

    return killed_procs


def kill_tree_multiple(pids: T_PROC_ARGS, raise_exception: bool = True) -> List[int]:
    """Iterate over given ``pids`` and perform `kill_tree()`.

    Args:
        pids: a list of PIDs - string or integer. Raise Exception if None.
        raise_exception: if True, exception is raised if any of processes
            can't be killed.

    Return:
        A list of killed processes.
    """
    killed_procs = []
    for parent_pid in pids:
        killed_procs.extend(kill_tree(parent_pid, raise_exception))

    return killed_procs


def get_alive(name_filter: str) -> List[int]:
    """Return a list of currently alive process PIDs.

    Args:
        name_filter: filter return list by finding ``name_filter``
            in a process name (lower case string is compared).

    Example:
        >>> dlpt.proc.get_alive("python.exe")
        [26316, 33672, 73992] # pids of local running python.exe processes

    Return:
        A list of currently alive process PIDs.
    """
    name_filter = name_filter.lower()
    pids = []
    for proc in psutil.process_iter(attrs=["name", "pid"]):
        if proc.name().lower() == name_filter:
            pids.append(proc.pid)

    return pids


def spawn_non_blocking_subproc(args: T_PROC_ARGS) -> int:
    """Spawn non-blockin subprocess with given command line arguments and
    return PID.

    Note:
        If spawned subprocess throw:
        "OSError: [WinError 740] The requested operation requires elevation"
        user does not have permission for executing them. Try to re-run script
        with admin permissions.

    Args:
        args: list of subprocess arguments.

    Example:
        >>> args = ['python.exe', 'proc.py']
        >>> dlpt.proc.spawn_non_blocking_subproc(args)
        1234

    Return:
        Spawned process PID.
    """
    args = _format_args(args)

    try:
        proc = subprocess.Popen(args)
        if proc.returncode in [None, 0]:
            # None: process is still executing
            # 0 - standard process success code
            return proc.pid
        else:  # pragma: no cover
            err_msg = f"Spawned non-blocking subprocess returned non-success exit code: {proc.returncode}."
            err_msg += f"\n\tCommand: {args}\n"
            raise Exception(err_msg)
    except Exception as err:
        err_msg = f"Exception while spawning non-blocking subprocess."
        err_msg += f"\n\tCommand: {args}\n"
        raise Exception(err_msg) from err


def spawn_subproc(
    args: T_PROC_ARGS,
    check_return_code: bool = True,
    stdout: Optional[int] = subprocess.PIPE,
    stderr: Optional[int] = subprocess.PIPE,
    stdin: Optional[int] = subprocess.PIPE,
    encoding: str = "utf-8",
    timeout_sec: Optional[float] = None,
    **run_args,
) -> subprocess.CompletedProcess:
    """Spawn subprocess and return CompletedProcess or raise exception.
    By default, raise exception on timeout (if given) or if return code is not
    zero. With ``**run_args``, allow setting all `subprocess.run()`_
    arguments.

    Note:
        If spawned subprocess throw:
        "OSError: [WinError 740] The requested operation requires elevation"
        user does not have permission for executing them. Try to re-run script
        with admin permissions.

    Args:
        args: command line arguments with which process will be spawned.
            Can be shell commands, like ping. Note: all commandline arguments
            (specifically paths) must be properly encoded. For example, path
            containing tilde will throw error.
        check_return_code: if True, return code is checked by run() function.
            In case it is not zero, `SubprocessReturncodeError()` is raised.
            If False, `CompletedProcess` is returned.
        stdout: STDOUT routing specifier.
        stderr: STDERR routing specifier.
        stdin: STDIN routing specifier. Note: By default, 'stdin' is set to
            subprocess.PIPE, which should raise exception if spawned subprocess
            require user input.
        encoding: STDOUT/ERR string encoding
        timeout_sec: timeout in seconds. If None, no timeout is implemented.
            Else, if timeout is reached, process is killed and TimeoutExpired
            exception re-raised.
        run_args: optional key-worded `subprocess.run()`_ arguments. Note: for the
            common basic `subprocess.run()` args,
            see :func:`spawn_subprocess()`.

    Example:
        >>> args = ['python.exe', 'proc.py']
        >>> env_vars = {**os.environ, 'TEST_KEY': 'testenvvar'} # optional kwarg
        >>> proc = dlpt.proc.spawn_subproc(args, timeout_sec: 3, env=env_vars)
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
    args = _format_args(args)

    proc = None
    try:
        proc = subprocess.run(
            args,
            stdout=stdout,
            stderr=stderr,
            stdin=stdin,
            encoding=encoding,
            timeout=timeout_sec,
            check=check_return_code,
            **run_args,
        )
        return proc

    except subprocess.TimeoutExpired as err:
        raise SubprocTimeoutError(
            err.cmd, err.timeout, _decode(err.stdout, encoding), _decode(err.stderr, encoding)
        ) from err

    except subprocess.CalledProcessError as err:
        # called if check_return_code is set to True
        raise SubprocError(
            err.cmd, err.returncode, _decode(err.stdout, encoding), _decode(err.stderr, encoding)
        ) from err

    except Exception as err:
        err_msg = f"Unexpected exception while spawning subprocess:"
        err_msg += f"\n\tCommand: {args}"
        if proc:  # pragma: no cover
            if proc.stdout:
                err_msg += f"\n\tStdout: {_decode(proc.stdout, encoding)}"
            if proc.stderr:
                err_msg += f"\n\tStderr: {_decode(proc.stdout, encoding)}"
        err_msg += f"\n\tTraceback: {traceback.format_exc()}"
        raise Exception(err_msg) from err


def spawn_shell_subproc(
    args: T_PROC_ARGS,
    check_return_code: bool = True,
    encoding: str = "utf-8",
    timeout_sec: Optional[float] = None,
    **run_args,
) -> subprocess.CompletedProcess:
    """Similar to :func:`spawn_subproc()` but for shell commands. STDOUT/ERR is
    hidden from user and only set in returned `proc.stdout/err`.

    Note:
        If spawned subprocess throw:
        "OSError: [WinError 740] The requested operation requires elevation"
        user does not have permission for executing them. Try to re-run script
        with admin permissions.

    Args:
        args: command line arguments with which process will be spawned.
            Can be shell commands, like ping. Note: all commandline arguments
            (specifically paths) must be properly encoded. For example, path
            containing tilde will throw error.
        check_return_code: if True, return code is checked by `run()` function.
            In case it is not zero, ``SubprocessReturncodeError`` is raised.
            If False, ``CompletedProcess`` is returned.
        encoding: STDOUT/ERR string encoding
        timeout_sec: timeout in seconds. If None, no timeout is implemented.
            Else, if timeout is reached, process is killed and TimeoutExpired
            exception re-raised.
        run_args: optional key-worded `subprocess.run()` arguments, that
            are added to `run()` call. Note: for the common, basic
            :func:`subprocess.run()` args, see :func:`spawn_subprocess()`

    Example:
        >>> args = ['dir']
        >>> dlpt.proc.spawn_shell_subproc(args)
        proc.py, pth.py, # ...

    Return:
        ``CompleteProcess`` object once process execution has finished or was
        terminated.
    """
    stdout = None
    stderr = None
    if (sys.version_info.major == 3) and (sys.version_info.minor < 7):
        # 'capture_output' was introduced in py 3.6
        stdout = subprocess.PIPE
        stderr = subprocess.PIPE
    else:
        run_args["capture_output"] = True

    return spawn_subproc(
        args,
        stdout=stdout,
        stderr=stderr,
        check_return_code=check_return_code,
        encoding=encoding,
        timeout_sec=timeout_sec,
        shell=True,
        **run_args,
    )


def _format_args(args: T_PROC_ARGS) -> List[str]:
    """Check if given 'args' is a list and raise exception if not.
    Cast any non-string items to string and return prepared arguments list.

    Args:
        args: argument variable to check (must be list)

    Return:
        List of arguments, where each item is a string.
    """
    if not isinstance(args, list):
        err_msg = f"'args' parameter must be list, not '{type(args)}': {args}"
        raise Exception(err_msg)

    new_args = []
    for arg in args:
        if isinstance(arg, str):
            new_args.append(arg)
        else:
            new_args.append(str(arg))

    return new_args


def _decode(data: Union[None, str, bytes], encoding: str) -> Optional[str]:
    """Encode given ``data`` with ``encoding`` format or return string|None.

    Args:
        data: data to encode.
        encoding: selected encoding of the given ``data``.

    Return:
        String representation of the given ``data`` or None.
    """
    if data is None:
        return None
    else:
        if isinstance(data, str):
            return data
        else:
            return str(data, encoding)
