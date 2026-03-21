@echo off
:: ============================================================
::  daily.bat - One-click daily OHLCV data update
::  Double-click this file (or run from Task Scheduler) to
::  pull the latest stock prices into your local CSVs.
:: ============================================================

echo ============================================================
echo  YfinanceDownloader - Daily Update
echo ============================================================
echo.

cd /d "%~dp0"

set /p UPDATE_SC="Do you want to update the NASDAQ Screener CSV file first? (Y/N): "
if /I "%UPDATE_SC%"=="Y" (
    echo.
    echo Running Screener Update...
    python downloader.py --update-screener --all
) else (
    python downloader.py --all
)

echo.
echo ============================================================
echo  Done!
echo ============================================================
pause
