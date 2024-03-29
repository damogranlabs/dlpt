![PyPI - License](https://img.shields.io/pypi/l/dlpt)
![PyPI](https://img.shields.io/pypi/v/dlpt)
![Read the Docs](https://img.shields.io/readthedocs/dlpt)
[![codecov](https://codecov.io/gh/damogranlabs/dlpt/branch/main/graph/badge.svg?token=9RXXPWZHRF)](https://codecov.io/gh/damogranlabs/dlpt)

# dlpt
Damogran Labs Python Tools, a collection of modules with utility functions to ease everyday Python 
usage. It runs smoothly on windows, linux and mac-os.  
Homepage: [https://damogranlabs.com/2021/01/dlpt/](https://damogranlabs.com/2021/01/dlpt/)  
PyPi: [https://pypi.org/project/dlpt/](https://pypi.org/project/dlpt/)  
Docs: [https://dlpt.readthedocs.io/en/latest/](https://dlpt.readthedocs.io/en/latest/)  
Install: `pip install -U dlpt`  

## Why?
This package main purpose is to stop reinventing the wheel on top of the built-in Python functions 
in every single project. Everyday struggle with:
* how do I initialize logger and add file handler?
* how do I temporary change current working directory?
* how do I spawn a subprocess and add stdout on any exception?
* how do I get only directories inside some location?
* how do I parse JSON file with comments?
* how do I format time to string in one line?
* how do I dynamically import some module that is not on a `sys.path`?
* ...

These and many more everyday Python code questions should be covered with this library. Nothing extra,
just simplified.  
Mostly built upon standard built-in code, but with a lot more straight-forward and less cluttered API.

## Modules
`dlpt.pth`: everything about paths and file/directory operations: list files/directories, copy/remove, get extensions, ...  
`dlpt.utils`: everyhting we always need and never remember: list/dict comparison, values<->string transformation, module inspections, ...  
`dlpt.log`: create new logger(s) and/or add common handlers (console/stream, file, ...) to any logger. Supports cross-process logging.  
`dlpt.proc`: everything about common process use cases, but with more info on exceptions and easier straight-forward API.  
`dlpt.time`: everything about time<->string transformation and code timing (timing decorator or special function wrapper)...  
`dlpt.json`: read/write JSON files or python objects, with comments and smart pickling using `jsonpickle` library...  
`dlpt.importer`: dynamically import python modules and inspect its object or call its functions/classes...


## Examples:  
> How do I initialize logger and add file handler?
```python
# init default logger with console and file handler (file in <cwd>/log sub-directory)
import dlpt

logger = dlpt.log.create_logger("my_logger")
dlpt.log.add_console_hdlr(logger)
hdlr, file_path = dlpt.log.add_file_hdlr(logger, "dlpt_example.log")
log.debug(f"Logger initialised, file: {file_path}")

# additionally, add handler to any existing logger with one liner:
dlpt.log.add_rotating_file_hdlr("root", "fname.log")
```

> How do I temporary change current working directory?
```python
import os
import dlpt

print(f"Current working directory: {os.getcwd()}")

dir_path = os.path.join(os.getcwd(), "..", "..")
with dlpt.pth.ChangeDir(dir_path):
    print(f"Current temporary working directory: {os.getcwd()}")
print(f"Current working directory: {os.getcwd()}")
```

> How do I spawn a subprocess and add stdout on any exception?
```python
import sys

import dlpt

# a valid subprocess
args = [sys.executable, "-c", "import dlpt; print(dlpt.utils.float_to_str(12324.56))"]
proc = dlpt.proc.spawn_subproc(args)
print(proc.stdout) # will print:
# '12324.56'

# invalid subprocess, will throw exception
args = [sys.executable, "-c", "throw exception"]
dlpt.proc.spawn_subproc(args) # will print:
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "D:\Stromarija\GIT\dlpt\dlpt\proc.py", line 417, in spawn_subproc
#     ) from err
# dlpt.proc.SubprocError: Subprocess throw `subprocess.CalledProcessError` exception.
#         Command: ['D:\\Stromarija\\GIT\\dlpt\\env\\Scripts\\python.exe', '-c', 'throw exception']
#         Return code: 1
#         Stderr: File "<string>", line 1
#     throw exception
#                   ^
# SyntaxError: invalid syntax
```

> How do I get only `.pyc` files inside some location?
```python
import dlpt

files = dlpt.pth.get_files_in_dir_tree(os.getcwd(), exclude_ext=[".pyc"])
for file_path in files:
    print(f"File {dlpt.pth.get_name(file_path)}: {file_path}")
```

> How do I get all subdirectories inside some location? Can I filter only the ones that have date: 10.3.2020 in name?
```python
import dlpt

dirs = dlpt.pth.get_dirs_in_dir(os.getcwd(), "10.3.2020_")
print(f"Dirs: {dlpt.utils.get_list_str(dirs)}")
```

> How do I parse JSON file with comments?
```python
import dlpt

file_path = input("Enter a path to a JSON file with comments: ")
data = dlpt.json.read(file_path)

# alternatively, if file was created with `dlpt.json.write_jsonpickle()`, user can:
data = dlpt.json.read_jsonpickle(file_path)
```

> How do I format time to a string in one line?
```python
import dlpt

# 2 days, 4 hours, 6 mins, 12 sec, 0.33 milliseconds
sec = dlpt.time.time_to_seconds(h=52, m=6, s=12.033)
end_time = dlpt.time.sec_to_str(duration_sec, dlpt.time.TIME_FORMAT_HMS_STRING)
print(end_time) # will print: '52 h 6 min 12.33 sec'
```

> How do I print approximate execution time of some function?
```python
import time
import dlpt

@dlpt.time.print_exec_time
def my_function(*args, **kwargs):
    time.sleep(42)

my_function()
# will print: "'my_function' execution time: 42.63 sec"

# alternatively, without decorator in a runtime/debug mode
my_function_timed = dlpt.time.func_stopwatch(my_function)
my_function_timed(arg1, arg2)
print(f"Execution time: {dlpt.time.get_last_measured_time_sec()}")
```

> How do I dynamically import some module that is not on a `sys.path`?
```python
import dlpt

file_path = input("Enter a path to a python module that you wish to dynamically import:")
importer = dlpt.importer.ModuleImporter(file_path)
print(f"Does module have an object with name 'myObject'? {importer.has_object('myObject')}")

# call a function of this module:
module = importer.get_module()
module.someFunction()
```

Many more examples and showcases of everyday uses can be found in [tests](https://github.com/damogranlabs/dlpt/tree/main/tests]). 


