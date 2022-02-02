from unittest import mock
import multiprocessing
import os
import sys
import time
from typing import List

import pytest

import dlpt

from tests import helpers

this_pid = os.getpid()


def _wait_for_chil_procs(parent_pid: int, num_of_childs: int, timeout_sec: float) -> List[int]:
    end_time = time.time() + timeout_sec
    childs = []
    while time.time() < end_time:
        childs = dlpt.proc.get_childs(parent_pid)
        if len(childs) == num_of_childs:
            return childs

    assert False, (
        f"During timeout ({timeout_sec} sec) {len(childs)} child "
        f" processes are available but expecting {num_of_childs}"
    )


def test_get_name():
    name = dlpt.proc.get_name(this_pid)
    assert ("python" in name) or ("pytest" in name)


def test_get_executable():
    exe_name = dlpt.proc.get_executable(this_pid)
    assert ("python" in exe_name) or ("pytest" in exe_name)


def test_get_cmd_args():
    args = dlpt.proc.get_cmd_args(this_pid)
    assert len(args) > 1


def test_is_alive():
    with pytest.raises(ValueError):
        dlpt.proc.is_alive(None)

    proc = multiprocessing.Process(target=helpers.sleep, args=(1,))
    proc.start()
    assert dlpt.proc.is_alive(proc.pid) is True
    proc.join(3)
    assert dlpt.proc.is_alive(proc.pid) is False


def test_get_childs():
    NUM_OF_CHILD_PROCS = 3
    TIMEOUT_SEC = 3

    # spawn parent process, which will spawn 3 subprocesses (childs)
    proc = multiprocessing.Process(target=helpers.multiprocess_parent, args=(NUM_OF_CHILD_PROCS,))
    proc.start()
    assert proc.pid is not None

    end_time = time.time() + TIMEOUT_SEC
    childs = []
    while time.time() < end_time:
        childs = dlpt.proc.get_childs(proc.pid)
        if len(childs) == NUM_OF_CHILD_PROCS:
            return  # success

    assert False, (
        f"During timeout ({TIMEOUT_SEC} sec) {len(childs)} "
        f"child processes are available but expecting {NUM_OF_CHILD_PROCS}."
    )


def test_kill():
    TIMEOUT_SEC = 3
    proc = multiprocessing.Process(target=helpers.sleep, args=(TIMEOUT_SEC,))
    proc.start()
    assert proc.pid is not None
    assert dlpt.proc.kill(proc.pid) is True
    assert dlpt.proc.is_alive(proc.pid) is False


def test_kill_childs():
    NUM_OF_CHILD_PROCS = 3
    TIMEOUT_SEC = 3
    # spawn parent process, which will spawn 3 subprocesses (childs)
    proc = multiprocessing.Process(target=helpers.multiprocess_parent, args=(NUM_OF_CHILD_PROCS,))
    proc.start()
    assert proc.pid is not None
    childs = _wait_for_chil_procs(proc.pid, NUM_OF_CHILD_PROCS, TIMEOUT_SEC)

    with mock.patch("dlpt.proc.kill") as kill_func:
        killed_childs = dlpt.proc.kill_childs(proc.pid)
        assert dlpt.utils.are_list_values_equal(childs, killed_childs)
        assert kill_func.call_count == NUM_OF_CHILD_PROCS


def test_kill_tree():
    NUM_OF_CHILD_PROCS = 3
    TIMEOUT_SEC = 3
    # spawn parent process, which will spawn 3 subprocesses (childs)
    proc = multiprocessing.Process(target=helpers.multiprocess_parent, args=(NUM_OF_CHILD_PROCS,))
    proc.start()
    assert proc.pid is not None
    childs = _wait_for_chil_procs(proc.pid, NUM_OF_CHILD_PROCS, TIMEOUT_SEC)

    with mock.patch("dlpt.proc.kill") as kill_func:
        killed_pids = dlpt.proc.kill_tree(proc.pid)
        assert dlpt.utils.are_list_values_equal(childs + [proc.pid], killed_pids)
        assert kill_func.call_count == NUM_OF_CHILD_PROCS + 1  # childs + parent


def test_kill_tree_multiple():
    with mock.patch("dlpt.proc.kill_tree") as kill_tree_func:
        dlpt.proc.kill_tree_multiple([1, 2, 3, 4])
        assert kill_tree_func.call_args_list == [
            mock.call(1, True),
            mock.call(2, True),
            mock.call(3, True),
            mock.call(4, True),
        ]


def test_get_alive():
    py_pids = dlpt.proc.get_alive(dlpt.proc.get_name(this_pid))
    assert this_pid in py_pids


def test_spawn_subproc_stdouterr():
    action_str = "import time; import sys; "
    action_str += "sys.stdout.write('std output'); sys.stdout.flush(); "
    action_str += "sys.stderr.write('std error'); sys.stderr.flush(); "
    args = [sys.executable, "-c", action_str]

    proc = dlpt.proc.spawn_subproc(args)
    assert proc.returncode == 0
    assert proc.stdout == "std output"
    assert proc.stderr == "std error"

    action_str += "sys.exit(1)"
    args = [sys.executable, "-c", action_str]
    with pytest.raises(dlpt.proc.SubprocError) as err:
        dlpt.proc.spawn_subproc(args)
        assert "std output" in str(err.value)
        assert "std error" in str(err.value)


def test_spawn_subproc_exitCode():
    # spawn subprocess with zero return code,  and check its return code
    args = [sys.executable, "-c", "import sys; sys.exit(0)"]
    proc = dlpt.proc.spawn_subproc(args)
    assert proc.returncode == 0

    # spawn subprocess with non-zero return code, ...
    args = [sys.executable, "-c", "import sys; sys.exit(1)"]

    # ... but don't check its return code
    proc = dlpt.proc.spawn_subproc(args, check_return_code=False)
    assert proc.returncode == 1


def test_spawn_subproc_exception():
    args = [sys.executable, "-c", "throw exception"]

    with pytest.raises(dlpt.proc.SubprocError) as err:
        dlpt.proc.spawn_subproc(args)
    assert "throw 'subprocess.CalledProcessError'" in str(err.value)
    assert "throw exception" in str(err.value)

    # invalid arg, spawn Exception
    with pytest.raises(Exception) as err:
        dlpt.proc.spawn_subproc(args, invalid_arg=None)
    assert "Unexpected exception while spawning subprocess" in str(err.value)
    assert "got an unexpected keyword argument 'invalid_arg'" in str(err.value)


def test_spawn_subproc_timeout():
    timeout_sec = 2

    action_str = "import time; import sys; "
    action_str += "sys.stderr.write('errDesc'); sys.stderr.flush(); "
    action_str += "time.sleep(5)"
    args = [sys.executable, "-c", action_str]

    start_time = time.time()
    with pytest.raises(dlpt.proc.SubprocTimeoutError) as err:
        dlpt.proc.spawn_subproc(args, timeout_sec=timeout_sec)
    duration_sec = time.time() - start_time
    assert (timeout_sec - 0.2) < duration_sec < (timeout_sec + 0.2)
    assert "throw 'subprocess.TimeoutExpired'" in str(err.value)
    assert "Stderr: errDesc" in str(err.value)


def test_spawn_subproc_customArgs():
    """
    Spawn a subprocess with extra key-worded run() args.
    """
    action_str = "import os; import sys; "
    action_str += "sys.stdout.write(str(list(os.environ))); sys.stdout.flush();"
    args = ["python", "-c", action_str]

    # get default env vars
    proc = dlpt.proc.spawn_subproc(args)
    assert proc.returncode == 0
    default_env = proc.stdout

    # get subproc env vars
    env_vars = {**os.environ, "_CUSTOM_ENV_VAR_": "keyworded_proc_args"}
    proc = dlpt.proc.spawn_subproc(args, env=env_vars)
    assert proc.returncode == 0
    new_env = proc.stdout

    # compare
    assert new_env != default_env
    assert "_CUSTOM_ENV_VAR_" not in default_env
    assert "_CUSTOM_ENV_VAR_" in new_env


def test_spawn_shell_subproc():
    if sys.platform == "win32":
        args = ["dir"]
    else:
        args = ["ls"]
    proc = dlpt.proc.spawn_shell_subproc(args, cwd=os.path.dirname(__file__))
    assert proc.returncode == 0
    assert proc.stdout != ""
    assert proc.stderr == ""

    args = ["asdqwezxc"]
    proc = dlpt.proc.spawn_shell_subproc(args, timeout_sec=0.5, check_return_code=False)
    assert proc.returncode != 0
    assert proc.stdout == ""
    assert proc.stderr != ""

    with pytest.raises(dlpt.proc.SubprocError):
        dlpt.proc.spawn_shell_subproc(args, timeout_sec=0.5)


def test_spawn_non_blocking_subproc():
    # invalid args, subprocess throws exception
    with pytest.raises(Exception) as err:
        dlpt.proc.spawn_non_blocking_subproc(["qweasdzxc"])

    args = helpers.get_test_proc_args()
    pid = dlpt.proc.spawn_non_blocking_subproc(args)
    assert dlpt.proc.is_alive(pid) is True
    dlpt.proc.kill(pid)


def test_format_args():
    ARGS_LIST = ["a", "s", "d", 1, 2, 3]
    ARGS_STR_LIST = ["a", "s", "d", "1", "2", "3"]

    args_list = dlpt.proc._format_args(ARGS_LIST)
    assert args_list == ARGS_STR_LIST
    with pytest.raises(Exception):
        dlpt.proc._format_args("asd")


def test_decode():
    assert dlpt.proc._decode(None, "utf-8") is None
    assert dlpt.proc._decode("asd", "utf-8") == "asd"
    assert dlpt.proc._decode(b"asd", "utf-8") == "asd"
