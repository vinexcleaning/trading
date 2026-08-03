@echo off
REM Starts the recorder, the paper bot, and the trading bot in separate
REM windows. None blocks the others, and closing one leaves the rest running.
REM
REM   run_both.bat            read-only trading window + recording + paper
REM   run_both.bat live       LIVE trading + recording + paper trading
REM
REM Only gui.py can place orders. The recorder and the paper bot both hold
REM read-only clients and cannot trade, whichever mode you pick.

cd /d "%~dp0"

REM The recorder refuses to start if one is already running (it holds a lock
REM file), so re-running this bat will NOT stack a second recorder. It will
REM just say so and close.
REM 20s, not 60s: a break of serve moves these markets ~20c, and at 60s the
REM whole reaction was over before the next snapshot landed.
echo Starting the data recorder in its own window...
start "Kalshi RECORDER (read-only)" cmd /k python record_data.py --interval 20 --out tennis_data.jsonl

REM Give it a moment so the windows don't fight over the console
timeout /t 2 /nobreak >nul

REM Paper bot: every strategy, side by side, on the same live markets, with
REM no money involved. Its history lives in paper_trades.jsonl.
echo Starting the paper bot in its own window...
start "Kalshi PAPER (no money)" cmd /k python paper_bot.py --interval 45

timeout /t 2 /nobreak >nul

REM CHANGED 3 Aug: the DEFAULT is now watch. You must ask for live by name.
REM   run_both.bat           recorder + paper + read-only trading window
REM   run_both.bat live      recorder + paper + REAL MONEY
if /i "%~1"=="live" (
    echo Starting the bot in LIVE mode ^(REAL MONEY^)...
    start "Kalshi BOT (LIVE)" cmd /k python gui.py --live --bankroll 125 --stake-pct 5
) else (
    echo Starting the bot in WATCH mode ^(no orders^)...
    start "Kalshi BOT (watch)" cmd /k python gui.py --watch --bankroll 125 --stake-pct 5
)

echo.
echo Three windows are up. Close this one - it is not needed.
echo.
echo   Compare every strategy, in any NEW window:
echo     python paper_bot.py --summary
echo.
echo   See what the recorder has collected:
echo     python record_data.py --summary tennis_data.jsonl
echo.
pause
