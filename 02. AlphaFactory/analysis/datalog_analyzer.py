#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

PX6_SIGNAL_FIELDS = [
    "signal_time", "session", "was_executed", "skip_reason",
    "passed_session", "passed_trend", "passed_vol", "bias",
    "body_ratio", "atr", "regime_state", "symbol",
    "asian_hi", "asian_lo", "asian_pts"
]

PX6_TRADE_FIELDS = [
    "event_time", "tag", "action", "order_type", "volume", "price",
    "sl", "tp", "reason", "retcode", "deal", "order", "symbol",
    "position_id", "entry_price", "initial_sl", "initial_tp", "risk_pts",
    "close_source", "deal_reason", "achievedr", "net_profit", "swap",
    "commission", "is_final_close",
]


def _detect_delimiter(sample: str) -> str:
    if "\t" in sample:
        return "\t"
    if sample.count(";") > sample.count(","):
        return ";"
    return ","


def _open_csv_reader(path: Path, expected_fields: Optional[List[str]] = None):
    # MT5 logs can be utf-8-sig, utf-16, or legacy ANSI; delimiter may be tab/semicolon/comma.
    raw_head = path.read_bytes()[:4]
    if raw_head.startswith(b"\xff\xfe") or raw_head.startswith(b"\xfe\xff"):
        encodings = ("utf-16", "utf-8-sig", "cp1252")
    else:
        encodings = ("utf-8-sig", "cp1252", "utf-16")

    for enc in encodings:
        try:
            f = path.open("r", encoding=enc, errors="replace", newline="")
            sample = f.read(4096)
            f.seek(0)
            delimiter = _detect_delimiter(sample)
            r = csv.DictReader(f, delimiter=delimiter)
            fieldnames = [x.strip() for x in (r.fieldnames or []) if x]
            fieldnames_lc = {x.lower() for x in fieldnames}
            if expected_fields:
                expected_lc = {x.lower() for x in expected_fields}
                match_count = sum(1 for x in fieldnames_lc if x in expected_lc)
                min_matches = max(3, min(5, len(expected_fields) // 3))
                keep_detected_schema = ("blocked_or_fired" in fieldnames_lc or "exit_reason" in fieldnames_lc)
                if match_count < min_matches and not keep_detected_schema:
                    f.seek(0)
                    r = csv.DictReader(f, delimiter=delimiter, fieldnames=expected_fields)
            return f, r
        except UnicodeError:
            continue
    raise UnicodeDecodeError("datalog_analyzer", b"", 0, 1, f"Unable to decode {path}")


def _row_lower(row: dict) -> dict:
    return {(k or "").strip().lower(): v for k, v in row.items()}


def _parse_dt(s: str) -> Optional[datetime]:
    ss = (s or "").strip()
    if not ss:
        return None
    for fmt in ("%Y.%m.%d %H:%M", "%Y.%m.%d %H:%M:%S"):
        try:
            return datetime.strptime(ss, fmt)
        except ValueError:
            pass
    return None


def _safe_float(s: str) -> Optional[float]:
    ss = (s or "").strip().replace(" ", "")
    if not ss:
        return None
    try:
        return float(ss)
    except ValueError:
        return None


def _safe_int(s: str) -> Optional[int]:
    ss = (s or "").strip()
    if not ss:
        return None
    try:
        return int(float(ss))
    except ValueError:
        return None


def _is_truthy(s: str, default: bool = False) -> bool:
    ss = (s or "").strip().lower()
    if not ss:
        return default
    return ss in ("1", "true", "yes", "y")


def _extract_token(path: Path, marker: str) -> str:
    name = path.name
    i = name.find(marker)
    if i < 0:
        return ""
    token = name[i + len(marker):]
    if "." in token:
        token = token.rsplit(".", 1)[0]
    return token


def _load_meta_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-16"))
    except json.JSONDecodeError:
        return {}


def _choose_primary_token(logs_dir: Path) -> str:
    signal_files = sorted(logs_dir.glob("*_Signals_*.csv"))
    trade_files = sorted(logs_dir.glob("*_Trades_*.csv"))
    meta_files = sorted(logs_dir.glob("*_RunMeta_*.json"))

    token_stats: Dict[str, dict] = {}

    def _ensure(token: str) -> dict:
        if token not in token_stats:
            token_stats[token] = {
                "signal_size": 0,
                "trade_size": 0,
                "signal_mtime": 0.0,
                "trade_mtime": 0.0,
                "meta_mtime": 0.0,
                "is_tester": 0,
                "closed_trades": 0,
            }
        return token_stats[token]

    for p in signal_files:
        token = _extract_token(p, "_Signals_")
        if not token:
            continue
        st = _ensure(token)
        st["signal_size"] += p.stat().st_size
        st["signal_mtime"] = max(st["signal_mtime"], p.stat().st_mtime)

    for p in trade_files:
        token = _extract_token(p, "_Trades_")
        if not token:
            continue
        st = _ensure(token)
        st["trade_size"] += p.stat().st_size
        st["trade_mtime"] = max(st["trade_mtime"], p.stat().st_mtime)

    for p in meta_files:
        token = _extract_token(p, "_RunMeta_")
        if not token:
            continue
        st = _ensure(token)
        st["meta_mtime"] = max(st["meta_mtime"], p.stat().st_mtime)
        meta = _load_meta_file(p)
        st["is_tester"] = max(st["is_tester"], int(meta.get("is_tester", 0)))
        st["closed_trades"] = max(st["closed_trades"], int(meta.get("closed_trades", 0)))

    if not token_stats:
        return ""

    best_token, _ = max(
        token_stats.items(),
        key=lambda kv: (
            kv[1]["is_tester"],
            kv[1]["closed_trades"],
            kv[1]["signal_size"] + kv[1]["trade_size"],
            max(kv[1]["meta_mtime"], kv[1]["signal_mtime"], kv[1]["trade_mtime"]),
            kv[0],
        ),
    )
    return best_token


def _percentile(xs: List[float], p: float) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    if p <= 0:
        return ys[0]
    if p >= 100:
        return ys[-1]
    k = (len(ys) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ys) - 1)
    if f == c:
        return ys[f]
    d0 = ys[f] * (c - k)
    d1 = ys[c] * (k - f)
    return d0 + d1


@dataclass
class SignalAgg:
    total: int = 0
    executed: int = 0
    skipped: int = 0


def analyze_signals(signal_files: List[Path]) -> dict:
    skip_reason: Dict[str, int] = {}
    gate_fail: Dict[str, int] = {}
    by_session: Dict[str, SignalAgg] = {}
    by_hour: Dict[int, SignalAgg] = {}

    gate_cols = ["passedsession", "passedtrend", "passedvolatility", "passed_session", "passed_trend", "passed_vol"]

    total = executed = skipped = 0

    for p in signal_files:
        f, r = _open_csv_reader(p, expected_fields=PX6_SIGNAL_FIELDS)
        with f:
            row_gate_cols = gate_cols
            if r.fieldnames:
                lowered_fields = {(x or "").strip().lower() for x in r.fieldnames}
                if "blocked_or_fired" in lowered_fields:
                    row_gate_cols = []
                else:
                    row_gate_cols = [c for c in gate_cols if c in lowered_fields]
            for row in r:
                row_l = _row_lower(row)
                total += 1
                if "blocked_or_fired" in row_l:
                    was_exe = ((row_l.get("blocked_or_fired", "") or "").strip().lower() == "fired")
                    sess = (row_l.get("session_bucket") or "").strip() or "(EMPTY)"
                    dt = _parse_dt(row_l.get("utc_ts", "") or row_l.get("server_ts", ""))
                else:
                    was_exe = ((row_l.get("wasexecuted") or row_l.get("was_executed") or "0").strip() == "1")
                    sess = (row_l.get("session") or "").strip() or "(EMPTY)"
                    dt = _parse_dt(row_l.get("signaltime", "") or row_l.get("signal_time", ""))
                if was_exe:
                    executed += 1
                else:
                    skipped += 1

                hour = dt.hour if dt else None

                if sess not in by_session:
                    by_session[sess] = SignalAgg()
                by_session[sess].total += 1
                if was_exe:
                    by_session[sess].executed += 1
                else:
                    by_session[sess].skipped += 1

                if hour is not None:
                    if hour not in by_hour:
                        by_hour[hour] = SignalAgg()
                    by_hour[hour].total += 1
                    if was_exe:
                        by_hour[hour].executed += 1
                    else:
                        by_hour[hour].skipped += 1

                if not was_exe:
                    sr = (row_l.get("block_reason") or row_l.get("skipreason") or row_l.get("skip_reason") or "").strip().strip('"')
                    if not sr:
                        sr = "(EMPTY)"
                    skip_reason[sr] = skip_reason.get(sr, 0) + 1

                    for gc in row_gate_cols:
                        v = (row_l.get(gc) or "").strip()
                        if v == "0":
                            gate_fail[gc] = gate_fail.get(gc, 0) + 1

    # sort helpers
    skip_reason_sorted = sorted(skip_reason.items(), key=lambda x: (-x[1], x[0]))
    gate_fail_sorted = sorted(gate_fail.items(), key=lambda x: (-x[1], x[0]))

    return {
        "files": [str(x) for x in signal_files],
        "total": total,
        "executed": executed,
        "skipped": skipped,
        "skip_reason": skip_reason_sorted,
        "gate_fail": gate_fail_sorted,
        "by_session": {
            k: {"total": v.total, "executed": v.executed, "skipped": v.skipped}
            for k, v in sorted(by_session.items(), key=lambda x: x[0])
        },
        "by_hour": {
            str(h): {"total": by_hour[h].total, "executed": by_hour[h].executed, "skipped": by_hour[h].skipped}
            for h in sorted(by_hour.keys())
        },
    }


def analyze_trades(trade_files: List[Path]) -> dict:
    achieved_r: List[float] = []
    by_close_reason: Dict[str, List[float]] = {}
    by_close_source: Dict[str, List[float]] = {}
    action_counts: Dict[str, int] = {}

    total = 0
    for p in trade_files:
        f, r = _open_csv_reader(p, expected_fields=PX6_TRADE_FIELDS)
        with f:
            fieldnames_lc = {(x or "").strip().lower() for x in (r.fieldnames or [])}
            is_xsp_schema = "exit_reason" in fieldnames_lc
            is_px6_event_schema = "action" in fieldnames_lc and "event_time" in fieldnames_lc
            for row in r:
                row_l = _row_lower(row)
                if is_xsp_schema and not _is_truthy(row_l.get("is_final_close", "1"), default=True):
                    continue
                if is_px6_event_schema:
                    action = (row_l.get("action") or "").strip().upper()
                    action_counts[action or "(EMPTY)"] = action_counts.get(action or "(EMPTY)", 0) + 1
                    if action not in ("CLOSE", "CLOSE_PARTIAL"):
                        continue
                    if not _is_truthy(row_l.get("is_final_close", "1"), default=(action == "CLOSE")):
                        continue
                total += 1
                ar = _safe_float(
                    row_l.get("realized_r" if is_xsp_schema else "achievedr", "")
                    or row_l.get("achieved_r", "")
                )
                if ar is not None:
                    achieved_r.append(ar)

                if is_xsp_schema:
                    cr = (row_l.get("exit_reason") or "").strip().strip('"')
                elif is_px6_event_schema:
                    cr = (row_l.get("reason") or row_l.get("deal_reason") or "").strip().strip('"')
                else:
                    cr = (row_l.get("closereason") or "").strip().strip('"')
                if not cr:
                    cr = "(EMPTY)"
                if cr not in by_close_reason:
                    by_close_reason[cr] = []
                if ar is not None:
                    by_close_reason[cr].append(ar)

                close_source = (
                    (row_l.get("close_source") or "").strip().strip('"')
                    if is_px6_event_schema
                    else ""
                )
                if not close_source:
                    close_source = "(EMPTY)"
                if close_source not in by_close_source:
                    by_close_source[close_source] = []
                if ar is not None:
                    by_close_source[close_source].append(ar)

    def _avg(xs: List[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    summary = {
        "files": [str(x) for x in trade_files],
        "total": total,
        "achieved_r": {
            "n": len(achieved_r),
            "mean": round(_avg(achieved_r), 4),
            "p10": round(_percentile(achieved_r, 10), 4),
            "p50": round(_percentile(achieved_r, 50), 4),
            "p90": round(_percentile(achieved_r, 90), 4),
            "pct_ge_2": round((sum(1 for x in achieved_r if x >= 2.0) / len(achieved_r) * 100.0) if achieved_r else 0.0, 2),
            "pct_ge_3": round((sum(1 for x in achieved_r if x >= 3.0) / len(achieved_r) * 100.0) if achieved_r else 0.0, 2),
        },
        "action_counts": [
            {"action": action, "n": n} for action, n in sorted(action_counts.items(), key=lambda x: (-x[1], x[0]))
        ],
        "by_close_reason": [],
        "by_close_source": [],
    }

    rows = []
    for cr, xs in by_close_reason.items():
        rows.append({
            "close_reason": cr,
            "n": len(xs),
            "mean_achieved_r": round(_avg(xs), 4),
            "p50_achieved_r": round(_percentile(xs, 50), 4),
        })
    rows.sort(key=lambda x: (-x["n"], x["close_reason"]))
    summary["by_close_reason"] = rows

    rows = []
    for close_source, xs in by_close_source.items():
        rows.append({
            "close_source": close_source,
            "n": len(xs),
            "mean_achieved_r": round(_avg(xs), 4),
            "p50_achieved_r": round(_percentile(xs, 50), 4),
        })
    rows.sort(key=lambda x: (-x["n"], x["close_source"]))
    summary["by_close_source"] = rows

    return summary


def write_csv_kv(path: Path, header: Tuple[str, str], rows: Iterable[Tuple[str, int]]):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(header))
        for k, v in rows:
            w.writerow([k, v])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs-dir", required=True, help="Directory containing *_Signals_*.csv and *_Trades_*.csv")
    ap.add_argument("--out", default="", help="Output directory (default: <logs-dir>/../datalog)")
    args = ap.parse_args()

    logs_dir = Path(args.logs_dir)
    if not logs_dir.exists():
        raise SystemExit(f"logs-dir not found: {logs_dir}")

    out_dir = Path(args.out) if args.out else (logs_dir.parent / "datalog")
    out_dir.mkdir(parents=True, exist_ok=True)

    signal_files = sorted(logs_dir.glob("*_Signals_*.csv"))
    trade_files = sorted(logs_dir.glob("*_Trades_*.csv"))

    # Prefer a single coherent tester token to avoid cross-run/live contamination in shared Common\Files.
    primary_token = _choose_primary_token(logs_dir)
    if primary_token:
        same_signal = [p for p in signal_files if _extract_token(p, "_Signals_") == primary_token]
        same_trade = [p for p in trade_files if _extract_token(p, "_Trades_") == primary_token]
        if same_signal:
            signal_files = sorted(same_signal)
        if same_trade:
            trade_files = sorted(same_trade)

    signals = analyze_signals(signal_files) if signal_files else {"files": [], "total": 0, "executed": 0, "skipped": 0}
    trades = analyze_trades(trade_files) if trade_files else {"files": [], "total": 0, "achieved_r": {"n": 0}}

    # Write artifacts
    (out_dir / "signals_summary.json").write_text(json.dumps(signals, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "trades_summary.json").write_text(json.dumps(trades, indent=2, ensure_ascii=False), encoding="utf-8")

    if signals.get("skip_reason"):
        write_csv_kv(out_dir / "skip_reason.csv", ("skip_reason", "count"), signals["skip_reason"])
    if signals.get("gate_fail"):
        write_csv_kv(out_dir / "gate_fail.csv", ("gate", "count"), signals["gate_fail"])

    print(f"[datalog_analyzer] logs={logs_dir} out={out_dir}")
    print(f"[datalog_analyzer] signals: total={signals.get('total', 0)} executed={signals.get('executed', 0)} skipped={signals.get('skipped', 0)}")
    print(f"[datalog_analyzer] trades: total={trades.get('total', 0)} achievedR_n={trades.get('achieved_r', {}).get('n', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
