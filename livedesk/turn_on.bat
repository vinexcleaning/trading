@echo off
REM Turns the BASEBALL desk back on. Does not touch the tennis bot.
cd /d "%~dp0"
if exist TRADING_DISABLED del TRADING_DISABLED
echo.
echo   ================================================
echo     BASEBALL desk is back ON  (livedesk)
echo   ================================================
echo.
echo   WARNING: with AUTO on, this window places REAL bets
echo   by itself. Press AUTO in the window to stop that.
echo.
echo   This did NOT change the tennis bot. That has its own
echo   switch in the kalshi-inplay-bot folder.
echo.
pause
