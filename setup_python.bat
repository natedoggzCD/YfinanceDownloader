@echo off
setlocal EnableDelayedExpansion
REM ============================================================
REM YfinanceDownloader - Python Setup & Dependency Installer
REM ============================================================
REM This script checks for Python, installs it if missing,
REM and then installs all required Python packages.
REM ============================================================

echo.
echo ============================================================
echo  YfinanceDownloader - Python Setup
echo ============================================================
echo.

REM --- Step 1: Check if Python is already installed ---
REM Use "where" to avoid the Windows Store python.exe alias
where python >nul 2>&1
if %errorlevel% equ 0 (
    REM Verify it's a real Python and not the Store stub
    python -c "import sys; print(sys.version)" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Python is already installed:
        python -c "import sys; print(sys.version)"
        echo.
        set "PYTHON_CMD=python"
        goto :install_packages
    )
)

REM Also check "py" launcher as fallback
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -c "import sys; print(sys.version)" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Python is already installed (via py launcher):
        py -c "import sys; print(sys.version)"
        echo.
        set "PYTHON_CMD=py"
        goto :install_packages
    )
)

echo [!] Python is not installed on this system.
echo.
echo This script will download and install Python 3.11.9 for you.
echo.
echo Press any key to continue or close this window to cancel...
pause >nul

echo.
echo ============================================================
echo  Downloading Python Installer...
echo ============================================================
echo.

REM Set Python version to download
set "PYTHON_VERSION=3.11.9"
set "PYTHON_MAJOR_MINOR=311"
set "INSTALLER_NAME=python-%PYTHON_VERSION%-amd64.exe"
set "DOWNLOAD_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%INSTALLER_NAME%"
set "INSTALLER_PATH=%TEMP%\%INSTALLER_NAME%"

REM Download Python installer using PowerShell
echo Downloading from python.org (approx. 25 MB)...
echo URL: %DOWNLOAD_URL%
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%INSTALLER_PATH%' -UseBasicParsing; if (Test-Path '%INSTALLER_PATH%') { Write-Host 'Download successful.'; exit 0 } else { Write-Host 'File not found after download.'; exit 1 } } catch { Write-Host ('Download error: ' + $_.Exception.Message); exit 1 }"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to download Python installer.
    echo Please download Python manually from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Double-check the file exists and is not empty
if not exist "%INSTALLER_PATH%" (
    echo [ERROR] Installer file not found after download.
    echo Please download Python manually from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Download complete.
echo.
echo ============================================================
echo  Installing Python %PYTHON_VERSION%...
echo ============================================================
echo.
echo A progress window will appear. This takes 2-3 minutes.
echo Do NOT close this window.
echo.

REM Install Python with:
REM   /passive    = show progress bar (not fully silent)
REM   start /wait = block until installer finishes
REM   PrependPath = add python to PATH automatically
REM   Include_pip = install pip
start /wait "" "%INSTALLER_PATH%" /passive InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python installation failed (error code: %errorlevel%).
    echo.
    echo Try running the installer manually:
    echo   %INSTALLER_PATH%
    echo Or download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo [OK] Python installer finished.
echo.

REM Clean up installer
del "%INSTALLER_PATH%" >nul 2>&1

REM --- Step 2: Refresh PATH so this session can find Python ---
echo Refreshing environment PATH...

REM Read the updated PATH from the registry using PowerShell (most reliable method)
for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('PATH','Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH','User')"`) do set "PATH=%%p"

REM Fallback: also add the default Python install directories explicitly
set "PY_USER_DIR=%LOCALAPPDATA%\Programs\Python\Python%PYTHON_MAJOR_MINOR%"
set "PY_USER_SCRIPTS=%PY_USER_DIR%\Scripts"
if exist "%PY_USER_DIR%\python.exe" (
    set "PATH=%PY_USER_DIR%;%PY_USER_SCRIPTS%;%PATH%"
)

echo.
echo ============================================================
echo  Verifying Python Installation...
echo ============================================================
echo.

REM Try to find Python
set "PYTHON_CMD="

REM Check 1: "python" in PATH
where python >nul 2>&1
if %errorlevel% equ 0 (
    python -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=python"
    )
)

REM Check 2: "py" launcher
if not defined PYTHON_CMD (
    where py >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_CMD=py"
    )
)

REM Check 3: direct path to default install location
if not defined PYTHON_CMD (
    if exist "%PY_USER_DIR%\python.exe" (
        set "PYTHON_CMD=%PY_USER_DIR%\python.exe"
    )
)

if not defined PYTHON_CMD (
    echo.
    echo [ERROR] Python was installed but cannot be found.
    echo.
    echo Please restart your computer and then double-click this script again.
    echo After restarting, Windows will recognize the new PATH.
    pause
    exit /b 1
)

%PYTHON_CMD% --version
echo [OK] Python is ready!
echo.

:install_packages
echo ============================================================
echo  Installing YfinanceDownloader Dependencies...
echo ============================================================
echo.

REM Upgrade pip first (use -m pip to ensure correct pip is used)
echo Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip
echo.

echo Installing required packages from requirements.txt...
%PYTHON_CMD% -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install some dependencies.
    echo Please check the error messages above.
    pause
    exit /b 1
)

REM Copy config if it doesn't exist
if not exist "config.py" (
    if exist "config.example.py" (
        echo.
        echo Creating config.py from config.example.py...
        copy config.example.py config.py >nul
        echo [OK] config.py created. You can edit it to change settings.
    )
)

echo.
echo ============================================================
echo  Installation Complete!
echo ============================================================
echo.
echo Python and all dependencies are now installed.
echo.
echo Next steps:
echo   1. Download the NASDAQ screener CSV from:
echo      https://www.nasdaq.com/market-activity/stocks/screener
echo      and save it as nasdaq_screener.csv in this folder.
echo   2. Edit config.py to set your preferred price range.
echo   3. Double-click daily.bat to download stock data.
echo.
pause
