@echo off
:: ============================================================
::  screen.bat - One-click stock screener
::  Double-click this file to score all stocks and find
::  today's top trade candidates.
::
::  Requires: daily_features.parquet (run generate.bat first)
:: ============================================================

echo ============================================================
echo  YfinanceDownloader - Stock Screener
echo ============================================================
echo.

cd /d "%~dp0"

if not exist "daily_features.parquet" (
    echo  ERROR: daily_features.parquet not found.
    echo  Run generate.bat first to create the features file.
    echo.
    pause
    exit /b 1
)

set /p USE_AI="Enable AI trade summaries? Requires API key in screen_config.py (Y/N): "
if /I "%USE_AI%"=="Y" (
    python screener.py --ai
) else (
    python screener.py
)

echo.
echo ============================================================
echo  Results saved to screener_results.csv
echo ============================================================
pause
