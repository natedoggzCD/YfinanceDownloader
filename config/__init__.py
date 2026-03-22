"""
Shared config loader.

Canonical config is `config/config.yaml`, which is what the GUI writes.
Legacy `config/config.py` is still accepted as a fallback so older local
setups continue to run and can be migrated through the GUI.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


PACKAGE_DIR = Path(__file__).resolve().parent
CONFIG_YAML = PACKAGE_DIR / "config.yaml"
CONFIG_EXAMPLE_YAML = PACKAGE_DIR / "config.example.yaml"
LEGACY_CONFIG_PY = PACKAGE_DIR / "config.py"


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        import yaml
    except ImportError:
        return {}

    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_legacy_python() -> dict:
    if not LEGACY_CONFIG_PY.exists():
        return {}

    namespace: dict = {}
    with LEGACY_CONFIG_PY.open("r", encoding="utf-8") as handle:
        exec(handle.read(), namespace)
    return namespace


def _legacy_to_exported(namespace: dict) -> dict:
    return {
        "MIN_PRICE": namespace.get("MIN_PRICE", 2.0),
        "MAX_PRICE": namespace.get("MAX_PRICE", 200.0),
        "START_DATE": namespace.get("START_DATE", "2018-01-02"),
        "END_DATE": namespace.get("END_DATE"),
        "DAILY_CSV": namespace.get("DAILY_CSV", "data/prices_daily.csv"),
        "HOURLY_CSV": namespace.get("HOURLY_CSV", "data/prices_hourly.csv"),
        "NASDAQ_SCREENER": namespace.get("NASDAQ_SCREENER", "data/nasdaq_screener.csv"),
        "BATCH_SIZE": namespace.get("BATCH_SIZE", 50),
        "PAUSE_AFTER_BATCHES": namespace.get("PAUSE_AFTER_BATCHES", 500),
        "PAUSE_DURATION_SECONDS": namespace.get("PAUSE_DURATION_SECONDS", 60),
        "INVALID_TICKER_PATTERNS": namespace.get("INVALID_TICKER_PATTERNS", r"[\^\.\/\-=]"),
        "MIN_OBSERVATIONS": namespace.get("MIN_OBSERVATIONS", 100),
        "MAX_RETRIES": namespace.get("MAX_RETRIES", 3),
        "RETRY_BACKOFF_SECONDS": namespace.get("RETRY_BACKOFF_SECONDS", 5),
        "STALE_TICKER_DAYS": namespace.get("STALE_TICKER_DAYS", 5),
        "HOURLY_MAX_DAYS": namespace.get("HOURLY_MAX_DAYS", 729),
        "GAP_THRESHOLD_DAYS": namespace.get("GAP_THRESHOLD_DAYS", 7),
        "TIMEZONE": namespace.get("TIMEZONE", "UTC"),
    }


def _yaml_to_exported(raw: dict) -> dict:
    data = raw.get("data", {})
    return {
        "MIN_PRICE": data.get("min_price", 2.0),
        "MAX_PRICE": data.get("max_price", 200.0),
        "START_DATE": data.get("start_date", "2018-01-02"),
        "END_DATE": data.get("end_date"),
        "DAILY_CSV": data.get("daily_csv", "data/prices_daily.csv"),
        "HOURLY_CSV": data.get("hourly_csv", "data/prices_hourly.csv"),
        "NASDAQ_SCREENER": data.get("nasdaq_screener", "data/nasdaq_screener.csv"),
        "BATCH_SIZE": data.get("batch_size", 50),
        "PAUSE_AFTER_BATCHES": data.get("pause_after_batches", 500),
        "PAUSE_DURATION_SECONDS": data.get("pause_duration_seconds", 60),
        "INVALID_TICKER_PATTERNS": data.get("invalid_ticker_patterns", r"[\^\.\/\-=]"),
        "MIN_OBSERVATIONS": data.get("min_observations", 100),
        "MAX_RETRIES": data.get("max_retries", 3),
        "RETRY_BACKOFF_SECONDS": data.get("retry_backoff_seconds", 5),
        "STALE_TICKER_DAYS": data.get("stale_ticker_days", 5),
        "HOURLY_MAX_DAYS": data.get("hourly_max_days", 729),
        "GAP_THRESHOLD_DAYS": data.get("gap_threshold_days", 7),
        "TIMEZONE": data.get("timezone", "UTC"),
    }


_yaml_defaults = _load_yaml(CONFIG_EXAMPLE_YAML)
_yaml_active = _load_yaml(CONFIG_YAML)

if _yaml_active:
    RAW_CONFIG = _deep_merge(_yaml_defaults, _yaml_active)
    _exports = _yaml_to_exported(RAW_CONFIG)
    ACTIVE_CONFIG_PATH = str(CONFIG_YAML)
    CONFIG_SOURCE = "yaml"
else:
    RAW_CONFIG = _load_legacy_python()
    _exports = _legacy_to_exported(RAW_CONFIG)
    ACTIVE_CONFIG_PATH = str(LEGACY_CONFIG_PY if LEGACY_CONFIG_PY.exists() else CONFIG_EXAMPLE_YAML)
    CONFIG_SOURCE = "python" if LEGACY_CONFIG_PY.exists() else "defaults"


globals().update(_exports)
config = SimpleNamespace(**_exports)

__all__ = [
    *sorted(_exports.keys()),
    "ACTIVE_CONFIG_PATH",
    "CONFIG_SOURCE",
    "CONFIG_YAML",
    "LEGACY_CONFIG_PY",
    "RAW_CONFIG",
    "config",
]
