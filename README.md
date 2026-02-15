# YfinanceDownloader

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![yfinance](https://img.shields.io/badge/data-Yahoo%20Finance-purple.svg)](https://pypi.org/project/yfinance/)

> **Bulk-download daily & hourly OHLCV stock data for every NASDAQ-listed ticker — filtered by price range, kept in sync, and ready for analysis.**

A command-line Python tool that downloads historical **Open, High, Low, Close, Volume** (OHLCV) data from Yahoo Finance for all stocks on the NASDAQ exchange. It maintains a local CSV database of daily and hourly prices that stays automatically synchronized with current NASDAQ listings — new IPOs get added, delisted stocks get removed, and your data stays up to date with a single command.

---

## Why Use This?

| Problem | Solution |
|---|---|
| Manually downloading price data for hundreds of stocks | One command downloads **all** NASDAQ stocks in your price range |
| Data goes stale after a few days | `--update` fetches only new rows since your last download |
| Companies get delisted or change tickers | `--reconcile` syncs your dataset with the latest NASDAQ screener |
| API rate limits cause failures | Built-in batching & pauses keep downloads reliable |
| Need both daily and intraday data | Downloads **daily** and **hourly** OHLCV in parallel |

---

## Features

- **Bulk OHLCV Downloads** — Daily & hourly candlestick data for 1,000+ stocks at once
- **Price Range Filtering** — Only download stocks within a configurable price range (default: $2–$200)
- **Smart Reconciliation** — Automatically adds new IPOs and removes delisted tickers
- **Incremental Updates** — Appends only new data since your last download (no re-downloading)
- **Rate Limiting** — Built-in batching and pauses to respect Yahoo Finance's API
- **Dry Run Mode** — Preview every change before committing
- **Ticker Filtering** — Excludes warrants, options, and other non-standard symbols
- **Clean CSV Output** — Ready to load into pandas, R, Excel, or any analysis tool

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/natedoggzCD/YfinanceDownloader.git
cd YfinanceDownloader
pip install -r requirements.txt
```

### 2. Get the NASDAQ Screener

1. Go to https://www.nasdaq.com/market-activity/stocks/screener
2. Click **Download CSV**
3. Save as `nasdaq_screener.csv` in the project folder

### 3. Download Everything

```bash
python downloader.py --init
```

That's it — you'll have `prices_daily.csv` and `prices_hourly.csv` with OHLCV data for every qualifying stock.

### 4. Keep It Updated

```bash
# Fetch the latest bars since your last download
python downloader.py --update

# Sync with current NASDAQ listings (add new IPOs, drop delisted)
python downloader.py --reconcile

# Or do everything at once
python downloader.py --all
```

---

## Usage

```
python downloader.py [OPTIONS]

Options:
  --init        Initial download of all NASDAQ stocks in your price range
  --update      Append new data since the last download
  --reconcile   Sync tickers with the current NASDAQ screener
  --all         Run reconcile + update (+ init if no data exists)
  --dry-run     Preview changes without downloading anything
  --tickers     Process only specific tickers (e.g. --tickers AAPL MSFT TSLA)
```

### Examples

```bash
# First-time setup — download everything
python downloader.py --init

# Daily maintenance — grab new bars
python downloader.py --update

# Weekly maintenance — sync listings + update
python downloader.py --all

# Preview what would change
python downloader.py --all --dry-run

# Update only specific stocks
python downloader.py --update --tickers AAPL MSFT GOOGL AMZN TSLA
```

---

## Configuration

All settings live in [`config.py`](config.py):

| Setting | Default | Description |
|---------|---------|-------------|
| `MIN_PRICE` | `2.0` | Minimum stock price to include ($) |
| `MAX_PRICE` | `200.0` | Maximum stock price to include ($) |
| `START_DATE` | `"2018-01-02"` | How far back to download daily data |
| `END_DATE` | `None` | End date (`None` = today) |
| `DAILY_CSV` | `"prices_daily.csv"` | Output file for daily OHLCV |
| `HOURLY_CSV` | `"prices_hourly.csv"` | Output file for hourly OHLCV |
| `BATCH_SIZE` | `50` | Tickers per download batch |
| `PAUSE_AFTER_BATCHES` | `500` | API calls before pausing |
| `PAUSE_DURATION_SECONDS` | `60` | Pause duration in seconds |

**Example — Penny Stocks:**
```python
MIN_PRICE = 0.5
MAX_PRICE = 5.0
START_DATE = "2020-01-01"
```

**Example — Large Caps:**
```python
MIN_PRICE = 50.0
MAX_PRICE = 500.0
START_DATE = "2015-01-01"
```

---

## Output Data Format

### `prices_daily.csv`

| Column | Description |
|--------|-------------|
| ticker | Stock symbol |
| interval | `daily` |
| Date | Trading date (`YYYY-MM-DD`) |
| Adj Close | Adjusted closing price |
| Close | Raw closing price |
| High | Intraday high |
| Low | Intraday low |
| Open | Opening price |
| Volume | Shares traded |

```csv
ticker,interval,Date,Adj Close,Close,High,Low,Open,Volume
AAPL,daily,2020-01-02,74.095,74.39,75.145,73.85,74.06,135480400
AAPL,daily,2020-01-03,73.425,73.44,74.98,73.19,74.29,146322800
```

### `prices_hourly.csv`

Same columns as daily, but with `Datetime` (UTC, ISO 8601) instead of `Date`:

```csv
ticker,interval,Datetime,Adj Close,Close,High,Low,Open,Volume
AAPL,hourly,2023-11-13 14:30:00+00:00,190.5,190.5,191.2,189.8,190.1,12500000
```

> **Note:** Hourly data is limited to the last ~700 days due to Yahoo Finance API restrictions.

---

## How Reconciliation Works

```
NASDAQ Screener ──► Filter by price range ──► Compare with local CSVs
                                                    │
                                          ┌─────────┴─────────┐
                                          ▼                   ▼
                                     New tickers         Missing tickers
                                     (download)           (remove rows)
```

1. Loads the latest `nasdaq_screener.csv` and filters by your price range
2. Compares against tickers already in your CSV files
3. **Removes** rows for delisted / renamed / out-of-range stocks
4. **Downloads** full history for any new additions

Run `--reconcile` weekly to keep your dataset current.

---

## Rate Limiting

The tool is designed to be respectful to Yahoo Finance's API:

- Downloads in batches of 50 tickers
- Pauses for 60 seconds after every 500 API calls
- Uses single-threaded downloads

> **Do not disable rate limiting** — aggressive downloading will likely result in IP blocking.

---

## Project Structure

```
YfinanceDownloader/
├── downloader.py        # Main script — all download/update/reconcile logic
├── config.py            # User-configurable settings
├── nasdaq_screener.csv  # NASDAQ stock listing (you download this)
├── requirements.txt     # Python dependencies
├── EXAMPLES.md          # Additional usage examples
├── LICENSE              # MIT License
└── README.md
```

---

## Requirements

- **Python** 3.8+
- **pandas** >= 1.5.0
- **yfinance** >= 0.2.0
- **numpy** >= 1.21.0

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `NASDAQ screener file not found` | Download it from [nasdaq.com/market-activity/stocks/screener](https://www.nasdaq.com/market-activity/stocks/screener) |
| No data returned for a ticker | The stock may be delisted or have no trading history — it will be skipped |
| Rate limit / connection errors | Increase `PAUSE_DURATION_SECONDS` in `config.py` |
| Column mismatch after yfinance update | Check `format_daily_data()` / `format_hourly_data()` column mappings |

---

## Contributing

Pull requests are welcome! Please ensure:
- Code follows the existing style
- Rate limiting is preserved
- New settings are added to `config.py`

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

## Disclaimer

This tool is for **educational and research purposes**. Stock data is sourced from Yahoo Finance via the [`yfinance`](https://pypi.org/project/yfinance/) library. Always verify data accuracy before making financial decisions. Please respect Yahoo Finance's terms of service.
