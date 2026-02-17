@echo off
REM ============================================================
REM YfinanceDownloader - Python Setup & Dependency Installer
REM ============================================================
REM This script checks for Python, installs it if missing,
REM and then installs all required Python packages.
REM ============================================================

echo.
echo ============================================================
echo YfinanceDownloader - Python Setup
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python is already installed.
    python --version
    echo.
    goto :install_packages
)

echo [!] Python is not installed on this system.
echo.
echo This script will download and install Python 3.11.7 for you.
echo.
echo Press any key to continue or close this window to cancel...
pause >nul

echo.
echo ============================================================
echo Downloading Python Installer...
echo ============================================================
echo.

REM Set Python version to download
set PYTHON_VERSION=3.11.7
set INSTALLER_NAME=python-%PYTHON_VERSION%-amd64.exe
set DOWNLOAD_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%INSTALLER_NAME%

REM Download Python installer using PowerShell
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%TEMP%\%INSTALLER_NAME%'}"

if %errorlevel% neq 0 (
    echo [ERROR] Failed to download Python installer.
    echo Please download Python manually from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Download complete.
echo.
echo ============================================================
echo Installing Python...
echo ============================================================
echo.
echo This may take a few minutes. Please wait...
echo.

REM Install Python silently with:
REM - Add to PATH
REM - Install pip
REM - Install to default location
REM - No progress UI
"%TEMP%\%INSTALLER_NAME%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0

if %errorlevel% neq 0 (
    echo [ERROR] Python installation failed.
    pause
    exit /b 1
)

echo [OK] Python installation complete.
echo.

REM Clean up installer
del "%TEMP%\%INSTALLER_NAME%" >nul 2>&1

REM Refresh PATH for current session
echo Refreshing environment variables...
call refreshenv >nul 2>&1

REM Alternative method to refresh PATH if refreshenv is not available
for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%a %%b"
for /f "skip=2 tokens=3*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYSTEM_PATH=%%a %%b"
set "PATH=%USER_PATH%;%SYSTEM_PATH%"

echo.
echo ============================================================
echo Verifying Python Installation...
echo ============================================================
echo.

REM Verify Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Python was installed but is not yet available in PATH.
    echo Please close this window and run this script again, or restart your computer.
    pause
    exit /b 1
)

python --version
echo [OK] Python is now available!
echo.

:install_packages
echo ============================================================
echo Installing YfinanceDownloader Dependencies...
echo ============================================================
echo.

REM Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing required packages from requirements.txt...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install some dependencies.
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo Python and all dependencies are now installed.
echo You can now run:
echo   - daily.bat       (to download stock data)
echo   - generate.bat    (to generate features)
echo.
echo Press any key to exit...
pause >nul
