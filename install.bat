@echo off
echo ============================================================
echo Installing YfinanceDownloader Dependencies
echo ============================================================
echo.

pip install -r requirements.txt

echo.
echo Installing Playwright browser (needed for --update-screener)...
playwright install chromium

echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
pause
