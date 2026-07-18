#!/usr/bin/env python3
"""HYP-MR-GRID-EURUSD-H1-002 — pre-registered exhaustive grid falsification sweep.

Owner-directed (2026-07-17) closure instrument for the regime-gated detrended-z
MR family on EURUSD H1. Design frozen in HYP-MR-GRID-EURUSD-H1-002_GRID_PLAN.md
(SHA-bound in the registry) after adversarial legality + statistics review:
- Stage 1: full cross of {W,Z,K_sl,TP_cap,k_ts,trailing} at session [7,16),
  SIX arms per cell (control, gated ensemble, 4 single gates) = full within-cell
  gate-family coverage. 1350 cells x 6 arms = 8100 simulations.
- Stage 2 (conditional, only for cells whose ANY arm passes the routing filter
  combined gross PF >= 1.25 with n >= 100): 10 remaining gate subsets, 8
  gate-threshold variants, 4 session-shift arms.
- Verdict on the POOLED 2015-2022 series, deflated by DSR with N = ALL
  simulations executed in the campaign. Default verdict KILL_FAMILY_EXHAUSTIVE;
  best case is FLAG_FOR_HOLDOUT_PREREG_REQUIRED (screened-at-most; opening the
  sealed 2023+ holdout needs a fresh Owner-approved prereg).
Research screen only: cost UNVERIFIED_PROXY, promotion_eligible=false.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import multiprocessing as mp
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import mr_grid_engine as eng
from mr_dsr import dsr, expected_max_sharpe

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
CACHE = HERE / "grid_cache"
TRIALS = HERE / "trials" / "trial_log.jsonl"
HYP = "HYP-MR-GRID-EURUSD-H1-002"
HOLDOUT_START = pd.Timestamp("2023-01-01")

# ---------------- FROZEN GRID (mirrors GRID_PLAN; no post-outcome edits) -----
SESSION_S1 = (7, 16)
AXES = {
    "W": [60, 80, 100, 125, 150],
    "Z": [1.6, 1.8, 2.0, 2.2, 2.4],
    "K_SL": [1.5, 2.0, 2.5],
    "TP_CAP": [1.2, 1.5, 1.8],
    "K_TS": [1.5, 2.0, 3.0],
    "TRAILING": [True, False],
}
D_ADX1, D_ADX4, D_ATR, D_HL = 23.0, 28.0, (25.0, 75.0), (4.0, 48.0)
DEFAULT_GATES = eng.GateSpec(D_ADX1, D_ADX4, D_ATR, D_HL)
STAGE1_ARMS: list[tuple[str, eng.GateSpec]] = [
    ("control", eng.GateSpec()),
    ("gated", DEFAULT_GATES),
    ("g_adx1", eng.GateSpec(adx_h1=D_ADX1)),
    ("g_adx4", eng.GateSpec(adx_h4=D_ADX4)),
    ("g_atr", eng.GateSpec(atr_band=D_ATR)),
    ("g_hl", eng.GateSpec(hl_band=D_HL)),
]
# Stage-2 arms (per routing-passer cell): remaining 10 of the 2^4 subsets ...
_S2_SUBSETS = [
    ("s_1100", eng.GateSpec(D_ADX1, D_ADX4, None, None)),
    ("s_1010", eng.GateSpec(D_ADX1, None, D_ATR, None)),
    ("s_1001", eng.GateSpec(D_ADX1, None, None, D_HL)),
    ("s_0110", eng.GateSpec(None, D_ADX4, D_ATR, None)),
    ("s_0101", eng.GateSpec(None, D_ADX4, None, D_HL)),
    ("s_0011", eng.GateSpec(None, None, D_ATR, D_HL)),
    ("s_1110", eng.GateSpec(D_ADX1, D_ADX4, D_ATR, None)),
    ("s_1101", eng.GateSpec(D_ADX1, D_ADX4, None, D_HL)),
    ("s_1011", eng.GateSpec(D_ADX1, None, D_ATR, D_HL)),
    ("s_0111", eng.GateSpec(None, D_ADX4, D_ATR, D_HL)),
]
# ... 8 single-axis threshold variants of the full ensemble ...
_S2_THRESH = [
    ("t_adx1_20", eng.GateSpec(20.0, D_ADX4, D_ATR, D_HL)),
    ("t_adx1_26", eng.GateSpec(26.0, D_ADX4, D_ATR, D_HL)),
    ("t_adx4_24", eng.GateSpec(D_ADX1, 24.0, D_ATR, D_HL)),
    ("t_adx4_32", eng.GateSpec(D_ADX1, 32.0, D_ATR, D_HL)),
    ("t_atr_wide", eng.GateSpec(D_ADX1, D_ADX4, (15.0, 85.0), D_HL)),
    ("t_atr_narrow", eng.GateSpec(D_ADX1, D_ADX4, (35.0, 65.0), D_HL)),
    ("t_hl_tight", eng.GateSpec(D_ADX1, D_ADX4, D_ATR, (4.0, 24.0))),
    ("t_hl_loose", eng.GateSpec(D_ADX1, D_ADX4, D_ATR, (8.0, 48.0))),
]
# ... and 4 session-shift arms (control + gated at each shifted window).
S2_SESSIONS = [(6, 15), (8, 17)]
ROUTING_GROSS_PF = 1.25
ROUTING_MIN_N = 100
MIN_N_COMBINED = 300
MIN_N_TRAIN, MIN_N_VAL = 150, 50
LOO_PF_FLOOR = 1.10
TOP1_SHARE_CAP = 0.20
MIN_POS_YEARS = 6           # of 8 (2015-2022)
DSR_FLOOR = 0.95
# ------------------------------------------------------------------------------

_ARR: dict[int, dict[str, np.ndarray]] = {}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _init_worker(cache_dir: str, ws: list[int]) -> None:
    global _ARR
    for w in ws:
        with np.load(Path(cache_dir) / f"W{w}.npz", allow_pickle=False) as z:
            _ARR[w] = {k: z[k] for k in z.files}


def _cfg(cell, session=SESSION_S1, gates=DEFAULT_GATES) -> eng.CellConfig:
    w, zt, ksl, tpc, kts, trail = cell
    cid = f"W{w}_Z{zt}_SL{ksl}_TP{tpc}_TS{kts}_TR{int(trail)}_S{session[0]}{session[1]}"
    return eng.CellConfig(cell_id=cid, W=w, z_entry=zt, k_sl=ksl, tp_cap_r=tpc,
                          k_ts=kts, session=session, trailing=trail, gates=gates)


def _eval_stage1(cell: tuple) -> dict:
    arrays = _ARR[cell[0]]
    rec: dict = {"cell": list(cell), "arms": {}}
    for arm_name, gates in STAGE1_ARMS:
        cfg = _cfg(cell, gates=gates)
        trades = eng.run_cell_arm(arrays, cfg, gated=(arm_name != "control"))
        rec["arms"][arm_name] = eng.summarize_arm(trades)
    rec["cell_id"] = _cfg(cell).cell_id
    return rec


def _eval_stage2(payload: tuple) -> dict:
    cell, arm_name, session, gates_tuple = payload
    gates = eng.GateSpec(*gates_tuple)
    arrays = _ARR[cell[0]]
    cfg = _cfg(cell, session=session, gates=gates)
    trades = eng.run_cell_arm(arrays, cfg, gated=(arm_name not in ("control", "s2_control_s")))
    return {"cell": list(cell), "cell_id": cfg.cell_id, "arm": arm_name,
            "session": list(session), "summary": eng.summarize_arm(trades)}


def prepare_cache(ws: list[int]) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    h1 = pd.read_parquet(EVIDENCE / "EURUSD_H1_2015_now.parquet",
                         filters=[("time_utc", "<", HOLDOUT_START)]).sort_values("time_server").reset_index(drop=True)
    h4 = pd.read_parquet(EVIDENCE / "EURUSD_H4_2015_now.parquet",
                         filters=[("time_utc", "<", HOLDOUT_START)]).sort_values("time_server").reset_index(drop=True)
    if h1["time_utc"].max() >= HOLDOUT_START or h4["time_utc"].max() >= HOLDOUT_START:
        raise SystemExit("HOLDOUT SEAL VIOLATION")
    base = eng.precompute_base(h1, h4)
    for w in ws:
        out = CACHE / f"W{w}.npz"
        if out.exists():
            continue
        feats = eng.add_w_features(base, w)
        np.savez_compressed(out, **eng.frame_to_arrays(feats))
        print(f"cache W{w}", flush=True)
    return {"h1_bars": int(len(h1)), "h4_bars": int(len(h4)),
            "last_bar_utc": str(h1["time_utc"].max()),
            "h1_sha256": sha256_file(EVIDENCE / "EURUSD_H1_2015_now.parquet"),
            "h4_sha256": sha256_file(EVIDENCE / "EURUSD_H4_2015_now.parquet")}


def _arm_conjunction(co: dict) -> dict:
    """Frozen survivor conjunction on the POOLED series (GRID_PLAN section 6)."""
    years = co.get("by_year_net_r_x1", {})
    pos_years = sum(1 for v in years.values() if v > 0)
    pos = {y: v for y, v in years.items() if v > 0}
    conc = (max(pos.values()) / sum(pos.values())) if pos else None
    checks = {
        "n_combined": bool(co.get("n", 0) >= MIN_N_COMBINED),
        "gross_pf": bool((co.get("gross_pf") or 0) >= 1.25),
        "pf_x1": bool((co.get("pf_x1") or 0) >= 1.25),
        "exp_x1": bool(co.get("exp_x1", -9) >= 0.08),
        "pf_x1_5": bool((co.get("pf_x1_5") or 0) >= 1.25),
        "pf_x2": bool((co.get("pf_x2") or 0) >= 1.00),
        "pos_years": bool(pos_years >= MIN_POS_YEARS),
        "concentration": bool(conc is not None and conc <= 0.40),
        "loo_pf": bool((co.get("loo_pf_x1") or 0) >= LOO_PF_FLOOR),
        "loo_exp": bool(co.get("loo_exp_x1", -9) >= 0.0),
        "top1_share": bool(co.get("top1_win_share") is not None and co["top1_win_share"] <= TOP1_SHARE_CAP),
    }
    return {"pass": all(checks.values()), "checks": checks}


def main() -> int:
    t0 = time.time()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    ws = AXES["W"]
    data_meta = prepare_cache(ws)
    plan_sha = sha256_file(HERE / "HYP-MR-GRID-EURUSD-H1-002_GRID_PLAN.md")

    cells = list(itertools.product(AXES["W"], AXES["Z"], AXES["K_SL"], AXES["TP_CAP"],
                                   AXES["K_TS"], AXES["TRAILING"]))
    print(f"stage1 cells={len(cells)} arms={len(cells) * len(STAGE1_ARMS)}", flush=True)

    workers = max(2, (os.cpu_count() or 8) - 2)
    stage1: list[dict] = []
    with mp.Pool(processes=workers, initializer=_init_worker, initargs=(str(CACHE), ws)) as pool:
        for k, rec in enumerate(pool.imap_unordered(_eval_stage1, cells, chunksize=4)):
            stage1.append(rec)
            if (k + 1) % 200 == 0:
                print(f"S1 {k + 1}/{len(cells)}  {time.time() - t0:.0f}s", flush=True)

    # ---- routing filter for Stage 2 ----
    def routing_pass(arm: dict) -> bool:
        co = arm["combined"]
        return (co.get("gross_pf") or 0) >= ROUTING_GROSS_PF and co.get("n", 0) >= ROUTING_MIN_N

    s2_cells = [tuple(rec["cell"]) for rec in stage1
                if any(routing_pass(a) for a in rec["arms"].values())]
    s2_payloads: list[tuple] = []
    for cell in s2_cells:
        for name, g in _S2_SUBSETS + _S2_THRESH:
            s2_payloads.append((cell, name, SESSION_S1, (g.adx_h1, g.adx_h4, g.atr_band, g.hl_band)))
        for sess in S2_SESSIONS:
            s2_payloads.append((cell, "s2_control_s", sess, (None, None, None, None)))
            s2_payloads.append((cell, "s2_gated_s", sess,
                                (D_ADX1, D_ADX4, D_ATR, D_HL)))
    stage2: list[dict] = []
    if s2_payloads:
        print(f"stage2 cells={len(s2_cells)} arms={len(s2_payloads)}", flush=True)
        with mp.Pool(processes=workers, initializer=_init_worker, initargs=(str(CACHE), ws)) as pool:
            stage2 = list(pool.imap_unordered(_eval_stage2, s2_payloads, chunksize=4))

    # ---- flatten all evaluations (trial universe) ----
    all_evals: list[dict] = []
    for rec in stage1:
        for arm_name, s in rec["arms"].items():
            all_evals.append({"stage": 1, "cell_id": rec["cell_id"], "arm": arm_name,
                              "session": list(SESSION_S1), "summary": s})
    for r in stage2:
        all_evals.append({"stage": 2, "cell_id": r["cell_id"], "arm": r["arm"],
                          "session": r["session"], "summary": r["summary"]})
    n_trials = len(all_evals)
    srs = [e["summary"]["combined"].get("sr_trade") for e in all_evals]
    srs = [s for s in srs if s is not None]
    var_sr = float(np.var(srs, ddof=1)) if len(srs) > 2 else 0.0

    # ---- verdict: conjunction + DSR on pooled series ----
    passers: list[dict] = []
    best = {"dsr": 0.0, "cell_id": None, "arm": None}
    for e in all_evals:
        co = e["summary"]["combined"]
        conj = _arm_conjunction(co)
        d = 0.0
        if all(co.get(k) is not None for k in ("sr_trade", "skew", "kurt")):
            d = dsr(co["sr_trade"], co["n"], co["skew"], co["kurt"], var_sr, n_trials)
        if d > best["dsr"]:
            best = {"dsr": round(d, 4), "cell_id": e["cell_id"], "arm": e["arm"],
                    "stage": e["stage"], "combined": co, "conjunction": conj}
        if conj["pass"] and d >= DSR_FLOOR:
            passers.append({"cell_id": e["cell_id"], "arm": e["arm"], "stage": e["stage"],
                            "dsr": round(d, 4), "combined": co})

    verdict = ("FLAG_FOR_HOLDOUT_PREREG_REQUIRED" if passers
               else "KILL_FAMILY_EXHAUSTIVE_AT_OFFLINE_GRID")

    # ---- persist: raw results + trial log (one row per simulation) ----
    raw_path = EVIDENCE / f"{ts}_HYP_MR_GRID_002_RESULTS.jsonl"
    with raw_path.open("w", encoding="utf-8", newline="\n") as fh:
        for e in all_evals:
            fh.write(json.dumps(e, ensure_ascii=True) + "\n")
    TRIALS.parent.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with TRIALS.open("a", encoding="utf-8", newline="\n") as fh:
        for i, e in enumerate(all_evals):
            co = e["summary"]["combined"]
            fh.write(json.dumps({
                "ts_utc": now_iso, "hypothesis_id": HYP, "trial_id": i + 1,
                "engine": eng.ENGINE_VERSION, "prereg_sha256": plan_sha,
                "stage": e["stage"], "cell_id": e["cell_id"], "arm": e["arm"],
                "session": e["session"], "n": co.get("n", 0),
                "gross_pf": co.get("gross_pf"), "pf_x1": co.get("pf_x1"),
                "pf_x1_5": co.get("pf_x1_5"), "pf_x2": co.get("pf_x2"),
                "exp_x1": co.get("exp_x1"), "sr_trade": co.get("sr_trade"),
                "skew": co.get("skew"), "kurt": co.get("kurt"),
                "loo_pf_x1": co.get("loo_pf_x1"), "top1_win_share": co.get("top1_win_share"),
            }, ensure_ascii=True) + "\n")

    artifact = {
        "schema_version": "mr_grid_falsification_sweep.v2",
        "hypothesis_id": HYP, "ea_name": "EA_HybridRegimeMR",
        "engine_version": eng.ENGINE_VERSION,
        "generated_at_utc": now_iso,
        "prereg_sha256": plan_sha,
        "stage1": {"cells": len(cells), "arms_per_cell": [a for a, _ in STAGE1_ARMS],
                   "session": list(SESSION_S1)},
        "stage2": {"routing_rule": f"combined gross PF >= {ROUTING_GROSS_PF} and n >= {ROUTING_MIN_N} in any Stage-1 arm",
                   "cells_routed": len(s2_cells), "arms_evaluated": len(s2_payloads)},
        "total_evaluations": n_trials,
        "inputs": data_meta | {"holdout_bars_loaded": 0},
        "cost_status": "UNVERIFIED_PROXY",
        "trial_accounting": {
            "n_trials": n_trials, "sr_population": len(srs),
            "var_sr_across_trials": round(var_sr, 6),
            "expected_max_sr": round(expected_max_sharpe(var_sr, n_trials), 5),
            "dsr_floor": DSR_FLOOR,
            "n_convention": "every executed simulation (config x arm x session), stages 1+2, incl. controls and failures; cost tiers are NOT separate trials",
        },
        "best_deflated": best,
        "flag_passers": passers,
        "verdict": verdict,
        "promotion_eligible": False,
        "results_file": raw_path.name,
        "results_sha256": sha256_file(raw_path),
        "runtime_seconds": round(time.time() - t0, 1),
    }
    out = EVIDENCE / f"{ts}_HYP_MR_GRID_002_SWEEP.json"
    out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: artifact[k] for k in ("stage1", "stage2", "total_evaluations",
                                               "trial_accounting", "best_deflated", "verdict")},
                     indent=2, default=str))
    print(f"ARTIFACT -> {out}")
    print(f"ARTIFACT_SHA256 {sha256_file(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
