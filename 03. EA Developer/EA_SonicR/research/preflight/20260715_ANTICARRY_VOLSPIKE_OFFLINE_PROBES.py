#!/usr/bin/env python3
"""Pivot after carry/swap-diff ALL_KILL + 6J densify INTAKE_KILL + G10 acquire BLOCKED.

Named next class: anti-carry × vol-spike (local-research backlog).
≠ V8_CARRY_VOL_REGIME (that holds WITH-carry when vol calm; this SHORTS carry
when vol innovation is positive).

A priori (≥2):
  1) HYP-FX3-ANTICARRY-VOLSPIKE-H4-001
  2) HYP-FX3-ANTICARRY-VOLSPIKE-D1CONFIRM-001
"""
from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"
RATES_CSV = ROOT / "03. EA Developer" / "EA_CarryPublicRates" / "carry_rates_d1.csv"

OUT_JSON = PRE / "20260715_ANTICARRY_VOLSPIKE_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_ANTICARRY_VOLSPIKE_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_ANTICARRY_VOLSPIKE_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_ANTICARRY_VOLSPIKE_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_ANTICARRY_VOLSPIKE_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_ANTICARRY_VOLSPIKE_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
UNIVERSE = ("EURUSD", "GBPUSD", "USDJPY")

CARRY_MIN = 0.25
VOL_LB = 20
VOL_AR_MIN = 60
SL_ATR = 1.5
MAX_HOLD_H4 = 8  # a priori; ≠ V8's 6 intentionally? use 8 for independence
MAX_OPEN = 2
D1_CONFIRM_LB = 2


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


def weekday(ts: int) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).weekday()


def pair_carry(symbol: str, usd: float, eur: float, gbp: float, jpy: float) -> float:
    if symbol == "EURUSD":
        return eur - usd
    if symbol == "GBPUSD":
        return gbp - usd
    if symbol == "USDJPY":
        return usd - jpy
    raise KeyError(symbol)


def load_rates_lagged() -> dict[str, tuple[list[date], list[float]]]:
    raw: dict[str, dict[date, float]] = {k: {} for k in ("usd", "eur", "gbp", "jpy")}
    with RATES_CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                d = date.fromisoformat(row["date"][:10])
                for k in raw:
                    v = float(row[k])
                    if math.isfinite(v):
                        raw[k][d] = v
            except (KeyError, ValueError, TypeError):
                continue
    lags = {"usd": 1, "eur": 1, "gbp": 1, "jpy": 2}
    out: dict[str, tuple[list[date], list[float]]] = {}
    for k, series in raw.items():
        items = sorted((d + timedelta(days=lags[k]), v) for d, v in series.items())
        out[k] = ([d for d, _ in items], [v for _, v in items])
    return out


def asof(series: tuple[list[date], list[float]], d: date) -> float | None:
    dates, vals = series
    if not dates:
        return None
    i = bisect.bisect_right(dates, d) - 1
    return None if i < 0 else vals[i]


def rates_on(lagged, d: date):
    vals = []
    for k in ("usd", "eur", "gbp", "jpy"):
        v = asof(lagged[k], d)
        if v is None:
            return None
        vals.append(v)
    return tuple(vals)


def resolve_r(direction, entry, sl, tp, i0, h, l, c, max_hold, rr_hit):
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    for j in range(i0, min(i0 + max_hold, len(c))):
        if direction > 0:
            if l[j] <= sl:
                return -1.0
            if tp is not None and h[j] >= tp:
                return float(rr_hit)
        else:
            if h[j] >= sl:
                return -1.0
            if tp is not None and l[j] <= tp:
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
        "family": "anticarry_volspike_fx3",
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
    d1["atr"] = atr_wilder(d1["high"], d1["low"], d1["close"], 14)
    # daily abs log-return for vol
    c = d1["close"]
    d1["absret"] = np.zeros(len(c))
    for i in range(1, len(c)):
        if c[i - 1] > 0 and c[i] > 0:
            d1["absret"][i] = abs(math.log(c[i] / c[i - 1]))
    return {"symbol": symbol, "h4": h4, "d1": d1}


def global_vol_innovation(books) -> dict[date, float]:
    """Cross-pair mean |log-ret| sigma_LB residual vs AR(1) on prior sigma."""
    # Align by calendar date using EURUSD D1 as master
    master = books["EURUSD"]["d1"]
    dates = [
        datetime.fromtimestamp(int(t), timezone.utc).date() for t in master["time"]
    ]
    # map each symbol date -> absret
    abs_maps = {}
    for sym, b in books.items():
        m = {}
        for i, t in enumerate(b["d1"]["time"]):
            m[datetime.fromtimestamp(int(t), timezone.utc).date()] = float(b["d1"]["absret"][i])
        abs_maps[sym] = m

    # daily cross-sectional mean absret
    xs = []
    for d in dates:
        vals = [abs_maps[s].get(d) for s in UNIVERSE]
        vals = [v for v in vals if v is not None]
        xs.append(float(np.mean(vals)) if vals else float("nan"))
    xs = np.array(xs)

    # rolling sigma of xs
    sig = np.full(len(xs), np.nan)
    for i in range(VOL_LB, len(xs)):
        w = xs[i - VOL_LB + 1 : i + 1]
        if np.any(~np.isfinite(w)):
            continue
        sig[i] = float(np.std(w, ddof=1)) if len(w) > 1 else float("nan")

    # AR(1) residual of sigma: e_t = sig_t - (a + b*sig_{t-1}) fit on trailing VOL_AR_MIN
    innov = {}
    for i in range(VOL_AR_MIN + 1, len(sig)):
        y = sig[i - VOL_AR_MIN + 1 : i + 1]
        x = sig[i - VOL_AR_MIN : i]
        mask = np.isfinite(y) & np.isfinite(x)
        if mask.sum() < VOL_AR_MIN * 0.8:
            continue
        yy, xx = y[mask], x[mask]
        # simple OLS
        b = np.cov(xx, yy, ddof=1)[0, 1] / (np.var(xx, ddof=1) + 1e-12)
        a = yy.mean() - b * xx.mean()
        if not np.isfinite(sig[i]) or not np.isfinite(sig[i - 1]):
            continue
        e = sig[i] - (a + b * sig[i - 1])
        innov[dates[i]] = float(e)
    return innov


def portfolio_select(cands, funnel, max_open: int):
    cands = sorted(cands, key=lambda x: (x["ts_entry"], -x["score"], x["symbol"]))
    trades = []
    open_until: dict[str, int] = {}
    for c in cands:
        ts = c["ts_entry"]
        open_until = {s: te for s, te in open_until.items() if te > ts}
        if c["symbol"] in open_until or len(open_until) >= max_open:
            funnel["n_blocked_overlap"] += 1
            continue
        open_until[c["symbol"]] = c["ts_exit"]
        trades.append({"r": c["r"], "symbol": c["symbol"], "ts": ts, "direction": c["direction"]})
        funnel["by_symbol"][c["symbol"]] = funnel["by_symbol"].get(c["symbol"], 0) + 1
        funnel["n_trades"] += 1
    return trades


def find_h4_after(h4, entry_ts_min):
    for i in range(len(h4["time"])):
        if int(h4["time"][i]) >= entry_ts_min:
            return i
    return None


def probe_volspike(books, lagged, innov, require_d1_confirm: bool, hid: str, note: str):
    funnel = {"n_armed": 0, "n_trades": 0, "n_blocked_overlap": 0, "n_no_spike": 0, "by_symbol": {}}
    cands = []
    ref = books["EURUSD"]["d1"]
    for i in range(VOL_AR_MIN + 2, len(ref["time"]) - 1):
        if weekday(int(ref["time"][i])) >= 5:
            continue
        d = datetime.fromtimestamp(int(ref["time"][i]), timezone.utc).date()
        e = innov.get(d)
        if e is None or e <= 0:
            funnel["n_no_spike"] += 1
            continue
        rates = rates_on(lagged, d)
        if rates is None:
            continue
        # rank pairs by carry; anti-carry = short highest positive / long most negative
        carries = {s: pair_carry(s, *rates) for s in UNIVERSE}
        # pick extreme |carry| >= deadband
        ranked = sorted(carries.items(), key=lambda kv: kv[1], reverse=True)
        hi_sym, hi_c = ranked[0]
        lo_sym, lo_c = ranked[-1]
        targets = []
        if hi_c >= CARRY_MIN:
            targets.append((hi_sym, -1, hi_c))  # short high-carry
        if lo_c <= -CARRY_MIN:
            targets.append((lo_sym, +1, -lo_c))  # long low-carry (= short that currency's funding)
        if not targets:
            continue
        if require_d1_confirm:
            # require prior D1_CONFIRM_LB closes moved WITH the would-be carry (crowding) before anti
            ok = []
            for sym, direction, score in targets:
                d1 = books[sym]["d1"]
                # find index of date d
                di = None
                for j, t in enumerate(d1["time"]):
                    if datetime.fromtimestamp(int(t), timezone.utc).date() == d:
                        di = j
                        break
                if di is None or di < D1_CONFIRM_LB:
                    continue
                # carry direction for hi is +1 for long-carry; crowding = price moved that way
                carry_dir = 1 if carries[sym] > 0 else -1
                move = d1["close"][di] - d1["close"][di - D1_CONFIRM_LB]
                if carry_dir * move <= 0:
                    continue
                ok.append((sym, direction, score))
            targets = ok
            if not targets:
                continue

        funnel["n_armed"] += 1
        for sym, direction, score in targets:
            h4 = books[sym]["h4"]
            entry_ts_min = int(ref["time"][i + 1])  # next day open region
            # use first H4 of next calendar day on that symbol
            hi = find_h4_after(h4, entry_ts_min)
            if hi is None or hi >= len(h4["time"]) - 2:
                continue
            a = h4["atr"][hi]
            if math.isnan(a) or a <= 0:
                continue
            entry = float(h4["open"][hi])
            sl = entry - direction * SL_ATR * a
            r = resolve_r(
                direction, entry, sl, None, hi, h4["high"], h4["low"], h4["close"], MAX_HOLD_H4, 0.0
            )
            if r is None:
                continue
            te = int(h4["time"][min(hi + MAX_HOLD_H4 - 1, len(h4["time"]) - 1)])
            for j in range(hi, min(hi + MAX_HOLD_H4, len(h4["time"]))):
                if direction > 0 and h4["low"][j] <= sl:
                    te = int(h4["time"][j])
                    break
                if direction < 0 and h4["high"][j] >= sl:
                    te = int(h4["time"][j])
                    break
            cands.append(
                {
                    "ts_entry": int(h4["time"][hi]),
                    "ts_exit": te,
                    "symbol": sym,
                    "direction": direction,
                    "score": float(score) + float(e),
                    "r": float(r),
                }
            )
    trades = portfolio_select(cands, funnel, MAX_OPEN)
    return pack(hid, funnel, trades, note)


def append_registry(results, receipt):
    ts = utc_now()
    with REG.open("a", encoding="utf-8") as f:
        for r in results:
            row = {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": "killed" if r["verdict"] != "PROBE_SURVIVOR" else "probe_survivor",
                "parent_candidate": "post_carry_swap_diff_anticarry_20260715",
                "feature_family": r["family"],
                "lane": "anticarry_volspike_20260715",
                "setup_type": r["note"],
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": "H4",
                "window": "2021.01.01-2025.12.31",
                "model": "offline_probe_only",
                "readout_path": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "metrics": {
                    "trades": r["metrics"]["n"],
                    "pf": r["metrics"]["pf"],
                    "tpw": r["metrics"]["tpw"],
                    "pf_cost_x1_5": r["haircuts"]["x1_5"]["pf"],
                },
                "validation": {
                    "offline_probe": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                    "receipt_sha256": receipt,
                    "status": r["verdict"],
                },
                "verdict": r["verdict"],
                "reason": ",".join(r["kill_notes"]),
                "updated_at": ts,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_docs(results, receipt):
    all_kill = all(r["verdict"] != "PROBE_SURVIVOR" for r in results)
    next_class = (
        "True greenfield off kill shelf after Owner-led cost/tick acquire, "
        "or G10 daily overnight rates when RBA/BoC download unblocked — "
        "not anticarry densify, not V8/USBILL/6J/D1-breakout densify."
    )
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — Anti-carry × vol-spike FX3",
                "",
                "Parent: carry/swap-diff ALL_KILL; 6J densify INTAKE_KILL; G10 acquire BLOCKED.",
                "",
                "## Design 1",
                "`HYP-FX3-ANTICARRY-VOLSPIKE-H4-001`",
                "When global FX vol AR(1) residual > 0: short highest-carry / long lowest-carry",
                f"(|carry|≥{CARRY_MIN}); H4 entry next day; SL {SL_ATR} ATR; hold≤{MAX_HOLD_H4}; ≤{MAX_OPEN} book.",
                "",
                "## Design 2",
                "`HYP-FX3-ANTICARRY-VOLSPIKE-D1CONFIRM-001`",
                "Same + require prior 2 D1 closes moved WITH carry (crowding) before anti-carry.",
                "",
                "## ≠ killed",
                "≠ V8_CARRY_VOL_REGIME (WITH-carry when vol calm); ≠ V8 weekly/daily/5bp rank;",
                "≠ USBILL; ≠ 6J z-gate; ≠ Mon→Thu harvest / flush-MR from prior board.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# De-dup — Anti-carry × vol-spike",
                "",
                "Status: **CLEARED** (mechanism inverse of V8 calm-carry hold).",
                "",
                "| ID | ≠ |",
                "|---|---|",
                "| `HYP-FX3-ANTICARRY-VOLSPIKE-H4-001` | ≠ Menkhoff calm WITH-carry; actively short carry on vol spike |",
                "| `HYP-FX3-ANTICARRY-VOLSPIKE-D1CONFIRM-001` | ≠ raw volspike without crowding confirm; ≠ V8 strip |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [
        "# Offline probes — Anti-carry × vol-spike",
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
                "# Session closeout — Anti-carry × vol-spike",
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
                "Do not densify vol AR / carry deadband / hold from this board.",
                "Best shelf RR2 `194548`. Cost GAP. Login not headline. GOAL unmet.",
                "",
                "## Next",
                next_class,
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN action brief — Anti-carry × vol-spike",
                "",
                f"- Offline 2 object → **{'OFFLINE_ALL_KILL / NO_MODEL0' if all_kill else 'có SURVIVOR'}**:",
            ]
            + [
                f"  - `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
                for r in results
            ]
            + [
                f"- Receipt `{receipt[:16]}…`",
                "- ≠ V8 calm-carry; không densify AR/deadband/hold.",
                f"- Next: {next_class}",
                "- Best shelf RR2 `194548`. Cost GAP. Login không headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    stamp = "2026-07-15 ~09:40 ICT"
    status = (
        "`EXO_FRED_DISPLACE_SPAM_PAUSED` / `OFFLINE_ALL_KILL__NO_MODEL0`"
        if all_kill
        else "`EXO_FRED_DISPLACE_SPAM_PAUSED` / `PROBE_SURVIVOR_PRESENT`"
    )
    lines_h = [
        f"- **ANTICARRY VOL-SPIKE CLOSEOUT ({stamp}) — {status}.**",
        "  Pivot after carry/swap-diff ALL_KILL; 6J densify INTAKE_KILL; G10 BLOCKED.",
        "  Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        lines_h.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    lines_h += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_ANTICARRY_VOLSPIKE_OFFLINE_PROBES.json`;",
        "  closeout `readouts/20260715_ANTICARRY_VOLSPIKE_SESSION_CLOSEOUT.md`;",
        "  VN `readouts/20260715_ANTICARRY_VOLSPIKE_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify vol AR / deadband / hold.",
        f"  Next class: {next_class}",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    bullet = "\n".join(lines_h)
    header = (
        "# Hot Cache\n\n"
        f"Updated: {stamp} | Anti-carry vol-spike offline "
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


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"mt5 init fail: {mt5.last_error()}")
    try:
        lagged = load_rates_lagged()
        books = {s: build(s) for s in UNIVERSE}
        innov = global_vol_innovation(books)
        results = [
            probe_volspike(
                books,
                lagged,
                innov,
                False,
                "HYP-FX3-ANTICARRY-VOLSPIKE-H4-001",
                "Vol innov>0 → anti-carry extremes; H4; SL1.5 ATR; hold≤8",
            ),
            probe_volspike(
                books,
                lagged,
                innov,
                True,
                "HYP-FX3-ANTICARRY-VOLSPIKE-D1CONFIRM-001",
                "Same + 2D1 crowding-with-carry confirm before anti",
            ),
        ]
    finally:
        mt5.shutdown()

    payload: dict[str, Any] = {
        "schema": "anticarry_volspike_offline_probes.v1",
        "generated_at_utc": utc_now(),
        "parent": "carry_swap_diff_ALL_KILL__6J_INTAKE_KILL__G10_BLOCKED",
        "window": {"from": FROM.isoformat(), "to": TO.isoformat(), "weeks": WEEKS},
        "cost": {"base_rt_usd": BASE_COST, "grade": "UNVERIFIED_OFFLINE_PROXY_PLUS12"},
        "joint_screen": {"n_min": 80, "tpw": [1.5, 6.0], "pf_min": 1.20, "x1_5_pf_min": 1.15},
        "results": results,
        "model0_policy": "PROBE_SURVIVOR_ONLY",
        "receipt_sha256": None,
    }
    stub = {k: v for k, v in payload.items() if k != "receipt_sha256"}
    receipt = sha256_bytes(json.dumps(stub, indent=2, sort_keys=True).encode("utf-8"))
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_docs(results, receipt)
    append_registry(results, receipt)
    print("receipt", receipt)
    for r in results:
        print(r["hypothesis_id"], r["verdict"], r["metrics"], r["haircuts"]["x1_5"], r["kill_notes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
