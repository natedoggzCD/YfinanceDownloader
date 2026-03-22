"""
trader.py — Execute trades on Alpaca using screener results.

Reads screener_results.csv, connects to your Alpaca paper (or live) account,
sizes positions using R-Unit risk management with conviction scaling, and
places bracket orders (entry + stop-loss + take-profit) for top-scoring stocks.

Usage:
    python trader.py                    # Trade top picks (with confirmation)
    python trader.py --top 5            # Only trade top 5 picks
    python trader.py --dry-run          # Preview orders without placing them
    python trader.py --status           # Show current positions and account info

Requires:
    pip install alpaca-py
    Set your keys in config/config.yaml (the GUI writes this file).
"""

import argparse
import sys
import os
from datetime import datetime

import numpy as np
import pandas as pd

# ── Load Config ──────────────────────────────────────────────────

def _flatten_config(raw: dict) -> dict:
    """Flatten nested YAML config into the format this module expects."""
    cfg = {}
    trading = raw.get("trading", {})
    for key, val in trading.items():
        cfg[key.upper()] = val

    # Also load screener section for shared settings
    scr = raw.get("screener", {})
    cfg["FEATURES_PARQUET"] = scr.get("features_parquet", "data/daily_features.parquet")
    cfg["OUTPUT_CSV"] = scr.get("output_csv", "data/screener_results.csv")
    if "SCREENER_CSV" not in cfg:
        cfg["SCREENER_CSV"] = cfg.get("OUTPUT_CSV", "data/screener_results.csv")

    return cfg


def _load_yaml_config(yaml_path: str) -> dict:
    """Load a YAML config file as a nested dictionary."""
    try:
        import yaml
    except ImportError:
        return {}

    if not os.path.exists(yaml_path):
        return {}

    with open(yaml_path, "r") as f:
        return yaml.safe_load(f) or {}


def _merge_dicts(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> dict:
    """Load shared YAML config, overlaying local values onto example defaults."""
    defaults = _load_yaml_config("config/config.example.yaml")
    active = _load_yaml_config("config/config.yaml")
    merged = _merge_dicts(defaults, active)
    if not merged:
        print("ERROR: config/config.example.yaml is missing or unreadable.")
        sys.exit(1)
    return _flatten_config(merged)


def validate_keys(cfg: dict):
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
        print("  4. Click 'View' next to API Keys -> 'Generate New Key'")
        print("  5. Copy your API Key and Secret Key")
        print("  6. Paste them into config/config.yaml:")
        print()
        print('     ALPACA_API_KEY = "PKXXXXXXXXXXXXXXXX"')
        print('     ALPACA_SECRET_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"')
        print()
        print("  Paper trading = simulated trades with $100k fake money.")
        print("  No credit card. No real money. No risk.")
        print("=" * 65)
        sys.exit(1)


# ── Alpaca Connection ────────────────────────────────────────────

def connect_alpaca(cfg: dict):
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
        print("Check that your API keys in config/config.yaml are correct.")
        print("Dashboard: https://app.alpaca.markets/paper/dashboard/overview")
        sys.exit(1)

    return client, account


def print_account_summary(account, paper: bool):
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


# ── Position Sizing (R-Unit with Conviction Scaling) ─────────────

def calculate_position_size(entry_price: float, stop_price: float, equity: float,
                            cfg: dict, score: float = None) -> int:
    """
    R-Unit position sizing with optional conviction scaling.
    Ported from AutoTrade's RUnitSizer + ConvictionEngine.

    When conviction_scaling is enabled, higher-scoring picks get more risk
    budget (up to 1.5%) while lower-scoring picks get less (down to 0.5%).
    """
    base_risk_pct = cfg.get("RISK_PER_TRADE_PCT", 1.0) / 100.0
    max_notional_pct = cfg.get("MAX_POSITION_PCT", 8.0) / 100.0
    min_value = cfg.get("MIN_POSITION_VALUE", 100.0)

    # Conviction-scaled risk (from AutoTrade conviction_engine)
    if cfg.get("CONVICTION_SCALING", True) and score is not None:
        risk_range = cfg.get("CONVICTION_RISK_RANGE", [0.5, 1.5])
        low_risk = risk_range[0] / 100.0
        high_risk = risk_range[1] / 100.0
        # Linear interpolation: score 50 -> low_risk, score 100 -> high_risk
        t = np.clip((score - 50) / 50, 0, 1)
        risk_pct = low_risk + t * (high_risk - low_risk)
    else:
        risk_pct = base_risk_pct

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


# ── Portfolio Risk ───────────────────────────────────────────────

def calculate_portfolio_heat(client, equity: float) -> float:
    """Calculate total open risk as % of equity.
    Ported from AutoTrade's policy_engine total_risk_dollars calculation.
    Estimates risk per position as 4% of current value (conservative proxy)."""
    positions = client.get_all_positions()
    total_risk = 0.0

    for p in positions:
        qty = abs(float(p.qty))
        price = float(p.current_price)
        # Conservative estimate: risk = 4% of position value
        # (real implementation would track actual stop levels)
        risk_per_share = price * 0.04
        total_risk += qty * risk_per_share

    return (total_risk / equity) * 100 if equity > 0 else 0


# ── Load Screener Results ────────────────────────────────────────

def load_screener_results(cfg: dict, top_n: int = None, min_score: float = None) -> pd.DataFrame:
    """Load and filter screener results."""
    csv_path = cfg.get("SCREENER_CSV", "data/screener_results.csv")
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
        min_score = cfg.get("MIN_SCORE_TO_TRADE", 65.0)
    df = df[df["score"] >= min_score].copy()

    if df.empty:
        print(f"  No stocks scored {min_score}+ in {csv_path}.")
        print("  Try lowering MIN_SCORE_TO_TRADE in your config.")
        return df

    # Limit to top N
    if top_n:
        df = df.head(top_n)

    return df


# ── Get Current Positions ────────────────────────────────────────

def get_open_positions(client) -> dict:
    """Get current open positions as a dict of {symbol: position}."""
    positions = client.get_all_positions()
    return {p.symbol: p for p in positions}


# ── Order Placement ──────────────────────────────────────────────

def place_order(client, symbol: str, qty: int, side: str, order_type: str, time_in_force: str):
    """Place a single market order on Alpaca."""
    from alpaca.trading.requests import MarketOrderRequest
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


def place_bracket_order(client, symbol: str, qty: int,
                        stop_price: float, target_price: float):
    """Place a bracket order: market entry + stop-loss + take-profit.
    Ported from AutoTrade's execution adapter bracket order support."""
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

    request = MarketOrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.GTC,  # Bracket orders need GTC
        order_class=OrderClass.BRACKET,
        take_profit={"limit_price": round(target_price, 2)},
        stop_loss={"stop_price": round(stop_price, 2)},
    )
    return client.submit_order(request)


# ── Trade Execution ──────────────────────────────────────────────

def execute_trades(client, account, candidates: pd.DataFrame, cfg: dict,
                   dry_run: bool = False) -> list:
    """Size and place orders for screener candidates with full risk validation."""
    equity, cash = float(account.equity), float(account.cash)
    paper = cfg.get("PAPER_TRADING", True)
    order_type = cfg.get("ORDER_TYPE", "market")
    tif = cfg.get("TIME_IN_FORCE", "day")
    max_positions = cfg.get("MAX_POSITIONS", 10)
    cash_reserve_pct = cfg.get("MIN_CASH_RESERVE_PCT", 20.0) / 100.0
    use_brackets = cfg.get("USE_BRACKET_ORDERS", True)
    min_rr = cfg.get("MIN_RR_TO_TRADE", 1.5)
    atr_stop_check = cfg.get("ATR_STOP_VALIDATION", True)

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

    # Portfolio heat check (ported from AutoTrade policy_engine)
    max_heat = cfg.get("PORTFOLIO_HEAT_MAX_PCT", 6.0)
    heat = calculate_portfolio_heat(client, equity)
    print(f"  Portfolio heat: {heat:.1f}% / {max_heat}% max")

    if heat >= max_heat:
        print(f"\n  Portfolio heat {heat:.1f}% >= {max_heat}% cap. No new trades.")
        print("  Close or reduce existing positions first.")
        return []

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
            print(f"  {symbol}: SKIP -- already holding a position")
            continue

        entry = row.get("entry_price", row["Close"])
        stop = row.get("stop_price", entry * 0.96)
        target = row.get("target_price", entry * 1.04)
        score = row.get("score", 65)
        atr_pct = row.get("atr_pct", 0)

        # R:R validation
        risk = entry - stop
        rr = row.get("risk_reward", (target - entry) / risk if risk > 0 else 0)
        if rr < min_rr:
            print(f"  {symbol}: SKIP -- R:R {rr:.1f} < minimum {min_rr}")
            continue

        # ATR stop validation (verify stop distance is meaningful)
        if atr_stop_check and atr_pct > 0:
            stop_dist_pct = abs(entry - stop) / entry * 100 if entry > 0 else 0
            min_stop_atr_mult = 1.5
            if stop_dist_pct < atr_pct * min_stop_atr_mult:
                print(f"  {symbol}: SKIP -- stop too tight ({stop_dist_pct:.1f}% < {min_stop_atr_mult}x ATR {atr_pct:.1f}%)")
                continue

        # R-Unit sizing with conviction scaling
        qty = calculate_position_size(entry, stop, equity, cfg, score=score)
        if qty <= 0:
            print(f"  {symbol}: SKIP -- position too small (entry=${entry:.2f}, stop=${stop:.2f})")
            continue

        cost = qty * entry
        if cost > available_cash:
            print(f"  {symbol}: SKIP -- insufficient cash (need ${cost:,.2f}, have ${available_cash:,.2f})")
            continue

        orders_planned.append({
            "symbol": symbol,
            "qty": qty,
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_reward": rr,
            "cost": cost,
            "score": score,
            "scan_type": row.get("scan_type", "general"),
        })

        available_cash -= cost

    if not orders_planned:
        print("  No trades to place -- all candidates filtered out.")
        return []

    # Display order plan
    print(f"  {'─' * 80}")
    print(f"  {'Symbol':<8} {'Qty':>5} {'Entry':>9} {'Stop':>9} {'Target':>9} "
          f"{'R:R':>5} {'Cost':>11} {'Score':>6} {'Type':<10}")
    print(f"  {'─' * 80}")

    total_cost = 0
    for o in orders_planned:
        scan = o["scan_type"][:10]
        print(f"  {o['symbol']:<8} {o['qty']:>5} ${o['entry']:>7.2f} ${o['stop']:>7.2f} "
              f"${o['target']:>7.2f} {o['risk_reward']:>4.1f}x ${o['cost']:>9,.2f} "
              f"{o['score']:>5.0f} {scan:<10}")
        total_cost += o["cost"]
    print(f"  {'─' * 80}")
    order_type_label = "BRACKET" if use_brackets else "MARKET"
    print(f"  Total: {len(orders_planned)} orders  |  ${total_cost:>,.2f}  |  {order_type_label} orders")
    print()

    if dry_run:
        print("  DRY RUN -- no orders placed.")
        return orders_planned

    # Confirmation gate
    if cfg.get("CONFIRM_BEFORE_TRADING", True):
        mode_label = "PAPER" if paper else "*** LIVE ***"
        print(f"  Mode: {mode_label}")
        response = input(f"  Place these {len(orders_planned)} orders? (yes/no): ").strip().lower()
        if response not in ("yes", "y"):
            print("  Cancelled -- no orders placed.")
            return []

    # Place orders
    placed = []
    for o in orders_planned:
        try:
            if use_brackets:
                order = place_bracket_order(
                    client, o["symbol"], o["qty"], o["stop"], o["target"]
                )
            else:
                order = place_order(client, o["symbol"], o["qty"], "buy", order_type, tif)

            status = getattr(order, "status", "submitted")
            order_id = str(getattr(order, "id", ""))
            bracket_label = " [BRACKET]" if use_brackets else ""
            print(f"  + {o['symbol']}: {o['qty']} shares -- {status} (ID: {order_id[:8]}...){bracket_label}")
            o["order_id"] = order_id
            o["status"] = str(status)
            o["timestamp"] = datetime.now().isoformat()
            placed.append(o)
        except Exception as e:
            print(f"  x {o['symbol']}: FAILED -- {e}")
            # If bracket fails, try plain market order as fallback
            if use_brackets:
                try:
                    order = place_order(client, o["symbol"], o["qty"], "buy", order_type, tif)
                    status = getattr(order, "status", "submitted")
                    order_id = str(getattr(order, "id", ""))
                    print(f"    + {o['symbol']}: fallback market order -- {status}")
                    o["order_id"] = order_id
                    o["status"] = str(status)
                    o["timestamp"] = datetime.now().isoformat()
                    placed.append(o)
                    continue
                except Exception as e2:
                    print(f"    x {o['symbol']}: fallback also failed -- {e2}")
            o["order_id"] = ""
            o["status"] = f"failed: {e}"
            o["timestamp"] = datetime.now().isoformat()
            placed.append(o)

    return placed


# ── Trade Log ────────────────────────────────────────────────────

def save_trade_log(trades: list, cfg: dict):
    """Append placed trades to the trade log CSV."""
    if not trades:
        return

    log_path = cfg.get("logs/trade_log.csv", "logs/trade_log.csv")
    df = pd.DataFrame(trades)

    if os.path.exists(log_path):
        existing = pd.read_csv(log_path)
        df = pd.concat([existing, df], ignore_index=True)

    df.to_csv(log_path, index=False)
    print(f"\n  Trade log saved to {log_path}")


# ── Show Status ──────────────────────────────────────────────────

def show_status(client, account, paper: bool):
    """Display current positions and P&L."""
    equity, cash = print_account_summary(account, paper)

    # Portfolio heat
    heat = calculate_portfolio_heat(client, float(account.equity))
    print(f"  Portfolio heat: {heat:.1f}%\n")

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
