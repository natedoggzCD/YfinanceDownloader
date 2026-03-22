<div align="center">

# 📈 YfinanceDownloader

**Download NASDAQ stock data, generate daily features, rank trade candidates, and optionally place Alpaca trades.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![yfinance](https://img.shields.io/badge/data_source-Yahoo_Finance-7B1FA2?style=for-the-badge)](https://pypi.org/project/yfinance/)

</div>

---

This project is built around a simple four-step workflow:

```text
Step 1: Download / update market data
        data/nasdaq_screener.csv
                |
                v
        data/prices_daily.csv
        data/prices_hourly.csv

Step 2: Generate features
                |
                v
        data/daily_features.parquet

Step 3: Screen stocks
                |
                v
        data/screener_results.csv

Step 4: Trade
                |
                v
        Alpaca orders + logs/trade_log.csv
```

## Quick Start

### Windows: easiest path

1. Install Python 3.8+ from [python.org](https://www.python.org/downloads/).
2. Clone or unzip the repo.
3. Run `install.bat`.
4. Run `run_gui.bat`.
5. Use the setup wizard to create `config/config.yaml`.
6. Run Step 1, then Step 2, then Step 3, then Step 4 if you want trading enabled.

### Command line

```bash
python src/validate_setup.py
python src/downloader.py --all
python src/generate.py
python src/screener.py
python src/trader.py --dry-run
```

## Configuration

The active config file is:

```text
config/config.yaml
```

Important behavior:

- The GUI setup wizard reads and writes `config/config.yaml`.
- `downloader.py`, `generate.py`, `screener.py`, and `trader.py` all use `config/config.yaml`.
- Legacy `config/config.py` still works as a fallback for older local setups, but it is migration-only now.
- The versioned template is `config/config.example.yaml`.

If the GUI opens and you already have a legacy `config/config.py`, the wizard uses those values as the starting point instead of forcing raw example defaults.

## GUI Workflow

Launch the GUI with:

```bat
run_gui.bat
```

The GUI exposes the full pipeline:

| GUI Step | What it does |
|----------|--------------|
| **Step 1: Download Data** | Refreshes the NASDAQ screener if requested, reconciles the universe, and updates daily/hourly price CSVs |
| **Step 2: Generate Features** | Reads `data/prices_daily.csv` and writes `data/daily_features.parquet` |
| **Step 3: Screen Stocks** | Scores the feature set and writes `data/screener_results.csv` |
| **Step 4: Trade** | Uses the screener output to preview trades, place orders, or show Alpaca account status |

## Batch File Reference

### `install.bat`

Installs dependencies from `requirements.txt` and runs the health check.

### `run_gui.bat`

Starts the GUI in [src/gui.py](src/gui.py).

Use this if you want one place to manage settings and run the four-step workflow.

### `daily.bat`

Runs the downloader pipeline in [src/downloader.py](src/downloader.py).

Behavior:

1. Optionally refreshes the NASDAQ screener first
2. Reconciles your local universe against `data/nasdaq_screener.csv`
3. Updates `data/prices_daily.csv`
4. Updates `data/prices_hourly.csv`

### `generate.bat`

Runs [src/generate.py](src/generate.py) to build `data/daily_features.parquet` from `data/prices_daily.csv`.

### `screen.bat`

Runs [src/screener.py](src/screener.py) to score the current feature set.

Output:

- `data/screener_results.csv`

### `trade.bat`

Runs [src/trader.py](src/trader.py) in one of three modes:

1. Dry run
2. Execute
3. Status

It expects:

- `config/config.yaml` to exist
- `data/screener_results.csv` to exist

## Python Entry Points

### `src/downloader.py`

Purpose:

- Refreshes the NASDAQ screener
- Reconciles local tickers with the screener
- Initializes missing tickers
- Updates existing daily/hourly CSVs

Common commands:

```bash
python src/downloader.py --all
python src/downloader.py --all --dry-run
python src/downloader.py --update
python src/downloader.py --reconcile
python src/downloader.py --update-screener
python src/downloader.py --update --tickers AAPL MSFT NVDA
```

Notes:

- NASDAQ screener refresh now uses Nasdaq's screener API directly, with browser automation as a fallback.
- Stale tickers are backfilled instead of being permanently skipped.
- Hourly backfills are capped to Yahoo Finance's approximate 729-day limit.

### `src/generate.py`

Purpose:

- Reads `data/prices_daily.csv`
- Computes technical indicators and rolling features
- Writes `data/daily_features.parquet`

Common commands:

```bash
python src/generate.py
python src/generate.py --input data/prices_daily.csv --output data/daily_features.parquet
python src/generate.py --min-obs 252
python src/generate.py --stale-days 5
```

### `src/screener.py`

Purpose:

- Reads `data/daily_features.parquet`
- Applies universe filters
- Scores momentum, trend, volume, pullback, and volatility factors
- Writes ranked trade candidates to `data/screener_results.csv`

Common commands:

```bash
python src/screener.py
python src/screener.py --top 20
python src/screener.py --scan momentum
python src/screener.py --scan reversion
python src/screener.py --scan breakout
python src/screener.py --scan pullback
python src/screener.py --validate
python src/screener.py --verbose
python src/screener.py --ai
python src/screener.py --output data/my_results.csv
```

### `src/trader.py`

Purpose:

- Reads `data/screener_results.csv`
- Connects to Alpaca using the `trading` section of `config/config.yaml`
- Sizes positions using risk-based logic
- Places bracket or market orders
- Writes trade history to `logs/trade_log.csv`

Common commands:

```bash
python src/trader.py
python src/trader.py --dry-run
python src/trader.py --status
python src/trader.py --top 5
python src/trader.py --min-score 70
python src/trader.py --input data/my_results.csv
```

### `src/validate_setup.py`

Purpose:

- Checks Python dependencies
- Checks config presence
- Detects Alpaca keys
- Verifies key data files are where the project expects them

Command:

```bash
python src/validate_setup.py
```

### `src/gui.py`

Purpose:

- Single-window runner for the whole project
- Setup wizard for `config/config.yaml`
- Status and output panel for all four pipeline steps

This is what `run_gui.bat` launches.

## File Usage Guide

| File | What it is for |
|------|----------------|
| `config/config.example.yaml` | Versioned template for the project config |
| `config/config.yaml` | Your active local config |
| `config/config.py` | Legacy fallback config for migration |
| `data/nasdaq_screener.csv` | Universe source used by downloader reconcile/init |
| `data/prices_daily.csv` | Daily OHLCV dataset |
| `data/prices_hourly.csv` | Hourly OHLCV dataset |
| `data/daily_features.parquet` | Feature-engineered daily dataset |
| `data/screener_results.csv` | Ranked candidates from the screener |
| `logs/trade_log.csv` | Trade log output from the trader |
| `run_gui.bat` | Starts the GUI |
| `daily.bat` | Runs Step 1 |
| `generate.bat` | Runs Step 2 |
| `screen.bat` | Runs Step 3 |
| `trade.bat` | Runs Step 4 |

## Configuration Highlights

The most important data settings live under the `data` section in `config/config.yaml`:

```yaml
data:
  min_price: 2.0
  max_price: 200.0
  start_date: "2018-01-02"
  daily_csv: "data/prices_daily.csv"
  hourly_csv: "data/prices_hourly.csv"
  nasdaq_screener: "data/nasdaq_screener.csv"
  batch_size: 50
  stale_ticker_days: 5
  hourly_max_days: 729
```

Screener settings live under `screener`, and Alpaca/trading settings live under `trading`.

## Output Files

### `data/prices_daily.csv`

```text
ticker,interval,Date,Adj Close,Close,High,Low,Open,Volume
AAPL,daily,2026-03-20,210.15,210.15,211.40,208.30,209.10,64321000
```

### `data/prices_hourly.csv`

```text
ticker,interval,Datetime,Adj Close,Close,High,Low,Open,Volume
AAPL,hourly,2026-03-20 19:30:00+00:00,210.15,210.15,210.30,209.85,210.00,4215000
```

### `data/daily_features.parquet`

Contains generated technical indicators and lagged/rolling features used by the screener.

### `data/screener_results.csv`

Contains ranked candidates such as:

```text
ticker,Close,score,scan_type,entry_price,stop_price,target_price,risk_reward
```

## How Reconciliation Works

```text
NASDAQ screener
      |
      v
filter by configured price range
      |
      v
compare against local CSV tickers
      |
      +--> remove out-of-universe tickers
      +--> add new in-universe tickers
      +--> update existing tickers
```

When you run Step 1:

1. The project loads `data/nasdaq_screener.csv`
2. Applies your configured price range
3. Compares the resulting ticker set to the local datasets
4. Removes local rows for tickers no longer in range
5. Downloads full history for newly added tickers
6. Updates the existing ticker set with fresh bars

## Project Structure

```text
YfinanceDownloader/
├── config/
│   ├── __init__.py
│   ├── config.example.yaml
│   ├── config.py
│   └── config.yaml
├── data/
│   ├── nasdaq_screener.csv
│   ├── prices_daily.csv
│   ├── prices_hourly.csv
│   ├── daily_features.parquet
│   └── screener_results.csv
├── logs/
│   └── trade_log.csv
├── src/
│   ├── downloader.py
│   ├── generate.py
│   ├── gui.py
│   ├── screener.py
│   ├── trader.py
│   ├── update_screener.py
│   └── validate_setup.py
├── daily.bat
├── generate.bat
├── install.bat
├── run_gui.bat
├── screen.bat
├── trade.bat
├── requirements.txt
└── README.md
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Wrong price range shown in Step 1 | Check `config/config.yaml` and rerun |
| GUI shows defaults you did not expect | Open Settings in the GUI and save once to migrate legacy values |
| `data/nasdaq_screener.csv` missing | Run Step 1 with screener refresh enabled |
| Screener update fails in browser mode | Retry Step 1; the updater now prefers Nasdaq's API first |
| `data/daily_features.parquet` missing | Run Step 2 |
| `data/screener_results.csv` missing | Run Step 3 |
| Alpaca keys missing | Add them to `config/config.yaml` under `trading` |
| Hourly data stops far behind daily data | Yahoo limits hourly history to about 729 days |

## License

[MIT](LICENSE)
