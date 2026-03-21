"""
trade_config.py — Configuration for the Alpaca paper/live trader.
Copy this file to trade_config.py and add your Alpaca API keys.

╔══════════════════════════════════════════════════════════════════╗
║  GET YOUR FREE API KEYS (takes 2 minutes):                      ║
║                                                                  ║
║  1. Go to https://app.alpaca.markets/signup                      ║
║  2. Sign up (email + password — no funding required)             ║
║  3. In the dashboard, click "Paper Trading" on the left sidebar  ║
║  4. Click "View" next to API Keys → "Generate New Key"           ║
║  5. Copy your API Key and Secret Key below                       ║
║                                                                  ║
║  Paper trading = free simulated trading with fake $100k.         ║
║  No credit card, no real money, no risk.                         ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ── Alpaca API Credentials ───────────────────────────────────────
# Paste your keys from https://app.alpaca.markets/paper/dashboard/overview
ALPACA_API_KEY = ""           # e.g. "PKXXXXXXXXXXXXXXXX"
ALPACA_SECRET_KEY = ""        # e.g. "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ── Paper vs Live Mode ──────────────────────────────────────────
# True  = Paper trading (simulated, no real money — RECOMMENDED to start)
# False = Live trading (real money — only switch when you're confident)
PAPER_TRADING = True

# ── Position Sizing ─────────────────────────────────────────────
# These settings control how much capital goes into each trade.
# Ported from AutoTrade's R-Unit sizing system.

RISK_PER_TRADE_PCT = 1.0     # % of account equity risked per trade (1% = conservative)
MAX_POSITION_PCT = 5.0        # Max % of equity in a single position (concentration limit)
MAX_POSITIONS = 10            # Maximum simultaneous open positions
MIN_POSITION_VALUE = 100.0    # Minimum dollar value per position (skip tiny trades)

# ── Order Settings ───────────────────────────────────────────────
ORDER_TYPE = "market"         # "market" or "limit" (market = fill immediately)
TIME_IN_FORCE = "day"         # "day" = cancel if not filled by market close

# ── Safety Controls ──────────────────────────────────────────────
MIN_CASH_RESERVE_PCT = 20.0   # Always keep at least 20% of equity in cash
MIN_SCORE_TO_TRADE = 60.0     # Only trade stocks scored 60+ by the screener
CONFIRM_BEFORE_TRADING = True # Ask for confirmation before placing orders (set False to auto-trade)

# ── Input / Output ──────────────────────────────────────────────
SCREENER_CSV = "screener_results.csv"   # Input: screener output file
TRADE_LOG_CSV = "trade_log.csv"         # Output: log of all placed trades
