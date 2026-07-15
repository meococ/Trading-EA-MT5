#!/usr/bin/env python3
"""Structural rebuild offline probes V4 — five fresh independent objects.

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
RR = 3.0
COST12 = 12.0
POINT = 0.001


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


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


def pack(hid, tf, funnel, trades) -> dict[str, Any]:
    m = sim_r(trades)
    verdict, notes = gate(m)
    return {
        "hypothesis_id": hid,
        "symbol": "USDJPY",
        "tf": tf,
        "funnel": funnel,
        "metrics": m,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def probe_orderblock(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_displace": 0, "n_ob": 0, "n_trades": 0}
    i = 20
    while i < len(c) - 8:
        if math.isnan(atr[i]) or atr[i] <= 0:
            i += 1
            continue
        body = abs(c[i] - o[i])
        if body < 1.2 * atr[i]:
            i += 1
            continue
        bull = c[i] > o[i]
        funnel["n_displace"] += 1
        # last opposite body in prior 8 bars
        ob_i = None
        for k in range(i - 1, max(i - 9, 0), -1):
            if bull and c[k] < o[k]:
                ob_i = k
                break
            if (not bull) and c[k] > o[k]:
                ob_i = k
                break
        if ob_i is None:
            i += 1
            continue
        ob_hi, ob_lo = max(o[ob_i], c[ob_i]), min(o[ob_i], c[ob_i])
        funnel["n_ob"] += 1
        for j in range(i + 1, min(i + 1 + 16, len(c) - 2)):
            ts = int(t[j])
            if not tradeable(ts):
                continue
            mid = 0.5 * (ob_hi + ob_lo)
            if bull:
                touch = l[j] <= ob_hi and l[j] >= ob_lo
                hold = c[j] >= mid
                direction = +1
                extreme = ob_lo
            else:
                touch = h[j] >= ob_lo and h[j] <= ob_hi
                hold = c[j] <= mid
                direction = -1
                extreme = ob_hi
            if not (touch and hold):
                continue
            entry = float(o[j + 1])
            sl = extreme - 0.1 * atr[j] if direction > 0 else extreme + 0.1 * atr[j]
            dist = abs(entry - sl)
            if dist < 100 * POINT or dist > 5000 * POINT:
                continue
            tp = entry + dist * RR if direction > 0 else entry - dist * RR
            r = resolve_trade(direction, entry, sl, tp, j + 1, h, l, c, 12)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            i = j + 2
            break
        else:
            i += 1
    return pack("HYP-H1-ORDERBLOCK-MITIGATION-001", "H1", funnel, trades)


def probe_d1_inside_h4(d1: dict, h4: dict) -> dict[str, Any]:
    o4, h4h, l4, c4, t4 = h4["open"], h4["high"], h4["low"], h4["close"], h4["time"]
    hd, ld, td = d1["high"], d1["low"], d1["time"]
    atr = atr14(h4h, l4, c4)
    trades = []
    funnel = {"n_inside_d1": 0, "n_break": 0, "n_trades": 0}
    # map each H4 to prior completed D1
    for i in range(30, len(c4) - 3):
        ts = int(t4[i])
        # prior D1: last D1 with time < day start
        day_start = datetime.fromtimestamp(ts, timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        d_idx = np.searchsorted(td, int(day_start.timestamp()), side="left") - 1
        if d_idx < 1:
            continue
        # inside day = D1[d_idx] inside D1[d_idx-1]
        if not (hd[d_idx] < hd[d_idx - 1] and ld[d_idx] > ld[d_idx - 1]):
            continue
        funnel["n_inside_d1"] += 1
        ins_hi, ins_lo = float(hd[d_idx]), float(ld[d_idx])
        # break on bar i
        broke_up = c4[i] > ins_hi and h4h[i] > ins_hi
        broke_dn = c4[i] < ins_lo and l4[i] < ins_lo
        if not (broke_up or broke_dn):
            continue
        funnel["n_break"] += 1
        # accept: next H4 closes beyond
        j = i + 1
        if j >= len(c4) - 1:
            continue
        tsj = int(t4[j])
        if not tradeable(tsj):
            continue
        if broke_up and c4[j] > ins_hi:
            direction = +1
            extreme = ins_lo
        elif broke_dn and c4[j] < ins_lo:
            direction = -1
            extreme = ins_hi
        else:
            continue
        if math.isnan(atr[j]) or atr[j] <= 0:
            continue
        entry = float(o4[j + 1]) if j + 1 < len(c4) else float(c4[j])
        sl = extreme - 0.1 * atr[j] if direction > 0 else extreme + 0.1 * atr[j]
        dist = abs(entry - sl)
        if dist < 100 * POINT or dist > 8000 * POINT:
            continue
        tp = entry + dist * RR if direction > 0 else entry - dist * RR
        start = min(j + 1, len(c4) - 1)
        r = resolve_trade(direction, entry, sl, tp, start, h4h, l4, c4, 20)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    # funnel n_inside_d1 counted per H4 bar → scale note only
    return pack("HYP-D1-INSIDE-H4-BREAK-001", "H4", funnel, trades)


def probe_london_drive_fail(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_london_days": 0, "n_displace": 0, "n_fail": 0, "n_trades": 0}
    by_day: dict[str, list[int]] = {}
    for i, ts in enumerate(t):
        by_day.setdefault(day_key(int(ts)), []).append(i)

    for _, idxs in by_day.items():
        # London open proxy 07:00–08:00 UTC
        open_bars = [i for i in idxs if hour_u(int(t[i])) == 7]
        if not open_bars:
            continue
        funnel["n_london_days"] += 1
        i0 = open_bars[0]
        london_open = float(o[i0])
        # first 2 H1 displace
        window = [i for i in idxs if 7 <= hour_u(int(t[i])) < 9]
        if len(window) < 2 or math.isnan(atr[i0]) or atr[i0] <= 0:
            continue
        hi = max(h[i] for i in window)
        lo = min(l[i] for i in window)
        up = hi - london_open >= 0.8 * atr[i0]
        dn = london_open - lo >= 0.8 * atr[i0]
        if not (up or dn):
            continue
        funnel["n_displace"] += 1
        # fail: later H1 closes back through london_open opposite to displace
        post = [i for i in idxs if 9 <= hour_u(int(t[i])) < 16]
        fail_i = None
        direction = 0
        for i in post:
            if up and c[i] < london_open:
                fail_i = i
                direction = -1  # fade short
                break
            if dn and c[i] > london_open:
                fail_i = i
                direction = +1
                break
        if fail_i is None:
            continue
        funnel["n_fail"] += 1
        ts = int(t[fail_i])
        if not tradeable(ts):
            continue
        entry = float(o[fail_i + 1]) if fail_i + 1 < len(c) else float(c[fail_i])
        if direction < 0:
            sl = hi + 0.1 * atr[fail_i]
        else:
            sl = lo - 0.1 * atr[fail_i]
        dist = abs(entry - sl)
        if dist < 100 * POINT or dist > 5000 * POINT:
            continue
        tp = entry + dist * RR if direction > 0 else entry - dist * RR
        r = resolve_trade(direction, entry, sl, tp, fail_i + 1, h, l, c, 12)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack("HYP-H1-LONDON-DRIVE-FAIL-FADE-001", "H1", funnel, trades)


def probe_asia_break_fail(m15: dict) -> dict[str, Any]:
    o, h, l, c, t = m15["open"], m15["high"], m15["low"], m15["close"], m15["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_asia_days": 0, "n_break": 0, "n_fail": 0, "n_trades": 0}
    by_day: dict[str, list[int]] = {}
    for i, ts in enumerate(t):
        by_day.setdefault(day_key(int(ts)), []).append(i)

    for _, idxs in by_day.items():
        asia = [i for i in idxs if 0 <= hour_u(int(t[i])) < 6]
        if len(asia) < 8:
            continue
        funnel["n_asia_days"] += 1
        a_hi = max(h[i] for i in asia)
        a_lo = min(l[i] for i in asia)
        if a_hi <= a_lo:
            continue
        london = [i for i in idxs if 7 <= hour_u(int(t[i])) < 12]
        break_i = None
        up = False
        for i in london:
            if h[i] > a_hi:
                break_i = i
                up = True
                break
            if l[i] < a_lo:
                break_i = i
                up = False
                break
        if break_i is None:
            continue
        funnel["n_break"] += 1
        # fail within 6 M15: close back inside Asia
        fail_i = None
        for k in range(break_i, min(break_i + 7, idxs[-1] + 1)):
            if a_lo < c[k] < a_hi:
                fail_i = k
                break
        if fail_i is None:
            continue
        funnel["n_fail"] += 1
        ts = int(t[fail_i])
        if not tradeable(ts):
            continue
        mid = 0.5 * (a_hi + a_lo)
        direction = -1 if up else +1
        entry = float(o[fail_i + 1]) if fail_i + 1 < len(c) else float(c[fail_i])
        atr_v = atr[fail_i] if not math.isnan(atr[fail_i]) else (a_hi - a_lo)
        sl = (a_hi + 0.1 * atr_v) if direction < 0 else (a_lo - 0.1 * atr_v)
        dist = abs(entry - sl)
        if dist < 80 * POINT or dist > 4000 * POINT:
            continue
        # TP toward Asia mid or RR - use RR for consistency
        tp = entry + dist * RR if direction > 0 else entry - dist * RR
        # also cap TP at mid if closer
        if direction < 0:
            tp = max(tp, mid)
        else:
            tp = min(tp, mid)
        # recompute effective R if mid closer
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        # use resolve with synthetic tp at least 1R toward mid
        r_target = abs(tp - entry) / risk
        if r_target < 0.8:
            continue
        # temporarily use custom RR for this trade by scaling
        # resolve_trade uses global RR for TP hits - build custom path
        r = None
        for j in range(fail_i + 1, min(fail_i + 1 + 16, len(c))):
            hi, lo, cl = h[j], l[j], c[j]
            hit_sl = (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl)
            hit_tp = (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp)
            if hit_sl:
                r = -1.0
                break
            if hit_tp:
                r = abs(tp - entry) / risk
                break
        if r is None:
            j = min(fail_i + 16, len(c) - 1)
            r = direction * (c[j] - entry) / risk
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack("HYP-M15-ASIA-BREAK-FAIL-FADE-001", "M15", funnel, trades)


def probe_break_pause_break(h4: dict) -> dict[str, Any]:
    o, h, l, c, t = h4["open"], h4["high"], h4["low"], h4["close"], h4["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_break": 0, "n_pause": 0, "n_trades": 0}
    for i in range(20, len(c) - 4):
        # break of prior 10-bar high/low on bar i
        prior_hi = max(h[i - 10 : i])
        prior_lo = min(l[i - 10 : i])
        up = c[i] > prior_hi
        dn = c[i] < prior_lo
        if not (up or dn):
            continue
        funnel["n_break"] += 1
        # pause bar i+1: inside relative to break bar
        j = i + 1
        if not (h[j] <= h[i] and l[j] >= l[i]):
            continue
        funnel["n_pause"] += 1
        k = i + 2
        ts = int(t[k])
        if not tradeable(ts):
            continue
        if up and c[k] > h[i]:
            direction = +1
            extreme = l[i]
        elif dn and c[k] < l[i]:
            direction = -1
            extreme = h[i]
        else:
            continue
        if math.isnan(atr[k]) or atr[k] <= 0:
            continue
        entry = float(o[k + 1]) if k + 1 < len(c) else float(c[k])
        sl = extreme - 0.1 * atr[k] if direction > 0 else extreme + 0.1 * atr[k]
        dist = abs(entry - sl)
        if dist < 100 * POINT or dist > 8000 * POINT:
            continue
        tp = entry + dist * RR if direction > 0 else entry - dist * RR
        start = min(k + 1, len(c) - 1)
        r = resolve_trade(direction, entry, sl, tp, start, h, l, c, 20)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack("HYP-H4-BREAK-PAUSE-BREAK-001", "H4", funnel, trades)


def main() -> int:
    if not mt5.initialize():
        raise RuntimeError(mt5.last_error())
    try:
        mt5.symbol_select("USDJPY", True)
        h1 = load("USDJPY", mt5.TIMEFRAME_H1)
        h4 = load("USDJPY", mt5.TIMEFRAME_H4)
        m15 = load("USDJPY", mt5.TIMEFRAME_M15)
        d1 = load("USDJPY", mt5.TIMEFRAME_D1)
        acc = mt5.account_info()
        server = getattr(acc, "server", None)
        login = getattr(acc, "login", None)
    finally:
        mt5.shutdown()

    probes = [
        probe_orderblock(h1),
        probe_d1_inside_h4(d1, h4),
        probe_london_drive_fail(h1),
        probe_asia_break_fail(m15),
        probe_break_pause_break(h4),
    ]
    survivors = [p["hypothesis_id"] for p in probes if p["verdict"] == "PROBE_SURVIVOR"]
    parks = [p["hypothesis_id"] for p in probes if p["verdict"] == "PARK_OFFLINE"]
    payload = {
        "schema_version": "sonic_structural_offline_probes.v4",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_FIRST_V4_COMPLETE",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "server": server,
        "login": login,
        "dedup": "readouts/20260714_STRUCTURAL_V4_DEDUP_CLEARANCE.md",
        "probes": probes,
        "offline_survivors": survivors,
        "offline_parks": parks,
        "any_model0_authorized": bool(survivors),
        "phase0_compose": "NOT_WAITED_DISCOVERY_CONTINUES",
        "best_shelf": "RR2 20260714_194548",
        "banned": [
            "densify_maxkz_rr",
            "retune_v1_v3",
            "retune_wave3_5",
            "model0_on_kill",
            "phase0_wait_stall",
        ],
    }
    out = PRE / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V4.json"
    write_json(out, payload)
    sha = sha256_file(out)

    lines = [
        "# Structural rebuild offline probes V4",
        "",
        f"Generated: {payload['created_at_utc']}",
        "Authority: Owner GOAL push; offline-first; GPT waived",
        "Status: **offline-first**; Model 0 only if `PROBE_SURVIVOR`",
        "",
        "De-dup: `20260714_STRUCTURAL_V4_DEDUP_CLEARANCE.md`",
        "",
        "| ID | N | PF | tpw | +$12 x1.5 PF | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for p in probes:
        m = p["metrics"]
        lines.append(
            f"| `{p['hypothesis_id']}` | {m['n']} | {m['pf']:.3f} | {m['tpw']:.2f} | "
            f"{m['pf_x15_cost12']:.3f} | **{p['verdict']}** |"
        )
    lines += [
        "",
        f"Offline survivors: `{survivors}`",
        f"Any Model 0 authorized: `{payload['any_model0_authorized']}`",
        f"Receipt SHA: `{sha}`",
        "",
        "## Funnels",
        "",
    ]
    for p in probes:
        lines.append(f"- `{p['hypothesis_id']}`: {p['funnel']} notes={p['kill_notes']}")
    lines += [
        "",
        "## Phase-0 / best shelf",
        "",
        "Discovery continues without Phase-0 Owner clear. Best shelf RR2 `194548`.",
        "Do not densify any V4 kill parameters.",
    ]
    (READ / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V4.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    for p in probes:
        state = (
            "killed"
            if "KILL" in p["verdict"]
            else ("parked" if "PARK" in p["verdict"] else "idea")
        )
        with REG.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": p["hypothesis_id"],
                        "state": state,
                        "verdict": p["verdict"],
                        "reason": f"offline V4 {p['metrics']}; notes={p['kill_notes']}",
                        "updated_at": "2026-07-14",
                        "lane": "structural_rebuild_v4_20260714",
                        "symbol": "USDJPY",
                        "timeframe": p["tf"],
                        "model": "offline_closed_bar_probe",
                        "metrics": p["metrics"],
                        "validation": {"model0": p["model0"]},
                        "receipt_sha256": sha,
                        "dedup": "readouts/20260714_STRUCTURAL_V4_DEDUP_CLEARANCE.md",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        json.dumps(
            {
                "sha": sha,
                "board": [
                    {
                        "id": p["hypothesis_id"],
                        "verdict": p["verdict"],
                        "n": p["metrics"]["n"],
                        "pf": round(p["metrics"]["pf"], 3),
                        "tpw": round(p["metrics"]["tpw"], 3),
                        "x15": round(p["metrics"]["pf_x15_cost12"], 3),
                    }
                    for p in probes
                ],
                "survivors": survivors,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
