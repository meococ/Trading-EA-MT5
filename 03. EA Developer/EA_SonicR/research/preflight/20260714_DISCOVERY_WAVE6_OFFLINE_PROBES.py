#!/usr/bin/env python3
"""Discovery Wave6 — offline probes for joint thick+cadence screen.

NOT Model 0. NOT confirmed. NOT GOAL. Kill-fast offline.
Cost stress +$12 x1.5 baked into gate.
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
COST12 = 12.0
RR3 = 3.0
RR25 = 2.5


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
    if rates is None or len(rates) < 200:
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


def tradeable(ts: int) -> bool:
    return mt5_dow(ts) in (1, 2, 3, 4) and hour_u(ts) < 22


def sim_r(trades: list[dict], cost: float = COST12) -> dict[str, Any]:
    if not trades:
        return {
            "n": 0,
            "pf": 0.0,
            "tpw": 0.0,
            "exp": 0.0,
            "net": 0.0,
            "pf_cost12": 0.0,
            "pf_x15_cost12": 0.0,
            "pf_x2_cost12": 0.0,
            "exp_x15_cost12": 0.0,
            "cost_per_trade": cost,
        }
    bal = DEPOSIT
    pnls = []
    for t in trades:
        pnl = bal * RISK * t["r"]
        pnls.append(pnl)
        bal += pnl
    wins = [p for p in pnls if p > 0]
    losses = [-p for p in pnls if p < 0]
    pf = (sum(wins) / sum(losses)) if losses else (999.0 if wins else 0.0)
    net = sum(pnls)
    n = len(pnls)

    def pf_at(mult: float) -> float:
        adj = [p - mult * cost for p in pnls]
        w = [p for p in adj if p > 0]
        l = [-p for p in adj if p < 0]
        return (sum(w) / sum(l)) if l else (999.0 if w else 0.0)

    pnls15 = [p - 1.5 * cost for p in pnls]
    return {
        "n": n,
        "pf": float(pf),
        "tpw": n / ELAPSED_WEEKS,
        "exp": net / n,
        "net": net,
        "pf_cost12": float(pf_at(1.0)),
        "pf_x15_cost12": float(pf_at(1.5)),
        "pf_x2_cost12": float(pf_at(2.0)),
        "exp_x15_cost12": sum(pnls15) / n,
        "cost_per_trade": cost,
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
    if (
        m["pf"] > 1.30
        and 2.0 <= m["tpw"] <= 5.0
        and m["pf_x15_cost12"] >= 1.25
        and m["pf_x2_cost12"] >= 1.00
    ):
        return "PROBE_SURVIVOR", notes
    return "PARK_OFFLINE", notes


def resolve(direction, entry, sl, tp, i0, h, l, c, max_hold, rr_hit):
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    for j in range(i0, min(i0 + max_hold, len(c))):
        hi, lo = h[j], l[j]
        if (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl):
            return -1.0
        if (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp):
            return float(rr_hit)
    j = min(i0 + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def pack(hid, symbol, tf, funnel, trades, cost=COST12) -> dict[str, Any]:
    m = sim_r(trades, cost=cost)
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


def by_day_index(t: np.ndarray) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for i, ts in enumerate(t):
        out.setdefault(day_key(int(ts)), []).append(i)
    return out


def min_dist(symbol: str) -> float:
    if symbol.startswith("XAU"):
        return 0.5
    if "JPY" in symbol:
        return 0.03
    return 0.0003


def max_dist(symbol: str) -> float:
    if symbol.startswith("XAU"):
        return 50.0
    if "JPY" in symbol:
        return 2.0
    return 0.02


# ---------------------------------------------------------------------------
# H1 MONO-CONTRACT BREAK
# ---------------------------------------------------------------------------
def probe_mono_contract(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    rng = h - l
    trades = []
    funnel = {"n_coil": 0, "n_break": 0, "n_trades": 0}
    i = 16
    while i < len(c) - 3:
        if not (rng[i] < rng[i - 1] < rng[i - 2]):
            i += 1
            continue
        if math.isnan(atr[i]) or atr[i] <= 0:
            i += 1
            continue
        coil_hi = max(h[i - 2], h[i - 1], h[i])
        coil_lo = min(l[i - 2], l[i - 1], l[i])
        coil_w = coil_hi - coil_lo
        if coil_w <= 0 or coil_w > 1.2 * atr[i]:
            i += 1
            continue
        funnel["n_coil"] += 1
        broke = False
        for j in range(i + 1, min(i + 6, len(c) - 2)):
            if not tradeable(int(t[j])):
                continue
            up = c[j] > coil_hi
            dn = c[j] < coil_lo
            if not (up or dn):
                continue
            funnel["n_break"] += 1
            direction = 1 if up else -1
            entry = float(o[j + 1])
            if not tradeable(int(t[j + 1])):
                break
            extreme = coil_lo if up else coil_hi
            sl = extreme - 0.1 * atr[j] if up else extreme + 0.1 * atr[j]
            dist = abs(entry - sl)
            if dist < min_dist("USDJPY") or dist > max_dist("USDJPY"):
                break
            tp = entry + dist * RR3 if up else entry - dist * RR3
            r = resolve(direction, entry, sl, tp, j + 1, h, l, c, 18, RR3)
            if r is None:
                break
            trades.append({"r": r})
            funnel["n_trades"] += 1
            broke = True
            i = j + 12
            break
        if not broke:
            i += 1
    return pack("HYP-H1-MONO-CONTRACT-BREAK-001", "USDJPY", "H1", funnel, trades)


# ---------------------------------------------------------------------------
# M15 BROKEN LEVEL RETEST
# ---------------------------------------------------------------------------
def swings(h, l, left=3):
    n = len(h)
    sh = np.full(n, False)
    sl = np.full(n, False)
    for i in range(left, n - left):
        if h[i] == max(h[i - left : i + left + 1]):
            sh[i] = True
        if l[i] == min(l[i - left : i + left + 1]):
            sl[i] = True
    return sh, sl


def probe_broken_level_retest(m15: dict) -> dict[str, Any]:
    o, h, l, c, t = m15["open"], m15["high"], m15["low"], m15["close"], m15["time"]
    atr = atr14(h, l, c)
    sh, sl_ = swings(h, l, 3)
    trades = []
    funnel = {"n_break": 0, "n_retest": 0, "n_trades": 0}
    last_sh = None
    last_sl = None
    pending = None  # (dir, level, break_i)
    i = 20
    while i < len(c) - 10:
        if sh[i]:
            last_sh = (i, float(h[i]))
        if sl_[i]:
            last_sl = (i, float(l[i]))
        if pending is None:
            if last_sh is not None and c[i] > last_sh[1] and i > last_sh[0]:
                pending = (1, last_sh[1], i)
                funnel["n_break"] += 1
            elif last_sl is not None and c[i] < last_sl[1] and i > last_sl[0]:
                pending = (-1, last_sl[1], i)
                funnel["n_break"] += 1
            i += 1
            continue
        direction, level, bi = pending
        if i - bi > 8:
            pending = None
            i += 1
            continue
        if i <= bi:
            i += 1
            continue
        # retest: touch level then close holds break side
        touched = (direction > 0 and l[i] <= level <= h[i]) or (
            direction < 0 and l[i] <= level <= h[i]
        )
        if not touched:
            i += 1
            continue
        hold = (direction > 0 and c[i] > level) or (direction < 0 and c[i] < level)
        if not hold:
            pending = None
            i += 1
            continue
        funnel["n_retest"] += 1
        if i + 1 >= len(c) - 1 or not tradeable(int(t[i + 1])):
            pending = None
            i += 1
            continue
        if math.isnan(atr[i]) or atr[i] <= 0:
            pending = None
            i += 1
            continue
        entry = float(o[i + 1])
        sl = level - 0.15 * atr[i] if direction > 0 else level + 0.15 * atr[i]
        dist = abs(entry - sl)
        if dist < min_dist("USDJPY") or dist > max_dist("USDJPY"):
            pending = None
            i += 1
            continue
        tp = entry + dist * RR3 if direction > 0 else entry - dist * RR3
        r = resolve(direction, entry, sl, tp, i + 1, h, l, c, 24, RR3)
        pending = None
        if r is None:
            i += 1
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
        i += 16
    return pack("HYP-M15-BROKEN-LEVEL-RETEST-001", "USDJPY", "M15", funnel, trades)


# ---------------------------------------------------------------------------
# H1 FORMING DAY EXTENSION FADE
# ---------------------------------------------------------------------------
def probe_forming_day_fade(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_days": 0, "n_ext": 0, "n_trades": 0}
    taken_day = set()
    for d, idxs in by_day_index(t).items():
        if len(idxs) < 12:
            continue
        funnel["n_days"] += 1
        for k in range(10, len(idxs) - 2):
            i = idxs[k]
            if d in taken_day:
                break
            if not tradeable(int(t[i])):
                continue
            if hour_u(int(t[i])) < 12 or hour_u(int(t[i])) > 18:
                continue
            if math.isnan(atr[i]) or atr[i] <= 0:
                continue
            day_so_far = idxs[: k + 1]
            dhi = max(h[j] for j in day_so_far)
            dlo = min(l[j] for j in day_so_far)
            drng = dhi - dlo
            if drng < 0.80 * atr[i]:
                continue
            mid = 0.5 * (dhi + dlo)
            thr_hi = dlo + 0.90 * drng
            thr_lo = dlo + 0.10 * drng
            fade_short = c[i] > thr_hi
            fade_long = c[i] < thr_lo
            if not (fade_short or fade_long):
                continue
            funnel["n_ext"] += 1
            direction = -1 if fade_short else 1
            j = i + 1
            if j >= len(c) - 1 or not tradeable(int(t[j])):
                continue
            entry = float(o[j])
            extreme = h[i] if fade_short else l[i]
            sl = extreme + 0.1 * atr[i] if fade_short else extreme - 0.1 * atr[i]
            dist = abs(entry - sl)
            if dist < min_dist("USDJPY") or dist > max_dist("USDJPY"):
                continue
            # TP toward day mid, capped at RR3
            tp_mid = mid
            risk = dist
            natural_r = abs(tp_mid - entry) / risk
            if natural_r < 1.0:
                continue
            rr_hit = min(RR3, natural_r)
            tp = entry + direction * risk * rr_hit
            r = resolve(direction, entry, sl, tp, j, h, l, c, 10, rr_hit)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            taken_day.add(d)
            break
    return pack("HYP-H1-FORMING-DAY-EXT-FADE-001", "USDJPY", "H1", funnel, trades)


# ---------------------------------------------------------------------------
# FX3 BODY/ATR CONTINUATION PORTFOLIO
# ---------------------------------------------------------------------------
def probe_bodyatr_one(symbol: str, h1: dict) -> list[dict]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    for i in range(20, len(c) - 3):
        if not tradeable(int(t[i])):
            continue
        if math.isnan(atr[i]) or atr[i] <= 0:
            continue
        body = abs(c[i] - o[i])
        if body < 1.0 * atr[i]:
            continue
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        bull = c[i] > o[i]
        # close in extreme quartile
        if bull and c[i] < l[i] + 0.75 * rng:
            continue
        if (not bull) and c[i] > l[i] + 0.25 * rng:
            continue
        j = i + 1
        if j >= len(c) - 1 or not tradeable(int(t[j])):
            continue
        # next bar open continuation; require same-direction open accept
        if bull and not (o[j] >= c[i] * 0.9999 or o[j] >= o[i]):
            # soft accept: open not deep reverse
            if o[j] < c[i] - 0.2 * atr[i]:
                continue
        if (not bull) and o[j] > c[i] + 0.2 * atr[i]:
            continue
        direction = 1 if bull else -1
        entry = float(o[j])
        extreme = l[i] if bull else h[i]
        sl = extreme - 0.1 * atr[i] if bull else extreme + 0.1 * atr[i]
        dist = abs(entry - sl)
        if dist < min_dist(symbol) or dist > max_dist(symbol):
            continue
        tp = entry + dist * RR25 if bull else entry - dist * RR25
        r = resolve(direction, entry, sl, tp, j, h, l, c, 12, RR25)
        if r is None:
            continue
        trades.append({"r": r, "symbol": symbol, "ts": int(t[j])})
    return trades


def probe_fx3_portfolio(h1_map: dict[str, dict]) -> dict[str, Any]:
    all_trades: list[dict] = []
    per = {}
    for sym, bars in h1_map.items():
        tlist = probe_bodyatr_one(sym, bars)
        per[sym] = len(tlist)
        all_trades.extend(tlist)
    # chronological pool; max 1 open per symbol-day via sort only (a priori pool)
    all_trades.sort(key=lambda x: x["ts"])
    # de-overlap: keep first trade per calendar day across book (a priori risk cap)
    kept = []
    days_used = set()
    for tr in all_trades:
        dk = day_key(tr["ts"]) + "|" + tr["symbol"]
        if dk in days_used:
            continue
        days_used.add(dk)
        kept.append({"r": tr["r"]})
    funnel = {"per_symbol_raw": per, "n_pooled_raw": len(all_trades), "n_trades": len(kept)}
    return pack(
        "HYP-FX3-H1-BODYATR-CONT-PORTFOLIO-001",
        "EURUSD+USDJPY+GBPUSD",
        "H1",
        funnel,
        kept,
        cost=COST12,
    )


def append_registry(rows: list[dict]) -> None:
    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        acc = mt5.account_info()
        usdjpy_h1 = load("USDJPY", mt5.TIMEFRAME_H1)
        usdjpy_m15 = load("USDJPY", mt5.TIMEFRAME_M15)
        eurusd_h1 = load("EURUSD", mt5.TIMEFRAME_H1)
        gbpusd_h1 = load("GBPUSD", mt5.TIMEFRAME_H1)

        probes = [
            probe_mono_contract(usdjpy_h1),
            probe_broken_level_retest(usdjpy_m15),
            probe_forming_day_fade(usdjpy_h1),
            probe_fx3_portfolio(
                {"EURUSD": eurusd_h1, "USDJPY": usdjpy_h1, "GBPUSD": gbpusd_h1}
            ),
        ]
    finally:
        mt5.shutdown()

    survivors = [p for p in probes if p["verdict"] == "PROBE_SURVIVOR"]
    out = {
        "schema_version": "sonic_discovery_wave6_offline_probes.v1",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_WAVE6_COMPLETE",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "dedup": "readouts/20260714_DISCOVERY_WAVE6_DEDUP_CLEARANCE.md",
        "server": getattr(acc, "server", None) if acc else None,
        "login": getattr(acc, "login", None) if acc else None,
        "joint_screen": "PF>1.30 ∧ tpw∈[2,5] ∧ x1.5≥1.25 ∧ x2≥1.00",
        "probes": probes,
        "survivors": [p["hypothesis_id"] for p in survivors],
        "model0_authorized": bool(survivors),
    }

    json_path = PRE / "20260714_DISCOVERY_WAVE6_OFFLINE_PROBES.json"
    write_json(json_path, out)
    sha = sha256_file(json_path)
    out["receipt_sha256"] = sha
    write_json(json_path, out)

    lines = [
        "# Discovery Wave6 — offline probes (joint thick + cadence)",
        "",
        f"Generated: {out['created_at_utc']}",
        f"De-dup: `{out['dedup']}`",
        f"Receipt SHA: `{sha}`",
        "",
        "| ID | Sym | N | PF | tpw | x1.5 | x2 | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for p in probes:
        m = p["metrics"]
        lines.append(
            f"| `{p['hypothesis_id']}` | {p['symbol']} | {m['n']} | "
            f"{m['pf']:.3f} | {m['tpw']:.2f} | {m['pf_x15_cost12']:.3f} | "
            f"{m['pf_x2_cost12']:.3f} | **{p['verdict']}** |"
        )
    lines += [
        "",
        f"Survivors: `{out['survivors']}`",
        f"Model 0 authorized: `{out['model0_authorized']}`",
        "",
        "## Funnels",
        "",
    ]
    for p in probes:
        lines.append(
            f"- `{p['hypothesis_id']}`: {p['funnel']} notes={p['kill_notes']}"
        )
    lines += [
        "",
        "Best shelf RR2 `194548` unchanged unless survivor promotes.",
        "Cost grade: `UNVERIFIED_OFFLINE_PROXY` (+$12 baked).",
        "",
    ]
    md_path = READ / "20260714_DISCOVERY_WAVE6_OFFLINE_PROBES.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    reg_rows = []
    for p in probes:
        m = p["metrics"]
        reg_rows.append(
            {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": p["hypothesis_id"],
                "state": "killed" if "KILL" in p["verdict"] else (
                    "parked" if "PARK" in p["verdict"] else "probe"
                ),
                "parent_candidate": "DISCOVERY_WAVE6_OFFLINE",
                "feature_family": p["hypothesis_id"].lower().replace("-", "_"),
                "lane": "discovery_wave6_20260714",
                "setup_type": p["hypothesis_id"],
                "symbol": p["symbol"],
                "timeframe": p["tf"],
                "window": "2021.01.01-2025.12.31",
                "model": None,
                "prereg_path": None,
                "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_DISCOVERY_WAVE6_OFFLINE_PROBES.md",
                "source_path": None,
                "run_ids": [],
                "metrics": m,
                "validation": {
                    "offline_probe": p["verdict"],
                    "kill_notes": p["kill_notes"],
                    "model0": p["model0"],
                },
                "verdict": p["verdict"],
                "cost_grade": "UNVERIFIED_OFFLINE_PROXY",
                "updated_at": "2026-07-14",
                "receipt_sha256": sha,
                "dedup": "readouts/20260714_DISCOVERY_WAVE6_DEDUP_CLEARANCE.md",
            }
        )
    append_registry(reg_rows)
    print(json.dumps({"sha": sha, "survivors": out["survivors"], "board": [
        {"id": p["hypothesis_id"], "verdict": p["verdict"], "m": {
            "n": p["metrics"]["n"], "pf": round(p["metrics"]["pf"], 3),
            "tpw": round(p["metrics"]["tpw"], 2),
            "x15": round(p["metrics"]["pf_x15_cost12"], 3),
        }} for p in probes
    ]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
