#!/usr/bin/env python3
"""Stage 1 - EA_ICTVisualEdge / HYP-ICTVIS-EURUSD-M5-001.

Build the decision-time candidate table for the OPEN visual feature-discovery
probe. Three responsibilities, each kept anti-peek and sealed:

  1. Closed-bar M1 -> M5 / M15 resampler (label=left, closed=left). A bar with
     open time T covers [T, T+step); it is decision-available only at its CLOSE
     time T+step. Candidate detection at bar i uses ONLY bars 0..i (all closed).
  2. GENEROUS (high-recall) sweep-candidate detector - deliberately loose so we
     do NOT pre-collapse cadence (the failure mode of every tightened ICT lane).
     No session gate, no structural-invalidation filter, both directions.
  3. Forward-R outcome label via a stop-first, cost-aware simulator (ported from
     drat_onnx_ict_probe.simulate_exit). Outcomes are computed but SEALED away
     from Stage-2 visual feature design: only asof (decision-time) fields feed
     the eye; the R label is used mechanically at probe time.

HOLDOUT (2023+) is sealed at READ time and never loaded here. Design 2015-2018,
train 2019-2021, val 2022 are all < 2023 so the full Stage-1 corpus stays
pre-holdout. Nothing here tunes on outcomes; this only manufactures the corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
M1_PATH = WORKSPACE / "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet"
HOLDOUT_START = pd.Timestamp("2023-01-01", tz=None)
PIP = 0.0001

# --- frozen Stage-1 corpus params (generous / high-recall; NOT strategy tuning) ---
STEP_MIN = {"M5": 5, "M15": 15}
SWEEP_LOOKBACK = 12          # generous small lookback -> high recall
STOP_BUFFER_PIP = 2.0        # beyond swept extreme
TARGET_R = 2.0               # label geometry (fixed, declared)
MAX_HOLD_BARS = 48           # on the decision TF (M5: 4h; wide enough to resolve)
COST_R_LABEL = 0.0           # labels are gross; cost applied at probe time

SPLIT_BOUNDS = {
    "DESIGN": ("2015-01-01", "2018-12-31"),
    "TRAIN":  ("2019-01-01", "2021-12-31"),
    "VAL":    ("2022-01-01", "2022-12-31"),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def load_m1_sealed() -> tuple[pd.DataFrame, dict]:
    """Load M1 strictly before the sealed holdout; return (df, seal receipt)."""
    df = pd.read_parquet(
        M1_PATH,
        columns=["time_utc", "open", "high", "low", "close", "tick_volume", "spread"],
        filters=[("time_utc", "<", HOLDOUT_START)],
    )
    df["time_utc"] = pd.to_datetime(df["time_utc"])
    if len(df) and df["time_utc"].max() >= HOLDOUT_START:
        raise RuntimeError("HOLDOUT SEAL VIOLATION: M1 contains bars >= holdout_start")
    df = df.sort_values("time_utc").reset_index(drop=True)
    receipt = {
        "bars_path": str(M1_PATH.relative_to(WORKSPACE).as_posix()),
        "bars_sha256": sha256_file(M1_PATH),
        "holdout_start": str(HOLDOUT_START),
        "m1_bars_loaded": int(len(df)),
        "holdout_bars_loaded": 0,
        "last_m1_loaded": str(df["time_utc"].max()) if len(df) else None,
    }
    return df, receipt


def resample_closed(m1: pd.DataFrame, step_min: int) -> pd.DataFrame:
    """Closed-bar OHLC resample. Bar open time = left edge; decision (close)
    time = open + step. Empty bins (weekend gaps) are dropped."""
    rule = f"{step_min}min"
    idx = m1.set_index("time_utc")
    agg = idx.resample(rule, label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        spread=("spread", "mean"),
        m1_count=("open", "size"),
    )
    agg = agg[agg["m1_count"] > 0].reset_index()
    agg = agg.rename(columns={"time_utc": "open_time_utc"})
    agg["decision_time_utc"] = agg["open_time_utc"] + pd.Timedelta(minutes=step_min)
    return agg.reset_index(drop=True)


def detect_generous_sweeps(bars: pd.DataFrame) -> pd.DataFrame:
    """High-recall sweep candidates on closed bars. A LONG candidate: bar i
    prints a low below the prior-N low but CLOSES back above it. SHORT mirror.
    No session/structure filter (recall first). Entry decided at bar i close."""
    low = bars["low"].to_numpy()
    high = bars["high"].to_numpy()
    close = bars["close"].to_numpy()
    n = len(bars)
    rows: list[dict] = []
    for i in range(SWEEP_LOOKBACK, n):
        prior_low = low[i - SWEEP_LOOKBACK:i].min()
        prior_high = high[i - SWEEP_LOOKBACK:i].max()
        # LONG: swept prior low, reclaimed
        if low[i] < prior_low and close[i] > prior_low:
            rows.append({"bar_i": i, "direction": 1, "swept_extreme": float(low[i])})
        # SHORT: swept prior high, reclaimed
        if high[i] > prior_high and close[i] < prior_high:
            rows.append({"bar_i": i, "direction": -1, "swept_extreme": float(high[i])})
    return pd.DataFrame(rows)


def simulate_exit(bars: pd.DataFrame, entry_i: int, direction: int, entry: float,
                  stop: float, target: float, max_hold: int, cost_r: float
                  ) -> tuple[int, float, str]:
    """Stop-first, cost-aware forward simulation (ported, conservative:
    ambiguous same-bar SL+TP resolves to SL)."""
    risk = abs(entry - stop)
    if not math.isfinite(risk) or risk <= 0.0:
        return entry_i, -1.0 - cost_r, "INVALID_RISK"
    last = min(len(bars) - 1, entry_i + max_hold - 1)
    lo = bars["low"].to_numpy()
    hi = bars["high"].to_numpy()
    cl = bars["close"].to_numpy()
    for i in range(entry_i, last + 1):
        stop_hit = lo[i] <= stop if direction > 0 else hi[i] >= stop
        target_hit = hi[i] >= target if direction > 0 else lo[i] <= target
        if stop_hit and target_hit:
            return i, -1.0 - cost_r, "BOTH_SL_FIRST"
        if stop_hit:
            return i, -1.0 - cost_r, "SL"
        if target_hit:
            return i, abs(target - entry) / risk - cost_r, "TP"
    r_value = direction * (cl[last] - entry) / risk - cost_r
    return last, float(r_value), "TIME"


def label_forward_r(bars: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    """Attach SEALED forward-R outcome to each candidate. Entry = decision bar
    close; stop = swept extreme +/- buffer; target = entry + dir*TARGET_R*risk.
    Entry executes on the NEXT bar (i+1) to honour closed-bar decision."""
    out = []
    close = bars["close"].to_numpy()
    for _, c in cand.iterrows():
        i = int(c["bar_i"])
        d = int(c["direction"])
        entry = float(close[i])
        stop = c["swept_extreme"] - d * STOP_BUFFER_PIP * PIP
        risk = abs(entry - stop)
        if risk <= 0:
            continue
        target = entry + d * TARGET_R * risk
        entry_i = i + 1
        if entry_i >= len(bars):
            continue
        exit_i, r, reason = simulate_exit(bars, entry_i, d, entry, stop, target,
                                          MAX_HOLD_BARS, COST_R_LABEL)
        out.append({
            "bar_i": i,
            "entry_i": entry_i,
            "decision_time_utc": bars["decision_time_utc"].iloc[i],
            "entry_time_utc": bars["open_time_utc"].iloc[entry_i],
            "direction": d,
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_pip": risk / PIP,
            "exit_i": exit_i,
            "exit_time_utc": bars["open_time_utc"].iloc[exit_i],
            "exit_reason": reason,
            "r_gross": r,
            "win": 1 if r > 0 else 0,
        })
    return pd.DataFrame(out)


def tag_split(ts: pd.Series) -> pd.Series:
    t = pd.to_datetime(ts)
    out = pd.Series(["NONE"] * len(t), index=t.index, dtype=object)
    for name, (lo, hi) in SPLIT_BOUNDS.items():
        mask = (t >= pd.Timestamp(lo)) & (t < pd.Timestamp(hi) + pd.Timedelta(days=1))
        out[mask] = name
    return out


def build_tf(m1: pd.DataFrame, tf: str, outdir: Path) -> dict:
    step = STEP_MIN[tf]
    bars = resample_closed(m1, step)
    cand = detect_generous_sweeps(bars)
    labelled = label_forward_r(bars, cand)
    labelled["split"] = tag_split(labelled["decision_time_utc"]).values
    labelled = labelled[labelled["split"] != "NONE"].reset_index(drop=True)

    bars_path = outdir / f"bars_{tf}.parquet"
    cand_path = outdir / f"candidates_{tf}.parquet"
    bars.to_parquet(bars_path, index=False)
    labelled.to_parquet(cand_path, index=False)

    summary = {"n_bars": int(len(bars)), "n_candidates_raw": int(len(cand)),
               "n_candidates_split": int(len(labelled))}
    for sp in SPLIT_BOUNDS:
        sub = labelled[labelled["split"] == sp]
        wk = (pd.Timestamp(SPLIT_BOUNDS[sp][1]) - pd.Timestamp(SPLIT_BOUNDS[sp][0])).days / 7.0 + 1 / 7.0
        summary[sp] = {
            "n": int(len(sub)),
            "per_week": round(len(sub) / wk, 3),
            "win_rate": round(float(sub["win"].mean()), 4) if len(sub) else None,
            "mean_r_gross": round(float(sub["r_gross"].mean()), 4) if len(sub) else None,
        }
    summary["bars_path"] = str(bars_path.relative_to(WORKSPACE).as_posix())
    summary["bars_sha256"] = sha256_file(bars_path)
    summary["candidates_path"] = str(cand_path.relative_to(WORKSPACE).as_posix())
    summary["candidates_sha256"] = sha256_file(cand_path)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(HERE / "evidence" / "stage1"))
    args = ap.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    m1, seal = load_m1_sealed()
    manifest = {
        "hypothesis_id": "HYP-ICTVIS-EURUSD-M5-001",
        "stage": 1,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seal": seal,
        "params": {
            "sweep_lookback": SWEEP_LOOKBACK, "stop_buffer_pip": STOP_BUFFER_PIP,
            "target_r": TARGET_R, "max_hold_bars": MAX_HOLD_BARS,
            "cost_r_label": COST_R_LABEL, "split_bounds": SPLIT_BOUNDS,
        },
        "timeframes": {},
    }
    for tf in ("M5", "M15"):
        manifest["timeframes"][tf] = build_tf(m1, tf, outdir)

    man_path = outdir / "stage1_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    print(json.dumps(manifest["timeframes"], indent=2, default=str))
    print(f"\nmanifest -> {man_path.relative_to(WORKSPACE).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
