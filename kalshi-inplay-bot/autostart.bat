@echo off
REM ---------------------------------------------------------------------
REM Auto-restart after a power cut or reboot.
REM
REM Put a SHORTCUT to this file in the Startup folder:
REM     Win+R  ->  shell:startup  ->  paste a shortcut to this file
REM
REM Why: this laptop has no battery, so losing power kills the bot instantly.
REM Your positions and your resting take-profits are safe (they live on
REM Kalshi), but the STOP LOSSES run inside the app and stop existing the
REM moment it dies. This gets them back automatically instead of waiting for
REM you to notice.
REM
REM It waits for the network first, because Windows starts programs before
REM Wi-Fi is connected and the bot would just error out on its first scan.
REM ---------------------------------------------------------------------

cd /d "%~dp0"

echo Waiting for the network...
set TRIES=0
:waitloop
ping -n 2 api.elections.kalshi.com >nul 2>&1
if %ERRORLEVEL%==0 goto online
set /a TRIES+=1
if %TRIES% GEQ 30 goto giveup
timeout /t 10 /nobreak >nul
goto waitloop

:giveup
echo Network never came up after 5 minutes. Starting anyway - the bot
echo retries its own reads, so it should recover once Wi-Fi returns.

:online
echo Network is up. Starting.

REM The recorder holds a lock file, so this can never stack a second copy.
start "Kalshi RECORDER (read-only)" cmd /k python record_data.py --interval 60 --out tennis_data.jsonl
timeout /t 3 /nobreak >nul

REM CHANGED 3 Aug: comes back up in WATCH (read-only) mode, not --live.
REM
REM This file is designed to be shortcut into the Startup folder, so as
REM written it would auto-resume UNATTENDED LIVE TRADING after any reboot.
REM Combined with the 28 Jul re-entry loop (see tennis_engine.Config), that
REM meant a machine could come back from a power cut and start buying a
REM falling market on its own with nobody watching.
REM
REM Change --watch to --live ONLY as a deliberate act, and only when you
REM intend the bot to trade real money unsupervised.
start "Kalshi BOT (watch)" cmd /k python gui.py --watch --bankroll 125 --stake-pct 5

echo.
echo Both are running. This window can be closed.
timeout /t 10
