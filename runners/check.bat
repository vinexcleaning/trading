@echo off
REM ===================================================================
REM  check.bat - THE ONE COMMAND, for every paper test on this machine.
REM
REM  Double-click it. Read-only: starts nothing, stops nothing, and
REM  cannot place a trade.
REM
REM  It prints every python process FIRST, so the two recorders are the
REM  first thing you see, then each registered test in its own words.
REM ===================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0status.ps1"
echo.
pause
