@echo off

CALL .\env\Scripts\activate.bat

cd docs

CALL make clean 
CALL make html
