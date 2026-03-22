@echo off
title YfinanceDownloader - Trader
echo.
echo ============================================================
echo   YFINANCE TRADER - Alpaca Paper / Live Execution
echo ============================================================
echo.

cd /d "%~dp0"

:: Check for config
if not exist "config\config.yaml" (
    echo   config\config.yaml not found.
    echo.
    echo   Run run_gui.bat first, or copy config\config.example.yaml to config\config.yaml
    echo   and add your Alpaca API keys under the trading section.
    echo.
    pause
    exit /b
)

:: Check for screener results
if not exist "data\screener_results.csv" (
    echo   No data\screener_results.csv found.
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
    python src/trader.py --dry-run
) else if "%choice%"=="2" (
    echo.
    python src/trader.py
) else if "%choice%"=="3" (
    echo.
    python src/trader.py --status
) else (
    echo.
    echo   Invalid choice.
)

echo.
pause
