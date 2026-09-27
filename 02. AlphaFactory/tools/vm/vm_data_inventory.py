"""Data inventory for the AlphaFactory VM isolate on MetaQuotes-Demo.

Attaches MetaTrader5 to the portable isolate via tools.factory_paths
(same contract alpha.ps1 enforces), then probes each symbol:
first/last M1 bar, real-tick availability (one sample day per year),
symbol spec, and on-disk history footprint under Bases/.

Measurement method (v2): copy_rates_from only sees history the terminal
has already downloaded, so a single shallow call under-reports depth
(repo precedent: 16 months reported where 16 years existed). For each
symbol we run a sync-walk: repeated copy_rates_from(M1, 2000-01-01)
requests force the terminal to pull history from the server until the
earliest returned bar converges. EURUSD/XAUUSD get a deep walk
(max_iter=25, settle=4); the rest get a shallow one (max_iter=8,
settle=2). Ticks are probed with one capped day per year (200 ticks) —
existence probe only, never a bulk pull.

Writes CSV + JSON to --out-dir. Prints nothing sensitive.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS_DIR.parent))
from tools.factory_paths import factory_install_root, mt5_initialize_kwargs  # noqa: E402

SYMBOLS = [
    "EURUSD", "XAUUSD",
    "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF",
    "EURJPY", "GBPJPY", "EURGBP", "AUDJPY",
]

DEEP_SYMBOLS = {"EURUSD", "XAUUSD"}
M1_SYNC_FLOOR = datetime(2000, 1, 1)

# mt5.initialize(path=...) LAUNCHES the isolate terminal when it is not
# running, and mt5.shutdown() only detaches -- a bare orphan terminal64
# would linger (holding the demo session and MCP port 22346). Same pattern
# as analysis/trade_chart_capture.py: snapshot isolate PIDs before attach,
# reap the delta on exit.
_LAUNCHED_TERMINAL_PIDS: list[int] = []


def _isolate_terminal_pids(isolate_exe: str) -> list[int]:
    """PIDs of terminal64.exe whose ExecutablePath is exactly the isolate exe."""
    try:
        out = subprocess.check_output(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" "
                "| Select-Object ProcessId,ExecutablePath "
                "| ConvertTo-Json -Compress",
            ],
            timeout=15,
            text=True,
        )
    except Exception:
        return []
    try:
        rows = json.loads(out) if out.strip() else []
    except json.JSONDecodeError:
        return []
    if isinstance(rows, dict):
        rows = [rows]
    norm = str(Path(isolate_exe)).lower()
    return [
        int(r["ProcessId"])
        for r in rows
        if isinstance(r, dict)
        and str(r.get("ExecutablePath", "")).lower() == norm
    ]


def _reap_launched_terminals() -> None:
    for pid in _LAUNCHED_TERMINAL_PIDS:
        try:
            subprocess.check_call(
                ["powershell", "-NoProfile", "-Command",
                 f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
                timeout=15,
            )
        except Exception:
            pass
    _LAUNCHED_TERMINAL_PIDS.clear()


def m1_sync_walk(mt5, symbol: str, max_iter: int, settle: int, sleep_s: float = 2.5):
    """Force-download M1 history: repeat copy_rates_from(M1_SYNC_FLOOR, 5)
    until the earliest returned bar stops moving earlier. Returns
    (earliest_iso | None, iters, converged)."""
    earliest = None
    stable = 0
    iters = 0
    for i in range(max_iter):
        iters = i + 1
        try:
            bars = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, M1_SYNC_FLOOR, 5)
        except Exception:
            bars = None
        if bars is not None and len(bars):
            t = int(bars[0]["time"])
            if earliest is None or t < earliest:
                earliest = t
                stable = 0
            else:
                stable += 1
        if stable >= settle:
            break
        time.sleep(sleep_s)
    iso = (
        datetime.fromtimestamp(earliest, tz=timezone.utc).isoformat()
        if earliest is not None
        else None
    )
    return iso, iters, stable >= settle


def dir_size_bytes(path: Path) -> int:
    if not path.is_dir():
        return 0
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def symbol_disk_bytes(isolate: Path, symbol: str) -> int:
    bases = isolate / "Bases"
    total = 0
    if bases.is_dir():
        for server_dir in bases.iterdir():
            if not server_dir.is_dir():
                continue
            for sub in ("history", "ticks", "cache"):
                d = server_dir / sub / symbol
                total += dir_size_bytes(d)
                # history files may live at <server>/<sub>/<symbol>.hcc or a dir
                f = server_dir / sub / (symbol + ".hcc")
                if f.is_file():
                    total += f.stat().st_size
    return total


def probe_symbol(mt5, isolate: Path, symbol: str) -> dict:
    row = {
        "symbol": symbol,
        "available": False,
        "digits": None,
        "point": None,
        "contract_size": None,
        "swap_long": None,
        "swap_short": None,
        "m1_first": None,
        "m1_last": None,
        "m1_probe_method": None,
        "m1_probe_iters": 0,
        "m1_probe_converged": False,
        "tick_years_with_data": [],
        "disk_bytes": symbol_disk_bytes(isolate, symbol),
        "error": None,
    }
    info = mt5.symbol_info(symbol)
    if info is None:
        row["error"] = f"symbol_info None: {mt5.last_error()}"
        return row
    row["available"] = True
    row["digits"] = info.digits
    row["point"] = info.point
    row["contract_size"] = info.trade_contract_size
    row["swap_long"] = info.swap_long
    row["swap_short"] = info.swap_short

    if not info.visible:
        mt5.symbol_select(symbol, True)

    # first M1 via sync-walk (see module docstring): deep for the two
    # reference symbols, shallow for the rest.
    if symbol in DEEP_SYMBOLS:
        m1_first, iters, converged = m1_sync_walk(mt5, symbol, max_iter=25, settle=4)
        row["m1_probe_method"] = "deep_sync_walk"
    else:
        m1_first, iters, converged = m1_sync_walk(mt5, symbol, max_iter=8, settle=2, sleep_s=2.0)
        row["m1_probe_method"] = "shallow_sync_walk"
    row["m1_first"] = m1_first
    row["m1_probe_iters"] = iters
    row["m1_probe_converged"] = converged
    last = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 5)
    if last is not None and len(last):
        row["m1_last"] = datetime.fromtimestamp(int(last[-1]["time"]), tz=timezone.utc).isoformat()

    # tick probe: one sample day (Jun 15) per year from first M1 to now;
    # copy_ticks_from with a small cap — existence probe, not a bulk pull
    first_year = 2000
    if row["m1_first"]:
        first_year = max(2000, int(row["m1_first"][:4]))
    now_year = datetime.now(tz=timezone.utc).year
    for year in range(first_year, now_year + 1):
        start = datetime(year, 6, 15, tzinfo=timezone.utc)
        try:
            ticks = mt5.copy_ticks_from(symbol, start, 200, mt5.COPY_TICKS_ALL)
            if ticks is not None and len(ticks) > 0:
                row["tick_years_with_data"].append(year)
        except Exception:
            pass
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    import MetaTrader5 as mt5

    isolate = factory_install_root()
    kwargs = mt5_initialize_kwargs()
    isolate_exe = str(kwargs.get("path") or (isolate / "terminal64.exe"))
    before_pids = set(_isolate_terminal_pids(isolate_exe))
    ok = mt5.initialize(**kwargs)
    attach_note = "factory_paths.mt5_initialize_kwargs"
    if not ok:
        # Backup per playbook: one explicit retry with path+portable.
        ok = mt5.initialize(path=isolate_exe, portable=True, timeout=60000)
        attach_note = "explicit path+portable retry"
    _LAUNCHED_TERMINAL_PIDS.extend(
        pid for pid in _isolate_terminal_pids(isolate_exe) if pid not in before_pids
    )
    if not ok:
        payload = {
            "schema_version": "alphafactory_vm_data_inventory.v1",
            "attached": False,
            "attach_error": str(mt5.last_error()),
            "attach_method": attach_note,
        }
        (out_dir / "inventory.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload))
        return 2

    try:
        term = mt5.terminal_info()
        build = term.build if term else None
        account = mt5.account_info()
        server = account.server if account else None

        rows = [probe_symbol(mt5, isolate, s) for s in SYMBOLS]

        disk_free_gb = None
        try:
            usage = os.statvfs(str(isolate)) if hasattr(os, "statvfs") else None
        except OSError:
            usage = None
        try:
            import shutil
            usage = shutil.disk_usage(str(isolate))
            disk_free_gb = round(usage.free / (1024 ** 3), 1)
        except Exception:
            pass

        lab_dir = isolate.parents[1] / "lab"  # 02. AlphaFactory/lab
        gap = {
            "lab_dir": str(lab_dir),
            "lab_present_on_main_2026_09_05": lab_dir.is_dir(),
            "note": (
                "02. AlphaFactory/lab khong ton tai tren main ae7bec2f (05/09); "
                "gap = symbol nao khong co history/tick tren MetaQuotes-Demo cua VM."
            ),
            "missing_symbols": [r["symbol"] for r in rows if not r["available"]],
            "symbols_without_m1": [r["symbol"] for r in rows if r["available"] and not r["m1_first"]],
            "symbols_without_real_ticks": [
                r["symbol"] for r in rows if r["available"] and not r["tick_years_with_data"]
            ],
        }

        payload = {
            "schema_version": "alphafactory_vm_data_inventory.v2",
            "measurement_method": (
                "m1_first via sync-walk: repeated copy_rates_from(M1, 2000-01-01) "
                "forces terminal download until earliest bar converges "
                "(deep: EURUSD/XAUUSD 25x/settle4; shallow: others 8x/settle2); "
                "ticks probed one capped day/year (max 200 ticks)"
            ),
            "attached": True,
            "attach_method": attach_note,
            "terminal_build": build,
            "server": server,
            "plane": "devin-vm-mqdemo",
            "checked_at_utc": datetime.now(tz=timezone.utc).isoformat(),
            "vm_disk_free_gb": disk_free_gb,
            "symbols": rows,
            "gap": gap,
        }
        (out_dir / "inventory.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

        with (out_dir / "inventory.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([
                "symbol", "available", "digits", "point", "contract_size",
                "swap_long", "swap_short", "m1_first", "m1_last",
                "m1_probe_method", "m1_probe_iters", "m1_probe_converged",
                "tick_years_with_data", "disk_bytes", "error",
            ])
            for r in rows:
                w.writerow([
                    r["symbol"], r["available"], r["digits"], r["point"],
                    r["contract_size"], r["swap_long"], r["swap_short"],
                    r["m1_first"], r["m1_last"],
                    r["m1_probe_method"], r["m1_probe_iters"], r["m1_probe_converged"],
                    "|".join(str(y) for y in r["tick_years_with_data"]),
                    r["disk_bytes"], r["error"],
                ])

        print(json.dumps(payload))
        return 0 if all(r["available"] for r in rows) else 1
    finally:
        mt5.shutdown()
        _reap_launched_terminals()


if __name__ == "__main__":
    sys.exit(main())
