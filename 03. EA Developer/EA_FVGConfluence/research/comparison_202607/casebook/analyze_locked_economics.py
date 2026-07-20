#!/usr/bin/env python3
"""Locked economics interface; all authorization checks run before bar loading."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from casebook_contract import (
    HYPOTHESIS_ID,
    M1_PATH,
    PROTOCOL_PATH,
    REGISTRY_PATH,
    SOURCE_PATH,
    STUDY_ID,
    ContractError,
    load_json,
    load_m1_pre_holdout,
    resample_ohlc,
    sha256_file,
)

PLAN_PATH = Path(__file__).resolve().parent / "SEALED_ANALYSIS_PLAN.json"


def _latest_registry_record(registry: Path, hypothesis_id: str) -> dict[str, Any] | None:
    latest = None
    for line in registry.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("hypothesis_id") == hypothesis_id:
            latest = row
    return latest


def authorize_before_outcome_load(internal: Path, gate_report: Path, prereg: Path,
                                  reviewer_1: Path, reviewer_2: Path,
                                  registry: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Fail before touching M1 unless every gate and SHA binding is exact."""
    gate = load_json(gate_report)
    if gate.get("schema_version") != "fvg_human_label_gate.v2" or gate.get("study_id") != STUDY_ID:
        raise ContractError("label-gate schema/study mismatch")
    if gate.get("status") != "PASS" or gate.get("outcomes_loaded") is not False or gate.get("outcome_join_performed") is not False:
        raise ContractError("label gate is not a clean PASS")
    registration = _latest_registry_record(registry, HYPOTHESIS_ID)
    if registration is None:
        raise ContractError(f"fresh registry record absent: {HYPOTHESIS_ID}")
    if registration.get("state") != "probe":
        raise ContractError("fresh hypothesis latest registry state must be probe")
    prereg_hash = sha256_file(prereg)
    if registration.get("prereg_sha256") != prereg_hash:
        raise ContractError("registry prereg SHA does not bind supplied prereg")
    if registration.get("validation", {}).get("label_gate_report_sha256") != sha256_file(gate_report):
        raise ContractError("registry record does not bind exact PASS label-gate report")
    frozen = load_json(prereg)
    if frozen.get("schema_version") != "fvg_human_context_prereg.v2":
        raise ContractError("prereg schema mismatch")
    if frozen.get("hypothesis_id") != HYPOTHESIS_ID or frozen.get("status") != "FROZEN_PRE_OUTCOME":
        raise ContractError("prereg is not the exact frozen fresh hypothesis")
    if frozen.get("outcomes_seen_before_freeze") is not False:
        raise ContractError("prereg does not attest outcome blindness")
    bindings = frozen.get("bindings", {})
    gate_bind = gate.get("bindings", {})
    required = {
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "source_sha256": sha256_file(SOURCE_PATH),
        "internal_casebook_sha256": sha256_file(internal),
        "label_gate_report_sha256": sha256_file(gate_report),
        "reviewer_1_sha256": sha256_file(reviewer_1),
        "reviewer_2_sha256": sha256_file(reviewer_2),
        "analysis_plan_sha256": sha256_file(PLAN_PATH),
        "packet_manifest_sha256": gate_bind.get("packet_manifest_sha256"),
        "attestation_1_sha256": gate_bind.get("attestation_1_sha256"),
        "attestation_2_sha256": gate_bind.get("attestation_2_sha256"),
    }
    if any(not required[key] for key in ("packet_manifest_sha256", "attestation_1_sha256", "attestation_2_sha256")):
        raise ContractError("label gate lacks packet/attestation bindings")
    bad = {key: (bindings.get(key), wanted) for key, wanted in required.items() if bindings.get(key) != wanted}
    if bad:
        raise ContractError(f"prereg SHA bindings mismatch: {bad}")
    gate_expected = {
        "internal_casebook_sha256": required["internal_casebook_sha256"],
        "reviewer_1_sha256": required["reviewer_1_sha256"],
        "reviewer_2_sha256": required["reviewer_2_sha256"],
        "packet_manifest_sha256": required["packet_manifest_sha256"],
        "attestation_1_sha256": required["attestation_1_sha256"],
        "attestation_2_sha256": required["attestation_2_sha256"],
    }
    gate_bad = {key: (gate_bind.get(key), wanted) for key, wanted in gate_expected.items()
                if gate_bind.get(key) != wanted}
    if gate_bad:
        raise ContractError(f"label gate binding mismatch: {gate_bad}")
    return {"registration": registration, "prereg": frozen, "gate": gate, "bindings": required}


def _overlay(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return {r["case_id"]: r for r in csv.DictReader(fh)}


def _simulate_common(m5: pd.DataFrame, case: dict[str, Any]) -> dict[str, Any]:
    decision = pd.Timestamp(case["decision_time_utc"].replace("Z", ""))
    times = m5["time_utc"].to_numpy()
    i = int(np.searchsorted(times, np.datetime64(decision)))
    if i < 5 or i >= len(m5):
        raise ContractError(f"event outside M5 bars: {case['case_id']}")
    direction = int(case["direction"])
    entry = float(m5["open"].iloc[i])
    prior = m5.iloc[i - 5:i]
    stop = float(prior["low"].min() - 0.0001) if direction == 1 else float(prior["high"].max() + 0.0001)
    risk = (entry - stop) * direction
    if risk <= 0:
        raise ContractError(f"nonpositive structural risk: {case['case_id']}")
    target = entry + direction * 2.0 * risk
    server_decision = pd.Timestamp(case["decision_time_server"])
    close_hour = 12 if case["session"] == "LONDON" else 17
    session_close = server_decision.normalize() + pd.Timedelta(hours=close_hour)
    future = m5.iloc[i:i + 48]
    future = future[(future["time_server"] + pd.Timedelta(minutes=5)) <= session_close]
    if future.empty:
        future = m5.iloc[i:i + 1]
    exit_r = None
    reason = "TIME"
    exit_time = None
    for bar in future.itertuples(index=False):
        stop_hit = bar.low <= stop if direction == 1 else bar.high >= stop
        target_hit = bar.high >= target if direction == 1 else bar.low <= target
        if stop_hit:  # explicitly stop-first, including same-bar collision
            exit_r, reason, exit_time = -1.0, "STOP", bar.bar_close_utc
            break
        if target_hit:
            exit_r, reason, exit_time = 2.0, "TARGET", bar.bar_close_utc
            break
    if exit_r is None:
        bar = future.iloc[-1]
        exit_r = direction * (float(bar["close"]) - entry) / risk
        exit_time = bar["bar_close_utc"]
    return {"gross_r": float(exit_r), "entry": entry, "stop": stop, "target": target,
            "risk_pips": risk / 0.0001, "exit_reason": reason,
            "exit_time_utc": pd.Timestamp(exit_time).strftime("%Y-%m-%dT%H:%M:%SZ")}


def _native_consensus(a: dict[str, str], b: dict[str, str]) -> dict[str, Any] | None:
    if a.get("setup_label", "").upper() != "ACCEPT" or b.get("setup_label", "").upper() != "ACCEPT":
        return None
    order_a, order_b = a.get("native_order_type", "").upper(), b.get("native_order_type", "").upper()
    if order_a not in {"MARKET", "LIMIT"} or order_a != order_b:
        return None
    try:
        pa = [float(a[k]) for k in ("native_entry", "native_stop", "native_target")]
        pb = [float(b[k]) for k in ("native_entry", "native_stop", "native_target")]
    except (TypeError, ValueError):
        return None
    if any(abs(x - y) > 0.1 * 0.0001 for x, y in zip(pa, pb)):
        return None
    entry, stop, target = [(x + y) / 2 for x, y in zip(pa, pb)]
    if not ((stop < entry < target) or (target < entry < stop)):
        return None
    return {"order_type": order_a, "entry": entry, "stop": stop, "target": target,
            "direction": 1 if target > entry else -1}


def _simulate_native(m5: pd.DataFrame, case: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    decision = pd.Timestamp(case["decision_time_utc"].replace("Z", ""))
    i = int(np.searchsorted(m5["time_utc"].to_numpy(), np.datetime64(decision)))
    if i >= len(m5):
        raise ContractError(f"native event outside M5 bars: {case['case_id']}")
    direction = int(plan["direction"])
    declared_entry = float(plan["entry"])
    stop, target = float(plan["stop"]), float(plan["target"])
    if direction * (declared_entry - stop) <= 0 or direction * (target - declared_entry) <= 0:
        raise ContractError(f"invalid native geometry: {case['case_id']}")
    fill_index = i
    entry = float(m5["open"].iloc[i])
    if plan["order_type"] == "LIMIT":
        marketable = (direction == 1 and declared_entry >= entry) or (direction == -1 and declared_entry <= entry)
        if not marketable:
            fill_index = -1
            for idx in range(i, min(i + 6, len(m5))):
                if float(m5["low"].iloc[idx]) <= declared_entry <= float(m5["high"].iloc[idx]):
                    fill_index, entry = idx, declared_entry
                    break
        if fill_index < 0:
            return {"filled": False, "gross_r": 0.0, "risk_pips": None, "exit_reason": "LIMIT_EXPIRED_6_BARS"}
    risk = direction * (entry - stop)
    reward = direction * (target - entry)
    if risk <= 0 or reward <= 0:
        return {"filled": False, "gross_r": 0.0, "risk_pips": None, "exit_reason": "INVALID_GEOMETRY_AT_ACTUAL_FILL"}
    future = m5.iloc[fill_index:fill_index + 48]
    result_r = None
    reason = "TIME"
    for bar in future.itertuples(index=False):
        stop_hit = bar.low <= stop if direction == 1 else bar.high >= stop
        target_hit = bar.high >= target if direction == 1 else bar.low <= target
        if stop_hit:
            result_r, reason = -1.0, "STOP"
            break
        if target_hit:
            result_r, reason = direction * (target - entry) / risk, "TARGET"
            break
    if result_r is None:
        result_r = direction * (float(future.iloc[-1]["close"]) - entry) / risk
    return {"filled": True, "gross_r": float(result_r), "risk_pips": risk / 0.0001, "exit_reason": reason}


def _metrics(values: list[float], accepted: list[bool], weeks: float) -> dict[str, Any]:
    arr = np.asarray(values, float)
    trades = arr[np.asarray(accepted, bool)]
    gain = float(trades[trades > 0].sum())
    loss = float(-trades[trades < 0].sum())
    equity = np.cumsum(arr)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    dd = peaks[1:] - equity
    return {"opportunities": int(len(arr)), "accepted_trades": int(len(trades)),
            "mean_r_per_opportunity": float(arr.mean()) if len(arr) else 0.0,
            "accepted_expectancy_r": float(trades.mean()) if len(trades) else None,
            "profit_factor_r": gain / loss if loss > 0 else None,
            "net_r": float(arr.sum()), "max_drawdown_r": float(dd.max()) if len(dd) else 0.0,
            "trades_per_elapsed_week": len(trades) / weeks if weeks else None}


def _paired_week_bootstrap(frame: pd.DataFrame, seed: int = 26071801, reps: int = 20000) -> dict[str, Any]:
    grouped = frame.groupby("iso_week", sort=True)[["human_r", "ea_r"]].agg(["sum", "count"])
    human_sum = grouped[("human_r", "sum")].to_numpy(float)
    ea_sum = grouped[("ea_r", "sum")].to_numpy(float)
    counts = grouped[("human_r", "count")].to_numpy(float)
    if not len(counts):
        raise ContractError("no week blocks")
    rng = np.random.default_rng(seed)
    deltas = np.empty(reps)
    batch = 1000
    for start in range(0, reps, batch):
        n = min(batch, reps - start)
        idx = rng.integers(0, len(counts), size=(n, len(counts)))
        denom = counts[idx].sum(axis=1)
        deltas[start:start + n] = ((ea_sum[idx] - human_sum[idx]).sum(axis=1) / denom)
    return {"method": "paired_iso_week_block_bootstrap", "week_blocks": int(len(counts)), "replicates": reps,
            "delta_ea_minus_human_mean_r_per_opportunity": float(frame["ea_r"].mean() - frame["human_r"].mean()),
            "ci90": [float(np.quantile(deltas, 0.05)), float(np.quantile(deltas, 0.95))],
            "ci95": [float(np.quantile(deltas, 0.025)), float(np.quantile(deltas, 0.975))]}


def analyze(internal_path: Path, gate_report: Path, prereg: Path, reviewer_1: Path,
            reviewer_2: Path, registry: Path = REGISTRY_PATH) -> dict[str, Any]:
    auth = authorize_before_outcome_load(internal_path, gate_report, prereg, reviewer_1, reviewer_2, registry)
    # Outcome-bearing bars are not touched until the authorization above returns.
    m1 = load_m1_pre_holdout(start="2021-12-01")
    m5 = resample_ohlc(m1, 5)
    internal = load_json(internal_path)
    a, b = _overlay(reviewer_1), _overlay(reviewer_2)
    cases = [r for r in internal["cases"] if r["split"] == "evaluation"]
    rows = []
    for case in sorted(cases, key=lambda x: x["decision_time_utc"]):
        cid = case["case_id"]
        human_accept = a[cid]["setup_label"].upper() == b[cid]["setup_label"].upper() == "ACCEPT"
        ea_accept = bool(case["ea_accept"])
        common = _simulate_common(m5, case)
        native_plan = _native_consensus(a[cid], b[cid])
        native = _simulate_native(m5, case, native_plan) if native_plan is not None else {
            "filled": False, "gross_r": 0.0, "risk_pips": None, "exit_reason": "NO_MATCHED_NATIVE_CONSENSUS"}
        week = pd.Timestamp(case["decision_time_utc"].replace("Z", "")).strftime("%G-W%V")
        rows.append({"case_id": cid, "iso_week": week, "human_accept": human_accept, "ea_accept": ea_accept,
                     "gross_r": common["gross_r"], "risk_pips": common["risk_pips"],
                     "native_consensus": native_plan is not None, "native_filled": native["filled"],
                     "native_gross_r": native["gross_r"], "native_risk_pips": native["risk_pips"]})
    frame = pd.DataFrame(rows)
    tiers = {}
    for cost in (1.5, 2.25, 3.0):
        net = frame["gross_r"] - cost / frame["risk_pips"]
        frame["human_r"] = np.where(frame["human_accept"], net, 0.0)
        frame["ea_r"] = np.where(frame["ea_accept"], net, 0.0)
        weeks = (pd.Timestamp("2023-01-01") - pd.Timestamp("2022-01-01")) / pd.Timedelta(weeks=1)
        human = _metrics(frame["human_r"].tolist(), frame["human_accept"].tolist(), weeks)
        ea = _metrics(frame["ea_r"].tolist(), frame["ea_accept"].tolist(), weeks)
        bootstrap = _paired_week_bootstrap(frame)
        native_net = np.where(
            frame["native_filled"],
            frame["native_gross_r"] - cost / frame["native_risk_pips"].fillna(np.inf),
            0.0,
        )
        native = _metrics(native_net.tolist(), frame["native_filled"].tolist(), weeks)
        if bootstrap["ci95"][0] > 0 and ea["max_drawdown_r"] <= human["max_drawdown_r"]:
            verdict = "SUPERIOR"
        elif (bootstrap["ci95"][1] < 0 and human["accepted_expectancy_r"] is not None
              and ea["accepted_expectancy_r"] is not None
              and ea["accepted_expectancy_r"] <= human["accepted_expectancy_r"] - 0.05):
            verdict = "INFERIOR"
        else:
            verdict = "INCONCLUSIVE"
        tiers[str(cost)] = {"human_common": human, "ea_common": ea, "human_native": native,
                            "paired_bootstrap": bootstrap, "verdict": verdict}
    return {"schema_version": "fvg_locked_economic_readout.v1", "study_id": STUDY_ID,
            "hypothesis_id": HYPOTHESIS_ID, "authorization": "PASS_BEFORE_OUTCOME_LOAD",
            "analysis_plan_sha256": sha256_file(PLAN_PATH), "evaluation_cases": len(frame),
            "calibration_cases_used_in_economics": 0, "cost_status": "UNVERIFIED_PROXY",
            "promotion_eligible": False, "cost_tiers": tiers,
            "elapsed_evaluation_weeks": float((pd.Timestamp("2023-01-01") - pd.Timestamp("2022-01-01")) / pd.Timedelta(weeks=1)),
            "recorded_casebook_deviations": internal.get("selection_audit", {}).get("splits", {}).get("evaluation", {}).get("protocol_deviations", []),
            "native_track": {"status": "REPORTED_WHEN_MATCHED_REVIEWER_DECLARATIONS_EXIST",
                             "consensus_native_events": int(frame["native_consensus"].sum()),
                             "filled_native_events": int(frame["native_filled"].sum()), "limit_expiry_m5_bars": 6,
                             "same_bar_collision": "stop_first"},
            "bindings": auth["bindings"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--internal", type=Path, required=True)
    ap.add_argument("--label-gate", type=Path, required=True)
    ap.add_argument("--prereg", type=Path, required=True)
    ap.add_argument("--reviewer-1", type=Path, required=True)
    ap.add_argument("--reviewer-2", type=Path, required=True)
    ap.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = analyze(args.internal, args.label_gate, args.prereg, args.reviewer_1, args.reviewer_2, args.registry)
    except Exception as exc:
        print(json.dumps({"status": "ANALYSIS_NOT_WRITTEN_FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 2
    args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
