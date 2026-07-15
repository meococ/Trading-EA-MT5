#!/usr/bin/env python3
"""Discovery Wave6 pack B — mother-bar / 3-day HL / USDCHF London range.

NOT Model 0. Kill-fast offline. Outside V7/V8 / Wave6A kill shelf.
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
RR = 3.0


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
            "pf_x15_cost12": 0.0,
            "pf_x2_cost12": 0.0,
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
    n = len(pnls)

    def pf_at(mult: float) -> float:
        adj = [p - mult * cost for p in pnls]
        w = [p for p in adj if p > 0]
        l = [-p for p in adj if p < 0]
        return (sum(w) / sum(l)) if l else (999.0 if w else 0.0)

    return {
        "n": n,
        "pf": float(pf),
        "tpw": n / ELAPSED_WEEKS,
        "exp": sum(pnls) / n,
        "net": sum(pnls),
        "pf_x15_cost12": float(pf_at(1.5)),
        "pf_x2_cost12": float(pf_at(2.0)),
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


def resolve(direction, entry, sl, tp, i0, h, l, c, max_hold, rr_hit=RR):
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


def by_day_index(t: np.ndarray) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for i, ts in enumerate(t):
        out.setdefault(day_key(int(ts)), []).append(i)
    return out


def min_dist(symbol: str) -> float:
    return 0.03 if "JPY" in symbol else 0.0003


def max_dist(symbol: str) -> float:
    return 2.0 if "JPY" in symbol else 0.02


def probe_mother_bar(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_mother": 0, "n_inside": 0, "n_break": 0, "n_trades": 0}
    i = 20
    while i < len(c) - 8:
        if math.isnan(atr[i]) or atr[i] <= 0:
            i += 1
            continue
        if (h[i] - l[i]) < 1.5 * atr[i]:
            i += 1
            continue
        funnel["n_mother"] += 1
        j = i + 1
        if j >= len(c) - 5:
            break
        # inside child
        if not (h[j] <= h[i] and l[j] >= l[i]):
            i += 1
            continue
        funnel["n_inside"] += 1
        mhi, mlo = float(h[i]), float(l[i])
        broke = False
        for k in range(j + 1, min(j + 5, len(c) - 2)):
            if not tradeable(int(t[k])):
                continue
            up = c[k] > mhi
            dn = c[k] < mlo
            if not (up or dn):
                continue
            funnel["n_break"] += 1
            if k + 1 >= len(c) - 1 or not tradeable(int(t[k + 1])):
                break
            direction = 1 if up else -1
            entry = float(o[k + 1])
            extreme = mlo if up else mhi
            sl = extreme - 0.1 * atr[k] if up else extreme + 0.1 * atr[k]
            dist = abs(entry - sl)
            if dist < min_dist("USDJPY") or dist > max_dist("USDJPY"):
                break
            tp = entry + dist * RR if up else entry - dist * RR
            r = resolve(direction, entry, sl, tp, k + 1, h, l, c, 18)
            if r is None:
                break
            trades.append({"r": r})
            funnel["n_trades"] += 1
            broke = True
            i = k + 12
            break
        if not broke:
            i += 1
    return pack("HYP-H1-MOTHER-BAR-BREAK-001", "USDJPY", "H1", funnel, trades)


def probe_three_day_break(h1: dict, d1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    d1t, d1h, d1l = d1["time"], d1["high"], d1["low"]
    # map day -> (hi, lo) for complete D1 bars
    dmap = {}
    for i in range(len(d1t)):
        dmap[day_key(int(d1t[i]))] = (float(d1h[i]), float(d1l[i]))
    days_sorted = sorted(dmap.keys())
    day_to_idx = {d: i for i, d in enumerate(days_sorted)}
    trades = []
    funnel = {"n_eligible": 0, "n_break": 0, "n_trades": 0}
    taken = set()
    for i in range(40, len(c) - 3):
        if not tradeable(int(t[i])):
            continue
        dk = day_key(int(t[i]))
        if dk in taken:
            continue
        if dk not in day_to_idx or day_to_idx[dk] < 3:
            continue
        # prior 3 complete days = days before today
        di = day_to_idx[dk]
        prior = days_sorted[di - 3 : di]
        if len(prior) < 3:
            continue
        phi = max(dmap[d][0] for d in prior)
        plo = min(dmap[d][1] for d in prior)
        if math.isnan(atr[i]) or atr[i] <= 0:
            continue
        body = abs(c[i] - o[i])
        if body < 0.5 * atr[i]:
            continue
        funnel["n_eligible"] += 1
        up = c[i] > phi
        dn = c[i] < plo
        if not (up or dn):
            continue
        funnel["n_break"] += 1
        if i + 1 >= len(c) - 1 or not tradeable(int(t[i + 1])):
            continue
        direction = 1 if up else -1
        entry = float(o[i + 1])
        extreme = plo if up else phi
        sl = extreme - 0.1 * atr[i] if up else extreme + 0.1 * atr[i]
        dist = abs(entry - sl)
        if dist < min_dist("USDJPY") or dist > max_dist("USDJPY"):
            continue
        tp = entry + dist * RR if up else entry - dist * RR
        r = resolve(direction, entry, sl, tp, i + 1, h, l, c, 24)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
        taken.add(dk)
    return pack("HYP-H1-THREE-DAY-HIGHLOW-BREAK-001", "USDJPY", "H1", funnel, trades)


def probe_usdchf_london(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_days": 0, "n_break": 0, "n_trades": 0}
    for _, idxs in by_day_index(t).items():
        box = [i for i in idxs if 7 <= hour_u(int(t[i])) < 10]
        if len(box) < 3:
            continue
        funnel["n_days"] += 1
        bhi = max(h[i] for i in box)
        blo = min(l[i] for i in box)
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
        # accept: still outside box
        if up and c[j] <= bhi:
            continue
        if (not up) and c[j] >= blo:
            continue
        if math.isnan(atr[j]) or atr[j] <= 0:
            continue
        direction = 1 if up else -1
        entry = float(o[j + 1]) if j + 1 < len(c) else float(o[j])
        entry_i = j + 1 if j + 1 < len(c) else j
        if not tradeable(int(t[entry_i])):
            continue
        extreme = blo if up else bhi
        sl = extreme - 0.1 * atr[j] if up else extreme + 0.1 * atr[j]
        dist = abs(entry - sl)
        if dist < min_dist("USDCHF") or dist > max_dist("USDCHF"):
            continue
        tp = entry + dist * RR if up else entry - dist * RR
        r = resolve(direction, entry, sl, tp, entry_i, h, l, c, 12)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack("HYP-USDCHF-H1-LONDON-RANGE-BREAK-001", "USDCHF", "H1", funnel, trades)


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        acc = mt5.account_info()
        usdjpy_h1 = load("USDJPY", mt5.TIMEFRAME_H1)
        usdjpy_d1 = load("USDJPY", mt5.TIMEFRAME_D1)
        usdchf_h1 = load("USDCHF", mt5.TIMEFRAME_H1)
        probes = [
            probe_mother_bar(usdjpy_h1),
            probe_three_day_break(usdjpy_h1, usdjpy_d1),
            probe_usdchf_london(usdchf_h1),
        ]
    finally:
        mt5.shutdown()

    survivors = [p for p in probes if p["verdict"] == "PROBE_SURVIVOR"]
    out = {
        "schema_version": "sonic_discovery_wave6b_offline_probes.v1",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_WAVE6B_COMPLETE",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "dedup": "readouts/20260714_DISCOVERY_WAVE6B_DEDUP_CLEARANCE.md",
        "server": getattr(acc, "server", None) if acc else None,
        "login": getattr(acc, "login", None) if acc else None,
        "probes": probes,
        "survivors": [p["hypothesis_id"] for p in survivors],
        "model0_authorized": bool(survivors),
    }
    json_path = PRE / "20260714_DISCOVERY_WAVE6B_OFFLINE_PROBES.json"
    write_json(json_path, out)
    sha = sha256_file(json_path)
    out["receipt_sha256"] = sha
    write_json(json_path, out)

    lines = [
        "# Discovery Wave6 pack B — offline probes",
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
        lines.append(f"- `{p['hypothesis_id']}`: {p['funnel']} notes={p['kill_notes']}")
    lines += ["", "Do not densify pack B params. Cost: `UNVERIFIED_OFFLINE_PROXY`.", ""]
    (READ / "20260714_DISCOVERY_WAVE6B_OFFLINE_PROBES.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    with REG.open("a", encoding="utf-8") as f:
        for p in probes:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": p["hypothesis_id"],
                        "state": "killed" if "KILL" in p["verdict"] else (
                            "parked" if "PARK" in p["verdict"] else "probe"
                        ),
                        "parent_candidate": "DISCOVERY_WAVE6B_OFFLINE",
                        "feature_family": p["hypothesis_id"].lower().replace("-", "_"),
                        "lane": "discovery_wave6_20260714",
                        "setup_type": p["hypothesis_id"],
                        "symbol": p["symbol"],
                        "timeframe": p["tf"],
                        "window": "2021.01.01-2025.12.31",
                        "model": None,
                        "prereg_path": None,
                        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_DISCOVERY_WAVE6B_OFFLINE_PROBES.md",
                        "metrics": p["metrics"],
                        "validation": {
                            "offline_probe": p["verdict"],
                            "kill_notes": p["kill_notes"],
                            "model0": p["model0"],
                        },
                        "verdict": p["verdict"],
                        "cost_grade": "UNVERIFIED_OFFLINE_PROXY",
                        "updated_at": "2026-07-14",
                        "receipt_sha256": sha,
                        "dedup": "readouts/20260714_DISCOVERY_WAVE6B_DEDUP_CLEARANCE.md",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        json.dumps(
            {
                "sha": sha,
                "survivors": out["survivors"],
                "board": [
                    {
                        "id": p["hypothesis_id"],
                        "verdict": p["verdict"],
                        "m": {
                            "n": p["metrics"]["n"],
                            "pf": round(p["metrics"]["pf"], 3),
                            "tpw": round(p["metrics"]["tpw"], 2),
                            "x15": round(p["metrics"]["pf_x15_cost12"], 3),
                        },
                    }
                    for p in probes
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
