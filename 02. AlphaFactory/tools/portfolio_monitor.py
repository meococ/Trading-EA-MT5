#!/usr/bin/env python3
"""Portfolio Performance Monitor — Paper Deploy Tracker.

Reads trade history from MT5 datalog CSV exports (or manual entry) and
compares live performance against backtest expectations for each EA.

Usage:
    python portfolio_monitor.py                               # show status
    python portfolio_monitor.py --add EA_Cobra sell 450       # log a trade manually
    python portfolio_monitor.py --find-csvs                   # list likely MT5 trade CSV exports
    python portfolio_monitor.py --import-csv path/to.csv      # import MT5/account-history CSV
    python portfolio_monitor.py --import-latest               # auto-import newest matching CSV
    python portfolio_monitor.py --check-export-paths          # verify PaperDeploy export folders/files
    python portfolio_monitor.py --report                      # detailed report
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ── Portfolio baseline expectations (from validated backtests) ──────────
PORTFOLIO = {
    "EA_Cobra": {
        "symbol": "XAUUSD",
        "tf": "M15",
        "magic": 202604,
        "pf_expected": 1.90,
        "trades_per_year": 28,
        "dd_max_pct": 9.1,
        "mc_p95_dd": 23.7,
        "bootstrap_ci": [1.386, 2.644],
        "win_rate": 55.5,
        "avg_win": 354.23,
        "avg_loss": -257.59,
        "risk_pct": 0.50,
        "status": "FUND-GRADE",
    },
    "EA_SilverBullet": {
        "symbol": "USDJPY",
        "tf": "M15",
        "magic": 20260325,
        "pf_expected": 1.28,
        "trades_per_year": 101,
        "dd_max_pct": 4.75,
        "mc_p95_dd": 16.0,
        "bootstrap_ci": [1.097, 1.505],
        "win_rate": 50.0,
        "avg_win": 370.0,
        "avg_loss": -243.0,
        "risk_pct": 0.50,
        "status": "DEPLOY",
        "monitor_regime_note": "Watch MID_VOL + DOWNTREND USDJPY (retrospective PF 0.57) and BOJ EVENT_WEEK (PF ~0.98, n=12). Monitor-only, not auto-disable.",
    },
    "EA_Spark_USDJPY": {
        "symbol": "USDJPY",
        "tf": "M15",
        "magic": 20260321,
        "pf_expected": 1.26,
        "trades_per_year": 71,
        "dd_max_pct": 6.0,
        "mc_p95_dd": 12.1,
        "bootstrap_ci": [0.99, 1.53],
        "win_rate": 52.0,
        "avg_win": 300.0,
        "avg_loss": -240.0,
        "risk_pct": 0.40,
        "status": "DEPLOY",
        "monitor_regime_note": "Watch LOW_VOL USDJPY and BOJ EVENT_WEEK pockets; retrospective EVENT_WEEK looked strong but n=10 is too thin for control logic. Monitor-only, not auto-disable.",
    },
    "EA_Spark_GBPUSD": {
        "symbol": "GBPUSD",
        "tf": "M15",
        "magic": 20260322,
        "pf_expected": 1.35,
        "trades_per_year": 30,
        "dd_max_pct": 7.6,
        "mc_p95_dd": 7.1,
        "bootstrap_ci": [1.05, 1.73],
        "win_rate": 54.0,
        "avg_win": 280.0,
        "avg_loss": -230.0,
        "risk_pct": 0.50,
        "status": "DEPLOY",
    },
    "EA_InsideBar_USDJPY": {
        "symbol": "USDJPY",
        "tf": "H1",
        "magic": 20260391,
        "pf_expected": 1.53,
        "trades_per_year": 17,
        "dd_max_pct": 3.4,
        "mc_p95_dd": 5.3,
        "bootstrap_ci": [1.10, 2.27],
        "win_rate": 50.4,
        "avg_win": 350.0,
        "avg_loss": -240.0,
        "risk_pct": 0.40,
        "status": "SATELLITE",
    },
    "EA_InsideBar_GBPUSD": {
        "symbol": "GBPUSD",
        "tf": "H1",
        "magic": 20260392,
        "pf_expected": 2.00,
        "trades_per_year": 7.7,
        "dd_max_pct": 4.4,
        "mc_p95_dd": 6.8,
        "bootstrap_ci": [1.13, 3.68],
        "win_rate": 57.4,
        "avg_win": 164.76,
        "avg_loss": -111.02,
        "risk_pct": 0.50,
        "status": "SATELLITE",
    },
}

# ── Paths ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
TRADES_FILE = SCRIPT_DIR / "portfolio_trades.csv"
FIELDNAMES = ["timestamp", "ea", "symbol", "direction", "profit", "comment"]
DEFAULT_IMPORT_DIRS = [
    Path(r"C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\Common\Files\PaperDeploy"),
    Path(r"C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\Common\Files"),
    Path(r"C:\Users\ADMIN\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files"),
]
CSV_ALIASES = {
    "timestamp": ["timestamp", "time", "date", "open time", "close time"],
    "symbol": ["symbol"],
    "direction": ["direction", "type", "side"],
    "profit": ["profit", "pnl", "net profit"],
    "comment": ["comment", "comments"],
    "magic": ["magic", "magic number"],
}


def _normalize_key(name: str) -> str:
    return name.strip().lower().replace("_", " ")


def _pick_field(row: dict, aliases: list[str]) -> str:
    normalized = {_normalize_key(k): v for k, v in row.items()}
    for alias in aliases:
        if alias in normalized and normalized[alias] not in (None, ""):
            return str(normalized[alias]).strip()
    return ""


def _infer_ea(symbol: str, magic: str, comment: str) -> str:
    symbol = symbol.upper()
    comment_u = comment.upper()
    magic_i = int(float(magic)) if magic not in ("", None) else None

    for ea_name, cfg in PORTFOLIO.items():
        if magic_i is not None and cfg.get("magic") == magic_i and cfg.get("symbol", "").upper() == symbol:
            return ea_name

    if "SB2" in comment_u and symbol == "USDJPY":
        return "EA_SilverBullet"
    if "IB1_GU" in comment_u and symbol == "GBPUSD":
        return "EA_InsideBar_GBPUSD"
    if "IB1" in comment_u and symbol == "USDJPY":
        return "EA_InsideBar_USDJPY"
    if symbol == "XAUUSD":
        return "EA_Cobra"
    if symbol == "USDJPY":
        return "EA_Spark_USDJPY"
    if symbol == "GBPUSD":
        return "EA_Spark_GBPUSD"
    return ""


def find_candidate_csvs(limit: int = 20) -> list[Path]:
    """Find likely MT5 trade CSV exports for the active deploy portfolio only."""
    candidates = []
    seen = set()
    patterns = ["*Trades*.csv", "**/trades_*.csv"]

    for root in DEFAULT_IMPORT_DIRS:
        if not root.exists():
            continue
        for pattern in patterns:
            for path in root.rglob(pattern):
                if path in seen:
                    continue
                seen.add(path)

                try:
                    with open(path, newline="", encoding="utf-8-sig") as f:
                        reader = csv.DictReader(f)
                        matched = False
                        for _ in range(5):
                            row = next(reader, None)
                            if row is None:
                                break
                            symbol = _pick_field(row, CSV_ALIASES["symbol"])
                            magic = _pick_field(row, CSV_ALIASES["magic"])
                            comment = _pick_field(row, CSV_ALIASES["comment"])
                            if _infer_ea(symbol, magic, comment):
                                matched = True
                                break
                        if not matched:
                            continue
                except Exception:
                    continue

                candidates.append(path)

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[:limit]

def import_trades(csv_path: Path) -> int:
    """Import MT5-exported trades into portfolio_trades.csv with de-duplication."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    existing = load_trades()
    existing_keys = {
        (t["timestamp"], t["ea"], t["symbol"], t["direction"], f"{float(t['profit']):.2f}", t.get("comment", ""))
        for t in existing
    }

    imported_rows = []
    total_rows = 0
    unknown_rows = 0
    unknown_examples = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = _pick_field(row, CSV_ALIASES["symbol"])
            profit_s = _pick_field(row, CSV_ALIASES["profit"])
            if not symbol or not profit_s:
                continue
            total_rows += 1

            try:
                profit = float(profit_s.replace(",", ""))
            except ValueError:
                continue

            direction = _pick_field(row, CSV_ALIASES["direction"]).lower()
            timestamp = _pick_field(row, CSV_ALIASES["timestamp"])
            comment = _pick_field(row, CSV_ALIASES["comment"])
            magic = _pick_field(row, CSV_ALIASES["magic"])
            ea = _infer_ea(symbol, magic, comment)
            if not ea:
                unknown_rows += 1
                if len(unknown_examples) < 3:
                    unknown_examples.append(f"symbol={symbol} magic={magic} comment={comment}")
                continue

            record = {
                "timestamp": timestamp or datetime.now().isoformat(timespec="seconds"),
                "ea": ea,
                "symbol": symbol,
                "direction": direction or "unknown",
                "profit": profit,
                "comment": comment,
            }
            key = (record["timestamp"], record["ea"], record["symbol"], record["direction"], f"{record['profit']:.2f}", record["comment"])
            if key not in existing_keys:
                existing_keys.add(key)
                imported_rows.append(record)

    if not imported_rows:
        if total_rows > 0 and unknown_rows == total_rows:
            print(f"[INFO] CSV has {total_rows} trade row(s) but none match the active deploy portfolio.")
            for ex in unknown_examples:
                print(f"  example: {ex}")
            print("[INFO] This usually means the file belongs to an old backtest/stale artifact, not the live deploy stack.")
        return 0

    is_new = not TRADES_FILE.exists()
    with open(TRADES_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if is_new:
            writer.writeheader()
        for row in imported_rows:
            writer.writerow(row)
    return len(imported_rows)


def load_trades() -> list[dict]:
    """Load trade log from CSV."""
    if not TRADES_FILE.exists():
        return []
    trades = []
    with open(TRADES_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["profit"] = float(row["profit"])
            trades.append(row)
    return trades


def check_export_paths():
    """Check whether PaperDeploy export folders/files are appearing as expected."""
    root = DEFAULT_IMPORT_DIRS[0]
    print("=" * 72)
    print(f"  PAPERDEPLOY EXPORT CHECK — {root}")
    print("=" * 72)
    if not root.exists():
        print("[INFO] PaperDeploy root does not exist yet.")
        print("[NEXT] This is expected before the first live trade closes.")
        return

    for ea_name, cfg in PORTFOLIO.items():
        if ea_name == "EA_Cobra":
            folder = root / "EA_Cobra"
        elif ea_name == "EA_SilverBullet":
            folder = root / "EA_SilverBullet"
        elif ea_name.startswith("EA_Spark"):
            folder = root / "EA_Spark"
        elif ea_name.startswith("EA_InsideBar"):
            folder = root / "EA_InsideBar"
        else:
            folder = root

        expected = folder / f"trades_{cfg['magic']}.csv"
        folder_ok = folder.exists()
        file_ok = expected.exists()
        print(f"{ea_name:24s} | folder={'YES' if folder_ok else 'NO ':3s} | file={'YES' if file_ok else 'NO ':3s} | {expected}")


def save_trade(ea: str, direction: str, profit: float, comment: str = ""):
    """Append a trade to the CSV log."""
    is_new = not TRADES_FILE.exists()
    with open(TRADES_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "ea": ea,
            "symbol": PORTFOLIO.get(ea, {}).get("symbol", "?"),
            "direction": direction,
            "profit": profit,
            "comment": comment,
        })
    print(f"[OK] Logged: {ea} {direction} ${profit:.2f}")


def show_status(trades: list[dict]):
    """Show portfolio status dashboard."""
    now = datetime.now()
    print("=" * 72)
    print(f"  PORTFOLIO MONITOR — {now.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 72)
    print()

    total_trades = 0
    total_pnl = 0.0

    for ea_name, cfg in PORTFOLIO.items():
        ea_trades = [t for t in trades if t["ea"] == ea_name]
        n = len(ea_trades)
        total_trades += n

        wins = [t for t in ea_trades if t["profit"] > 0]
        losses = [t for t in ea_trades if t["profit"] < 0]
        pnl = sum(t["profit"] for t in ea_trades)
        total_pnl += pnl

        if wins and losses:
            pf = sum(t["profit"] for t in wins) / abs(sum(t["profit"] for t in losses))
            wr = 100 * len(wins) / n
        elif wins:
            pf = 99.0
            wr = 100.0
        elif losses:
            pf = 0.0
            wr = 0.0
        else:
            pf = None
            wr = None

        # Calculate expected trades from actual live log history, not a placeholder
        if ea_trades:
            first_ts = min(datetime.fromisoformat(t["timestamp"]) for t in ea_trades)
            days_active = max((now - first_ts).days + 1, 1)
        else:
            days_active = 0
        expected_trades = cfg["trades_per_year"] * days_active / 252 if days_active > 0 else 0.0
        trade_pace = (n / expected_trades) if expected_trades > 0 else None

        # Status flags
        flags = []
        if trade_pace is not None and n >= 5:
            if trade_pace < 0.5:
                flags.append(f"[WARN] Trade pace low ({n:.0f} vs exp {expected_trades:.1f})")
            elif trade_pace > 1.8:
                flags.append(f"[WARN] Trade pace high ({n:.0f} vs exp {expected_trades:.1f})")
        elif n == 0:
            flags.append("[INFO] No live trades logged yet")
        elif expected_trades == 0:
            flags.append("[INFO] Need more elapsed time for pace check")

        pace_str = f"{n:.0f}/{expected_trades:.1f}" if expected_trades > 0 else f"{n:.0f}/-"

        # Performance flags
        flags = list(flags)
        if pf is not None:
            if pf < cfg["bootstrap_ci"][0]:
                flags.append("[WARN] PF below CI lower bound")
            if pf < 1.0:
                flags.append("[FAIL] PF < 1.0")
        if n > 10 and wr is not None and abs(wr - cfg["win_rate"]) > 15:
            flags.append(f"[WARN] WR drift ({wr:.0f}% vs {cfg['win_rate']:.0f}%)")
        if cfg.get("monitor_regime_note") and n >= 5:
            flags.append(f"[MONITOR] {cfg['monitor_regime_note']}")
        elif cfg.get("monitor_regime_note"):
            flags.append("[INFO] Regime monitor note activates after 5 live trades")

        pf_str = f"{pf:.2f}" if pf is not None else "N/A"
        wr_str = f"{wr:.0f}%" if wr is not None else "N/A"

        print(f"  {ea_name:24s} | {cfg['symbol']:8s} | {n:3d} trades | "
              f"pace {pace_str:>8s} | PF {pf_str:>5s} (exp {cfg['pf_expected']:.2f}) | "
              f"PnL ${pnl:>8.2f} | {cfg['status']}")
        for flag in flags:
            print(f"    {flag}")

        if n >= 5 and cfg.get("monitor_regime_note"):
            print("    [NEXT] Compare current live trades against this regime note before changing presets.")
        elif cfg.get("monitor_regime_note"):
            print("    [NEXT] Build sample first; do not react to regime hints before 5 trades.")

    print()
    print(f"  {'PORTFOLIO TOTAL':24s} | {'':8s} | {total_trades:3d} trades | "
          f"{'':18s} | PnL ${total_pnl:>8.2f}")
    print("=" * 72)

    # Alerts
    if total_trades == 0:
        print("\n  [INFO] No trades recorded yet. Use --add to log trades.")
        print("  Example: python portfolio_monitor.py --add EA_Cobra sell 450")


def show_report(trades: list[dict]):
    """Detailed performance report."""
    show_status(trades)
    print()

    if not trades:
        return

    for ea_name, cfg in PORTFOLIO.items():
        ea_trades = [t for t in trades if t["ea"] == ea_name]
        if not ea_trades:
            continue

        print(f"\n--- {ea_name} ({cfg['symbol']} {cfg['tf']}) ---")
        print(f"{'#':>3s} | {'Time':20s} | {'Dir':5s} | {'Profit':>10s} | Comment")
        print("-" * 60)
        for i, t in enumerate(ea_trades, 1):
            ts = t["timestamp"][:19]
            print(f"{i:3d} | {ts:20s} | {t['direction']:5s} | "
                  f"${t['profit']:>9.2f} | {t.get('comment', '')}")

        profits = [t["profit"] for t in ea_trades]
        print(f"\n  Net: ${sum(profits):.2f} | "
              f"Best: ${max(profits):.2f} | "
              f"Worst: ${min(profits):.2f} | "
              f"Avg: ${sum(profits)/len(profits):.2f}")


def main():
    parser = argparse.ArgumentParser(description="Portfolio Performance Monitor")
    parser.add_argument("--add", nargs=3, metavar=("EA", "DIR", "PROFIT"),
                        help="Log a trade: EA_NAME direction profit")
    parser.add_argument("--import-csv", help="Import MT5/account-history CSV into portfolio_trades.csv")
    parser.add_argument("--import-latest", action="store_true", help="Auto-import the newest matching MT5 trade CSV")
    parser.add_argument("--find-csvs", action="store_true", help="List likely MT5 trade CSVs under default import roots")
    parser.add_argument("--comment", default="", help="Optional trade comment")
    parser.add_argument("--report", action="store_true", help="Detailed report")
    parser.add_argument("--check-export-paths", action="store_true", help="Check whether PaperDeploy export folders/files exist")
    parser.add_argument("--list-eas", action="store_true", help="List portfolio EAs")

    args = parser.parse_args()

    if args.list_eas:
        print("Portfolio EAs:")
        for name, cfg in PORTFOLIO.items():
            print(f"  {name:24s} | {cfg['symbol']:8s} | {cfg['tf']:4s} | "
                  f"Magic {cfg['magic']} | PF {cfg['pf_expected']:.2f} | "
                  f"{cfg['status']}")
        print("\nQuick start:")
        print("  1) python portfolio_monitor.py --check-export-paths")
        print("  2) python portfolio_monitor.py --import-latest")
        print("  3) python portfolio_monitor.py --report")
        print("  Inspect candidates manually:")
        print("  python portfolio_monitor.py --find-csvs")
        print("  Or import a specific file:")
        print("  python portfolio_monitor.py --import-csv <csv_path>")
        print("  Fallback manual log:")
        print("  python portfolio_monitor.py --add EA_Cobra sell 450 --comment \"manual entry\"")
        return

    if args.check_export_paths:
        check_export_paths()
        return

    if args.import_latest:
        candidates = find_candidate_csvs(limit=1)
        if not candidates:
            print("[INFO] No candidate trade CSVs found under default import roots")
            return
        latest = candidates[0]
        imported = import_trades(latest)
        print(f"[OK] Imported {imported} trade(s) from latest candidate: {latest}")
        trades = load_trades()
        show_status(trades)
        return


    if args.add:
        ea, direction, profit = args.add
        if ea not in PORTFOLIO:
            print(f"[ERROR] Unknown EA: {ea}")
            print(f"  Valid EAs: {', '.join(PORTFOLIO.keys())}")
            sys.exit(1)
        save_trade(ea, direction, float(profit), args.comment)
        trades = load_trades()
        show_status(trades)
        return

    if args.find_csvs:
        candidates = find_candidate_csvs()
        if not candidates:
            print("[INFO] No candidate trade CSVs found under default import roots")
            return
        print("Likely MT5 trade CSVs:")
        for path in candidates:
            print(f"  {path}")
        return

    if args.import_csv:
        imported = import_trades(Path(args.import_csv))
        print(f"[OK] Imported {imported} trade(s)")
        trades = load_trades()
        show_status(trades)
        return

    trades = load_trades()
    if args.report:
        show_report(trades)
    else:
        show_status(trades)


if __name__ == "__main__":
    main()
