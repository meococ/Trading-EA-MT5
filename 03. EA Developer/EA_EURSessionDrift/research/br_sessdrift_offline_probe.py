#!/usr/bin/env python3
"""Frozen offline probe HYP-BR-SESSDRIFT-EURUSD-H1-001 (Breedon-Ranaldo drift).

Unconditional time-of-day drift: daily SHORT EURUSD 07:00->11:00 UTC and LONG
13:00->17:00 UTC, per the frozen PROBE_PLAN. Two simulated arms only
(book_nostop primary, book_sl secondary); short/long figures are partitions.
Research screen: cost UNVERIFIED_PROXY, promotion_eligible=false, holdout
2023+ never loaded.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
TRIALS = HERE / "trials" / "trial_log.jsonl"
PLAN = HERE / "HYP-BR-SESSDRIFT-EURUSD-H1-001_PROBE_PLAN.md"
H1_PARQUET = HERE.parents[1] / "EA_HybridRegimeMR" / "research" / "evidence" / "EURUSD_H1_2015_now.parquet"
HYP = "HYP-BR-SESSDRIFT-EURUSD-H1-001"
HOLDOUT_START = pd.Timestamp("2023-01-01")

PIP = 0.0001
COST_PIPS_RT_X1 = 1.5
R_ATR_MULT = 2.0
WINDOWS = [(7, 11, -1), (13, 17, 1)]  # (start hour, end hour, direction)
SPLIT_BOUNDS = {
    "train": (date(2015, 1, 1), date(2020, 12, 31)),
    "validation": (date(2021, 1, 1), date(2022, 12, 31)),
    "combined": (date(2015, 1, 1), date(2022, 12, 31)),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def wilder_atr14(df: pd.DataFrame) -> np.ndarray:
    """Same Wilder RMA formula as the MR lane (init SMA(14), alpha=1/14)."""
    h, l, c = df["high"].to_numpy(float), df["low"].to_numpy(float), df["close"].to_numpy(float)
    prev = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - prev), np.abs(l - prev)]), axis=0)
    tr[0] = h[0] - l[0]
    out = np.full(len(tr), np.nan)
    if len(tr) < 14:
        return out
    out[13] = np.nanmean(tr[:14])
    alpha = 1.0 / 14.0
    for i in range(14, len(tr)):
        out[i] = out[i - 1] + alpha * (tr[i] - out[i - 1])
    return out


def simulate(df: pd.DataFrame, use_sl: bool) -> tuple[list[dict], dict]:
    o = df["open"].to_numpy(float)
    hi = df["high"].to_numpy(float)
    lo = df["low"].to_numpy(float)
    atr = df["atr14"]
    tu = df["time_utc"]
    idx_by_date_hour = {(t.date(), t.hour): i for i, t in enumerate(tu)}
    dates = sorted({t.date() for t in tu})

    trades: list[dict] = []
    skips = {"missing_bars": 0, "atr_nan": 0}
    for d in dates:
        for h_start, h_end, direction in WINDOWS:
            i0 = idx_by_date_hour.get((d, h_start))
            i1 = idx_by_date_hour.get((d, h_end))
            if i0 is None or i1 is None or i1 <= i0:
                skips["missing_bars"] += 1
                continue
            if i0 == 0 or not np.isfinite(atr.iloc[i0 - 1]) or atr.iloc[i0 - 1] <= 0:
                skips["atr_nan"] += 1
                continue
            r_price = R_ATR_MULT * float(atr.iloc[i0 - 1])
            entry = o[i0]
            exit_price = o[i1]
            reason = "WINDOW_END"
            if use_sl:
                sl = entry - direction * r_price
                for j in range(i0, i1):
                    if direction == 1 and lo[j] <= sl:
                        exit_price, reason = sl, "SL"
                        break
                    if direction == -1 and hi[j] >= sl:
                        exit_price, reason = sl, "SL"
                        break
            gross_r = direction * (exit_price - entry) / r_price
            r_pips = r_price / PIP
            cost_r = COST_PIPS_RT_X1 / r_pips
            trades.append({
                "date": str(d), "year": d.year, "direction": direction,
                "window": f"{h_start:02d}-{h_end:02d}",
                "entry": entry, "exit": exit_price, "reason": reason,
                "r_pips": r_pips, "gross_r": gross_r,
                "net_r_x1": gross_r - cost_r,
                "net_r_x1_5": gross_r - 1.5 * cost_r,
                "net_r_x2": gross_r - 2.0 * cost_r,
            })
    return trades, skips


def _pf(vals: np.ndarray) -> float | None:
    wins = float(vals[vals > 0].sum())
    losses = float(-vals[vals < 0].sum())
    if losses == 0.0:
        return None if wins == 0.0 else 999.0
    return round(wins / losses, 4)


def summarize(trades: list[dict], subset=None) -> dict:
    rows = [t for t in trades if subset is None or subset(t)]
    out: dict = {}
    for split, (lo_d, hi_d) in SPLIT_BOUNDS.items():
        sel = [t for t in rows if lo_d <= date.fromisoformat(t["date"]) <= hi_d]
        weeks = ((hi_d - lo_d).days + 1) / 7.0
        s: dict = {"n": len(sel), "tpw": round(len(sel) / weeks, 3)}
        if sel:
            gross = np.array([t["gross_r"] for t in sel])
            x1 = np.array([t["net_r_x1"] for t in sel])
            s["gross_pf"] = _pf(gross)
            s["pf_x1"] = _pf(x1)
            s["pf_x1_5"] = _pf(np.array([t["net_r_x1_5"] for t in sel]))
            s["pf_x2"] = _pf(np.array([t["net_r_x2"] for t in sel]))
            s["exp_x1"] = round(float(x1.mean()), 5)
            s["net_r_x1"] = round(float(x1.sum()), 3)
            s["sr_trade"] = round(float(x1.mean() / x1.std(ddof=1)), 5) if len(sel) > 2 and x1.std(ddof=1) > 0 else None
            s["skew"] = round(float(pd.Series(x1).skew()), 4) if len(sel) > 2 else None
            s["kurt"] = round(float(pd.Series(x1).kurt() + 3.0), 4) if len(sel) > 3 else None
            if split == "combined":
                by_year: dict[str, float] = {}
                for t in sel:
                    by_year[str(t["year"])] = round(by_year.get(str(t["year"]), 0.0) + t["net_r_x1"], 3)
                s["by_year_net_r_x1"] = by_year
                pos = x1[x1 > 0]
                s["top1_win_share"] = round(float(pos.max() / pos.sum()), 5) if len(pos) else None
        out[split] = s
    return out


def gates_for(co: dict) -> dict:
    years = co.get("by_year_net_r_x1", {})
    pos_years = sum(1 for v in years.values() if v > 0)
    pos = {y: v for y, v in years.items() if v > 0}
    conc = (max(pos.values()) / sum(pos.values())) if pos else None
    checks = {
        "sample_n_ge_1000": bool(co.get("n", 0) >= 1000),
        "pf_x1_ge_1_25": bool((co.get("pf_x1") or 0) >= 1.25),
        "exp_x1_ge_0_02": bool(co.get("exp_x1", -9) >= 0.02),
        "pf_x1_5_ge_1_25": bool((co.get("pf_x1_5") or 0) >= 1.25),
        "pf_x2_ge_1_00": bool((co.get("pf_x2") or 0) >= 1.00),
        "pos_years_ge_6of8": bool(pos_years >= 6),
        "concentration_le_40": bool(conc is not None and conc <= 0.40),
        "top1_share_le_5pct": bool(co.get("top1_win_share") is not None and co["top1_win_share"] <= 0.05),
    }
    return {"pass_economics": all(checks.values()), "checks": checks,
            "pos_years": pos_years, "concentration": None if conc is None else round(conc, 4)}


def main() -> int:
    import sys
    sys.path.insert(0, str(HERE.parents[1] / "EA_HybridRegimeMR" / "research"))
    from mr_dsr import dsr

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    df = pd.read_parquet(H1_PARQUET, filters=[("time_utc", "<", HOLDOUT_START)]).sort_values("time_server").reset_index(drop=True)
    if df["time_utc"].max() >= HOLDOUT_START:
        raise SystemExit("HOLDOUT SEAL VIOLATION")
    df["atr14"] = wilder_atr14(df)

    arms: dict[str, dict] = {}
    ledger_rows: list[tuple[str, dict]] = []
    for arm_name, use_sl in (("book_nostop", False), ("book_sl", True)):
        trades, skips = simulate(df, use_sl)
        arms[arm_name] = {
            "summary": summarize(trades),
            "partition_short": summarize(trades, lambda t: t["direction"] == -1),
            "partition_long": summarize(trades, lambda t: t["direction"] == 1),
            "skips": skips,
        }
        ledger_rows.extend((arm_name, t) for t in trades)

    # DSR: N = 2 simulations; V[SR] across both arms' pooled SRs
    srs = [arms[a]["summary"]["combined"].get("sr_trade") for a in arms]
    srs = [s for s in srs if s is not None]
    var_sr = float(np.var(srs, ddof=1)) if len(srs) >= 2 else 0.0
    verdict_rows = []
    for arm_name, arm in arms.items():
        co = arm["summary"]["combined"]
        g = gates_for(co)
        d = 0.0
        if all(co.get(k) is not None for k in ("sr_trade", "skew", "kurt")):
            d = dsr(co["sr_trade"], co["n"], co["skew"], co["kurt"], var_sr, 2)
        g["dsr"] = round(d, 4)
        g["pass_all"] = bool(g["pass_economics"] and d >= 0.95)
        arm["gates"] = g
        verdict_rows.append(g["pass_all"])
    verdict = "SURVIVE_CONTINUE_TO_PREREG" if any(verdict_rows) else "KILL_AT_OFFLINE_PROBE"

    ledger = EVIDENCE / f"{ts}_HYP_BR_SESSDRIFT_001_TRADES.csv"
    with ledger.open("w", encoding="utf-8", newline="") as fh:
        wtr = csv.writer(fh, lineterminator="\n")
        wtr.writerow(["arm", "date", "window", "direction", "entry", "exit", "reason",
                      "r_pips", "gross_r", "net_r_x1", "net_r_x1_5", "net_r_x2"])
        for arm_name, t in ledger_rows:
            wtr.writerow([arm_name, t["date"], t["window"], t["direction"],
                          f"{t['entry']:.5f}", f"{t['exit']:.5f}", t["reason"],
                          f"{t['r_pips']:.1f}", f"{t['gross_r']:.4f}",
                          f"{t['net_r_x1']:.4f}", f"{t['net_r_x1_5']:.4f}", f"{t['net_r_x2']:.4f}"])

    TRIALS.parent.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with TRIALS.open("a", encoding="utf-8", newline="\n") as fh:
        for i, arm_name in enumerate(arms):
            co = arms[arm_name]["summary"]["combined"]
            fh.write(json.dumps({
                "ts_utc": now_iso, "hypothesis_id": HYP, "trial_id": i + 1,
                "engine": "br_sessdrift_probe.v1", "prereg_sha256": sha256_file(PLAN),
                "arm": arm_name, "n": co.get("n"), "gross_pf": co.get("gross_pf"),
                "pf_x1": co.get("pf_x1"), "exp_x1": co.get("exp_x1"),
                "sr_trade": co.get("sr_trade"),
            }, ensure_ascii=True) + "\n")

    artifact = {
        "schema_version": "br_sessdrift_offline_probe.v1",
        "hypothesis_id": HYP, "ea_name": "EA_EURSessionDrift",
        "generated_at_utc": now_iso,
        "prereg_sha256": sha256_file(PLAN),
        "windows_utc": [[h0, h1, d] for h0, h1, d in WINDOWS],
        "inputs": {"h1_parquet": str(H1_PARQUET), "h1_sha256": sha256_file(H1_PARQUET),
                   "bars_loaded": int(len(df)), "holdout_bars_loaded": 0,
                   "last_bar_utc_loaded": str(df["time_utc"].max())},
        "cost_status": "UNVERIFIED_PROXY",
        "cost_model": "1.5 pips RT x1; no swap (intraday); stress x1.5/x2; R = 2xATR14 last closed bar",
        "trial_accounting": {"n_trials": 2, "var_sr_across_trials": round(var_sr, 6)},
        "arms": arms,
        "verdict": verdict,
        "promotion_eligible": False,
        "trade_ledger": ledger.name,
    }
    out = EVIDENCE / f"{ts}_HYP_BR_SESSDRIFT_001_PROBE.json"
    out.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    brief = {a: {"combined": arms[a]["summary"]["combined"],
                 "gates": arms[a]["gates"],
                 "short": arms[a]["partition_short"]["combined"].get("pf_x1"),
                 "long": arms[a]["partition_long"]["combined"].get("pf_x1")} for a in arms}
    print(json.dumps({"arms": brief, "verdict": verdict}, indent=2))
    print(f"ARTIFACT -> {out}")
    print(f"ARTIFACT_SHA256 {sha256_file(out)}")
    print(f"LEDGER_SHA256 {sha256_file(ledger)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
