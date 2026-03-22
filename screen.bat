@echo off
:: ============================================================
::  screen.bat - One-click stock screener
::  Double-click this file to score all stocks and find
::  today's top trade candidates.
::
::  Requires: data\daily_features.parquet (run generate.bat first)
:: ============================================================

echo ============================================================
echo  YfinanceDownloader - Stock Screener
echo ============================================================
echo.

cd /d "%~dp0"

if not exist "data\daily_features.parquet" (
    echo  ERROR: data\daily_features.parquet not found.
    echo  Run generate.bat first to create the features file.
    echo.
    pause
    exit /b 1
)

set /p USE_AI="Enable AI trade summaries? Requires API key in config\config.yaml (Y/N): "
if /I "%USE_AI%"=="Y" (
    python src/screener.py --ai
) else (
    python src/screener.py
)

echo.
echo ============================================================
echo  Results saved to data\screener_results.csv
echo ============================================================
pause
