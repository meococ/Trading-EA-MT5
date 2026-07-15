#!/usr/bin/env python3
"""Post ATR-trail Model0 double-KILL — entry-state / book / independent sleeve.

Authority: Owner R&D continue after ARM075+ARM100 native KILL; free Model 0
only for PROBE_SURVIVOR. EXO_FRED_DISPLACE_SPAM_PAUSED. QFSI parallel only.
Login never headline. Cost freeze still GAP — do not invent zeros.

FORBIDDEN densify / clone families (intake ban):
  RR2 exit (BE@1R / MFE stall / ATR-trail / scaleout / timebox / vol-regime-R)
  trail arm/k grid · FRED displace/ToT · LNY fade/coil/catchup · XS residual/mom
  AUDNZD z · Asia pctl coil densify · MaxKZ/RR · H4 regime · vol-target rescale
  D1-H1-PB USDJPY densify twin

A priori frozen (≥2; board runs 3):
  1) HYP-RR2-ENTRY-IMPULSE-BODYATR-GATE-001
     Keep RR2 `194548` trade only if closed M15 bar immediately before entry
     has body/ATR14 ≥ 0.55 AND close in trade direction.
  2) HYP-RR2-BOOK-DROP-THINRISK-P25-001
     Book rule: drop trades with risk_usd ≤ empirical p25 of frozen book.
     Flat +$12 taxes thin-risk legs; raise post-friction expectancy by cut.
     ≠ vol-target (no rescale; hard drop).
  3) HYP-USDJPY-H1-ASIA-PDCLOSE-MAGNET-FADE-001
     Independent sleeve: Asia 00–06 UTC, if |close−prior_D1_close| ≥ 0.80·ATR14_H1
     fade toward prior D1 close; SL 1.2 ATR; RR 1.5; expire 07:00; Mon–Thu.
     ≠ Asia coil→London break; ≠ LNY; ≠ PDH break continuation.
"""
from __future__ import annotations

import csv
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
RUNS = ROOT / "02. AlphaFactory" / "runs"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"

RR2_RUN = "20260714_194548"
RR2_DIR = RUNS / "EA_SilverBullet" / RR2_RUN
SYMBOL = "USDJPY"

OUT_JSON = PRE / "20260715_ENTRYSTATE_REBUILD_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_ENTRYSTATE_REBUILD_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_ENTRYSTATE_REBUILD_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_ENTRYSTATE_REBUILD_DESIGN_MEMO.md"
OUT_PANEL = READ / "20260715_ENTRYSTATE_3CRITIC_LEAD_MEMO.md"
OUT_CLOSE = READ / "20260715_ENTRYSTATE_REBUILD_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_ENTRYSTATE_REBUILD_VN_ACTION_BRIEF.md"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

# --- Object 1: M15 impulse body/ATR entry gate ---
IMPULSE_BODY_ATR = 0.55
IMPULSE_ATR_LEN = 14

# --- Object 2: thin-risk book drop ---
THINRISK_PCTL = 25.0  # drop ≤ p25 risk_usd

# --- Object 3: Asia PD-close magnet fade sleeve ---
ASIA_H0, ASIA_H1 = 0, 7  # signal window [0,7); hard expire at 07
MAGNET_EXT_ATR = 0.80
MAGNET_SL_ATR = 1.20
MAGNET_RR = 1.50
MAGNET_ATR_LEN = 14
MAGNET_MAX_HOLD = 8  # H1 bars


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


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


def joint_verdict(
    m: dict,
    hc: dict,
    baseline_x15: float | None = None,
    require_lift: bool = False,
) -> tuple[str, list[str]]:
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
    if require_lift and baseline_x15 is not None and x15 <= baseline_x15 + 0.01:
        notes.append("no_stress_lift_vs_baseline")
    if (
        n >= 80
        and pf > 1.20
        and 1.5 <= tpw <= 6.0
        and x15 >= 1.15
        and (
            (not require_lift)
            or baseline_x15 is None
            or x15 > baseline_x15 + 0.01
        )
    ):
        return "PROBE_SURVIVOR", notes
    if not notes:
        notes.append("joint_screen_miss")
    return "KILLED_AT_OFFLINE_PROBE", notes


def parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def find_trades_csv(run_dir: Path) -> Path:
    hits = list(run_dir.glob("logs/*_Trades_*.csv"))
    if not hits:
        hits = list(run_dir.glob("**/logs/*_Trades_*.csv"))
    if not hits:
        raise FileNotFoundError(f"no trades csv under {run_dir}")
    return sorted(hits)[0]


def load_closed_trades(path: Path) -> list[dict]:
    opens: dict[str, dict] = {}
    closed: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = str(row.get("position_id") or "").strip()
            action = str(row.get("action") or "").upper()
            if action == "OPEN":
                opens[pid] = row
            elif action == "CLOSE" and str(row.get("is_final_close") or "0") in (
                "1",
                "true",
                "True",
            ):
                op = opens.get(pid, {})
                try:
                    pnl = float(row.get("net_profit") or 0)
                except ValueError:
                    continue
                entry = float(op.get("entry_price") or op.get("price") or 0)
                sl = float(op.get("sl") or op.get("initial_sl") or 0)
                vol = float(op.get("volume") or row.get("volume") or 0)
                side = str(op.get("order_type") or "").upper()
                direction = -1 if "SELL" in side else (1 if "BUY" in side else 0)
                risk_pts = abs(entry - sl) if entry and sl else 0.0
                px = entry if entry else 150.0
                risk_usd = (
                    (vol * 100_000.0 * risk_pts) / px
                    if px > 0 and vol > 0 and risk_pts > 0
                    else 0.0
                )
                ot = parse_dt(op.get("event_time") or "")
                closed.append(
                    {
                        "position_id": pid,
                        "tag": op.get("tag") or "",
                        "open_time": ot,
                        "pnl": pnl,
                        "entry": entry,
                        "sl": sl,
                        "volume": vol,
                        "direction": direction,
                        "risk_pts": risk_pts,
                        "risk_usd": risk_usd,
                    }
                )
    return closed


def atr_wilder(
    high: list[float], low: list[float], close: list[float], length: int
) -> list[float | None]:
    n = len(close)
    tr = [0.0] * n
    for i in range(n):
        if i == 0:
            tr[i] = high[i] - low[i]
        else:
            tr[i] = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1]),
            )
    out: list[float | None] = [None] * n
    if n < length:
        return out
    seed = sum(tr[:length]) / length
    out[length - 1] = seed
    prev = seed
    for i in range(length, n):
        prev = (prev * (length - 1) + tr[i]) / length
        out[i] = prev
    return out


def load_rates(symbol: str, timeframe: int) -> dict[str, Any]:
    if not mt5.initialize():
        raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")
    try:
        rates = mt5.copy_rates_range(symbol, timeframe, FROM, TO)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"no rates {symbol}/{timeframe}: {mt5.last_error()}")
        times = [datetime.utcfromtimestamp(int(r["time"])) for r in rates]
        return {
            "time": times,
            "open": [float(r["open"]) for r in rates],
            "high": [float(r["high"]) for r in rates],
            "low": [float(r["low"]) for r in rates],
            "close": [float(r["close"]) for r in rates],
        }
    finally:
        mt5.shutdown()


def index_at_or_before(times: list[datetime], t: datetime) -> int | None:
    lo, hi = 0, len(times) - 1
    ans = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if times[mid] <= t:
            ans = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return ans


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def probe_impulse_gate(trades: list[dict], m15: dict, baseline_x15: float) -> dict:
    hid = "HYP-RR2-ENTRY-IMPULSE-BODYATR-GATE-001"
    atr = atr_wilder(m15["high"], m15["low"], m15["close"], IMPULSE_ATR_LEN)
    kept: list[float] = []
    funnel = {"n_in": len(trades), "n_kept": 0, "n_skip_no_bar": 0, "n_skip_weak": 0}
    for t in trades:
        ot = t["open_time"]
        if ot is None or t["direction"] == 0:
            funnel["n_skip_no_bar"] += 1
            continue
        # closed-bar: last fully closed M15 with time < open (or <= open-1s)
        idx = index_at_or_before(m15["time"], ot)
        if idx is None or idx < 1:
            funnel["n_skip_no_bar"] += 1
            continue
        # if bar time == open_time exactly, step back one (bar just opening)
        if m15["time"][idx] == ot:
            idx -= 1
        if idx < IMPULSE_ATR_LEN or atr[idx] is None or atr[idx] <= 0:
            funnel["n_skip_no_bar"] += 1
            continue
        body = m15["close"][idx] - m15["open"][idx]
        body_atr = abs(body) / atr[idx]
        aligned = (t["direction"] > 0 and body > 0) or (t["direction"] < 0 and body < 0)
        if body_atr >= IMPULSE_BODY_ATR and aligned:
            kept.append(t["pnl"])
            funnel["n_kept"] += 1
        else:
            funnel["n_skip_weak"] += 1
    m = metrics(kept)
    hc = haircuts(kept)
    verdict, notes = joint_verdict(m, hc, baseline_x15=baseline_x15, require_lift=True)
    return {
        "hypothesis_id": hid,
        "family": "entry_state_impulse_gate",
        "contract": {
            "body_atr_min": IMPULSE_BODY_ATR,
            "atr_len": IMPULSE_ATR_LEN,
            "bar": "closed_M15_before_entry",
            "align": "body_direction_matches_trade",
            "parent": RR2_RUN,
            "not": "exit / H4 regime / MaxKZ / FRED / Asia coil",
        },
        "funnel": funnel,
        "metrics": m,
        "haircut_flat12": hc,
        "baseline_x15": baseline_x15,
        "stress_lift_vs_baseline": round(
            ((hc.get("x1_5") or {}).get("pf") or 0) - baseline_x15, 4
        ),
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def probe_thinrisk_book(trades: list[dict], baseline_x15: float) -> dict:
    hid = "HYP-RR2-BOOK-DROP-THINRISK-P25-001"
    risks = [t["risk_usd"] for t in trades if t["risk_usd"] > 0]
    thr = percentile(risks, THINRISK_PCTL) if risks else 0.0
    kept = [t["pnl"] for t in trades if t["risk_usd"] > thr]
    m = metrics(kept)
    hc = haircuts(kept)
    verdict, notes = joint_verdict(m, hc, baseline_x15=baseline_x15, require_lift=True)
    return {
        "hypothesis_id": hid,
        "family": "book_rule_thinrisk_drop",
        "contract": {
            "drop_if_risk_usd_le": "empirical_p25_frozen_book",
            "pctl": THINRISK_PCTL,
            "threshold_risk_usd": round(thr, 4),
            "action": "hard_drop_no_rescale",
            "parent": RR2_RUN,
            "not": "voltarget_rescale / MaxKZ / exit / RR densify",
        },
        "funnel": {
            "n_in": len(trades),
            "n_kept": len(kept),
            "n_dropped": len(trades) - len(kept),
            "threshold_risk_usd": round(thr, 4),
        },
        "metrics": m,
        "haircut_flat12": hc,
        "baseline_x15": baseline_x15,
        "stress_lift_vs_baseline": round(
            ((hc.get("x1_5") or {}).get("pf") or 0) - baseline_x15, 4
        ),
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
    }


def resolve_rr(
    direction: int,
    entry: float,
    sl: float,
    tp: float,
    i0: int,
    h: list[float],
    l: list[float],
    c: list[float],
    max_hold: int,
    rr_hit: float,
) -> float | None:
    risk = abs(entry - sl)
    if risk <= 0 or i0 >= len(c) - 1:
        return None
    for j in range(i0, min(i0 + max_hold, len(c))):
        hi, lo = h[j], l[j]
        if (direction > 0 and lo <= sl) or (direction < 0 and hi >= sl):
            return -1.0
        if (direction > 0 and hi >= tp) or (direction < 0 and lo <= tp):
            return float(rr_hit)
    j = min(i0 + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def probe_asia_pdclose_magnet(h1: dict, d1: dict) -> dict:
    hid = "HYP-USDJPY-H1-ASIA-PDCLOSE-MAGNET-FADE-001"
    atr = atr_wilder(h1["high"], h1["low"], h1["close"], MAGNET_ATR_LEN)
    trades_r: list[dict] = []
    funnel = {
        "n_asia_bars": 0,
        "n_extended": 0,
        "n_trades": 0,
        "n_skip_weekend": 0,
    }
    last_day: str | None = None
    for i in range(len(h1["time"])):
        t = h1["time"][i]
        # Mon–Thu only (weekday 0–3)
        if t.weekday() > 3:
            funnel["n_skip_weekend"] += 1
            continue
        if not (ASIA_H0 <= t.hour < ASIA_H1):
            continue
        funnel["n_asia_bars"] += 1
        if atr[i] is None or atr[i] <= 0:
            continue
        # prior D1 close: last D1 bar with time < current day
        day0 = t.replace(hour=0, minute=0, second=0, microsecond=0)
        di = index_at_or_before(d1["time"], day0)
        if di is None:
            continue
        # if D1 bar is today's open bar, step back
        if d1["time"][di] >= day0:
            di -= 1
        if di < 0:
            continue
        pd_close = d1["close"][di]
        ext = h1["close"][i] - pd_close
        if abs(ext) < MAGNET_EXT_ATR * atr[i]:
            continue
        funnel["n_extended"] += 1
        dk = t.strftime("%Y-%m-%d")
        if dk == last_day:
            continue
        # fade toward PD close
        direction = -1 if ext > 0 else 1
        i0 = i + 1
        if i0 >= len(h1["close"]) - 2:
            continue
        # expire: entry must be before 07:00
        if h1["time"][i0].hour >= ASIA_H1:
            continue
        entry = h1["open"][i0]
        sl = entry - direction * MAGNET_SL_ATR * atr[i]
        tp = entry + direction * MAGNET_RR * MAGNET_SL_ATR * atr[i]
        # also soft-cap TP at pd_close if closer (magnet)
        if direction > 0:
            tp = min(tp, pd_close) if pd_close > entry else tp
        else:
            tp = max(tp, pd_close) if pd_close < entry else tp
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        # recompute effective RR if magnet TP shorter
        rr_eff = abs(tp - entry) / risk
        if rr_eff < 0.75:
            continue
        r = resolve_rr(
            direction,
            entry,
            sl,
            tp,
            i0,
            h1["high"],
            h1["low"],
            h1["close"],
            MAGNET_MAX_HOLD,
            rr_eff,
        )
        if r is None:
            continue
        trades_r.append({"r": r, "ts": h1["time"][i0].isoformat(), "rr_eff": rr_eff})
        funnel["n_trades"] += 1
        last_day = dk

    bal = DEPOSIT
    pnls: list[float] = []
    for tr in trades_r:
        pnl = bal * RISK_FRAC * tr["r"]
        pnls.append(pnl)
        bal += pnl
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc, require_lift=False)
    return {
        "hypothesis_id": hid,
        "family": "independent_sleeve_asia_pdclose_magnet",
        "symbol": SYMBOL,
        "tf": "H1",
        "contract": {
            "session_utc": f"[{ASIA_H0},{ASIA_H1})",
            "extend_atr": MAGNET_EXT_ATR,
            "sl_atr": MAGNET_SL_ATR,
            "rr": MAGNET_RR,
            "magnet": "prior_D1_close",
            "max_hold_h1": MAGNET_MAX_HOLD,
            "days": "Mon-Thu",
            "not": "Asia coil London break / LNY / PDH break / RR2 exit",
        },
        "funnel": funnel,
        "metrics": m,
        "haircut_flat12": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
        "note": "cost proxy +$12/trade flat; NOT research-grade freeze",
    }


def write_docs(payload: dict) -> None:
    results = payload["results"]
    lines = [
        "# Offline probes — entry-state rebuild (post ATR-trail Model0 KILL)",
        "",
        f"Date: 2026-07-15",
        f"Receipt SHA256: `{payload['receipt_sha256']}`",
        f"Authority: post ATR-trail native double KILL; offline-first; Model 0 survivors only",
        "",
        "## Baseline RR2 `194548`",
        "",
        f"- N={payload['baseline']['metrics']['n']} PF={payload['baseline']['metrics']['pf']} "
        f"tpw={payload['baseline']['metrics']['tpw']} "
        f"x1.5={payload['baseline']['haircut_flat12']['x1_5']['pf']}",
        f"- trades_csv: `{payload['trades_csv']}`",
        "",
        "## Results",
        "",
        "| ID | N | PF | tpw | x1.5 | lift | Verdict |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        m = r["metrics"]
        hc = r["haircut_flat12"]
        lift = r.get("stress_lift_vs_baseline", "n/a")
        lines.append(
            f"| `{r['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{hc['x1_5']['pf']} | {lift} | **{r['verdict']}** |"
        )
    lines += [
        "",
        "Survivor bar: N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15 "
        "(+ stress lift vs RR2 baseline for RR2 children).",
        "",
        "## Kill notes",
        "",
    ]
    for r in results:
        lines.append(f"- `{r['hypothesis_id']}`: {', '.join(r.get('kill_notes') or []) or '—'}")
    lines += [
        "",
        f"Survivors: **{payload['n_survivors']}** / {len(results)}",
        f"Model 0: **{payload['model0_policy']}**",
        f"Best shelf: RR2 `{RR2_RUN}`",
        "GOAL unmet.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# De-dup clearance — entry-state rebuild board",
                "",
                "Status: `INTAKE_CLEARED / INDEPENDENT` (a priori)",
                "",
                "| Object | Vs killed / banned shelf |",
                "|---|---|",
                "| `HYP-RR2-ENTRY-IMPULSE-BODYATR-GATE-001` | Entry quality on frozen RR2; "
                "**≠** H4 regime ATR%ile+EMA; **≠** exit family; **≠** MaxKZ/RR densify; "
                "**≠** XAU S1 M15 ATR impulse (different EA/symbol/family) |",
                "| `HYP-RR2-BOOK-DROP-THINRISK-P25-001` | Book hard-drop thin risk_usd≤p25; "
                "**≠** vol-target rescale; **≠** MaxKZ=1 densify; **≠** exit |",
                "| `HYP-USDJPY-H1-ASIA-PDCLOSE-MAGNET-FADE-001` | Asia magnet fade to prior D1 close; "
                "**≠** Asia pctl coil→London break; **≠** LNY EUR/GBP; **≠** PDH break cont; "
                "**≠** XS/FRED/AUDNZD |",
                "",
                "Banned densify remains: trail arm/k · BE@1R/MFE/ATR-trail · FRED · LNY · XS · "
                "Asia coil p40 · MaxKZ/RR · H4 regime · vol-target · D1-H1-PB twin.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — entry-state / book / independent sleeve",
                "",
                "Date: 2026-07-15",
                "Lane: single; offline-first; after ATR-trail Model0 BOTH KILL",
                "",
                "## Problem",
                "",
                "RR2 exit-path family exhausted on Model 0 authority "
                "(BE@1R / MFE stall / ATR-trail native). Offline envelope invalidated. "
                "Need highest-EV path that raises post-friction expectancy **without** "
                "exit spam or FRED/LNY/XS densify.",
                "",
                "## Design 1 — Impulse body/ATR entry gate",
                "",
                "`HYP-RR2-ENTRY-IMPULSE-BODYATR-GATE-001`",
                "",
                "**Thesis:** SB FVG entries after limp M15 bars are noise; require "
                "closed-bar impulse confirmation (body/ATR≥0.55, direction-aligned) "
                "to lift average R after flat friction.",
                "",
                "## Design 2 — Drop thin-risk book rule",
                "",
                "`HYP-RR2-BOOK-DROP-THINRISK-P25-001`",
                "",
                "**Thesis:** Flat +$12 round-turn dominates legs with small risk_usd. "
                "Hard-drop ≤p25 risk (no rescale) removes friction traps. "
                "≠ vol-target (which kept all trades and rescaled).",
                "",
                "## Design 3 — Asia PD-close magnet fade sleeve",
                "",
                "`HYP-USDJPY-H1-ASIA-PDCLOSE-MAGNET-FADE-001`",
                "",
                "**Thesis:** Extensions away from prior D1 close in Asia mean-revert "
                "toward the magnet before London; independent of SB FVG stack.",
                "",
                "## Model 0 policy",
                "",
                "Only if offline `PROBE_SURVIVOR`. Else withhold.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# Lead memo (3-critic) — next path after ATR-trail Model0 double KILL",
                "",
                "Date: 2026-07-15",
                "Panel: Sonic trader / quant validation / MQL5 systems (lead merge)",
                "Authority: Owner R&D continue; exit family exhausted; QFSI parallel only",
                f"Receipt: `{payload['receipt_sha256']}`",
                "",
                "## Situation (evidence)",
                "",
                "- ARM075 `20260715_081213` PF 1.100 / ×1.5 **0.666** → KILL",
                "- ARM100 `20260715_082030` PF 1.086 / ×1.5 **0.715** → KILL",
                "- Offline MFE-envelope invalidated as deploy evidence",
                "- RR2 exit family (BE@1R / MFE stall / ATR-trail) **exhausted** on Model 0",
                "- Best shelf still RR2 `194548`; cost freeze GAP; GOAL unmet",
                "",
                "## Critic theses (a priori — chosen path)",
                "",
                "| Critic | Highest-EV class now | Why |",
                "|---|---|---|",
                "| Sonic trader | **Entry-state rebuild** (impulse confirm on SB) | "
                "Edge death is selection quality, not exit plumbing; limp FVGs bleed under +$12 |",
                "| Quant validation | **Book rule** drop thin-risk legs | "
                "Post-friction EV is size×edge − cost; cut cost-dominated quartile without exit spam |",
                "| MQL5/MT5 systems | **Independent Asia PD-close magnet sleeve** | "
                "Executable closed-bar H1; no trail tick path; de-dup vs coil/LNY/PDH |",
                "",
                "## Rejected a priori",
                "",
                "- Densify trail arm/k or reopen BE@1R / MFE stall / scaleout / timebox",
                "- FRED displace/ToT · LNY fade/coil/catchup · XS residual/mom · AUDNZD z",
                "- Asia pctl coil densify · MaxKZ/RR · H4 regime · vol-target rescale",
                "- Invent research-grade cost freeze from shallow QFSI",
                "- Login / Real stall as headline (QFSI accumulate stays parallel)",
                "",
                "## Offline joint screen",
                "",
                "| ID | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
            ]
            + [
                f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
                f"{r['metrics']['tpw']} | {r['haircut_flat12']['x1_5']['pf']} | "
                f"**{r['verdict']}** |"
                for r in results
            ]
            + [
                "",
                "## Coordinator decision",
                "",
                f"- Survivors: **{payload['n_survivors']}** / {len(results)}",
                f"- Model 0: **{payload['model0_policy']}**",
                "- `EXO_FRED_DISPLACE_SPAM_PAUSED` remains",
                "- Do not densify impulse body_atr / thinrisk pctl / magnet ATR from readout",
                f"- Best shelf: RR2 `{RR2_RUN}` — GOAL unmet",
                "",
                "## Highest-EV next if all kill",
                "",
                "1. Keep QFSI accumulate toward research-grade cost (parallel, not blocker headline)",
                "2. Next board: new independent signal architecture **outside** this entry/book/magnet pack "
                "(not exit, not FRED/LNY/XS densify)",
                "",
            ]
        ),
        encoding="utf-8",
    )

    survivors = [r["hypothesis_id"] for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — entry-state rebuild (post ATR-trail Model0)",
                "",
                "Date: 2026-07-15",
                f"Status: `EXO_FRED_DISPLACE_SPAM_PAUSED` / "
                f"`{'PROBE_SURVIVOR_PRESENT' if survivors else 'OFFLINE_ALL_KILL'}` / "
                f"`{'MODEL0_ARMED' if survivors else 'NO_MODEL0'}`",
                "",
                "## Executed",
                "",
                "1. Lead 3-critic memo: entry-state / book / independent sleeve (exits closed).",
                "2. Offline joint screen ×3 a priori objects.",
                "3. Model 0 withheld unless PROBE_SURVIVOR.",
                "",
                "## Results",
                "",
            ]
            + [
                f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                f"x1.5={r['haircut_flat12']['x1_5']['pf']} → **{r['verdict']}** "
                f"({', '.join(r.get('kill_notes') or [])})"
                for r in results
            ]
            + [
                "",
                f"Receipt: `{payload['receipt_sha256']}`",
                f"Panel: `readouts/20260715_ENTRYSTATE_3CRITIC_LEAD_MEMO.md`",
                f"VN: `readouts/20260715_ENTRYSTATE_REBUILD_VN_ACTION_BRIEF.md`",
                "",
                "## Decisions",
                "",
                "1. Keep exit-path family closed — no trail densify.",
                "2. Do not densify impulse / thinrisk / magnet params from this board.",
                "3. Best shelf remains RR2 `194548`. GOAL unmet.",
                "4. Cost freeze still GAP; QFSI parallel only; login not headline.",
                "",
                "## Next",
                "",
                (
                    "Model 0 on survivors only: " + ", ".join(survivors)
                    if survivors
                    else "Zero survivors — next independent object outside this pack + exit/FRED/LNY/XS densify."
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    vn_lines = [
        "# Brief hành động (VN) — entry-state rebuild sau ATR-trail KILL",
        "",
        "- Exit RR2 (BE@1R / MFE stall / ATR-trail) **đóng** — không densify arm/k.",
        "- Path chọn: **entry-state + book rule + sleeve độc lập** (offline-first).",
        "",
    ]
    for r in results:
        vn_lines.append(
            f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
            f"×1.5={r['haircut_flat12']['x1_5']['pf']} → **{r['verdict']}**"
        )
    vn_lines += [
        "",
        f"- Survivors: **{payload['n_survivors']}** → Model 0 "
        f"{'ARMED' if survivors else 'WITHHELD'}.",
        "- Shelf tốt nhất vẫn RR2 `194548`. Cost freeze vẫn GAP. GOAL unmet.",
        "- QFSI song song; login không phải headline.",
        "",
    ]
    OUT_VN.write_text("\n".join(vn_lines), encoding="utf-8")


def patch_hot(payload: dict) -> None:
    text = HOT.read_text(encoding="utf-8")
    survivors = [r["hypothesis_id"] for r in payload["results"] if r["verdict"] == "PROBE_SURVIVOR"]
    status = (
        f"PROBE_SURVIVOR_PRESENT__MODEL0_ARMED"
        if survivors
        else "OFFLINE_ALL_KILL__NO_MODEL0"
    )
    block = (
        f"# Hot Cache\n\n"
        f"Updated: 2026-07-15 ~08:40 ICT | Entry-state rebuild offline "
        f"{'SURVIVOR' if survivors else 'ALL_KILL'}; Real on; GOAL unmet\n\n"
        f"## Active Truth\n\n"
        f"- **ENTRY-STATE REBUILD CLOSEOUT (2026-07-15 ~08:40 ICT) —\n"
        f"  `EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**\n"
        f"  Post ATR-trail Model0 double KILL; exits closed; offline-first ≥3 objects\n"
        f"  outside exit densify + FRED/LNY/XS. Lead memo\n"
        f"  `readouts/20260715_ENTRYSTATE_3CRITIC_LEAD_MEMO.md`.\n"
        f"  1. `HYP-RR2-ENTRY-IMPULSE-BODYATR-GATE-001` → "
        f"**{payload['results'][0]['verdict']}** "
        f"(N={payload['results'][0]['metrics']['n']} "
        f"PF={payload['results'][0]['metrics']['pf']} "
        f"x1.5={payload['results'][0]['haircut_flat12']['x1_5']['pf']}).\n"
        f"  2. `HYP-RR2-BOOK-DROP-THINRISK-P25-001` → "
        f"**{payload['results'][1]['verdict']}** "
        f"(N={payload['results'][1]['metrics']['n']} "
        f"PF={payload['results'][1]['metrics']['pf']} "
        f"x1.5={payload['results'][1]['haircut_flat12']['x1_5']['pf']}).\n"
        f"  3. `HYP-USDJPY-H1-ASIA-PDCLOSE-MAGNET-FADE-001` → "
        f"**{payload['results'][2]['verdict']}** "
        f"(N={payload['results'][2]['metrics']['n']} "
        f"PF={payload['results'][2]['metrics']['pf']} "
        f"x1.5={payload['results'][2]['haircut_flat12']['x1_5']['pf']}).\n"
        f"  Receipt `{payload['receipt_sha256']}`\n"
        f"  `preflight/20260715_ENTRYSTATE_REBUILD_OFFLINE_PROBES.json`;\n"
        f"  closeout `readouts/20260715_ENTRYSTATE_REBUILD_SESSION_CLOSEOUT.md`;\n"
        f"  VN `readouts/20260715_ENTRYSTATE_REBUILD_VN_ACTION_BRIEF.md`.\n"
        f"  Do **not** densify impulse body_atr / thinrisk pctl / magnet ATR.\n"
        f"  Do **not** reopen RR2 exit family. Best shelf RR2 `194548`.\n"
        f"  Cost freeze GAP; QFSI parallel; login not headline. GOAL unmet.\n\n"
    )
    # Replace header through first Active Truth section start
    if text.startswith("# Hot Cache"):
        # Insert new active truth after "## Active Truth\n\n"
        marker = "## Active Truth\n\n"
        idx = text.find(marker)
        if idx >= 0:
            rest = text[idx + len(marker) :]
            # rebuild with new header + new bullet + previous bullets
            # Keep prior first bullet (ATR-trail) as historical under new one
            new_text = block + rest
            HOT.write_text(new_text, encoding="utf-8")
            return
    HOT.write_text(block + text, encoding="utf-8")


def append_registry(payload: dict) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with REG.open("a", encoding="utf-8") as f:
        for r in payload["results"]:
            state = "probe_survivor" if r["verdict"] == "PROBE_SURVIVOR" else "killed"
            rec = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": state,
                "verdict": r["verdict"],
                "lane": "entrystate_rebuild_20260715",
                "parent_candidate": "HYP-SB-MAXKZ2-RR2-FRICTION-001"
                if r["hypothesis_id"].startswith("HYP-RR2-")
                else None,
                "feature_family": r.get("family"),
                "symbol": r.get("symbol", SYMBOL),
                "timeframe": r.get("tf", "M15"),
                "window": "2021.01.01-2025.12.31",
                "model": "offline_closed_bar_probe",
                "metrics": r.get("metrics"),
                "validation": {
                    "cost_stress": "a_priori_+12_flat_proxy",
                    "kill_notes": r.get("kill_notes"),
                    "model0": r.get("model0"),
                    "dedup": "readouts/20260715_ENTRYSTATE_REBUILD_DEDUP_CLEARANCE.md",
                    "panel": "readouts/20260715_ENTRYSTATE_3CRITIC_LEAD_MEMO.md",
                },
                "receipt_sha256": payload["receipt_sha256"],
                "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260715_ENTRYSTATE_REBUILD_OFFLINE_PROBES.md",
                "updated_at": ts,
                "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
                "reason": ",".join(r.get("kill_notes") or []) or r["verdict"],
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    trades_path = find_trades_csv(RR2_DIR)
    trades = load_closed_trades(trades_path)
    base_pnls = [t["pnl"] for t in trades]
    base_m = metrics(base_pnls)
    base_hc = haircuts(base_pnls)
    baseline_x15 = float((base_hc.get("x1_5") or {}).get("pf") or 0.0)

    m15 = load_rates(SYMBOL, mt5.TIMEFRAME_M15)
    h1 = load_rates(SYMBOL, mt5.TIMEFRAME_H1)
    d1 = load_rates(SYMBOL, mt5.TIMEFRAME_D1)

    r1 = probe_impulse_gate(trades, m15, baseline_x15)
    r2 = probe_thinrisk_book(trades, baseline_x15)
    r3 = probe_asia_pdclose_magnet(h1, d1)
    results = [r1, r2, r3]
    n_surv = sum(1 for r in results if r["verdict"] == "PROBE_SURVIVOR")

    payload: dict[str, Any] = {
        "schema": "entrystate_rebuild_offline_probes.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": (
            "Owner R&D continue post ATR-trail Model0 BOTH KILL; "
            "EXO_FRED_DISPLACE_SPAM_PAUSED; offline-first; Model0 survivors only"
        ),
        "rr2_sleeve": RR2_RUN,
        "trades_csv": str(trades_path.relative_to(ROOT)).replace("\\", "/"),
        "trades_csv_sha256": sha256_file(trades_path),
        "n_trades": len(trades),
        "baseline": {"metrics": base_m, "haircut_flat12": base_hc},
        "results": results,
        "n_survivors": n_surv,
        "model0_policy": "ARMED_ON_SURVIVOR" if n_surv else "WITHHELD_ZERO_SURVIVOR",
        "best_shelf": f"RR2_{RR2_RUN}",
        "banned": [
            "exit densify",
            "trail arm/k",
            "FRED",
            "LNY",
            "XS",
            "Asia coil densify",
            "MaxKZ/RR",
            "invent cost freeze",
        ],
        "goal": "unmet",
    }
    payload["receipt_sha256"] = "PENDING"
    raw = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False).encode(
        "utf-8"
    )
    payload["receipt_sha256"] = sha256_bytes(raw)
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    write_docs(payload)
    append_registry(payload)
    patch_hot(payload)

    print(json.dumps({
        "receipt": payload["receipt_sha256"],
        "n_survivors": n_surv,
        "verdicts": {r["hypothesis_id"]: r["verdict"] for r in results},
        "metrics": {
            r["hypothesis_id"]: {
                "n": r["metrics"]["n"],
                "pf": r["metrics"]["pf"],
                "tpw": r["metrics"]["tpw"],
                "x15": r["haircut_flat12"]["x1_5"]["pf"],
                "notes": r["kill_notes"],
            }
            for r in results
        },
    }, indent=2))


if __name__ == "__main__":
    main()
