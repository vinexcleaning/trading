@echo off
REM ============================================================================
REM  THE ONE COMMAND.  Double-click this, or run it from any prompt.
REM
REM  Prints whether the runner is alive, what every bot has done, why bots
REM  declined, market health for the last twelve ticks, and the closing-line
REM  value table -- which is the primary endpoint.
REM
REM  Exit code 0 = alive, 2 = STALE (no tick in the last 20 minutes).
REM ============================================================================
setlocal
set "PROJ=%~dp0.."
pushd "%PROJ%"
".venv\Scripts\python.exe" "src\status.py" %*
set RC=%ERRORLEVEL%
popd
REM Pause only when double-clicked, so the window does not vanish. Detected
REM via cmdcmdline: a double-click runs cmd /c "...check.bat", a shell run does
REM not. The old version paused whenever %1 was empty, which made the file
REM unusable from any script or scheduled job -- it would hang forever with no
REM output. Found by running it non-interactively.
echo %cmdcmdline% | find /i "%~0" >nul
if not errorlevel 1 (
  echo.
  echo [press a key to close]
  pause >nul
)
exit /b %RC%
