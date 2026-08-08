@echo off
REM ---------------------------------------------------------------------------
REM  THE ONE COMMAND.  Double-click it, or run:  coordinator\start.bat
REM
REM  It only reads. It changes no project file, makes no network call, holds no
REM  credential, and cannot place a trade. See coordinator\COORDINATOR.md --
REM  section 3 and 3b are the list of what it CANNOT do, and they are the
REM  honest half of the design.
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

REM --- 1. WHERE IS EVERYTHING AT.  The answer most of the time. -------------
echo.
%PY% coordinator\where.py
echo.

REM --- 2. Every background test, one by one. --------------------------------
echo.
%PY% coordinator\runners.py
echo.

REM --- 3. Anything else a human should look at, from git and the filesystem.
echo ===========================================================================
%PY% coordinator\scan.py
echo ===========================================================================
echo.

REM --- 4. The brief, and the one address to paste out. ----------------------
echo --- BRIEF.md ---
%PY% coordinator\brief.py check
%PY% coordinator\brief.py list
echo.
%PY% coordinator\brief.py chain
echo.

REM --- 5. Instructions nobody has answered. ---------------------------------
echo --- Instructions still waiting for an answer ---
%PY% coordinator\mail.py open
echo.

echo ---------------------------------------------------------------------------
echo   Full detail:  coordinator\WHERE.md  and  coordinator\SCAN.md
echo.
echo   To send an instruction to one chat, or to turn a new idea into a
echo   prompt for a fresh session, just say so in plain English in this
echo   window. You never type the commands yourself.
echo ---------------------------------------------------------------------------
echo.
endlocal
