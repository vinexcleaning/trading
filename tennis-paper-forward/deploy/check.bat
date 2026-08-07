@echo off
REM ===================================================================
REM  check.bat - THE ONE COMMAND.
REM
REM  Double-click it, or run it from anywhere. Read-only: it starts
REM  nothing, stops nothing, and cannot place a trade.
REM
REM  It prints, in this order:
REM    1. every python process on the machine, so you can SEE the two
REM       recorders are still running before you look at anything else
REM    2. whether this forward test is alive, what it is seeing, how
REM       many matches have settled, and how long the rest will take
REM ===================================================================
setlocal
set "HERE=%~dp0"
set "PROJ=%HERE%.."
set "PY=%PROJ%\.venv\Scripts\python.exe"

echo.
echo ===========================================================================
echo  PYTHON PROCESSES ON THIS MACHINE  (the two recorders must be in this list)
echo ===========================================================================
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name like 'python%%'\" | Select-Object ProcessId, @{n='Started';e={$_.CreationDate}}, @{n='Command';e={$_.CommandLine.Substring(0,[Math]::Min(110,$_.CommandLine.Length))}} | Format-Table -AutoSize"

if not exist "%PY%" (
  echo [check] no interpreter at %PY%
  exit /b 2
)
cd /d "%PROJ%"
"%PY%" -m src.status
set RC=%ERRORLEVEL%
echo.
if %RC%==0 (echo RESULT: the forward test is running normally.) else (echo RESULT: the forward test is NOT running normally - see above.)
echo.
pause
exit /b %RC%
