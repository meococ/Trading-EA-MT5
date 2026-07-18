#!/usr/bin/env python3
"""Frozen offline probe HYP-MR-REGIME-EURUSD-H1-001 — control vs challenger.

Cheap research screen per PROBE_PLAN_V2 (SHA-bound in the registry probe row).
Not Strategy Tester evidence, not promotion evidence: cost UNVERIFIED_PROXY,
promotion_eligible=false. Holdout 2023+ is never loaded (parquet read filter).
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import mr_probe_engine as eng

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
TRIALS = HERE / "trials" / "trial_log.jsonl"
PLAN_V2 = HERE / "HYP-MR-REGIME-EURUSD-H1-001_PROBE_PLAN_V2.md"
HYP = "HYP-MR-REGIME-EURUSD-H1-001"
HOLDOUT_START = pd.Timestamp("2023-01-01")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def load_sealed(name: str) -> pd.DataFrame:
    path = EVIDENCE / name
    df = pd.read_parquet(path, filters=[("time_utc", "<", HOLDOUT_START)])
    if len(df) and df["time_utc"].max() >= HOLDOUT_START:
        raise SystemExit("HOLDOUT SEAL VIOLATION")
    return df.sort_values("time_server").reset_index(drop=True)


def gate_table(ch: dict, ct: dict, combined_years: dict[str, float]) -> list[dict]:
    def g(name, passed, value, threshold):
        return {"gate": name, "pass": bool(passed), "value": value, "threshold": threshold}

    gates = []
    n_comb = ch["train"]["trades"] + ch["validation"]["trades"]
    gates.append(g("sample_min_trades", n_comb >= 300, n_comb, ">=300 train+validation"))

    econ_ok = all(
        (ch[s].get("pf_x1") or 0) >= 1.25 and ch[s].get("expectancy_r_x1", -9) >= 0.08
        for s in ("train", "validation")
    )
    gates.append(g("economics_pf_x1_and_expectancy", econ_ok,
                   {s: [ch[s].get("pf_x1"), ch[s].get("expectancy_r_x1")] for s in ("train", "validation")},
                   "PF@x1>=1.25 AND exp>=0.08R in both splits"))

    stress_ok = all(
        (ch[s].get("pf_x1_5") or 0) >= 1.25 and (ch[s].get("pf_x2") or 0) >= 1.00
        for s in ("train", "validation")
    )
    gates.append(g("stress_x1_5_x2", stress_ok,
                   {s: [ch[s].get("pf_x1_5"), ch[s].get("pf_x2")] for s in ("train", "validation")},
                   "PF@x1.5>=1.25 AND PF@x2>=1.00 in both splits"))

    pos = {y: v for y, v in combined_years.items() if v > 0}
    conc = (max(pos.values()) / sum(pos.values())) if pos else None
    gates.append(g("year_concentration", conc is not None and conc <= 0.40,
                   None if conc is None else round(conc, 4),
                   "max positive-year share of positive net R <= 40%"))

    margin_ok = all(
        ch[s].get("pf_x1") is not None and ct[s].get("pf_x1") is not None
        and ch[s]["pf_x1"] >= ct[s]["pf_x1"] + 0.10
        and ch[s].get("net_r_x1", -9e9) > ct[s].get("net_r_x1", 9e9)
        for s in ("train", "validation")
    )
    gates.append(g("incremental_value_vs_control", margin_ok,
                   {s: {"challenger": [ch[s].get("pf_x1"), ch[s].get("net_r_x1")],
                        "control": [ct[s].get("pf_x1"), ct[s].get("net_r_x1")]}
                    for s in ("train", "validation")},
                   "challenger PF@x1 >= control+0.10 AND net_R > control, both splits"))

    weeks_comb = ch["train"]["elapsed_weeks"] + ch["validation"]["elapsed_weeks"]
    tpw_comb = n_comb / weeks_comb if weeks_comb else 0.0
    gates.append(g("cadence_floor", tpw_comb >= 0.7, round(tpw_comb, 4),
                   ">=0.7 trades/elapsed-week combined (single-asset floor)"))
    gates.append(g("cadence_ceiling", tpw_comb <= 5.0, round(tpw_comb, 4),
                   "<=5 trades/elapsed-week combined"))
    return gates


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    h1 = load_sealed("EURUSD_H1_2015_now.parquet")
    h4 = load_sealed("EURUSD_H4_2015_now.parquet")

    feats = eng.compute_features(h1, h4)
    results: dict[str, dict] = {}
    all_trades: list[tuple[str, eng.Trade]] = []
    for arm in ("control", "challenger"):
        trades = eng.run_arm(feats, arm)
        results[arm] = {s: eng.metrics_for(trades, feats, s) for s in ("train", "validation")}
        all_trades.extend((arm, t) for t in trades)

    # combined challenger by-year for concentration gate
    combined_years: dict[str, float] = {}
    for s in ("train", "validation"):
        for y, v in results["challenger"][s].get("by_year_net_r_x1", {}).items():
            combined_years[y] = combined_years.get(y, 0.0) + v

    gates = gate_table(results["challenger"], results["control"], combined_years)
    all_pass = all(x["pass"] for x in gates)
    n_comb = results["challenger"]["train"]["trades"] + results["challenger"]["validation"]["trades"]
    econ_gates_pass = all(x["pass"] for x in gates if x["gate"] in
                          ("economics_pf_x1_and_expectancy", "stress_x1_5_x2",
                           "year_concentration", "incremental_value_vs_control"))
    if all_pass:
        verdict = "SURVIVE_CONTINUE_TO_PREREG"
    elif 200 <= n_comb < 300 and econ_gates_pass:
        verdict = "PARK_SAMPLE_AMBIGUOUS"
    else:
        verdict = "KILL_AT_OFFLINE_PROBE"

    # ---- trades ledger ----
    ledger = EVIDENCE / f"{ts}_HYP_MR_REGIME_EURUSD_H1_001_TRADES.csv"
    with ledger.open("w", encoding="utf-8", newline="") as fh:
        wtr = csv.writer(fh, lineterminator="\n")
        wtr.writerow([
            "arm", "split", "direction", "entry_time_server", "entry_time_utc",
            "exit_time_server", "exit_reason", "entry", "sl_initial", "tp",
            "tp_binding", "r_pips", "hl_e", "ts_bars", "swap_events",
            "swap_weighted", "gross_r", "cost_pips_x1", "net_r_x1", "net_r_x1_5",
            "net_r_x2", "feature_time_utc", "decision_time_utc", "execution_time_utc",
        ])
        for arm, t in all_trades:
            e_utc = feats["time_utc"].iloc[t.entry_idx]
            wtr.writerow([
                arm, eng.split_of(e_utc), t.direction,
                t.times["entry_time_server"], str(e_utc),
                t.times["exit_time_server"], t.exit_reason,
                f"{t.entry:.5f}", f"{t.sl:.5f}", f"{t.tp:.5f}", t.tp_binding,
                f"{t.r_pips():.1f}", f"{t.hl_e:.2f}", t.ts_bars,
                t.swap_events, t.swap_weighted, f"{t.gross_r:.4f}",
                f"{t.cost_pips(1.0):.2f}", f"{t.net_r(1.0):.4f}",
                f"{t.net_r(1.5):.4f}", f"{t.net_r(2.0):.4f}",
                t.times["feature_time_utc"], t.times["decision_time_utc"],
                t.times["execution_time_utc"],
            ])

    # ---- trial log (every evaluation of the frozen config) ----
    TRIALS.parent.mkdir(parents=True, exist_ok=True)
    with TRIALS.open("a", encoding="utf-8", newline="\n") as fh:
        for arm in ("control", "challenger"):
            fh.write(json.dumps({
                "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "hypothesis_id": HYP,
                "engine": eng.ENGINE_VERSION,
                "prereg_sha256": sha256_file(PLAN_V2),
                "arm": arm,
                "config": "FROZEN_DEFAULTS_PROBE_PLAN_V2",
                "trades_train": results[arm]["train"]["trades"],
                "trades_validation": results[arm]["validation"]["trades"],
                "pf_x1_train": results[arm]["train"].get("pf_x1"),
                "pf_x1_validation": results[arm]["validation"].get("pf_x1"),
            }, ensure_ascii=True) + "\n")

    # ---- probe artifact ----
    artifact = {
        "schema_version": "mr_regime_gated_offline_probe.v1",
        "hypothesis_id": HYP,
        "ea_name": "EA_HybridRegimeMR",
        "engine_version": eng.ENGINE_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prereg_path": "03. EA Developer/EA_HybridRegimeMR/research/HYP-MR-REGIME-EURUSD-H1-001_PROBE_PLAN_V2.md",
        "prereg_sha256": sha256_file(PLAN_V2),
        "inputs": {
            "h1_parquet_sha256": sha256_file(EVIDENCE / "EURUSD_H1_2015_now.parquet"),
            "h4_parquet_sha256": sha256_file(EVIDENCE / "EURUSD_H4_2015_now.parquet"),
            "h1_bars_loaded": int(len(h1)),
            "h4_bars_loaded": int(len(h4)),
            "holdout_bars_loaded": 0,
            "last_bar_utc_loaded": str(h1["time_utc"].max()),
        },
        "cost_status": "UNVERIFIED_PROXY",
        "cost_model": "1.5 pips RT x1 + 0.8 pip per weighted rollover (Wed x3, Fri->Mon=1); stress x1.5/x2",
        "risk_pct": eng.RISK_PCT,
        "results": results,
        "gates": gates,
        "verdict": verdict,
        "promotion_eligible": False,
        "trade_ledger": ledger.name,
    }
    out = EVIDENCE / f"{ts}_HYP_MR_REGIME_EURUSD_H1_001_PROBE.json"
    out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"results": results, "gates": gates, "verdict": verdict}, indent=2))
    print(f"ARTIFACT -> {out}")
    print(f"ARTIFACT_SHA256 {sha256_file(out)}")
    print(f"LEDGER_SHA256 {sha256_file(ledger)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
