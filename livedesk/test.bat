@echo off
REM Must run in THIS venv: the button-position test needs a working Tcl, and
REM mlb-paper's venv has none, so there it silently SKIPS the one test that
REM matters most.
cd /d "%~dp0"
.venv\Scripts\python.exe -m pytest tests -q -rs
pause
