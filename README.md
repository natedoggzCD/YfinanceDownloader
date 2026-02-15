<div align="center">

# 📈 YfinanceDownloader

**Bulk-download daily & hourly OHLCV stock data for every NASDAQ-listed ticker.**

Filtered by price range · Incrementally updated · Synced with current listings · Ready for analysis

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![yfinance](https://img.shields.io/badge/data_source-Yahoo_Finance-7B1FA2?style=for-the-badge)](https://pypi.org/project/yfinance/)

</div>

---

A command-line Python tool that downloads historical **Open, High, Low, Close, Volume** (OHLCV) data from Yahoo Finance for all stocks on the NASDAQ exchange. It maintains local CSV files of daily and hourly prices that stay automatically synchronized with current NASDAQ listings — new IPOs get added, delisted stocks get removed, and your data stays up to date with a single command or a double-click of `daily.bat`.

---

## ⚡ Quick Start

```bash
git clone https://github.com/natedoggzCD/YfinanceDownloader.git
cd YfinanceDownloader
pip install -r requirements.txt
```

1. Download the NASDAQ screener CSV from [nasdaq.com/market-activity/stocks/screener](https://www.nasdaq.com/market-activity/stocks/screener) and save it as `nasdaq_screener.csv` in the project folder.
2. Run the initial download:

```bash
python downloader.py --init
```

That's it — `prices_daily.csv` and `prices_hourly.csv` will be created with OHLCV data for every qualifying stock.

> **Note:** Initial download of 1,000+ stocks takes several hours due to rate limiting.

---

## 🔄 Daily Updates

The easiest way to keep your data current:

### Option A — Double-click the batch file (Windows)

Just double-click **`daily.bat`**. It runs `--update` automatically and pulls the latest bars into your CSVs.

### Option B — Command line

```bash
python downloader.py --update
```

### Option C — Full maintenance

```bash
# Sync listings + update data in one shot
python downloader.py --all
```

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
| **`daily.bat`** | **One-click wrapper** — runs `--update` (Windows) |

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

All settings live in [`config.py`](config.py) — edit to match your needs:

```python
# Price range filter
MIN_PRICE = 2.0          # Minimum stock price ($)
MAX_PRICE = 200.0        # Maximum stock price ($)

# How far back to download
START_DATE = "2018-01-02"
END_DATE = None           # None = today

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
├── config.py            # All user-configurable settings
├── daily.bat            # One-click daily update (Windows)
├── nasdaq_screener.csv  # NASDAQ stock listing (you download this)
├── requirements.txt     # Python dependencies
├── EXAMPLES.md          # Additional usage examples
├── LICENSE              # MIT License
└── README.md
```

---

## 🚦 Rate Limiting

The tool respects Yahoo Finance's API with built-in safeguards:

- Downloads in batches of **50 tickers**
- Pauses **60 seconds** after every **500 API calls**
- Single-threaded to avoid triggering blocks

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
