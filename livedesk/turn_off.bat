@echo off
REM Stops the desk recommending anything. One file, no code change, no restart.
cd /d "%~dp0"
echo TURNED OFF by turn_off.bat on %DATE% %TIME% > TRADING_DISABLED
echo.
echo   The desk is now OFF. The button is dead until you run turn_on.bat.
echo.
pause
