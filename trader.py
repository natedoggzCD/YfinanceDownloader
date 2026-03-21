"""
trader.py — Execute trades on Alpaca using screener results.

Reads screener_results.csv, connects to your Alpaca paper (or live) account,
sizes positions using R-Unit risk management, and places orders for the
top-scoring stocks.

Usage:
    python trader.py                    # Trade top picks (with confirmation)
    python trader.py --top 5            # Only trade top 5 picks
    python trader.py --dry-run          # Preview orders without placing them
    python trader.py --status           # Show current positions and account info

Requires:
    pip install alpaca-py
    Copy trade_config.example.py → trade_config.py and add your API keys.
"""

import argparse
import sys
import os
from datetime import datetime

import pandas as pd

# ── Load Config ──────────────────────────────────────────────────

def load_config():
    """Load trade_config.py, fall back to trade_config.example.py."""
    config = {}
    config_file = "trade_config.py"
    if not os.path.exists(config_file):
        config_file = "trade_config.example.py"
        if not os.path.exists(config_file):
            print("ERROR: No trade_config.py found.")
            print("Copy trade_config.example.py to trade_config.py and add your Alpaca API keys.")
            sys.exit(1)
    with open(config_file, "r") as f:
        exec(f.read(), config)
    return config


def validate_keys(cfg):
    """Check that API keys are set."""
    key = cfg.get("ALPACA_API_KEY", "")
    secret = cfg.get("ALPACA_SECRET_KEY", "")
    if not key or not secret:
        print("=" * 65)
        print("  ALPACA API KEYS NOT SET")
        print("=" * 65)
        print()
        print("  You need free Alpaca API keys to trade. Setup takes 2 minutes:")
        print()
        print("  1. Go to https://app.alpaca.markets/signup")
        print("  2. Sign up (email + password — no funding required)")
        print("  3. Click 'Paper Trading' in the left sidebar")
        print("  4. Click 'View' next to API Keys → 'Generate New Key'")
        print("  5. Copy your API Key and Secret Key")
        print("  6. Paste them into trade_config.py:")
        print()
        print('     ALPACA_API_KEY = "PKXXXXXXXXXXXXXXXX"')
        print('     ALPACA_SECRET_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"')
        print()
        print("  Paper trading = simulated trades with $100k fake money.")
        print("  No credit card. No real money. No risk.")
        print("=" * 65)
        sys.exit(1)


# ── Alpaca Connection ────────────────────────────────────────────

def connect_alpaca(cfg):
    """Create and validate the Alpaca trading client."""
    try:
        from alpaca.trading.client import TradingClient
    except ImportError:
        print("ERROR: alpaca-py is not installed.")
        print("Run:  pip install alpaca-py")
        print("Or:   double-click install.bat")
        sys.exit(1)

    paper = cfg.get("PAPER_TRADING", True)
    client = TradingClient(
        api_key=cfg["ALPACA_API_KEY"],
        secret_key=cfg["ALPACA_SECRET_KEY"],
        paper=paper,
    )

    # Validate connection
    try:
        account = client.get_account()
    except Exception as e:
        print(f"ERROR: Could not connect to Alpaca: {e}")
        print()
        print("Check that your API keys in trade_config.py are correct.")
        print("Dashboard: https://app.alpaca.markets/paper/dashboard/overview")
        sys.exit(1)

    return client, account


def print_account_summary(account, paper):
    """Display account status."""
    mode = "PAPER" if paper else "LIVE"
    equity = float(account.equity)
    cash = float(account.cash)
    buying_power = float(account.buying_power)

    print(f"\n  {'=' * 50}")
    print(f"  ALPACA ACCOUNT ({mode} TRADING)")
    print(f"  {'=' * 50}")
    print(f"  Equity:        ${equity:>12,.2f}")
    print(f"  Cash:          ${cash:>12,.2f}")
    print(f"  Buying Power:  ${buying_power:>12,.2f}")
    print(f"  Status:        {account.status}")
    print(f"  {'=' * 50}\n")

    return equity, cash


# ── Position Sizing (R-Unit from AutoTrade) ──────────────────────

def calculate_position_size(entry_price, stop_price, equity, cfg):
    """
    R-Unit position sizing — ported from AutoTrade's RUnitSizer.
    Calculates share quantity so that hitting the stop costs exactly
    RISK_PER_TRADE_PCT of your account.
    """
    risk_pct = cfg.get("RISK_PER_TRADE_PCT", 1.0) / 100.0
    max_notional_pct = cfg.get("MAX_POSITION_PCT", 5.0) / 100.0
    min_value = cfg.get("MIN_POSITION_VALUE", 100.0)

    # Dollar risk per trade (1R)
    risk_unit = equity * risk_pct

    # Risk per share
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0:
        return 0

    # R-Unit quantity
    qty = int(risk_unit / risk_per_share)

    # Cap by max notional (concentration limit)
    max_notional = equity * max_notional_pct
    max_qty = int(max_notional / entry_price)
    qty = min(qty, max_qty)

    # Enforce minimum position value
    if qty * entry_price < min_value:
        return 0

    return qty


# ── Load Screener Results ────────────────────────────────────────

def load_screener_results(cfg, top_n=None, min_score=None):
    """Load and filter screener results."""
    csv_path = cfg.get("SCREENER_CSV", "screener_results.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} not found.")
        print("Run the screener first:  python screener.py")
        print("Or double-click:         screen.bat")
        sys.exit(1)

    df = pd.read_csv(csv_path)

    if "score" not in df.columns or "ticker" not in df.columns:
        print(f"ERROR: {csv_path} is missing required columns (ticker, score).")
        sys.exit(1)

    # Filter by minimum score
    if min_score is None:
        min_score = cfg.get("MIN_SCORE_TO_TRADE", 60.0)
    df = df[df["score"] >= min_score].copy()

    if df.empty:
        print(f"  No stocks scored {min_score}+ in {csv_path}.")
        print("  Try lowering MIN_SCORE_TO_TRADE in trade_config.py.")
        return df

    # Limit to top N
    if top_n:
        df = df.head(top_n)

    return df


# ── Get Current Positions ────────────────────────────────────────

def get_open_positions(client):
    """Get current open positions as a dict of {symbol: position}."""
    positions = client.get_all_positions()
    return {p.symbol: p for p in positions}


# ── Order Placement ──────────────────────────────────────────────

def place_order(client, symbol, qty, side, order_type, time_in_force):
    """Place a single order on Alpaca."""
    from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce

    alpaca_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
    tif = TimeInForce.DAY if time_in_force == "day" else TimeInForce.GTC

    if order_type == "market":
        request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=alpaca_side,
            time_in_force=tif,
        )
    else:
        return None  # Only market orders for simplicity

    order = client.submit_order(request)
    return order


# ── Trade Execution ──────────────────────────────────────────────

def execute_trades(client, account, candidates, cfg, dry_run=False):
    """Size and place orders for screener candidates."""
    equity, cash = float(account.equity), float(account.cash)
    paper = cfg.get("PAPER_TRADING", True)
    order_type = cfg.get("ORDER_TYPE", "market")
    tif = cfg.get("TIME_IN_FORCE", "day")
    max_positions = cfg.get("MAX_POSITIONS", 10)
    cash_reserve_pct = cfg.get("MIN_CASH_RESERVE_PCT", 20.0) / 100.0

    # Get existing positions
    positions = get_open_positions(client)
    open_count = len(positions)
    slots_available = max(0, max_positions - open_count)

    # Cash available for new trades (respecting reserve)
    min_cash = equity * cash_reserve_pct
    available_cash = max(0, cash - min_cash)

    print(f"  Open positions: {open_count} / {max_positions}")
    print(f"  Slots available: {slots_available}")
    print(f"  Cash available for trading: ${available_cash:,.2f} (keeping ${min_cash:,.2f} reserve)")
    print()

    if slots_available <= 0:
        print("  All position slots are full. Close some positions first.")
        return []

    # Build order plan
    orders_planned = []

    for _, row in candidates.iterrows():
        if len(orders_planned) >= slots_available:
            break

        symbol = row["ticker"]

        # Skip if already holding
        if symbol in positions:
            print(f"  {symbol}: SKIP — already holding a position")
            continue

        entry = row.get("entry_price", row["Close"])
        stop = row.get("stop_price", entry * 0.96)

        # R-Unit sizing
        qty = calculate_position_size(entry, stop, equity, cfg)
        if qty <= 0:
            print(f"  {symbol}: SKIP — position too small (entry=${entry:.2f}, stop=${stop:.2f})")
            continue

        cost = qty * entry
        if cost > available_cash:
            print(f"  {symbol}: SKIP — insufficient cash (need ${cost:,.2f}, have ${available_cash:,.2f})")
            continue

        target = row.get("target_price", entry * 1.04)
        risk = entry - stop
        rr = row.get("risk_reward", (target - entry) / risk if risk > 0 else 0)

        orders_planned.append({
            "symbol": symbol,
            "qty": qty,
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_reward": rr,
            "cost": cost,
            "score": row["score"],
            "scan_type": row.get("scan_type", "general"),
        })

        available_cash -= cost

    if not orders_planned:
        print("  No trades to place — all candidates filtered out.")
        return []

    # Display order plan
    print(f"  {'─' * 75}")
    print(f"  {'Symbol':<8} {'Qty':>5} {'Entry':>9} {'Stop':>9} {'Target':>9} {'R:R':>5} {'Cost':>11} {'Score':>6}")
    print(f"  {'─' * 75}")

    total_cost = 0
    for o in orders_planned:
        print(f"  {o['symbol']:<8} {o['qty']:>5} ${o['entry']:>7.2f} ${o['stop']:>7.2f} "
              f"${o['target']:>7.2f} {o['risk_reward']:>4.1f}x ${o['cost']:>9,.2f} {o['score']:>5.0f}")
        total_cost += o["cost"]
    print(f"  {'─' * 75}")
    print(f"  Total: {len(orders_planned)} orders  |  ${total_cost:>,.2f}")
    print()

    if dry_run:
        print("  DRY RUN — no orders placed.")
        return orders_planned

    # Confirmation gate
    if cfg.get("CONFIRM_BEFORE_TRADING", True):
        mode_label = "PAPER" if paper else "*** LIVE ***"
        print(f"  Mode: {mode_label}")
        response = input(f"  Place these {len(orders_planned)} orders? (yes/no): ").strip().lower()
        if response not in ("yes", "y"):
            print("  Cancelled — no orders placed.")
            return []

    # Place orders
    placed = []
    for o in orders_planned:
        try:
            order = place_order(client, o["symbol"], o["qty"], "buy", order_type, tif)
            status = getattr(order, "status", "submitted")
            order_id = str(getattr(order, "id", ""))
            print(f"  ✓ {o['symbol']}: {o['qty']} shares — {status} (ID: {order_id[:8]}...)")
            o["order_id"] = order_id
            o["status"] = str(status)
            o["timestamp"] = datetime.now().isoformat()
            placed.append(o)
        except Exception as e:
            print(f"  ✗ {o['symbol']}: FAILED — {e}")
            o["order_id"] = ""
            o["status"] = f"failed: {e}"
            o["timestamp"] = datetime.now().isoformat()
            placed.append(o)

    return placed


# ── Trade Log ────────────────────────────────────────────────────

def save_trade_log(trades, cfg):
    """Append placed trades to the trade log CSV."""
    if not trades:
        return

    log_path = cfg.get("TRADE_LOG_CSV", "trade_log.csv")
    df = pd.DataFrame(trades)

    if os.path.exists(log_path):
        existing = pd.read_csv(log_path)
        df = pd.concat([existing, df], ignore_index=True)

    df.to_csv(log_path, index=False)
    print(f"\n  Trade log saved to {log_path}")


# ── Show Status ──────────────────────────────────────────────────

def show_status(client, account, paper):
    """Display current positions and P&L."""
    print_account_summary(account, paper)

    positions = client.get_all_positions()
    if not positions:
        print("  No open positions.\n")
        return

    print(f"  {'Symbol':<8} {'Qty':>6} {'Avg Entry':>10} {'Current':>10} {'P&L':>11} {'P&L %':>8}")
    print(f"  {'─' * 60}")

    total_pl = 0
    for p in positions:
        symbol = p.symbol
        qty = int(p.qty)
        avg_entry = float(p.avg_entry_price)
        current = float(p.current_price)
        pl = float(p.unrealized_pl)
        pl_pct = float(p.unrealized_plpc) * 100
        total_pl += pl

        sign = "+" if pl >= 0 else ""
        print(f"  {symbol:<8} {qty:>6} ${avg_entry:>8.2f} ${current:>8.2f} "
              f"{sign}${pl:>9.2f} {sign}{pl_pct:>6.1f}%")

    sign = "+" if total_pl >= 0 else ""
    print(f"  {'─' * 60}")
    print(f"  Total P&L: {sign}${total_pl:,.2f}\n")


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Execute trades from screener results via Alpaca")
    parser.add_argument("--top", type=int, default=None, help="Only trade top N picks")
    parser.add_argument("--dry-run", action="store_true", help="Preview orders without placing them")
    parser.add_argument("--status", action="store_true", help="Show account and positions")
    parser.add_argument("--min-score", type=float, default=None, help="Minimum score to trade")
    parser.add_argument("--input", type=str, default=None, help="Custom screener CSV path")
    args = parser.parse_args()

    cfg = load_config()

    # Override input path if specified
    if args.input:
        cfg["SCREENER_CSV"] = args.input

    print("\n" + "=" * 60)
    print("  YFINANCE TRADER — Alpaca Execution")
    print("=" * 60)

    validate_keys(cfg)
    client, account = connect_alpaca(cfg)
    paper = cfg.get("PAPER_TRADING", True)

    if args.status:
        show_status(client, account, paper)
        return

    print_account_summary(account, paper)

    # Load screener results
    print("  Loading screener results...")
    candidates = load_screener_results(cfg, top_n=args.top, min_score=args.min_score)
    if candidates.empty:
        return

    print(f"  {len(candidates)} candidates ready for trading\n")

    # Execute
    trades = execute_trades(client, account, candidates, cfg, dry_run=args.dry_run)

    # Log
    if trades and not args.dry_run:
        save_trade_log(trades, cfg)

    print("\n  Done.\n")


if __name__ == "__main__":
    main()
