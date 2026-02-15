@echo off
:: ============================================================
::  daily.bat — One-click daily OHLCV data update
::  Double-click this file (or run from Task Scheduler) to
::  pull the latest stock prices into your local CSVs.
:: ============================================================

echo ============================================================
echo  YfinanceDownloader — Daily Update
echo ============================================================
echo.

cd /d "%~dp0"
python downloader.py --update

echo.
echo ============================================================
echo  Done!
echo ============================================================
pause
