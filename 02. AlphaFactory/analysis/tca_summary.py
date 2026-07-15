#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PX6_EXEC_FIELDS = [
    "event_time", "phase", "state", "tag", "order_type", "volume",
    "request_price", "fill_price", "sl", "tp", "reason", "retcode",
    "deal", "order", "slippage_pts", "symbol",
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
            reader = csv.DictReader(f, delimiter=delimiter)
            fieldnames = [x.strip() for x in (reader.fieldnames or []) if x]
            fieldnames_lc = {x.lower() for x in fieldnames}
            if expected_fields:
                expected_lc = {x.lower() for x in expected_fields}
                match_count = sum(1 for x in fieldnames_lc if x in expected_lc)
                min_matches = max(3, min(5, len(expected_fields) // 3))
                if match_count < min_matches:
                    f.seek(0)
                    reader = csv.DictReader(f, delimiter=delimiter, fieldnames=expected_fields)
            return f, reader
        except UnicodeError:
            continue
    raise UnicodeDecodeError("tca_summary", b"", 0, 1, f"Unable to decode {path}")


def _row_lower(row: dict) -> dict:
    return {(k or "").strip().lower(): v for k, v in row.items()}


def _safe_float(s: str) -> Optional[float]:
    ss = (s or "").strip().replace(" ", "")
    if not ss:
        return None
    try:
        return float(ss)
    except ValueError:
        return None


def _is_truthy(s: str, default: bool = False) -> bool:
    ss = (s or "").strip().lower()
    if not ss:
        return default
    return ss in ("1", "true", "yes", "y")


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


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


def _extract_token(name: str, marker: str) -> str:
    i = name.find(marker)
    if i < 0:
        return ""
    token = name[i + len(marker):]
    if "." in token:
        token = token.rsplit(".", 1)[0]
    return token


def _pick_latest(files: List[Path]) -> Optional[Path]:
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def _load_meta_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-16"))
    except json.JSONDecodeError:
        return {}


def _choose_best_token(exec_files: List[Path], trade_files: List[Path], meta_files: List[Path]) -> str:
    token_stats: Dict[str, dict] = {}

    def _ensure(token: str) -> dict:
        if token not in token_stats:
            token_stats[token] = {
                "exec_size": 0,
                "trade_size": 0,
                "exec_mtime": 0.0,
                "trade_mtime": 0.0,
                "meta_mtime": 0.0,
                "is_tester": 0,
                "closed_trades": 0,
            }
        return token_stats[token]

    for p in exec_files:
        token = _extract_token(p.name, "_PX6_Exec_")
        if not token:
            continue
        st = _ensure(token)
        st["exec_size"] += p.stat().st_size
        st["exec_mtime"] = max(st["exec_mtime"], p.stat().st_mtime)

    for p in trade_files:
        token = _extract_token(p.name, "_PX6_Trades_")
        if not token:
            continue
        st = _ensure(token)
        st["trade_size"] += p.stat().st_size
        st["trade_mtime"] = max(st["trade_mtime"], p.stat().st_mtime)

    for p in meta_files:
        token = _extract_token(p.name, "_RunMeta_")
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
            kv[1]["trade_size"] + kv[1]["exec_size"],
            max(kv[1]["meta_mtime"], kv[1]["trade_mtime"], kv[1]["exec_mtime"]),
            kv[0],
        ),
    )
    return best_token


def select_run_files(logs_dir: Path) -> Tuple[str, Optional[Path], Optional[Path], Optional[Path]]:
    exec_files = sorted(logs_dir.glob("*_PX6_Exec_*.csv"))
    trade_files = sorted(logs_dir.glob("*_PX6_Trades_*.csv"))
    meta_files = sorted(logs_dir.glob("*_RunMeta_*.json"))

    token = _choose_best_token(exec_files, trade_files, meta_files)

    def _match(files: List[Path], marker: str) -> Optional[Path]:
        if not files:
            return None
        if token:
            same = [p for p in files if _extract_token(p.name, marker) == token]
            if same:
                return _pick_latest(same)
        return _pick_latest(files)

    return (
        token,
        _match(exec_files, "_PX6_Exec_"),
        _match(trade_files, "_PX6_Trades_"),
        _match(meta_files, "_RunMeta_"),
    )


def analyze_exec(exec_file: Optional[Path]) -> dict:
    if not exec_file or not exec_file.exists():
        return {"file": "", "rows": 0, "phase_counts": [], "retcodes": [], "reasons": [], "slippage_pts": {}}

    phase_counts: Dict[str, int] = {}
    retcodes: Dict[str, int] = {}
    reasons: Dict[str, int] = {}
    slippage: List[float] = []
    rows = 0

    f, r = _open_csv_reader(exec_file, expected_fields=PX6_EXEC_FIELDS)
    with f:
        for row in r:
            row_l = _row_lower(row)
            rows += 1

            phase = (row_l.get("phase") or "").strip().upper() or "(EMPTY)"
            reason = (row_l.get("reason") or "").strip() or "(EMPTY)"
            retcode = (row_l.get("retcode") or "").strip() or "(EMPTY)"

            phase_counts[phase] = phase_counts.get(phase, 0) + 1
            reasons[reason] = reasons.get(reason, 0) + 1
            retcodes[retcode] = retcodes.get(retcode, 0) + 1

            slip = _safe_float(row_l.get("slippage_pts", ""))
            if slip is not None:
                slippage.append(slip)

    return {
        "file": str(exec_file),
        "rows": rows,
        "phase_counts": [{"phase": k, "n": v} for k, v in sorted(phase_counts.items(), key=lambda x: (-x[1], x[0]))],
        "retcodes": [{"retcode": k, "n": v} for k, v in sorted(retcodes.items(), key=lambda x: (-x[1], x[0]))],
        "reasons": [{"reason": k, "n": v} for k, v in sorted(reasons.items(), key=lambda x: (-x[1], x[0]))],
        "slippage_pts": {
            "n": len(slippage),
            "mean": round(_mean(slippage), 4),
            "abs_mean": round(_mean([abs(x) for x in slippage]), 4) if slippage else 0.0,
            "p50": round(_percentile(slippage, 50), 4),
            "p90_abs": round(_percentile([abs(x) for x in slippage], 90), 4) if slippage else 0.0,
            "max_abs": round(max((abs(x) for x in slippage), default=0.0), 4),
        },
    }


def analyze_trades(trade_file: Optional[Path]) -> dict:
    if not trade_file or not trade_file.exists():
        return {
            "file": "",
            "rows": 0,
            "final_closes": 0,
            "partial_close_rows": 0,
            "action_counts": [],
            "close_sources": [],
            "close_reasons": [],
            "achieved_r": {},
            "net_profit": {},
        }

    action_counts: Dict[str, int] = {}
    close_sources: Dict[str, int] = {}
    close_reasons: Dict[str, int] = {}
    achieved_r: List[float] = []
    net_profit: List[float] = []
    rows = 0
    final_closes = 0
    partial_close_rows = 0

    f, r = _open_csv_reader(trade_file, expected_fields=PX6_TRADE_FIELDS)
    with f:
        for row in r:
            row_l = _row_lower(row)
            rows += 1

            action = (row_l.get("action") or "").strip().upper() or "(EMPTY)"
            action_counts[action] = action_counts.get(action, 0) + 1

            is_close_action = action in ("CLOSE", "CLOSE_PARTIAL")
            is_final_close = _is_truthy(row_l.get("is_final_close", "1"), default=(action == "CLOSE"))

            if action == "CLOSE_PARTIAL" or (is_close_action and not is_final_close):
                partial_close_rows += 1

            if not is_close_action or not is_final_close:
                continue

            final_closes += 1
            close_source = (row_l.get("close_source") or "").strip() or "(EMPTY)"
            reason = (row_l.get("reason") or row_l.get("deal_reason") or "").strip() or "(EMPTY)"
            close_sources[close_source] = close_sources.get(close_source, 0) + 1
            close_reasons[reason] = close_reasons.get(reason, 0) + 1

            ar = _safe_float(row_l.get("achievedr", "") or row_l.get("achieved_r", ""))
            if ar is not None:
                achieved_r.append(ar)

            np = _safe_float(row_l.get("net_profit", ""))
            if np is not None:
                net_profit.append(np)

    return {
        "file": str(trade_file),
        "rows": rows,
        "final_closes": final_closes,
        "partial_close_rows": partial_close_rows,
        "action_counts": [{"action": k, "n": v} for k, v in sorted(action_counts.items(), key=lambda x: (-x[1], x[0]))],
        "close_sources": [{"close_source": k, "n": v} for k, v in sorted(close_sources.items(), key=lambda x: (-x[1], x[0]))],
        "close_reasons": [{"reason": k, "n": v} for k, v in sorted(close_reasons.items(), key=lambda x: (-x[1], x[0]))],
        "achieved_r": {
            "n": len(achieved_r),
            "mean": round(_mean(achieved_r), 4),
            "p10": round(_percentile(achieved_r, 10), 4),
            "p50": round(_percentile(achieved_r, 50), 4),
            "p90": round(_percentile(achieved_r, 90), 4),
        },
        "net_profit": {
            "n": len(net_profit),
            "mean": round(_mean(net_profit), 2),
            "p10": round(_percentile(net_profit, 10), 2),
            "p50": round(_percentile(net_profit, 50), 2),
            "p90": round(_percentile(net_profit, 90), 2),
        },
    }


def load_run_meta(meta_file: Optional[Path]) -> dict:
    if not meta_file or not meta_file.exists():
        return {}
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(meta_file.read_text(encoding="utf-16"))


def _lookup_count(rows: List[dict], key_name: str, key_value: str) -> int:
    for row in rows:
        if row.get(key_name) == key_value:
            return int(row.get("n", 0))
    return 0


def build_summary(logs_dir: Path) -> dict:
    token, exec_file, trade_file, meta_file = select_run_files(logs_dir)
    exec_summary = analyze_exec(exec_file)
    trade_summary = analyze_trades(trade_file)
    run_meta = load_run_meta(meta_file)

    meta_tca = run_meta.get("tca", {}) if isinstance(run_meta, dict) else {}

    open_ack = _lookup_count(exec_summary.get("phase_counts", []), "phase", "OPEN_ACK")
    fill_count = _lookup_count(exec_summary.get("phase_counts", []), "phase", "FILL")
    modify_applied_phase = _lookup_count(exec_summary.get("phase_counts", []), "phase", "MODIFY_APPLIED")
    modify_ack = _lookup_count(exec_summary.get("phase_counts", []), "phase", "MODIFY_ACK")
    modify_fail = _lookup_count(exec_summary.get("phase_counts", []), "phase", "MODIFY_FAIL")
    close_ack = _lookup_count(exec_summary.get("phase_counts", []), "phase", "CLOSE_ACK")
    close_fail = _lookup_count(exec_summary.get("phase_counts", []), "phase", "CLOSE_FAIL")

    modify_requests = int(meta_tca.get("modify_requests", modify_ack + modify_fail))
    modify_applied = max(int(meta_tca.get("modify_applied", 0)), modify_ack, modify_applied_phase)
    modify_failed = int(meta_tca.get("modify_failed", modify_fail))
    close_requests = int(meta_tca.get("close_requests", close_ack + close_fail))
    close_failed = int(meta_tca.get("close_failed", close_fail))
    close_deals = int(meta_tca.get("close_deals", trade_summary.get("final_closes", 0)))
    close_partials = int(meta_tca.get("close_partials", trade_summary.get("partial_close_rows", 0)))
    requested_close_sources = {"market_exit", "friday_flatten", "news_guard", "manual_close"}
    requested_close_deals = sum(
        int(row.get("n", 0))
        for row in trade_summary.get("close_sources", [])
        if row.get("close_source") in requested_close_sources
    )
    passive_final_closes = max(int(trade_summary.get("final_closes", 0)) - requested_close_deals, 0)

    reconciliation = {
        "open_ack": open_ack,
        "fill_count": fill_count,
        "open_ack_minus_fill_gap": open_ack - fill_count,
        "modify_requests": modify_requests,
        "modify_applied": modify_applied,
        "modify_failed": modify_failed,
        "modify_unresolved": max(modify_requests - modify_applied - modify_failed, 0),
        "close_requests": close_requests,
        "close_failed": close_failed,
        "close_deals": close_deals,
        "close_partials": close_partials,
        "requested_close_deals": requested_close_deals,
        "passive_final_closes": passive_final_closes,
        "close_unresolved": max(close_requests - close_failed - requested_close_deals, 0),
        "close_ack": close_ack,
        "close_ack_minus_requested_close_gap": close_ack - requested_close_deals,
    }

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "logs_dir": str(logs_dir),
        "token": token,
        "files": {
            "exec": str(exec_file) if exec_file else "",
            "trades": str(trade_file) if trade_file else "",
            "run_meta": str(meta_file) if meta_file else "",
        },
        "run_meta": {
            "stage": run_meta.get("stage", ""),
            "closed_trades": run_meta.get("closed_trades", 0),
            "sqn": run_meta.get("sqn", 0.0),
            "custom_score": run_meta.get("custom_score", 0.0),
            "mean_achieved_r": run_meta.get("mean_achieved_r", 0.0),
            "mean_net_profit": run_meta.get("mean_net_profit", 0.0),
            "mean_hold_minutes": run_meta.get("mean_hold_minutes", 0.0),
            "close_sources": run_meta.get("close_sources", {}),
        },
        "exec": exec_summary,
        "trades": trade_summary,
        "reconciliation": reconciliation,
    }


def build_text(summary: dict) -> str:
    rm = summary.get("run_meta", {})
    rec = summary.get("reconciliation", {})
    tr = summary.get("trades", {})
    ex = summary.get("exec", {})
    lines = [
        f"token: {summary.get('token', '')}",
        f"stage: {rm.get('stage', '')}",
        f"sqn: {rm.get('sqn', 0.0)} | custom_score: {rm.get('custom_score', 0.0)}",
        f"entry fills: {rec.get('fill_count', 0)} | open_ack gap: {rec.get('open_ack_minus_fill_gap', 0)}",
        f"modify req/applied/failed/unresolved: {rec.get('modify_requests', 0)}/{rec.get('modify_applied', 0)}/{rec.get('modify_failed', 0)}/{rec.get('modify_unresolved', 0)}",
        f"close req/requested_deals/failed/partials/unresolved: {rec.get('close_requests', 0)}/{rec.get('requested_close_deals', 0)}/{rec.get('close_failed', 0)}/{rec.get('close_partials', 0)}/{rec.get('close_unresolved', 0)}",
        f"final closes: {tr.get('final_closes', 0)} | passive_final_closes: {rec.get('passive_final_closes', 0)} | ack-requested gap: {rec.get('close_ack_minus_requested_close_gap', 0)}",
        f"achievedR mean/p50/p90: {tr.get('achieved_r', {}).get('mean', 0.0)}/{tr.get('achieved_r', {}).get('p50', 0.0)}/{tr.get('achieved_r', {}).get('p90', 0.0)}",
        f"net mean/p50/p90: {tr.get('net_profit', {}).get('mean', 0.0)}/{tr.get('net_profit', {}).get('p50', 0.0)}/{tr.get('net_profit', {}).get('p90', 0.0)}",
        f"slippage mean/abs_mean/max_abs: {ex.get('slippage_pts', {}).get('mean', 0.0)}/{ex.get('slippage_pts', {}).get('abs_mean', 0.0)}/{ex.get('slippage_pts', {}).get('max_abs', 0.0)}",
    ]
    close_sources = tr.get("close_sources", [])
    if close_sources:
        lines.append("close_sources: " + ", ".join(f"{row['close_source']}={row['n']}" for row in close_sources[:8]))
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs-dir", required=True, help="Directory containing copied run logs")
    ap.add_argument("--out-dir", default="", help="Output directory (default: parent of logs-dir)")
    args = ap.parse_args()

    logs_dir = Path(args.logs_dir)
    if not logs_dir.exists():
        raise SystemExit(f"logs-dir not found: {logs_dir}")

    out_dir = Path(args.out_dir) if args.out_dir else logs_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = build_summary(logs_dir)
    (out_dir / "tca_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "tca_summary.txt").write_text(build_text(summary), encoding="utf-8")

    print(f"[tca_summary] logs={logs_dir}")
    print(f"[tca_summary] token={summary.get('token', '')}")
    print(f"[tca_summary] final_closes={summary.get('trades', {}).get('final_closes', 0)} close_unresolved={summary.get('reconciliation', {}).get('close_unresolved', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
