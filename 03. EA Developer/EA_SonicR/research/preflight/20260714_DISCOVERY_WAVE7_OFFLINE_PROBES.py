#!/usr/bin/env python3
"""Discovery Wave7 — new price objects + thick-park compose.

NOT Model 0. Kill-fast offline. Outside Wave6/V1–V8 densify bans.
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def atr14(h, l, c):
    n = len(c)
    prev_c = np.empty(n)
    prev_c[0] = c[0]
    prev_c[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    out = np.full(n, np.nan)
    if n < 14:
        return out
    out[13] = tr[:14].mean()
    alpha = 1.0 / 14.0
    for i in range(14, n):
        out[i] = out[i - 1] * (1.0 - alpha) + tr[i] * alpha
    return out


def load(symbol, tf):
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"symbol_select fail {symbol}: {mt5.last_error()}")
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


def week_key(ts: int) -> str:
    dt = datetime.fromtimestamp(ts, timezone.utc)
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


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


def pack(hid, symbol, tf, funnel, trades, extra=None) -> dict[str, Any]:
    m = sim_r(trades)
    verdict, notes = gate(m)
    out = {
        "hypothesis_id": hid,
        "symbol": symbol,
        "tf": tf,
        "funnel": funnel,
        "metrics": m,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }
    if extra:
        out["extra"] = extra
    return out


def by_day_index(t: np.ndarray) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for i, ts in enumerate(t):
        out.setdefault(day_key(int(ts)), []).append(i)
    return out


def min_dist(symbol: str) -> float:
    return 0.03 if "JPY" in symbol else 0.0003


def max_dist(symbol: str) -> float:
    return 2.0 if "JPY" in symbol else 0.02


def probe_nzdusd_asia_london(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_days": 0, "n_break": 0, "n_trades": 0}
    rr = 3.0
    for _, idxs in by_day_index(t).items():
        asia = [i for i in idxs if 0 <= hour_u(int(t[i])) < 7]
        if len(asia) < 4:
            continue
        funnel["n_days"] += 1
        bhi = max(h[i] for i in asia)
        blo = min(l[i] for i in asia)
        if bhi <= blo:
            continue
        london = [i for i in idxs if 7 <= hour_u(int(t[i])) < 16]
        break_i = None
        up = False
        for i in london:
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
        if j >= len(c) - 2 or not tradeable(int(t[j])):
            continue
        if up and c[j] <= bhi:
            continue
        if (not up) and c[j] >= blo:
            continue
        if math.isnan(atr[j]) or atr[j] <= 0:
            continue
        entry_i = j + 1
        if entry_i >= len(c) - 1 or not tradeable(int(t[entry_i])):
            continue
        direction = 1 if up else -1
        entry = float(o[entry_i])
        extreme = blo if up else bhi
        sl = extreme - 0.1 * atr[j] if up else extreme + 0.1 * atr[j]
        dist = abs(entry - sl)
        if dist < min_dist("NZDUSD") or dist > max_dist("NZDUSD"):
            continue
        tp = entry + dist * rr if up else entry - dist * rr
        r = resolve(direction, entry, sl, tp, entry_i, h, l, c, 12, rr)
        if r is None:
            continue
        trades.append({"r": r, "entry_ts": int(t[entry_i]), "day": day_key(int(t[entry_i]))})
        funnel["n_trades"] += 1
    return pack(
        "HYP-NZDUSD-H1-ASIA-RANGE-LONDON-BREAK-001",
        "NZDUSD",
        "H1",
        funnel,
        trades,
    )


def probe_w1_open_accept(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    # prior week open = first H1 open of that ISO week
    week_open: dict[str, float] = {}
    week_first_ts: dict[str, int] = {}
    for i, ts in enumerate(t):
        wk = week_key(int(ts))
        if wk not in week_first_ts or int(ts) < week_first_ts[wk]:
            week_first_ts[wk] = int(ts)
            week_open[wk] = float(o[i])
    weeks_sorted = sorted(week_open.keys())
    w_idx = {w: i for i, w in enumerate(weeks_sorted)}
    trades = []
    funnel = {"n_eligible": 0, "n_signal": 0, "n_trades": 0}
    taken = set()
    rr = 3.0
    for i in range(40, len(c) - 3):
        if not tradeable(int(t[i])):
            continue
        wk = week_key(int(t[i]))
        if wk in taken or wk not in w_idx or w_idx[wk] < 1:
            continue
        prior_wk = weeks_sorted[w_idx[wk] - 1]
        wo = week_open[prior_wk]
        if math.isnan(atr[i]) or atr[i] <= 0:
            continue
        body = abs(c[i] - o[i])
        if body < 0.45 * atr[i]:
            continue
        funnel["n_eligible"] += 1
        up = c[i] > wo + 0.15 * atr[i]
        dn = c[i] < wo - 0.15 * atr[i]
        if not (up or dn):
            continue
        funnel["n_signal"] += 1
        if i + 1 >= len(c) - 1 or not tradeable(int(t[i + 1])):
            continue
        direction = 1 if up else -1
        entry = float(o[i + 1])
        sl = wo - 0.1 * atr[i] if up else wo + 0.1 * atr[i]
        dist = abs(entry - sl)
        if dist < min_dist("USDJPY") or dist > max_dist("USDJPY"):
            continue
        tp = entry + dist * rr if up else entry - dist * rr
        r = resolve(direction, entry, sl, tp, i + 1, h, l, c, 24, rr)
        if r is None:
            continue
        trades.append({"r": r, "entry_ts": int(t[i + 1]), "day": day_key(int(t[i + 1]))})
        funnel["n_trades"] += 1
        taken.add(wk)
    return pack("HYP-W1-OPEN-H1-ACCEPT-CONT-001", "USDJPY", "H1", funnel, trades)


def probe_london_mid_reclaim(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades = []
    funnel = {"n_days": 0, "n_pierce": 0, "n_trades": 0}
    rr = 3.0
    for _, idxs in by_day_index(t).items():
        box = [i for i in idxs if 7 <= hour_u(int(t[i])) < 12]
        if len(box) < 3:
            continue
        funnel["n_days"] += 1
        bhi = max(h[i] for i in box)
        blo = min(l[i] for i in box)
        mid = 0.5 * (bhi + blo)
        if bhi <= blo:
            continue
        # post-box window for pierce+reclaim same day until 16
        post = [i for i in idxs if 12 <= hour_u(int(t[i])) < 16]
        pierce_dir = 0
        pierce_i = None
        for i in post:
            if c[i] > mid and h[i] > mid:
                # need actual pierce beyond mid with prior below or touch
                pierce_dir, pierce_i = 1, i
                break
            if c[i] < mid and l[i] < mid:
                pierce_dir, pierce_i = -1, i
                break
        if pierce_i is None:
            continue
        funnel["n_pierce"] += 1
        # reclaim: next closed bar closes back through mid in pierce direction
        # cont interpretation: pierce UP then reclaim = close back above mid after dip below? 
        # Spec: pierce beyond mid then closed reclaim back through mid in direction of pierce
        # = pierce up (close>mid), then a bar that dipped <=mid and closes >mid again → long
        # = pierce dn, then bar that spiked >=mid and closes <mid → short
        found = False
        for j in range(pierce_i + 1, min(pierce_i + 5, len(c) - 2)):
            if j not in post and hour_u(int(t[j])) >= 16:
                break
            if not tradeable(int(t[j])):
                continue
            if pierce_dir > 0:
                if l[j] <= mid and c[j] > mid:
                    found = True
                else:
                    continue
            else:
                if h[j] >= mid and c[j] < mid:
                    found = True
                else:
                    continue
            if not found:
                continue
            if math.isnan(atr[j]) or atr[j] <= 0:
                break
            entry_i = j + 1
            if entry_i >= len(c) - 1 or not tradeable(int(t[entry_i])):
                break
            direction = pierce_dir
            entry = float(o[entry_i])
            sl = mid - 0.15 * atr[j] if direction > 0 else mid + 0.15 * atr[j]
            dist = abs(entry - sl)
            if dist < min_dist("USDJPY") or dist > max_dist("USDJPY"):
                break
            tp = entry + dist * rr if direction > 0 else entry - dist * rr
            r = resolve(direction, entry, sl, tp, entry_i, h, l, c, 10, rr)
            if r is None:
                break
            trades.append({"r": r, "entry_ts": int(t[entry_i]), "day": day_key(int(t[entry_i]))})
            funnel["n_trades"] += 1
            break
    return pack("HYP-H1-LONDON-MID-RECLAIM-CONT-001", "USDJPY", "H1", funnel, trades)


def probe_aud_lead_eur(aud: dict, eur: dict) -> dict[str, Any]:
    eur_t = eur["time"]
    eur_ts_to_i = {int(ts): i for i, ts in enumerate(eur_t)}
    eur_ts_sorted = np.array(sorted(eur_ts_to_i.keys()), dtype=np.int64)
    ao, ah, al, ac = aud["open"], aud["high"], aud["low"], aud["close"]
    eo, eh, el, ec = eur["open"], eur["high"], eur["low"], eur["close"]
    a_atr = atr14(ah, al, ac)
    e_atr = atr14(eh, el, ec)
    trades = []
    funnel = {"n_lead": 0, "n_follow": 0, "n_trades": 0}
    rr = 2.5
    taken = set()

    def eur_index_in_hour(target: int) -> int | None:
        pos = int(np.searchsorted(eur_ts_sorted, target, side="left"))
        if pos >= len(eur_ts_sorted):
            return None
        ts = int(eur_ts_sorted[pos])
        if ts < target + 3600:
            return eur_ts_to_i[ts]
        return None

    for i in range(20, len(ac) - 4):
        if not tradeable(int(aud["time"][i])):
            continue
        if math.isnan(a_atr[i]) or a_atr[i] <= 0:
            continue
        body = abs(ac[i] - ao[i])
        if body < 0.70 * a_atr[i]:
            continue
        lead_dir = 1 if ac[i] > ao[i] else -1
        funnel["n_lead"] += 1
        lead_ts = int(aud["time"][i])
        for lag in (1, 2):
            j = eur_index_in_hour(lead_ts + lag * 3600)
            if j is None or j + 1 >= len(ec) - 1:
                continue
            if not tradeable(int(eur_t[j])):
                continue
            if math.isnan(e_atr[j]) or e_atr[j] <= 0:
                continue
            ebody = abs(ec[j] - eo[j])
            if ebody < 0.40 * e_atr[j]:
                continue
            follow_dir = 1 if ec[j] > eo[j] else -1
            if follow_dir != lead_dir:
                continue
            funnel["n_follow"] += 1
            dk = day_key(int(eur_t[j]))
            if dk in taken:
                break
            entry_i = j + 1
            if not tradeable(int(eur_t[entry_i])):
                break
            direction = lead_dir
            entry = float(eo[entry_i])
            sl = el[j] - 0.1 * e_atr[j] if direction > 0 else eh[j] + 0.1 * e_atr[j]
            dist = abs(entry - sl)
            if dist < min_dist("EURUSD") or dist > max_dist("EURUSD"):
                break
            tp = entry + dist * rr if direction > 0 else entry - dist * rr
            r = resolve(direction, entry, sl, tp, entry_i, eh, el, ec, 12, rr)
            if r is None:
                break
            trades.append({"r": r, "entry_ts": int(eur_t[entry_i]), "day": dk})
            funnel["n_trades"] += 1
            taken.add(dk)
            break
    return pack("HYP-AUDUSD-LEAD-EURUSD-H1-001", "EURUSD", "H1", funnel, trades)


def probe_weekend_gap_fill(h1: dict) -> dict[str, Any]:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    # group by day
    days = by_day_index(t)
    day_list = sorted(days.keys())
    trades = []
    funnel = {"n_gaps": 0, "n_trades": 0}
    rr = 2.0
    for di, dk in enumerate(day_list):
        idxs = days[dk]
        # Monday = weekday 0 in python; mt5_dow: Sun=0 Mon=1 ...
        if mt5_dow(int(t[idxs[0]])) != 1:
            continue
        # find Friday = previous calendar trading day with dow==5 (Fri mt5_dow=5)
        fri_idxs = None
        for back in range(1, 5):
            if di - back < 0:
                break
            prev = day_list[di - back]
            if mt5_dow(int(t[days[prev][0]])) == 5:
                fri_idxs = days[prev]
                break
        if not fri_idxs:
            continue
        fri_close = float(c[fri_idxs[-1]])
        mon_open_i = idxs[0]
        # first tradeable Mon bar
        for i in idxs:
            if tradeable(int(t[i])) or hour_u(int(t[i])) >= 0:
                mon_open_i = i
                break
        if math.isnan(atr[mon_open_i]) or atr[mon_open_i] <= 0:
            continue
        mon_open = float(o[mon_open_i])
        gap = mon_open - fri_close
        if abs(gap) < 0.35 * atr[mon_open_i]:
            continue
        funnel["n_gaps"] += 1
        # fade toward Friday close
        direction = -1 if gap > 0 else 1
        entry_i = mon_open_i
        if entry_i + 1 < len(c) and tradeable(int(t[entry_i + 1])):
            entry_i = entry_i + 1
        if not tradeable(int(t[entry_i])) and hour_u(int(t[entry_i])) >= 22:
            continue
        entry = float(o[entry_i])
        # SL beyond Monday first bar extreme opposite to fade
        if direction < 0:  # short gap-up
            sl = float(h[mon_open_i]) + 0.1 * atr[mon_open_i]
        else:
            sl = float(l[mon_open_i]) - 0.1 * atr[mon_open_i]
        dist = abs(entry - sl)
        if dist < min_dist("EURUSD") or dist > max_dist("EURUSD"):
            continue
        # TP at Friday close (fill) — encode as RR via distance to fill
        fill_dist = abs(entry - fri_close)
        if fill_dist <= 0:
            continue
        # use fixed RR=2 relative to SL risk (may overshoot fill — ok)
        tp = entry + dist * rr if direction > 0 else entry - dist * rr
        r = resolve(direction, entry, sl, tp, entry_i, h, l, c, 12, rr)
        if r is None:
            continue
        trades.append({"r": r, "entry_ts": int(t[entry_i]), "day": dk})
        funnel["n_trades"] += 1
    return pack("HYP-EURUSD-H1-WEEKEND-GAP-FILL-001", "EURUSD", "H1", funnel, trades)


def probe_three_day_trades(h1: dict, d1: dict) -> list[dict]:
    """Replicate Wave6B three-day HL for compose (frozen params)."""
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    d1t, d1h, d1l = d1["time"], d1["high"], d1["low"]
    dmap = {}
    for i in range(len(d1t)):
        dmap[day_key(int(d1t[i]))] = (float(d1h[i]), float(d1l[i]))
    days_sorted = sorted(dmap.keys())
    day_to_idx = {d: i for i, d in enumerate(days_sorted)}
    trades = []
    taken = set()
    rr = 3.0
    for i in range(40, len(c) - 3):
        if not tradeable(int(t[i])):
            continue
        dk = day_key(int(t[i]))
        if dk in taken:
            continue
        if dk not in day_to_idx or day_to_idx[dk] < 3:
            continue
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
        up = c[i] > phi
        dn = c[i] < plo
        if not (up or dn):
            continue
        if i + 1 >= len(c) - 1 or not tradeable(int(t[i + 1])):
            continue
        direction = 1 if up else -1
        entry = float(o[i + 1])
        extreme = plo if up else phi
        sl = extreme - 0.1 * atr[i] if up else extreme + 0.1 * atr[i]
        dist = abs(entry - sl)
        if dist < min_dist("USDJPY") or dist > max_dist("USDJPY"):
            continue
        tp = entry + dist * rr if up else entry - dist * rr
        r = resolve(direction, entry, sl, tp, i + 1, h, l, c, 24, rr)
        if r is None:
            continue
        trades.append({"r": r, "entry_ts": int(t[i + 1]), "day": dk, "sleeve": "3day"})
        taken.add(dk)
    return trades


def atr14_sma(h, l, c):
    """Simple 14-TR mean (matches London-open-drive parked probe)."""
    n = len(c)
    out = np.zeros(n)
    for i in range(14, n):
        trs = []
        for j in range(i - 13, i + 1):
            prev = c[j - 1]
            trs.append(max(h[j] - l[j], abs(h[j] - prev), abs(l[j] - prev)))
        out[i] = sum(trs) / 14.0
    return out


def probe_london_drive_trades(h1: dict) -> list[dict]:
    """Replicate London-open-drive frozen params for compose (N≈104 fidelity)."""
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14_sma(h, l, c)
    trades = []
    rr = 2.5
    for i in range(20, len(c) - 3):
        # Python weekday Mon=0..; skip Fri+ (weekday>3) per parked probe
        wd = datetime.fromtimestamp(int(t[i]), timezone.utc).weekday()
        if wd > 3:
            continue
        if hour_u(int(t[i])) != 7:
            continue
        a = atr[i]
        if a <= 0:
            continue
        rng = h[i] - l[i]
        if rng <= 0:
            continue
        body = abs(c[i] - o[i])
        if body < 0.50 * a:
            continue
        direction = 0
        if c[i] > o[i] and (c[i] - l[i]) / rng >= 0.67:
            direction = 1
        elif c[i] < o[i] and (h[i] - c[i]) / rng >= 0.67:
            direction = -1
        else:
            continue
        entry = float(c[i])
        sl = (l[i] - 0.1 * a) if direction > 0 else (h[i] + 0.1 * a)
        dist = abs(entry - sl)
        if dist <= 0:
            continue
        tp = entry + dist * rr if direction > 0 else entry - dist * rr
        r = None
        for j in range(i + 1, min(i + 1 + 8, len(c))):
            wdj = datetime.fromtimestamp(int(t[j]), timezone.utc).weekday()
            if hour_u(int(t[j])) >= 16 or wdj >= 4:
                r = (c[j] - entry) / dist if direction > 0 else (entry - c[j]) / dist
                break
            if direction > 0:
                if l[j] <= sl:
                    r = -1.0
                    break
                if h[j] >= tp:
                    r = float(rr)
                    break
            else:
                if h[j] >= sl:
                    r = -1.0
                    break
                if l[j] <= tp:
                    r = float(rr)
                    break
            r = (c[j] - entry) / dist if direction > 0 else (entry - c[j]) / dist
        if r is None:
            continue
        trades.append(
            {
                "r": float(r),
                "entry_ts": int(t[i]),
                "day": day_key(int(t[i])),
                "sleeve": "london_drive",
            }
        )
    return trades


def probe_compose(h1: dict, d1: dict) -> dict[str, Any]:
    a = probe_three_day_trades(h1, d1)
    b = probe_london_drive_trades(h1)
    # equal-join all trades chronologically
    pooled = sorted(a + b, key=lambda x: x["entry_ts"])
    days_a = {t["day"] for t in a}
    days_b = {t["day"] for t in b}
    same_day = days_a & days_b
    # same entry timestamp overlap
    ts_a = {t["entry_ts"] for t in a}
    ts_b = {t["entry_ts"] for t in b}
    exact_ts = ts_a & ts_b
    extra = {
        "sleeve_a_n": len(a),
        "sleeve_b_n": len(b),
        "same_day_overlap": len(same_day),
        "exact_entry_ts_overlap": len(exact_ts),
        "compose_rule": "a_priori_equal_join_3day_PARK_plus_london_drive_thick",
    }
    return pack(
        "HYP-BOOK-COMPOSE-3DAY-LONDONDRIVE-001",
        "USDJPY",
        "H1",
        {"n_3day": len(a), "n_london_drive": len(b), "n_pooled": len(pooled)},
        pooled,
        extra=extra,
    )


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        acc = mt5.account_info()
        print("loading rates...", flush=True)
        nzd = load("NZDUSD", mt5.TIMEFRAME_H1)
        usdjpy_h1 = load("USDJPY", mt5.TIMEFRAME_H1)
        usdjpy_d1 = load("USDJPY", mt5.TIMEFRAME_D1)
        aud = load("AUDUSD", mt5.TIMEFRAME_H1)
        eur = load("EURUSD", mt5.TIMEFRAME_H1)
        print("probing...", flush=True)
        probes = []
        for name, fn in (
            ("NZD", lambda: probe_nzdusd_asia_london(nzd)),
            ("W1OPEN", lambda: probe_w1_open_accept(usdjpy_h1)),
            ("MID", lambda: probe_london_mid_reclaim(usdjpy_h1)),
            ("AUDLEAD", lambda: probe_aud_lead_eur(aud, eur)),
            ("GAP", lambda: probe_weekend_gap_fill(eur)),
            ("COMPOSE", lambda: probe_compose(usdjpy_h1, usdjpy_d1)),
        ):
            print(f"  {name}...", flush=True)
            probes.append(fn())
            print(f"  {name} done n={probes[-1]['metrics']['n']}", flush=True)
    finally:
        mt5.shutdown()

    survivors = [p for p in probes if p["verdict"] == "PROBE_SURVIVOR"]
    out = {
        "schema_version": "sonic_discovery_wave7_offline_probes.v1",
        "created_at_utc": utc_now(),
        "status": "OFFLINE_WAVE7_COMPLETE",
        "honesty": "NOT_MODEL0_NOT_CONFIRMED_NOT_GOAL",
        "dedup": "readouts/20260714_DISCOVERY_WAVE7_DEDUP_CLEARANCE.md",
        "server": getattr(acc, "server", None) if acc else None,
        "login": getattr(acc, "login", None) if acc else None,
        "probes": probes,
        "survivors": [p["hypothesis_id"] for p in survivors],
        "model0_authorized": bool(survivors),
        "screen": "PF>1.30 AND tpw[2,5] AND x1.5>=1.25 AND x2>=1.00",
    }
    json_path = PRE / "20260714_DISCOVERY_WAVE7_OFFLINE_PROBES.json"
    write_json(json_path, out)
    sha = sha256_file(json_path)
    out["receipt_sha256"] = sha
    write_json(json_path, out)

    lines = [
        "# Discovery Wave7 — offline probes",
        "",
        f"Generated: {out['created_at_utc']}",
        f"De-dup: `{out['dedup']}`",
        f"Receipt SHA: `{sha}`",
        f"Server/login: `{out['server']}` / `{out['login']}`",
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
        "## Funnels / extras",
        "",
    ]
    for p in probes:
        lines.append(
            f"- `{p['hypothesis_id']}`: funnel={p['funnel']} notes={p['kill_notes']}"
            + (f" extra={p.get('extra')}" if p.get("extra") else "")
        )
    lines += [
        "",
        "Do not densify Wave7 params. Cost: `UNVERIFIED_OFFLINE_PROXY`.",
        "Compose is a priori thick-park join — not Phase-0 SB/Spark reopen.",
        "",
    ]
    (READ / "20260714_DISCOVERY_WAVE7_OFFLINE_PROBES.md").write_text(
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
                        "state": (
                            "killed"
                            if "KILL" in p["verdict"]
                            else ("parked" if "PARK" in p["verdict"] else "probe")
                        ),
                        "parent_candidate": "DISCOVERY_WAVE7_OFFLINE",
                        "feature_family": p["hypothesis_id"].lower().replace("-", "_"),
                        "lane": "discovery_wave7_20260714",
                        "setup_type": p["hypothesis_id"],
                        "symbol": p["symbol"],
                        "timeframe": p["tf"],
                        "window": "2021.01.01-2025.12.31",
                        "model": None,
                        "prereg_path": None,
                        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260714_DISCOVERY_WAVE7_OFFLINE_PROBES.md",
                        "metrics": p["metrics"],
                        "validation": {
                            "offline_probe": p["verdict"],
                            "kill_notes": p["kill_notes"],
                            "model0": p["model0"],
                            "extra": p.get("extra"),
                        },
                        "verdict": p["verdict"],
                        "cost_grade": "UNVERIFIED_OFFLINE_PROXY",
                        "updated_at": "2026-07-14",
                        "receipt_sha256": sha,
                        "dedup": "readouts/20260714_DISCOVERY_WAVE7_DEDUP_CLEARANCE.md",
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
                            "x2": round(p["metrics"]["pf_x2_cost12"], 3),
                        },
                        "notes": p["kill_notes"],
                        "extra": p.get("extra"),
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
