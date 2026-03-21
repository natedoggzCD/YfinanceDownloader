"""
trade_config.py — Configuration for the Alpaca paper/live trader.
Copy this file to trade_config.py and add your Alpaca API keys.

TIP: You can also use config.yaml (preferred) for all settings in one file.
     If config.yaml exists, it takes priority over this file.

+==================================================================+
|  GET YOUR FREE API KEYS (takes 2 minutes):                        |
|                                                                    |
|  1. Go to https://app.alpaca.markets/signup                        |
|  2. Sign up (email + password — no funding required)               |
|  3. In the dashboard, click "Paper Trading" on the left sidebar    |
|  4. Click "View" next to API Keys -> "Generate New Key"            |
|  5. Copy your API Key and Secret Key below                         |
|                                                                    |
|  Paper trading = free simulated trading with fake $100k.           |
|  No credit card, no real money, no risk.                           |
+==================================================================+
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
# R-Unit sizing: each trade risks exactly RISK_PER_TRADE_PCT of your account.
# With conviction scaling ON, this becomes the midpoint — high-scoring picks
# risk up to 1.5%, low-scoring picks risk down to 0.5%.
RISK_PER_TRADE_PCT = 1.0     # Base % of account equity risked per trade
MAX_POSITION_PCT = 8.0        # Max % of equity in a single position
MAX_POSITIONS = 10            # Maximum simultaneous open positions
MIN_POSITION_VALUE = 100.0    # Minimum dollar value per position (skip tiny trades)

# ── Conviction-Scaled Sizing (NEW) ──────────────────────────────
# Scales risk budget by screener score quality.
# Score 100 -> 1.5% risk, Score 65 -> 0.65% risk, Score 50 -> 0.5% risk
CONVICTION_SCALING = True
CONVICTION_RISK_RANGE = [0.5, 1.5]  # [min%, max%] risk range

# ── Portfolio Risk Controls (NEW) ───────────────────────────────
# Total open risk across all positions, as % of equity.
# Once this cap is hit, no new trades until risk decreases.
PORTFOLIO_HEAT_MAX_PCT = 6.0

# ── Order Settings ───────────────────────────────────────────────
ORDER_TYPE = "market"         # "market" = fill immediately
TIME_IN_FORCE = "day"         # "day" = cancel if not filled by close

# Bracket orders place stop-loss + take-profit automatically with each entry.
# Highly recommended — protects positions even if you're not watching.
USE_BRACKET_ORDERS = True

# ── Safety Controls ──────────────────────────────────────────────
MIN_CASH_RESERVE_PCT = 20.0   # Always keep at least 20% of equity in cash
MIN_SCORE_TO_TRADE = 65.0     # Only trade stocks scored 65+ by the screener
MIN_RR_TO_TRADE = 1.5         # Skip trades with risk:reward below 1.5
ATR_STOP_VALIDATION = True    # Verify stop distance is >= 1.5x ATR
CONFIRM_BEFORE_TRADING = True # Ask for confirmation before placing orders

# ── Input / Output ──────────────────────────────────────────────
SCREENER_CSV = "screener_results.csv"   # Input: screener output file
TRADE_LOG_CSV = "trade_log.csv"         # Output: log of all placed trades
