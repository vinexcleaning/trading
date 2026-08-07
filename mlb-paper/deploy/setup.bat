@echo off
REM ============================================================================
REM  One-time setup on a new machine.  Creates the virtual environment,
REM  installs the two dependencies, runs the robots gate and runs the tests.
REM
REM  Run this ONCE on the laptop before install_task.ps1.
REM ============================================================================
setlocal
set "PROJ=%~dp0.."
pushd "%PROJ%"

echo [1/5] locating a real Python interpreter
REM `python` on PATH is a Microsoft Store stub on these machines and silently
REM does nothing, which is why this looks for a real interpreter first.
set "PY="
for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "C:\Python313\python.exe"
  "C:\Python312\python.exe"
) do (
  if exist %%P if not defined PY set "PY=%%~P"
)
if not defined PY (
  echo     could not find a real Python. Install Python 3.11+ from python.org
  echo     ^(NOT the Microsoft Store build^) and run this again.
  popd
  exit /b 1
)
echo     using "%PY%"

echo [2/5] creating the virtual environment
if not exist ".venv\Scripts\python.exe" "%PY%" -m venv ".venv"

echo [3/5] installing dependencies
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :fail

echo [4/5] running the robots.txt gate
".venv\Scripts\python.exe" "src\robots_check.py"
if errorlevel 1 goto :fail

echo [5/5] running the tests
".venv\Scripts\python.exe" -m pytest tests -q
if errorlevel 1 goto :fail

echo.
echo SETUP OK.  Next: right-click deploy\install_task.ps1 and
echo            "Run with PowerShell", or see deploy\README.md.
popd
exit /b 0

:fail
echo.
echo SETUP FAILED at the step above. Nothing was started.
popd
exit /b 1
