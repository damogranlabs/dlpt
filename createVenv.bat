@echo off

SET PY_EXE_PATH="C:\Python36\python.exe"
REM SET PY_EXE_PATH="C:\Python3.8.7\python.exe"
REM SET PY_EXE_PATH="C:\Python310\python.exe"

%PY_EXE_PATH% -m venv ./env
CALL .\env\Scripts\activate.bat

python -m pip install -U pip
pip install -r requirements.txt
pause