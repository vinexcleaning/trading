@echo off
REM Must run in THIS venv: the button-position test needs a working Tcl.
REM LIVEDESK_REQUIRE_GUI turns "no display" from a SKIP into a FAILURE, so this
REM command can never come back green with the button untested.
cd /d "%~dp0"
set LIVEDESK_REQUIRE_GUI=1
.venv\Scripts\python.exe -m pytest tests -q -rs
pause
