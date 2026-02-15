#!/usr/bin/env python3
"""
YfinanceDownloader - NASDAQ Stock Price Downloader

Downloads daily and hourly stock price data from Yahoo Finance for stocks
listed in the NASDAQ screener within a configurable price range.

Usage:
    python downloader.py --init          # Initial download of all stocks
    python downloader.py --update        # Update existing data files
    python downloader.py --reconcile     # Reconcile stocks with NASDAQ screener
    python downloader.py --all           # Reconcile + update (+ init if needed)
    python downloader.py --dry-run       # Preview changes without downloading

    daily.bat                            # One-click: runs --all (Windows)
"""

import argparse
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

# Import configuration
from config import (
    MIN_PRICE,
    MAX_PRICE,
    START_DATE,
    END_DATE,
    DAILY_CSV,
    HOURLY_CSV,
    NASDAQ_SCREENER,
    BATCH_SIZE,
    PAUSE_AFTER_BATCHES,
    PAUSE_DURATION_SECONDS,
    INVALID_TICKER_PATTERNS,
    HOURLY_MAX_DAYS,
)


# ============================================================================
# Configuration Classes
# ============================================================================


@dataclass(frozen=True)
class TargetConfig:
    """Configuration for a single CSV update target."""

    label: str
    csv_path: Path
    interval_value: str
    yf_interval: str
    time_col: str
    tz_aware: bool
    step: timedelta
    end_pad: timedelta


# ============================================================================
# Utility Functions
# ============================================================================


def parse_price(price_str: str) -> Optional[float]:
    """Parse price from string like '$125.81' to float."""
    if pd.isna(price_str) or price_str == "" or str(price_str).strip() == "":
        return None
    try:
        clean = str(price_str).replace("$", "").replace(",", "").strip()
        return float(clean)
    except (ValueError, TypeError):
        return None


def has_special_chars(ticker) -> bool:
    """Check if ticker contains invalid special characters."""
    if pd.isna(ticker):
        return True
    return bool(re.search(INVALID_TICKER_PATTERNS, str(ticker)))


def ensure_flat_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Flatten MultiIndex columns returned by yfinance."""
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame.columns = [str(col) for col in frame.columns]
    return frame


def format_time_column(series: pd.Series, tz_aware: bool) -> List[str]:
    """Format time column for CSV output."""
    from datetime import timezone

    if tz_aware:
        return [
            ts.to_pydatetime().isoformat(sep=" ", timespec="seconds")
            for ts in series.dt.tz_convert(timezone.utc)
        ]
    return series.dt.strftime("%Y-%m-%d").tolist()


def _chunked(sequence: Sequence[str], size: int):
    """Split sequence into chunks of specified size."""
    for start in range(0, len(sequence), size):
        yield sequence[start : start + size]


# ============================================================================
# Data Loading Functions
# ============================================================================


def load_nasdaq_screener(screener_path: str) -> pd.DataFrame:
    """Load and filter NASDAQ screener data based on configuration."""
    print(f"Loading NASDAQ screener from {screener_path}...")

    if not Path(screener_path).exists():
        print(f"ERROR: NASDAQ screener file not found: {screener_path}")
        print(
            "Please download it from https://www.nasdaq.com/market-activity/stocks/screener"
        )
        sys.exit(1)

    df = pd.read_csv(screener_path, dtype={"Symbol": str, "Last Sale": str})

    # Parse Last Sale prices
    df["LastPrice"] = df["Last Sale"].apply(parse_price)

    # Filter by price range from config
    df_valid = df[
        (df["LastPrice"] >= MIN_PRICE) & (df["LastPrice"] <= MAX_PRICE)
    ].copy()

    # Remove tickers with special characters
    df_valid = df_valid[~df_valid["Symbol"].apply(has_special_chars)]

    print(f"  Loaded {len(df)} total stocks")
    print(f"  {len(df_valid)} stocks in ${MIN_PRICE}-{MAX_PRICE} range")

    return df_valid


def get_csv_info(csv_path: Path) -> Tuple[List[str], datetime, datetime]:
    """Get tickers and date range from CSV."""
    if not csv_path.exists():
        return [], datetime.min, datetime.max

    time_col = "Datetime" if "hourly" in str(csv_path).lower() else "Date"
    df = pd.read_csv(csv_path, usecols=["ticker", time_col])
    df[time_col] = pd.to_datetime(df[time_col])

    tickers = df["ticker"].unique().tolist()
    min_date = df[time_col].min()
    max_date = df[time_col].max()

    return tickers, min_date, max_date


# ============================================================================
# Download Functions
# ============================================================================


def download_ticker_data(
    ticker: str, start: datetime, end: datetime, interval: str
) -> Optional[pd.DataFrame]:
    """Download historical price data for a single ticker."""
    try:
        data = yf.download(
            tickers=ticker,
            interval=interval,
            start=start,
            end=end + timedelta(days=1),
            progress=False,
            auto_adjust=False,
            actions=False,
            prepost=False,
            threads=False,
        )

        if data.empty:
            return None

        df = data.reset_index()
        df = ensure_flat_columns(df)
        return df

    except Exception as e:
        print(f"    ERROR downloading {ticker}: {e}")
        return None


def format_daily_data(raw_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Format raw yfinance data to match daily CSV format."""
    if raw_df.empty:
        return pd.DataFrame()

    df = raw_df.copy()

    # Map columns (handle yfinance's ticker-appended column names)
    column_mapping = {}
    for col in df.columns:
        col_str = str(col).lower().strip()
        if col_str == "date":
            column_mapping[col] = "Date"
        elif "adj" in col_str and "close" in col_str:
            column_mapping[col] = "Adj Close"
        elif "close" in col_str:
            column_mapping[col] = "Close"
        elif "high" in col_str:
            column_mapping[col] = "High"
        elif "low" in col_str:
            column_mapping[col] = "Low"
        elif "open" in col_str:
            column_mapping[col] = "Open"
        elif "volume" in col_str:
            column_mapping[col] = "Volume"

    df = df.rename(columns=column_mapping)

    required_cols = ["Date", "Adj Close", "Close", "High", "Low", "Open", "Volume"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return pd.DataFrame()

    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df.insert(0, "ticker", ticker)
    df.insert(1, "interval", "daily")
    df["Volume"] = df["Volume"].fillna(0).astype("Int64")

    return df[
        [
            "ticker",
            "interval",
            "Date",
            "Adj Close",
            "Close",
            "High",
            "Low",
            "Open",
            "Volume",
        ]
    ]


def format_hourly_data(raw_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Format raw yfinance data to match hourly CSV format."""
    if raw_df.empty:
        return pd.DataFrame()

    df = raw_df.copy()

    # Map columns
    column_mapping = {}
    for col in df.columns:
        col_str = str(col).lower().strip()
        if "datetime" in col_str or col_str == "date":
            column_mapping[col] = "Datetime"
        elif "adj" in col_str and "close" in col_str:
            column_mapping[col] = "Adj Close"
        elif "close" in col_str:
            column_mapping[col] = "Close"
        elif "high" in col_str:
            column_mapping[col] = "High"
        elif "low" in col_str:
            column_mapping[col] = "Low"
        elif "open" in col_str:
            column_mapping[col] = "Open"
        elif "volume" in col_str:
            column_mapping[col] = "Volume"

    df = df.rename(columns=column_mapping)

    required_cols = ["Datetime", "Adj Close", "Close", "High", "Low", "Open", "Volume"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return pd.DataFrame()

    df["Datetime"] = pd.to_datetime(df["Datetime"])
    if df["Datetime"].dt.tz is None:
        df["Datetime"] = df["Datetime"].dt.tz_localize("UTC")
    else:
        df["Datetime"] = df["Datetime"].dt.tz_convert("UTC")

    df.insert(0, "ticker", ticker)
    df.insert(1, "interval", "hourly")
    df["Volume"] = df["Volume"].fillna(0).astype("Int64")

    return df[
        [
            "ticker",
            "interval",
            "Datetime",
            "Adj Close",
            "Close",
            "High",
            "Low",
            "Open",
            "Volume",
        ]
    ]


# ============================================================================
# Initial Download
# ============================================================================


def initial_download(tickers: List[str], dry_run: bool = False):
    """Download initial historical data for all tickers."""
    print(f"\n[INITIAL DOWNLOAD]")
    print(f"  Stocks to download: {len(tickers)}")

    # Determine date range
    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end = (
        datetime.now() if END_DATE is None else datetime.strptime(END_DATE, "%Y-%m-%d")
    )

    print(f"  Date range: {start.date()} to {end.date()}")

    # Warn user if requested range exceeds the hourly data limit
    total_days = (end - start).days
    if total_days > HOURLY_MAX_DAYS:
        hourly_earliest = (end - timedelta(days=HOURLY_MAX_DAYS)).date()
        print(f"\n  NOTE: Yahoo Finance only provides hourly data for the last ~2 years.")
        print(f"        Hourly data will start from {hourly_earliest} instead of {start.date()}.")
        print(f"        Daily data will still cover the full range.\n")

    if dry_run:
        print("  [DRY RUN] No data will be downloaded")
        return

    daily_path = Path(DAILY_CSV)
    hourly_path = Path(HOURLY_CSV)

    # Create empty CSVs with headers if they don't exist
    if not daily_path.exists():
        headers = [
            "ticker",
            "interval",
            "Date",
            "Adj Close",
            "Close",
            "High",
            "Low",
            "Open",
            "Volume",
        ]
        pd.DataFrame(columns=headers).to_csv(daily_path, index=False)

    if not hourly_path.exists():
        headers = [
            "ticker",
            "interval",
            "Datetime",
            "Adj Close",
            "Close",
            "High",
            "Low",
            "Open",
            "Volume",
        ]
        pd.DataFrame(columns=headers).to_csv(hourly_path, index=False)

    request_count = 0
    daily_added = 0
    hourly_added = 0
    failed = []

    for i, ticker in enumerate(tickers, 1):
        print(f"  [{i}/{len(tickers)}] Downloading {ticker}...")

        # Daily data
        daily_raw = download_ticker_data(ticker, start, end, "1d")
        if daily_raw is not None and not daily_raw.empty:
            daily_formatted = format_daily_data(daily_raw, ticker)
            if not daily_formatted.empty:
                daily_formatted.to_csv(daily_path, mode="a", header=False, index=False)
                daily_added += len(daily_formatted)
        else:
            failed.append(f"{ticker} (daily)")

        request_count += 1

        # Hourly data (limited to last ~2 years due to yfinance limits)
        hourly_start = max(start, end - timedelta(days=HOURLY_MAX_DAYS))
        hourly_raw = download_ticker_data(ticker, hourly_start, end, "1h")
        if hourly_raw is not None and not hourly_raw.empty:
            hourly_formatted = format_hourly_data(hourly_raw, ticker)
            if not hourly_formatted.empty:
                hourly_formatted.to_csv(
                    hourly_path, mode="a", header=False, index=False
                )
                hourly_added += len(hourly_formatted)
        else:
            failed.append(f"{ticker} (hourly)")

        request_count += 1

        # Rate limiting
        if request_count >= PAUSE_AFTER_BATCHES:
            print(f"\n  Rate limit: Pausing for {PAUSE_DURATION_SECONDS}s...")
            time.sleep(PAUSE_DURATION_SECONDS)
            request_count = 0

    print(f"\n[DOWNLOAD COMPLETE]")
    print(f"  Daily rows added: {daily_added}")
    print(f"  Hourly rows added: {hourly_added}")
    if failed:
        print(f"  Failed: {len(failed)} tickers")


# ============================================================================
# Update Functions (from update.py)
# ============================================================================


def load_latest_per_ticker(
    csv_path: Path, time_col: str, chunk_size: int = 100000
) -> Dict[str, datetime]:
    """Load the latest timestamp for each ticker from CSV."""
    latest_by_ticker: Dict[str, datetime] = {}

    try:
        for chunk in pd.read_csv(
            csv_path, usecols=["ticker", time_col], chunksize=chunk_size
        ):
            chunk[time_col] = pd.to_datetime(chunk[time_col])
            for ticker, group in chunk.groupby("ticker"):
                ticker = str(ticker).strip().upper()
                max_ts = group[time_col].max()
                if ticker not in latest_by_ticker or max_ts > latest_by_ticker[ticker]:
                    latest_by_ticker[ticker] = max_ts
    except FileNotFoundError:
        pass

    return latest_by_ticker


def update_data(
    cfg: TargetConfig, tickers: Optional[List[str]] = None, dry_run: bool = False
):
    """Update existing CSV with new data."""
    print(f"\n[UPDATE: {cfg.label}]")

    if not cfg.csv_path.exists():
        print(f"  ERROR: {cfg.csv_path} does not exist. Run --init first.")
        return

    # Get latest timestamps
    latest_by_ticker = load_latest_per_ticker(cfg.csv_path, cfg.time_col)

    if tickers:
        tickers_to_update = [t for t in tickers if t.upper() in latest_by_ticker]
    else:
        tickers_to_update = list(latest_by_ticker.keys())

    print(f"  Tickers to update: {len(tickers_to_update)}")

    if dry_run:
        print("  [DRY RUN] No updates will be made")
        return

    end_time = datetime.now() + cfg.end_pad
    headers = pd.read_csv(cfg.csv_path, nrows=0).columns.tolist()

    request_count = 0
    total_added = 0

    for batch_idx, batch in enumerate(_chunked(tickers_to_update, BATCH_SIZE), 1):
        print(f"  Batch {batch_idx}: Processing {len(batch)} tickers...")

        for ticker in batch:
            last_seen = latest_by_ticker.get(ticker.upper())
            if not last_seen:
                continue

            start = last_seen + cfg.step
            if start >= end_time:
                continue

            # Download new data
            data = download_ticker_data(ticker, start, end_time, cfg.yf_interval)

            if data is not None and not data.empty:
                # Format and filter
                if cfg.interval_value == "daily":
                    formatted = format_daily_data(data, ticker)
                else:
                    formatted = format_hourly_data(data, ticker)

                if not formatted.empty:
                    # Filter to only new data
                    time_col = cfg.time_col
                    formatted[time_col] = pd.to_datetime(formatted[time_col])
                    formatted = formatted[formatted[time_col] > pd.Timestamp(last_seen)]

                    if not formatted.empty:
                        formatted[time_col] = format_time_column(
                            formatted[time_col], cfg.tz_aware
                        )
                        formatted.to_csv(
                            cfg.csv_path, mode="a", header=False, index=False
                        )
                        total_added += len(formatted)

            request_count += 1

        # Rate limiting
        if request_count >= PAUSE_AFTER_BATCHES:
            print(f"  Rate limit: Pausing for {PAUSE_DURATION_SECONDS}s...")
            time.sleep(PAUSE_DURATION_SECONDS)
            request_count = 0

    print(f"  Added {total_added} new rows")


# ============================================================================
# Reconcile Functions
# ============================================================================


def reconcile_stocks(dry_run: bool = False):
    """Reconcile stock dataset with current NASDAQ listings."""
    print("\n[RECONCILING STOCKS]")

    daily_path = Path(DAILY_CSV)
    hourly_path = Path(HOURLY_CSV)

    # Load NASDAQ screener
    nasdaq_df = load_nasdaq_screener(NASDAQ_SCREENER)
    nasdaq_tickers = [t.upper() for t in nasdaq_df["Symbol"].tolist()]

    # Get current tickers
    current_daily, daily_min, daily_max = get_csv_info(daily_path)
    current_hourly, _, _ = get_csv_info(hourly_path)
    current_tickers = list(set(current_daily + current_hourly))

    # Identify changes
    to_remove = [
        t
        for t in current_tickers
        if t.upper() not in nasdaq_tickers and not has_special_chars(t)
    ]
    special_chars = [t for t in current_tickers if has_special_chars(t)]
    to_add = [
        t
        for t in nasdaq_tickers
        if t.upper() not in [ct.upper() for ct in current_tickers]
    ]

    print(f"\n  Current dataset: {len(current_tickers)} tickers")
    print(f"  NASDAQ screener: {len(nasdaq_tickers)} tickers")
    print(f"  To remove (not in NASDAQ): {len(to_remove)}")
    print(f"  To remove (special chars): {len(special_chars)}")
    print(f"  To add: {len(to_add)}")

    if dry_run:
        print("\n  [DRY RUN] No changes will be made")
        return

    # Remove invalid tickers
    all_to_remove = list(set(to_remove + special_chars))
    if all_to_remove and daily_path.exists():
        print(f"\n  Removing {len(all_to_remove)} invalid tickers...")
        remove_set = set(t.upper() for t in all_to_remove)

        # Remove from daily
        chunks = []
        for chunk in pd.read_csv(daily_path, chunksize=100000):
            mask = ~chunk["ticker"].str.upper().isin(remove_set)
            chunks.append(chunk[mask])
        pd.concat(chunks, ignore_index=True).to_csv(daily_path, index=False)

        # Remove from hourly
        if hourly_path.exists():
            chunks = []
            for chunk in pd.read_csv(hourly_path, chunksize=100000):
                mask = ~chunk["ticker"].str.upper().isin(remove_set)
                chunks.append(chunk[mask])
            pd.concat(chunks, ignore_index=True).to_csv(hourly_path, index=False)

    # Add new tickers
    if to_add:
        print(f"\n  Adding {len(to_add)} new tickers...")
        initial_download(to_add, dry_run=False)

    print("\n[RECONCILIATION COMPLETE]")


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="YfinanceDownloader - NASDAQ Stock Price Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python downloader.py --init              # Initial download of all stocks
  python downloader.py --update            # Update existing data
  python downloader.py --reconcile         # Sync with NASDAQ screener
  python downloader.py --all --dry-run     # Preview all operations
        """,
    )

    parser.add_argument(
        "--init", action="store_true", help="Initial download of all NASDAQ stocks"
    )
    parser.add_argument(
        "--update", action="store_true", help="Update existing data files"
    )
    parser.add_argument(
        "--reconcile", action="store_true", help="Reconcile stocks with NASDAQ screener"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run reconcile, update, and init if needed"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without downloading"
    )
    parser.add_argument("--tickers", nargs="+", help="Specific tickers to process")

    args = parser.parse_args()

    if not any([args.init, args.update, args.reconcile, args.all]):
        parser.print_help()
        sys.exit(0)

    print("=" * 60)
    print("YfinanceDownloader")
    print("=" * 60)
    print(f"Price Range: ${MIN_PRICE} - ${MAX_PRICE}")
    print(f"NASDAQ Screener: {NASDAQ_SCREENER}")
    print(f"Daily CSV: {DAILY_CSV}")
    print(f"Hourly CSV: {HOURLY_CSV}")

    # Check if the configured date range exceeds the hourly data limit
    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end = datetime.now() if END_DATE is None else datetime.strptime(END_DATE, "%Y-%m-%d")
    total_days = (end - start).days
    if total_days > HOURLY_MAX_DAYS:
        print(f"\nWARNING: START_DATE ({START_DATE}) is more than 2 years ago.")
        print(f"         Yahoo Finance only provides hourly data for the last ~{HOURLY_MAX_DAYS} days (~2 years).")
        print(f"         Hourly data will be limited accordingly. Daily data is unaffected.")

    print("=" * 60)

    # Reconcile
    if args.reconcile or args.all:
        reconcile_stocks(dry_run=args.dry_run)

    # Initial download
    if args.init or (args.all and not Path(DAILY_CSV).exists()):
        if args.tickers:
            tickers = args.tickers
        else:
            nasdaq_df = load_nasdaq_screener(NASDAQ_SCREENER)
            tickers = nasdaq_df["Symbol"].tolist()
        initial_download(tickers, dry_run=args.dry_run)

    # Update
    if args.update or args.all:
        # Daily update config
        daily_cfg = TargetConfig(
            label="Daily",
            csv_path=Path(DAILY_CSV),
            interval_value="daily",
            yf_interval="1d",
            time_col="Date",
            tz_aware=False,
            step=timedelta(days=1),
            end_pad=timedelta(days=1),
        )

        # Hourly update config
        hourly_cfg = TargetConfig(
            label="Hourly",
            csv_path=Path(HOURLY_CSV),
            interval_value="hourly",
            yf_interval="1h",
            time_col="Datetime",
            tz_aware=True,
            step=timedelta(hours=1),
            end_pad=timedelta(hours=1),
        )

        if Path(DAILY_CSV).exists():
            update_data(daily_cfg, args.tickers, dry_run=args.dry_run)

        if Path(HOURLY_CSV).exists():
            update_data(hourly_cfg, args.tickers, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
