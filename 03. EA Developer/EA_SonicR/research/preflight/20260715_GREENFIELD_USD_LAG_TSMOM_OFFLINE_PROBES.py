#!/usr/bin/env python3
"""True greenfield joint screen post AONIA/thin3 ALL_KILL.

Outside densify shelves:
  ≠ AONIA wedge/level, ≠ CORRA bp, ≠ thin3 jump, ≠ TOM/gap/consec/XAU-z,
  ≠ anticarry/carry flush/fundproxy, ≠ D1 volregime, ≠ swing ADX/thrust/ROC,
  ≠ XS residual fade / XS mom top1, ≠ session LNY, ≠ FRED displace, ≠ RR2 exit.

A priori (≥2), +$12, Model 0 only if PROBE_SURVIVOR:
  1) HYP-FX3-H4-USD-MAJORITY-LAG-FOLLOW-001
  2) HYP-FX3-H4-TSMOM-BAND-CONT-001
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

OUT_JSON = PRE / "20260715_GREENFIELD_USD_LAG_TSMOM_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_USD_LAG_TSMOM_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_USD_LAG_TSMOM_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_USD_LAG_TSMOM_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_USD_LAG_TSMOM_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_USD_LAG_TSMOM_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

# --- Object 1: USD majority → lag follow ---
LAG_STRONG = 0.45
LAG_WEAK = 0.20
LAG_SL_ATR = 1.25
LAG_RR = 2.0
LAG_HOLD = 4  # H4 bars (~16 H1)
LAG_MAX_OPEN = 1
LAG_MAX_PER_DAY = 1

# --- Object 2: H4 TS-mom band continuation ---
TS_LB = 5
TS_LO = 1.0
TS_HI = 2.5
TS_BODY = 0.35
TS_SL_ATR = 1.20
TS_RR = 2.5
TS_HOLD = 10
TS_MAX_PER_DAY = 1
TS_MAX_OPEN = 3  # one per symbol


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def pf_of(pnls):
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls):
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [p - BASE_COST * mult for p in pnls]
        out[key] = {
            "pf": None if not cut else round(pf_of(cut) or 0.0, 4),
            "net": round(sum(cut), 2) if cut else 0.0,
            "exp": round(sum(cut) / len(cut), 4) if cut else 0.0,
        }
    return out


def metrics(pnls):
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


def joint_verdict(m, hc):
    notes = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0:
        notes.append("cadence_fail")
    if hc["x1_5"]["pf"] is None or hc["x1_5"]["pf"] < 1.25:
        notes.append("stress_fail")
    return ("PROBE_SURVIVOR", []) if not notes else ("KILLED_AT_OFFLINE_PROBE", notes)


def atr_arr(h, l, c, n=14):
    prev = np.roll(c, 1)
    prev[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev), np.abs(l - prev)))
    out = np.full_like(tr, np.nan, dtype=float)
    s = tr[:n].sum()
    out[n - 1] = s / n
    for i in range(n, len(tr)):
        s = s - tr[i - n] + tr[i]
        out[i] = s / n
    return out


def load(symbol, tf):
    rates = mt5.copy_rates_range(symbol, tf, FROM, TO)
    if rates is None or len(rates) < 100:
        raise RuntimeError(f"{symbol} tf={tf}: {mt5.last_error()}")
    return {
        "t": rates["time"].astype(np.int64),
        "o": rates["open"].astype(float),
        "h": rates["high"].astype(float),
        "l": rates["low"].astype(float),
        "c": rates["close"].astype(float),
    }


def pip_size(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.01 if "JPY" in symbol else 0.0001
    return info.point * (10 if info.digits in (3, 5) else 1)


def cash_pnl(symbol, side, entry, exit_px, lots):
    info = mt5.symbol_info(symbol)
    tick_val = float(info.trade_tick_value) if info else 1.0
    tick_size = float(info.trade_tick_size) if info else pip_size(symbol)
    if tick_size <= 0:
        tick_size = pip_size(symbol)
    return (exit_px - entry) * side / tick_size * tick_val * lots


def risk_lots(symbol, entry, sl):
    info = mt5.symbol_info(symbol)
    risk = DEPOSIT * RISK_FRAC
    dist = abs(entry - sl)
    if dist <= 0 or info is None:
        return 0.01
    tick_val = float(info.trade_tick_value) or 1.0
    tick_size = float(info.trade_tick_size) or pip_size(symbol)
    loss = dist / tick_size * tick_val
    if loss <= 0:
        return 0.01
    return min(5.0, max(0.01, math.floor(risk / loss * 100) / 100))


def usd_signed_body(sym, o, c, atr):
    """Positive = USD strength impulse on this print (body / ATR)."""
    if not np.isfinite(atr) or atr <= 0:
        return 0.0
    body = (c - o) / atr
    if sym in ("EURUSD", "GBPUSD"):
        return -body
    return body  # USDJPY


def pair_side_for_usd(sym, usd_sign):
    """Trade side on pair that is WITH USD majority (usd_sign +1/-1)."""
    if sym in ("EURUSD", "GBPUSD"):
        return -1 if usd_sign > 0 else 1
    return 1 if usd_sign > 0 else -1


def manage_exits(open_pos, data, ts, closed, hold_limit):
    still = []
    for pos in open_pos:
        sym = pos["sym"]
        d = data[sym]
        idx = int(np.searchsorted(d["t"], ts, side="left"))
        if idx >= len(d["t"]) or d["t"][idx] != ts:
            still.append(pos)
            continue
        exit_px = None
        reason = None
        if pos["side"] > 0:
            if d["l"][idx] <= pos["sl"]:
                exit_px, reason = pos["sl"], "sl"
            elif d["h"][idx] >= pos["tp"]:
                exit_px, reason = pos["tp"], "tp"
        else:
            if d["h"][idx] >= pos["sl"]:
                exit_px, reason = pos["sl"], "sl"
            elif d["l"][idx] <= pos["tp"]:
                exit_px, reason = pos["tp"], "tp"
        pos["bars"] += 1
        if exit_px is None and pos["bars"] >= hold_limit:
            exit_px, reason = d["c"][idx], "time"
        if exit_px is not None:
            closed.append(
                {
                    "pnl": cash_pnl(sym, pos["side"], pos["entry"], exit_px, pos["lots"]),
                    "reason": reason,
                    "sym": sym,
                }
            )
        else:
            still.append(pos)
    return still


def flush_open(open_pos, data, closed):
    for pos in open_pos:
        d = data[pos["sym"]]
        closed.append(
            {
                "pnl": cash_pnl(
                    pos["sym"], pos["side"], pos["entry"], float(d["c"][-1]), pos["lots"]
                ),
                "reason": "eod",
                "sym": pos["sym"],
            }
        )


def summarize(closed):
    pnls = [x["pnl"] for x in closed]
    detail = {"by_reason": {}, "by_sym": {}}
    for x in closed:
        detail["by_reason"][x["reason"]] = detail["by_reason"].get(x["reason"], 0) + 1
        detail["by_sym"][x["sym"]] = detail["by_sym"].get(x["sym"], 0) + 1
    return pnls, detail


def probe_usd_majority_lag(data):
    """≥2 FX3 strong same-USD H4; lag quiet → follow USD on lag at next H4 open."""
    closed = []
    clock = data["EURUSD"]["t"]
    open_pos = []
    day_count = {}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data, ts, closed, LAG_HOLD)

        if dt.weekday() >= 5:
            continue
        if len(open_pos) >= LAG_MAX_OPEN:
            continue
        # Signal uses prior closed H4 (i-1); enter at this bar open
        j = i - 1
        if j < 20:
            continue

        moves = {}
        for sym in FX3:
            d = data[sym]
            idx = int(np.searchsorted(d["t"], clock[j], side="left"))
            if idx >= len(d["t"]) or d["t"][idx] != clock[j]:
                moves = None
                break
            atr = d["atr"][idx]
            moves[sym] = usd_signed_body(sym, d["o"][idx], d["c"][idx], atr)
        if moves is None:
            continue

        for usd_sign in (1, -1):
            strong = [s for s, m in moves.items() if m * usd_sign >= LAG_STRONG]
            weak = [s for s, m in moves.items() if m * usd_sign < LAG_WEAK]
            if len(strong) < 2:
                continue
            # lag = not strong and weak (quiet vs majority)
            lag_cands = [s for s in FX3 if s not in strong and s in weak]
            if len(lag_cands) != 1:
                continue
            lag = lag_cands[0]
            # day cap
            day_key = (dt.date().isoformat(),)
            if day_count.get(day_key, 0) >= LAG_MAX_PER_DAY:
                continue
            if any(p["sym"] == lag for p in open_pos):
                continue

            d = data[lag]
            eidx = int(np.searchsorted(d["t"], ts, side="left"))
            if eidx >= len(d["t"]) or d["t"][eidx] != ts:
                continue
            atr = d["atr"][eidx - 1] if eidx >= 1 else d["atr"][eidx]
            if not np.isfinite(atr) or atr <= 0:
                continue
            side = pair_side_for_usd(lag, usd_sign)
            entry = float(d["o"][eidx])
            sl = entry - side * LAG_SL_ATR * atr
            tp = entry + side * LAG_RR * LAG_SL_ATR * atr
            open_pos.append(
                {
                    "sym": lag,
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": risk_lots(lag, entry, sl),
                    "bars": 0,
                }
            )
            day_count[day_key] = day_count.get(day_key, 0) + 1
            break  # at most one signal per bar

    flush_open(open_pos, data, closed)
    return summarize(closed)


def probe_tsmom_band(data):
    """5-bar H4 return sum in ATR units inside [1.0, 2.5] + body gate → continue."""
    closed = []
    clock = data["EURUSD"]["t"]
    open_pos = []
    day_count = {}

    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        open_pos = manage_exits(open_pos, data, ts, closed, TS_HOLD)

        if dt.weekday() >= 5:
            continue
        if len(open_pos) >= TS_MAX_OPEN:
            continue
        open_syms = {p["sym"] for p in open_pos}
        j = i - 1  # signal on closed bar
        if j < TS_LB + 20:
            continue

        day = dt.date().isoformat()

        for sym in FX3:
            if sym in open_syms or len(open_pos) >= TS_MAX_OPEN:
                continue
            if day_count.get((day, sym), 0) >= TS_MAX_PER_DAY:
                continue
            d = data[sym]
            sidx = int(np.searchsorted(d["t"], clock[j], side="left"))
            if sidx < TS_LB + 1 or sidx >= len(d["t"]) or d["t"][sidx] != clock[j]:
                continue
            atr = d["atr"][sidx]
            if not np.isfinite(atr) or atr <= 0:
                continue
            body = abs(d["c"][sidx] - d["o"][sidx])
            if body < TS_BODY * atr:
                continue
            # sum of last TS_LB close-to-close returns in ATR units
            s_sum = 0.0
            ok = True
            for k in range(TS_LB):
                ii = sidx - k
                a = d["atr"][ii]
                if not np.isfinite(a) or a <= 0:
                    ok = False
                    break
                s_sum += (d["c"][ii] - d["c"][ii - 1]) / a
            if not ok:
                continue
            if abs(s_sum) < TS_LO or abs(s_sum) > TS_HI:
                continue

            eidx = int(np.searchsorted(d["t"], ts, side="left"))
            if eidx >= len(d["t"]) or d["t"][eidx] != ts:
                continue
            side = 1 if s_sum > 0 else -1
            entry = float(d["o"][eidx])
            sl = entry - side * TS_SL_ATR * atr
            tp = entry + side * TS_RR * TS_SL_ATR * atr
            open_pos.append(
                {
                    "sym": sym,
                    "side": side,
                    "entry": entry,
                    "sl": sl,
                    "tp": tp,
                    "lots": risk_lots(sym, entry, sl),
                    "bars": 0,
                }
            )
            open_syms.add(sym)
            day_count[(day, sym)] = day_count.get((day, sym), 0) + 1

    flush_open(open_pos, data, closed)
    return summarize(closed)


def write_all(results, receipt, any_surv):
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — USD majority lag-follow + H4 TS-mom band",
                "",
                "Date: 2026-07-15",
                "Lane: single; offline-first; nested critic `cursor-grok-4.5-high-fast`",
                "Parent: AONIA unlock + thin3 ALL_KILL; do not densify AONIA/CORRA/thin3",
                "",
                "## 1 `HYP-FX3-H4-USD-MAJORITY-LAG-FOLLOW-001`",
                "Thesis: when ≥2/3 FX3 print strong same-USD H4 body (≥0.45 ATR) and the",
                "remaining lag is quiet (<0.20 ATR same-sign), delayed USD repricing hits the",
                "lag pair — continuation WITH USD majority (not residual fade).",
                "Frozen: enter next H4 open on lag; SL=1.25 ATR; RR=2.0; hold≤4 H4;",
                "MaxOpen=1; MaxPerDay=1; +$12 a priori.",
                "",
                "## 2 `HYP-FX3-H4-TSMOM-BAND-CONT-001`",
                "Thesis: soft 5-bar H4 TS-momentum in ATR units stays alive inside [1.0, 2.5]",
                "(not dead chop, not climax) with body≥0.35 ATR → continue with sign(S).",
                "Frozen: SL=1.20 ATR; RR=2.5; hold≤10 H4; MaxPerDay=1/symbol; FX3 book; +$12.",
                "",
                "## Model 0 policy",
                "Only if offline PROBE_SURVIVOR. Else withhold. No densify of killed cousins.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup clearance — USD lag + TS-mom greenfield",
                "",
                "| Object | Vs killed / banned shelf |",
                "|---|---|",
                "| USD majority lag-follow | ≠ XS residual fade / XS mom top1 (no factor z; majority+lag gate, cont on laggard). ≠ LNY EUR-lead catchup (no session hour). ≠ thin3/consec3/AONIA/CORRA. |",
                "| H4 TS-mom band cont | ≠ swing ADX/thrust/TD/ROC. ≠ D1 volregime 8d/2close. ≠ H1 bodyATR cont (H4 sum band). ≠ carry/anticarry densify. |",
                "",
                "Backup held (not probed this screen): `HYP-FX3-H1-CLOSELOC-PRESSURE-CONT-001`",
                "(closest densify-rhyme to impulse/body packs).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [
        "# Offline probes — USD majority lag + H4 TS-mom band",
        "",
        f"Receipt `{receipt}`",
        f"Generated `{utc_now()}`",
        "Cost a priori +$12; joint gates N≥80 PF≥1.30 tpw≥2 x1.5≥1.25.",
        "",
    ]
    for r in results:
        lines += [
            f"## {r['hypothesis_id']}",
            f"- **{r['verdict']}** ({', '.join(r['fail_notes']) or 'pass'})",
            f"- N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']}",
            f"- detail={json.dumps(r['detail'])}",
            "",
        ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Closeout — USD lag + TS-mom greenfield",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                *[f"- `{r['hypothesis_id']}` → **{r['verdict']}**" for r in results],
                "Do not densify majority ATR / TS band / RR / hold.",
                "Do not densify AONIA/CORRA/thin3. QFSI parallel only for cost.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — USD lag + TS-mom greenfield",
                f"- `{status}`",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
                    for r in results
                ],
                "- Không densify majority/TS band. Không densify AONIA/CORRA/thin3.",
                "- Best shelf RR2 `194548`. Cost GAP. QFSI song song. Login không headline.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Refresh session VN brief (continue R&D track)
    OUT_SESSION_VN.write_text(
        "\n".join(
            [
                "# VN brief — continue R&D: USD lag + TS-mom (post AONIA kill)",
                "",
                "Thời điểm: 2026-07-15 (continue; không densify AONIA/CORRA/thin3; không idle cost)",
                "",
                "## Invent + de-dup",
                "- `HYP-FX3-H4-USD-MAJORITY-LAG-FOLLOW-001` — USD cascade trên lag pair (≠ XS fade).",
                "- `HYP-FX3-H4-TSMOM-BAND-CONT-001` — H4 TS-mom band continuation (≠ ADX/volregime).",
                "",
                "## Offline joint (+$12)",
                f"- Status: `{status}`",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → **{r['verdict']}**"
                    for r in results
                ],
                f"- Receipt `{receipt}`",
                "",
                "## Quyết định",
                "- Model 0 chỉ nếu survivor; nếu ALL_KILL → withhold.",
                "- Không densify: AONIA / CORRA / thin3 / majority ATR / TS band.",
                "- Best shelf RR2 `194548`. Cost freeze GAP. QFSI parallel only.",
                "- Next EV: next true greenfield ngoài killboard — không densify shelves.",
                "",
                "Login không phải headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_reg(results, receipt):
    with REG.open("a", encoding="utf-8") as f:
        for r in results:
            f.write(
                json.dumps(
                    {
                        "record_type": "candidate",
                        "schema_version": 1,
                        "hypothesis_id": r["hypothesis_id"],
                        "state": "killed"
                        if r["verdict"] != "PROBE_SURVIVOR"
                        else "probe_survivor",
                        "parent_candidate": "post_aonia_thin3_greenfield_20260715",
                        "feature_family": "greenfield_usd_lag_tsmom",
                        "lane": "greenfield_usd_lag_tsmom_20260715",
                        "setup_type": r["setup_type"],
                        "symbol": r["symbol"],
                        "timeframe": r["timeframe"],
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
                            "offline_probe": str(OUT_JSON.relative_to(ROOT)).replace(
                                "\\", "/"
                            ),
                            "receipt_sha256": receipt,
                            "status": r["verdict"],
                            "dedup": str(OUT_DEDUP.relative_to(ROOT)).replace("\\", "/"),
                        },
                        "verdict": r["verdict"],
                        "reason": ",".join(r["fail_notes"]) or "offline_pass",
                        "updated_at": "2026-07-15",
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )


def patch_hot(results, receipt, any_surv):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    block = [
        f"- **GREENFIELD USD-LAG + TSMOM CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  True greenfield outside AONIA/CORRA/thin3 densify (post unlock ALL_KILL).",
        "  Nested critic `cursor-grok-4.5-high-fast`. Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        block.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    block += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_USD_LAG_TSMOM_OFFLINE_PROBES.json`;",
        "  dedup `readouts/20260715_GREENFIELD_USD_LAG_TSMOM_DEDUP_CLEARANCE.md`;",
        "  VN `readouts/20260715_GREENFIELD_USD_LAG_TSMOM_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify majority ATR / TS band / RR / AONIA / CORRA / thin3.",
        "  Next: next true greenfield outside killboard — QFSI parallel only for cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | USD-lag+TSMOM greenfield "
            f"{status.split('__')[0]}; zero Model0 unless survivor; GOAL unmet"
        )
    out = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if not inserted and ln.strip() == "## Active Truth":
            out.extend(block)
            inserted = True
    HOT.write_text("\n".join(out) + "\n", encoding="utf-8")


def main():
    if not mt5.initialize():
        raise SystemExit(mt5.last_error())
    try:
        for s in FX3:
            mt5.symbol_select(s, True)
        fx = {}
        for s in FX3:
            d = load(s, mt5.TIMEFRAME_H4)
            d["atr"] = atr_arr(d["h"], d["l"], d["c"], 14)
            fx[s] = d

        pnls1, det1 = probe_usd_majority_lag(fx)
        m1, h1 = metrics(pnls1), haircuts(pnls1)
        v1, n1 = joint_verdict(m1, h1)

        pnls2, det2 = probe_tsmom_band(fx)
        m2, h2 = metrics(pnls2), haircuts(pnls2)
        v2, n2 = joint_verdict(m2, h2)

        results = [
            {
                "hypothesis_id": "HYP-FX3-H4-USD-MAJORITY-LAG-FOLLOW-001",
                "setup_type": (
                    "≥2 FX3 strong same-USD H4 (≥0.45ATR), lag <0.20 → follow USD; "
                    "SL1.25 RR2 ≤4"
                ),
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": "H4",
                "metrics": m1,
                "haircuts": h1,
                "verdict": v1,
                "fail_notes": n1,
                "detail": det1,
            },
            {
                "hypothesis_id": "HYP-FX3-H4-TSMOM-BAND-CONT-001",
                "setup_type": (
                    "5H4 TS sum ATR-units ∈[1.0,2.5] + body≥0.35ATR → cont; "
                    "SL1.2 RR2.5 ≤10"
                ),
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": "H4",
                "metrics": m2,
                "haircuts": h2,
                "verdict": v2,
                "fail_notes": n2,
                "detail": det2,
            },
        ]
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema": "greenfield_usd_lag_tsmom_offline_probes.v1",
            "generated_at_utc": utc_now(),
            "base_cost_usd": BASE_COST,
            "window": "2021.01.01-2025.12.31",
            "dedup_note": (
                "≠ AONIA/CORRA/thin3 densify; ≠ XS residual fade; ≠ swing ADX; "
                "≠ D1 volregime; ≠ carry/anticarry"
            ),
            "results": results,
            "any_survivor": any_surv,
            "model0_authorized": any_surv,
            "receipt_sha256": None,
        }
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        write_all(results, receipt, any_surv)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv)
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "any_survivor": any_surv,
                    "model0_authorized": any_surv,
                    "results": [
                        {
                            "id": r["hypothesis_id"],
                            "verdict": r["verdict"],
                            **r["metrics"],
                            "x15": r["haircuts"]["x1_5"]["pf"],
                            "notes": r["fail_notes"],
                            "detail": r["detail"],
                        }
                        for r in results
                    ],
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
