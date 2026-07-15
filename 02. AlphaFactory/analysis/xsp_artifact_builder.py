#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le", errors="ignore")
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be", errors="ignore")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="ignore")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="ignore")


def _read_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(_read_text(path))
    except Exception:
        return {} if default is None else default


def _parse_dt(value: str):
    s = (value or "").strip()
    if not s:
        return None
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def _f(value, default=0.0):
    try:
        return float(str(value).strip().replace(" ", ""))
    except Exception:
        return default


def _i(value, default=0):
    try:
        return int(float(str(value).strip()))
    except Exception:
        return default


def _safe_div(a, b):
    return a / b if b else 0.0


def _clean_tester_input(value):
    s = "" if value is None else str(value)
    return s.split("||")[0].strip()


def _percentile(values, p):
    xs = sorted(values)
    if not xs:
        return 0.0
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f == c:
        return xs[f]
    return xs[f] * (c - k) + xs[c] * (k - f)


def _profit_factor(pnls):
    gross_profit = sum(x for x in pnls if x > 0)
    gross_loss = -sum(x for x in pnls if x < 0)
    return gross_profit / gross_loss if gross_loss > 0 else 999.99


def _max_drawdown(equity):
    if not equity:
        return 0.0, 0.0
    peak = equity[0]
    max_dd = 0.0
    max_dd_pct = 0.0
    for e in equity:
        peak = max(peak, e)
        dd = peak - e
        max_dd = max(max_dd, dd)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, dd / peak * 100.0)
    return max_dd, max_dd_pct


def _group_paths(logs_dir: Path, pattern: str):
    return sorted(logs_dir.glob(pattern), key=lambda p: p.stat().st_mtime)


def _pick_latest(paths):
    return paths[-1] if paths else None


def _extract_token(path: Path, marker: str):
    if not path:
        return ""
    name = path.name
    idx = name.find(marker)
    if idx < 0:
        return ""
    token = name[idx + len(marker):]
    if "." in token:
        token = token.rsplit(".", 1)[0]
    return token


def load_signal_rows(signal_path: Path):
    rows = []
    if not signal_path or not signal_path.exists():
        return rows
    with signal_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["quality_score"] = _f(row.get("quality_score"))
            row["won_router"] = _i(row.get("won_router"))
            row["utc_dt"] = _parse_dt(row.get("utc_ts"))
            row["server_dt"] = _parse_dt(row.get("server_ts"))
            rows.append(row)
    return rows


def load_shadow_rows(shadow_path: Path):
    rows = []
    if not shadow_path or not shadow_path.exists():
        return rows
    with shadow_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["realized_net_points"] = _f(row.get("realized_net_points"))
            row["mfe_points"] = _f(row.get("mfe_points"))
            row["mae_points"] = _f(row.get("mae_points"))
            row["score"] = _f(row.get("score"))
            row["violation_avoided"] = _i(row.get("violation_avoided"))
            rows.append(row)
    return rows


def aggregate_trades(trades_path: Path):
    rows = []
    if not trades_path or not trades_path.exists():
        return [], []

    with trades_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["position_id"] = str(row.get("position_id", "")).strip()
            row["entry_server_dt"] = _parse_dt(row.get("entry_server_ts"))
            row["entry_utc_dt"] = _parse_dt(row.get("entry_utc_ts"))
            row["exit_server_dt"] = _parse_dt(row.get("exit_server_ts"))
            row["exit_utc_dt"] = _parse_dt(row.get("exit_utc_ts"))
            for key in (
                "hold_minutes", "entry_price", "exit_price", "stop_loss", "target_price",
                "sl_dist_points", "initial_r_points", "mfe_points", "mae_points",
                "giveback_points", "realized_r", "pnl_gross", "commission", "swap", "pnl_net",
                "initial_volume", "remaining_volume", "news_proximity_min", "friday_proximity_min",
                "mfe_r", "mae_r", "achieved_r"
            ):
                row[key] = _f(row.get(key))
            for key in ("is_final_close", "timeout_flag", "spread_abnormal_flag", "compliance_rule_active", "close_rows", "overnight_flag"):
                row[key] = _i(row.get(key))
            row["close_deal_ticket"] = _i(row.get("close_deal_ticket"))
            rows.append(row)

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["position_id"]].append(row)

    trades = []
    for position_id, items in grouped.items():
        items.sort(key=lambda r: (r["exit_server_dt"] or datetime.min, r["close_rows"], r.get("close_deal_ticket", 0)))
        first = items[0]
        last = items[-1]
        pnl_net = sum(r["pnl_net"] for r in items)
        pnl_gross = sum(r["pnl_gross"] for r in items)
        commission = sum(r["commission"] for r in items)
        swap = sum(r["swap"] for r in items)
        trade = {
            "position_id": position_id,
            "engine_name": first.get("engine_name", ""),
            "engine_variant": first.get("engine_variant", ""),
            "entry_server_dt": first["entry_server_dt"],
            "entry_utc_dt": first["entry_utc_dt"],
            "exit_server_dt": last["exit_server_dt"],
            "exit_utc_dt": last["exit_utc_dt"],
            "hold_minutes": last["hold_minutes"] or _safe_div(((last["exit_server_dt"] - first["entry_server_dt"]).total_seconds() if first["entry_server_dt"] and last["exit_server_dt"] else 0), 60.0),
            "entry_reason": first.get("entry_reason", ""),
            "exit_reason": last.get("exit_reason", ""),
            "close_reason_class": last.get("close_reason_class", ""),
            "direction": first.get("direction", ""),
            "entry_price": first["entry_price"],
            "exit_price": last["exit_price"],
            "stop_loss": first["stop_loss"],
            "target_price": first["target_price"],
            "sl_dist_points": first["sl_dist_points"],
            "initial_r_points": first["initial_r_points"],
            "mfe_points": max(r["mfe_points"] for r in items),
            "mae_points": max(r["mae_points"] for r in items),
            "giveback_points": last["giveback_points"],
            "realized_r_last": last["realized_r"],
            "mfe_r": max(r.get("mfe_r", 0.0) for r in items),
            "mae_r": max(r.get("mae_r", 0.0) for r in items),
            "achieved_r": last.get("achieved_r", last.get("realized_r", 0.0)),
            "pnl_gross": pnl_gross,
            "commission": commission,
            "swap": swap,
            "pnl_net": pnl_net,
            "initial_volume": first["initial_volume"],
            "timeout_flag": any(r["timeout_flag"] for r in items),
            "spread_abnormal_flag": any(r["spread_abnormal_flag"] for r in items),
            "compliance_rule_active": any(r["compliance_rule_active"] for r in items),
            "overnight_flag": any(r.get("overnight_flag", 0) for r in items),
            "news_proximity_min": min(r["news_proximity_min"] for r in items) if items else 999999,
            "friday_proximity_min": min(r["friday_proximity_min"] for r in items) if items else 999999,
            "session_tag": first.get("session_tag", ""),
            "weekday_tag": first.get("weekday_tag", ""),
            "parent_trade_id": first.get("parent_trade_id", ""),
            "setup_family": first.get("setup_family", ""),
            "range_type": first.get("range_type", ""),
            "entry_pattern": first.get("entry_pattern", ""),
            "cost_profile": first.get("cost_profile", ""),
            "close_rows": len(items),
            "partial_exit_flag": len(items) > 1,
        }
        trades.append(trade)

    trades.sort(key=lambda x: x["exit_server_dt"] or datetime.min)
    return rows, trades


def bucket_trade_stats(trades):
    pnls = [t["pnl_net"] for t in trades]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    holds = [t["hold_minutes"] for t in trades]
    return {
        "trades": len(trades),
        "net_profit": round(sum(pnls), 2),
        "gross_profit": round(sum(wins), 2),
        "gross_loss": round(sum(losses), 2),
        "profit_factor": round(_profit_factor(pnls), 4),
        "win_rate_pct": round(_safe_div(len(wins) * 100.0, len(trades)), 2),
        "avg_win": round(_safe_div(sum(wins), len(wins)), 2),
        "avg_loss": round(_safe_div(sum(losses), len(losses)), 2),
        "avg_hold_minutes": round(_safe_div(sum(holds), len(holds)), 2),
        "median_hold_minutes": round(median(holds), 2) if holds else 0.0,
        "p95_hold_minutes": round(_percentile(holds, 0.95), 2) if holds else 0.0,
        "timeout_ratio_pct": round(_safe_div(sum(1 for t in trades if t["timeout_flag"]) * 100.0, len(trades)), 2),
        "partial_exit_ratio_pct": round(_safe_div(sum(1 for t in trades if t["partial_exit_flag"]) * 100.0, len(trades)), 2),
    }


def parse_history_quality(report_path: Path):
    if not report_path.exists():
        return ""
    text = _read_text(report_path)
    m = re.search(r"History Quality:</td>\s*<td[^>]*><b>([^<]+)</b>", text, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def update_run_meta(run_meta_path: Path, report_path: Path):
    meta = _read_json(run_meta_path, {})
    if not meta:
        return {}
    history_quality = parse_history_quality(report_path)
    if history_quality:
        meta["history_quality"] = history_quality
        run_meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta


def compute_concentration(trades):
    winners = sorted([t["pnl_net"] for t in trades if t["pnl_net"] > 0], reverse=True)
    gross_profit = sum(winners)
    top5 = _safe_div(sum(winners[:5]) * 100.0, gross_profit)
    top10 = _safe_div(sum(winners[:10]) * 100.0, gross_profit)
    return round(top5, 2), round(top10, 2)


def compute_max_overlap(trades):
    events = []
    for t in trades:
        start = t.get("entry_server_dt")
        end = t.get("exit_server_dt")
        if not start or not end:
            continue
        events.append((start, 1))
        events.append((end, -1))
    if not events:
        return 0
    events.sort(key=lambda x: (x[0], x[1]))
    cur = 0
    best = 0
    for _, delta in events:
        cur += delta
        best = max(best, cur)
    return best


def count_overnight_trades(trades):
    return sum(1 for t in trades if t.get("entry_server_dt") and t.get("exit_server_dt") and t["entry_server_dt"].date() != t["exit_server_dt"].date())


def build_reports(run_dir: Path, analysis_dir: Path, logs_dir: Path):
    reports_dir = run_dir / "reports"
    charts_dir = run_dir / "charts"
    reports_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    signal_candidates = _group_paths(logs_dir, "*_Signals_*.csv")
    trades_candidates = _group_paths(logs_dir, "*_Trades_*.csv")
    shadow_candidates = _group_paths(logs_dir, "*_Shadow_*.csv")
    run_meta_candidates = _group_paths(logs_dir, "*_RunMeta_*.json")
    signal_path = _pick_latest(signal_candidates)
    token = _extract_token(signal_path, "_Signals_")
    trades_path = next((p for p in trades_candidates if _extract_token(p, "_Trades_") == token), _pick_latest(trades_candidates))
    shadow_path = next((p for p in shadow_candidates if _extract_token(p, "_Shadow_") == token), _pick_latest(shadow_candidates))
    run_meta_path = next((p for p in run_meta_candidates if _extract_token(p, "_RunMeta_") == token), _pick_latest(run_meta_candidates))
    report_path = run_dir / "report.html"

    run_meta = update_run_meta(run_meta_path, report_path) if run_meta_path else {}
    for key in (
        "run_id", "campaign_id", "scenario_id", "router_mode", "orb_exit_variant",
        "execution_mode", "cost_stress_profile", "calendar_snapshot_id",
        "calendar_snapshot_hash", "snapshot_coverage_from", "snapshot_coverage_to",
        "included_event_classes", "source_provenance", "history_quality", "timeframe",
        "session_template", "breakout_range_source"
    ):
        if key in run_meta:
            run_meta[key] = _clean_tester_input(run_meta.get(key))
    enhanced_summary = _read_json(analysis_dir / "enhanced_summary.json", {})
    signal_rows = load_signal_rows(signal_path)
    shadow_rows = load_shadow_rows(shadow_path)
    trade_rows, trades = aggregate_trades(trades_path)

    actual_net = sum(t["pnl_net"] for t in trades)
    actual_trade_count = len(trades)
    max_hold_minutes = _i(run_meta.get("max_hold_minutes"), 180) or 180
    max_overlap = compute_max_overlap(trades)
    overnight_count = count_overnight_trades(trades)
    equity = [enhanced_summary.get("start_equity", 10000.0)]
    for t in trades:
        equity.append(equity[-1] + t["pnl_net"])
    max_dd_abs, max_dd_pct = _max_drawdown(equity)
    top5_contrib, top10_contrib = compute_concentration(trades)

    core = bucket_trade_stats(trades)
    core["max_drawdown_abs"] = round(max_dd_abs, 2)
    core["max_drawdown_pct"] = round(max_dd_pct, 2)
    core["top5_trades_contribution_pct"] = top5_contrib
    core["top10_trades_contribution_pct"] = top10_contrib
    core["monthly_consistency_pct"] = 0.0
    core["worst_day"] = {"date": "", "pnl": 0.0}
    core["worst_intraday_loss"] = 0.0

    by_engine = defaultdict(list)
    by_hour = defaultdict(list)
    by_session = defaultdict(list)
    by_weekday = defaultdict(list)
    monthly = defaultdict(float)
    daily = defaultdict(float)
    for t in trades:
        by_engine[t["engine_name"]].append(t)
        entry_utc = t["entry_utc_dt"] or t["entry_server_dt"]
        if entry_utc:
            by_hour[entry_utc.hour].append(t)
            monthly[entry_utc.strftime("%Y-%m")] += t["pnl_net"]
            daily[entry_utc.strftime("%Y-%m-%d")] += t["pnl_net"]
        by_session[t["session_tag"]].append(t)
        by_weekday[t["weekday_tag"]].append(t)

    positive_months = sum(1 for v in monthly.values() if v > 0)
    core["monthly_consistency_pct"] = round(_safe_div(positive_months * 100.0, len(monthly)), 2) if monthly else 0.0
    if daily:
        worst_day_key, worst_day_pnl = min(daily.items(), key=lambda kv: kv[1])
        core["worst_day"] = {"date": worst_day_key, "pnl": round(worst_day_pnl, 2)}
        core["worst_intraday_loss"] = round(min(daily.values()), 2)

    long_holds = [t for t in trades if t["hold_minutes"] > max_hold_minutes]
    pnl_long_holds = sum(t["pnl_net"] for t in long_holds)
    pnl_long_hold_pct = round(_safe_div(pnl_long_holds * 100.0, actual_net), 2) if actual_net != 0 else 0.0
    scalp_like_hold_pct = round(_safe_div(sum(t["pnl_net"] for t in trades if t["hold_minutes"] <= max_hold_minutes) * 100.0, actual_net), 2) if actual_net != 0 else 0.0

    timeout_ratio_pct = round(_safe_div(sum(1 for t in trades if t["timeout_flag"]) * 100.0, actual_trade_count), 2)
    forced_flat_counter = Counter(
        t["exit_reason"] for t in trades
        if t["exit_reason"] in ("friday_cutoff", "rollover_cutoff") or t["exit_reason"].startswith("force_flat_news_")
    )

    blocked_signals_by_rule = Counter()
    blocked_by_rule_points = Counter()
    router_lost_counter = Counter()
    score_deltas = []
    for s in signal_rows:
        if (s.get("blocked_or_fired") or "").lower() == "blocked":
            reason = s.get("block_reason") or "(EMPTY)"
            blocked_signals_by_rule[reason] += 1
            if reason in ("router_shadow_lost_slot", "router_slot_limit"):
                router_lost_counter[s.get("lost_to_engine") or "(UNKNOWN)"] += 1
                score_deltas.append(_f(s.get("winner_engine_score")) - _f(s.get("lost_engine_score")))

    compliance_prefixes = ("news_", "force_flat_news_", "friday_", "rollover_", "entry_spread_guard", "spread_abnormal")
    compliance_shadow = [r for r in shadow_rows if any((r.get("block_reason") or "").startswith(prefix) for prefix in compliance_prefixes)]
    for r in compliance_shadow:
        blocked_by_rule_points[r.get("block_reason") or "(EMPTY)"] += r["realized_net_points"]

    positive_points_blocked = sum(max(r["realized_net_points"], 0.0) for r in compliance_shadow)
    negative_points_avoided = -sum(min(r["realized_net_points"], 0.0) for r in compliance_shadow)
    hypothetical_no_compliance_expectancy = _safe_div(actual_net + positive_points_blocked - negative_points_avoided, actual_trade_count + len(compliance_shadow))
    compliance_adjusted_expectancy = _safe_div(actual_net, actual_trade_count)

    near_news_pnl = sum(t["pnl_net"] for t in trades if t["news_proximity_min"] <= 15)
    near_news_trade_count = sum(1 for t in trades if t["news_proximity_min"] <= 15)
    near_friday_pnl = sum(t["pnl_net"] for t in trades if t["friday_proximity_min"] <= 30)

    engine_rows = []
    for engine_name, items in sorted(by_engine.items()):
        row = {"engine_name": engine_name}
        row.update(bucket_trade_stats(items))
        row["net_profit_share_pct"] = round(_safe_div(sum(t["pnl_net"] for t in items) * 100.0, actual_net), 2) if actual_net != 0 else 0.0
        engine_rows.append(row)

    hour_rows = []
    for hour in range(24):
        stats = bucket_trade_stats(by_hour.get(hour, []))
        hour_rows.append({"bucket_type": "hour_utc", "bucket": hour, **stats})
    for session_name in ("Asia", "London", "NewYork", "OffHours", ""):
        label = session_name or "(EMPTY)"
        stats = bucket_trade_stats(by_session.get(session_name, []))
        hour_rows.append({"bucket_type": "session", "bucket": label, **stats})

    mfe_rows = []
    exit_reason_counter = Counter()
    profit_per_session_bucket = {}
    for t in trades:
        mfe_rows.append({
            "position_id": t["position_id"],
            "engine_name": t["engine_name"],
            "engine_variant": t["engine_variant"],
            "hold_minutes": round(t["hold_minutes"], 2),
            "mfe_points": round(t["mfe_points"], 2),
            "mae_points": round(t["mae_points"], 2),
            "giveback_points": round(t["giveback_points"], 2),
            "pnl_net": round(t["pnl_net"], 2),
            "realized_r_last": round(t["realized_r_last"], 4),
            "timeout_flag": int(t["timeout_flag"]),
            "partial_exit_flag": int(t["partial_exit_flag"]),
            "exit_reason": t["exit_reason"],
        })
        exit_reason_counter[t["exit_reason"]] += 1
    for session_name, items in by_session.items():
        profit_per_session_bucket[session_name or "(EMPTY)"] = round(sum(t["pnl_net"] for t in items), 2)

    report_trade_count = enhanced_summary.get("n_trades", 0)
    missing_position_ids = sum(1 for t in trades if not t["position_id"])
    dominant_engine_share = max((abs(r["net_profit_share_pct"]) for r in engine_rows), default=0.0)

    gates = {
        "GateA_DataIntegrity": {
            "pass": bool(report_trade_count == 0 or report_trade_count == actual_trade_count) and missing_position_ids == 0 and bool(run_meta.get("calendar_snapshot_hash")),
            "checks": {
                "report_trade_count": report_trade_count,
                "trade_log_trade_count": actual_trade_count,
                "missing_position_ids": missing_position_ids,
                "calendar_snapshot_hash_present": bool(run_meta.get("calendar_snapshot_hash")),
            },
        },
        "GateB_StructureQuality": {
            "pass": max_overlap <= 1 and overnight_count == 0 and top5_contrib <= 35.0 and top10_contrib <= 55.0 and core["median_hold_minutes"] <= 120.0 and core["p95_hold_minutes"] <= max_hold_minutes and abs(pnl_long_hold_pct) <= 15.0 and dominant_engine_share <= 70.0,
            "checks": {
                "max_overlap_positions": max_overlap,
                "overnight_trades": overnight_count,
                "top5_trades_contribution_pct": top5_contrib,
                "top10_trades_contribution_pct": top10_contrib,
                "median_hold_minutes": core["median_hold_minutes"],
                "p95_hold_minutes": core["p95_hold_minutes"],
                "max_hold_minutes_gate": max_hold_minutes,
                "pnl_from_trades_gt_max_hold_pct": pnl_long_hold_pct,
                "timeout_ratio_pct": timeout_ratio_pct,
                "dominant_engine_share_pct": dominant_engine_share,
            },
        },
        "GateC_ExecutionRealism": {
            "pass": True,
            "checks": {
                "status": "pending_real_ticks_delay_cost_campaigns"
            },
        },
        "GateD_ComplianceFitness": {
            "pass": True,
            "checks": {
                "signals_blocked_by_news": sum(v for k, v in blocked_signals_by_rule.items() if k.startswith("news_")),
                "forced_flat_news_trades": sum(v for k, v in forced_flat_counter.items() if k.startswith("force_flat_news_")),
                "near_news_trade_count": near_news_trade_count,
                "near_news_pnl": round(near_news_pnl, 2),
                "near_friday_pnl": round(near_friday_pnl, 2),
                "compliance_adjusted_expectancy": round(compliance_adjusted_expectancy, 4),
                "counterfactual_violations_avoided": sum(r["violation_avoided"] for r in compliance_shadow),
            },
        },
        "GateE_Robustness": {
            "pass": True,
            "checks": {
                "status": "pending_nearby_settings_and_M15_phase1B"
            },
        },
    }

    top_findings = [
        f"Trades={actual_trade_count}, net={actual_net:.2f}, expectancy={compliance_adjusted_expectancy:.4f}, maxDD={core['max_drawdown_pct']:.2f}%",
        f"Hold median={core['median_hold_minutes']:.1f}m, p95={core['p95_hold_minutes']:.1f}m, max_hold_gate={max_hold_minutes}m",
        f"Overlap={max_overlap}, overnight_trades={overnight_count}, timeout={timeout_ratio_pct:.1f}%",
        f"Top5 contribution={top5_contrib:.1f}%, Top10 contribution={top10_contrib:.1f}%",
        f"Scalp-like PnL share={scalp_like_hold_pct:.1f}%, dominant engine share={dominant_engine_share:.1f}%",
    ]
    top_actions = [
        "Run IS/OOS split exactly on M15 with real-ticks before trusting headline expectancy.",
        "Stress test with delay + adverse fills using cost profiles instead of chasing PF.",
        "If overnight/overlap > 0, treat it as architecture failure before any signal tweak.",
        "Use MFE/MAE + hold-time clustering to decide whether time-stop or entry timing is the pain point.",
        "Replace the placeholder calendar snapshot before any serious compliance conclusion.",
    ]

    summary = {
        "run_id": run_meta.get("run_id", ""),
        "build_id": run_meta.get("run_id", ""),
        "engine_tested": sorted(set(t["engine_name"] for t in trades)),
        "test_config": {
            "campaign_id": run_meta.get("campaign_id", ""),
            "scenario_id": run_meta.get("scenario_id", ""),
            "router_mode": run_meta.get("router_mode", ""),
            "max_open_positions_portfolio": run_meta.get("max_open_positions_portfolio", ""),
            "orb_exit_variant": run_meta.get("orb_exit_variant", ""),
            "session_template": run_meta.get("session_template", ""),
            "breakout_range_source": run_meta.get("breakout_range_source", ""),
            "max_hold_minutes": max_hold_minutes,
            "model": run_meta.get("model", ""),
            "execution_mode": run_meta.get("execution_mode", ""),
            "fixed_delay_ms": run_meta.get("fixed_delay_ms", 0),
            "history_quality": run_meta.get("history_quality", ""),
            "calendar_snapshot_id": run_meta.get("calendar_snapshot_id", ""),
            "calendar_snapshot_hash": run_meta.get("calendar_snapshot_hash", ""),
            "snapshot_coverage_from": run_meta.get("snapshot_coverage_from", ""),
            "snapshot_coverage_to": run_meta.get("snapshot_coverage_to", ""),
            "included_event_classes": run_meta.get("included_event_classes", ""),
            "source_provenance": run_meta.get("source_provenance", ""),
        },
        "verdict": "PASS_SMOKE" if gates["GateA_DataIntegrity"]["pass"] else "FAIL_DATA_INTEGRITY",
        "top_5_findings": top_findings,
        "top_5_action_items": top_actions,
        "core_metrics": {
            "full_basket": core,
            "by_engine": engine_rows,
        },
        "forensic_metrics": {
            "exit_reason_decomposition": dict(exit_reason_counter),
            "timeout_ratio_pct": timeout_ratio_pct,
            "max_overlap_positions": max_overlap,
            "overnight_trades": overnight_count,
            "pnl_from_trades_gt_max_hold_pct": pnl_long_hold_pct,
            "scalp_like_pnl_share_pct": scalp_like_hold_pct,
            "profit_per_session_bucket": profit_per_session_bucket,
            "pnl_near_news": round(near_news_pnl, 2),
            "pnl_near_friday_cutoff": round(near_friday_pnl, 2),
        },
        "compliance_metrics": {
            "signals_blocked_by_rule": dict(blocked_signals_by_rule),
            "trades_forced_flat_by_rule": dict(forced_flat_counter),
            "counterfactual_pnl_points_by_rule": {k: round(v, 2) for k, v in blocked_by_rule_points.items()},
            "counterfactual_violations_avoided": sum(r["violation_avoided"] for r in compliance_shadow),
            "positive_points_blocked": round(positive_points_blocked, 2),
            "negative_points_avoided": round(negative_points_avoided, 2),
            "hypothetical_no_compliance_expectancy": round(hypothetical_no_compliance_expectancy, 4),
            "compliance_adjusted_expectancy": round(compliance_adjusted_expectancy, 4),
        },
        "router_metrics": {
            "signals_lost_by_router_target": dict(router_lost_counter),
            "avg_router_score_delta": round(_safe_div(sum(score_deltas), len(score_deltas)), 4),
            "shadow_counterfactual_status": dict(Counter(r.get("counterfactual_status", "") for r in shadow_rows)),
            "max_overlap_positions": max_overlap,
        },
        "gates": gates,
    }

    (reports_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    with (reports_dir / "engine_comparison.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(engine_rows[0].keys()) if engine_rows else ["engine_name"])
        writer.writeheader()
        for row in engine_rows:
            writer.writerow(row)

    with (reports_dir / "hour_session_breakdown.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(hour_rows[0].keys()) if hour_rows else ["bucket_type", "bucket"])
        writer.writeheader()
        for row in hour_rows:
            writer.writerow(row)

    with (reports_dir / "mfe_mae.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(mfe_rows[0].keys()) if mfe_rows else ["position_id"])
        writer.writeheader()
        for row in mfe_rows:
            writer.writerow(row)

    (reports_dir / "compliance_report.json").write_text(json.dumps(summary["compliance_metrics"], indent=2, ensure_ascii=False), encoding="utf-8")
    (reports_dir / "router_report.json").write_text(json.dumps(summary["router_metrics"], indent=2, ensure_ascii=False), encoding="utf-8")
    (reports_dir / "pass_fail_checklist.json").write_text(json.dumps(gates, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"# XAU_Scalp_Portfolio Summary - {summary['run_id']}",
        "",
        f"- Verdict: **{summary['verdict']}**",
        f"- Scenario: `{run_meta.get('scenario_id', '')}` | Campaign: `{run_meta.get('campaign_id', '')}`",
        f"- Router: `{run_meta.get('router_mode', '')}` | Slots: `{run_meta.get('max_open_positions_portfolio', '')}` | Session template: `{run_meta.get('session_template', '')}`",
        f"- Model: `{run_meta.get('model', '')}` | Execution: `{run_meta.get('execution_mode', '')}` | Delay ms: `{run_meta.get('fixed_delay_ms', 0)}`",
        f"- History Quality: `{run_meta.get('history_quality', '')}`",
        "",
        "## Top 5 findings",
    ]
    lines.extend([f"- {x}" for x in top_findings])
    lines.extend(["", "## Top 5 action items"])
    lines.extend([f"- {x}" for x in top_actions])
    lines.extend([
        "",
        "## Core metrics",
        f"- Trades: **{actual_trade_count}**",
        f"- Net profit: **{actual_net:.2f}**",
        f"- Profit factor: **{core['profit_factor']:.2f}**",
        f"- Win rate: **{core['win_rate_pct']:.2f}%**",
        f"- Max drawdown: **{core['max_drawdown_pct']:.2f}%**",
        f"- Median hold: **{core['median_hold_minutes']:.1f}m** | P95 hold: **{core['p95_hold_minutes']:.1f}m**",
        f"- Timeout ratio: **{timeout_ratio_pct:.1f}%**",
        f"- Overlap max: **{max_overlap}** | Overnight trades: **{overnight_count}**",
        f"- PnL from trades >{max_hold_minutes}m: **{pnl_long_hold_pct:.1f}%**",
        f"- Compliance-adjusted expectancy: **{compliance_adjusted_expectancy:.4f}**",
    ])
    (reports_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    if HAS_MATPLOTLIB and trades:
        exits = [t["exit_server_dt"] for t in trades]
        eq = [enhanced_summary.get("start_equity", 10000.0)]
        for t in trades:
            eq.append(eq[-1] + t["pnl_net"])
        eq_dates = [trades[0]["entry_server_dt"]] + exits

        plt.figure(figsize=(10, 4))
        plt.plot(eq_dates, eq, linewidth=1.0)
        plt.title("Equity Curve")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(charts_dir / "equity.png", dpi=140)
        plt.close()

        running_peak = eq[0]
        dd = []
        for v in eq:
            running_peak = max(running_peak, v)
            dd.append(v - running_peak)
        plt.figure(figsize=(10, 4))
        plt.fill_between(eq_dates, dd, 0, alpha=0.5, color="red")
        plt.title("Underwater")
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(charts_dir / "underwater.png", dpi=140)
        plt.close()

        plt.figure(figsize=(8, 4))
        names = [r["engine_name"] for r in engine_rows]
        vals = [r["net_profit"] for r in engine_rows]
        plt.bar(names, vals)
        plt.title("PnL by Engine")
        plt.xticks(rotation=20)
        plt.tight_layout()
        plt.savefig(charts_dir / "pnl_by_engine.png", dpi=140)
        plt.close()

        plt.figure(figsize=(10, 4))
        plt.bar(list(range(24)), [sum(t["pnl_net"] for t in by_hour.get(h, [])) for h in range(24)])
        plt.title("PnL by Hour (UTC)")
        plt.tight_layout()
        plt.savefig(charts_dir / "pnl_by_hour.png", dpi=140)
        plt.close()

        session_labels = ["Asia", "London", "NewYork", "OffHours", "(EMPTY)"]
        plt.figure(figsize=(8, 4))
        plt.bar(session_labels, [profit_per_session_bucket.get(x, 0.0) for x in session_labels])
        plt.title("PnL by Session")
        plt.tight_layout()
        plt.savefig(charts_dir / "pnl_by_session.png", dpi=140)
        plt.close()

        plt.figure(figsize=(8, 4))
        plt.hist([t["hold_minutes"] for t in trades], bins=min(25, max(5, len(trades))))
        plt.title("Trade Duration")
        plt.tight_layout()
        plt.savefig(charts_dir / "trade_duration.png", dpi=140)
        plt.close()

        winners = sorted([t["pnl_net"] for t in trades if t["pnl_net"] > 0], reverse=True)
        if winners:
            cum = []
            s = 0.0
            gross_profit = sum(winners)
            for x in winners:
                s += x
                cum.append(_safe_div(s * 100.0, gross_profit))
            plt.figure(figsize=(8, 4))
            plt.plot(range(1, len(cum) + 1), cum)
            plt.axhline(35, color="orange", linestyle="--", linewidth=0.8)
            plt.axhline(55, color="red", linestyle="--", linewidth=0.8)
            plt.title("Top Trades Concentration")
            plt.tight_layout()
            plt.savefig(charts_dir / "top_trades_concentration.png", dpi=140)
            plt.close()

        timeout_counts = [sum(1 for t in trades if not t["timeout_flag"]), sum(1 for t in trades if t["timeout_flag"])]
        plt.figure(figsize=(6, 4))
        plt.bar(["non-timeout", "timeout"], timeout_counts)
        plt.title("Timeout Distribution")
        plt.tight_layout()
        plt.savefig(charts_dir / "timeout_distribution.png", dpi=140)
        plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--analysis-dir", required=True)
    ap.add_argument("--logs-dir", required=True)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    analysis_dir = Path(args.analysis_dir)
    logs_dir = Path(args.logs_dir)
    build_reports(run_dir, analysis_dir, logs_dir)


if __name__ == "__main__":
    main()
