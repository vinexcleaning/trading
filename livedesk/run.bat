@echo off
REM Open the baseball desk. Nothing here can send an order.
cd /d "%~dp0"
py -3 src\desk.py
pause
