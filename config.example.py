# Configuration file for YfinanceDownloader
# Copy this file to config.py and modify as needed:
#   cp config.example.py config.py
#
# config.py is gitignored so your local settings won't be overwritten.

# Stock price range filter (in USD)
# Only stocks within this price range will be included
MIN_PRICE = 2.0
MAX_PRICE = 200.0

# Date range for historical data downloads
# Format: "YYYY-MM-DD"
START_DATE = "2018-01-02"
END_DATE = None  # Set to None to use current date

# Data file paths
DAILY_CSV = "prices_daily.csv"
HOURLY_CSV = "prices_hourly.csv"
NASDAQ_SCREENER = "nasdaq_screener.csv"

# Rate limiting settings (to avoid hitting API limits)
BATCH_SIZE = 50  # Number of stocks to download per batch
PAUSE_AFTER_BATCHES = 500  # Pause after this many API calls
PAUSE_DURATION_SECONDS = 60  # Duration of pause in seconds

# Special characters to filter out (warrants, options, etc.)
# These patterns indicate tickers that should be excluded
INVALID_TICKER_PATTERNS = r"[\^\.\/\-=]"

# Minimum number of data points required for a stock to be kept
MIN_OBSERVATIONS = 100

# Retry settings for failed downloads
MAX_RETRIES = 3          # Maximum number of retry attempts per ticker
RETRY_BACKOFF_SECONDS = 5  # Base wait time between retries (doubles each attempt)

# Stale ticker threshold
# Tickers whose latest data is older than this many days are auto-skipped during updates
STALE_TICKER_DAYS = 5

# Yahoo Finance hourly data limit (days)
# yfinance only provides hourly data for approximately the last 730 days (~2 years)
# Using 729 to stay safely within the boundary Yahoo enforces
HOURLY_MAX_DAYS = 729

# Gap detection threshold (days)
# Stocks with data gaps larger than this will be flagged
GAP_THRESHOLD_DAYS = 7

# Timezone settings
TIMEZONE = "UTC"
