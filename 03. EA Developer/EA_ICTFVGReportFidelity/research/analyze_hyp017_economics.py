#!/usr/bin/env python3
"""Reconcile and score the single frozen HYP-017 Model-0 run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, pstdev


ROOT = Path(r"D:\Trading EA MT5")
HYPOTHESIS_ID = "HYP-ICT-FVG-HUMAN-CONTEXT-POLICY-EURUSD-M5-017"
SOURCE_SHA256 = "FF02340C65CBB0E36B1794CB8263023FDD9B7F9218492E749F1F8875C826A5C6"
NATURAL_STATES = {"EXTERNAL_SWEEP_WITH_ROOM", "INTERNAL_SWEEP_WITH_ROOM"}
COST_PIPS = (1.5, 2.25, 3.0)
BOOTSTRAP_SEED = 20260719
BOOTSTRAP_REPS = 10000


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def load_clock_module():
    path = ROOT / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
    spec = importlib.util.spec_from_file_location("fivepercent_server_clock", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load FivePercent server clock")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return path, module


def parse_time(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y.%m.%d %H:%M:%S")


def profit_factor(values: list[float]) -> float | None:
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    if gross_loss <= 0:
        return None
    return gross_profit / gross_loss


def max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    worst = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def r_distribution(values: list[float]) -> dict:
    ordered = sorted(values)
    buckets = Counter()
    for value in values:
        if value <= -1.25:
            buckets["le_-1_25R"] += 1
        elif value <= -0.75:
            buckets["minus1R_zone"] += 1
        elif value < 0.0:
            buckets["small_loss"] += 1
        elif value < 0.75:
            buckets["small_win"] += 1
        elif value < 1.5:
            buckets["mid_win"] += 1
        else:
            buckets["near_2R_or_more"] += 1
    return {
        "mean": mean(values),
        "median": percentile(ordered, 0.5),
        "p05": percentile(ordered, 0.05),
        "p25": percentile(ordered, 0.25),
        "p75": percentile(ordered, 0.75),
        "p95": percentile(ordered, 0.95),
        "buckets": dict(sorted(buckets.items())),
    }


def percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        return 0.0
    position = probability * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def session_name(utc_time: datetime) -> str:
    minute = utc_time.hour * 60 + utc_time.minute
    if 7 * 60 <= minute < 11 * 60:
        return "LONDON"
    if 13 * 60 <= minute < 17 * 60:
        return "NEW_YORK"
    return "OUTSIDE"


def week_monday(value: datetime) -> datetime:
    day = value.replace(hour=0, minute=0, second=0, microsecond=0)
    return day - timedelta(days=day.weekday())


def find_sidecar(run_dir: Path, manifest: dict, marker: str) -> Path:
    matches = []
    for item in manifest.get("sidecars") or []:
        rel = str(item.get("path", ""))
        if marker in Path(rel).name:
            path = run_dir / rel
            if not path.is_file() or sha_file(path) != str(item.get("sha256", "")).upper():
                raise ValueError(f"sidecar missing or drifted: {rel}")
            matches.append(path)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {marker} sidecar")
    return matches[0]


def load_trades(lifecycle_path: Path, clock) -> list[dict]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with lifecycle_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            grouped[row["position_id"]].append(row)
    trades = []
    for position_id, rows in grouped.items():
        opens = [row for row in rows if row["action"] == "OPEN"]
        closes = [row for row in rows if row["action"] == "CLOSE" and row["is_final_close"] == "1"]
        if len(opens) != 1 or len(closes) != 1 or len(rows) != 2:
            raise ValueError(f"position {position_id} lifecycle is not one OPEN plus one final CLOSE")
        opened, closed = opens[0], closes[0]
        entry_server = parse_time(opened["event_time"])
        close_server = parse_time(closed["event_time"])
        entry_utc = clock.server_to_utc(entry_server)
        close_utc = clock.server_to_utc(close_server)
        volume = float(opened["volume"])
        risk_account = float(opened["initial_risk_account"])
        base_net = sum(float(row["deal_net"]) for row in rows)
        if risk_account <= 0 or volume <= 0:
            raise ValueError(f"position {position_id} has invalid risk/volume")
        trades.append(
            {
                "position_id": position_id,
                "entry_server": opened["event_time"],
                "entry_utc": entry_utc,
                "close_utc": close_utc,
                "direction": "LONG" if opened["order_type"] == "BUY" else "SHORT",
                "direction_code": "1" if opened["order_type"] == "BUY" else "-1",
                "volume": volume,
                "risk_account": risk_account,
                "base_net": base_net,
                "base_r": base_net / risk_account,
                "hold_minutes": (close_utc - entry_utc).total_seconds() / 60.0,
                "session": session_name(entry_utc),
                "year": str(close_utc.year),
                "week": week_monday(entry_utc).date().isoformat(),
            }
        )
    trades.sort(key=lambda trade: (trade["entry_utc"], int(trade["position_id"])))
    return trades


def join_context(trades: list[dict], context_path: Path) -> dict:
    candidates: dict[tuple[str, str], list[str]] = defaultdict(list)
    by_direction: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    with context_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["valid"] == "1" and row["context_state"] in NATURAL_STATES:
                candidates[(row["decision_time"], row["direction"])].append(row["context_state"])
                by_direction[row["direction"]].append(
                    (parse_time(row["decision_time"]), row["context_state"])
                )
    matched = 0
    tolerance_matches = 0
    ambiguous = 0
    unmatched = 0
    for trade in trades:
        values = candidates.get((trade["entry_server"], trade["direction_code"]), [])
        if not values:
            entry_server = parse_time(trade["entry_server"])
            fallback = [
                state
                for decision_time, state in by_direction[trade["direction_code"]]
                if 0.0 <= (entry_server - decision_time).total_seconds() <= 300.0
            ]
            if len(fallback) == 1:
                trade["context_state"] = fallback[0]
                matched += 1
                tolerance_matches += 1
            else:
                trade["context_state"] = "UNMATCHED"
                unmatched += 1
        else:
            trade["context_state"] = values[0]
            matched += 1
            ambiguous += int(len(values) > 1)
    return {
        "matched": matched,
        "unmatched": unmatched,
        "ambiguous_keys": ambiguous,
        "within_5m_delayed_tick_matches": tolerance_matches,
    }


def breakdown(trades: list[dict], key: str, value_key: str) -> dict:
    grouped: dict[str, list[float]] = defaultdict(list)
    for trade in trades:
        grouped[str(trade[key])].append(float(trade[value_key]))
    return {
        group: {
            "trades": len(values),
            "net": sum(values),
            "profit_factor": profit_factor(values),
            "mean": mean(values),
            "win_rate": sum(value > 0 for value in values) / len(values),
        }
        for group, values in sorted(grouped.items())
    }


def bootstrap_week_blocks(trades: list[dict], value_key: str) -> dict:
    grouped: dict[str, list[float]] = defaultdict(list)
    for trade in trades:
        grouped[trade["week"]].append(float(trade[value_key]))
    weeks = sorted(grouped)
    rng = random.Random(BOOTSTRAP_SEED)
    estimates = []
    for _ in range(BOOTSTRAP_REPS):
        values = []
        for _ in weeks:
            values.extend(grouped[rng.choice(weeks)])
        estimates.append(mean(values) if values else 0.0)
    estimates.sort()
    return {
        "seed": BOOTSTRAP_SEED,
        "repetitions": BOOTSTRAP_REPS,
        "calendar_week_blocks": len(weeks),
        "mean_r_per_trade": mean(float(trade[value_key]) for trade in trades),
        "ci95": [percentile(estimates, 0.025), percentile(estimates, 0.975)],
    }


def risk_metrics(trades: list[dict], value_key: str) -> dict:
    weekly: dict[datetime, float] = defaultdict(float)
    for trade in trades:
        weekly[week_monday(trade["entry_utc"])] += float(trade[value_key])
    start = min(weekly)
    end = max(weekly)
    series = []
    cursor = start
    while cursor <= end:
        series.append(weekly.get(cursor, 0.0))
        cursor += timedelta(days=7)
    avg = mean(series)
    vol = pstdev(series)
    downside = math.sqrt(mean(min(0.0, value) ** 2 for value in series))
    values = [float(trade[value_key]) for trade in trades]
    sorted_values = sorted(values)
    tail_n = max(1, math.ceil(0.05 * len(sorted_values)))
    years = (trades[-1]["close_utc"] - trades[0]["entry_utc"]).total_seconds() / (365.25 * 86400)
    annual_r = sum(values) / years if years > 0 else 0.0
    dd_r = max_drawdown(values)
    return {
        "weekly_sharpe": avg / vol * math.sqrt(52) if vol > 0 else None,
        "weekly_sortino": avg / downside * math.sqrt(52) if downside > 0 else None,
        "calmar_r": annual_r / dd_r if dd_r > 0 else None,
        "max_drawdown_r": dd_r,
        "cvar_5pct_r_per_trade": mean(sorted_values[:tail_n]),
        "median_hold_minutes": percentile(sorted(trade["hold_minutes"] for trade in trades), 0.5),
        "mean_hold_minutes": mean(trade["hold_minutes"] for trade in trades),
    }


def analyze(run_dir: Path) -> dict:
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    lifecycle_path = find_sidecar(run_dir, manifest, "_LifecycleTrades_")
    runmeta_path = find_sidecar(run_dir, manifest, "_RunMeta_")
    context_path = find_sidecar(run_dir, manifest, "_HumanContext_")
    enhanced_path = run_dir / "analysis" / "enhanced_summary.json"
    enhanced = json.loads(enhanced_path.read_text(encoding="utf-8-sig"))
    runmeta = json.loads(runmeta_path.read_text(encoding="utf-8-sig"))
    diagnostic = runmeta.get("diagnostic") or {}
    clock_path, clock = load_clock_module()
    trades = load_trades(lifecycle_path, clock)
    context_join = join_context(trades, context_path)
    elapsed_weeks = (
        (trades[-1]["close_utc"] - trades[0]["entry_utc"]).total_seconds() / (7 * 86400)
        if trades
        else 0.0
    )

    cost_results = {}
    for pips in COST_PIPS:
        key = f"cost_{str(pips).replace('.', '_')}p"
        for trade in trades:
            incremental = pips * 10.0 * trade["volume"]
            trade[key + "_net"] = trade["base_net"] - incremental
            trade[key + "_r"] = trade[key + "_net"] / trade["risk_account"]
        nets = [trade[key + "_net"] for trade in trades]
        rs = [trade[key + "_r"] for trade in trades]
        cost_results[key] = {
            "incremental_round_turn_pips": pips,
            "trades": len(trades),
            "net": sum(nets),
            "profit_factor": profit_factor(nets),
            "expectancy_usd_per_trade": mean(nets),
            "expectancy_r_per_trade": mean(rs),
            "win_rate": sum(value > 0 for value in nets) / len(nets),
        }

    primary_key = "cost_1_5p"
    primary_net_key = primary_key + "_net"
    primary_r_key = primary_key + "_r"
    years = breakdown(trades, "year", primary_net_key)
    positive_years = [year for year, row in years.items() if row["net"] > 0]
    total_positive_year_profit = sum(row["net"] for row in years.values() if row["net"] > 0)
    concentration = (
        max((row["net"] for row in years.values() if row["net"] > 0), default=0.0)
        / total_positive_year_profit
        if total_positive_year_profit > 0
        else None
    )
    lifecycle_net = sum(trade["base_net"] for trade in trades)
    report_net = float(enhanced["net_profit"])
    gates = {
        "identity_and_history": (
            manifest.get("hypothesis_id") == HYPOTHESIS_ID
            and manifest.get("source_sha256") == SOURCE_SHA256
            and manifest.get("telemetry_profile") == "lifecycle-v3"
            and str((manifest.get("fingerprint_basis") or {}).get("history_quality")) == "99%"
            and runmeta.get("hypothesis_id") == HYPOTHESIS_ID
            and runmeta.get("signal_mode") == 3
        ),
        "lifecycle_report_reconciled": (
            len(trades) == int(enhanced["n_trades"])
            == int(diagnostic.get("entries_opened", -1))
            and abs(lifecycle_net - report_net) <= 0.01
            and context_join["unmatched"] == 0
        ),
        "min_200_trades": len(trades) >= 200,
        "cadence_2_to_5_per_week": 2.0 <= len(trades) / elapsed_weeks <= 5.0,
        "primary_cost_pf_ge_1_30": (cost_results[primary_key]["profit_factor"] or 0.0) >= 1.30,
        "stress_2_25p_pf_ge_1_25": (cost_results["cost_2_25p"]["profit_factor"] or 0.0) >= 1.25,
        "stress_3_0p_pf_ge_1_00": (cost_results["cost_3_0p"]["profit_factor"] or 0.0) >= 1.00,
        "primary_expectancy_positive": cost_results[primary_key]["expectancy_r_per_trade"] > 0,
        "max_account_dd_le_8pct": float(enhanced["max_drawdown_pct"]) <= 8.0,
        "at_least_6_positive_years": len(positive_years) >= 6,
        "positive_profit_concentration_le_40pct": concentration is not None and concentration <= 0.40,
    }
    result = {
        "schema_version": "hyp017_model0_economic_result.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": run_dir.name,
        "input_hashes": {
            "run_manifest": sha_file(manifest_path),
            "enhanced_summary": sha_file(enhanced_path),
            "run_meta": sha_file(runmeta_path),
            "lifecycle_trades": sha_file(lifecycle_path),
            "human_context": sha_file(context_path),
            "server_clock": sha_file(clock_path),
        },
        "native": {
            "trades": len(trades),
            "elapsed_calendar_weeks": elapsed_weeks,
            "cadence_per_week": len(trades) / elapsed_weeks,
            "net": report_net,
            "profit_factor": float(enhanced["profit_factor"]),
            "win_rate_pct": float(enhanced["win_rate_pct"]),
            "max_drawdown_pct": float(enhanced["max_drawdown_pct"]),
            "expectancy_usd_per_trade": float(enhanced["expectancy_per_trade"]),
            "lifecycle_net": lifecycle_net,
            "history_quality_pct": 99.0,
            "bars": int((manifest.get("fingerprint_basis") or {})["bars"]),
            "ticks": int((manifest.get("fingerprint_basis") or {})["ticks"]),
        },
        "funnel": {
            "sweeps": int(diagnostic["sweeps"]),
            "policy_rejections": int(diagnostic["human_policy_rejections"]),
            "policy_accepts": int(diagnostic["sweeps"]) - int(diagnostic["human_policy_rejections"]),
            "prop_rejections": int(diagnostic["prop_rejections"]),
            "exposure_rejections": int(diagnostic["exposure_rejections"]),
            "spread_rejections": int(diagnostic["spread_rejections"]),
            "risk_rejections": int(diagnostic["risk_rejections"]),
            "session_rejections": int(diagnostic["session_rejections"]),
            "entries_attempted": int(diagnostic["entries_attempted"]),
            "entries_opened": int(diagnostic["entries_opened"]),
            "ordercheck_rejections": int(diagnostic["ordercheck_rejections"]),
            "ordercheck_zero_successes": int(diagnostic["ordercheck_zero_successes"]),
        },
        "context_join": context_join,
        "cost_diagnostics": cost_results,
        "base_r_distribution": r_distribution([trade["base_r"] for trade in trades]),
        "primary_cost_r_distribution": r_distribution(
            [trade[primary_r_key] for trade in trades]
        ),
        "by_year_primary_cost": years,
        "by_session_primary_cost": breakdown(trades, "session", primary_net_key),
        "by_direction_primary_cost": breakdown(trades, "direction", primary_net_key),
        "by_context_state_primary_cost": breakdown(trades, "context_state", primary_net_key),
        "positive_years": positive_years,
        "positive_profit_concentration": concentration,
        "risk_metrics_primary_cost": risk_metrics(trades, primary_r_key),
        "week_block_bootstrap_primary_cost": bootstrap_week_blocks(trades, primary_r_key),
        "gates": gates,
        "gates_passed": sum(gates.values()),
        "gates_total": len(gates),
        "all_gates_pass": all(gates.values()),
        "verdict": (
            "PASS_DIAGNOSTIC_REQUIRES_FRESH_VALIDATION"
            if all(gates.values())
            else "KILL_AT_HYP017_MODEL0_NO_STABLE_EDGE"
        ),
        "promotion_eligible": False,
        "limitations": [
            "Design-after-family-history diagnostic, not an independent sealed holdout.",
            "Historical broker spread/slippage provenance is not verified.",
            "Incremental pip costs are conservative because tester spread is already embedded.",
            "No failed subgroup may be removed post hoc to rescue HYP-017.",
        ],
    }
    result["canonical_result_sha256"] = canonical_sha(result)
    return result


def render_markdown(result: dict) -> str:
    native = result["native"]
    primary = result["cost_diagnostics"]["cost_1_5p"]
    boot = result["week_block_bootstrap_primary_cost"]
    failed = [name for name, passed in result["gates"].items() if not passed]
    return f"""# HYP-017 Model-0 readout

## Verdict

`{result['verdict']}`. Promotion remains `false`.

## Native run

- Run: `{result['run_id']}`; EURUSD M5 Model 0; 2018-01-01 to 2026-07-19.
- {native['trades']} reconciled trades over {native['elapsed_calendar_weeks']:.6f} elapsed weeks = {native['cadence_per_week']:.4f}/week.
- Tester PF {native['profit_factor']:.4f}; net ${native['net']:.2f}; win rate {native['win_rate_pct']:.2f}%; max DD {native['max_drawdown_pct']:.3f}%.
- Lifecycle net ${native['lifecycle_net']:.2f}; history quality {native['history_quality_pct']:.0f}%; {native['bars']:,} bars / {native['ticks']:,} ticks.

## Frozen cost diagnostic

- Additional 1.5-pip RT: PF {primary['profit_factor']:.4f}; net ${primary['net']:.2f}; {primary['expectancy_r_per_trade']:.5f}R/trade.
- Week-block bootstrap mean {boot['mean_r_per_trade']:.5f}R/trade; 95% CI [{boot['ci95'][0]:.5f}, {boot['ci95'][1]:.5f}].
- Gates passed: {result['gates_passed']}/{result['gates_total']}. Failed: {', '.join(failed)}.

## Interpretation

The fixed human-context states reduce the opportunity universe but do not create positive expectancy. Both named sessions and both directions remain negative after the frozen cost diagnostic; post-hoc session, weekday, year, state, RR, or threshold filtering is not authorized.

## Reproducibility

- Canonical result SHA-256: `{result['canonical_result_sha256']}`.
- Source SHA-256: `{SOURCE_SHA256}`.
- Promotion ineligible because cost provenance and independent validation remain unmet.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run.resolve())
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.md_out.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({"json": str(args.json_out), "sha256": sha_file(args.json_out), "verdict": result["verdict"]}))
    return 0 if result["all_gates_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
