@echo off
REM Stops the BASEBALL desk only. One file, no code change, no restart.
REM The tennis bot has its own separate switch in kalshi-inplay-bot and this
REM does not touch it.
cd /d "%~dp0"
echo TURNED OFF by turn_off.bat on %DATE% %TIME% > TRADING_DISABLED
echo.
echo   ================================================
echo     BASEBALL desk is now OFF  (livedesk)
echo   ================================================
echo.
echo   It will not place any bet until you run turn_on.bat.
echo.
echo   This did NOT change the tennis bot. That has its own
echo   switch in the kalshi-inplay-bot folder.
echo.
pause
