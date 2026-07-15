#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def _read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _safe_float(v, default=0.0):
    try:
        return float((v or "").strip())
    except Exception:
        return default


def _safe_int(v, default=0):
    try:
        return int(float((v or "").strip()))
    except Exception:
        return default


def _median(xs):
    return round(statistics.median(xs), 4) if xs else 0.0


def _mean(xs):
    return round(sum(xs) / len(xs), 4) if xs else 0.0


def _find_single(logs_dir: Path, pattern: str):
    files = sorted(logs_dir.glob(pattern))
    return files[0] if files else None


def analyze_signals(signal_rows):
    by_engine = defaultdict(lambda: {"total": 0, "fired": 0, "blocked": 0})
    fired_by_hour = Counter()
    blocked_by_reason = Counter()

    for row in signal_rows:
        engine = row.get("engine_name", "") or "(EMPTY)"
        status = (row.get("blocked_or_fired", "") or "").strip().lower()
        hour = row.get("hour_server", "") or "?"
        reason = row.get("block_reason", "") or "(EMPTY)"

        by_engine[engine]["total"] += 1
        if status == "fired":
            by_engine[engine]["fired"] += 1
            fired_by_hour[hour] += 1
        else:
            by_engine[engine]["blocked"] += 1
            blocked_by_reason[reason] += 1

    return {
        "by_engine": dict(sorted(by_engine.items())),
        "fired_by_hour_server": dict(sorted(fired_by_hour.items(), key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 999)),
        "blocked_by_reason": dict(sorted(blocked_by_reason.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def analyze_trades(trade_rows):
    hold_buckets = {
        "0_30": [],
        "31_60": [],
        "61_90": [],
        "91_120": [],
        "121_180": [],
        "gt_180": [],
    }
    timeout_by_hour = defaultdict(list)
    timeout_by_session = defaultdict(list)
    by_close_reason = defaultdict(list)
    overnight = []

    for row in trade_rows:
        achieved_r = _safe_float(row.get("achieved_r"))
        hold = _safe_float(row.get("hold_minutes"))
        close_reason = row.get("close_reason_class") or row.get("exit_reason") or "(EMPTY)"
        by_close_reason[close_reason].append(achieved_r)

        entry_ts = row.get("entry_server_ts", "") or ""
        entry_hour = entry_ts[11:13] if len(entry_ts) >= 13 else "?"
        session = row.get("session_tag", "") or "(EMPTY)"

        if hold <= 30:
            hold_buckets["0_30"].append(achieved_r)
        elif hold <= 60:
            hold_buckets["31_60"].append(achieved_r)
        elif hold <= 90:
            hold_buckets["61_90"].append(achieved_r)
        elif hold <= 120:
            hold_buckets["91_120"].append(achieved_r)
        elif hold <= 180:
            hold_buckets["121_180"].append(achieved_r)
        else:
            hold_buckets["gt_180"].append(achieved_r)

        if close_reason == "timeout":
            timeout_by_hour[entry_hour].append(achieved_r)
            timeout_by_session[session].append(achieved_r)

        if _safe_int(row.get("overnight_flag")) == 1:
            overnight.append({
                "entry_server_ts": row.get("entry_server_ts"),
                "exit_server_ts": row.get("exit_server_ts"),
                "engine_name": row.get("engine_name"),
                "session_tag": row.get("session_tag"),
                "entry_reason": row.get("entry_reason"),
                "exit_reason": row.get("exit_reason"),
                "hold_minutes": hold,
                "achieved_r": achieved_r,
                "pnl_net": _safe_float(row.get("pnl_net")),
            })

    close_reason_summary = []
    for reason, xs in by_close_reason.items():
        close_reason_summary.append({
            "close_reason": reason,
            "n": len(xs),
            "mean_achieved_r": _mean(xs),
            "median_achieved_r": _median(xs),
        })
    close_reason_summary.sort(key=lambda x: (-x["n"], x["close_reason"]))

    timeout_hour_summary = []
    for hour, xs in timeout_by_hour.items():
        timeout_hour_summary.append({
            "entry_hour_server": hour,
            "n_timeout": len(xs),
            "mean_achieved_r": _mean(xs),
            "median_achieved_r": _median(xs),
        })
    timeout_hour_summary.sort(key=lambda x: (-x["n_timeout"], x["entry_hour_server"]))

    timeout_session_summary = []
    for session, xs in timeout_by_session.items():
        timeout_session_summary.append({
            "session_tag": session,
            "n_timeout": len(xs),
            "mean_achieved_r": _mean(xs),
            "median_achieved_r": _median(xs),
        })
    timeout_session_summary.sort(key=lambda x: (-x["n_timeout"], x["session_tag"]))

    hold_bucket_summary = {}
    for bucket, xs in hold_buckets.items():
        hold_bucket_summary[bucket] = {
            "n": len(xs),
            "mean_achieved_r": _mean(xs),
            "median_achieved_r": _median(xs),
        }

    return {
        "close_reason_summary": close_reason_summary,
        "timeout_by_entry_hour_server": timeout_hour_summary,
        "timeout_by_session": timeout_session_summary,
        "hold_bucket_summary": hold_bucket_summary,
        "overnight_offenders": overnight,
    }


def analyze_engine_audit(audit_rows):
    by_engine = defaultdict(list)
    for row in audit_rows:
        by_engine[row.get("engine_name", "")].append({
            "audit_stage": row.get("audit_stage", ""),
            "reason": row.get("reason", ""),
            "count": _safe_int(row.get("count")),
        })

    for engine in by_engine:
        by_engine[engine].sort(key=lambda x: (-x["count"], x["audit_stage"], x["reason"]))

    return dict(sorted(by_engine.items()))


def build_markdown(run_id, signals, trades, audit):
    lines = [
        f"# XSP Forensics — {run_id}",
        "",
        "## Signal surface",
    ]
    for engine, row in signals["by_engine"].items():
        lines.append(f"- `{engine}`: total={row['total']}, fired={row['fired']}, blocked={row['blocked']}")

    lines += ["", "## Timeout pain map"]
    for row in trades["timeout_by_entry_hour_server"][:8]:
        lines.append(
            f"- hour {row['entry_hour_server']}: timeout_n={row['n_timeout']}, meanR={row['mean_achieved_r']}, medianR={row['median_achieved_r']}"
        )

    lines += ["", "## Close-reason summary"]
    for row in trades["close_reason_summary"]:
        lines.append(
            f"- {row['close_reason']}: n={row['n']}, meanR={row['mean_achieved_r']}, medianR={row['median_achieved_r']}"
        )

    lines += ["", "## Engine veto map"]
    if not audit:
        lines.append("- Engine audit artifact chưa có cho run này.")
    else:
        for engine, rows in audit.items():
            lines.append(f"### {engine}")
            for row in rows[:12]:
                lines.append(f"- [{row['audit_stage']}] {row['reason']}: {row['count']}")
            lines.append("")

    if trades["overnight_offenders"]:
        lines += ["## Overnight offenders"]
        for row in trades["overnight_offenders"]:
            lines.append(
                f"- {row['entry_server_ts']} -> {row['exit_server_ts']} | {row['engine_name']} | hold={row['hold_minutes']}m | R={row['achieved_r']}"
            )

    return "\n".join(lines).strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    logs_dir = run_dir / "analysis" / "logs"
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    signal_file = _find_single(logs_dir, "*_Signals_*.csv")
    trade_file = _find_single(logs_dir, "*_Trades_*.csv")
    audit_file = _find_single(logs_dir, "*_EngineAudit_*.csv")

    if not signal_file or not trade_file:
        raise SystemExit(f"Missing signal/trade logs in {logs_dir}")

    signal_rows = _read_csv(signal_file)
    trade_rows = _read_csv(trade_file)
    audit_rows = _read_csv(audit_file) if audit_file else []

    signals = analyze_signals(signal_rows)
    trades = analyze_trades(trade_rows)
    audit = analyze_engine_audit(audit_rows)

    bundle = {
        "run_dir": str(run_dir),
        "signal_file": str(signal_file),
        "trade_file": str(trade_file),
        "audit_file": str(audit_file) if audit_file else "",
        "signals": signals,
        "trades": trades,
        "engine_audit": audit,
    }

    (reports_dir / "xsp_forensics.json").write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    (reports_dir / "xsp_forensics.md").write_text(build_markdown(run_dir.name, signals, trades, audit), encoding="utf-8")
    print(f"[xsp_forensics] wrote {reports_dir / 'xsp_forensics.json'}")
    print(f"[xsp_forensics] wrote {reports_dir / 'xsp_forensics.md'}")


if __name__ == "__main__":
    main()
