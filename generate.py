#!/usr/bin/env python3
"""
generate.py - Technical Feature Engineering for Daily Stock Data

Reads prices_daily.csv, computes technical indicators, lag features,
and rolling statistics, then saves the result to an HDF5 file.

Usage:
    python generate.py                                  # Default paths
    python generate.py --input prices_daily.csv --output daily_features.h5
    python generate.py --min-obs 252                    # Require 1 year of history
    python generate.py --stale-days 5                   # Skip tickers stale > 5 days
"""

import argparse
from datetime import timedelta

import numpy as np
import pandas as pd

from config import DAILY_CSV, STALE_TICKER_DAYS


# ============================================================================
# Technical Indicator Functions
# ============================================================================


def sma(series, window):
    """Simple moving average."""
    return series.rolling(window).mean()


def ema(series, span):
    """Exponential moving average."""
    return series.ewm(span=span, adjust=False).mean()


def rsi(series, window=14):
    """Relative Strength Index."""
    diff = series.diff(1)
    gain = diff.where(diff > 0, 0.0)
    loss = -diff.where(diff < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(series, fast=12, slow=26, signal=9):
    """MACD line, signal line, and histogram."""
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger_bands(series, window=20, n_std=2):
    """Bollinger Bands (middle, upper, lower)."""
    rolling_mean = series.rolling(window=window).mean()
    rolling_std = series.rolling(window=window).std()
    return rolling_mean, rolling_mean + rolling_std * n_std, rolling_mean - rolling_std * n_std


def stochastic_oscillator(high, low, close, window=14, smooth=3):
    """Stochastic Oscillator %K and %D."""
    lowest_low = low.rolling(window=window).min()
    highest_high = high.rolling(window=window).max()
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=smooth).mean()
    return k_percent, d_percent


def cci(high, low, close, window=20):
    """Commodity Channel Index."""
    tp = (high + low + close) / 3.0
    ma = tp.rolling(window=window).mean()
    md = (tp - ma).abs().rolling(window=window).mean()
    return (tp - ma) / (0.015 * md)


def adx(high, low, close, window=14):
    """Average Directional Index plus +DI and -DI."""
    high_diff = high - high.shift()
    low_diff = low.shift() - low
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_val = tr.rolling(window=window).mean()
    plus_dm = pd.Series(
        np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0),
        index=high.index,
    )
    minus_dm = pd.Series(
        np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0),
        index=high.index,
    )
    plus_di = 100 * (plus_dm.rolling(window=window).sum() / atr_val)
    minus_di = 100 * (minus_dm.rolling(window=window).sum() / atr_val)
    sum_di = plus_di + minus_di
    dx = 100 * (abs(plus_di - minus_di) / sum_di.replace(0, np.nan))
    adx_val = dx.rolling(window=window).mean()
    return adx_val, plus_di, minus_di


def atr(high, low, close, window=14):
    """Average True Range."""
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window=window).mean()


def obv(close, volume):
    """On-Balance Volume."""
    obv_values = [0]
    for current, previous, vol in zip(close[1:], close[:-1], volume[1:]):
        if current > previous:
            obv_values.append(obv_values[-1] + vol)
        elif current < previous:
            obv_values.append(obv_values[-1] - vol)
        else:
            obv_values.append(obv_values[-1])
    return pd.Series(obv_values, index=close.index)


def roc(series, window=12):
    """Rate of Change."""
    return ((series - series.shift(window)) / series.shift(window)) * 100


def ichimoku(high, low, close):
    """Ichimoku Cloud components."""
    tenkan = (high.rolling(window=9).max() + low.rolling(window=9).min()) / 2
    kijun = (high.rolling(window=26).max() + low.rolling(window=26).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    senkou_b = ((high.rolling(window=52).max() + low.rolling(window=52).min()) / 2).shift(26)
    chikou = close.shift(-26)
    return tenkan, kijun, senkou_a, senkou_b, chikou


# ============================================================================
# Feature Engineering
# ============================================================================


def add_technical_indicators(df):
    """Append a comprehensive set of technical indicators to the dataframe."""
    df["SMA_10"] = sma(df["Close"], 10)
    df["SMA_20"] = sma(df["Close"], 20)
    df["EMA_10"] = ema(df["Close"], 10)
    df["EMA_20"] = ema(df["Close"], 20)
    df["RSI_14"] = rsi(df["Close"], 14)

    macd_line, macd_signal, macd_hist = macd(df["Close"])
    df["MACD"] = macd_line
    df["MACD_signal"] = macd_signal
    df["MACD_hist"] = macd_hist

    mid, upper, lower = bollinger_bands(df["Close"])
    df["BB_mid"] = mid
    df["BB_upper"] = upper
    df["BB_lower"] = lower

    k_percent, d_percent = stochastic_oscillator(df["High"], df["Low"], df["Close"])
    df["Stoch_%K"] = k_percent
    df["Stoch_%D"] = d_percent

    df["CCI"] = cci(df["High"], df["Low"], df["Close"])

    adx_val, plus_di, minus_di = adx(df["High"], df["Low"], df["Close"])
    df["ADX"] = adx_val
    df["DI_plus"] = plus_di
    df["DI_minus"] = minus_di

    df["OBV"] = obv(df["Close"], df["Volume"])

    tenkan, kijun, senkou_a, senkou_b, chikou = ichimoku(
        df["High"], df["Low"], df["Close"]
    )
    df["Ichimoku_tenkan"] = tenkan
    df["Ichimoku_kijun"] = kijun
    df["Ichimoku_senkou_A"] = senkou_a
    df["Ichimoku_senkou_B"] = senkou_b
    df["Ichimoku_chikou"] = chikou

    # ATR calculations
    df["atr_5"] = atr(df["High"], df["Low"], df["Close"], window=5)
    df["atr_14"] = atr(df["High"], df["Low"], df["Close"], window=14)

    # ATR-based normalized metrics
    df["atr_ratio_5_14"] = df["atr_5"] / df["atr_14"].replace(0, np.nan)
    df["price_to_atr_5"] = df["Close"] / df["atr_5"].replace(0, np.nan)
    df["price_to_atr_14"] = df["Close"] / df["atr_14"].replace(0, np.nan)

    # Momentum indicators
    df["ROC_5"] = roc(df["Close"], window=5)
    df["ROC_10"] = roc(df["Close"], window=10)
    df["ROC_20"] = roc(df["Close"], window=20)

    # Price position metrics
    df["price_position_bb"] = (df["Close"] - df["BB_lower"]) / (
        df["BB_upper"] - df["BB_lower"]
    ).replace(0, np.nan)
    df["distance_from_sma20"] = (df["Close"] - df["SMA_20"]) / df["SMA_20"].replace(
        0, np.nan
    )

    # Volume indicators
    df["volume_sma_20"] = df["Volume"].rolling(window=20).mean()
    df["volume_ratio"] = df["Volume"] / df["volume_sma_20"].replace(0, np.nan)
    df["volume_roc_5"] = roc(df["Volume"], window=5)

    # Volatility expansion/contraction
    df["bb_width"] = (df["BB_upper"] - df["BB_lower"]) / df["BB_mid"].replace(
        0, np.nan
    )
    df["bb_width_sma"] = df["bb_width"].rolling(window=20).mean()
    df["bb_squeeze"] = df["bb_width"] / df["bb_width_sma"].replace(0, np.nan)

    # Trend strength
    df["ema_10_20_diff"] = (df["EMA_10"] - df["EMA_20"]) / df["EMA_20"].replace(
        0, np.nan
    )
    df["adx_di_diff"] = df["DI_plus"] - df["DI_minus"]

    return df


def add_lag_features(df, columns, lags=None):
    """Add lagged copies of specified columns."""
    if lags is None:
        lags = [1, 2, 3, 5, 10]
    for col in columns:
        for lag in lags:
            df[f"{col}_lag_{lag}"] = df[col].shift(lag)
    return df


def add_rolling_features(df, columns, windows=None):
    """Add rolling mean and std for each column over the requested windows."""
    if windows is None:
        windows = [5, 10, 20]
    for col in columns:
        for window in windows:
            df[f"{col}_roll_mean_{window}"] = df[col].rolling(window=window).mean()
            df[f"{col}_roll_std_{window}"] = df[col].rolling(window=window).std()
    return df


def filter_active_tickers(df, min_obs=252, date_col="Date", last_date=None):
    """Keep tickers with sufficient data history and optional recency."""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.groupby("ticker").filter(lambda x: len(x) >= min_obs)
    if last_date is not None:
        last_date = pd.to_datetime(last_date)
        df = df.groupby("ticker").filter(lambda x: x[date_col].max() >= last_date)
    return df


def load_daily_data(file_path):
    """Load the daily CSV file while gracefully skipping malformed rows."""
    skipped = {"count": 0}

    def _skip_malformed_line(_):
        skipped["count"] += 1
        return None

    df = pd.read_csv(
        file_path,
        parse_dates=["Date"],
        engine="python",
        on_bad_lines=_skip_malformed_line,
    )
    return df, skipped["count"]


# ============================================================================
# Main Feature Generation
# ============================================================================


def generate_features(
    daily_path="prices_daily.csv",
    output_path="daily_features.h5",
    min_obs=100,
    stale_days=None,
):
    """Read price data, compute indicators, and persist the engineered features."""
    if stale_days is None:
        stale_days = STALE_TICKER_DAYS

    daily_data, skipped = load_daily_data(daily_path)

    print(
        f"Loaded {daily_data['ticker'].nunique()} tickers "
        f"({len(daily_data):,} rows) from {daily_path}"
    )
    if skipped:
        print(f"Skipped {skipped} malformed rows.")

    daily_data["Date"] = pd.to_datetime(daily_data["Date"])
    print(
        f"Source date range: {daily_data['Date'].min()} to {daily_data['Date'].max()}"
    )

    # Calculate reference date (95th percentile to avoid outliers)
    max_dates_per_ticker = daily_data.groupby("ticker")["Date"].max()
    reference_date = pd.Timestamp(max_dates_per_ticker.quantile(0.95))
    print(f"Reference date (95th percentile): {reference_date.strftime('%Y-%m-%d')}")

    # Remove stale tickers (not updated within stale_days of reference)
    stale_cutoff = reference_date - timedelta(days=stale_days)
    stale_tickers = max_dates_per_ticker[
        max_dates_per_ticker < stale_cutoff
    ].index.tolist()
    if stale_tickers:
        print(
            f"Removing {len(stale_tickers)} stale tickers "
            f"(no data since {stale_cutoff.strftime('%Y-%m-%d')})"
        )
        daily_data = daily_data[~daily_data["ticker"].isin(stale_tickers)]

    # Filter by minimum observations
    filtered_daily = filter_active_tickers(
        daily_data, min_obs=min_obs, date_col="Date", last_date=None
    )

    if filtered_daily.empty:
        print("No tickers met the filtering criteria. Adjust --min-obs or --stale-days.")
        return

    feature_frames = []
    total_tickers = filtered_daily["ticker"].nunique()
    print(f"\nProcessing {total_tickers} tickers...")

    for idx, (ticker, group) in enumerate(filtered_daily.groupby("ticker"), 1):
        if idx % 100 == 0 or idx == total_tickers:
            print(f"  Processed {idx}/{total_tickers} tickers...")
        group = group.sort_values("Date").reset_index(drop=True)
        group = add_technical_indicators(group)
        group = add_lag_features(
            group,
            columns=["Close", "Volume", "atr_5", "atr_14", "RSI_14"],
            lags=[1, 2, 3, 5],
        )
        group = add_rolling_features(
            group, columns=["Close", "Volume", "atr_14"], windows=[5, 10, 20]
        )
        feature_frames.append(group)

    if not feature_frames:
        print("No feature data created; nothing to save.")
        return

    features_df = pd.concat(feature_frames, ignore_index=True)

    print(f"\nCleaning data:")
    print(f"  Before cleaning: {len(features_df):,} rows")

    # Only drop rows where critical indicators are missing
    critical_cols = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "atr_5",
        "atr_14",
        "RSI_14",
        "SMA_20",
        "EMA_20",
        "MACD",
        "BB_mid",
        "ADX",
    ]
    critical_cols = [c for c in critical_cols if c in features_df.columns]

    initial_nans = features_df[critical_cols].isna().sum().sum()
    features_df = features_df.dropna(subset=critical_cols).reset_index(drop=True)

    print(f"  After cleaning: {len(features_df):,} rows")
    print(f"  Dropped {initial_nans:,} rows with NaNs in critical columns")

    if features_df.empty:
        raise RuntimeError("Dropping NaNs produced an empty feature dataset.")

    # Save with data_columns for efficient queries and better compression
    features_df.to_hdf(
        output_path,
        key="data",
        mode="w",
        format="table",
        data_columns=["ticker", "Date"],
        complevel=9,
        complib="blosc",
    )
    print(
        f"\nFeatures computed for {features_df['ticker'].nunique()} tickers. "
        f"Saved to {output_path}."
    )
    print(f"Date range: {features_df['Date'].min()} to {features_df['Date'].max()}")
    print(f"Total rows: {len(features_df):,}")

    # Data quality report
    print(f"\nData Quality Report:")
    nan_counts = features_df.isna().sum()
    cols_with_nans = nan_counts[nan_counts > 0]
    if len(cols_with_nans) > 0:
        print(f"  Columns with NaNs: {len(cols_with_nans)}")
        for col, count in cols_with_nans.head(10).items():
            pct = (count / len(features_df)) * 100
            print(f"    {col}: {count:,} ({pct:.2f}%)")
        if len(cols_with_nans) > 10:
            print(f"    ... and {len(cols_with_nans) - 10} more columns")
    else:
        print("  No NaN values detected")

    # Freshness report
    max_dates = features_df.groupby("ticker")["Date"].max()
    overall_max = features_df["Date"].max()
    days_behind = (overall_max - max_dates).dt.days
    behind_7 = (days_behind > 7).sum()

    print(f"\nFreshness Report:")
    print(f"  Latest date: {overall_max.strftime('%Y-%m-%d')}")
    print(
        f"  Tickers within 7 days: {len(days_behind) - behind_7}/{len(days_behind)}"
    )
    if behind_7 > 0:
        print(f"  Tickers >7 days behind: {behind_7} (these may need attention)")

    print(f"\nSample data:")
    print(features_df.head())


def main():
    """Run feature generation with CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Generate technical features from daily price data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate.py
  python generate.py --input prices_daily.csv --output daily_features.h5
  python generate.py --min-obs 252 --stale-days 5
        """,
    )
    parser.add_argument(
        "--input",
        default=DAILY_CSV,
        help=f"Path to daily prices CSV (default: {DAILY_CSV})",
    )
    parser.add_argument(
        "--output",
        default="daily_features.h5",
        help="Path for output HDF5 file (default: daily_features.h5)",
    )
    parser.add_argument(
        "--min-obs",
        type=int,
        default=100,
        help="Minimum observations required per ticker (default: 100)",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=STALE_TICKER_DAYS,
        help=f"Skip tickers with no data in this many days (default: {STALE_TICKER_DAYS})",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Feature Generator")
    print("=" * 60)
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")
    print(f"Min observations: {args.min_obs}")
    print(f"Stale ticker threshold: {args.stale_days} days")
    print("=" * 60)

    generate_features(
        daily_path=args.input,
        output_path=args.output,
        min_obs=args.min_obs,
        stale_days=args.stale_days,
    )

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
