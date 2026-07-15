#!/usr/bin/env python3
"""Next class after swing thick ALL_KILL — D1 vol-regime breakout FX3.

NOT densify ADX/thrust/TD/ROC. NOT NR7/Donchian/EMA-PB/Outside/exit/FRED/LNY/XS.
Model 0 only if PROBE_SURVIVOR. Login never headline. Cost GAP → +$12 proxy.

A priori (≥2):
  1) HYP-FX3-D1-VOLREGIME-8D-BREAK-001
  2) HYP-FX3-D1-VOLREGIME-2CLOSE-FOLLOW-001
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
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

OUT_JSON = PRE / "20260715_D1_VOLREGIME_BREAK_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_D1_VOLREGIME_BREAK_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_D1_VOLREGIME_BREAK_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_D1_VOLREGIME_BREAK_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_D1_VOLREGIME_BREAK_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_D1_VOLREGIME_BREAK_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
UNIVERSE = ("EURUSD", "GBPUSD", "USDJPY")

EXP_RATIO = 1.20  # ATR14 / ATR50
LOOKBACK = 8
SL_ATR = 1.60
RR = 2.5
MAX_HOLD = 32
MAX_OPEN = 2


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float]) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - BASE_COST * mult for p in pnls]
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
    return {
        "n": n,
        "pf": None if p is None else round(p, 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(n / WEEKS, 4) if WEEKS else None,
    }


def joint_verdict(m: dict, hc: dict) -> tuple[str, list[str]]:
    notes: list[str] = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if not (1.5 <= tpw <= 6.0):
        notes.append("cadence_fail")
    if pf <= 1.20:
        notes.append("pf_fail")
    if x15 < 1.15:
        notes.append("stress_fail")
    if n >= 80 and pf > 1.20 and 1.5 <= tpw <= 6.0 and x15 >= 1.15:
        return "PROBE_SURVIVOR", notes
    return "KILLED_AT_OFFLINE_PROBE", notes or ["joint_screen_miss"]


def atr_wilder(h, l, c, length=14):
    n = len(c)
    tr = np.zeros(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    out = np.full(n, np.nan)
    if n < length:
        return out
    out[length - 1] = tr[:length].mean()
    for i in range(length, n):
        out[i] = (out[i - 1] * (length - 1) + tr[i]) / length
    return out


def load_tf(symbol, tf):
    rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
    if rates is None or len(rates) < 200:
        raise RuntimeError(f"rates fail {symbol}: {mt5.last_error()}")
    return {
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
    }


def day_key(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def weekday(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).weekday()


def resolve_r(direction, entry, sl, tp, i0, h, l, c, max_hold, rr_hit):
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    for j in range(i0, min(i0 + max_hold, len(c))):
        if direction > 0:
            if l[j] <= sl:
                return -1.0
            if h[j] >= tp:
                return float(rr_hit)
        else:
            if h[j] >= sl:
                return -1.0
            if l[j] <= tp:
                return float(rr_hit)
    j = min(i0 + max_hold - 1, len(c) - 1)
    return direction * (c[j] - entry) / risk


def pnls_from_r(trades):
    bal = DEPOSIT
    out = []
    for t in trades:
        pnl = bal * RISK_FRAC * t["r"]
        out.append(pnl)
        bal += pnl
    return out


def pack(hid, funnel, trades, note=""):
    pnls = pnls_from_r(trades)
    m, hc = metrics(pnls), haircuts(pnls)
    verdict, notes = joint_verdict(m, hc)
    return {
        "hypothesis_id": hid,
        "symbol": "BOOK:EUR+GBP+USDJPY",
        "tf": "D1→H4",
        "family": "d1_volregime_break_fx3",
        "funnel": funnel,
        "metrics": m,
        "haircuts": hc,
        "kill_notes": notes,
        "verdict": verdict,
        "model0": "AUTHORIZED_IF_SURVIVOR" if verdict == "PROBE_SURVIVOR" else "WITHHELD",
        "note": note,
        "n_trades_raw": len(trades),
    }


def build(symbol):
    h4 = load_tf(symbol, mt5.TIMEFRAME_H4)
    d1 = load_tf(symbol, mt5.TIMEFRAME_D1)
    h4["atr"] = atr_wilder(h4["high"], h4["low"], h4["close"], 14)
    d1["atr14"] = atr_wilder(d1["high"], d1["low"], d1["close"], 14)
    d1["atr50"] = atr_wilder(d1["high"], d1["low"], d1["close"], 50)
    return {"symbol": symbol, "h4": h4, "d1": d1}


def portfolio_select(cands, funnel):
    cands = sorted(cands, key=lambda x: (x["ts_entry"], -x["score"], x["symbol"]))
    by_day_dir = {}
    for c in cands:
        if c["symbol"] in ("EURUSD", "GBPUSD"):
            by_day_dir.setdefault((c["day"], c["direction"]), []).append(c)
    blocked = set()
    for group in by_day_dir.values():
        if len(group) < 2:
            continue
        best = max(group, key=lambda x: x["score"])
        for g in group:
            if g is not best:
                blocked.add(id(g))
    trades = []
    open_until = {}
    for c in cands:
        if id(c) in blocked:
            funnel["n_blocked_overlap"] += 1
            continue
        ts = c["ts_entry"]
        open_until = {s: te for s, te in open_until.items() if te > ts}
        if c["symbol"] in open_until or len(open_until) >= MAX_OPEN:
            funnel["n_blocked_overlap"] += 1
            continue
        open_until[c["symbol"]] = c["ts_exit"]
        trades.append(
            {
                "r": c["r"],
                "symbol": c["symbol"],
                "ts": ts,
                "direction": c["direction"],
            }
        )
        funnel["by_symbol"][c["symbol"]] = funnel["by_symbol"].get(c["symbol"], 0) + 1
        funnel["n_trades"] += 1
    return trades


def find_h4_entry(h4, entry_ts_min):
    ht = h4["time"]
    for i in range(len(ht)):
        if int(ht[i]) >= entry_ts_min:
            return i
    return None


def exit_ts_of(h4, hi, direction, sl, tp):
    ht, hh, hl = h4["time"], h4["high"], h4["low"]
    for j in range(hi, min(hi + MAX_HOLD, len(ht))):
        if direction > 0 and (hl[j] <= sl or hh[j] >= tp):
            return int(ht[j])
        if direction < 0 and (hh[j] >= sl or hl[j] <= tp):
            return int(ht[j])
    return int(ht[min(hi + MAX_HOLD - 1, len(ht) - 1)])


def probe_8d_break(books):
    """Expansion regime + single D1 close beyond prior 8-day extreme."""
    funnel = {"n_armed": 0, "n_trades": 0, "n_blocked_overlap": 0, "by_symbol": {}}
    cands = []
    for sym, b in books.items():
        d1, h4 = b["d1"], b["h4"]
        n = len(d1["time"])
        for i in range(max(50, LOOKBACK + 1), n - 1):
            if weekday(int(d1["time"][i])) >= 5:
                continue
            a14, a50 = d1["atr14"][i], d1["atr50"][i]
            if any(math.isnan(x) for x in (a14, a50)) or a50 <= 0:
                continue
            if a14 / a50 < EXP_RATIO:
                continue
            prior_hi = float(max(d1["high"][i - LOOKBACK : i]))
            prior_lo = float(min(d1["low"][i - LOOKBACK : i]))
            c = d1["close"][i]
            if c > prior_hi:
                direction = 1
                extreme = prior_hi
            elif c < prior_lo:
                direction = -1
                extreme = prior_lo
            else:
                continue
            funnel["n_armed"] += 1
            entry_ts_min = int(d1["time"][i + 1])
            hi = find_h4_entry(h4, entry_ts_min)
            if hi is None or hi >= len(h4["time"]) - 2:
                continue
            a_h = h4["atr"][hi]
            if math.isnan(a_h) or a_h <= 0:
                continue
            entry = float(h4["open"][hi])
            sl = extreme - direction * SL_ATR * a_h
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + direction * RR * risk
            r = resolve_r(
                direction, entry, sl, tp, hi, h4["high"], h4["low"], h4["close"], MAX_HOLD, RR
            )
            if r is None:
                continue
            cands.append(
                {
                    "ts_entry": int(h4["time"][hi]),
                    "ts_exit": exit_ts_of(h4, hi, direction, sl, tp),
                    "symbol": sym,
                    "direction": direction,
                    "score": float(a14 / a50),
                    "r": float(r),
                    "day": day_key(int(d1["time"][i])),
                }
            )
    trades = portfolio_select(cands, funnel)
    return pack(
        "HYP-FX3-D1-VOLREGIME-8D-BREAK-001",
        funnel,
        trades,
        "ATR14/ATR50≥1.20 + D1 close beyond prior 8d extreme; RR2.5; FX3 caps",
    )


def probe_2close_follow(books):
    """Same expansion, require two consecutive closes beyond the 8d extreme."""
    funnel = {"n_armed": 0, "n_trades": 0, "n_blocked_overlap": 0, "by_symbol": {}}
    cands = []
    for sym, b in books.items():
        d1, h4 = b["d1"], b["h4"]
        n = len(d1["time"])
        for i in range(max(50, LOOKBACK + 2), n - 1):
            if weekday(int(d1["time"][i])) >= 5:
                continue
            a14, a50 = d1["atr14"][i], d1["atr50"][i]
            if any(math.isnan(x) for x in (a14, a50)) or a50 <= 0:
                continue
            if a14 / a50 < EXP_RATIO:
                continue
            # extreme measured before the first of the two closes (i-1)
            prior_hi = float(max(d1["high"][i - 1 - LOOKBACK : i - 1]))
            prior_lo = float(min(d1["low"][i - 1 - LOOKBACK : i - 1]))
            c0, c1 = d1["close"][i - 1], d1["close"][i]
            if c0 > prior_hi and c1 > prior_hi:
                direction = 1
                extreme = prior_hi
            elif c0 < prior_lo and c1 < prior_lo:
                direction = -1
                extreme = prior_lo
            else:
                continue
            funnel["n_armed"] += 1
            entry_ts_min = int(d1["time"][i + 1])
            hi = find_h4_entry(h4, entry_ts_min)
            if hi is None or hi >= len(h4["time"]) - 2:
                continue
            a_h = h4["atr"][hi]
            if math.isnan(a_h) or a_h <= 0:
                continue
            entry = float(h4["open"][hi])
            sl = extreme - direction * SL_ATR * a_h
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + direction * RR * risk
            r = resolve_r(
                direction, entry, sl, tp, hi, h4["high"], h4["low"], h4["close"], MAX_HOLD, RR
            )
            if r is None:
                continue
            cands.append(
                {
                    "ts_entry": int(h4["time"][hi]),
                    "ts_exit": exit_ts_of(h4, hi, direction, sl, tp),
                    "symbol": sym,
                    "direction": direction,
                    "score": float(a14 / a50),
                    "r": float(r),
                    "day": day_key(int(d1["time"][i])),
                }
            )
    trades = portfolio_select(cands, funnel)
    return pack(
        "HYP-FX3-D1-VOLREGIME-2CLOSE-FOLLOW-001",
        funnel,
        trades,
        "Expansion + 2 consecutive D1 closes beyond 8d extreme; confirmation; FX3 caps",
    )


def write_docs(payload):
    results = payload["results"]
    receipt = payload["receipt_sha256"]
    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    all_kill = not survivors

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — D1 vol-regime breakout FX3",
                "",
                "Date: 2026-07-15",
                "Parent: swing thick book ALL_KILL → named next class",
                "",
                "## Design 1 — 8d extreme break under expansion",
                "`HYP-FX3-D1-VOLREGIME-8D-BREAK-001`",
                "ATR14/ATR50≥1.20; D1 close beyond prior 8-day high/low; next H4 open;",
                f"SL {SL_ATR} ATR_H4 beyond extreme; RR={RR}; hold≤{MAX_HOLD} H4;",
                f"≤1/symbol; ≤{MAX_OPEN} book; EUR+GBP same-dir → higher ATR ratio.",
                "",
                "## Design 2 — Two-close confirmation",
                "`HYP-FX3-D1-VOLREGIME-2CLOSE-FOLLOW-001`",
                "Same expansion; require two consecutive closes beyond the frozen 8d extreme.",
                "",
                "## ≠ killed",
                "≠ NR7/RV-compress (no range-rank compress); ≠ Donchian channel fade/break",
                "with RV gate; ≠ ADX/thrust/TD/ROC densify; ≠ Outside/Engulf/EMA-PB/Weekly-HL.",
                "",
                "## If both fail — next object class",
                "Multi-day **carry / swap-aware differential** book (USD rate-diff proxy from",
                "public price slope of short-rate FX) OR microstructure after research-grade",
                "cost — not another D1 breakout densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# De-dup — D1 vol-regime break FX3",
                "",
                "Status: **CLEARED** for offline probe (2 objects).",
                "",
                "| ID | ≠ |",
                "|---|---|",
                "| `HYP-FX3-D1-VOLREGIME-8D-BREAK-001` | ≠ NR7; ≠ Donchian20; ≠ H4 Outside; ≠ swing ADX/thrust densify |",
                "| `HYP-FX3-D1-VOLREGIME-2CLOSE-FOLLOW-001` | ≠ single-bar break twin without confirmation; ≠ Weekly-HL; ≠ EMA-PB |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [
        "# Offline probes — D1 vol-regime break FX3",
        "",
        f"Receipt: `{receipt}`",
        "",
        "| ID | N | PF | tpw | x1.5 | Verdict | Notes |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        lines.append(
            f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
            f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | **{r['verdict']}** | "
            f"{','.join(r['kill_notes'])} |"
        )
    lines += ["", f"Model 0: {'WITHHELD' if all_kill else 'survivors only'}.", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — D1 vol-regime break FX3",
                "",
                "Date: 2026-07-15",
                "Status: `EXO_FRED_DISPLACE_SPAM_PAUSED` / "
                + ("`OFFLINE_ALL_KILL` / `NO_MODEL0`" if all_kill else "`PROBE_SURVIVOR_PRESENT`"),
                "",
            ]
            + [
                f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → **{r['verdict']}**"
                for r in results
            ]
            + [
                "",
                f"Receipt: `{receipt}`",
                "Do not densify ATR ratio / 8d lookback / RR from this board.",
                "Best shelf RR2 `194548`. Cost GAP. Login not headline. GOAL unmet.",
                "",
                "## Next",
                "If empty: multi-day **carry/swap-aware differential** book or microstructure",
                "after research-grade cost — not D1 breakout densify.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    vn = [
        "# Brief hành động (VN) — D1 vol-regime break FX3",
        "",
        "- Class kế tiếp sau swing thick KILL: **D1 vol-regime breakout FX3**.",
        "",
    ]
    for r in results:
        vn.append(
            f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
            f"×1.5={r['haircuts']['x1_5']['pf']} → **{r['verdict']}**"
        )
    vn += [
        "",
        f"- Survivors: **{len(survivors)}** → Model 0 "
        + ("WITHHELD." if all_kill else "armed."),
        "- Shelf RR2 `194548`. Cost GAP. GOAL unmet. Login không headline.",
        "- Next: carry/swap-aware differential **hoặc** microstructure sau cost research-grade.",
        "",
    ]
    OUT_VN.write_text("\n".join(vn), encoding="utf-8")


def append_registry(payload):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with REG.open("a", encoding="utf-8") as f:
        for r in payload["results"]:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": r["hypothesis_id"],
                        "state": "probe_survivor"
                        if r["verdict"] == "PROBE_SURVIVOR"
                        else "killed",
                        "verdict": r["verdict"],
                        "lane": "d1_volregime_break_20260715",
                        "feature_family": r.get("family"),
                        "symbol": r.get("symbol"),
                        "timeframe": r.get("tf"),
                        "window": "2021.01.01-2025.12.31",
                        "model": "offline_closed_bar_probe",
                        "metrics": r.get("metrics"),
                        "receipt_sha256": payload["receipt_sha256"],
                        "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260715_D1_VOLREGIME_BREAK_OFFLINE_PROBES.md",
                        "updated_at": ts,
                        "cost_grade": "UNVERIFIED_TESTER_DEFAULT",
                        "reason": ",".join(r.get("kill_notes") or []),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def patch_hot(payload):
    results = payload["results"]
    receipt = payload["receipt_sha256"]
    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    all_kill = not survivors
    status = (
        "`EXO_FRED_DISPLACE_SPAM_PAUSED` / `OFFLINE_ALL_KILL__NO_MODEL0`"
        if all_kill
        else "`EXO_FRED_DISPLACE_SPAM_PAUSED` / `PROBE_SURVIVOR_PRESENT`"
    )
    lines = [
        f"- **D1 VOL-REGIME BREAK CLOSEOUT (2026-07-15 ~09:05 ICT) — {status}.**",
        "  Named next class after swing thick ALL_KILL. Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        lines.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    lines += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_D1_VOLREGIME_BREAK_OFFLINE_PROBES.json`;",
        "  design `readouts/20260715_D1_VOLREGIME_BREAK_DESIGN_MEMO.md`;",
        "  closeout `readouts/20260715_D1_VOLREGIME_BREAK_SESSION_CLOSEOUT.md`;",
        "  VN `readouts/20260715_D1_VOLREGIME_BREAK_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify ATR ratio / 8d / RR. Do not densify prior swing ADX/thrust/TD/ROC.",
        "  Next class: multi-day carry/swap-aware differential **or** microstructure after",
        "  research-grade cost — not another D1 breakout densify.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    bullet = "\n".join(lines)
    header = (
        "# Hot Cache\n\n"
        "Updated: 2026-07-15 ~09:05 ICT | D1 vol-regime break offline "
        + ("ALL_KILL; " if all_kill else "SURVIVOR; ")
        + "Real on; GOAL unmet\n\n"
        "## Active Truth\n\n"
    )
    text = HOT.read_text(encoding="utf-8")
    marker = "## Active Truth\n"
    idx = text.find(marker)
    if idx >= 0:
        rest = text[idx + len(marker) :]
        if rest.startswith("\n"):
            rest = rest[1:]
        HOT.write_text(header + bullet + rest, encoding="utf-8")
    else:
        HOT.write_text(header + bullet + text, encoding="utf-8")


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 init fail: {mt5.last_error()}")
    try:
        books = {s: build(s) for s in UNIVERSE}
        results = [probe_8d_break(books), probe_2close_follow(books)]
        n_surv = sum(1 for r in results if r["verdict"] == "PROBE_SURVIVOR")
        payload = {
            "schema": "d1_volregime_break_offline_probes.v1",
            "created_at_utc": utc_now(),
            "parent_board": "swing_thick_book_ALL_KILL",
            "results": results,
            "n_survivors": n_surv,
            "model0_policy": "ARMED_ON_SURVIVOR" if n_surv else "WITHHELD_ZERO_SURVIVOR",
            "best_shelf": "RR2_20260714_194548",
            "next_class_if_empty": (
                "multi-day carry/swap-aware differential book OR microstructure "
                "after research-grade cost"
            ),
            "goal": "unmet",
            "receipt_sha256": "PENDING",
        }
        raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        payload["receipt_sha256"] = sha256_bytes(raw)
        OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        write_docs(payload)
        append_registry(payload)
        patch_hot(payload)
        print(
            json.dumps(
                {
                    "receipt": payload["receipt_sha256"],
                    "n_survivors": n_surv,
                    "verdicts": {r["hypothesis_id"]: r["verdict"] for r in results},
                    "metrics": {
                        r["hypothesis_id"]: {
                            "n": r["metrics"]["n"],
                            "pf": r["metrics"]["pf"],
                            "tpw": r["metrics"]["tpw"],
                            "x15": r["haircuts"]["x1_5"]["pf"],
                            "notes": r["kill_notes"],
                        }
                        for r in results
                    },
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
