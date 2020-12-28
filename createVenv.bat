@echo off

SET PY_EXE_PATH=python

%PY_EXE_PATH% -m venv ./env
CALL .\env\Scripts\activate.bat

pip install -r requirements.txt
pause