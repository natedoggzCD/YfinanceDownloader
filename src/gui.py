"""YfinanceDownloader GUI — single interface for the full workflow."""

import csv
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections import deque
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_YAML = PROJECT_ROOT / "config" / "config.yaml"
LEGACY_CONFIG_PY = PROJECT_ROOT / "config" / "config.py"
CONFIG_EXAMPLE_YAML = PROJECT_ROOT / "config" / "config.example.yaml"
SENTINEL = object()  # signals worker thread completion
MAX_OUTPUT_LINES = 5000


# ---------------------------------------------------------------------------
# Setup Wizard
# ---------------------------------------------------------------------------

class SetupWizard(tk.Toplevel):
    """Tabbed dialog that collects settings and writes config/config.yaml."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("YfinanceDownloader — Setup")
        self.geometry("560x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = False  # True if user clicked Save

        # Load the active config when present, otherwise use example defaults.
        self._defaults = self._load_active_config()

        # Bottom buttons — pack FIRST so they are never pushed off-screen
        btn_frame = ttk.Frame(self, padding=(6, 4))
        btn_frame.pack(side="bottom", fill="x")
        ttk.Button(btn_frame, text="Save & Continue", command=self._save).pack(side="right", padx=(4, 0))
        ttk.Button(btn_frame, text="Cancel", command=self._cancel).pack(side="right")

        # Build notebook (tabs)
        nb = ttk.Notebook(self, padding=6)
        nb.pack(fill="both", expand=True)

        self._vars = {}
        self._build_data_tab(nb)
        self._build_screener_tab(nb)
        self._build_trading_tab(nb)

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _load_active_config(self):
        """Load current config.yaml, then legacy config.py, then example defaults."""
        if CONFIG_YAML.exists():
            try:
                with open(CONFIG_YAML, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                if cfg:
                    return cfg
            except Exception:
                pass

        defaults = {}
        if CONFIG_EXAMPLE_YAML.exists():
            with open(CONFIG_EXAMPLE_YAML, encoding="utf-8") as f:
                defaults = yaml.safe_load(f) or {}

        if LEGACY_CONFIG_PY.exists():
            try:
                namespace = {}
                with open(LEGACY_CONFIG_PY, encoding="utf-8") as f:
                    exec(f.read(), namespace)

                defaults.setdefault("data", {})
                defaults["data"]["min_price"] = namespace.get(
                    "MIN_PRICE", defaults["data"].get("min_price", 2.0)
                )
                defaults["data"]["max_price"] = namespace.get(
                    "MAX_PRICE", defaults["data"].get("max_price", 200.0)
                )
                defaults["data"]["start_date"] = namespace.get(
                    "START_DATE", defaults["data"].get("start_date", "2018-01-02")
                )
                defaults["data"]["daily_csv"] = namespace.get(
                    "DAILY_CSV", defaults["data"].get("daily_csv", "data/prices_daily.csv")
                )
                defaults["data"]["hourly_csv"] = namespace.get(
                    "HOURLY_CSV", defaults["data"].get("hourly_csv", "data/prices_hourly.csv")
                )
                defaults["data"]["nasdaq_screener"] = namespace.get(
                    "NASDAQ_SCREENER",
                    defaults["data"].get("nasdaq_screener", "data/nasdaq_screener.csv"),
                )
                defaults["data"]["batch_size"] = namespace.get(
                    "BATCH_SIZE", defaults["data"].get("batch_size", 50)
                )
                defaults["data"]["stale_ticker_days"] = namespace.get(
                    "STALE_TICKER_DAYS", defaults["data"].get("stale_ticker_days", 5)
                )
                defaults["data"]["hourly_max_days"] = namespace.get(
                    "HOURLY_MAX_DAYS", defaults["data"].get("hourly_max_days", 729)
                )
                return defaults
            except Exception:
                pass

        if defaults:
            return defaults
        return {"data": {}, "screener": {}, "trading": {}}

    # --- helpers to add labelled fields ---

    def _add_entry(self, parent, label, key, default, row, width=20, show=""):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2, padx=(0, 8))
        var = tk.StringVar(value=str(default))
        e = ttk.Entry(parent, textvariable=var, width=width)
        if show:
            e.config(show=show)
        e.grid(row=row, column=1, sticky="w", pady=2)
        self._vars[key] = var
        return var

    def _add_check(self, parent, label, key, default, row):
        var = tk.BooleanVar(value=default)
        ttk.Checkbutton(parent, text=label, variable=var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=2)
        self._vars[key] = var
        return var

    def _add_combo(self, parent, label, key, default, values, row, width=18):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2, padx=(0, 8))
        var = tk.StringVar(value=str(default))
        ttk.Combobox(parent, textvariable=var, values=values, width=width,
                     state="readonly").grid(row=row, column=1, sticky="w", pady=2)
        self._vars[key] = var
        return var

    # --- Tab builders ---

    def _build_data_tab(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="  Data  ")
        d = self._defaults.get("data", {})

        ttk.Label(f, text="Stock Price Range", font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self._add_entry(f, "Min Price ($):", "data.min_price", d.get("min_price", 2.0), 1)
        self._add_entry(f, "Max Price ($):", "data.max_price", d.get("max_price", 200.0), 2)

        ttk.Separator(f, orient="horizontal").grid(row=3, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(f, text="Historical Data", font=("", 10, "bold")).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self._add_entry(f, "Start Date:", "data.start_date", d.get("start_date", "2018-01-02"), 5)

        ttk.Separator(f, orient="horizontal").grid(row=6, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(f, text="Download Rate Limiting", font=("", 10, "bold")).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self._add_entry(f, "Batch Size:", "data.batch_size", d.get("batch_size", 50), 8, width=10)
        self._add_entry(f, "Stale Ticker Days:", "data.stale_ticker_days",
                        d.get("stale_ticker_days", 5), 9, width=10)

    def _build_screener_tab(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="  Screener  ")
        s = self._defaults.get("screener", {})

        ttk.Label(f, text="Universe Filters", font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self._add_entry(f, "Min Price ($):", "screener.min_price", s.get("min_price", 1.0), 1)
        self._add_entry(f, "Max Price ($):", "screener.max_price", s.get("max_price", 350.0), 2)
        self._add_entry(f, "Min Avg Volume:", "screener.min_avg_volume",
                        s.get("min_avg_volume", 500000), 3)
        self._add_entry(f, "Top N Results:", "screener.top_n", s.get("top_n", 50), 4, width=10)

        ttk.Separator(f, orient="horizontal").grid(row=5, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(f, text="Scoring Weights (must sum to 1.0)", font=("", 10, "bold")).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 4))
        w = s.get("weights", {})
        self._add_entry(f, "Momentum:", "screener.weights.momentum", w.get("momentum", 0.30), 7, width=8)
        self._add_entry(f, "Trend:", "screener.weights.trend", w.get("trend", 0.15), 8, width=8)
        self._add_entry(f, "Volume:", "screener.weights.volume", w.get("volume", 0.25), 9, width=8)
        self._add_entry(f, "Pullback:", "screener.weights.pullback", w.get("pullback", 0.10), 10, width=8)
        self._add_entry(f, "Volatility:", "screener.weights.volatility", w.get("volatility", 0.20), 11, width=8)

        ttk.Separator(f, orient="horizontal").grid(row=12, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(f, text="Quality Gates", font=("", 10, "bold")).grid(
            row=13, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self._add_entry(f, "Min Score:", "screener.min_score", s.get("min_score", 65), 14, width=8)
        self._add_entry(f, "Min R:R Ratio:", "screener.min_rr_ratio",
                        s.get("min_rr_ratio", 1.5), 15, width=8)

        ttk.Separator(f, orient="horizontal").grid(row=16, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(f, text="AI Summaries (optional)", font=("", 10, "bold")).grid(
            row=17, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ai = s.get("ai", {})
        self._add_entry(f, "OpenAI API Key:", "screener.ai.api_key",
                        ai.get("api_key", ""), 18, width=36, show="*")
        self._add_combo(f, "Model:", "screener.ai.model",
                        ai.get("model", "gpt-4o-mini"),
                        ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1-nano"], 19)

    def _build_trading_tab(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="  Trading  ")
        t = self._defaults.get("trading", {})

        ttk.Label(f, text="Alpaca API Credentials", font=("", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(f, text="Get free keys at app.alpaca.markets/signup",
                  foreground="gray").grid(row=1, column=0, columnspan=2, sticky="w")
        self._add_entry(f, "API Key:", "trading.alpaca_api_key",
                        t.get("alpaca_api_key", ""), 2, width=36, show="*")
        self._add_entry(f, "Secret Key:", "trading.alpaca_secret_key",
                        t.get("alpaca_secret_key", ""), 3, width=36, show="*")
        self._add_check(f, "Paper Trading (simulated — no real money)",
                        "trading.paper_trading", t.get("paper_trading", True), 4)

        ttk.Separator(f, orient="horizontal").grid(row=5, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(f, text="Position Sizing", font=("", 10, "bold")).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self._add_entry(f, "Risk Per Trade (%):", "trading.risk_per_trade_pct",
                        t.get("risk_per_trade_pct", 1.0), 7, width=8)
        self._add_entry(f, "Max Position (%):", "trading.max_position_pct",
                        t.get("max_position_pct", 8.0), 8, width=8)
        self._add_entry(f, "Max Positions:", "trading.max_positions",
                        t.get("max_positions", 10), 9, width=8)

        ttk.Separator(f, orient="horizontal").grid(row=10, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(f, text="Risk Controls", font=("", 10, "bold")).grid(
            row=11, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self._add_entry(f, "Max Portfolio Heat (%):", "trading.portfolio_heat_max_pct",
                        t.get("portfolio_heat_max_pct", 6.0), 12, width=8)
        self._add_entry(f, "Min Cash Reserve (%):", "trading.min_cash_reserve_pct",
                        t.get("min_cash_reserve_pct", 20.0), 13, width=8)
        self._add_entry(f, "Min Score to Trade:", "trading.min_score_to_trade",
                        t.get("min_score_to_trade", 65), 14, width=8)

    # --- Save / Cancel ---

    def _build_config_dict(self):
        """Assemble the nested YAML dict from the flat vars, merging with example defaults."""
        # Start with the full example as base (preserves ATR multiples, signal thresholds, etc.)
        cfg = {}
        for section in ("data", "screener", "trading"):
            if section in self._defaults:
                cfg[section] = dict(self._defaults[section])
            else:
                cfg[section] = {}

        # Deep-copy nested dicts from defaults
        for key in ("weights", "scan_types", "atr_multiples", "momentum",
                     "mean_reversion", "breakout", "pullback_entry", "ai"):
            if key in self._defaults.get("screener", {}):
                cfg["screener"][key] = dict(self._defaults["screener"][key])
                # atr_multiples has sub-dicts
                if key == "atr_multiples":
                    for sub in cfg["screener"][key]:
                        if isinstance(cfg["screener"][key][sub], dict):
                            cfg["screener"][key][sub] = dict(cfg["screener"][key][sub])

        def _typed(val_str):
            """Convert string to int/float/bool where appropriate."""
            if val_str.lower() in ("true", "false"):
                return val_str.lower() == "true"
            try:
                return int(val_str)
            except ValueError:
                pass
            try:
                return float(val_str)
            except ValueError:
                pass
            return val_str

        # Overlay user entries
        for dotkey, var in self._vars.items():
            val = var.get() if isinstance(var, tk.StringVar) else var.get()
            if isinstance(val, str):
                val = _typed(val)
            parts = dotkey.split(".")
            d = cfg
            for p in parts[:-1]:
                d = d.setdefault(p, {})
            d[parts[-1]] = val

        return cfg

    def _save(self):
        cfg = self._build_config_dict()

        # Validate weights sum
        w = cfg.get("screener", {}).get("weights", {})
        total = sum(v for v in w.values() if isinstance(v, (int, float)))
        if abs(total - 1.0) > 0.01:
            messagebox.showwarning("Validation Error",
                                   f"Scoring weights must sum to 1.0 (currently {total:.2f})",
                                   parent=self)
            return

        # Write YAML
        CONFIG_YAML.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_YAML, "w", encoding="utf-8") as f:
            f.write("# YfinanceDownloader — Configuration\n")
            f.write("# Generated by Setup Wizard\n\n")
            yaml.dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()


# ---------------------------------------------------------------------------
# Data freshness helpers
# ---------------------------------------------------------------------------

def _get_daily_price_date():
    """Max date from prices_daily.csv by reading the tail."""
    path = PROJECT_ROOT / "data" / "prices_daily.csv"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            header = f.readline().strip().split(",")
            date_idx = header.index("Date")
            tail = deque(f, maxlen=200)
        max_date = ""
        for line in tail:
            cols = line.strip().split(",")
            if len(cols) > date_idx:
                d = cols[date_idx][:10]
                if d > max_date:
                    max_date = d
        return max_date if max_date else None
    except Exception:
        return None


def _get_features_date():
    """Max date from daily_features.parquet (selective column read)."""
    path = PROJECT_ROOT / "data" / "daily_features.parquet"
    if not path.exists():
        return None
    try:
        import pandas as pd
        df = pd.read_parquet(path, columns=["Date"])
        max_dt = df["Date"].max()
        return max_dt.strftime("%Y-%m-%d") if pd.notna(max_dt) else None
    except Exception:
        return None


def _get_screener_mtime():
    """File modification time of screener_results.csv."""
    path = PROJECT_ROOT / "data" / "screener_results.csv"
    if not path.exists():
        return None
    try:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return None


def _get_trade_date():
    """Most recent timestamp from trade_log.csv."""
    path = PROJECT_ROOT / "logs" / "trade_log.csv"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            tail = deque(reader, maxlen=20)
        max_ts = ""
        for row in tail:
            ts = row.get("timestamp", "")
            if ts > max_ts:
                max_ts = ts
        return max_ts[:16].replace("T", " ") if max_ts else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YfinanceDownloader")
        self.geometry("780x700")
        self.minsize(680, 600)

        self._process = None
        self._thread = None
        self._cancel_requested = False
        self._queue = queue.Queue()

        # Variables for step options
        self.var_update_screener = tk.BooleanVar(value=True)
        self.var_ai = tk.BooleanVar(value=False)
        self.var_verbose = tk.BooleanVar(value=False)
        self.var_validate = tk.BooleanVar(value=False)
        self.var_scan = tk.StringVar(value="all")
        self.var_trade_mode = tk.StringVar(value="dry-run")

        # Freshness labels (will be set during build)
        self._freshness_labels = {}

        self._build_menu()
        self._build_ui()
        self._refresh_freshness()
        self._poll_queue()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Show setup wizard only when no active config exists yet.
        if not CONFIG_YAML.exists() and not LEGACY_CONFIG_PY.exists():
            self.after(100, self._show_setup)

    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        menubar.add_command(label="Settings", command=self._show_setup)

    def _show_setup(self):
        """Open the setup wizard dialog."""
        wiz = SetupWizard(self)
        self.wait_window(wiz)
        if wiz.result:
            self._append_output("Settings saved. Config reloaded.\n")
        elif not CONFIG_YAML.exists() and not LEGACY_CONFIG_PY.exists():
            messagebox.showinfo("Setup Required",
                                "Config file not found. Using example defaults.\n"
                                "Click 'Settings' in the menu bar to configure.",
                                parent=self)

    # --- UI Construction ---

    def _build_ui(self):
        container = ttk.Frame(self, padding=8)
        container.pack(fill="both", expand=True)

        # Step 1: Download
        f1 = ttk.LabelFrame(container, text="Step 1: Download Data", padding=6)
        f1.pack(fill="x", pady=(0, 4))
        row1 = ttk.Frame(f1)
        row1.pack(fill="x")
        ttk.Checkbutton(row1, text="Update NASDAQ Screener CSV first",
                        variable=self.var_update_screener).pack(side="left")
        self._btn1 = ttk.Button(row1, text="Run", command=lambda: self._run_step(1))
        self._btn1.pack(side="right")
        lbl1 = ttk.Label(f1, text="Last data: ...", foreground="gray")
        lbl1.pack(anchor="w")
        self._freshness_labels[1] = lbl1

        # Step 2: Generate
        f2 = ttk.LabelFrame(container, text="Step 2: Generate Features", padding=6)
        f2.pack(fill="x", pady=(0, 4))
        row2 = ttk.Frame(f2)
        row2.pack(fill="x")
        ttk.Label(row2, text="Computes technical indicators from daily prices").pack(side="left")
        self._btn2 = ttk.Button(row2, text="Run", command=lambda: self._run_step(2))
        self._btn2.pack(side="right")
        lbl2 = ttk.Label(f2, text="Last data: ...", foreground="gray")
        lbl2.pack(anchor="w")
        self._freshness_labels[2] = lbl2

        # Step 3: Screen
        f3 = ttk.LabelFrame(container, text="Step 3: Screen Stocks", padding=6)
        f3.pack(fill="x", pady=(0, 4))
        row3a = ttk.Frame(f3)
        row3a.pack(fill="x")
        ttk.Checkbutton(row3a, text="AI summaries", variable=self.var_ai).pack(side="left")
        ttk.Checkbutton(row3a, text="Verbose", variable=self.var_verbose).pack(side="left", padx=(12, 0))
        ttk.Checkbutton(row3a, text="Validate", variable=self.var_validate).pack(side="left", padx=(12, 0))
        self._btn3 = ttk.Button(row3a, text="Run", command=lambda: self._run_step(3))
        self._btn3.pack(side="right")
        row3b = ttk.Frame(f3)
        row3b.pack(fill="x", pady=(2, 0))
        ttk.Label(row3b, text="Scan:").pack(side="left")
        ttk.Combobox(row3b, textvariable=self.var_scan, width=14, state="readonly",
                     values=["all", "momentum", "reversion", "breakout", "pullback"]).pack(side="left", padx=4)
        lbl3 = ttk.Label(f3, text="Last run: ...", foreground="gray")
        lbl3.pack(anchor="w", pady=(2, 0))
        self._freshness_labels[3] = lbl3

        # Step 4: Trade
        f4 = ttk.LabelFrame(container, text="Step 4: Trade", padding=6)
        f4.pack(fill="x", pady=(0, 4))
        row4 = ttk.Frame(f4)
        row4.pack(fill="x")
        ttk.Radiobutton(row4, text="Dry Run", variable=self.var_trade_mode, value="dry-run").pack(side="left")
        ttk.Radiobutton(row4, text="Execute", variable=self.var_trade_mode, value="execute").pack(side="left", padx=(12, 0))
        ttk.Radiobutton(row4, text="Status", variable=self.var_trade_mode, value="status").pack(side="left", padx=(12, 0))
        self._btn4 = ttk.Button(row4, text="Run", command=lambda: self._run_step(4))
        self._btn4.pack(side="right")
        lbl4 = ttk.Label(f4, text="Last trade: ...", foreground="gray")
        lbl4.pack(anchor="w")
        self._freshness_labels[4] = lbl4

        # Pipeline + Cancel
        ctrl = ttk.Frame(container)
        ctrl.pack(fill="x", pady=(4, 4))
        self._btn_pipeline = ttk.Button(ctrl, text="Run Full Pipeline",
                                        command=self._run_pipeline)
        self._btn_pipeline.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self._btn_cancel = ttk.Button(ctrl, text="Cancel", command=self._cancel,
                                      state="disabled")
        self._btn_cancel.pack(side="left")

        # Output area
        out_frame = ttk.LabelFrame(container, text="Output", padding=4)
        out_frame.pack(fill="both", expand=True, pady=(0, 4))
        self._output = tk.Text(out_frame, wrap="word", font=("Consolas", 9),
                               state="disabled", bg="#1e1e1e", fg="#d4d4d4",
                               insertbackground="#d4d4d4")
        scrollbar = ttk.Scrollbar(out_frame, orient="vertical", command=self._output.yview)
        self._output.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._output.pack(fill="both", expand=True)

        # Status bar
        status_bar = ttk.Frame(container)
        status_bar.pack(fill="x")
        self._status_var = tk.StringVar(value="Ready")
        ttk.Label(status_bar, textvariable=self._status_var).pack(side="left")
        ttk.Button(status_bar, text="Clear Log", command=self._clear_output).pack(side="right")

        self._all_buttons = [self._btn1, self._btn2, self._btn3, self._btn4, self._btn_pipeline]

    # --- Freshness ---

    def _refresh_freshness(self):
        """Update all freshness labels from data files."""
        d1 = _get_daily_price_date()
        self._freshness_labels[1].config(
            text=f"Last data: {d1}" if d1 else "Last data: No data",
            foreground="" if d1 else "gray")

        d2 = _get_features_date()
        self._freshness_labels[2].config(
            text=f"Last data: {d2}" if d2 else "Last data: No data",
            foreground="" if d2 else "gray")

        d3 = _get_screener_mtime()
        self._freshness_labels[3].config(
            text=f"Last run: {d3}" if d3 else "Last run: No data",
            foreground="" if d3 else "gray")

        d4 = _get_trade_date()
        self._freshness_labels[4].config(
            text=f"Last trade: {d4}" if d4 else "Last trade: No data",
            foreground="" if d4 else "gray")

    # --- Command Building ---

    def _build_command(self, step):
        if step == 1:
            cmd = [sys.executable, "src/downloader.py", "--all"]
            if self.var_update_screener.get():
                cmd.append("--update-screener")
            return cmd
        elif step == 2:
            return [sys.executable, "src/generate.py"]
        elif step == 3:
            cmd = [sys.executable, "src/screener.py"]
            if self.var_ai.get():
                cmd.append("--ai")
            if self.var_verbose.get():
                cmd.append("--verbose")
            if self.var_validate.get():
                cmd.append("--validate")
            scan = self.var_scan.get()
            if scan != "all":
                cmd.extend(["--scan", scan])
            return cmd
        elif step == 4:
            cmd = [sys.executable, "src/trader.py"]
            mode = self.var_trade_mode.get()
            if mode == "dry-run":
                cmd.append("--dry-run")
            elif mode == "status":
                cmd.append("--status")
            return cmd

    # --- Execution ---

    def _run_step(self, step):
        if self._thread and self._thread.is_alive():
            return
        cmd = self._build_command(step)
        label = f"Step {step}"
        self._set_buttons_enabled(False)
        self._cancel_requested = False
        self._status_var.set(f"{label} running...")
        self._append_output(f"\n{'='*50}\n{label}: {' '.join(cmd)}\n{'='*50}\n")
        self._thread = threading.Thread(target=self._worker, args=(cmd, label), daemon=True)
        self._thread.start()

    def _run_pipeline(self):
        if self._thread and self._thread.is_alive():
            return
        self._set_buttons_enabled(False)
        self._cancel_requested = False
        self._status_var.set("Pipeline: starting...")
        self._thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        self._thread.start()

    def _pipeline_worker(self):
        for step in range(1, 5):
            if self._cancel_requested:
                self._queue.put("[Pipeline cancelled]\n")
                break
            cmd = self._build_command(step)
            label = f"Step {step}/4"
            self._queue.put(f"\n{'='*50}\n{label}: {' '.join(cmd)}\n{'='*50}\n")
            rc = self._run_subprocess(cmd, label)
            if rc != 0:
                self._queue.put(f"\n{label} FAILED (exit code {rc}). Pipeline stopped.\n")
                break
        self._queue.put(SENTINEL)

    def _worker(self, cmd, label):
        rc = self._run_subprocess(cmd, label)
        if rc != 0:
            self._queue.put(f"\n{label} finished with exit code {rc}\n")
        else:
            self._queue.put(f"\n{label} completed successfully.\n")
        self._queue.put(SENTINEL)

    def _run_subprocess(self, cmd, label):
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(PROJECT_ROOT),
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            for line in self._process.stdout:
                if self._cancel_requested:
                    self._process.terminate()
                    break
                self._queue.put(line)
            self._process.wait()
            return self._process.returncode or 0
        except FileNotFoundError:
            self._queue.put(f"ERROR: Could not find {cmd[0]}\n")
            return 1
        except Exception as e:
            self._queue.put(f"ERROR: {e}\n")
            return 1
        finally:
            self._process = None

    def _cancel(self):
        self._cancel_requested = True
        if self._process:
            self._process.terminate()

    # --- Output ---

    def _poll_queue(self):
        try:
            while True:
                item = self._queue.get_nowait()
                if item is SENTINEL:
                    self._set_buttons_enabled(True)
                    self._btn_cancel.config(state="disabled")
                    if "FAILED" not in self._status_var.get():
                        self._status_var.set("Done")
                    self._refresh_freshness()
                else:
                    self._append_output(item)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _append_output(self, text):
        ts = datetime.now().strftime("[%H:%M:%S] ")
        self._output.config(state="normal")
        for line in text.splitlines(keepends=True):
            self._output.insert("end", ts + line if line.strip() else "\n")
        # Trim if too long
        line_count = int(self._output.index("end-1c").split(".")[0])
        if line_count > MAX_OUTPUT_LINES:
            self._output.delete("1.0", f"{line_count - MAX_OUTPUT_LINES}.0")
        self._output.see("end")
        self._output.config(state="disabled")

    def _clear_output(self):
        self._output.config(state="normal")
        self._output.delete("1.0", "end")
        self._output.config(state="disabled")

    # --- State ---

    def _set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for btn in self._all_buttons:
            btn.config(state=state)
        self._btn_cancel.config(state="disabled" if enabled else "normal")

    def _on_close(self):
        self._cancel_requested = True
        if self._process:
            self._process.terminate()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
