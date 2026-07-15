#!/usr/bin/env python3
"""London–NY overlap / EUR–GBP structural objects — offline joint screen.

Authority: EXO_FRED_DISPLACE_SPAM_PAUSED; post MFE/Asia ALL_KILL.
NOT FRED spam. NOT RR2 exit retune. NOT Asia densify. NOT invent cost freeze.
NOT IB/ORB/NY-IB/LORBA/Spark/ITSM densify. NOT MULTISYM 07-10 continue-break
or GBP NY-impulse retune.

A priori frozen (≥2 independent; board runs 3):
  1) HYP-EURUSD-H1-LONDON-IMBAL-NY-FADE-001
  2) HYP-GBPUSD-H1-LONDON-COIL-NY-BREAK-001
  3) HYP-GBPUSD-H1-EURUSD-LEAD-OVERLAP-CATCHUP-001

Model 0 only if PROBE_SURVIVOR. Kill-fast offline.
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
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"

OUT_JSON = PRE / "20260715_LNY_OVERLAP_EURGBP_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_LNY_OVERLAP_EURGBP_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_LNY_OVERLAP_EURGBP_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_LNY_OVERLAP_EURGBP_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_LNY_OVERLAP_EURGBP_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_LNY_OVERLAP_EURGBP_VN_ACTION_BRIEF.md"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

# --- Object 1: EUR London imbalance → NY fade ---
IMBAL_L0, IMBAL_L1 = 7, 12
IMBAL_FIRE0, IMBAL_FIRE1 = 13, 16
IMBAL_MID_ATR = 0.75
IMBAL_RANGE_ATR = 0.80
IMBAL_RR = 2.0
IMBAL_SL_BUF = 0.10
IMBAL_MAX_HOLD = 12

# --- Object 2: GBP London coil → NY break ---
COIL_L0, COIL_L1 = 7, 12
COIL_FIRE0, COIL_FIRE1 = 13, 16
COIL_PCTL = 40.0
COIL_LOOKBACK = 60
COIL_RR = 2.5
COIL_SL_BUF = 0.10
COIL_MAX_HOLD = 12

# --- Object 3: EUR lead → GBP catch-up at overlap ---
LEAD_HOURS = {11, 12}
LEAD_BODY_ATR = 0.80
LAG_BODY_ATR = 0.40
LEAD_SWING = 8
CATCH_FIRE0, CATCH_FIRE1 = 13, 15
CATCH_RR = 2.0
CATCH_SL_ATR = 1.0
CATCH_MAX_HOLD = 10


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float], base: float = BASE_COST) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - base * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls: list[float]) -> dict:
    n = len(pnls)
    p = pf_of(pnls)
    net = sum(pnls) if pnls else 0.0
    tpw = n / WEEKS if WEEKS else None
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(tpw, 4) if tpw is not None else None,
    }


def joint_verdict(m: dict, hc: dict) -> tuple[str, list[str]]:
    notes: list[str] = []
    n = m["n"] or 0
    pf = m["pf"] or 0.0
    tpw = m["tpw"] or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if not (1.5 <= tpw <= 6.0):
        notes.append("cadence_fail")
    if pf <= 1.20:
        notes.append("pf_fail")
    if x15 < 1.15:
        notes.append("stress_fail")
    if (
        n >= 80
        and pf > 1.20
        and 1.5 <= tpw <= 6.0
        and x15 >= 1.15
    ):
        return "PROBE_SURVIVOR", notes
    if not notes:
        notes.append("joint_screen_miss")
    return "KILLED_AT_OFFLINE_PROBE", notes


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


def load(symbol: str) -> dict:
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, FROM, TO)
    if rates is None or len(rates) < 500:
        raise RuntimeError(f"rates fail {symbol}: {mt5.last_error()}")
    return {
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
    }


def mt5_dow(ts: int) -> int:
    return (datetime.fromtimestamp(ts, timezone.utc).weekday() + 1) % 7


def hour_u(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).hour


def day_key(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def tradeable(ts: int) -> bool:
    return mt5_dow(ts) in (1, 2, 3, 4) and hour_u(ts) < 22


def by_day_index(t: np.ndarray) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for i, ts in enumerate(t):
        out.setdefault(day_key(int(ts)), []).append(i)
    return out


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


def pnls_from_r(trades: list[dict]) -> list[float]:
    bal = DEPOSIT
    out = []
    for t in trades:
        pnl = bal * RISK_FRAC * t["r"]
        out.append(pnl)
        bal += pnl
    return out


def pack(hid: str, symbol: str, funnel: dict, trades: list[dict]) -> dict:
    pnls = pnls_from_r(trades)
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": hid,
        "symbol": symbol,
        "tf": "H1",
        "funnel": funnel,
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
        "cost_proxy_usd": BASE_COST,
        "note": "cost proxy +$12/trade flat; NOT research-grade freeze",
    }


def probe_eur_london_imbal_ny_fade(h1: dict) -> dict:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades: list[dict] = []
    funnel = {"n_days": 0, "n_armed": 0, "n_fire": 0, "n_trades": 0}
    for _, idxs in by_day_index(t).items():
        london = [i for i in idxs if IMBAL_L0 <= hour_u(int(t[i])) < IMBAL_L1]
        if len(london) < 4:
            continue
        funnel["n_days"] += 1
        i_ref = london[-1]
        if math.isnan(atr[i_ref]) or atr[i_ref] <= 0:
            continue
        bhi = max(h[i] for i in london)
        blo = min(l[i] for i in london)
        mid = 0.5 * (bhi + blo)
        rng = bhi - blo
        close12 = float(c[i_ref])
        if rng < IMBAL_RANGE_ATR * atr[i_ref]:
            continue
        if abs(close12 - mid) < IMBAL_MID_ATR * atr[i_ref]:
            continue
        funnel["n_armed"] += 1
        # fade toward mid: short if London closed above mid
        fade_short = close12 > mid
        fire = [
            i
            for i in idxs
            if IMBAL_FIRE0 <= hour_u(int(t[i])) < IMBAL_FIRE1 and tradeable(int(t[i]))
        ]
        fire_i = None
        for i in fire:
            if fade_short and c[i] < mid and (i == 0 or c[i - 1] >= mid):
                fire_i = i
                break
            if (not fade_short) and c[i] > mid and (i == 0 or c[i - 1] <= mid):
                fire_i = i
                break
        if fire_i is None:
            continue
        funnel["n_fire"] += 1
        j = fire_i  # enter next open after signal close
        if j + 1 >= len(c) - 1 or not tradeable(int(t[j + 1])):
            continue
        if math.isnan(atr[j]) or atr[j] <= 0:
            continue
        direction = -1 if fade_short else 1
        entry = float(o[j + 1])
        extreme = bhi if fade_short else blo
        sl = (
            extreme + IMBAL_SL_BUF * atr[j]
            if fade_short
            else extreme - IMBAL_SL_BUF * atr[j]
        )
        dist = abs(entry - sl)
        if dist < 0.0003 or dist > 0.025:
            continue
        tp = entry + dist * IMBAL_RR if direction > 0 else entry - dist * IMBAL_RR
        r = resolve(direction, entry, sl, tp, j + 1, h, l, c, IMBAL_MAX_HOLD, IMBAL_RR)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack("HYP-EURUSD-H1-LONDON-IMBAL-NY-FADE-001", "EURUSD", funnel, trades)


def probe_gbp_london_coil_ny_break(h1: dict) -> dict:
    o, h, l, c, t = h1["open"], h1["high"], h1["low"], h1["close"], h1["time"]
    atr = atr14(h, l, c)
    trades: list[dict] = []
    funnel = {
        "n_days": 0,
        "n_coil": 0,
        "n_break": 0,
        "n_trades": 0,
        "coil_pctl": COIL_PCTL,
        "coil_lookback": COIL_LOOKBACK,
    }
    # collect London ranges chronologically for percentile arm
    day_map = by_day_index(t)
    day_keys = sorted(day_map.keys())
    london_ranges: list[float] = []
    day_london: dict[str, tuple[float, float, float, int]] = {}
    for dk in day_keys:
        idxs = day_map[dk]
        london = [i for i in idxs if COIL_L0 <= hour_u(int(t[i])) < COIL_L1]
        if len(london) < 4:
            continue
        bhi = max(h[i] for i in london)
        blo = min(l[i] for i in london)
        i_ref = london[-1]
        day_london[dk] = (bhi, blo, bhi - blo, i_ref)

    for dk in day_keys:
        if dk not in day_london:
            continue
        funnel["n_days"] += 1
        bhi, blo, rng, i_ref = day_london[dk]
        if math.isnan(atr[i_ref]) or atr[i_ref] <= 0:
            london_ranges.append(rng)
            continue
        hist = london_ranges[-COIL_LOOKBACK:]
        london_ranges.append(rng)
        if len(hist) < max(20, COIL_LOOKBACK // 3):
            continue
        thr = float(np.percentile(hist, COIL_PCTL))
        if rng > thr:
            continue
        funnel["n_coil"] += 1
        idxs = day_map[dk]
        fire = [
            i
            for i in idxs
            if COIL_FIRE0 <= hour_u(int(t[i])) < COIL_FIRE1 and tradeable(int(t[i]))
        ]
        break_i = None
        up = False
        for i in fire:
            if c[i] > bhi:
                break_i, up = i, True
                break
            if c[i] < blo:
                break_i, up = i, False
                break
        if break_i is None:
            continue
        funnel["n_break"] += 1
        j = break_i
        if j + 1 >= len(c) - 1 or not tradeable(int(t[j + 1])):
            continue
        if math.isnan(atr[j]) or atr[j] <= 0:
            continue
        direction = 1 if up else -1
        entry = float(o[j + 1])
        extreme = blo if up else bhi
        sl = (
            extreme - COIL_SL_BUF * atr[j]
            if up
            else extreme + COIL_SL_BUF * atr[j]
        )
        dist = abs(entry - sl)
        if dist < 0.0003 or dist > 0.025:
            continue
        tp = entry + dist * COIL_RR if up else entry - dist * COIL_RR
        r = resolve(direction, entry, sl, tp, j + 1, h, l, c, COIL_MAX_HOLD, COIL_RR)
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack("HYP-GBPUSD-H1-LONDON-COIL-NY-BREAK-001", "GBPUSD", funnel, trades)


def probe_gbp_eur_lead_catchup(eur: dict, gbp: dict) -> dict:
    eo, eh, el, ec, et = eur["open"], eur["high"], eur["low"], eur["close"], eur["time"]
    go, gh, gl, gc, gt = gbp["open"], gbp["high"], gbp["low"], gbp["close"], gbp["time"]
    eatr = atr14(eh, el, ec)
    gatr = atr14(gh, gl, gc)
    # align GBP index by timestamp
    g_by_t = {int(ts): i for i, ts in enumerate(gt)}
    trades: list[dict] = []
    funnel = {
        "n_lead_bars": 0,
        "n_lag_ok": 0,
        "n_fire": 0,
        "n_trades": 0,
        "lead_hours_utc": sorted(LEAD_HOURS),
    }
    # process by day on EUR
    for _, eidxs in by_day_index(et).items():
        lead_i = None
        lead_up = False
        for i in eidxs:
            hu = hour_u(int(et[i]))
            if hu not in LEAD_HOURS:
                continue
            if math.isnan(eatr[i]) or eatr[i] <= 0:
                continue
            body = abs(ec[i] - eo[i])
            if body < LEAD_BODY_ATR * eatr[i]:
                continue
            if i < LEAD_SWING:
                continue
            prior_hi = max(eh[i - LEAD_SWING : i])
            prior_lo = min(el[i - LEAD_SWING : i])
            up = ec[i] > eo[i] and ec[i] > prior_hi
            dn = ec[i] < eo[i] and ec[i] < prior_lo
            if not (up or dn):
                continue
            # lag gate on GBP same timestamp
            gi = g_by_t.get(int(et[i]))
            if gi is None or math.isnan(gatr[gi]) or gatr[gi] <= 0:
                continue
            funnel["n_lead_bars"] += 1
            gbody = abs(gc[gi] - go[gi])
            if gbody >= LAG_BODY_ATR * gatr[gi]:
                continue
            funnel["n_lag_ok"] += 1
            lead_i = i
            lead_up = up
            break  # first qualifying lead bar that day
        if lead_i is None:
            continue
        # fire on GBP 13-15
        day = day_key(int(et[lead_i]))
        gidxs = [
            g_by_t[int(et[i])]
            for i in by_day_index(et).get(day, [])
            if int(et[i]) in g_by_t
        ]
        # rebuild from gbp day map more reliably
        g_day = by_day_index(gt).get(day, [])
        fire = [
            i
            for i in g_day
            if CATCH_FIRE0 <= hour_u(int(gt[i])) < CATCH_FIRE1
            and tradeable(int(gt[i]))
            and int(gt[i]) > int(et[lead_i])
        ]
        fire_i = None
        for i in fire:
            if i < 1:
                continue
            if lead_up and gc[i] > gh[i - 1] and gc[i] > go[i]:
                fire_i = i
                break
            if (not lead_up) and gc[i] < gl[i - 1] and gc[i] < go[i]:
                fire_i = i
                break
        if fire_i is None:
            continue
        funnel["n_fire"] += 1
        j = fire_i
        if j + 1 >= len(gc) - 1 or not tradeable(int(gt[j + 1])):
            continue
        if math.isnan(gatr[j]) or gatr[j] <= 0:
            continue
        direction = 1 if lead_up else -1
        entry = float(go[j + 1])
        sl = (
            entry - CATCH_SL_ATR * gatr[j]
            if direction > 0
            else entry + CATCH_SL_ATR * gatr[j]
        )
        dist = abs(entry - sl)
        if dist < 0.0003 or dist > 0.025:
            continue
        tp = entry + dist * CATCH_RR if direction > 0 else entry - dist * CATCH_RR
        r = resolve(
            direction, entry, sl, tp, j + 1, gh, gl, gc, CATCH_MAX_HOLD, CATCH_RR
        )
        if r is None:
            continue
        trades.append({"r": r})
        funnel["n_trades"] += 1
    return pack(
        "HYP-GBPUSD-H1-EURUSD-LEAD-OVERLAP-CATCHUP-001", "GBPUSD", funnel, trades
    )


def append_registry(rows: list[dict]) -> None:
    REG.parent.mkdir(parents=True, exist_ok=True)
    with REG.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_docs(results: list[dict], receipt_sha: str) -> None:
    lines = [
        "# Offline probes — London–NY overlap EUR/GBP",
        "",
        f"Date: 2026-07-15",
        f"Receipt SHA256: `{receipt_sha}`",
        f"Lane: `EXO_FRED_DISPLACE_SPAM_PAUSED`",
        "",
        "| ID | N | PF | tpw | x1.5 | Verdict | Notes |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        m, hc = r["metrics"], r["haircuts"]
        lines.append(
            f"| `{r['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{hc['x1_5']['pf']} | **{r['verdict']}** | {','.join(r['kill_notes']) or '—'} |"
        )
    lines += [
        "",
        "Survivor bar: N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15.",
        "Cost proxy only — not research-grade freeze.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    OUT_DEDUP.write_text(
        """# De-dup clearance — London–NY overlap EUR/GBP

Date: 2026-07-15
Authority: post MFE/Asia ALL_KILL; `EXO_FRED_DISPLACE_SPAM_PAUSED`
Status: `A_PRIORI_CLEARANCE_BEFORE_PROBE`

## Objects

| ID | Class | Independence claim |
|---|---|---|
| `HYP-EURUSD-H1-LONDON-IMBAL-NY-FADE-001` | London mid-imbalance → NY fade | Fade to London mid in 13–16; **≠** MULTISYM EUR 07–10 continue-break; **≠** AUD overlap fail-fade; **≠** ORB/IB/LORBA |
| `HYP-GBPUSD-H1-LONDON-COIL-NY-BREAK-001` | London relative coil → NY break | p40/60 LondonRange → fire 13–16 H/L break; **≠** GBP NY-impulse body≥1.2ATR; **≠** EUR overlap-break; **≠** Asia-coil densify |
| `HYP-GBPUSD-H1-EURUSD-LEAD-OVERLAP-CATCHUP-001` | EUR lead → GBP lag catch-up | Lead EUR 11/12 + GBP quiet → GBP fire 13–15; **≠** EURGBP→EURUSD lead; **≠** JPY-cross catch-up; **≠** Spark/ITSM |

## Kill shelf (do not retune)

IB · ORB · NY-IB · Failed ORB · LORBA · Spark · ITSM session spam · MULTISYM EUR London-overlap continue-break · MULTISYM GBP NY-open impulse · AUD overlap fail-fade · USDJPY London mid-reclaim / drive-fail / LondonNY PB · EUR Asia-box · MaxKZ/RR · FRED exo · RR2 exit-path · Asia densify.

## Survivor bar

N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15.
Model 0 withheld unless `PROBE_SURVIVOR`.

## Clearance

**CLEARED** for offline probe only (3 LNY EUR/GBP objects).
""",
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        """# Design memo — London–NY overlap EUR/GBP structural board

Date: 2026-07-15
Lane: single; no-Git; offline-first; `EXO_FRED_DISPLACE_SPAM_PAUSED`

## Problem

MFE stall-cut + Asia pctl-coil KILL. Exit-path on RR2 exhausted. Asia nearest
miss cadence-only — no densify. Named next: NY/London-overlap structure on
EUR/GBP not Wave5–7/MULTISYM-exhausted.

## Rejected a priori

- FRED displace/ToT spam.
- RR2 BE@1R / MFE stall-cut densify.
- Asia coil p40/hours densify.
- MULTISYM EUR 07–10 continue-break hour/RR rescue.
- MULTISYM GBP NY-impulse body/ATR densify.
- IB/ORB/NY-IB/LORBA/Spark/ITSM family retune.
- Invent multi-month cost freeze.

## Design 1 — EUR London imbalance → NY fade

`HYP-EURUSD-H1-LONDON-IMBAL-NY-FADE-001`

**Thesis:** One-sided London AM (07–12) mid-displacement leaves inventory that
NY-overlap liquidity mean-reverts toward London mid.

**Frozen:** arm `|Close12−Mid|≥0.75·ATR` and LondonRange≥0.80·ATR; fire first
mid-cross close 13–16; SL beyond London extreme ±0.10·ATR; RR=2; 1/day; EXPIRE 16.

## Design 2 — GBP London coil → NY break

`HYP-GBPUSD-H1-LONDON-COIL-NY-BREAK-001`

**Thesis:** Relative London-AM coil stores energy released on first NY-overlap
range break (state arm → fire → EXPIRE).

**Frozen:** coil LondonRange ≤ p40 of prior 60; fire 13–16 close beyond London
H/L; SL opposite extreme; RR=2.5; 1/day; EXPIRE 16.

## Design 3 — EUR lead → GBP overlap catch-up

`HYP-GBPUSD-H1-EURUSD-LEAD-OVERLAP-CATCHUP-001`

**Thesis:** Late-London EURUSD impulse with quiet GBPUSD implies GBP is the
lagged USD-factor leg; GBP catches up in EUR lead direction in early NY.

**Frozen:** EUR 11 or 12 body≥0.80·ATR + swing break; GBP same-bar body<0.40·ATR;
GBP fire 13–15 close beyond prior H1 extreme in lead dir; SL 1.0·ATR; RR=2;
1/day; no EURGBP; EXPIRE 15.

## Model 0 policy

Only if offline `PROBE_SURVIVOR`. Else withhold. No Real stall required.
""",
        encoding="utf-8",
    )

    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    status = (
        "OFFLINE_HAS_SURVIVOR / MODEL0_ARMED"
        if survivors
        else "OFFLINE_ALL_KILL / NO_MODEL0"
    )
    board_rows = []
    for r in results:
        m, hc = r["metrics"], r["haircuts"]
        board_rows.append(
            f"| `{r['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"**{hc['x1_5']['pf']}** | **{r['verdict'].replace('KILLED_AT_OFFLINE_PROBE','KILL').replace('PROBE_SURVIVOR','SURVIVOR')}** |"
        )
    OUT_CLOSE.write_text(
        f"""# Session closeout — London–NY overlap EUR/GBP

Date: 2026-07-15
Status: `EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`
Lane: single checkout; no-Git; no Real stall

## Board

| ID | N | PF | tpw | stress x1.5 | Verdict |
|---|---:|---:|---:|---:|---|
{chr(10).join(board_rows)}

Receipt: `{receipt_sha}`
Design: `readouts/20260715_LNY_OVERLAP_EURGBP_DESIGN_MEMO.md`
De-dup: `readouts/20260715_LNY_OVERLAP_EURGBP_DEDUP_CLEARANCE.md`
Probes: `preflight/20260715_LNY_OVERLAP_EURGBP_OFFLINE_PROBES.json`

## Model 0

{"Survivors: " + ", ".join(r["hypothesis_id"] for r in survivors) if survivors else "Withheld (zero PROBE_SURVIVOR)."}

## Decisions

1. Keep **`EXO_FRED_DISPLACE_SPAM_PAUSED`** — no new FRED series.
2. Do **not** densify MULTISYM EUR 07–10 / GBP NY-impulse / Asia coil / RR2 exit.
3. Do **not** invent cost freeze; do **not** densify MaxKZ/RR / IB/ORB/Spark/ITSM.
4. Best shelf unchanged: RR2 `194548`. GOAL unmet.

## Next autonomous EV (non-login-only)

1. {"Prereg + Model 0 for survivors only." if survivors else "New independent object class outside LNY fade/coil/catch-up densify — or wait research-grade cost then microstructure."}
2. Keep QFSI 006 accumulating; rebind harness `--execute` only on gate GO.
3. Owner PIT/vendor tape still required for multi-month session×hour cost freeze.
""",
        encoding="utf-8",
    )

    kill_lines = []
    for r in results:
        m, hc = r["metrics"], r["haircuts"]
        short = r["hypothesis_id"].replace("HYP-", "").replace("-001", "")
        kill_lines.append(
            f"  - {short}: N={m['n']} PF **{m['pf']}** x1.5 **{hc['x1_5']['pf']}** "
            f"tpw **{m['tpw']}** → {r['verdict']}"
        )
    OUT_VN.write_text(
        f"""# VN action brief — London–NY overlap EUR/GBP

## Kết quả
- Tiếp `EXO_FRED_DISPLACE_SPAM_PAUSED` — không FRED spam; không stall vì login.
- Offline 3 object (de-dup cleared) → **{status}**:
{chr(10).join(kill_lines)}
- Shelf tốt nhất vẫn RR2 `194548`. GOAL unmet.

## Receipt
- `{receipt_sha}`
- Design/dedup/closeout: `20260715_LNY_OVERLAP_EURGBP_*`

## Không làm
- Densify MULTISYM EUR 07–10 / GBP NY-impulse / coil p40 / imbalance ATR / catch-up body.
- Revive BE@1R / MFE stall / Asia densify / FRED exo / MaxKZ / RR / IB-ORB-Spark-ITSM.
- Invent multi-year cost; full-cost rebind khi gate còn STOP.

## Next (không phải “đi login”)
1. {"Prereg + Model 0 chỉ cho survivor." if survivors else "Object mới ngoài densify LNY fade/coil/catch-up — hoặc đợi cost research-grade rồi microstructure."}
2. Giữ QFSI accumulate; harness `--execute` chỉ khi GO.
3. Multi-month cost freeze: Owner PIT/vendor hoặc tích lũy ≥90 ngày.
""",
        encoding="utf-8",
    )


def patch_hot(results: list[dict], receipt_sha: str) -> None:
    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    status = (
        "OFFLINE_HAS_SURVIVOR / MODEL0_ARMED"
        if survivors
        else "OFFLINE_ALL_KILL / NO_MODEL0"
    )
    bullets = []
    for r in results:
        m, hc = r["metrics"], r["haircuts"]
        tag = "SURVIVOR" if r["verdict"] == "PROBE_SURVIVOR" else "KILL"
        reason = ""
        if "cadence_fail" in r["kill_notes"] and tag == "KILL":
            reason = " (cadence)"
        elif "stress_fail" in r["kill_notes"] and tag == "KILL":
            reason = " (stress)"
        elif "pf_fail" in r["kill_notes"] and tag == "KILL":
            reason = " (pf)"
        elif "n_fail" in r["kill_notes"] and tag == "KILL":
            reason = " (n)"
        bullets.append(
            f"  {len(bullets)+1}. `{r['hypothesis_id']}` N=**{m['n']}** PF "
            f"**{m['pf']}** tpw **{m['tpw']}** x1.5 **{hc['x1_5']['pf']}** → "
            f"**{tag}**{reason}."
        )
    next_line = (
        "Next: prereg+Model 0 for survivors only; no densify of killed arms."
        if survivors
        else (
            "Next: independent object outside LNY fade/coil/catch-up densify "
            "(or microstructure after research-grade cost). Do not densify "
            "imbalance ATR / coil p40 / lead body."
        )
    )
    block = (
        f"- **LNY overlap EUR/GBP CLOSEOUT (2026-07-15 ~01:05 ICT) —\n"
        f"  `EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.** Named post-MFE/Asia\n"
        f"  board: ≥2 independent London–NY / EUR–GBP structural objects\n"
        f"  (de-dup vs IB/ORB/NY-IB/LORBA/Spark/ITSM + MULTISYM 07–10 continue /\n"
        f"  GBP NY-impulse). Offline joint screen; Model 0 "
        f"{'armed for survivors' if survivors else 'withheld'}:\n"
        + "\n".join(bullets)
        + f"\n  Receipt `{receipt_sha}`\n"
        f"  `preflight/20260715_LNY_OVERLAP_EURGBP_OFFLINE_PROBES.json`; design\n"
        f"  `readouts/20260715_LNY_OVERLAP_EURGBP_DESIGN_MEMO.md`; dedup\n"
        f"  `readouts/20260715_LNY_OVERLAP_EURGBP_DEDUP_CLEARANCE.md`; closeout\n"
        f"  `readouts/20260715_LNY_OVERLAP_EURGBP_SESSION_CLOSEOUT.md`; VN\n"
        f"  `readouts/20260715_LNY_OVERLAP_EURGBP_VN_ACTION_BRIEF.md`. "
        f"{'Model 0 survivors listed above.' if survivors else '**Zero Model 0.**'} "
        f"Do not densify imbalance/coil/catch-up params; do not revive FRED spam /\n"
        f"  RR2 exit / Asia densify / invent cost freeze. {next_line} Best shelf\n"
        f"  RR2 `194548`. GOAL unmet.\n\n"
    )
    text = HOT.read_text(encoding="utf-8")
    # bump header
    lines = text.splitlines(keepends=True)
    if lines and lines[0].startswith("# Hot Cache"):
        # replace Updated line if present
        if len(lines) > 2 and lines[2].startswith("Updated:"):
            lines[2] = (
                "Updated: 2026-07-15 ~01:05 ICT | `EXO_FRED_DISPLACE_SPAM_PAUSED` +\n"
            )
            # also rewrite the status subtitle line (line index 3 typically)
            if len(lines) > 3 and "MFE/Asia" in lines[3]:
                lines[3] = (
                    f"LNY EUR/GBP {status.split('/')[0].strip()}; QFSI 006 live; "
                    f"RR2 `194548`; GOAL unmet\n"
                )
        # insert new Active Truth bullet after "## Active Truth\n\n"
        body = "".join(lines)
        marker = "## Active Truth\n\n"
        idx = body.find(marker)
        if idx >= 0:
            insert_at = idx + len(marker)
            body = body[:insert_at] + block + body[insert_at:]
            HOT.write_text(body, encoding="utf-8")


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        eur = load("EURUSD")
        gbp = load("GBPUSD")
    finally:
        mt5.shutdown()

    results = [
        probe_eur_london_imbal_ny_fade(eur),
        probe_gbp_london_coil_ny_break(gbp),
        probe_gbp_eur_lead_catchup(eur, gbp),
    ]

    payload = {
        "schema": "lny_overlap_eurgbp_offline_probes_v1",
        "created_at": utc_now(),
        "lane": "EXO_FRED_DISPLACE_SPAM_PAUSED",
        "window": {"from": FROM.isoformat(), "to": TO.isoformat(), "weeks": WEEKS},
        "survivor_bar": {
            "n_min": 80,
            "pf_min": 1.20,
            "tpw_min": 1.5,
            "tpw_max": 6.0,
            "x15_min": 1.15,
            "cost_proxy_usd": BASE_COST,
        },
        "banned": [
            "FRED_spam",
            "RR2_exit_retune",
            "Asia_densify",
            "invent_cost_freeze",
            "IB_ORB_NYIB_LORBA_Spark_ITSM_densify",
            "MULTISYM_EUR_0710_continue_rescue",
            "MULTISYM_GBP_NY_impulse_densify",
        ],
        "results": results,
        "survivors": [
            r["hypothesis_id"] for r in results if r["verdict"] == "PROBE_SURVIVOR"
        ],
        "model0_policy": "AUTHORIZED_IF_SURVIVOR_ELSE_WITHHELD",
    }
    write_json(OUT_JSON, payload)
    receipt_sha = sha256_file(OUT_JSON)
    payload["receipt_sha256"] = receipt_sha
    write_json(OUT_JSON, payload)
    receipt_sha = sha256_file(OUT_JSON)

    write_docs(results, receipt_sha)

    reg_rows = []
    for r in results:
        state = (
            "probe_survivor"
            if r["verdict"] == "PROBE_SURVIVOR"
            else "killed_at_offline_probe"
        )
        reg_rows.append(
            {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": state,
                "parent_candidate": None,
                "feature_family": "lny_overlap_eurgbp_structural",
                "lane": "exo_fred_displace_spam_paused_lny_eurgbp",
                "setup_type": r["hypothesis_id"],
                "symbol": r["symbol"],
                "timeframe": "H1",
                "window": "2021.01.01-2025.12.31",
                "model": "offline_probe_only",
                "source_provenance": "20260715 LNY overlap EUR/GBP board post MFE/Asia KILL",
                "prereg_path": None,
                "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260715_LNY_OVERLAP_EURGBP_SESSION_CLOSEOUT.md",
                "metrics": r["metrics"],
                "validation": {
                    "offline_probe": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                    "haircuts": r["haircuts"],
                    "kill_notes": r["kill_notes"],
                    "dedup": "readouts/20260715_LNY_OVERLAP_EURGBP_DEDUP_CLEARANCE.md",
                },
                "verdict": r["verdict"],
                "updated_at": "2026-07-15",
            }
        )
    append_registry(reg_rows)
    patch_hot(results, receipt_sha)

    print(json.dumps({"receipt_sha256": receipt_sha, "results": [
        {
            "id": r["hypothesis_id"],
            "verdict": r["verdict"],
            "n": r["metrics"]["n"],
            "pf": r["metrics"]["pf"],
            "tpw": r["metrics"]["tpw"],
            "x15": r["haircuts"]["x1_5"]["pf"],
            "notes": r["kill_notes"],
        }
        for r in results
    ]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
