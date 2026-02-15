@echo off
:: ============================================================
::  generate.bat - One-click feature engineering
::  Double-click this file to generate daily_features.parquet
::  from your prices_daily.csv data.
:: ============================================================

echo ============================================================
echo  YfinanceDownloader - Feature Generation
echo ============================================================
echo.

cd /d "%~dp0"
python generate.py

echo.
echo ============================================================
echo  Done!
echo ============================================================
pause
