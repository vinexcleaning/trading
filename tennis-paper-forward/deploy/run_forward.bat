@echo off
REM ===================================================================
REM  run_forward.bat - the laptop wrapper.
REM
REM  PAPER ONLY. This starts a process that cannot place an order:
REM  no credentials, no order endpoint, GET-only host allowlist.
REM
REM  Safe to run every few minutes from Task Scheduler. If a runner is
REM  already alive it exits immediately - the lock file in data\ is
REM  checked against a live process id, so this doubles as a watchdog
REM  that restarts the runner after a crash or a reboot and does
REM  nothing at all the rest of the time.
REM
REM  IT TOUCHES NOTHING ELSE ON THE MACHINE. It starts no other
REM  process, stops no process, and writes only inside this folder.
REM  The two recorders on this laptop are not referenced anywhere in
REM  this file or in the code it runs.
REM ===================================================================
setlocal

set "HERE=%~dp0"
set "PROJ=%HERE%.."
set "PY=%PROJ%\.venv\Scripts\python.exe"
set "LOGDIR=%PROJ%\logs"

if not exist "%PY%" (
  echo [run_forward] no interpreter at %PY%
  echo [run_forward] create it with:  python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
  exit /b 2
)

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM Refuse to inherit live Kalshi credentials into a paper process. The code
REM refuses too; this just fails faster and more visibly.
set "KALSHI_KEY_ID="
set "KALSHI_KEY_PATH="
set "KALSHI_API_KEY="
set "KALSHI_PRIVATE_KEY="

cd /d "%PROJ%"
echo [run_forward] %DATE% %TIME% starting >> "%LOGDIR%\wrapper.log"
"%PY%" -m src.forward --poll 60 --target 50 >> "%LOGDIR%\wrapper.log" 2>&1
set RC=%ERRORLEVEL%
echo [run_forward] %DATE% %TIME% exited rc=%RC% >> "%LOGDIR%\wrapper.log"
exit /b %RC%
