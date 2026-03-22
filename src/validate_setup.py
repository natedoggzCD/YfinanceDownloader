#!/usr/bin/env python3
"""
validate_setup.py — Health check for YfinanceDownloader.

Verifies:
1. Python version and dependencies.
2. Configuration files (YAML or Python).
3. API keys for Alpaca (if enabled).
4. Data file existence.
"""

import os
import sys
import importlib
from pathlib import Path

def print_step(msg):
    print(f"\n[ ] {msg}")

def print_ok(msg):
    print(f"    SUCCESS: {msg}")

def print_err(msg):
    print(f"    ERROR: {msg}")

def print_warn(msg):
    print(f"    WARNING: {msg}")

def check_dependencies():
    print_step("Checking dependencies...")
    required = [
        "pandas", "yfinance", "numpy", "pyarrow", "yaml", "alpaca"
    ]
    missing = []
    for lib in required:
        try:
            importlib.import_module(lib if lib != "alpaca" else "alpaca.trading")
            print_ok(f"{lib} installed")
        except ImportError:
            missing.append(lib)
            print_err(f"{lib} NOT found")
    
    if missing:
        print_err(f"Missing libraries: {', '.join(missing)}")
        print("    Run: pip install -r requirements.txt")
        return False
    return True

def check_config():
    print_step("Checking configuration...")
    
    # Check for config.yaml or legacy config.py
    has_yaml = os.path.exists("config/config.yaml")
    has_py = os.path.exists("config/config.py")
    
    if not has_yaml and not has_py:
        print_err("No config/config.yaml or legacy config/config.py found.")
        print("    Action: Copy config/config.example.yaml to config/config.yaml or run run_gui.bat")
        return None
    
    if has_yaml:
        print_ok("config/config.yaml found")
        # Simple validation could go here
    elif has_py:
        print_ok("config/config.py found (legacy fallback)")
    
    return "yaml" if has_yaml else "py"

def check_alpaca(cfg_type):
    print_step("Checking Alpaca API keys...")
    
    key = ""
    secret = ""
    
    if cfg_type == "yaml":
        try:
            import yaml
            with open("config/config.yaml", "r") as f:
                raw = yaml.safe_load(f) or {}
                trading = raw.get("trading", {})
                key = trading.get("alpaca_api_key", "")
                secret = trading.get("alpaca_secret_key", "")
        except:
            pass
    else:
        try:
            from config import config
            key = getattr(config, "ALPACA_API_KEY", "")
            secret = getattr(config, "ALPACA_SECRET_KEY", "")
        except:
            pass
            
    if not key or "PK" not in str(key):
        print_warn("Alpaca API keys appear to be empty or default.")
        print("    You won't be able to run trade.bat.")
    else:
        print_ok("Alpaca API keys detected")

def check_data_files():
    print_step("Checking data files...")
    files = {
        "data/nasdaq_screener.csv": "Required for downloader.py",
        "data/prices_daily.csv": "Created by daily.bat",
        "data/daily_features.parquet": "Created by generate.bat",
        "data/screener_results.csv": "Created by screen.bat"
    }
    
    for f, desc in files.items():
        if os.path.exists(f):
            size = os.path.getsize(f) / (1024 * 1024)
            print_ok(f"{f} exists ({size:.1f} MB)")
        else:
            if f == "data/nasdaq_screener.csv":
                print_err(f"{f} MISSING. {desc}")
                print("    Download from: https://www.nasdaq.com/market-activity/stocks/screener")
            else:
                print_warn(f"{f} not yet created. {desc}")

def main():
    print("=" * 60)
    print("  YfinanceDownloader Health Check")
    print("=" * 60)
    
    deps_ok = check_dependencies()
    cfg_type = check_config()
    
    if cfg_type:
        check_alpaca(cfg_type)
    
    check_data_files()
    
    print("\n" + "=" * 60)
    if deps_ok and cfg_type:
        print("  SYSTEM READY: You are good to go!")
    else:
        print("  SYSTEM NOT READY: Please fix the errors above.")
    print("=" * 60)

if __name__ == "__main__":
    main()
