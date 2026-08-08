@echo off
REM ---------------------------------------------------------------------------
REM  THE ONE COMMAND.  Double-click it, or run:  coordinator\start.bat
REM
REM  It only reads. It changes no project file, makes no network call, holds no
REM  credential, and cannot place a trade. See coordinator\COORDINATOR.md.
REM ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0.."

set "PY="
py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined PY if exist "%CD%\mlb-paper\.venv\Scripts\python.exe" set "PY=%CD%\mlb-paper\.venv\Scripts\python.exe"
if not defined PY if exist "%CD%\tennis-paper-forward\.venv\Scripts\python.exe" set "PY=%CD%\tennis-paper-forward\.venv\Scripts\python.exe"

if not defined PY (
  echo.
  echo   Could not find a working Python on this machine.
  echo   Nothing was changed. Tell your Claude session exactly this line
  echo   and it will sort it out.
  echo.
  exit /b 1
)

echo.
echo ===========================================================================
%PY% coordinator\scan.py
echo ===========================================================================
echo.
echo --- BRIEF.md ---
%PY% coordinator\brief.py check
%PY% coordinator\brief.py list
echo.
%PY% coordinator\brief.py chain
echo.
echo --- Instructions still waiting for an answer ---
%PY% coordinator\mail.py open
echo.
echo Full detail: coordinator\SCAN.md
echo.
endlocal
