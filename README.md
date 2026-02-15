<div align="center">

# 📈 YfinanceDownloader

**Bulk-download daily & hourly OHLCV stock data for every NASDAQ-listed ticker, then generate ML-ready technical features.**

Filtered by price range · Incrementally updated · Synced with current listings · Feature engineering built in

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![yfinance](https://img.shields.io/badge/data_source-Yahoo_Finance-7B1FA2?style=for-the-badge)](https://pypi.org/project/yfinance/)

</div>

---

A command-line Python tool that downloads historical **Open, High, Low, Close, Volume** (OHLCV) data from Yahoo Finance for all stocks on the NASDAQ exchange. It maintains local CSV files of daily and hourly prices that stay automatically synchronized with current NASDAQ listings — new IPOs get added, delisted stocks get removed, and your data stays up to date with a single command or a double-click of `daily.bat`.

It also includes a **feature engineering pipeline** (`generate.py`) that computes 60+ technical indicators, lag features, and rolling statistics from the daily data and saves the result to a compact HDF5 file ready for ML or analysis.

---

## ⚡ Quick Start

```bash
git clone https://github.com/natedoggzCD/YfinanceDownloader.git
cd YfinanceDownloader
pip install -r requirements.txt
cp config.example.py config.py   # Create your local config
```

1. Download the NASDAQ screener CSV from [nasdaq.com/market-activity/stocks/screener](https://www.nasdaq.com/market-activity/stocks/screener) and save it as `nasdaq_screener.csv` in the project folder.
2. Edit `config.py` to set your preferred price range and settings.
3. **Double-click `daily.bat`** (Windows) — or run `python downloader.py --all` from a terminal.

That's it. On the first run it downloads all historical data; on every run after that it only fetches new bars. The output files `prices_daily.csv` and `prices_hourly.csv` are created automatically.

> **Note:** The first run downloads 1,000+ stocks and takes several hours due to rate limiting. Every run after that is fast.

---

## 🔄 Keeping Data Updated

| Method | How | Best for |
|--------|-----|----------|
| **`daily.bat`** | Double-click the file | Easiest — no terminal needed (Windows) |
| **`generate.bat`** | Double-click the file | Generate features after updating (Windows) |
| `python downloader.py --all` | Run from terminal | Cross-platform, same as daily.bat |
| `python downloader.py --update` | Run from terminal | Quick update only (skip reconciliation) |

`daily.bat` runs `python downloader.py --all` under the hood, which:
1. **Initializes** data if no CSVs exist yet (first run)
2. **Reconciles** tickers with the NASDAQ screener (adds new IPOs, removes delisted)
3. **Updates** your CSVs with the latest price bars

Just double-click it daily and your data stays current.

---

## 🛠️ All Commands

| Command | What it does |
|---------|-------------|
| `python downloader.py --init` | First-time download of all NASDAQ stocks in your price range |
| `python downloader.py --update` | Append new bars since the last download |
| `python downloader.py --reconcile` | Add new IPOs, remove delisted tickers from your CSVs |
| `python downloader.py --all` | Reconcile + update (+ init if no data exists yet) |
| `python downloader.py --dry-run` | Preview changes without downloading anything |
| `python downloader.py --tickers AAPL MSFT` | Process only specific tickers |
| `python generate.py` | Generate technical features → `daily_features.parquet` |
| **`daily.bat`** | **One-click wrapper** — runs `--all` (Windows) |
| **`generate.bat`** | **One-click wrapper** — runs `generate.py` (Windows) |

### Examples

```bash
# Preview what would change before committing
python downloader.py --all --dry-run

# Update only specific stocks
python downloader.py --update --tickers AAPL MSFT GOOGL AMZN TSLA

# Weekly maintenance — sync NASDAQ listings + pull new data
python downloader.py --all
```

---

## ⚙️ Configuration

All settings live in [`config.py`](config.example.py) (copy from `config.example.py`) — edit to match your needs:

```python
# Price range filter
MIN_PRICE = 2.0          # Minimum stock price ($)
MAX_PRICE = 200.0        # Maximum stock price ($)

# How far back to download
START_DATE = "2018-01-02"
END_DATE = None           # None = today

# Robustness
MAX_RETRIES = 3           # Retry failed downloads
RETRY_BACKOFF_SECONDS = 5 # Exponential backoff base
STALE_TICKER_DAYS = 5     # Auto-skip tickers stale > N days

# Output files
DAILY_CSV = "prices_daily.csv"
HOURLY_CSV = "prices_hourly.csv"
```

<details>
<summary><b>All configuration options</b></summary>

| Setting | Default | Description |
|---------|---------|-------------|
| `MIN_PRICE` | `2.0` | Minimum stock price to include ($) |
| `MAX_PRICE` | `200.0` | Maximum stock price to include ($) |
| `START_DATE` | `"2018-01-02"` | Earliest date for daily data |
| `END_DATE` | `None` | End date (`None` = today) |
| `DAILY_CSV` | `"prices_daily.csv"` | Daily OHLCV output file |
| `HOURLY_CSV` | `"prices_hourly.csv"` | Hourly OHLCV output file |
| `BATCH_SIZE` | `50` | Tickers downloaded per batch |
| `PAUSE_AFTER_BATCHES` | `500` | API calls before pausing |
| `PAUSE_DURATION_SECONDS` | `60` | Pause duration (seconds) |
| `MAX_RETRIES` | `3` | Retry attempts per failed download |
| `RETRY_BACKOFF_SECONDS` | `5` | Base wait between retries (doubles each attempt) |
| `STALE_TICKER_DAYS` | `5` | Auto-skip tickers with no data in N days |

</details>

<details>
<summary><b>Example: Penny stocks only</b></summary>

```python
MIN_PRICE = 0.5
MAX_PRICE = 5.0
START_DATE = "2020-01-01"
```
</details>

<details>
<summary><b>Example: Large caps only</b></summary>

```python
MIN_PRICE = 50.0
MAX_PRICE = 500.0
START_DATE = "2015-01-01"
```
</details>

---

## 📊 Output Format

### `prices_daily.csv`

```
ticker, interval, Date,       Adj Close, Close, High,   Low,   Open,  Volume
AAPL,   daily,    2020-01-02, 74.095,    74.39, 75.145, 73.85, 74.06, 135480400
AAPL,   daily,    2020-01-03, 73.425,    73.44, 74.98,  73.19, 74.29, 146322800
```

### `prices_hourly.csv`

```
ticker, interval, Datetime,                   Adj Close, Close, High,  Low,   Open,  Volume
AAPL,   hourly,   2023-11-13 14:30:00+00:00,  190.5,     190.5, 191.2, 189.8, 190.1, 12500000
```

| Column | Description |
|--------|-------------|
| `ticker` | Stock symbol (e.g. `AAPL`) |
| `interval` | `daily` or `hourly` |
| `Date` / `Datetime` | Trading date or UTC timestamp |
| `Open` `High` `Low` `Close` | Standard OHLC prices |
| `Adj Close` | Split/dividend-adjusted close |
| `Volume` | Shares traded |

> **Note:** Hourly data is limited to the last ~700 days due to Yahoo Finance API restrictions.

---

## 🔁 How Reconciliation Works

```
NASDAQ Screener ──► Filter by price range ──► Compare with local CSVs
                                                    │
                                          ┌─────────┴─────────┐
                                          ▼                   ▼
                                     New tickers         Missing tickers
                                     (download)           (remove rows)
```

1. Loads `nasdaq_screener.csv` and filters by your price range
2. Compares against tickers already in your CSV files
3. **Removes** rows for delisted / renamed / out-of-range stocks
4. **Downloads** full history for any new additions

> **Tip:** Run `--reconcile` weekly to keep your dataset current with new IPOs and delistings.

---

## 📁 Project Structure

```
YfinanceDownloader/
├── downloader.py        # Core script — download, update, reconcile
├── generate.py          # Feature engineering → daily_features.parquet
├── config.example.py    # Configuration template (copy to config.py)
├── config.py            # Your local settings (gitignored)
├── daily.bat            # One-click daily update (Windows)
├── generate.bat         # One-click feature generation (Windows)
├── nasdaq_screener.csv  # NASDAQ stock listing (you download this)
├── requirements.txt     # Python dependencies
├── EXAMPLES.md          # Additional usage examples
├── LICENSE              # MIT License
└── README.md
```

---

## 🧪 Feature Engineering (`generate.py`)

After downloading price data, generate an HDF5 file with 60+ technical features for ML or analysis:

```bash
python generate.py
# or on Windows, just double-click:
generate.bat
```

### Options

```bash
python generate.py --input prices_daily.csv --output daily_features.parquet
python generate.py --min-obs 252        # Require 1 year of history per ticker
python generate.py --stale-days 5       # Skip tickers with no recent data
```

### Indicators Computed

| Category | Features |
|----------|----------|
| **Moving Averages** | SMA(10, 20), EMA(10, 20) |
| **Momentum** | RSI(14), MACD, Stochastic %K/%D, ROC(5, 10, 20), CCI |
| **Volatility** | ATR(5, 14), Bollinger Bands, BB width/squeeze |
| **Trend** | ADX, +DI/-DI, Ichimoku Cloud (5 components), EMA crossover |
| **Volume** | OBV, Volume SMA(20), Volume ratio, Volume ROC |
| **Derived** | ATR ratios, price-to-ATR, BB price position, distance from SMA20 |
| **Lag Features** | Close, Volume, ATR, RSI lagged 1–5 days |
| **Rolling Stats** | Rolling mean & std (5, 10, 20 day) for Close, Volume, ATR |

### Output: `daily_features.parquet`

Compressed Parquet file optimized for columnar queries:

```python
import pandas as pd
df = pd.read_parquet("daily_features.parquet")

# Query a single ticker
aapl = df[df['ticker'] == 'AAPL']
```

> **Note:** Requires `pyarrow` — included in `requirements.txt`.

---

## 🛡️ Robustness Features

## 🛡️ Robustness Features

The downloader is built for unattended daily use with several safeguards:

- **Max retries with exponential backoff** — failed downloads retry up to 3 times (5s → 10s → 20s wait)
- **Stale ticker auto-skip** — tickers with no data in 5+ days are skipped during updates (configurable)
- **Detailed failure reporting** — failed and stale tickers are listed at the end of each run
- **Rate limiting** — downloads in batches of 50, pauses 60s after 500 API calls
- **Single-threaded** — avoids triggering Yahoo Finance IP blocks

> ⚠️ **Do not disable rate limiting** — aggressive downloading will result in IP blocking.

---

## ❓ Troubleshooting

| Issue | Fix |
|-------|-----|
| `NASDAQ screener file not found` | Download it from [nasdaq.com/market-activity/stocks/screener](https://www.nasdaq.com/market-activity/stocks/screener) |
| No data returned for a ticker | Stock may be delisted or have no history — it gets skipped automatically |
| Rate limit / connection errors | Increase `PAUSE_DURATION_SECONDS` in `config.py` |
| Column mismatch after yfinance update | Check `format_daily_data()` / `format_hourly_data()` column mappings |

---

## 🤝 Contributing

Pull requests are welcome! Please ensure:
- Code follows the existing style
- Rate limiting is preserved
- New settings are added to `config.py`

---

## 📄 License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">

**Built with** [yfinance](https://pypi.org/project/yfinance/) **·** Data sourced from Yahoo Finance

*For educational and research purposes. Always verify data accuracy before making financial decisions.*

</div>
