#!/usr/bin/env python3
"""MT5 indicator parity harness: iATR/iADX/iRSI vs python on identical bars.

capture: compile mql5/ParityDump.mq5 into the portable terminal, launch the
terminal with a [StartUp] script config, collect the CSV the script writes to
MQL5/Files, verify the terminal exited (the script calls TerminalClose).
compare: join the MT5 dump with the lane parquet on server time, PROVE bar
identity (close equality) first, then diff python indicators computed on the
full parquet series against the in-terminal values, excluding a warm-up
window. Emits a hash-bound parity artifact (schema parity_harness.v1).

Symbol/period/periods are arguments — nothing here is strategy- or
lane-specific.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SCHEMA = "parity_harness.v1"
HERE = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def capture(root: Path, symbol: str, period: str, timeout: int) -> Path:
    editor = root / "MetaEditor64.exe"
    terminal = root / "terminal64.exe"
    if not editor.is_file() or not terminal.is_file():
        raise SystemExit(f"portable root incomplete: {root}")

    scripts = root / "MQL5" / "Scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    src = scripts / "ParityDump.mq5"
    shutil.copyfile(HERE / "mql5" / "ParityDump.mq5", src)
    log = scripts / "ParityDump.compile.log"
    # MetaEditor requires the path quoted INSIDE the argument; pass a raw
    # command string so subprocess does not re-quote the whole token.
    cmd = f'"{editor}" /portable /compile:"{src}" /log:"{log}"'
    subprocess.run(cmd, capture_output=True, timeout=180)
    ex5 = src.with_suffix(".ex5")
    if not ex5.is_file():
        detail = ""
        if log.is_file():
            raw = log.read_bytes()
            detail = raw.decode("utf-16", errors="replace") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") \
                else raw.decode("utf-8", errors="replace")
        raise SystemExit(f"compile failed; log: {detail[:2000] or 'no log produced'}")

    csv_out = root / "MQL5" / "Files" / f"parity_dump_{symbol}_PERIOD_{period}.csv"
    csv_out.unlink(missing_ok=True)

    ini = root / "config" / "parity_startup.ini"
    ini.write_text("\n".join([
        "[Charts]", "MaxBars=1000000", "",
        "[StartUp]", "Script=ParityDump", f"Symbol={symbol}", f"Period={period}", "",
    ]), encoding="utf-8")

    # Same embedded-quote requirement as MetaEditor: pass a raw command string.
    proc = subprocess.Popen(f'"{terminal}" /portable /config:"{ini}"')
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None and csv_out.is_file():
            break
        if csv_out.is_file() and proc.poll() is not None:
            break
        time.sleep(2)
    if proc.poll() is None:
        proc.kill()
        proc.wait(30)
    leftover = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-Process terminal64 -ErrorAction SilentlyContinue | Measure-Object).Count"],
        capture_output=True, text=True).stdout.strip()
    if not csv_out.is_file():
        raise SystemExit(f"capture failed: no CSV at {csv_out} (terminal64 leftover={leftover})")
    print(f"CAPTURE ok rows_file={csv_out} terminal64_leftover={leftover}")
    return csv_out


def compare(mt5_csv: Path, bars_parquet: Path, time_col_server: str,
            atr_p: int, adx_p: int, rsi_p: int, warmup: int,
            tol_atr: float, tol_adx: float, tol_rsi: float,
            out: Path) -> int:
    import sys
    sys.path.insert(0, str(HERE))
    from indicators import adx_mt5, adx_wilder, atr_mt5, atr_wilder, rsi_wilder

    mt5 = pd.read_csv(mt5_csv)
    mt5["time_server"] = pd.to_datetime(mt5["time"], unit="s")
    bars = pd.read_parquet(bars_parquet).sort_values(time_col_server).reset_index(drop=True)
    bars["_ts"] = pd.to_datetime(bars[time_col_server])

    # Parity targets are the *_mt5 variants; the classic Wilder variants are
    # also diffed and reported as informational (they are NOT expected to
    # match iATR/iADX — MT5 uses SMA-of-TR and EMA-of-per-bar-DI).
    bars["py_atr"] = atr_mt5(bars, atr_p)
    bars["py_adx"] = adx_mt5(bars, adx_p)
    bars["py_rsi"] = rsi_wilder(bars["close"], rsi_p)
    bars["py_atr_wilder"] = atr_wilder(bars, atr_p)
    bars["py_adx_wilder"] = adx_wilder(bars, adx_p)

    joined = mt5.merge(bars, left_on="time_server", right_on="_ts",
                       suffixes=("_mt5", "_py"))
    if len(joined) < warmup + 100:
        raise SystemExit(f"join too small: {len(joined)} rows")

    close_diff = (joined["close_mt5"] - joined["close_py"]).abs()
    bar_identity = {
        "joined_rows": int(len(joined)),
        "mt5_rows": int(len(mt5)),
        "close_max_abs_diff": float(close_diff.max()),
        "identical_bars": bool(close_diff.max() < 1e-9),
    }

    win = joined.iloc[warmup:]
    stats = {}
    verdicts = {}
    for name, mt5_col, py_col, tol in (
            ("atr", "atr", "py_atr", tol_atr),
            ("adx", "adx", "py_adx", tol_adx),
            ("rsi", "rsi", "py_rsi", tol_rsi)):
        d = (win[mt5_col] - win[py_col]).abs()
        d = d[np.isfinite(d)]
        stats[name] = {
            "n": int(len(d)),
            "max_abs": float(d.max()),
            "mean_abs": float(d.mean()),
            "p99_abs": float(d.quantile(0.99)),
            "n_over_tol": int((d > tol).sum()),
            "tolerance": tol,
        }
        verdicts[name] = "PASS" if stats[name]["max_abs"] <= tol else "FAIL"

    wilder_gap = {}
    for name, mt5_col, py_col in (("atr_wilder_vs_iatr", "atr", "py_atr_wilder"),
                                  ("adx_wilder_vs_iadx", "adx", "py_adx_wilder")):
        d = (win[mt5_col] - win[py_col]).abs()
        d = d[np.isfinite(d)]
        wilder_gap[name] = {"max_abs": float(d.max()), "mean_abs": float(d.mean())}

    artifact = {
        "schema_version": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mt5_csv": str(mt5_csv), "mt5_csv_sha256": sha256_file(mt5_csv),
        "bars_parquet": str(bars_parquet), "bars_sha256": sha256_file(bars_parquet),
        "periods": {"atr": atr_p, "adx": adx_p, "rsi": rsi_p},
        "warmup_rows_excluded": warmup,
        "bar_identity": bar_identity,
        "stats": stats,
        "verdicts": verdicts,
        "wilder_variant_gap_informational": wilder_gap,
        "overall": "PASS" if bar_identity["identical_bars"]
                   and all(v == "PASS" for v in verdicts.values()) else "FAIL",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"bar_identity": bar_identity, "stats": stats,
                      "verdicts": verdicts, "overall": artifact["overall"]}, indent=2))
    print(f"ARTIFACT -> {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("capture", "compare", "run"))
    ap.add_argument("--root", type=Path,
                    default=Path(__file__).resolve().parents[2] / "runtime" / "mt5-portable-fivepercent")
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--period", default="H1")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--mt5-csv", type=Path, default=None)
    ap.add_argument("--bars", type=Path, default=None)
    ap.add_argument("--time-col-server", default="time_server")
    ap.add_argument("--atr-period", type=int, default=14)
    ap.add_argument("--adx-period", type=int, default=14)
    ap.add_argument("--rsi-period", type=int, default=14)
    ap.add_argument("--warmup", type=int, default=500)
    ap.add_argument("--tol-atr", type=float, default=1e-8)
    ap.add_argument("--tol-adx", type=float, default=1e-6)
    ap.add_argument("--tol-rsi", type=float, default=1e-6)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    csv_path = args.mt5_csv
    if args.mode in ("capture", "run"):
        csv_path = capture(args.root, args.symbol, args.period, args.timeout)
    if args.mode in ("compare", "run"):
        if not csv_path or not args.bars:
            raise SystemExit("compare needs --mt5-csv (or capture) and --bars")
        out = args.out or Path.cwd() / f"parity_{args.symbol}_{args.period}.json"
        return compare(csv_path, args.bars, args.time_col_server,
                       args.atr_period, args.adx_period, args.rsi_period,
                       args.warmup, args.tol_atr, args.tol_adx, args.tol_rsi, out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
