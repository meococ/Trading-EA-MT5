#!/usr/bin/env python3
"""
runs_db.py — SQLite experiment tracking database for EA backtesting workspace.

Scans all run folders under 02. AlphaFactory/runs/, parses backtest artifacts,
stores metrics in SQLite, provides CLI for querying and gate checks.

Usage:
    python runs_db.py build                     # Rebuild DB from scratch
    python runs_db.py query "PF > 1.5 AND DD < 8"  # Query with human-readable conditions
    python runs_db.py top [N]                   # Top N runs by net profit (default 10)
    python runs_db.py compare run1 run2         # Side-by-side comparison
    python runs_db.py gates                     # Show runs vs PROP_READY gates
    python runs_db.py summary                   # Quick stats per EA
    python runs_db.py info <run_id>             # Detailed info for a single run

Author: Max (AlphaFactory)
"""

import sqlite3
import json
import os
import re
import sys
import io
import glob
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# Force UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ALPHA_DIR = SCRIPT_DIR.parent                     # 02. AlphaFactory/
RUNS_DIR = ALPHA_DIR / "runs"
DB_PATH = ALPHA_DIR / "runs.db"

# PROP_READY gate thresholds
GATES = {
    "cagr":               {"op": ">=", "val": 20.0,  "unit": "%",   "nullable": False},
    "max_dd_pct":         {"op": "<=", "val": 8.0,   "unit": "%",   "nullable": False},
    "trades_per_year":    {"op": ">=", "val": 100.0,  "unit": "",   "nullable": False},
    "win_loss_ratio":     {"op": ">=", "val": 1.4,   "unit": "",    "nullable": False},  # avg_win / abs(avg_loss)
    "max_loss_streak":    {"op": "<=", "val": 15,    "unit": "",    "nullable": False},
    "wfa_efficiency":     {"op": ">=", "val": 0.60,  "unit": "",    "nullable": True},
    "mc_p95_dd":          {"op": "<=", "val": 8.0,   "unit": "%",   "nullable": True},
    "robustness_pass_rate": {"op": ">=", "val": 0.60, "unit": "",   "nullable": True},
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id               TEXT UNIQUE,
    ea_name              TEXT,
    run_path             TEXT,
    timestamp            DATETIME,
    -- From HTML report
    symbol               TEXT,
    period               TEXT,
    date_from            TEXT,
    date_to              TEXT,
    deposit              REAL,
    -- From enhanced_summary.json
    n_trades             INTEGER,
    net_profit           REAL,
    profit_factor        REAL,
    win_rate             REAL,
    avg_win              REAL,
    avg_loss             REAL,
    max_dd_pct           REAL,
    max_dd_abs           REAL,
    expectancy           REAL,
    start_equity         REAL,
    final_equity         REAL,
    max_win_streak       INTEGER,
    max_loss_streak      INTEGER,
    -- Calculated
    trades_per_year      REAL,
    cagr                 REAL,
    years                REAL,
    win_loss_ratio       REAL,
    -- From tca_summary.json
    sqn                  REAL,
    -- Robustness (nullable)
    wfa_efficiency       REAL,
    wfa_oos_ratio        REAL,
    mc_p95_dd            REAL,
    robustness_pass_rate REAL,
    param_stability      REAL,
    -- Meta
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_runs_ea_name ON runs(ea_name);
CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(timestamp);
CREATE INDEX IF NOT EXISTS idx_runs_pf ON runs(profit_factor);
CREATE INDEX IF NOT EXISTS idx_runs_net_profit ON runs(net_profit);
"""

# Column aliases for human-readable query
COLUMN_ALIASES = {
    "pf":          "profit_factor",
    "dd":          "max_dd_pct",
    "dd_pct":      "max_dd_pct",
    "dd_abs":      "max_dd_abs",
    "trades":      "n_trades",
    "wr":          "win_rate",
    "winrate":     "win_rate",
    "exp":         "expectancy",
    "tpy":         "trades_per_year",
    "wfa":         "wfa_efficiency",
    "mc":          "mc_p95_dd",
    "robust":      "robustness_pass_rate",
    "param":       "param_stability",
    "ea":          "ea_name",
    "profit":      "net_profit",
    "streak":      "max_loss_streak",
    "wl":          "win_loss_ratio",
    "wlr":         "win_loss_ratio",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-7s │ %(message)s",
)
log = logging.getLogger("runs_db")

# ---------------------------------------------------------------------------
# File parsing helpers
# ---------------------------------------------------------------------------

def read_file_smart(path: Path, encoding_hint: str = "utf-8") -> Optional[str]:
    """Read a file, auto-detecting UTF-16 vs UTF-8."""
    if not path.exists():
        return None
    try:
        raw = path.read_bytes()
        # Detect BOM for UTF-16
        if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
            return raw.decode("utf-16")
        # Try UTF-8 first
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("utf-16", errors="replace")
    except Exception as e:
        log.warning(f"Cannot read {path}: {e}")
        return None


def load_json(path: Path) -> Optional[Dict]:
    """Load JSON file with graceful error handling."""
    content = read_file_smart(path)
    if content is None:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        log.warning(f"Bad JSON in {path}: {e}")
        return None


def safe_float(val, default=None):
    """Convert to float safely."""
    if val is None:
        return default
    try:
        f = float(val)
        return f if math.isfinite(f) else default
    except (ValueError, TypeError):
        return default


def safe_int(val, default=None):
    """Convert to int safely."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# HTML report parser
# ---------------------------------------------------------------------------

def parse_html_report(html_path: Path) -> Dict[str, Any]:
    """
    Extract EA name, symbol, period, date range from MT5 HTML report.
    Reports are UTF-16 encoded with Vietnamese labels.
    """
    result = {
        "ea_name_html": None,
        "symbol": None,
        "period": None,
        "date_from": None,
        "date_to": None,
    }

    content = read_file_smart(html_path)
    if content is None:
        return result

    # Expert name: <td ...>Expert:</td> ... <b>EA_NAME</b>
    m = re.search(r'Expert:\s*</td>\s*<td[^>]*>\s*<b>([^<]+)</b>', content, re.IGNORECASE)
    if m:
        result["ea_name_html"] = m.group(1).strip()

    # Symbol: <td ...>Symbol:</td> ... <b>SYMBOL</b>
    m = re.search(r'Symbol:\s*</td>\s*<td[^>]*>\s*<b>([^<]+)</b>', content, re.IGNORECASE)
    if m:
        result["symbol"] = m.group(1).strip().rstrip("+")  # Remove trailing + from E8 broker

    # Period + date range: <b>M15 (2019.01.01 - 2025.12.31)</b>
    # Label can be "Period:" or "Chu kỳ:" (Vietnamese)
    m = re.search(r'(?:Period|Chu kỳ):\s*</td>\s*<td[^>]*>\s*<b>([^<]+)</b>', content, re.IGNORECASE)
    if m:
        period_str = m.group(1).strip()
        # Parse "M15 (2019.01.01 - 2025.12.31)"
        pm = re.match(r'(\w+)\s*\((\d{4}\.\d{2}\.\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2})\)', period_str)
        if pm:
            result["period"] = pm.group(1)
            result["date_from"] = pm.group(2)
            result["date_to"] = pm.group(3)
        else:
            result["period"] = period_str

    return result


def parse_config_ini(config_path: Path) -> Dict[str, Any]:
    """
    Parse config.ini (UTF-16) for symbol, period, dates, deposit.
    Fallback if HTML parsing fails.
    """
    result = {}
    content = read_file_smart(config_path)
    if content is None:
        return result

    for line in content.splitlines():
        line = line.strip()
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if key == "Symbol":
                result["symbol"] = val.rstrip("+")
            elif key == "Period":
                result["period"] = val
            elif key == "FromDate":
                result["date_from"] = val
            elif key == "ToDate":
                result["date_to"] = val
            elif key == "Deposit":
                result["deposit"] = safe_float(val)
            elif key == "Expert":
                # Extract EA name from path like Advisors\...\EA_Phoenix_v6_core.ex5
                ea_basename = val.rsplit("\\", 1)[-1]
                ea_basename = ea_basename.replace(".ex5", "").replace(".mq5", "")
                result["ea_name_ini"] = ea_basename

    return result


# ---------------------------------------------------------------------------
# Run scanner
# ---------------------------------------------------------------------------

def discover_runs(runs_dir: Path) -> List[Tuple[str, str, Path]]:
    """
    Discover all valid run folders.
    Returns list of (ea_name, run_id, run_path).

    Structure:
      runs/<EA_NAME>/<YYYYMMDD_HHMMSS>/   -> ea_name from folder
      runs/<YYYYMMDD_HHMMSS>/              -> ea_name from report/config
    """
    results = []
    run_id_pattern = re.compile(r'^\d{8}_\d{6}$')

    if not runs_dir.exists():
        log.error(f"Runs directory not found: {runs_dir}")
        return results

    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue

        if run_id_pattern.match(entry.name):
            # Standalone run at runs/<YYYYMMDD_HHMMSS>/
            results.append(("_unknown_", entry.name, entry))
        else:
            # EA subfolder: runs/<EA_NAME>/<YYYYMMDD_HHMMSS>/
            ea_name = entry.name
            for sub in sorted(entry.iterdir()):
                if sub.is_dir() and run_id_pattern.match(sub.name):
                    results.append((ea_name, sub.name, sub))

    return results


def parse_run(ea_name: str, run_id: str, run_path: Path) -> Optional[Dict[str, Any]]:
    """Parse all artifacts from a single run folder into a flat dict."""

    # ── enhanced_summary.json (primary) ──────────────────────────────
    summary_path = run_path / "analysis" / "enhanced_summary.json"
    summary = load_json(summary_path)
    if summary is None:
        log.debug(f"SKIP {ea_name}/{run_id}: no enhanced_summary.json")
        return None

    # ── HTML report ──────────────────────────────────────────────────
    html_path = run_path / "report.html"
    html_data = parse_html_report(html_path)

    # ── config.ini (fallback) ────────────────────────────────────────
    config_path = run_path / "config.ini"
    config_data = parse_config_ini(config_path)

    # ── Resolve EA name ──────────────────────────────────────────────
    resolved_ea = ea_name
    if resolved_ea == "_unknown_":
        resolved_ea = (
            html_data.get("ea_name_html")
            or config_data.get("ea_name_ini")
            or "_unknown_"
        )

    # ── Resolve symbol, period, dates ────────────────────────────────
    symbol = html_data.get("symbol") or config_data.get("symbol")
    period = html_data.get("period") or config_data.get("period")
    date_from = html_data.get("date_from") or config_data.get("date_from")
    date_to = html_data.get("date_to") or config_data.get("date_to")
    deposit = config_data.get("deposit") or safe_float(summary.get("start_equity"))

    # ── Parse timestamp from run_id ──────────────────────────────────
    try:
        ts = datetime.strptime(run_id, "%Y%m%d_%H%M%S")
    except ValueError:
        ts = None

    # ── Core metrics from summary ────────────────────────────────────
    n_trades = safe_int(summary.get("n_trades"), 0)
    net_profit = safe_float(summary.get("net_profit"), 0.0)
    profit_factor = safe_float(summary.get("profit_factor"))
    win_rate = safe_float(summary.get("win_rate_pct"))
    avg_win = safe_float(summary.get("avg_win"))
    avg_loss = safe_float(summary.get("avg_loss"))
    max_dd_pct = safe_float(summary.get("max_drawdown_pct"))
    max_dd_abs = safe_float(summary.get("max_drawdown_abs"))
    expectancy = safe_float(summary.get("expectancy_per_trade"))
    start_equity = safe_float(summary.get("start_equity"), 10000.0)
    final_equity = safe_float(summary.get("final_equity"))

    # Streaks
    streaks = summary.get("streaks", {})
    max_win_streak = safe_int(streaks.get("max_win_streak"))
    max_loss_streak = safe_int(streaks.get("max_loss_streak"))

    # ── Calculate years, trades_per_year, CAGR ───────────────────────
    years = None
    if date_from and date_to:
        try:
            d1 = datetime.strptime(date_from.replace(".", "-"), "%Y-%m-%d")
            d2 = datetime.strptime(date_to.replace(".", "-"), "%Y-%m-%d")
            years = max((d2 - d1).days / 365.25, 0.1)
        except ValueError:
            pass

    trades_per_year = None
    if years and n_trades:
        trades_per_year = n_trades / years

    cagr = None
    if years and start_equity and final_equity and start_equity > 0 and final_equity > 0:
        try:
            cagr = ((final_equity / start_equity) ** (1.0 / years) - 1.0) * 100.0
        except (ValueError, ZeroDivisionError, OverflowError):
            pass

    # win/loss ratio
    win_loss_ratio = None
    if avg_win is not None and avg_loss is not None and avg_loss != 0:
        win_loss_ratio = abs(avg_win / avg_loss)

    # ── TCA summary (SQN) ───────────────────────────────────────────
    sqn = None
    tca_path = run_path / "analysis" / "tca_summary.json"
    tca = load_json(tca_path)
    if tca:
        sqn_val = safe_float(tca.get("run_meta", {}).get("sqn"))
        if sqn_val and sqn_val != 0.0:
            sqn = sqn_val

    # ── WFA results ──────────────────────────────────────────────────
    wfa_efficiency = None
    wfa_oos_ratio = None
    wfa_path = run_path / "walk_forward" / "wfa_results.json"
    wfa = load_json(wfa_path)
    if wfa:
        wfa_summary = wfa.get("summary", {})
        wfa_efficiency = safe_float(wfa_summary.get("efficiency_ratio"))
        wfa_oos_ratio = safe_float(wfa_summary.get("oos_profitable_ratio"))

    # ── Monte Carlo results ──────────────────────────────────────────
    mc_p95_dd = None
    mc_path = run_path / "monte_carlo" / "monte_carlo_results.json"
    mc = load_json(mc_path)
    if mc:
        mc_dd = mc.get("max_drawdown_pct", {})
        mc_p95_dd = safe_float(mc_dd.get("p95"))

    # ── Robustness results ───────────────────────────────────────────
    robustness_pass_rate = None
    rob_path = run_path / "robustness" / "robustness_results.json"
    rob = load_json(rob_path)
    if rob:
        rob_summary = rob.get("summary", {})
        pr = safe_float(rob_summary.get("pass_rate"))
        if pr is not None:
            robustness_pass_rate = pr / 100.0  # Stored as 0-1 in DB

    # ── Param sensitivity ────────────────────────────────────────────
    param_stability = None
    param_path = run_path / "param_analysis" / "sensitivity_results.json"
    param = load_json(param_path)
    if param:
        param_stability = safe_float(param.get("stability_score"))

    # ── Build row ────────────────────────────────────────────────────
    return {
        "run_id":               run_id,
        "ea_name":              resolved_ea,
        "run_path":             str(run_path),
        "timestamp":            ts.isoformat() if ts else None,
        "symbol":               symbol,
        "period":               period,
        "date_from":            date_from,
        "date_to":              date_to,
        "deposit":              deposit,
        "n_trades":             n_trades,
        "net_profit":           net_profit,
        "profit_factor":        profit_factor,
        "win_rate":             win_rate,
        "avg_win":              avg_win,
        "avg_loss":             avg_loss,
        "max_dd_pct":           max_dd_pct,
        "max_dd_abs":           max_dd_abs,
        "expectancy":           expectancy,
        "start_equity":         start_equity,
        "final_equity":         final_equity,
        "max_win_streak":       max_win_streak,
        "max_loss_streak":      max_loss_streak,
        "trades_per_year":      trades_per_year,
        "cagr":                 cagr,
        "years":                years,
        "win_loss_ratio":       win_loss_ratio,
        "sqn":                  sqn,
        "wfa_efficiency":       wfa_efficiency,
        "wfa_oos_ratio":        wfa_oos_ratio,
        "mc_p95_dd":            mc_p95_dd,
        "robustness_pass_rate": robustness_pass_rate,
        "param_stability":      param_stability,
    }


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

class RunsDB:
    """SQLite wrapper for the runs database."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()

    def create_tables(self):
        self.conn.executescript(CREATE_TABLE_SQL)
        self.conn.commit()

    def drop_tables(self):
        self.conn.execute("DROP TABLE IF EXISTS runs")
        self.conn.commit()

    def insert_run(self, data: Dict[str, Any]):
        cols = [k for k in data.keys()]
        placeholders = [":" + k for k in cols]
        sql = f"""
            INSERT OR REPLACE INTO runs ({', '.join(cols)})
            VALUES ({', '.join(placeholders)})
        """
        self.conn.execute(sql, data)

    def build(self, runs_dir: Path = RUNS_DIR):
        """Rebuild database from scratch."""
        log.info(f"Scanning runs in: {runs_dir}")
        runs = discover_runs(runs_dir)
        log.info(f"Found {len(runs)} run folders")

        self.drop_tables()
        self.create_tables()

        inserted = 0
        skipped = 0
        errors = 0

        for ea_name, run_id, run_path in runs:
            try:
                row = parse_run(ea_name, run_id, run_path)
                if row is None:
                    skipped += 1
                    continue
                self.insert_run(row)
                inserted += 1
            except Exception as e:
                log.warning(f"ERROR {ea_name}/{run_id}: {e}")
                errors += 1

        self.conn.commit()
        log.info(f"Build complete: {inserted} inserted, {skipped} skipped, {errors} errors")
        return inserted, skipped, errors

    def query_raw(self, sql: str, params=()) -> List[sqlite3.Row]:
        """Execute raw SQL and return rows."""
        return self.conn.execute(sql, params).fetchall()

    def translate_query(self, human_query: str) -> str:
        """
        Translate human-readable query conditions to SQL WHERE clause.
        E.g. "PF > 1.5 AND DD < 8" -> "profit_factor > 1.5 AND max_dd_pct < 8"
        """
        result = human_query
        # Sort by length descending to avoid partial replacements
        for alias, col in sorted(COLUMN_ALIASES.items(), key=lambda x: -len(x[0])):
            # Case-insensitive word boundary replacement
            result = re.sub(
                rf'\b{re.escape(alias)}\b',
                col,
                result,
                flags=re.IGNORECASE
            )
        return result

    def query_human(self, conditions: str, order_by: str = "net_profit DESC",
                    limit: int = 50) -> List[sqlite3.Row]:
        """Query with human-readable conditions."""
        where = self.translate_query(conditions)
        sql = f"""
            SELECT run_id, ea_name, n_trades, net_profit, profit_factor,
                   win_rate, max_dd_pct, expectancy, trades_per_year, cagr,
                   win_loss_ratio, max_loss_streak,
                   wfa_efficiency, mc_p95_dd, robustness_pass_rate, param_stability,
                   timestamp
            FROM runs
            WHERE {where}
            ORDER BY {order_by}
            LIMIT {limit}
        """
        try:
            return self.conn.execute(sql).fetchall()
        except sqlite3.OperationalError as e:
            log.error(f"SQL error: {e}")
            log.error(f"Translated query: {sql}")
            return []

    def top_runs(self, n: int = 10, order_by: str = "net_profit DESC") -> List[sqlite3.Row]:
        """Return top N runs."""
        sql = f"""
            SELECT run_id, ea_name, n_trades, net_profit, profit_factor,
                   win_rate, max_dd_pct, expectancy, trades_per_year, cagr,
                   win_loss_ratio, max_loss_streak,
                   wfa_efficiency, mc_p95_dd, robustness_pass_rate,
                   timestamp
            FROM runs
            WHERE n_trades > 0
            ORDER BY {order_by}
            LIMIT {n}
        """
        return self.conn.execute(sql).fetchall()

    def compare_runs(self, run_id1: str, run_id2: str) -> Tuple[Optional[sqlite3.Row], Optional[sqlite3.Row]]:
        """Fetch two runs for comparison. Supports partial run_id matching."""
        def find_run(rid):
            # Exact match first
            row = self.conn.execute(
                "SELECT * FROM runs WHERE run_id = ?", (rid,)
            ).fetchone()
            if row:
                return row
            # Partial match
            row = self.conn.execute(
                "SELECT * FROM runs WHERE run_id LIKE ?", (f"%{rid}%",)
            ).fetchone()
            return row

        return find_run(run_id1), find_run(run_id2)

    def check_gates(self) -> List[Dict[str, Any]]:
        """Check all runs against PROP_READY gates."""
        rows = self.conn.execute("""
            SELECT run_id, ea_name, n_trades, net_profit, profit_factor,
                   win_rate, max_dd_pct, cagr, trades_per_year,
                   avg_win, avg_loss, win_loss_ratio, max_loss_streak,
                   wfa_efficiency, wfa_oos_ratio, mc_p95_dd,
                   robustness_pass_rate, param_stability, timestamp
            FROM runs
            WHERE n_trades > 0
            ORDER BY net_profit DESC
        """).fetchall()

        results = []
        for row in rows:
            rd = dict(row)
            gate_results = {}
            passed_count = 0
            total_count = 0

            for gate_name, gate_def in GATES.items():
                op = gate_def["op"]
                threshold = gate_def["val"]
                nullable = gate_def["nullable"]

                # Get the value to check
                if gate_name == "win_loss_ratio":
                    val = rd.get("win_loss_ratio")
                else:
                    val = rd.get(gate_name)

                if val is None:
                    if nullable:
                        gate_results[gate_name] = {"status": "N/A", "value": None, "threshold": threshold}
                        # Don't count nullable gates against the run
                        continue
                    else:
                        gate_results[gate_name] = {"status": "FAIL", "value": None, "threshold": threshold}
                        total_count += 1
                        continue

                # Check gate
                total_count += 1
                if op == ">=" and val >= threshold:
                    gate_results[gate_name] = {"status": "PASS", "value": val, "threshold": threshold}
                    passed_count += 1
                elif op == "<=" and val <= threshold:
                    gate_results[gate_name] = {"status": "PASS", "value": val, "threshold": threshold}
                    passed_count += 1
                else:
                    gate_results[gate_name] = {"status": "FAIL", "value": val, "threshold": threshold}

            rd["gates"] = gate_results
            rd["gates_passed"] = passed_count
            rd["gates_total"] = total_count
            rd["gates_all_pass"] = (passed_count == total_count) and total_count > 0
            results.append(rd)

        return results

    def summary_by_ea(self) -> List[sqlite3.Row]:
        """Summary stats grouped by EA."""
        sql = """
            SELECT ea_name,
                   COUNT(*) as n_runs,
                   ROUND(AVG(profit_factor), 2) as avg_pf,
                   ROUND(MAX(profit_factor), 2) as max_pf,
                   ROUND(AVG(net_profit), 0) as avg_profit,
                   ROUND(MAX(net_profit), 0) as max_profit,
                   ROUND(AVG(max_dd_pct), 1) as avg_dd,
                   ROUND(AVG(n_trades), 0) as avg_trades,
                   ROUND(AVG(win_rate), 1) as avg_wr,
                   MIN(timestamp) as first_run,
                   MAX(timestamp) as last_run
            FROM runs
            WHERE n_trades > 0
            GROUP BY ea_name
            ORDER BY max_profit DESC
        """
        return self.conn.execute(sql).fetchall()

    def get_run(self, run_id: str) -> Optional[sqlite3.Row]:
        """Get a single run by exact or partial ID."""
        row = self.conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row:
            return row
        return self.conn.execute(
            "SELECT * FROM runs WHERE run_id LIKE ?", (f"%{run_id}%",)
        ).fetchone()


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def fmt_val(val, fmt=".2f", suffix="", na="—"):
    """Format a value for display."""
    if val is None:
        return na
    try:
        return f"{val:{fmt}}{suffix}"
    except (ValueError, TypeError):
        return str(val)


def gate_icon(status: str) -> str:
    """Return icon for gate status."""
    return {"PASS": "✅", "FAIL": "❌", "N/A": "⬜"}.get(status, "?")


def print_table(headers: List[str], rows: List[List[str]], min_widths: Optional[List[int]] = None):
    """Print a formatted ASCII table."""
    if not rows:
        print("  (no results)")
        return

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    if min_widths:
        for i, mw in enumerate(min_widths):
            if i < len(widths):
                widths[i] = max(widths[i], mw)

    # Header
    header_line = " │ ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep_line = "─┼─".join("─" * widths[i] for i in range(len(headers)))
    print(f" {header_line}")
    print(f" {sep_line}")

    # Rows
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            s = str(cell)
            # Right-align numeric-looking cells
            if re.match(r'^[\-\d\.\,]+%?$', s.strip().replace("—", "")):
                cells.append(s.rjust(widths[i]))
            else:
                cells.append(s.ljust(widths[i]))
        print(f" {' │ '.join(cells)}")


def display_top(db: RunsDB, n: int = 10):
    """Display top N runs by net profit."""
    rows = db.top_runs(n)
    if not rows:
        print("No runs found in database.")
        return

    headers = ["#", "Run ID", "EA", "Trades", "Net $", "PF", "WR%",
               "DD%", "TPY", "CAGR%", "W/L", "Streak", "WFA", "MC DD", "Rob%"]
    table_rows = []
    for i, row in enumerate(rows, 1):
        d = dict(row)
        table_rows.append([
            str(i),
            d["run_id"],
            (d["ea_name"] or "?")[:14],
            fmt_val(d["n_trades"], "d"),
            fmt_val(d["net_profit"], ",.0f"),
            fmt_val(d["profit_factor"], ".2f"),
            fmt_val(d["win_rate"], ".1f"),
            fmt_val(d["max_dd_pct"], ".1f"),
            fmt_val(d["trades_per_year"], ".0f"),
            fmt_val(d["cagr"], ".1f"),
            fmt_val(d["win_loss_ratio"], ".2f"),
            fmt_val(d["max_loss_streak"], "d"),
            fmt_val(d["wfa_efficiency"], ".2f"),
            fmt_val(d["mc_p95_dd"], ".1f"),
            fmt_val(d["robustness_pass_rate"], ".0%") if d["robustness_pass_rate"] is not None else "—",
        ])

    print(f"\n  Top {n} Runs by Net Profit")
    print(f"  {'='*80}")
    print_table(headers, table_rows)
    print()


def display_query(db: RunsDB, conditions: str):
    """Display query results."""
    rows = db.query_human(conditions)
    translated = db.translate_query(conditions)

    print(f"\n  Query: {conditions}")
    print(f"  SQL:   WHERE {translated}")
    print(f"  {'='*80}")

    if not rows:
        print("  No matching runs.")
        return

    headers = ["#", "Run ID", "EA", "Trades", "Net $", "PF", "WR%",
               "DD%", "TPY", "CAGR%", "W/L", "Streak"]
    table_rows = []
    for i, row in enumerate(rows, 1):
        d = dict(row)
        table_rows.append([
            str(i),
            d["run_id"],
            (d["ea_name"] or "?")[:14],
            fmt_val(d["n_trades"], "d"),
            fmt_val(d["net_profit"], ",.0f"),
            fmt_val(d["profit_factor"], ".2f"),
            fmt_val(d["win_rate"], ".1f"),
            fmt_val(d["max_dd_pct"], ".1f"),
            fmt_val(d["trades_per_year"], ".0f"),
            fmt_val(d["cagr"], ".1f"),
            fmt_val(d["win_loss_ratio"], ".2f"),
            fmt_val(d["max_loss_streak"], "d"),
        ])

    print(f"  {len(rows)} results:")
    print_table(headers, table_rows)
    print()


def display_compare(db: RunsDB, id1: str, id2: str):
    """Side-by-side comparison of two runs."""
    r1, r2 = db.compare_runs(id1, id2)

    if r1 is None:
        print(f"  ❌ Run '{id1}' not found")
        return
    if r2 is None:
        print(f"  ❌ Run '{id2}' not found")
        return

    d1 = dict(r1)
    d2 = dict(r2)

    print(f"\n  Run Comparison")
    print(f"  {'='*72}")

    fields = [
        ("Run ID",              "run_id",               None),
        ("EA Name",             "ea_name",              None),
        ("Symbol",              "symbol",               None),
        ("Period",              "period",               None),
        ("Date Range",          "date_from",            None),
        ("─── Core Metrics",    None,                   None),
        ("Trades",              "n_trades",             "d"),
        ("Net Profit",          "net_profit",           ",.2f"),
        ("Profit Factor",       "profit_factor",        ".3f"),
        ("Win Rate %",          "win_rate",             ".1f"),
        ("Avg Win",             "avg_win",              ",.2f"),
        ("Avg Loss",            "avg_loss",             ",.2f"),
        ("Win/Loss Ratio",      "win_loss_ratio",       ".2f"),
        ("Expectancy",          "expectancy",           ",.2f"),
        ("Max DD %",            "max_dd_pct",           ".2f"),
        ("Max DD $",            "max_dd_abs",           ",.2f"),
        ("─── Calculated",      None,                   None),
        ("CAGR %",              "cagr",                 ".1f"),
        ("Trades/Year",         "trades_per_year",      ".0f"),
        ("Years",               "years",                ".1f"),
        ("Win Streak",          "max_win_streak",       "d"),
        ("Loss Streak",         "max_loss_streak",      "d"),
        ("SQN",                 "sqn",                  ".2f"),
        ("─── Robustness",      None,                   None),
        ("WFA Efficiency",      "wfa_efficiency",       ".2f"),
        ("WFA OOS Ratio",       "wfa_oos_ratio",        ".2f"),
        ("MC P95 DD",           "mc_p95_dd",            ".1f"),
        ("Robustness Rate",     "robustness_pass_rate", ".0%"),
        ("Param Stability",     "param_stability",      ".1f"),
    ]

    for label, key, fmt in fields:
        if key is None:
            # Section separator
            print(f"  {label}{'─'*(70 - len(label))}")
            continue

        v1 = d1.get(key)
        v2 = d2.get(key)

        if fmt and key != "run_id" and key != "ea_name" and key != "symbol" and key != "period" and key != "date_from":
            s1 = fmt_val(v1, fmt)
            s2 = fmt_val(v2, fmt)
            # Show delta
            if v1 is not None and v2 is not None:
                try:
                    delta = float(v2) - float(v1)
                    sign = "+" if delta >= 0 else ""
                    delta_s = f"({sign}{delta:{fmt}})"
                except (ValueError, TypeError):
                    delta_s = ""
            else:
                delta_s = ""
        else:
            s1 = str(v1 or "—")
            s2 = str(v2 or "—")
            delta_s = ""

        print(f"  {label:<22} │ {s1:>14} │ {s2:>14} │ {delta_s}")

    print()


def display_gates(db: RunsDB):
    """Display gate check results."""
    results = db.check_gates()

    if not results:
        print("No runs found in database.")
        return

    # First show runs that pass all gates
    all_pass = [r for r in results if r["gates_all_pass"]]
    partial = [r for r in results if not r["gates_all_pass"]]

    gate_names = list(GATES.keys())
    short_names = {
        "cagr": "CAGR",
        "max_dd_pct": "DD%",
        "trades_per_year": "TPY",
        "win_loss_ratio": "W/L",
        "max_loss_streak": "Strk",
        "wfa_efficiency": "WFA",
        "mc_p95_dd": "MC",
        "robustness_pass_rate": "Rob",
    }

    print(f"\n  PROP_READY Gate Check — {len(results)} runs evaluated")
    print(f"  {'='*90}")

    if all_pass:
        print(f"\n  ✅ PROP_READY ({len(all_pass)} runs pass ALL gates):")
        print(f"  {'-'*90}")

        headers = ["Run ID", "EA", "Net $", "PF"] + [short_names[g] for g in gate_names]
        table_rows = []
        for r in all_pass:
            row = [
                r["run_id"],
                (r["ea_name"] or "?")[:12],
                fmt_val(r["net_profit"], ",.0f"),
                fmt_val(r["profit_factor"], ".2f"),
            ]
            for gn in gate_names:
                gi = r["gates"][gn]
                row.append(gate_icon(gi["status"]))
            table_rows.append(row)
        print_table(headers, table_rows)
    else:
        print(f"\n  ⚠️  No runs pass ALL gates.")

    # Show top 15 partial passes
    partial_sorted = sorted(partial, key=lambda r: r["gates_passed"], reverse=True)[:15]
    if partial_sorted:
        print(f"\n  ⏳ Top partial passes ({len(partial)} total, showing top 15):")
        print(f"  {'-'*90}")

        headers = ["Run ID", "EA", "Pass", "Net $"] + [short_names[g] for g in gate_names]
        table_rows = []
        for r in partial_sorted:
            row = [
                r["run_id"],
                (r["ea_name"] or "?")[:12],
                f"{r['gates_passed']}/{r['gates_total']}",
                fmt_val(r["net_profit"], ",.0f"),
            ]
            for gn in gate_names:
                gi = r["gates"][gn]
                if gi["status"] == "N/A":
                    row.append("⬜")
                elif gi["status"] == "PASS":
                    row.append("✅")
                else:
                    # Show actual value for failed gates
                    v = gi["value"]
                    if v is not None:
                        row.append(f"❌{v:.1f}")
                    else:
                        row.append("❌ —")
            table_rows.append(row)
        print_table(headers, table_rows)

    # Gate threshold reference
    print(f"\n  Gate thresholds:")
    for gn, gd in GATES.items():
        print(f"    {short_names[gn]:<6} │ {gn:<24} {gd['op']} {gd['val']}{gd['unit']}"
              f"{'  (nullable)' if gd['nullable'] else ''}")
    print()


def display_summary(db: RunsDB):
    """Display summary by EA."""
    rows = db.summary_by_ea()

    print(f"\n  EA Summary")
    print(f"  {'='*80}")

    headers = ["EA", "Runs", "Avg PF", "Max PF", "Avg $", "Max $",
               "Avg DD%", "Avg Trades", "Avg WR%", "First Run", "Last Run"]
    table_rows = []
    for row in rows:
        d = dict(row)
        table_rows.append([
            (d["ea_name"] or "?")[:16],
            str(d["n_runs"]),
            fmt_val(d["avg_pf"], ".2f"),
            fmt_val(d["max_pf"], ".2f"),
            fmt_val(d["avg_profit"], ",.0f"),
            fmt_val(d["max_profit"], ",.0f"),
            fmt_val(d["avg_dd"], ".1f"),
            fmt_val(d["avg_trades"], ".0f"),
            fmt_val(d["avg_wr"], ".1f"),
            (d["first_run"] or "—")[:10],
            (d["last_run"] or "—")[:10],
        ])

    print_table(headers, table_rows)

    # Total count
    total = sum(dict(r)["n_runs"] for r in rows)
    print(f"\n  Total: {total} runs across {len(rows)} EAs")
    print()


def display_info(db: RunsDB, run_id: str):
    """Display detailed info for a single run."""
    row = db.get_run(run_id)
    if row is None:
        print(f"  ❌ Run '{run_id}' not found")
        return

    d = dict(row)

    print(f"\n  Run Details: {d['run_id']}")
    print(f"  {'='*60}")

    sections = [
        ("Identity", [
            ("EA Name",        d["ea_name"]),
            ("Run Path",       d["run_path"]),
            ("Timestamp",      d["timestamp"]),
            ("Symbol",         d["symbol"]),
            ("Period",         d["period"]),
            ("Date Range",     f"{d['date_from']} — {d['date_to']}"),
            ("Deposit",        fmt_val(d["deposit"], ",.0f", " USD")),
        ]),
        ("Core Metrics", [
            ("Trades",         fmt_val(d["n_trades"], "d")),
            ("Net Profit",     fmt_val(d["net_profit"], ",.2f", " USD")),
            ("Profit Factor",  fmt_val(d["profit_factor"], ".3f")),
            ("Win Rate",       fmt_val(d["win_rate"], ".1f", "%")),
            ("Avg Win",        fmt_val(d["avg_win"], ",.2f", " USD")),
            ("Avg Loss",       fmt_val(d["avg_loss"], ",.2f", " USD")),
            ("Win/Loss Ratio", fmt_val(d["win_loss_ratio"], ".2f")),
            ("Expectancy",     fmt_val(d["expectancy"], ",.2f", " USD/trade")),
            ("Max DD %",       fmt_val(d["max_dd_pct"], ".2f", "%")),
            ("Max DD $",       fmt_val(d["max_dd_abs"], ",.2f", " USD")),
        ]),
        ("Calculated", [
            ("CAGR",           fmt_val(d["cagr"], ".1f", "%")),
            ("Trades/Year",    fmt_val(d["trades_per_year"], ".0f")),
            ("Years",          fmt_val(d["years"], ".1f")),
            ("Max Win Streak", fmt_val(d["max_win_streak"], "d")),
            ("Max Loss Streak",fmt_val(d["max_loss_streak"], "d")),
            ("SQN",            fmt_val(d["sqn"], ".2f")),
        ]),
        ("Robustness", [
            ("WFA Efficiency",      fmt_val(d["wfa_efficiency"], ".2f")),
            ("WFA OOS Ratio",       fmt_val(d["wfa_oos_ratio"], ".2f")),
            ("MC P95 DD",           fmt_val(d["mc_p95_dd"], ".1f", "%")),
            ("Robustness Pass Rate",fmt_val(d["robustness_pass_rate"], ".0%") if d["robustness_pass_rate"] is not None else "—"),
            ("Param Stability",     fmt_val(d["param_stability"], ".1f")),
        ]),
    ]

    for section_name, fields in sections:
        print(f"\n  ── {section_name} {'─'*(55 - len(section_name))}")
        for label, value in fields:
            print(f"  {label:<22} │ {value}")

    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

USAGE = """
Usage:
  python runs_db.py build                          Rebuild DB from scratch
  python runs_db.py query "PF > 1.5 AND DD < 8"   Query with human conditions
  python runs_db.py top [N]                        Top N runs by profit (default 10)
  python runs_db.py compare <run_id1> <run_id2>    Side-by-side comparison
  python runs_db.py gates                          PROP_READY gate check
  python runs_db.py summary                        Summary stats per EA
  python runs_db.py info <run_id>                  Detailed info for one run
  python runs_db.py sql "SELECT ..."               Raw SQL query

Aliases for query conditions:
  PF=profit_factor  DD=max_dd_pct  WR=win_rate  TPY=trades_per_year
  WL=win_loss_ratio  EA=ea_name  TRADES=n_trades  PROFIT=net_profit
  WFA=wfa_efficiency  MC=mc_p95_dd  ROBUST=robustness_pass_rate
  PARAM=param_stability  STREAK=max_loss_streak  EXP=expectancy

Examples:
  python runs_db.py query "PF > 1.5 AND DD < 8 AND trades > 200"
  python runs_db.py query "ea = 'v6' AND PF > 1.3"
  python runs_db.py compare 20260311_071217 20260320_084324
"""


def main():
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "build":
        with RunsDB() as db:
            inserted, skipped, errors = db.build()
            print(f"\n  ✅ Database built: {DB_PATH}")
            print(f"     {inserted} runs indexed, {skipped} skipped, {errors} errors\n")
            display_summary(db)

    elif command == "query":
        if len(sys.argv) < 3:
            print("  Usage: python runs_db.py query \"PF > 1.5 AND DD < 8\"")
            sys.exit(1)
        conditions = sys.argv[2]
        with RunsDB() as db:
            display_query(db, conditions)

    elif command == "top":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        with RunsDB() as db:
            display_top(db, n)

    elif command == "compare":
        if len(sys.argv) < 4:
            print("  Usage: python runs_db.py compare <run_id1> <run_id2>")
            sys.exit(1)
        with RunsDB() as db:
            display_compare(db, sys.argv[2], sys.argv[3])

    elif command == "gates":
        with RunsDB() as db:
            display_gates(db)

    elif command == "summary":
        with RunsDB() as db:
            display_summary(db)

    elif command == "info":
        if len(sys.argv) < 3:
            print("  Usage: python runs_db.py info <run_id>")
            sys.exit(1)
        with RunsDB() as db:
            display_info(db, sys.argv[2])

    elif command == "sql":
        if len(sys.argv) < 3:
            print("  Usage: python runs_db.py sql \"SELECT ...\"")
            sys.exit(1)
        with RunsDB() as db:
            try:
                rows = db.query_raw(sys.argv[2])
                if rows:
                    headers = rows[0].keys()
                    table_rows = [[str(r[k]) for k in headers] for r in rows]
                    print_table(list(headers), table_rows)
                else:
                    print("  (no results)")
            except sqlite3.OperationalError as e:
                print(f"  SQL Error: {e}")

    else:
        print(f"  Unknown command: {command}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
