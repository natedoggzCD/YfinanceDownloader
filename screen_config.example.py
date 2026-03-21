"""
screen_config.py — Configuration for the stock screener.
Copy this file to screen_config.py and edit to your preferences.
"""

# ── Data Source ──────────────────────────────────────────────────
# Path to the daily features parquet file produced by generate.py
FEATURES_PARQUET = "daily_features.parquet"

# ── Universe Filters ─────────────────────────────────────────────
MIN_PRICE = 1.00            # Minimum stock price ($)
MAX_PRICE = 350.00          # Maximum stock price ($)
MIN_AVG_VOLUME = 500_000    # Minimum 20-day average volume (shares)
MIN_ATR_PCT = 0.5           # Minimum ATR as % of price (too low = no movement)
MAX_ATR_PCT = 8.0           # Maximum ATR as % of price (too high = erratic)

# ── Scoring Weights (must sum to 1.0) ───────────────────────────
# These match AutoTrade's proven weighting for pre-trade screening.
WEIGHT_MOMENTUM   = 0.30    # ROC, MACD histogram, weekly return
WEIGHT_TREND      = 0.15    # SMA alignment, ADX strength
WEIGHT_VOLUME     = 0.25    # Volume surge vs 20-day average
WEIGHT_PULLBACK   = 0.10    # RSI pullback sweet-spot scoring
WEIGHT_VOLATILITY = 0.20    # ATR in optimal range (Goldilocks zone)

# ── Scan Modes ──────────────────────────────────────────────────
# Which signal families to run. Set to False to disable.
SCAN_MOMENTUM_BREAKOUT = True    # Trending + volume expansion
SCAN_MEAN_REVERSION    = True    # RSI < 35 + volume capitulation
SCAN_BREAKOUT          = True    # Bollinger squeeze releasing

# ── Momentum Breakout Thresholds ────────────────────────────────
MOMENTUM_MIN_WEEKLY_RETURN = 1.0     # % minimum weekly return
MOMENTUM_RSI_MIN = 30                # RSI floor
MOMENTUM_RSI_MAX = 70                # RSI ceiling
MOMENTUM_MIN_VOLUME_RATIO = 1.5      # Volume vs 20-day average

# ── Mean Reversion Thresholds ───────────────────────────────────
REVERSION_MAX_WEEKLY_RETURN = -3.0   # % maximum (negative = falling)
REVERSION_RSI_MAX = 35               # RSI must be oversold
REVERSION_MIN_VOLUME_RATIO = 2.0     # Capitulation volume

# ── Breakout Thresholds ─────────────────────────────────────────
BREAKOUT_BB_WIDTH_MIN = 0.03         # Min Bollinger bandwidth (squeeze)
BREAKOUT_MIN_VOLUME_RATIO = 1.5      # Volume confirmation

# ── Output ──────────────────────────────────────────────────────
OUTPUT_CSV = "screener_results.csv"  # Ranked candidates output
TOP_N = 50                           # Number of top picks to output

# ── AI Summary (Optional) ───────────────────────────────────────
# Set your API key to enable AI-powered trade summaries.
# Leave empty string "" to run without AI (pure quantitative only).
# Supports: OpenAI, or any OpenAI-compatible endpoint (Ollama, LM Studio, etc.)
AI_API_KEY = ""                                     # Your API key (or "" to disable)
AI_BASE_URL = "https://api.openai.com/v1"           # OpenAI default. Change for local models.
AI_MODEL = "gpt-4o-mini"                            # Model name. Use "gpt-4o" for best quality.
AI_MAX_PICKS_TO_SUMMARIZE = 10                      # Only summarize top N picks (saves tokens)
