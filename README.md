<div align="center">

# 📈 YfinanceDownloader

**Free OHLCV stock data for the entire NASDAQ — updated daily with a double-click.**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![yfinance](https://img.shields.io/badge/data_source-Yahoo_Finance-7B1FA2?style=for-the-badge)](https://pypi.org/project/yfinance/)

</div>

---

**Accurate data is the foundation of every trading strategy, ML model, and backtest.** If your prices are stale, your listings are outdated, or your features are miscalculated, nothing built on top of that data can be trusted. YfinanceDownloader solves this by giving you a single source of truth — clean, current, and complete NASDAQ price data that stays in sync automatically.

It downloads historical **Open, High, Low, Close, Volume** (OHLCV) data from Yahoo Finance for every NASDAQ-listed stock, keeps it automatically synced with current listings (new IPOs added, delisted stocks removed), transforms the raw prices into **60+ ML-ready technical features**, and then **scores every stock** across momentum, trend, volume, and volatility factors — giving you ranked trade candidates with entry/stop/target prices. No terminal required.

Five batch files do all the work:

| Double-click this | What it does |
|-------------------|-------------|
| **`install.bat`** | Installs all Python dependencies (one-time setup) |
| **`daily.bat`** | Downloads / updates all stock price data |
| **`generate.bat`** | Builds 60+ technical features for ML from your data |
| **`screen.bat`** | Scores all stocks and outputs today's top trade candidates |
| **`trade.bat`** | Executes trades on Alpaca (paper or live) from screener results |

```
daily.bat  →  generate.bat  →  screen.bat  →  trade.bat
(download)    (features)       (trade picks)   (execute)
```

---

## ⚡ Quick Start

Pick whichever setup method you prefer — **batch files** (no terminal needed) or **Docker** (no Python install needed):

### Option A: Batch Files (Windows — Easiest)

> **Prerequisite:** Install Python 3.8+ from [python.org](https://www.python.org/downloads/) (check "Add to PATH" during install).

**1. Download the project** — unzip or clone:
```
git clone https://github.com/natedoggzCD/YfinanceDownloader.git
```

**2. Set up (one time)**
1. **Double-click `install.bat`** — installs all Python packages automatically.
2. Copy `config.example.py` to `config.py` — edit it to set your price range if you want (defaults work fine).
3. Download the NASDAQ screener CSV from [nasdaq.com/market-activity/stocks/screener](https://www.nasdaq.com/market-activity/stocks/screener) and save it as `nasdaq_screener.csv` in the project folder.

**3. Get your data** — **double-click `daily.bat`**. It asks if you want to refresh the screener, then downloads everything. Two CSV files appear: `prices_daily.csv` and `prices_hourly.csv`.

**4. Keep it updated** — **double-click `daily.bat` anytime**. It only downloads new data, so repeat runs are fast.

**5. Generate ML features** — **double-click `generate.bat`** to produce `daily_features.parquet` with 60+ technical indicators.

**6. Screen for trade candidates** — **double-click `screen.bat`** to score every stock and get ranked picks with entry/stop/target prices saved to `screener_results.csv`.

**7. Execute trades (optional)** — **double-click `trade.bat`** to paper-trade your top picks on Alpaca. See [Alpaca Setup](#-alpaca-paper-trading-free) below for the free 2-minute signup.

---

### Option B: Docker (Any OS — No Python Install)

> **Prerequisite:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, Mac, or Linux).

**1. Download the project:**
```bash
git clone https://github.com/natedoggzCD/YfinanceDownloader.git
cd YfinanceDownloader
```

**2. Set up (one time):**
```bash
cp config.example.py config.py    # Edit price range if desired
```
Place your `nasdaq_screener.csv` in the project folder (download from [nasdaq.com/market-activity/stocks/screener](https://www.nasdaq.com/market-activity/stocks/screener)).

**3. Get your data:**
```bash
docker compose up --build
```

**4. Keep it updated:**
```bash
# Update screener + download latest data
docker compose run --rm yfinance python downloader.py --update-screener --all
```

**5. Generate ML features:**
```bash
docker compose run --rm yfinance python generate.py
```

**6. Screen for trade candidates:**
```bash
docker compose run --rm yfinance python screener.py
# With AI summaries:
docker compose run --rm yfinance python screener.py --ai
```

**7. Execute trades (optional):**
```bash
# Preview trades (no orders placed)
docker compose run --rm yfinance python trader.py --dry-run
# Execute paper trades
docker compose run --rm yfinance python trader.py
# Check positions
docker compose run --rm yfinance python trader.py --status
```

> **💾 Your data is persistent.** The `docker-compose.yml` bind-mounts your project folder (`volumes: - .:/app`), so all downloaded CSVs and generated Parquet files are written directly to your machine — not inside the container. You can stop, rebuild, or remove the container at any time without losing data. Your files will always be in the `YfinanceDownloader/` folder:
>
> | File | Location on your machine |
> |------|-------------------------|
> | `prices_daily.csv` | `YfinanceDownloader/prices_daily.csv` |
> | `prices_hourly.csv` | `YfinanceDownloader/prices_hourly.csv` |
> | `daily_features.parquet` | `YfinanceDownloader/daily_features.parquet` |
> | `config.py` | `YfinanceDownloader/config.py` |

---

> **First run note:** The initial download covers 1,000+ stocks and takes several hours due to Yahoo Finance rate limits. Every run after that is fast.

---

## 🖱️ Batch File Reference

### `install.bat`

Runs `pip install -r requirements.txt`. Double-click once after downloading the project.

### `daily.bat`

Prompts whether to refresh the NASDAQ screener, then runs the full pipeline:
1. **Initializes** data if no CSVs exist yet (first run)
2. **Reconciles** tickers with the NASDAQ screener (adds new IPOs, removes delisted)
3. **Updates** your CSVs with the latest price bars

### `generate.bat`

Runs the feature engineering pipeline. Reads `prices_daily.csv` and produces `daily_features.parquet` with 60+ indicators.

### `screen.bat`

Scores every stock in `daily_features.parquet` across momentum, trend, volume, pullback, and volatility factors. Outputs ranked trade candidates with entry/stop/target prices to `screener_results.csv`. Optionally asks if you want AI-powered trade summaries (requires an API key in `screen_config.py`).

### `trade.bat`

Reads `screener_results.csv` and executes trades on your Alpaca account. Offers three modes:
1. **Preview** (dry run) — shows exactly what would be traded, no orders placed
2. **Execute** — places paper (or live) orders with R-Unit position sizing
3. **Status** — shows your current positions and P&L

Requires Alpaca API keys in `trade_config.py`. See [setup guide](#-alpaca-paper-trading-free) below.

---

## 🎯 Stock Screener

The screener uses quantitative scoring logic ported from the [AutoTrade](https://github.com/natedoggzCD) trading system — no LLM, no GPU, no machine learning required. Pure rule-based signal scoring.

### Signal Families

| Scan Type | What it looks for | Key Thresholds |
|-----------|-------------------|----------------|
| **Momentum Breakout** | Trending stocks with volume expansion | Weekly return > 1%, RSI 30-70, volume > 1.5x avg, price > SMA20 |
| **Mean Reversion** | Oversold bounce candidates | Weekly return < -3%, RSI < 35, volume > 2x avg (capitulation) |
| **Breakout** | Bollinger squeeze releasing | BB width contracting, volume confirmation > 1.5x |

### Scoring Factors (Weighted to 100)

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| **Momentum** | 30% | ROC, MACD histogram, weekly return |
| **Volume** | 25% | Current volume vs 20-day average |
| **Volatility** | 20% | ATR in optimal range (1.5% ideal) |
| **Trend** | 15% | SMA alignment (20/50/200) + ADX strength |
| **Pullback** | 10% | RSI sweet-spot for entry timing |

### Output: `screener_results.csv`

Each row is a ranked trade candidate with:

```
ticker, Close, score, scan_type, entry_price, stop_price, target_price, risk_reward,
momentum_score, trend_score, volume_score, pullback_score, volatility_score, atr_pct
```

### AI Trade Summaries (Optional)

Set an API key in `screen_config.py` to get AI-generated 2-3 sentence trade summaries for your top picks. Works with:

- **OpenAI** — `gpt-4o-mini` (cheap) or `gpt-4o` (best)
- **Any OpenAI-compatible API** — Ollama, LM Studio, vLLM, etc. (just change `AI_BASE_URL`)

No API key? The screener works perfectly without it — pure quantitative scoring.

### Screener Commands

```bash
python screener.py                     # Run with defaults
python screener.py --top 20            # Show top 20 only
python screener.py --scan momentum     # Only momentum breakout scan
python screener.py --scan reversion    # Only mean reversion scan
python screener.py --ai                # Enable AI summaries
python screener.py --output picks.csv  # Custom output file
```

---

## 💰 Alpaca Paper Trading (Free)

**New to trading APIs?** Alpaca gives you a free paper trading account with $100,000 in simulated cash. No credit card, no real money, no risk. Setup takes 2 minutes.

### Step 1: Create a Free Alpaca Account

1. Go to **[https://app.alpaca.markets/signup](https://app.alpaca.markets/signup)**
2. Sign up with your email and a password
3. Verify your email (check your inbox)
4. You now have a paper trading account with **$100,000 fake money**

### Step 2: Get Your API Keys

1. Log in to [https://app.alpaca.markets](https://app.alpaca.markets)
2. In the left sidebar, click **"Paper Trading"**
3. Click **"View"** next to **API Keys**
4. Click **"Generate New Key"**
5. **Copy both keys** — you'll need the API Key ID and the Secret Key

> **Important:** The Secret Key is only shown once. Copy it immediately.

### Step 3: Configure YfinanceDownloader

1. Copy `trade_config.example.py` to `trade_config.py`
2. Paste your keys:

```python
ALPACA_API_KEY = "PKXXXXXXXXXXXXXXXX"        # Your API Key ID
ALPACA_SECRET_KEY = "xxxxxxxxxxxxxxxxxxxxxxx"  # Your Secret Key
PAPER_TRADING = True                            # Start with paper trading!
```

3. **Double-click `trade.bat`** — that's it.

### How It Works

The trader reads your `screener_results.csv` and:

1. **Connects** to your Alpaca paper account
2. **Sizes positions** using R-Unit risk management (same logic as [AutoTrade](https://github.com/natedoggzCD)) — risking 1% of equity per trade
3. **Shows you the plan** — every order with entry, stop, target, and cost
4. **Asks for confirmation** before placing any orders
5. **Logs every trade** to `trade_log.csv` for review

### Position Sizing (R-Unit)

Every trade is sized so that hitting your stop loss costs exactly 1% of your account:

```
Risk per trade = Account Equity × 1%
Shares = Risk per trade ÷ (Entry Price - Stop Price)
```

Example: $100,000 account, buying a $50 stock with a $47 stop:
- Risk = $100,000 × 1% = $1,000
- Risk per share = $50 - $47 = $3
- Shares = $1,000 ÷ $3 = **333 shares** ($16,650 position)

### Trader Commands

```bash
python trader.py                     # Trade top picks (asks for confirmation)
python trader.py --dry-run           # Preview orders without placing them
python trader.py --status            # Show account balance and positions
python trader.py --top 5             # Only trade top 5 picks
python trader.py --min-score 70      # Only trade stocks scored 70+
python trader.py --input my_picks.csv  # Use custom screener output
```

### Trader Configuration

All settings in `trade_config.py`:

```python
# Position sizing
RISK_PER_TRADE_PCT = 1.0     # 1% risk per trade (conservative)
MAX_POSITION_PCT = 5.0        # Max 5% of equity per position
MAX_POSITIONS = 10            # Max 10 open positions at once

# Safety
MIN_CASH_RESERVE_PCT = 20.0   # Always keep 20% in cash
MIN_SCORE_TO_TRADE = 60.0     # Only trade stocks scored 60+
CONFIRM_BEFORE_TRADING = True # Ask before placing orders

# Mode
PAPER_TRADING = True          # True = paper, False = live
```

### Going Live

When you're confident with paper trading results:

1. Fund your Alpaca account at [https://app.alpaca.markets](https://app.alpaca.markets)
2. Switch to **Live Trading** in the sidebar → generate **Live API Keys**
3. Update `trade_config.py`:

```python
ALPACA_API_KEY = "your-live-key"
ALPACA_SECRET_KEY = "your-live-secret"
PAPER_TRADING = False    # ← This switches to real money
```

> **⚠️ Start with paper trading.** Run it for at least a few weeks to understand how the system behaves before risking real capital.

---

### Screener Configuration

Copy `screen_config.example.py` to `screen_config.py` and edit thresholds:

```python
# Universe filters
MIN_PRICE = 1.00            # Min stock price
MAX_PRICE = 350.00          # Max stock price
MIN_AVG_VOLUME = 500_000    # Min 20-day avg volume

# Scoring weights (must sum to 1.0)
WEIGHT_MOMENTUM   = 0.30
WEIGHT_VOLUME     = 0.25
WEIGHT_VOLATILITY = 0.20
WEIGHT_TREND      = 0.15
WEIGHT_PULLBACK   = 0.10

# AI (optional)
AI_API_KEY = ""                            # Your key (or "" to disable)
AI_BASE_URL = "https://api.openai.com/v1"  # Change for local models
AI_MODEL = "gpt-4o-mini"
```

---

## 💻 Terminal / Command-Line Usage

If you prefer the command line (or you're on Mac/Linux), everything works from a terminal too:

```bash
cd YfinanceDownloader
pip install -r requirements.txt
cp config.example.py config.py
python downloader.py --all
```

---

## ️ All Commands

| Command | What it does |
|---------|-------------|
| `python downloader.py --init` | First-time download of all NASDAQ stocks in your price range |
| `python downloader.py --update` | Append new bars since the last download |
| `python downloader.py --reconcile` | Add new IPOs, remove delisted tickers from your CSVs |
| `python downloader.py --update-screener` | Uses Playwright to download the latest NASDAQ Screener CSV |
| `python downloader.py --all` | Reconcile + update (+ init if no data exists yet) |
| `python downloader.py --dry-run` | Preview changes without downloading anything |
| `python downloader.py --tickers AAPL MSFT` | Process only specific tickers |
| `python generate.py` | Generate technical features → `daily_features.parquet` |
| **`daily.bat`** | **One-click wrapper** — runs `--all` and prompts to update screener (Windows) |
| **`generate.bat`** | **One-click wrapper** — runs `generate.py` (Windows) |
| `python trader.py` | Execute trades on Alpaca from screener results |
| `python trader.py --dry-run` | Preview trades without placing orders |
| `python trader.py --status` | Show Alpaca account balance and positions |
| **`trade.bat`** | **One-click wrapper** — runs `trader.py` with menu (Windows) |

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
├── downloader.py              # Core script — download, update, reconcile
├── generate.py                # Feature engineering → daily_features.parquet
├── screener.py                # Stock screener → screener_results.csv
├── config.example.py          # Downloader config template (copy to config.py)
├── screen_config.example.py   # Screener config template (copy to screen_config.py)
├── trade_config.example.py    # Trader config template (copy to trade_config.py)
├── config.py                  # Your downloader settings (gitignored)
├── screen_config.py           # Your screener settings (gitignored)
├── trade_config.py            # Your Alpaca API keys (gitignored)
├── install.bat                # One-click dependency install (Windows)
├── daily.bat                  # One-click daily update (Windows)
├── generate.bat               # One-click feature generation (Windows)
├── screen.bat                 # One-click stock screener (Windows)
├── trade.bat                  # One-click Alpaca trader (Windows)
├── trader.py                  # Trade execution → trade_log.csv
├── nasdaq_screener.csv        # NASDAQ stock listing (you download this)
├── requirements.txt           # Python dependencies
├── EXAMPLES.md                # Additional usage examples
├── LICENSE                    # MIT License
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
| `ALPACA API KEYS NOT SET` | Sign up at [app.alpaca.markets/signup](https://app.alpaca.markets/signup), get keys, paste into `trade_config.py` |
| `Could not connect to Alpaca` | Double-check your API Key and Secret Key in `trade_config.py`. Make sure you're using Paper keys with `PAPER_TRADING = True` |
| `alpaca-py is not installed` | Run `pip install alpaca-py` or double-click `install.bat` |

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
