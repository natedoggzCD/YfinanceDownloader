@echo off
title YfinanceDownloader - Trader
echo.
echo ============================================================
echo   YFINANCE TRADER - Alpaca Paper / Live Execution
echo ============================================================
echo.

:: Check for trade_config.py
if not exist trade_config.py (
    echo   trade_config.py not found!
    echo.
    echo   FIRST-TIME SETUP:
    echo   1. Copy trade_config.example.py to trade_config.py
    echo   2. Sign up at https://app.alpaca.markets/signup  (free)
    echo   3. Go to Paper Trading ^> API Keys ^> Generate New Key
    echo   4. Paste your API Key and Secret Key into trade_config.py
    echo.
    echo   Then run this batch file again.
    echo.
    copy trade_config.example.py trade_config.py >nul 2>&1
    echo   (Created trade_config.py for you - just add your keys)
    echo.
    pause
    exit /b
)

:: Check for screener results
if not exist screener_results.csv (
    echo   No screener_results.csv found.
    echo   Run the screener first: double-click screen.bat
    echo.
    pause
    exit /b
)

:: Ask what to do
echo   What would you like to do?
echo.
echo   [1] Preview trades (dry run - no orders placed)
echo   [2] Execute trades (paper trading)
echo   [3] View account status and positions
echo.
set /p choice="  Enter 1, 2, or 3: "

if "%choice%"=="1" (
    echo.
    python trader.py --dry-run
) else if "%choice%"=="2" (
    echo.
    python trader.py
) else if "%choice%"=="3" (
    echo.
    python trader.py --status
) else (
    echo.
    echo   Invalid choice.
)

echo.
pause
