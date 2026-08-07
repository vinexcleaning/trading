@echo off
REM ============================================================================
REM  mlb-paper -- the unattended runner.  PAPER ONLY.  No keys, no orders.
REM
REM  Started by the Windows scheduled task "mlb-paper" (see install_task.ps1),
REM  and safe to double-click by hand.  Only one copy can run: the runner takes
REM  a PID lock and a second copy exits immediately rather than doubling every
REM  decision.
REM ============================================================================
setlocal

REM this file lives in <repo>\mlb-paper\deploy\, so the project is one up
set "PROJ=%~dp0.."
pushd "%PROJ%"

if not exist ".venv\Scripts\python.exe" (
  echo [mlb-paper] no virtual environment found at "%PROJ%\.venv".
  echo [mlb-paper] run deploy\setup.bat first.
  popd
  exit /b 1
)

if not exist "reports\robots_policy.json" (
  echo [mlb-paper] robots gate has not been run. Running it now.
  ".venv\Scripts\python.exe" "src\robots_check.py"
  if errorlevel 1 (
    echo [mlb-paper] robots gate FAILED. Refusing to fetch anything.
    popd
    exit /b 1
  )
)

if not exist "logs" mkdir "logs"
echo [mlb-paper] starting runner at %DATE% %TIME%
".venv\Scripts\python.exe" "src\run.py" %*
set RC=%ERRORLEVEL%
echo [mlb-paper] runner exited with %RC% at %DATE% %TIME%
popd
exit /b %RC%
