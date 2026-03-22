# YfinanceDownloader

Download NASDAQ stock data from Yahoo Finance, generate daily features, rank trade candidates, and optionally place Alpaca paper trades.

## Workflow

1. Step 1 downloads or updates `data/prices_daily.csv` and `data/prices_hourly.csv`.
2. Step 2 builds `data/daily_features.parquet`.
3. Step 3 scores the universe into `data/screener_results.csv`.
4. Step 4 optionally places Alpaca trades from the screener output.

## Configuration

The active config file is `config/config.yaml`.

- The GUI setup wizard reads and writes `config/config.yaml`.
- `downloader.py`, `generate.py`, `screener.py`, and `trader.py` all use `config/config.yaml`.
- Legacy `config/config.py` is still accepted as a fallback for downloader settings, but it is only kept for migration. New changes should go into `config/config.yaml`.

Start from `config/config.example.yaml` if you want to create the file manually.

## GUI

Launch the GUI with:

```bat
run_gui.bat
```

The GUI gives you a four-step workflow:

- Step 1: Download and reconcile price data
- Step 2: Generate features
- Step 3: Run the screener
- Step 4: Preview or place Alpaca trades

If `config/config.yaml` does not exist, the GUI setup wizard will create it. If only a legacy `config/config.py` exists, the GUI will use those values as the starting point instead of forcing example defaults.

## Quick Start

### Windows batch flow

```bat
install.bat
run_gui.bat
```

Or run the batch files directly:

```bat
daily.bat
generate.bat
screen.bat
trade.bat
```

### Command line

```bash
python src/downloader.py --all
python src/generate.py
python src/screener.py
python src/trader.py --dry-run
```

## Downloader behavior

- The NASDAQ screener refresh now uses Nasdaq's screener API directly, with browser automation only as a fallback.
- Update runs backfill stale tickers instead of permanently skipping them.
- Hourly backfills are capped to Yahoo Finance's approximate 729-day limit.
- Reconcile uses the price range from `config/config.yaml`, so your universe size depends on `data.min_price` and `data.max_price`.

## Common commands

```bash
python src/downloader.py --all
python src/downloader.py --all --dry-run
python src/downloader.py --update-screener
python src/downloader.py --update --tickers AAPL MSFT NVDA

python src/generate.py

python src/screener.py --top 20
python src/screener.py --scan momentum
python src/screener.py --ai

python src/trader.py --dry-run
python src/trader.py --status
```

## Important files

```text
YfinanceDownloader/
├── config/
│   ├── config.example.yaml
│   ├── config.py              # legacy fallback only
│   └── config.yaml            # active local config
├── data/
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
├── run_gui.bat
├── screen.bat
├── trade.bat
└── requirements.txt
```

## Notes

- `config/config.yaml` is gitignored.
- `data/*.csv` and generated outputs are gitignored.
- Alpaca API keys belong in `config/config.yaml` under `trading`.

## Troubleshooting

- If the price range shown by the downloader is wrong, check `config/config.yaml`.
- If the GUI appears with defaults you did not expect, open `Settings` and save once to migrate any legacy values into `config/config.yaml`.
- If the screener refresh fails, rerun Step 1. The updater now prefers Nasdaq's API and should no longer depend on fragile page navigation.
