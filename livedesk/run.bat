@echo off
REM Open the baseball desk with auto-execution enabled.
REM Bets are placed automatically via Kalshi's PRODUCTION environment.
REM Toggle auto-exec with the AUTO button in the window.
cd /d "%~dp0"
set KALSHI_KEY_ID=950b93d7-d7c1-4128-b487-1d03dc4406e9
set "KALSHI_KEY_PATH=C:\Users\vinig\trading\kalshi-keys\MLB Bot.pem"
py -3 src\desk.py
pause
