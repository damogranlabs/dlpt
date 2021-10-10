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
* how do I get only folders inside some location?
* how do I parse JSON file with comments?
* how do I format time to string in one line?
* how do I dynamically import some module that is not on a `sys.path`?
* ...

These and many more everyday Python code questions should be covered with this library. Nothing extra,
just simplified.  
Mostly built upon standard built-in code, but with a lot more straight-forward and less cluttered API.

## Modules
`dlpt.pth`: everything about paths and filed/folder operations: list files/folders, copy/remove, get extensions, ...  
`dlpt.utils`: everyhting we always need and never remember: list/dict comparison, values<->string transformation, module inspections, ...  
`dlpt.log`: create new logger(s) and/or add common handlers (console/stream, file, ...) to any logger. Supports cross-process logging.  
`dlpt.proc`: everything about common process use cases, but with more info on exceptions and easier straight-forward API.  
`dlpt.time`: everything about time<->string transformation and code timing (timing decorator or special function wrapper)...  
`dlpt.json`: read/write JSON files or python objects, with comments and smart pickling using `jsonpickle` library...  
`dlpt.importer`: dynamically import python modules and inspect its object or call its functions/classes...


## Examples:  
> How do I initialize logger and add file handler?
```python
# init default logger with console and file handler (file in <cwd>/log subfolder)
import dlpt

logger = dlpt.log.createLogger("myLogger")
dlpt.log.addConsoleHandler(logger)
hdlr, fPath = dlpt.log.addFileHandler(logger,
                                     "dlpt_example.log")
log.debug(f"Logger initialised, file: {fPath}")
```

> How do I temporary change current working directory?
```python
import os
import dlpt

print(f"Current working directory: {os.getcwd()}")

dirPath = os.path.join(os.getcwd(), "..", "..")
with dlpt.pth.ChangeDir(dirPath):
    print(f"Current temporary working directory: {os.getcwd()}")

print(f"Current working directory: {os.getcwd()}")
```

> How do I spawn a subprocess and add stdout on any exception?
```python
import sys

import dlpt

# a valid subprocess
args = [sys.executable, "-c", "import dlpt; print(dlpt.utils.floatToStr(12324.5678))"]
proc = dlpt.proc.spawnSubproc(args)
print(proc.stdout) # will print '12324.57'

# invalid subprocess, will throw exception
args = [sys.executable, "-c", "throw exception"]
dlpt.proc.spawnSubproc(args)
```

> How do I get only folders inside some location?
```python
import dlpt

files = dlpt.pth.getFilesInFolderTree(os.getcwd(), excludeExt=[".pyc"])
for fPath in files:
    print(f"File {dlpt.pth.getName(fPath)}: {fPath}")
```
> How do I parse JSON file with comments?
```python
import dlpt

fPath = input("Enter a path to a JSON file with comments: ")
data = dlpt.json.read(fPath)
# alternatively, if file was created with `dlpt.json.writeJsonpickle()`, user can:
data = dlpt.json.readJsonpickle(fPath)
```

> How do I format time to string in one line?
```python
import dlpt

# 2 days, 4 hours, 6 mins, 12 sec, 0.33 milliseconds
sec = dlpt.time.timeToSeconds(h=52, m=6, s=12.033)
hmsStr = dlpt.time.secToStr(durationSec, dlpt.time.TIME_FORMAT_HMS_STRING)
print(hmsStr) # will print: '52 h 6 min 12.33 sec'
```

> How do I dynamically import some module that is not on a `sys.path`?
```python
import dlpt

fPath = input("Enter a path to a python module that you wish to dynamically import: ")
importer = dlpt.importer.ModuleImporter(fPath)
print("Does module have an object with name 'myObject'? {importer.hasObject('myObject')}")
module = importer.getModule()
# call a function of this module:
module.someFunction()
```



