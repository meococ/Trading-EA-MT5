#!/usr/bin/env python3
"""Greenfield book / monetization / cross-sectional offline joint screen.

Authority: post LNY EUR/GBP ALL_KILL; EXO_FRED_DISPLACE_SPAM_PAUSED; no Real stall.
Panel: Sonic trader / quant validation / MQL5 systems (cursor-grok-4.5-high-fast).

FORBIDDEN densify / clone families:
  session-overlap / IB / ORB / Asia-coil / LNY fade-coil-catchup
  RR2 exit / RR2 gates / FRED displace-ToT / COT size|z
  Wave1-9 / Structural V1-V9 / MaxKZ-RR densify

A priori frozen (≥3 greenfield classes; probe top 3):
  1) HYP-XS-USD-RESIDUAL-H1-FADE-BOOK-001
  2) HYP-XS-USD-MOM-H1-TOP1-BOOK-001
  3) HYP-AUDNZD-H1-RESIDUAL-ZMR-001

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
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

OUT_JSON = PRE / "20260715_GREENFIELD_BOOK_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_BOOK_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_BOOK_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_BOOK_DESIGN_MEMO.md"
OUT_PANEL = READ / "20260715_GREENFIELD_3CRITIC_PANEL_MERGE.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_BOOK_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_BOOK_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005

# --- Object 1: XS USD residual fade book ---
XS_UNIVERSE = ("EURUSD", "GBPUSD", "AUDUSD", "USDJPY")
XS_SIGN = {"EURUSD": -1.0, "GBPUSD": -1.0, "AUDUSD": -1.0, "USDJPY": 1.0}
XS_RET_BARS = 24
XS_Z_LB = 60
XS_Z_ENTRY = 1.50
XS_SL_ATR = 1.20
XS_RR = 2.0
XS_MAX_HOLD = 24
XS_FIRE_HOUR = 16  # UTC decision on closed H1 15→16 bar
XS_MAX_BOOK = 1  # top |z| only — architecture: concentrated book

# --- Object 2: XS USD momentum top1 book ---
MOM_RET_BARS = 24
MOM_Z_LB = 60
MOM_Z_ENTRY = 0.75  # factor intensity floor
MOM_SL_ATR = 1.20
MOM_RR = 2.0
MOM_MAX_HOLD = 24
MOM_FIRE_HOUR = 16

# --- Object 3: AUDNZD residual Z MR ---
AUDNZD_Z_LB = 48
AUDNZD_Z_ENTRY = 2.00
AUDNZD_SL_ATR = 1.50
AUDNZD_RR = 1.50
AUDNZD_MAX_HOLD = 36
AUDNZD_FIRE_HOUR = 12  # mid-London decision, not LNY overlap window


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
    if n >= 80 and pf > 1.20 and 1.5 <= tpw <= 6.0 and x15 >= 1.15:
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
        "symbol": symbol,
        "time": rates["time"].astype(np.int64),
        "open": rates["open"].astype(float),
        "high": rates["high"].astype(float),
        "low": rates["low"].astype(float),
        "close": rates["close"].astype(float),
    }


def hour_u(ts: int) -> int:
    return int(datetime.utcfromtimestamp(ts).hour)


def day_key(ts: int) -> str:
    return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")


def tradeable(ts: int) -> bool:
    # Mon–Fri only (UTC dow: Mon=0)
    return datetime.utcfromtimestamp(ts).weekday() < 5


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


def pack(hid: str, symbol: str, funnel: dict, trades: list[dict], note: str = "") -> dict:
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
        "note": note or "cost proxy +$12/trade flat; NOT research-grade freeze",
        "n_trades_raw": len(trades),
    }


def align_books(books: dict[str, dict]) -> tuple[np.ndarray, dict[str, dict]]:
    """Intersect on exact H1 timestamps; return common times + sliced series."""
    sets = [set(b["time"].tolist()) for b in books.values()]
    common = sorted(set.intersection(*sets))
    if len(common) < 1000:
        raise RuntimeError(f"sync too thin: {len(common)}")
    t = np.array(common, dtype=np.int64)
    out: dict[str, dict] = {}
    for sym, b in books.items():
        idx = {int(x): i for i, x in enumerate(b["time"])}
        ii = np.array([idx[int(x)] for x in t], dtype=np.int64)
        out[sym] = {
            "symbol": sym,
            "time": t,
            "open": b["open"][ii],
            "high": b["high"][ii],
            "low": b["low"][ii],
            "close": b["close"][ii],
        }
        out[sym]["atr"] = atr14(out[sym]["high"], out[sym]["low"], out[sym]["close"])
    return t, out


def usd_signed_ret(sym: str, close: np.ndarray, i: int, bars: int) -> float:
    if i < bars:
        return float("nan")
    c0, c1 = close[i - bars], close[i]
    if c0 <= 0 or c1 <= 0:
        return float("nan")
    raw = math.log(c1 / c0)
    return XS_SIGN[sym] * raw


def rolling_z(series: list[float], lb: int, i: int) -> float:
    if i < lb:
        return float("nan")
    window = series[i - lb + 1 : i + 1]
    if any(math.isnan(x) for x in window):
        return float("nan")
    mu = sum(window) / lb
    var = sum((x - mu) ** 2 for x in window) / lb
    if var <= 1e-18:
        return float("nan")
    return (series[i] - mu) / math.sqrt(var)


def probe_xs_residual_fade(synced: dict[str, dict]) -> dict:
    """Fade the pair with most extreme residual vs equal-weight USD factor."""
    t = synced["EURUSD"]["time"]
    n = len(t)
    # Precompute USD moves and factor
    u = {s: np.full(n, np.nan) for s in XS_UNIVERSE}
    for s in XS_UNIVERSE:
        c = synced[s]["close"]
        for i in range(n):
            u[s][i] = usd_signed_ret(s, c, i, XS_RET_BARS)
    factor = np.full(n, np.nan)
    resid = {s: np.full(n, np.nan) for s in XS_UNIVERSE}
    for i in range(n):
        vals = [u[s][i] for s in XS_UNIVERSE]
        if any(math.isnan(v) for v in vals):
            continue
        f = float(np.mean(vals))
        factor[i] = f
        for s in XS_UNIVERSE:
            resid[s][i] = u[s][i] - f

    resid_z = {s: [float("nan")] * n for s in XS_UNIVERSE}
    for s in XS_UNIVERSE:
        series = resid[s].tolist()
        for i in range(n):
            resid_z[s][i] = rolling_z(series, XS_Z_LB, i)

    trades: list[dict] = []
    funnel = {"n_decision_bars": 0, "n_armed": 0, "n_trades": 0, "by_symbol": {}}
    last_day = None
    for i in range(n):
        if hour_u(int(t[i])) != XS_FIRE_HOUR:
            continue
        if not tradeable(int(t[i])):
            continue
        dk = day_key(int(t[i]))
        if dk == last_day:
            continue
        funnel["n_decision_bars"] += 1
        # pick max |z|
        cands = []
        for s in XS_UNIVERSE:
            z = resid_z[s][i]
            atr = synced[s]["atr"][i]
            if math.isnan(z) or math.isnan(atr) or atr <= 0:
                continue
            if abs(z) < XS_Z_ENTRY:
                continue
            cands.append((abs(z), s, z, atr))
        if not cands:
            continue
        cands.sort(reverse=True)
        funnel["n_armed"] += 1
        for _, s, z, atr in cands[:XS_MAX_BOOK]:
            # residual >0 means pair's USD-move above factor → fade: lean against residual
            # Trade the FX pair: if residual positive (USD-signed excess), fade toward mean
            # USD-signed residual positive on EURUSD means EURUSD fell more than basket
            # (because s_EUR=-1: large EUR drop → large positive u). Fade residual → buy EURUSD.
            # Direction on pair price: opposite to raw residual sign mapped through XS_SIGN.
            # residual_z > 0 → expect residual → 0 → reduce USD-signed u → move opposite to sign*price
            # price direction = -sign(residual) * XS_SIGN  (because u = sign * dlogP)
            # If resid>0: want Δu <0 → sign*ΔlogP <0 → ΔlogP has sign opposite to XS_SIGN
            # → direction_price = -XS_SIGN when resid>0; = +XS_SIGN when resid<0
            # → direction_price = -np.sign(resid) * XS_SIGN
            direction = int(-np.sign(z) * XS_SIGN[s])
            if direction == 0:
                continue
            entry = float(synced[s]["close"][i])
            sl = entry - direction * XS_SL_ATR * atr
            tp = entry + direction * XS_RR * XS_SL_ATR * atr
            # enter next bar open to avoid same-bar lookahead on close signal
            i0 = i + 1
            if i0 >= n - 2:
                continue
            entry = float(synced[s]["open"][i0])
            sl = entry - direction * XS_SL_ATR * atr
            tp = entry + direction * XS_RR * XS_SL_ATR * atr
            r = resolve(
                direction,
                entry,
                sl,
                tp,
                i0,
                synced[s]["high"],
                synced[s]["low"],
                synced[s]["close"],
                XS_MAX_HOLD,
                XS_RR,
            )
            if r is None:
                continue
            trades.append(
                {
                    "r": r,
                    "symbol": s,
                    "ts": int(t[i0]),
                    "z": round(float(z), 4),
                    "direction": direction,
                }
            )
            funnel["by_symbol"][s] = funnel["by_symbol"].get(s, 0) + 1
            funnel["n_trades"] += 1
            last_day = dk
            break
    return pack(
        "HYP-XS-USD-RESIDUAL-H1-FADE-BOOK-001",
        "BOOK:EUR+GBP+AUD+USDJPY",
        funnel,
        trades,
        "closed-bar H1 sync residual fade; NOT M15 XS PB-break; NOT LNY fade",
    )


def probe_xs_momentum_top1(synced: dict[str, dict]) -> dict:
    """Long the pair already expressing USD factor most strongly (continuation)."""
    t = synced["EURUSD"]["time"]
    n = len(t)
    u = {s: np.full(n, np.nan) for s in XS_UNIVERSE}
    for s in XS_UNIVERSE:
        c = synced[s]["close"]
        for i in range(n):
            u[s][i] = usd_signed_ret(s, c, i, MOM_RET_BARS)
    factor = np.full(n, np.nan)
    for i in range(n):
        vals = [u[s][i] for s in XS_UNIVERSE]
        if any(math.isnan(v) for v in vals):
            continue
        factor[i] = float(np.mean(vals))
    factor_z = [rolling_z(factor.tolist(), MOM_Z_LB, i) for i in range(n)]

    trades: list[dict] = []
    funnel = {"n_decision_bars": 0, "n_armed": 0, "n_trades": 0, "by_symbol": {}}
    last_day = None
    for i in range(n):
        if hour_u(int(t[i])) != MOM_FIRE_HOUR:
            continue
        if not tradeable(int(t[i])):
            continue
        dk = day_key(int(t[i]))
        if dk == last_day:
            continue
        funnel["n_decision_bars"] += 1
        fz = factor_z[i]
        if math.isnan(fz) or abs(fz) < MOM_Z_ENTRY:
            continue
        # strongest aligned pair: max u if factor>0 (USD strength), min u if factor<0
        scored = []
        for s in XS_UNIVERSE:
            ui = u[s][i]
            atr = synced[s]["atr"][i]
            if math.isnan(ui) or math.isnan(atr) or atr <= 0:
                continue
            align = ui if factor[i] > 0 else -ui
            scored.append((align, s, ui, atr))
        if not scored:
            continue
        scored.sort(reverse=True)
        align, s, ui, atr = scored[0]
        if align <= 0:
            continue
        funnel["n_armed"] += 1
        # Continue USD factor: if factor>0 (USD strength), trade pair in USD-strength direction
        # USD strength on EURUSD → short EURUSD (direction = XS_SIGN? wait)
        # u = sign * dlogP; USD strength → positive u. Continue → more positive u →
        # ΔlogP has same sign as XS_SIGN → direction_price = XS_SIGN when factor>0
        direction = int(np.sign(factor[i]) * XS_SIGN[s])
        if direction == 0:
            continue
        i0 = i + 1
        if i0 >= n - 2:
            continue
        entry = float(synced[s]["open"][i0])
        sl = entry - direction * MOM_SL_ATR * atr
        tp = entry + direction * MOM_RR * MOM_SL_ATR * atr
        r = resolve(
            direction,
            entry,
            sl,
            tp,
            i0,
            synced[s]["high"],
            synced[s]["low"],
            synced[s]["close"],
            MOM_MAX_HOLD,
            MOM_RR,
        )
        if r is None:
            continue
        trades.append(
            {
                "r": r,
                "symbol": s,
                "ts": int(t[i0]),
                "factor_z": round(float(fz), 4),
                "direction": direction,
            }
        )
        funnel["by_symbol"][s] = funnel["by_symbol"].get(s, 0) + 1
        funnel["n_trades"] += 1
        last_day = dk
    return pack(
        "HYP-XS-USD-MOM-H1-TOP1-BOOK-001",
        "BOOK:EUR+GBP+AUD+USDJPY",
        funnel,
        trades,
        "closed-bar H1 XS mom top1; NOT M15 XS PB-break; NOT lead-lag catch-up",
    )


def probe_audnzd_residual_zmr(aud: dict, nzd: dict) -> dict:
    """Trade AUDNZD when log-spread z extreme (relative-value MR)."""
    books = {"AUDUSD": aud, "NZDUSD": nzd}
    t, syn = align_books(books)
    a = syn["AUDUSD"]
    zpair = syn["NZDUSD"]
    n = len(t)
    spread = np.full(n, np.nan)
    for i in range(n):
        if a["close"][i] <= 0 or zpair["close"][i] <= 0:
            continue
        spread[i] = math.log(a["close"][i]) - math.log(zpair["close"][i])
    # Use AUDUSD ATR as proxy for leg risk; direction on AUDUSD, hedge notionally NZD
    # For offline simplicity: trade AUDUSD only in residual direction (AUD rich/cheap vs NZD)
    sz = [rolling_z(spread.tolist(), AUDNZD_Z_LB, i) for i in range(n)]
    trades: list[dict] = []
    funnel = {"n_decision_bars": 0, "n_armed": 0, "n_trades": 0}
    last_day = None
    for i in range(n):
        if hour_u(int(t[i])) != AUDNZD_FIRE_HOUR:
            continue
        if not tradeable(int(t[i])):
            continue
        dk = day_key(int(t[i]))
        if dk == last_day:
            continue
        funnel["n_decision_bars"] += 1
        z = sz[i]
        atr = a["atr"][i]
        if math.isnan(z) or math.isnan(atr) or atr <= 0:
            continue
        if abs(z) < AUDNZD_Z_ENTRY:
            continue
        funnel["n_armed"] += 1
        # spread = log AUD - log NZD; z>0 AUD rich → short AUDUSD (fade)
        direction = -1 if z > 0 else 1
        i0 = i + 1
        if i0 >= n - 2:
            continue
        entry = float(a["open"][i0])
        sl = entry - direction * AUDNZD_SL_ATR * atr
        tp = entry + direction * AUDNZD_RR * AUDNZD_SL_ATR * atr
        r = resolve(
            direction,
            entry,
            sl,
            tp,
            i0,
            a["high"],
            a["low"],
            a["close"],
            AUDNZD_MAX_HOLD,
            AUDNZD_RR,
        )
        if r is None:
            continue
        trades.append({"r": r, "symbol": "AUDUSD", "ts": int(t[i0]), "z": round(float(z), 4)})
        funnel["n_trades"] += 1
        last_day = dk
    return pack(
        "HYP-AUDNZD-H1-RESIDUAL-ZMR-001",
        "AUDUSD(vs NZDUSD spread)",
        funnel,
        trades,
        "AUD–NZD log-spread Z MR via AUDUSD leg; NOT EURGBP lead; NOT LNY catch-up",
    )


def append_registry(rows: list[dict]) -> None:
    with REG.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_panel_and_docs(results: list[dict], receipt_sha: str) -> None:
    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    all_kill = len(survivors) == 0

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# Merge memo — Greenfield 3-critic panel (post-LNY)",
                "",
                "Date: 2026-07-15",
                "Panel: Sonic trader / quant validation / MQL5 systems (`cursor-grok-4.5-high-fast`)",
                "Authority: Owner R&D continue; no Real stall; login never headline",
                f"Receipt: `{receipt_sha}`",
                "",
                "## Critic theses (a priori classes)",
                "",
                "| Critic | Greenfield class | Why not exhausted shelf |",
                "|---|---|---|",
                "| Sonic trader | Cross-sectional USD **residual fade book** | Relative-value object across majors; invalidation = residual z mean-revert or ATR stop — **≠** LNY session fade/coil/catch-up |",
                "| Quant validation | Cross-sectional USD **momentum top-1 book** | Book cadence from daily factor intensity; concentrated top-1 avoids CorrCap blend — **≠** RR2 gates / FRED / COT |",
                "| MQL5/MT5 systems | **AUD–NZD residual Z-MR** (AUDUSD leg) | Executable closed-bar sync; commodity-dollar RV — **≠** EURGBP→EURUSD lead, **≠** exo displace |",
                "",
                "## Rejected a priori (clone spam)",
                "",
                "- Session-overlap / IB / ORB / Asia-coil / LNY fade-coil-catchup densify",
                "- RR2 BE@1R / MFE stall / vol-target / H4-regime / COT size|z / FRED displace-ToT",
                "- Phase-0 SB+Spark CorrCap reopen; MaxKZ/RR densify",
                "- Invent research-grade cost freeze from 2-day tick sample",
                "- Rescue densify of Wave1–9 / Structural V1–V9 nearest misses",
                "",
                "## Offline joint screen",
                "",
                "| ID | N | PF | tpw | x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
            ]
            + [
                (
                    f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
                    f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | **{r['verdict']}** |"
                )
                for r in results
            ]
            + [
                "",
                "Survivor bar: N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15.",
                "",
                "## Research conclusion (evidence-backed)",
                "",
            ]
            + (
                [
                    "Public **price + currently frozen exo panels** have now failed joint",
                    "thick+cadence under a priori +$12 across: FRED displace/ToT, RR2 exit/gates,",
                    "session structure Waves/V1–V9/LNY, COT size|z, and this greenfield",
                    "XS/RV book board. **No offline survivor** → Model 0 withheld.",
                    "",
                    "Highest-EV autonomous next experiment (do not idle):",
                    "1. **Acquire new surface** — multi-month same-broker tick bid/ask +",
                    "   session×symbol commission/slip so `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001`",
                    "   (M15 tick-synced) and research-grade cost rebind become legal; **or**",
                    "2. **Rebuild EA monetization paradigm** — leave fixed-RR scalp P&L engine;",
                    "   design a new contract (e.g. maker/microstructure or multi-day carry strip",
                    "   with honest cost) only after Owner scope update in `hot.md`.",
                    "",
                    "Best shelf remains RR2 `194548` (research HIT; GOAL +$12 unmet).",
                ]
                if all_kill
                else [
                    "At least one greenfield survivor — Model 0 authorized only for survivors.",
                    "Do not densify losers. Best shelf still RR2 `194548` until Model 0 beats it.",
                ]
            )
            + [
                "",
                "## Coordinator decision",
                "",
                f"- Survivors: **{len(survivors)}** / {len(results)}",
                "- Model 0: "
                + (
                    "WITHHELD (zero PROBE_SURVIVOR)"
                    if all_kill
                    else "AUTHORIZED for survivors only"
                ),
                "- `EXO_FRED_DISPLACE_SPAM_PAUSED` remains.",
                "- Login never headline; QFSI 006 may keep accumulating in parallel.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# De-dup clearance — Greenfield book board",
                "",
                "Status: **CLEARED** for offline probe only (3 greenfield objects).",
                "",
                "| ID | Mechanism | Explicit ≠ |",
                "|---|---|---|",
                "| `HYP-XS-USD-RESIDUAL-H1-FADE-BOOK-001` | H1 sync residual fade top\\|z\\| | ≠ M15 XS USD-factor PB-break (blocked); ≠ LNY EUR fade; ≠ EURGBP lead; ≠ JPY catch-up |",
                "| `HYP-XS-USD-MOM-H1-TOP1-BOOK-001` | H1 sync factor intensity → top1 continuation | ≠ residual fade twin; ≠ lead-lag; ≠ RR2 gate; ≠ FRED |",
                "| `HYP-AUDNZD-H1-RESIDUAL-ZMR-001` | AUD–NZD log-spread Z MR via AUDUSD | ≠ EURGBP→EURUSD; ≠ LNY catch-up; ≠ WTI-USDCAD commodity clone |",
                "",
                "Not cleared: densify / rescue of any killed family above.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — Greenfield book / XS / RV board",
                "",
                "Date: 2026-07-15",
                "Lane: single; no-Git; offline-first; `EXO_FRED_DISPLACE_SPAM_PAUSED`",
                "",
                "## Problem",
                "",
                "LNY EUR/GBP 3/3 KILL. Session/IB/ORB/coil/FRED/RR2-exit/COT boards exhausted.",
                "Need true greenfield classes that can hit joint thick+cadence under +$12.",
                "",
                "## Design 1 — XS USD residual fade book",
                "",
                "`HYP-XS-USD-RESIDUAL-H1-FADE-BOOK-001`",
                "",
                "**Thesis:** After a common-USD move, the pair with extreme residual vs equal-weight",
                "factor mean-reverts; concentrate book on top |z| once/day.",
                "",
                "**Frozen:** universe EUR/GBP/AUD/USDJPY; ret=24H1; z_lb=60; |z|≥1.5; fire UTC16;",
                "SL=1.2 ATR; RR=2; max_hold=24; enter next open; 1 trade/day.",
                "",
                "## Design 2 — XS USD momentum top1 book",
                "",
                "`HYP-XS-USD-MOM-H1-TOP1-BOOK-001`",
                "",
                "**Thesis:** When |factor_z|≥0.75, continue USD factor via the strongest aligned pair.",
                "",
                "**Frozen:** same universe; factor mean of signed 24H1 returns; fire UTC16;",
                "SL=1.2 ATR; RR=2; max_hold=24; 1 trade/day.",
                "",
                "## Design 3 — AUD–NZD residual Z-MR",
                "",
                "`HYP-AUDNZD-H1-RESIDUAL-ZMR-001`",
                "",
                "**Thesis:** AUD vs NZD log-spread extremes mean-revert (commodity-dollar RV).",
                "",
                "**Frozen:** spread=ln(AUDUSD)−ln(NZDUSD); z_lb=48; |z|≥2; fire UTC12;",
                "trade AUDUSD leg; SL=1.5 ATR; RR=1.5; max_hold=36; 1/day.",
                "",
                "## Model 0 policy",
                "",
                "Only if offline `PROBE_SURVIVOR`. Else withhold. No Real stall required.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    lines = [
        "# Offline probes — Greenfield book / XS / RV",
        "",
        f"Receipt: `{receipt_sha}`",
        "",
        "| ID | N | PF | tpw | x1.5 | Verdict | Notes |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for r in results:
        lines.append(
            f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
            f"{r['metrics']['tpw']} | {r['haircuts']['x1_5']['pf']} | **{r['verdict']}** | "
            f"{','.join(r['kill_notes']) or '—'} |"
        )
    lines += [
        "",
        "Survivor bar: N≥80 ∧ PF>1.20 ∧ tpw∈[1.5,6] ∧ +$12 x1.5≥1.15.",
        "",
        f"Model 0: {'WITHHELD' if all_kill else 'survivors only'}.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — Greenfield book board",
                "",
                "Date: 2026-07-15",
                "Status: `EXO_FRED_DISPLACE_SPAM_PAUSED` / "
                + (
                    "`OFFLINE_ALL_KILL / NO_MODEL0`"
                    if all_kill
                    else "`PROBE_SURVIVOR_PRESENT`"
                ),
                "Lane: single checkout; no-Git; no Real stall",
                "",
                "## Board",
                "",
                "| ID | N | PF | tpw | stress x1.5 | Verdict |",
                "|---|---:|---:|---:|---:|---|",
            ]
            + [
                (
                    f"| `{r['hypothesis_id']}` | {r['metrics']['n']} | {r['metrics']['pf']} | "
                    f"{r['metrics']['tpw']} | **{r['haircuts']['x1_5']['pf']}** | **{r['verdict']}** |"
                )
                for r in results
            ]
            + [
                "",
                f"Receipt: `{receipt_sha}`",
                "Panel: `readouts/20260715_GREENFIELD_3CRITIC_PANEL_MERGE.md`",
                "Design: `readouts/20260715_GREENFIELD_BOOK_DESIGN_MEMO.md`",
                "De-dup: `readouts/20260715_GREENFIELD_BOOK_DEDUP_CLEARANCE.md`",
                "Probes: `preflight/20260715_GREENFIELD_BOOK_OFFLINE_PROBES.json`",
                "",
                "## Model 0",
                "",
                (
                    "Withheld (zero PROBE_SURVIVOR)."
                    if all_kill
                    else "Authorized for survivors only."
                ),
                "",
                "## Decisions",
                "",
                "1. Keep **`EXO_FRED_DISPLACE_SPAM_PAUSED`**.",
                "2. Do **not** densify XS z / mom factor_z / AUDNZD z from this readout.",
                "3. Do **not** revive LNY / RR2 exit / FRED / COT / Asia coil densify.",
                "4. Best shelf unchanged: RR2 `194548`. GOAL unmet.",
                "",
                "## Next autonomous EV (non-login-only)",
                "",
            ]
            + (
                [
                    "1. **Highest EV:** acquire multi-month same-broker tick bid/ask +",
                    "   commission/slip surface (unlock legal M15 XS USD-factor + cost rebind),",
                    "   **or** Owner-scoped rebuild of EA monetization paradigm beyond fixed-RR scalp.",
                    "2. Keep QFSI 006 accumulating; rebind harness `--execute` only on gate GO.",
                    "3. Do not idle on another session-structure clone board.",
                ]
                if all_kill
                else [
                    "1. Model 0 matched control/challenger for survivors only.",
                    "2. Keep QFSI 006 accumulating in parallel.",
                ]
            )
            + ["",]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# Brief hành động (VN) — Greenfield book board",
                "",
                "## Kết quả",
                "",
            ]
            + [
                (
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF **{r['metrics']['pf']}** "
                    f"tpw **{r['metrics']['tpw']}** x1.5 **{r['haircuts']['x1_5']['pf']}** → "
                    f"**{r['verdict']}**"
                )
                for r in results
            ]
            + [
                "",
                "## Ý nghĩa",
                "",
                (
                    "Ba lớp greenfield (XS residual fade / XS mom top1 / AUDNZD RV) **đều KILL** "
                    "offline dưới +$12. Không Model 0. Kết luận nghiên cứu: price công khai + exo "
                    "hiện có **chưa** cho joint thick+cadence đạt GOAL. Next EV cao nhất = "
                    "**acquire surface tick/cost mới** hoặc **Owner mở scope rebuild monetization** "
                    "— không clone session/FRED/RR2."
                    if all_kill
                    else "Có survivor offline — chỉ Model 0 cho survivor; không densify loser."
                ),
                "",
                "## Không làm",
                "",
                "- Densify z / factor_z / AUDNZD params từ readout này",
                "- Revive LNY / Asia coil / RR2 exit / FRED spam / COT size|z",
                "- Coi login Real là headline / stall discovery",
                "",
                f"Shelf tốt nhất vẫn RR2 `194548`. Receipt `{receipt_sha[:16]}…`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def patch_hot(results: list[dict], receipt_sha: str) -> None:
    survivors = [r for r in results if r["verdict"] == "PROBE_SURVIVOR"]
    all_kill = len(survivors) == 0
    lines = HOT.read_text(encoding="utf-8").splitlines()
    # Replace header updated line
    if lines and lines[0].startswith("# Hot Cache"):
        pass
    # Build new Active Truth block
    board_lines = []
    for i, r in enumerate(results, 1):
        m = r["metrics"]
        hc = r["haircuts"]
        board_lines.append(
            f"  {i}. `{r['hypothesis_id']}` N=**{m['n']}** PF **{m['pf']}** tpw "
            f"**{m['tpw']}** x1.5 **{hc['x1_5']['pf']}** → **{r['verdict'].replace('KILLED_AT_OFFLINE_PROBE','KILL').replace('PROBE_SURVIVOR','SURVIVOR')}**"
            + (f" ({','.join(r['kill_notes'])})." if r['kill_notes'] else ".")
        )
    block = [
        "# Hot Cache",
        "",
        "Updated: 2026-07-15 ~01:20 ICT | Greenfield XS/RV book "
        + ("3/3 KILL" if all_kill else "SURVIVOR")
        + "; `EXO_FRED_DISPLACE_SPAM_PAUSED`; RR2 `194548`; GOAL unmet",
        "",
        "## Active Truth",
        "",
        "- **GREENFIELD BOOK CLOSEOUT (2026-07-15 ~01:20 ICT) —",
        "  `EXO_FRED_DISPLACE_SPAM_PAUSED` / "
        + (
            "`OFFLINE_ALL_KILL` / `NO_MODEL0`."
            if all_kill
            else "`PROBE_SURVIVOR` / Model0 survivors only."
        ),
        "  3-critic panel (`cursor-grok-4.5-high-fast`) proposed ≥3 greenfield",
        "  classes **outside** session-overlap/IB/ORB/coil/LNY fade-coil-catchup,",
        "  RR2 exit/gates, FRED displace/ToT, COT size|z. Offline joint screen:",
    ] + board_lines + [
        f"  Receipt `{receipt_sha}`",
        "  `preflight/20260715_GREENFIELD_BOOK_OFFLINE_PROBES.json`; panel",
        "  `readouts/20260715_GREENFIELD_3CRITIC_PANEL_MERGE.md`; design",
        "  `readouts/20260715_GREENFIELD_BOOK_DESIGN_MEMO.md`; dedup",
        "  `readouts/20260715_GREENFIELD_BOOK_DEDUP_CLEARANCE.md`; closeout",
        "  `readouts/20260715_GREENFIELD_BOOK_SESSION_CLOSEOUT.md`; VN",
        "  `readouts/20260715_GREENFIELD_BOOK_VN_ACTION_BRIEF.md`.",
        (
            "  **Research conclusion:** public price + current exo cannot jointly"
            "  hit GOAL thick+cadence under a priori +$12 on exhausted boards +"
            "  this greenfield pack. **Highest-EV next:** acquire multi-month"
            "  tick bid/ask+commission/slip surface (unlock M15 XS USD-factor +"
            "  cost rebind) **or** Owner-scoped rebuild of EA monetization beyond"
            "  fixed-RR scalp — do not idle on session/FRED/RR2 clones."
            if all_kill
            else "  Model 0 authorized for survivors only; do not densify losers."
        ),
        "  Do not densify XS z / mom factor_z / AUDNZD z. Best shelf RR2 `194548`.",
        "  GOAL unmet.",
        "",
    ]
    # Find first "## Active Truth" and insert after header; keep prior active truths
    try:
        at = lines.index("## Active Truth")
    except ValueError:
        new_text = "\n".join(block + lines[1:])
        HOT.write_text(new_text + "\n", encoding="utf-8")
        return
    # Keep old active truth bullets but after new block's first bullet section
    # Reconstruct: new header+Active Truth intro+new bullet, then old bullets from previous first "-"
    # Find start of first old bullet after Active Truth
    rest = lines[at + 1 :]
    # skip blank lines
    i = 0
    while i < len(rest) and rest[i].strip() == "":
        i += 1
    old_active = rest[i:]
    # Also patch Next Move section
    text = "\n".join(block + old_active)
    # Replace Next Move active paragraph
    nm_marker = "## Next Move"
    if nm_marker in text:
        pre, post = text.split(nm_marker, 1)
        # rebuild Next Move head
        nm = [
            "## Next Move",
            "",
            "- **ACTIVE — Greenfield board closed; research-conclusion lane.**",
            "  `EXO_FRED_DISPLACE_SPAM_PAUSED` remains. LNY EUR/GBP + MFE/Asia +",
            "  FRED/RR2-exit/COT boards exhausted. Greenfield XS residual / XS mom /",
            "  AUDNZD RV "
            + ("**3/3 KILL** offline." if all_kill else "has survivor(s)."),
            (
                "  Evidence-backed conclusion: public price+current exo **do not**"
                "  jointly clear GOAL under +$12. Highest-EV next (non-login): (1)"
                "  acquire multi-month same-broker tick+cost surface to unlock"
                "  `HYP-SR-FX-CROSS-SECTIONAL-USD-FACTOR-001` + research-grade rebind;"
                "  **or** (2) Owner-scoped monetization paradigm rebuild beyond"
                "  fixed-RR scalp. Keep QFSI 006 accumulate. Do **not** densify"
                "  XS/AUDNZD/LNY/Asia/RR2-exit/FRED. Best shelf RR2 `194548`;"
                "  `231750` PARK_MISS. GOAL unmet."
                if all_kill
                else "  Next: Model 0 for survivors only. Keep QFSI 006. Best shelf"
                "  RR2 `194548`. GOAL unmet."
            ),
            "",
            "- **CLOSED — Greenfield XS/RV book:** "
            + ("3/3 KILL. " if all_kill else "survivor path. ")
            + "`readouts/20260715_GREENFIELD_BOOK_SESSION_CLOSEOUT.md`.",
            "- **CLOSED — LNY overlap EUR/GBP:** 3/3 KILL.",
            "  `readouts/20260715_LNY_OVERLAP_EURGBP_SESSION_CLOSEOUT.md`.",
        ]
        # Keep rest of post after first active bullet block — find second "- **CLOSED"
        # Simpler: take from first CLOSED in old Next Move
        post_lines = post.splitlines()
        # drop until we find historical CLOSED that isn't our new ones — keep from
        # "- **CLOSED — MFE" onward if present
        keep_from = None
        for j, ln in enumerate(post_lines):
            if ln.startswith("- **CLOSED — MFE"):
                keep_from = j
                break
            if ln.startswith("- **CLOSED — STRATEGY PIVOT"):
                keep_from = j
                break
        if keep_from is not None:
            nm.extend(post_lines[keep_from:])
        else:
            # keep everything after first blank-separated chunk
            nm.extend(post_lines)
        text = pre.rstrip() + "\n\n" + "\n".join(nm)
        if not text.endswith("\n"):
            text += "\n"
    HOT.write_text(text, encoding="utf-8")


def main() -> int:
    if not mt5.initialize():
        raise SystemExit(f"mt5 init fail: {mt5.last_error()}")
    try:
        books = {s: load(s) for s in XS_UNIVERSE}
        aud = load("AUDUSD")
        nzd = load("NZDUSD")
        _, synced = align_books(books)
        results = [
            probe_xs_residual_fade(synced),
            probe_xs_momentum_top1(synced),
            probe_audnzd_residual_zmr(aud, nzd),
        ]
    finally:
        mt5.shutdown()

    payload = {
        "schema": "greenfield_book_offline_probes_v1",
        "created_utc": utc_now(),
        "window": {"from": FROM.isoformat(), "to": TO.isoformat(), "weeks": WEEKS},
        "survivor_bar": {
            "n_min": 80,
            "pf_min": 1.20,
            "tpw_min": 1.5,
            "tpw_max": 6.0,
            "x15_pf_min": 1.15,
            "cost_proxy_usd": BASE_COST,
        },
        "forbidden_families": [
            "session_overlap_ib_orb_coil_lny_fade_catchup",
            "rr2_exit_gates",
            "fred_displace_tot",
            "cot_size_z",
        ],
        "panel": "sonic_trader+quant_validation+mql5_systems@cursor-grok-4.5-high-fast",
        "results": results,
        "survivors": [r["hypothesis_id"] for r in results if r["verdict"] == "PROBE_SURVIVOR"],
        "model0_policy": "survivors_only",
    }
    write_json(OUT_JSON, payload)
    receipt_sha = sha256_file(OUT_JSON)
    payload["receipt_sha256"] = receipt_sha
    write_json(OUT_JSON, payload)
    receipt_sha = sha256_file(OUT_JSON)

    write_panel_and_docs(results, receipt_sha)

    reg_rows = []
    for r in results:
        reg_rows.append(
            {
                "record_type": "candidate",
                "schema_version": 1,
                "hypothesis_id": r["hypothesis_id"],
                "state": (
                    "probe_survivor"
                    if r["verdict"] == "PROBE_SURVIVOR"
                    else "killed_at_offline_probe"
                ),
                "parent_candidate": None,
                "feature_family": "greenfield_xs_rv_book",
                "lane": "exo_fred_displace_spam_paused_greenfield_book",
                "setup_type": r["hypothesis_id"],
                "symbol": r["symbol"],
                "timeframe": "H1",
                "window": "2021.01.01-2025.12.31",
                "model": "offline_probe_only",
                "source_provenance": "20260715 greenfield 3-critic panel post LNY KILL",
                "prereg_path": None,
                "readout_path": "03. EA Developer/EA_SonicR/research/readouts/20260715_GREENFIELD_BOOK_SESSION_CLOSEOUT.md",
                "metrics": r["metrics"],
                "validation": {
                    "offline_probe": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                    "haircuts": r["haircuts"],
                    "kill_notes": r["kill_notes"],
                    "model0": r["model0"],
                    "funnel": r["funnel"],
                },
                "verdict": r["verdict"],
                "receipt_sha256": receipt_sha,
                "updated_at": "2026-07-15",
                "cost_grade": "A_PRIORI_FLAT_12_PROXY_NOT_RESEARCH_FREEZE",
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
