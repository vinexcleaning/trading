@echo off
REM ---------------------------------------------------------------------------
REM  THE DICTATOR CHAT -- the one command.
REM
REM  Two layers, always. The table first, because it is the answer to the
REM  question you usually have. Then plain English underneath: what each chat
REM  tried, on what data, from when, and what came out.
REM
REM  It only reads. It changes no project file, makes no network call, holds no
REM  credential, and cannot place a trade. What it CANNOT do is written down
REM  first, in DICTATOR.md section 1. Read that before trusting a cell.
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

REM --- LAYER 1.  The table. --------------------------------------------------
echo.
%PY% coordinator\where.py
echo.

REM --- Is each background test still producing anything. ---------------------
%PY% coordinator\runners.py
echo.

REM --- LAYER 2.  What each chat has actually tried, in plain English. --------
%PY% coordinator\detail.py
echo.

REM --- The names, and whether the two lists of chats still agree. ------------
%PY% coordinator\chats.py check
echo.

REM --- Anything else a human should look at, from git and the filesystem. ----
echo ===========================================================================
%PY% coordinator\scan.py
echo ===========================================================================
echo.

REM --- The brief, and the one address to paste out. --------------------------
echo --- BRIEF.md ---
%PY% coordinator\brief.py check
%PY% coordinator\brief.py list
echo.
%PY% coordinator\brief.py chain
echo.

REM --- Instructions nobody has answered. -------------------------------------
echo --- Instructions still waiting for an answer ---
%PY% coordinator\mail.py open
echo.

echo ---------------------------------------------------------------------------
echo   Say any of these in plain English. You never type a command:
echo.
echo     "where is everything at"          the table and the detail
echo     "tell me more about the X one"    just that chat
echo     "has anyone tried <idea>"         the prior-work check, nothing filed
echo     "new idea: <idea>"                checked, then filed to the right chat
echo     "start a new chat for <idea>"     named, with a ready prompt
echo.
echo   What this CANNOT do is written down in DICTATOR.md, section 1.
echo ---------------------------------------------------------------------------
echo.
endlocal
