#!/usr/bin/env python3
"""Structural V7 coil/retest/dayfade — outside V1–V6 + multi-sym collision board.

Collision-safe stem: STRUCTURAL_V7_COIL_RETEST_DAYFADE_*
NOT Model 0. NOT confirmed. NOT GOAL. Kill-fast offline.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer/EA_SonicR/research/preflight"
READ = ROOT / "03. EA Developer/EA_SonicR/research/readouts"
REG = ROOT / "03. EA Developer/EA_SonicR/research/CANDIDATE_REGISTRY.jsonl"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59, 59)
ELAPSED_WEEKS = (TO - FROM).total_seconds() / (7 * 24 * 3600)
DEPOSIT = 100000.0
RISK = 0.005
RR = 2.5
COST12 = 12.0
POINT = 0.001


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def atr14(h, l, c):
    n = len(c)
    tr = np.zeros(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    out = np.full(n, np.nan)
    if n < 14:
        return out
    out[13] = tr[:14].mean()
    for i in range(14, n):
        out[i] = (out[i - 1] * 13 + tr[i]) / 14
    return out


def load(symbol, tf):
    rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
    if rates is None or len(rates) < 100:
        raise RuntimeError(f"rates fail {symbol} {tf}: {mt5.last_error()}")
    return {
        k: rates[k].astype(float) if k != "time" else rates[k].astype(np.int64)
        for k in ("time", "open", "high", "low", "close")
    }


def mt5_dow(ts: int) -> int:
    return (datetime.fromtimestamp(ts, timezone.utc).weekday() + 1) % 7


def hour_u(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).hour


def day_key(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def sim_r(trades_spec: list[dict]) -> dict[str, Any]:
    if not trades_spec:
        return {
            "n": 0,
            "pf": 0.0,
            "tpw": 0.0,
            "exp": 0.0,
            "net": 0.0,
            "pf_x15_cost12": 0.0,
            "exp_x15_cost12": 0.0,
        }
    bal = DEPOSIT
    pnls = []
    for t in trades_spec:
        risk_cash = bal * RISK
        pnl = risk_cash * t["r"]
        pnls.append(pnl)
        bal += pnl
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    pf = (sum(wins) / sum(losses)) if losses else (999.0 if wins else 0.0)
    net = sum(pnls)
    n = len(pnls)
    pnls125 = [p - 1.5 * COST12 for p in pnls]
    w125 = [p for p in pnls125 if p > 0]
    l125 = [-p for p in pnls125 if p < 0]
    pf125 = (sum(w125) / sum(l125)) if l125 else 0.0
    return {
        "n": n,
        "pf": pf,
        "tpw": n / ELAPSED_WEEKS,
        "exp": net / n,
        "net": net,
        "pf_x15_cost12": pf125,
        "exp_x15_cost12": sum(pnls125) / n,
    }


def gate(m: dict[str, Any]) -> tuple[str, list[str]]:
    notes = []
    if m["n"] < 80:
        notes.append("n_fail")
    if not (1.0 <= m["tpw"] <= 6.0):
        notes.append("cadence_fail")
    if m["pf"] < 1.0:
        notes.append("pf_fail")
    if m["pf_x15_cost12"] < 1.25:
        notes.append("stress_fail")
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    if m["pf"] > 1.30 and 2.0 <= m["tpw"] <= 5.0 and m["pf_x15_cost12"] >= 1.25:
        return "PROBE_SURVIVOR", notes
    return "PARK_OFFLINE", notes


def resolve_trade(direction, entry, sl, tp, i_entry, h, l, c, max_hold):
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    for j in range(i_entry, min(i_entry + max_hold, len(c))):
        hi, lo = h[j], l[j]
        hit_sl = (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl)
        hit_tp = (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp)
        if hit_sl:
            return -1.0
        if hit_tp:
            return RR
    j = min(i_entry + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def tradeable(ts: int) -> bool:
    return mt5_dow(ts) in (1, 2, 3, 4) and hour_u(ts) < 22


def pack(hid, symbol, tf, funnel, trades) -> dict[str, Any]:
    m = sim_r(trades)
    verdict, notes = gate(m)
    return {
        "hypothesis_id": hid,
        "symbol": symbol,
        "tf": tf,
        "funnel": funnel,
        "metrics": m,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def probe_mono_contract_break(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_coil": 0, "n_trades": 0}
    i = 20
    while i < len(c) - 6:
        if math.isnan(atr[i]) or atr[i] <= 0:
            i += 1
            continue
        r0 = h[i] - l[i]
        r1 = h[i - 1] - l[i - 1]
        r2 = h[i - 2] - l[i - 2]
        if not (r0 < r1 < r2 and r0 > 0):
            i += 1
            continue
        if r2 > 1.5 * atr[i]:
            i += 1
            continue
        coil_hi = max(h[i], h[i - 1], h[i - 2])
        coil_lo = min(l[i], l[i - 1], l[i - 2])
        funnel["n_coil"] += 1
        found = False
        for j in range(i + 1, min(i + 1 + 4, len(c) - 2)):
            ts = int(t[j])
            if not tradeable(ts):
                continue
            bull = c[j] > coil_hi and h[j] > coil_hi
            bear = c[j] < coil_lo and l[j] < coil_lo
            if not (bull or bear):
                continue
            direction = +1 if bull else -1
            entry = float(o[j + 1])
            extreme = coil_lo if direction > 0 else coil_hi
            sl = extreme - 0.1 * atr[j] if direction > 0 else extreme + 0.1 * atr[j]
            dist = abs(entry - sl)
            if dist < 100 * POINT or dist > 5000 * POINT:
                continue
            tp = entry + dist * RR if direction > 0 else entry - dist * RR
            r = resolve_trade(direction, entry, sl, tp, j + 1, h, l, c, 16)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            i = j + 2
            found = True
            break
        if not found:
            i += 1
    return pack("HYP-H1-MONO-CONTRACT-BREAK-001", "USDJPY", "H1", funnel, trades)


def pivot_high(h, i, L=3):
    for k in range(1, L + 1):
        if h[i] <= h[i - k] or h[i] <= h[i + k]:
            return False
    return True


def pivot_low(l, i, L=3):
    for k in range(1, L + 1):
        if l[i] >= l[i - k] or l[i] >= l[i + k]:
            return False
    return True


def probe_broken_level_retest(m15: dict) -> dict[str, Any]:
    o, h, l, c, t = m15["open"], m15["high"], m15["low"], m15["close"], m15["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_break": 0, "n_retest": 0, "n_trades": 0}
    L = 3
    i = 30
    while i < len(c) - L - 12:
        if math.isnan(atr[i]) or atr[i] <= 0:
            i += 1
            continue
        pi = i - L
        is_ph = pivot_high(h, pi, L)
        is_pl = pivot_low(l, pi, L)
        if not (is_ph or is_pl):
            i += 1
            continue
        level = h[pi] if is_ph else l[pi]
        brk = None
        for j in range(i, min(i + 12, len(c) - 10)):
            if is_ph and c[j] > level and h[j] > level:
                brk = (j, +1, level)
                break
            if is_pl and c[j] < level and l[j] < level:
                brk = (j, -1, level)
                break
        if brk is None:
            i += 1
            continue
        bj, direction, lvl = brk
        funnel["n_break"] += 1
        taken = False
        for k in range(bj + 1, min(bj + 1 + 8, len(c) - 2)):
            ts = int(t[k])
            if not tradeable(ts):
                continue
            zone = 0.15 * atr[k]
            if direction > 0:
                touch = l[k] <= lvl + zone and l[k] >= lvl - zone
                hold = c[k] > lvl and c[k] > o[k]
                extreme = min(l[bj], l[k], lvl) - 0.05 * atr[k]
            else:
                touch = h[k] >= lvl - zone and h[k] <= lvl + zone
                hold = c[k] < lvl and c[k] < o[k]
                extreme = max(h[bj], h[k], lvl) + 0.05 * atr[k]
            if not (touch and hold):
                continue
            funnel["n_retest"] += 1
            entry = float(o[k + 1])
            sl = extreme
            dist = abs(entry - sl)
            if dist < 80 * POINT or dist > 6000 * POINT:
                continue
            tp = entry + dist * RR if direction > 0 else entry - dist * RR
            r = resolve_trade(direction, entry, sl, tp, k + 1, h, l, c, 24)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            i = k + 2
            taken = True
            break
        if not taken:
            i = bj + 1
    return pack("HYP-M15-BROKEN-LEVEL-RETEST-001", "USDJPY", "M15", funnel, trades)


def probe_forming_day_ext_fade(h1: dict, d1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    hd, ld, cd, td = d1["high"], d1["low"], d1["close"], d1["time"]
    atr_h = atr14(h, l, c)
    atr_d = atr14(hd, ld, cd)
    trades = []
    funnel = {"n_ready": 0, "n_trades": 0}

    d1_atr = {}
    for di in range(len(cd)):
        dk = day_key(int(td[di]))
        if not math.isnan(atr_d[di]):
            d1_atr[dk] = float(atr_d[di])

    by_day: dict[str, list[int]] = {}
    for i in range(len(c)):
        by_day.setdefault(day_key(int(t[i])), []).append(i)

    for dk, idxs in by_day.items():
        if len(idxs) < 12:
            continue
        ad = d1_atr.get(dk)
        if ad is None or ad <= 0:
            continue
        for pos in range(10, len(idxs) - 2):
            j = idxs[pos]
            ts = int(t[j])
            if not tradeable(ts):
                continue
            if math.isnan(atr_h[j]) or atr_h[j] <= 0:
                continue
            day_idxs = idxs[: pos + 1]
            day_hi = max(h[m] for m in day_idxs)
            day_lo = min(l[m] for m in day_idxs)
            day_rng = day_hi - day_lo
            if day_rng < 0.80 * ad:
                continue
            funnel["n_ready"] += 1
            mid = 0.5 * (day_hi + day_lo)
            thr_hi = day_lo + 0.90 * day_rng
            thr_lo = day_hi - 0.90 * day_rng
            fade_short = h[j] >= thr_hi and c[j] < o[j] and c[j] < thr_hi
            fade_long = l[j] <= thr_lo and c[j] > o[j] and c[j] > thr_lo
            if not (fade_short or fade_long):
                continue
            direction = -1 if fade_short else +1
            if j + 1 >= len(c):
                continue
            entry = float(o[j + 1])
            if direction < 0:
                sl = day_hi + 0.15 * atr_h[j]
                tp = mid
            else:
                sl = day_lo - 0.15 * atr_h[j]
                tp = mid
            dist = abs(entry - sl)
            if dist < 100 * POINT or dist > 5000 * POINT:
                continue
            reward = abs(tp - entry)
            if reward < 1.5 * dist:
                tp = entry + dist * RR if direction > 0 else entry - dist * RR
            else:
                max_tp = entry + dist * RR if direction > 0 else entry - dist * RR
                tp = min(tp, max_tp) if direction > 0 else max(tp, max_tp)
            r = resolve_trade(direction, entry, sl, tp, j + 1, h, l, c, 12)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            break
    return pack("HYP-H1-FORMING-DAY-EXT-FADE-001", "USDJPY", "H1", funnel, trades)


def append_registry(rows: list[dict[str, Any]]) -> None:
    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        uj_h1 = load("USDJPY", mt5.TIMEFRAME_H1)
        uj_d1 = load("USDJPY", mt5.TIMEFRAME_D1)
        uj_m15 = load("USDJPY", mt5.TIMEFRAME_M15)
        results = [
            probe_mono_contract_break(uj_h1),
            probe_broken_level_retest(uj_m15),
            probe_forming_day_ext_fade(uj_h1, uj_d1),
        ]
    finally:
        mt5.shutdown()

    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    out = {
        "generated_at_utc": utc_now(),
        "authority": "Owner GOAL push; offline-first V7 coil/retest/dayfade; GPT waived",
        "stem": "STRUCTURAL_V7_COIL_RETEST_DAYFADE",
        "dedup": "readouts/20260714_STRUCTURAL_V7_DEDUP_CLEARANCE.md",
        "rr": RR,
        "cost_stress": "fixed -$12 x1.5 cash per trade diagnostic",
        "results": results,
        "survivors": [r["hypothesis_id"] for r in survivors],
        "any_model0_authorized": bool(survivors),
        "best_shelf": "RR2 20260714_194548",
        "note": "Collision-safe vs multi-sym board that reused V7 filename",
    }
    json_path = PRE / "20260714_STRUCTURAL_V7_COIL_RETEST_DAYFADE_PROBES.json"
    write_json(json_path, out)
    receipt_sha = sha256_bytes(json_path.read_bytes())
    out["receipt_sha256"] = receipt_sha
    write_json(json_path, out)

    md_lines = [
        "# Structural V7 — coil / retest / day-fade offline probes",
        "",
        f"Generated: {out['generated_at_utc']}",
        "Stem: `STRUCTURAL_V7_COIL_RETEST_DAYFADE` (collision-safe)",
        "Authority: Owner GOAL push; offline-first; GPT waived",
        "Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`",
        "",
        "De-dup: `20260714_STRUCTURAL_V7_DEDUP_CLEARANCE.md`",
        "",
        "| ID | Symbol | N | PF | tpw | +$12 x1.5 PF | Verdict |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for r in results:
        m = r["metrics"]
        md_lines.append(
            f"| `{r['hypothesis_id']}` | {r['symbol']} | {m['n']} | {m['pf']:.3f} | "
            f"{m['tpw']:.2f} | {m['pf_x15_cost12']:.3f} | **{r['verdict']}** |"
        )
    md_lines += [
        "",
        f"Offline survivors: `{out['survivors']}`",
        f"Any Model 0 authorized: `{out['any_model0_authorized']}`",
        f"Receipt SHA: `{receipt_sha}`",
        "",
        "## Funnels",
        "",
    ]
    for r in results:
        md_lines.append(
            f"- `{r['hypothesis_id']}`: {r['funnel']} notes={r['kill_notes']}"
        )
    md_lines += [
        "",
        "## Best shelf",
        "",
        "RR2 `194548`. Do not densify V7 coil/retest/dayfade params.",
        "",
    ]
    (READ / "20260714_STRUCTURAL_V7_COIL_RETEST_DAYFADE_PROBES.md").write_text(
        "\n".join(md_lines), encoding="utf-8"
    )

    reg_rows = []
    for r in results:
        state = (
            "probe_survivor"
            if r["verdict"] == "PROBE_SURVIVOR"
            else ("parked" if r["verdict"] == "PARK_OFFLINE" else "killed")
        )
        reg_rows.append(
            {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": state,
                "parent_candidate": "STRUCTURAL_V7_COIL_RETEST_DAYFADE",
                "feature_family": r["hypothesis_id"].lower().replace("-", "_"),
                "lane": "structural_v7_coil_retest_dayfade_20260714",
                "setup_type": r["hypothesis_id"],
                "symbol": r["symbol"],
                "timeframe": r["tf"],
                "window": "2021.01.01-2025.12.31",
                "model": None,
                "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_STRUCTURAL_V7_COIL_RETEST_DAYFADE_PROBES.md",
                "run_ids": [],
                "metrics": r["metrics"],
                "validation": {"offline_probe": r["verdict"], "kill_notes": r["kill_notes"]},
                "verdict": r["verdict"],
                "cost_grade": "UNVERIFIED_OFFLINE_PROXY",
                "updated_at": "2026-07-14",
            }
        )
    append_registry(reg_rows)
    print(
        json.dumps(
            {
                "receipt_sha256": receipt_sha,
                "survivors": out["survivors"],
                "results": [
                    {
                        "id": r["hypothesis_id"],
                        "verdict": r["verdict"],
                        "n": r["metrics"]["n"],
                        "pf": round(r["metrics"]["pf"], 3),
                        "tpw": round(r["metrics"]["tpw"], 2),
                        "stress": round(r["metrics"]["pf_x15_cost12"], 3),
                        "notes": r["kill_notes"],
                    }
                    for r in results
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
