#!/usr/bin/env python3
"""Structural V6 — multi-symbol offline probes (escape USDJPY TF saturation).

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
COST = {"EURUSD": 12.0, "GBPUSD": 12.0, "XAUUSD": 25.0}


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


def sim_r(trades: list[dict], symbol: str) -> dict[str, Any]:
    cost = COST[symbol]
    if not trades:
        return {
            "n": 0,
            "pf": 0.0,
            "tpw": 0.0,
            "exp": 0.0,
            "net": 0.0,
            "pf_x15_cost": 0.0,
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
    pnls125 = [p - 1.5 * cost for p in pnls]
    w = [p for p in pnls125 if p > 0]
    l = [-p for p in pnls125 if p < 0]
    pf125 = (sum(w) / sum(l)) if l else 0.0
    return {
        "n": n,
        "pf": pf,
        "tpw": n / ELAPSED_WEEKS,
        "exp": net / n,
        "net": net,
        "pf_x15_cost": pf125,
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
    if m["pf_x15_cost"] < 1.25:
        notes.append("stress_fail")
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    if m["pf"] > 1.30 and 2.0 <= m["tpw"] <= 5.0 and m["pf_x15_cost"] >= 1.25:
        return "PROBE_SURVIVOR", notes
    return "PARK_OFFLINE", notes


def resolve(direction, entry, sl, tp, i0, h, l, c, max_hold, rr_hit=None):
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    target_r = rr_hit if rr_hit is not None else RR
    for j in range(i0, min(i0 + max_hold, len(c))):
        hi, lo = h[j], l[j]
        if (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl):
            return -1.0
        if (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp):
            return target_r
    j = min(i0 + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def pack(hid, symbol, tf, funnel, trades) -> dict[str, Any]:
    m = sim_r(trades, symbol)
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


def probe_eur_london_overlap(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_days": 0, "n_break": 0, "n_trades": 0}
    for _, idxs in by_day_index(t).items():
        box = [i for i in idxs if 7 <= hour_u(int(t[i])) < 10]
        if len(box) < 3:
            continue
        funnel["n_days"] += 1
        bhi, blo = max(h[i] for i in box), min(l[i] for i in box)
        post = [i for i in idxs if 10 <= hour_u(int(t[i])) < 16]
        break_i = None
        up = False
        for i in post:
            if c[i] > bhi:
                break_i, up = i, True
                break
            if c[i] < blo:
                break_i, up = i, False
                break
        if break_i is None:
            continue
        funnel["n_break"] += 1
        j = break_i + 1
        if j >= len(c) - 1 or not tradeable(int(t[j])):
            continue
        if up and c[j] <= bhi:
            continue
        if (not up) and c[j] >= blo:
            continue
        if math.isnan(atr[j]) or atr[j] <= 0:
            continue
        direction = 1 if up else -1
        entry = float(o[j + 1])
        extreme = blo if up else bhi
        sl = extreme - 0.1 * atr[j] if up else extreme + 0.1 * atr[j]
        dist = abs(entry - sl)
        if dist < 0.0003 or dist > 0.02:
            continue
        tp = entry + dist * RR if up else entry - dist * RR
        r = resolve(direction, entry, sl, tp, j + 1, h, l, c, 12)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack(
        "HYP-EURUSD-H1-LONDON-OVERLAP-RANGE-BREAK-001",
        "EURUSD",
        "H1",
        funnel,
        trades,
    )


def probe_gbp_ny_impulse(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_days": 0, "n_impulse": 0, "n_trades": 0}
    for _, idxs in by_day_index(t).items():
        ny = [i for i in idxs if hour_u(int(t[i])) == 13]
        if not ny:
            continue
        funnel["n_days"] += 1
        i0 = ny[0]
        if math.isnan(atr[i0]) or atr[i0] <= 0:
            continue
        body = abs(c[i0] - o[i0])
        if body < 1.2 * atr[i0]:
            continue
        funnel["n_impulse"] += 1
        bull = c[i0] > o[i0]
        j = i0 + 1
        if j >= len(c) - 1 or hour_u(int(t[j])) != 14:
            continue
        if not tradeable(int(t[j])):
            continue
        mid = 0.5 * (o[i0] + c[i0])
        if bull and not (c[j] > mid and c[j] >= o[j]):
            continue
        if (not bull) and not (c[j] < mid and c[j] <= o[j]):
            continue
        direction = 1 if bull else -1
        entry = float(o[j + 1])
        extreme = l[i0] if bull else h[i0]
        sl = extreme - 0.1 * atr[j] if bull else extreme + 0.1 * atr[j]
        dist = abs(entry - sl)
        if dist < 0.0003 or dist > 0.02:
            continue
        tp = entry + dist * RR if bull else entry - dist * RR
        r = resolve(direction, entry, sl, tp, j + 1, h, l, c, 12)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack("HYP-GBPUSD-H1-NY-OPEN-IMPULSE-001", "GBPUSD", "H1", funnel, trades)


def probe_xau_asia_compress(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_days": 0, "n_compress": 0, "n_break": 0, "n_trades": 0}
    for _, idxs in by_day_index(t).items():
        asia = [i for i in idxs if 0 <= hour_u(int(t[i])) < 6]
        if len(asia) < 4:
            continue
        funnel["n_days"] += 1
        ahi, alo = max(h[i] for i in asia), min(l[i] for i in asia)
        i_ref = asia[-1]
        if math.isnan(atr[i_ref]) or atr[i_ref] <= 0:
            continue
        if (ahi - alo) > 0.55 * atr[i_ref]:
            continue
        funnel["n_compress"] += 1
        post = [i for i in idxs if 7 <= hour_u(int(t[i])) < 14]
        break_i = None
        up = False
        for i in post:
            if c[i] > ahi:
                break_i, up = i, True
                break
            if c[i] < alo:
                break_i, up = i, False
                break
        if break_i is None:
            continue
        funnel["n_break"] += 1
        j = break_i + 1
        if j >= len(c) - 1 or not tradeable(int(t[j])):
            continue
        if up and c[j] <= ahi:
            continue
        if (not up) and c[j] >= alo:
            continue
        direction = 1 if up else -1
        entry = float(o[j + 1])
        extreme = alo if up else ahi
        sl = extreme - 0.15 * atr[j] if up else extreme + 0.15 * atr[j]
        dist = abs(entry - sl)
        if dist < 0.5 or dist > 80:
            continue
        tp = entry + dist * RR if up else entry - dist * RR
        r = resolve(direction, entry, sl, tp, j + 1, h, l, c, 12)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack(
        "HYP-XAUUSD-H1-ASIA-COMPRESS-LONDON-BREAK-001",
        "XAUUSD",
        "H1",
        funnel,
        trades,
    )


def probe_eur_d1_outside_fade(d1: dict, h1: dict) -> dict[str, Any]:
    hd, ld, od, cd, td = d1["high"], d1["low"], d1["open"], d1["close"], d1["time"]
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_outside_d1": 0, "n_trades": 0}
    # For each D1 outside bar at index d, search next day's H1
    for d in range(2, len(cd) - 1):
        if not (hd[d] > hd[d - 1] and ld[d] < ld[d - 1]):
            continue
        funnel["n_outside_d1"] += 1
        mid = 0.5 * (hd[d] + ld[d])
        # H1 bars after this D1 completes: time >= next day start
        day_end = int(td[d]) + 24 * 3600
        # find first H1 index with time >= td[d]+86400 roughly next session
        start = np.searchsorted(t, int(td[d]) + 20 * 3600, side="left")
        end = np.searchsorted(t, int(td[d]) + 5 * 24 * 3600, side="left")
        for j in range(start, min(end, len(c) - 2)):
            if not tradeable(int(t[j])):
                continue
            # close back through mid from outside close side
            if cd[d] >= mid and c[j] < mid and c[j - 1] >= mid:
                direction = -1
                extreme = hd[d]
            elif cd[d] <= mid and c[j] > mid and c[j - 1] <= mid:
                direction = 1
                extreme = ld[d]
            else:
                continue
            if math.isnan(atr[j]) or atr[j] <= 0:
                continue
            entry = float(o[j + 1])
            sl = extreme + 0.1 * atr[j] if direction < 0 else extreme - 0.1 * atr[j]
            dist = abs(entry - sl)
            if dist < 0.0005 or dist > 0.03:
                continue
            tp = entry + dist * RR if direction > 0 else entry - dist * RR
            r = resolve(direction, entry, sl, tp, j + 1, h, l, c, 16)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            break
    return pack("HYP-EURUSD-D1-OUTSIDE-H1-FADE-001", "EURUSD", "H1", funnel, trades)


def probe_gbp_h4_break_h1_pb(h4: dict, h1: dict) -> dict[str, Any]:
    o4, h4h, l4, c4, t4 = h4["open"], h4["high"], h4["low"], h4["close"], h4["time"]
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_h4_break": 0, "n_pb": 0, "n_trades": 0}
    for i in range(10, len(c4) - 2):
        prior_hi = max(h4h[i - 5 : i])
        prior_lo = min(l4[i - 5 : i])
        up = c4[i] > prior_hi
        dn = c4[i] < prior_lo
        if not (up or dn):
            continue
        funnel["n_h4_break"] += 1
        brk_open = float(o4[i])
        # H1 after this H4 bar time
        start = np.searchsorted(t, int(t4[i]) + 4 * 3600, side="left")
        end = min(start + 24, len(c) - 2)
        for j in range(start, end):
            if not tradeable(int(t[j])):
                continue
            if up:
                touch = l[j] <= brk_open <= h[j]
                hold = c[j] > brk_open
                direction = 1
                extreme = l[j]
            else:
                touch = l[j] <= brk_open <= h[j]
                hold = c[j] < brk_open
                direction = -1
                extreme = h[j]
            if not (touch and hold):
                continue
            funnel["n_pb"] += 1
            if math.isnan(atr[j]) or atr[j] <= 0:
                continue
            entry = float(o[j + 1])
            sl = extreme - 0.1 * atr[j] if direction > 0 else extreme + 0.1 * atr[j]
            dist = abs(entry - sl)
            if dist < 0.0003 or dist > 0.02:
                continue
            tp = entry + dist * RR if direction > 0 else entry - dist * RR
            r = resolve(direction, entry, sl, tp, j + 1, h, l, c, 12)
            if r is None:
                continue
            trades.append({"r": r})
            funnel["n_trades"] += 1
            break
    return pack("HYP-GBPUSD-H4-BREAK-H1-OPEN-PB-001", "GBPUSD", "H1", funnel, trades)


def probe_xau_h4_wick(h4: dict) -> dict[str, Any]:
    o, h, l, c, t = h4["open"], h4["high"], h4["low"], h4["close"], h4["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_wick": 0, "n_trades": 0}
    for i in range(20, len(c) - 3):
        rng = h[i] - l[i]
        if rng <= 0 or math.isnan(atr[i]) or atr[i] <= 0:
            continue
        upper = h[i] - max(o[i], c[i])
        lower = min(o[i], c[i]) - l[i]
        mid = 0.5 * (h[i] + l[i])
        # bearish wick reject
        if upper / rng >= 0.60 and c[i] < mid:
            direction = -1
            extreme = h[i]
        elif lower / rng >= 0.60 and c[i] > mid:
            direction = 1
            extreme = l[i]
        else:
            continue
        funnel["n_wick"] += 1
        j = i  # signal on closed H4 i; enter next open
        if not tradeable(int(t[j])):
            continue
        entry = float(o[i + 1])
        sl = extreme + 0.1 * atr[i] if direction < 0 else extreme - 0.1 * atr[i]
        dist = abs(entry - sl)
        if dist < 0.8 or dist > 100:
            continue
        tp = entry + dist * RR if direction > 0 else entry - dist * RR
        r = resolve(direction, entry, sl, tp, i + 1, h, l, c, 16)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack("HYP-XAUUSD-H4-WICK-REJECT-FADE-001", "XAUUSD", "H4", funnel, trades)


def main() -> int:
    if not mt5.initialize():
        raise RuntimeError(mt5.last_error())
    try:
        for s in ("EURUSD", "GBPUSD", "XAUUSD"):
            mt5.symbol_select(s, True)
        eur_h1 = load("EURUSD", mt5.TIMEFRAME_H1)
        eur_d1 = load("EURUSD", mt5.TIMEFRAME_D1)
        gbp_h1 = load("GBPUSD", mt5.TIMEFRAME_H1)
        gbp_h4 = load("GBPUSD", mt5.TIMEFRAME_H4)
        xau_h1 = load("XAUUSD", mt5.TIMEFRAME_H1)
        xau_h4 = load("XAUUSD", mt5.TIMEFRAME_H4)
        acc = mt5.account_info()
        server = getattr(acc, "server", None)
        login = getattr(acc, "login", None)
    finally:
        mt5.shutdown()

    probes = [
        probe_eur_london_overlap(eur_h1),
        probe_gbp_ny_impulse(gbp_h1),
        probe_xau_asia_compress(xau_h1),
        probe_eur_d1_outside_fade(eur_d1, eur_h1),
        probe_gbp_h4_break_h1_pb(gbp_h4, gbp_h1),
        probe_xau_h4_wick(xau_h4),
    ]
    survivors = [p["hypothesis_id"] for p in probes if p["verdict"] == "PROBE_SURVIVOR"]
    parks = [p["hypothesis_id"] for p in probes if p["verdict"] == "PARK_OFFLINE"]
    payload = {
        "schema_version": "sonic_structural_offline_probes.v6_multisym",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_FIRST_V6_MULTISYM_COMPLETE",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "escape": "USDJPY_TF_SATURATION_EXPLICIT",
        "server": server,
        "login": login,
        "dedup": "readouts/20260714_STRUCTURAL_V6_MULTISYM_DEDUP_CLEARANCE.md",
        "probes": probes,
        "offline_survivors": survivors,
        "offline_parks": parks,
        "any_model0_authorized": bool(survivors),
        "phase0_compose": "NOT_WAITED_DISCOVERY_CONTINUES",
        "best_shelf": "RR2 20260714_194548",
        "banned": [
            "usdjpy_v1_v5_retune",
            "densify_maxkz_rr",
            "model0_on_kill",
            "phase0_wait_stall",
            "xau_hour_day_mine",
        ],
    }
    out = PRE / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V6.json"
    write_json(out, payload)
    sha = sha256_file(out)

    lines = [
        "# Structural rebuild offline probes V6 (multi-symbol)",
        "",
        f"Generated: {payload['created_at_utc']}",
        "Escape: **USDJPY TF saturation** → EURUSD / GBPUSD / XAUUSD",
        "De-dup: `20260714_STRUCTURAL_V6_MULTISYM_DEDUP_CLEARANCE.md`",
        "",
        "| ID | Sym | N | PF | tpw | cost×1.5 PF | Verdict |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for p in probes:
        m = p["metrics"]
        lines.append(
            f"| `{p['hypothesis_id']}` | {p['symbol']} | {m['n']} | {m['pf']:.3f} | "
            f"{m['tpw']:.2f} | {m['pf_x15_cost']:.3f} | **{p['verdict']}** |"
        )
    lines += [
        "",
        f"Survivors: `{survivors}`",
        f"Model 0 authorized: `{payload['any_model0_authorized']}`",
        f"Receipt SHA: `{sha}`",
        "",
        "## Funnels",
        "",
    ]
    for p in probes:
        lines.append(f"- `{p['hypothesis_id']}`: {p['funnel']} notes={p['kill_notes']}")
    lines += [
        "",
        "Best shelf RR2 `194548` unchanged. No Phase-0 wait.",
    ]
    (READ / "20260714_STRUCTURAL_REBUILD_OFFLINE_PROBES_V6.md").write_text(
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
                        "reason": f"offline V6 multisym {p['metrics']}; {p['kill_notes']}",
                        "updated_at": "2026-07-14",
                        "lane": "structural_rebuild_v6_multisym_20260714",
                        "symbol": p["symbol"],
                        "timeframe": p["tf"],
                        "model": "offline_closed_bar_probe",
                        "metrics": p["metrics"],
                        "validation": {"model0": p["model0"]},
                        "receipt_sha256": sha,
                        "dedup": "readouts/20260714_STRUCTURAL_V6_MULTISYM_DEDUP_CLEARANCE.md",
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
                        "sym": p["symbol"],
                        "verdict": p["verdict"],
                        "n": p["metrics"]["n"],
                        "pf": round(p["metrics"]["pf"], 3),
                        "tpw": round(p["metrics"]["tpw"], 3),
                        "x15": round(p["metrics"]["pf_x15_cost"], 3),
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
