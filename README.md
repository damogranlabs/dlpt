# dlpt
Damogran Labs Python Tools, a collection of modules with utility functions to ease everyday Python usage.  
Homepage: [https://damogranlabs.com/2021/01/dlpt/](https://damogranlabs.com/2021/01/dlpt/)  
PyPi: [https://pypi.org/project/dlpt/](https://pypi.org/project/dlpt/)  
Docs: [https://dlpt.readthedocs.io/en/latest/](https://dlpt.readthedocs.io/en/latest/)  
Install: `pip install -U dlpt`  

## Why?
This package main purpose is to stop reinventing the wheel on top of the built-in Python functions 
in every single project. Everyday struggle with:
* how do I initialize logger and add file handler?
* how do I temporary change current working directory?
* how do I get only folders inside some location?
* how do I parse JSON file with comments?
* how do I format time to string in one line?
* how do I dynamically import some module that is not on a `sys.path`?
* ...

These and many more everyday Python code questions should be covered with this library. Nothing extra,
just simplified.  
Mostly built upon standard built-in code, but with a lot more straight-forward and less cluttered API.

## What?
Paths, processes, loggers, JSON handlers, pytest fixtures, time utils, watchdog, ...
Example:
```python
import os
import time

import dlpt
import dlpt.log as log

LOG_FILE_NAME = "dlpt_example.log"

startTime = time.time()

# init default logger with console and file handler (file in <cwd>/log subfolder)
logger = log.LogHandler()
logger.addConsoleHandler()
logFilePath = logger.addFileHandler(LOG_FILE_NAME)
log.debug("Logger initialised...")

# search log file path
files = dlpt.pth.getFilesInFolderTree(os.getcwd())
for filePath in files:
    fileName = dlpt.pth.getName(filePath)
    if fileName == LOG_FILE_NAME:
        log.info(f"Log file found: {filePath}")
        break
else:
    log.error(f"Log file not found, expected in a default folder: '{log.DEFAULT_LOG_FOLDER_NAME}'")

# process example
pid = os.getpid()
executable = dlpt.proc.getExecutable(pid)
log.info(f"This process was run with python: {executable}")
args = dlpt.proc.getCmdArgs(pid)
log.info(f"\tArgs: {dlpt.utils.getListStr(args[1:])}")

# utils
endTime = time.time()
log.info(f"Example duration: {dlpt.time.secondsToString(endTime - startTime)}")

# close logger and remove log file
log.closeAllLoggers()
dlpt.pth.removeFile(logFilePath)
```




