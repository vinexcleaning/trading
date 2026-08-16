@echo off
REM Open the baseball desk.
REM
REM  *** THIS PLACES REAL BETS WITH REAL MONEY, AND AUTO STARTS ON. ***
REM  Press the AUTO button in the window to stop it betting by itself.
REM
REM Credentials are NOT in this file. This repo is PUBLIC.
REM They live in kalshi_env.bat, which is gitignored. If it is missing, see
REM the message below.
cd /d "%~dp0"

if not exist kalshi_env.bat (
  echo.
  echo   ================================================
  echo     NO CREDENTIALS FILE — the desk cannot trade
  echo   ================================================
  echo.
  echo   Make a file next to this one called   kalshi_env.bat
  echo   containing these two lines, with your own key id:
  echo.
  echo     set KALSHI_KEY_ID=your-key-id-here
  echo     set "KALSHI_KEY_PATH=C:\Users\vinig\trading\kalshi-keys\MLB Bot.pem"
  echo.
  echo   It is gitignored, so it never leaves this computer.
  echo   The window still opens without it — it just cannot place a bet.
  echo.
  pause
)

if exist kalshi_env.bat call kalshi_env.bat
py -3 src\desk.py
pause
