"""
screener.py — Stock screener aligned with AutoTrade's scoring logic.

Reads daily_features.parquet from YfinanceDownloader, scores every stock
across momentum/trend/volume/pullback/volatility factors, and outputs
ranked trade candidates with entry/stop/target prices.

Usage:
    python screener.py                    # Run with defaults
    python screener.py --top 20           # Show top 20 only
    python screener.py --scan momentum    # Only momentum breakout scan
    python screener.py --ai               # Enable AI summaries (requires API key)

Scoring formulas are ported directly from AutoTrade's universe scanner
and screener_v2 modules.
"""

import argparse
import sys
import os
import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# ── Load Config ──────────────────────────────────────────────────

def load_config():
    """Load screen_config.py, fall back to screen_config.example.py."""
    config = {}
    config_file = "screen_config.py"
    if not os.path.exists(config_file):
        config_file = "screen_config.example.py"
        if not os.path.exists(config_file):
            print("ERROR: No screen_config.py or screen_config.example.py found.")
            print("Copy screen_config.example.py to screen_config.py and edit it.")
            sys.exit(1)
    # Load config as module dict
    with open(config_file, "r") as f:
        exec(f.read(), config)
    return config


# ── Universe Filtering ───────────────────────────────────────────

def filter_universe(df, cfg):
    """Apply hard filters to remove untradeable stocks."""
    latest = df.groupby("ticker").tail(1).copy()

    # Price filter
    mask = (latest["Close"] >= cfg.get("MIN_PRICE", 1.0)) & \
           (latest["Close"] <= cfg.get("MAX_PRICE", 350.0))

    # Volume filter (use Volume SMA 20 if available, else raw Volume)
    vol_col = "Volume_SMA_20" if "Volume_SMA_20" in latest.columns else "Volume"
    mask &= latest[vol_col] >= cfg.get("MIN_AVG_VOLUME", 500_000)

    # ATR% filter
    if "ATR_14" in latest.columns:
        atr_pct = (latest["ATR_14"] / latest["Close"]) * 100
        mask &= (atr_pct >= cfg.get("MIN_ATR_PCT", 0.5)) & \
                (atr_pct <= cfg.get("MAX_ATR_PCT", 8.0))

    valid_tickers = latest.loc[mask, "ticker"].unique()
    print(f"  Universe: {len(latest)} tickers -> {len(valid_tickers)} after filters")
    return df[df["ticker"].isin(valid_tickers)].copy()


# ── Factor Scoring Functions ─────────────────────────────────────
# Each returns a 0-100 score per stock, matching AutoTrade's formulas.

def score_momentum(row):
    """Momentum score: ROC + MACD histogram + weekly return.
    Weight: 30% of composite (AutoTrade universe scanner)."""
    score = 50.0

    # ROC component (if available)
    if "ROC_10" in row.index and pd.notna(row.get("ROC_10")):
        roc = np.clip(row["ROC_10"], -10, 10)
        score += roc * 2.0
    elif "ROC_5" in row.index and pd.notna(row.get("ROC_5")):
        roc = np.clip(row["ROC_5"], -10, 10)
        score += roc * 2.0

    # MACD histogram component
    if "MACD_Histogram" in row.index and pd.notna(row.get("MACD_Histogram")):
        close = row["Close"] if row["Close"] > 0 else 1
        macd_norm = (row["MACD_Histogram"] / close) * 100
        score += np.clip(macd_norm * 8, -15, 15)

    # Weekly return component (5-day return as proxy)
    if "Close_lag_5" in row.index and pd.notna(row.get("Close_lag_5")):
        weekly_ret = ((row["Close"] - row["Close_lag_5"]) / row["Close_lag_5"]) * 100
        score += np.clip(weekly_ret * 1.5, -15, 15)

    return np.clip(score, 0, 100)


def score_trend(row):
    """Trend score: SMA alignment + ADX strength.
    Weight: 15% of composite (AutoTrade screener_v2)."""
    score = 0.0

    # SMA alignment (Close > SMA20: 40pts, > SMA50: 30pts, > SMA200: 30pts)
    close = row["Close"]
    if "SMA_20" in row.index and pd.notna(row.get("SMA_20")):
        if close > row["SMA_20"]:
            score += 40
    if "SMA_50" in row.index and pd.notna(row.get("SMA_50")):
        if close > row["SMA_50"]:
            score += 30
    elif "EMA_20" in row.index and pd.notna(row.get("EMA_20")):
        # Fallback to EMA if SMA_50 not available
        if close > row["EMA_20"]:
            score += 30
    if "SMA_200" in row.index and pd.notna(row.get("SMA_200")):
        if close > row["SMA_200"]:
            score += 30

    # ADX trend quality bonus
    if "ADX" in row.index and pd.notna(row.get("ADX")):
        adx = row["ADX"]
        if adx > 30:
            score = score * 0.5 + 100 * 0.5  # Strong trend boost
        elif adx > 20:
            score = score * 0.6 + 60 * 0.4
        # ADX < 20: no trend, keep SMA score as-is

    return np.clip(score, 0, 100)


def score_volume(row):
    """Volume score: current volume vs 20-day average.
    Weight: 25% of composite (AutoTrade: volume_surge_score)."""
    vol_ratio = 1.0

    if "Volume_SMA_20" in row.index and pd.notna(row.get("Volume_SMA_20")):
        avg_vol = row["Volume_SMA_20"]
        if avg_vol > 0:
            vol_ratio = row["Volume"] / avg_vol
    elif "Volume_Ratio" in row.index and pd.notna(row.get("Volume_Ratio")):
        vol_ratio = row["Volume_Ratio"]

    # AutoTrade formula: 40 + volume_ratio * 20, clipped 0.2-4.0x
    ratio_clamped = np.clip(vol_ratio, 0.2, 4.0)
    score = 40 + ratio_clamped * 20

    return np.clip(score, 0, 100)


def score_pullback(row):
    """RSI pullback score: sweet-spot detection for entry timing.
    Weight: 10% of composite (AutoTrade: rsi_pullback_score)."""
    if "RSI_14" not in row.index or pd.isna(row.get("RSI_14")):
        return 50.0  # neutral default

    rsi = row["RSI_14"]

    # AutoTrade's RSI pullback scoring
    if 35 <= rsi <= 65:
        return 100.0   # Sweet spot
    elif (30 <= rsi < 35) or (65 < rsi <= 70):
        return 75.0     # Acceptable
    elif (25 <= rsi < 30) or (70 < rsi <= 75):
        return 55.0     # Edge case (potential reversal)
    elif rsi < 25:
        return 55.0     # Deeply oversold (mean reversion opportunity)
    else:  # rsi > 75
        return 35.0     # Overbought (caution)


def score_volatility(row):
    """Volatility score: ATR in Goldilocks zone.
    Weight: 20% of composite (AutoTrade: atr_pct scoring)."""
    if "ATR_14" not in row.index or pd.isna(row.get("ATR_14")):
        return 50.0

    close = row["Close"] if row["Close"] > 0 else 1
    atr_pct = (row["ATR_14"] / close) * 100

    # AutoTrade target: 1.5% ATR is ideal. Score drops as you move away.
    atr_mid = 1.5
    deviation = abs(atr_pct - atr_mid)
    score = (1 - min(deviation / 3.0, 1.0)) * 100

    return np.clip(score, 0, 100)


def score_mean_reversion(row):
    """Mean reversion score for oversold bounce candidates."""
    score = 0.0
    rsi = row.get("RSI_14", 50)
    if pd.isna(rsi):
        rsi = 50

    # Bollinger Band position (lower = more oversold)
    bb_pos = 50.0
    if "BB_Lower" in row.index and "BB_Upper" in row.index:
        bb_lower = row.get("BB_Lower", 0)
        bb_upper = row.get("BB_Upper", 0)
        if pd.notna(bb_lower) and pd.notna(bb_upper) and bb_upper > bb_lower:
            bb_pos = ((row["Close"] - bb_lower) / (bb_upper - bb_lower)) * 100

    # AutoTrade mean reversion scoring
    if rsi < 10 and bb_pos < 20:
        score = 90
    elif rsi < 20:
        score = 70
    elif rsi < 30:
        score = 55
    elif rsi > 80:
        score = 20
    else:
        score = 40

    return np.clip(score, 0, 100)


# ── Scan Type Classification ────────────────────────────────────

def classify_scan_type(row, cfg):
    """Classify each stock into a signal family."""
    scan_types = []

    rsi = row.get("RSI_14", 50)
    if pd.isna(rsi):
        rsi = 50
    close = row["Close"]

    # Volume ratio
    vol_ratio = 1.0
    if "Volume_SMA_20" in row.index and pd.notna(row.get("Volume_SMA_20")):
        avg_vol = row["Volume_SMA_20"]
        if avg_vol > 0:
            vol_ratio = row["Volume"] / avg_vol

    # Weekly return proxy
    weekly_ret = 0.0
    if "Close_lag_5" in row.index and pd.notna(row.get("Close_lag_5")):
        if row["Close_lag_5"] > 0:
            weekly_ret = ((close - row["Close_lag_5"]) / row["Close_lag_5"]) * 100

    sma_20 = row.get("SMA_20", close)
    if pd.isna(sma_20):
        sma_20 = close

    # Momentum breakout
    if cfg.get("SCAN_MOMENTUM_BREAKOUT", True):
        if (weekly_ret > cfg.get("MOMENTUM_MIN_WEEKLY_RETURN", 1.0) and
            cfg.get("MOMENTUM_RSI_MIN", 30) <= rsi <= cfg.get("MOMENTUM_RSI_MAX", 70) and
            vol_ratio >= cfg.get("MOMENTUM_MIN_VOLUME_RATIO", 1.5) and
            close > sma_20):
            scan_types.append("momentum_breakout")

    # Mean reversion
    if cfg.get("SCAN_MEAN_REVERSION", True):
        if (weekly_ret < cfg.get("REVERSION_MAX_WEEKLY_RETURN", -3.0) and
            rsi < cfg.get("REVERSION_RSI_MAX", 35) and
            vol_ratio >= cfg.get("REVERSION_MIN_VOLUME_RATIO", 2.0)):
            scan_types.append("mean_reversion")

    # Breakout (Bollinger squeeze)
    if cfg.get("SCAN_BREAKOUT", True):
        if "BB_Width" in row.index and pd.notna(row.get("BB_Width")):
            if (row["BB_Width"] <= cfg.get("BREAKOUT_BB_WIDTH_MIN", 0.03) and
                vol_ratio >= cfg.get("BREAKOUT_MIN_VOLUME_RATIO", 1.5)):
                scan_types.append("breakout")

    if not scan_types:
        scan_types.append("general")

    return scan_types[0]  # Primary scan type


# ── Entry / Stop / Target Calculation ────────────────────────────

def compute_trade_levels(row):
    """Calculate entry, stop loss, and target price using ATR."""
    close = row["Close"]
    atr = row.get("ATR_14", close * 0.02)  # Default 2% if no ATR
    if pd.isna(atr) or atr <= 0:
        atr = close * 0.02

    entry = close
    stop = close - (atr * 2.0)     # 2 ATR stop (AutoTrade default)
    target = close + (atr * 2.2)   # 2.2 ATR target (matches AutoTrade target_mult base)

    risk = entry - stop
    reward = target - entry
    rr_ratio = reward / risk if risk > 0 else 0

    return pd.Series({
        "entry_price": round(entry, 2),
        "stop_price": round(stop, 2),
        "target_price": round(target, 2),
        "risk_reward": round(rr_ratio, 2),
    })


# ── Composite Scoring ────────────────────────────────────────────

def score_universe(df, cfg):
    """Score every stock in the universe and return ranked results."""
    latest = df.groupby("ticker").tail(1).copy()
    print(f"  Scoring {len(latest)} stocks...")

    # Compute individual factor scores
    latest["momentum_score"] = latest.apply(score_momentum, axis=1)
    latest["trend_score"] = latest.apply(score_trend, axis=1)
    latest["volume_score"] = latest.apply(score_volume, axis=1)
    latest["pullback_score"] = latest.apply(score_pullback, axis=1)
    latest["volatility_score"] = latest.apply(score_volatility, axis=1)
    latest["mean_reversion_score"] = latest.apply(score_mean_reversion, axis=1)

    # Classify scan type
    latest["scan_type"] = latest.apply(lambda r: classify_scan_type(r, cfg), axis=1)

    # Composite score (weighted sum — matches AutoTrade universe scanner weights)
    w_m = cfg.get("WEIGHT_MOMENTUM", 0.30)
    w_t = cfg.get("WEIGHT_TREND", 0.15)
    w_v = cfg.get("WEIGHT_VOLUME", 0.25)
    w_p = cfg.get("WEIGHT_PULLBACK", 0.10)
    w_vol = cfg.get("WEIGHT_VOLATILITY", 0.20)

    latest["score"] = (
        latest["momentum_score"] * w_m +
        latest["trend_score"] * w_t +
        latest["volume_score"] * w_v +
        latest["pullback_score"] * w_p +
        latest["volatility_score"] * w_vol
    ).round(1)

    # For mean reversion candidates, blend in reversion score
    mr_mask = latest["scan_type"] == "mean_reversion"
    if mr_mask.any():
        latest.loc[mr_mask, "score"] = (
            latest.loc[mr_mask, "mean_reversion_score"] * 0.40 +
            latest.loc[mr_mask, "volume_score"] * 0.30 +
            latest.loc[mr_mask, "volatility_score"] * 0.20 +
            latest.loc[mr_mask, "pullback_score"] * 0.10
        ).round(1)

    # Compute trade levels
    levels = latest.apply(compute_trade_levels, axis=1)
    latest = pd.concat([latest, levels], axis=1)

    # ATR %
    latest["atr_pct"] = ((latest.get("ATR_14", latest["Close"] * 0.02) / latest["Close"]) * 100).round(2)

    # Sort by score descending
    latest = latest.sort_values("score", ascending=False).reset_index(drop=True)

    return latest


# ── AI Summary Layer (Optional) ──────────────────────────────────

def generate_ai_summaries(results_df, cfg):
    """Generate AI trade summaries for top picks. Requires API key in config."""
    api_key = cfg.get("AI_API_KEY", "")
    if not api_key:
        return results_df

    try:
        import httpx
    except ImportError:
        try:
            import requests as httpx
            httpx.Client = None  # flag that we're using requests
        except ImportError:
            print("  AI summaries skipped: install httpx or requests")
            return results_df

    base_url = cfg.get("AI_BASE_URL", "https://api.openai.com/v1")
    model = cfg.get("AI_MODEL", "gpt-4o-mini")
    max_picks = cfg.get("AI_MAX_PICKS_TO_SUMMARIZE", 10)

    print(f"  Generating AI summaries for top {max_picks} picks ({model})...")

    summaries = []
    top = results_df.head(max_picks)

    for _, row in top.iterrows():
        prompt = (
            f"You are a professional equity analyst. Give a 2-3 sentence trade summary for {row['ticker']}.\n"
            f"Price: ${row['Close']:.2f} | RSI: {row.get('RSI_14', 'N/A'):.0f} | "
            f"Score: {row['score']:.0f}/100 | Scan: {row['scan_type']}\n"
            f"Entry: ${row['entry_price']} | Stop: ${row['stop_price']} | Target: ${row['target_price']} | R:R: {row['risk_reward']}\n"
            f"Momentum: {row['momentum_score']:.0f} | Trend: {row['trend_score']:.0f} | "
            f"Volume: {row['volume_score']:.0f} | ATR%: {row['atr_pct']:.1f}%\n"
            f"Be concise. State the setup type, key risk, and actionable bias (long/avoid/wait)."
        )

        try:
            import httpx as _httpx
            with _httpx.Client(timeout=30) as client:
                resp = client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": 150, "temperature": 0.3},
                )
                resp.raise_for_status()
                summary = resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            try:
                import requests
                resp = requests.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": 150, "temperature": 0.3},
                    timeout=30,
                )
                resp.raise_for_status()
                summary = resp.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                summary = f"(AI unavailable: {e})"

        summaries.append(summary)

    results_df.loc[results_df.index[:max_picks], "ai_summary"] = summaries
    return results_df


# ── Output Formatting ────────────────────────────────────────────

def print_results(results, top_n, show_ai=False):
    """Print results to terminal in a readable format."""
    top = results.head(top_n)

    print()
    print("=" * 90)
    print(f"  TOP {len(top)} TRADE CANDIDATES — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 90)

    for i, (_, row) in enumerate(top.iterrows(), 1):
        scan_label = row["scan_type"].upper().replace("_", " ")
        rsi_str = f"{row['RSI_14']:.0f}" if pd.notna(row.get('RSI_14')) else "N/A"

        print(f"\n  #{i:>2}  {row['ticker']:<6}  ${row['Close']:>8.2f}  "
              f"Score: {row['score']:>5.1f}  [{scan_label}]")
        print(f"       Entry: ${row['entry_price']:>8.2f}  "
              f"Stop: ${row['stop_price']:>8.2f}  "
              f"Target: ${row['target_price']:>8.2f}  "
              f"R:R: {row['risk_reward']:.1f}")
        print(f"       RSI: {rsi_str:>3}  "
              f"Mom: {row['momentum_score']:>3.0f}  "
              f"Trend: {row['trend_score']:>3.0f}  "
              f"Vol: {row['volume_score']:>3.0f}  "
              f"ATR%: {row['atr_pct']:.1f}%")

        if show_ai and "ai_summary" in row.index and pd.notna(row.get("ai_summary")):
            print(f"       AI: {row['ai_summary']}")

    print()
    print("=" * 90)

    # Stats summary
    scan_counts = top["scan_type"].value_counts()
    parts = [f"{t}: {c}" for t, c in scan_counts.items()]
    print(f"  Signal breakdown: {' | '.join(parts)}")
    print(f"  Score range: {top['score'].min():.1f} - {top['score'].max():.1f}")
    print("=" * 90)


def save_results(results, output_file, top_n):
    """Save top candidates to CSV."""
    cols = ["ticker", "Close", "score", "scan_type",
            "entry_price", "stop_price", "target_price", "risk_reward",
            "momentum_score", "trend_score", "volume_score",
            "pullback_score", "volatility_score", "atr_pct"]

    if "ai_summary" in results.columns:
        cols.append("ai_summary")

    # Only include columns that exist
    cols = [c for c in cols if c in results.columns]
    top = results.head(top_n)[cols]
    top.to_csv(output_file, index=False)
    print(f"\n  Saved {len(top)} candidates to {output_file}")


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Screen stocks using AutoTrade-aligned quantitative scoring."
    )
    parser.add_argument("--top", type=int, default=None,
                        help="Number of top picks to show (default: from config)")
    parser.add_argument("--scan", type=str, default=None,
                        choices=["momentum", "reversion", "breakout", "all"],
                        help="Run only a specific scan type")
    parser.add_argument("--ai", action="store_true",
                        help="Enable AI trade summaries (requires API key in config)")
    parser.add_argument("--input", type=str, default=None,
                        help="Path to features parquet file")
    parser.add_argument("--output", type=str, default=None,
                        help="Output CSV path")

    args = parser.parse_args()
    cfg = load_config()

    # Override config with CLI args
    if args.scan:
        cfg["SCAN_MOMENTUM_BREAKOUT"] = args.scan in ("momentum", "all")
        cfg["SCAN_MEAN_REVERSION"] = args.scan in ("reversion", "all")
        cfg["SCAN_BREAKOUT"] = args.scan in ("breakout", "all")

    input_file = args.input or cfg.get("FEATURES_PARQUET", "daily_features.parquet")
    output_file = args.output or cfg.get("OUTPUT_CSV", "screener_results.csv")
    top_n = args.top or cfg.get("TOP_N", 50)

    print()
    print("============================================================")
    print("  YfinanceDownloader — Stock Screener")
    print("  Scoring engine aligned with AutoTrade signal pipeline")
    print("============================================================")

    # Load data
    print(f"\n  Loading {input_file}...")
    if not os.path.exists(input_file):
        print(f"  ERROR: {input_file} not found.")
        print("  Run generate.py first to create the features file.")
        sys.exit(1)

    df = pd.read_parquet(input_file)
    print(f"  Loaded {len(df):,} rows, {df['ticker'].nunique():,} tickers")

    # Filter universe
    print("\n  Applying universe filters...")
    df = filter_universe(df, cfg)

    if df.empty:
        print("  No stocks passed filters. Check your config thresholds.")
        sys.exit(1)

    # Score everything
    print("\n  Running signal scoring...")
    results = score_universe(df, cfg)

    # AI summaries (optional)
    use_ai = args.ai or bool(cfg.get("AI_API_KEY", ""))
    if use_ai and cfg.get("AI_API_KEY", ""):
        results = generate_ai_summaries(results, cfg)

    # Output
    print_results(results, top_n, show_ai=use_ai)
    save_results(results, output_file, top_n)

    print("\n  Done!")
    print("============================================================")


if __name__ == "__main__":
    main()
