#!/usr/bin/env python3
"""Independent greenfield outside just-killed densify list.

≠ CORRA bp / TOM / weekend gap / consec3 impulse / XAU residual-z /
anticarry / carry flush / D1 volregime / swing / entry-state / FRED / LNY / XS / RR2.

A priori:
  HYP-FX3-H1-THIN3-JUMP-FADE-001
  3 thin H1 ranges then jump bar → fade jump body; enter next open.

Model 0 only if PROBE_SURVIVOR. +$12.
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

OUT_JSON = PRE / "20260715_GREENFIELD_THIN3_JUMP_FADE_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_THIN3_JUMP_FADE_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_THIN3_JUMP_FADE_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_THIN3_JUMP_FADE_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_THIN3_JUMP_FADE_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_THIN3_JUMP_FADE_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

THIN_ATR = 0.40
JUMP_RANGE_ATR = 1.25
JUMP_BODY_ATR = 0.50
SL_PAD_ATR = 0.05
RR = 1.5
MAX_HOLD = 6
MAX_OPEN = 2


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


def probe_thin3_jump(data):
    closed = []
    clock = data["EURUSD"]["t"]
    open_pos = []
    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
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
            if exit_px is None and pos["bars"] >= MAX_HOLD:
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
        open_pos = still

        if dt.weekday() >= 5:
            continue
        if len(open_pos) >= MAX_OPEN:
            continue
        open_syms = {p["sym"] for p in open_pos}

        for sym in FX3:
            if sym in open_syms or len(open_pos) >= MAX_OPEN:
                continue
            d = data[sym]
            # jump bar closed at idx-1; thin bars idx-4..idx-2; enter at open idx
            idx = int(np.searchsorted(d["t"], ts, side="left"))
            if idx < 20 or d["t"][idx] != ts:
                continue
            j = idx - 1
            if j < 4:
                continue
            atr = d["atr"][j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            thin_ok = True
            for k in range(j - 3, j):
                rng = d["h"][k] - d["l"][k]
                if rng >= THIN_ATR * atr:
                    thin_ok = False
                    break
            if not thin_ok:
                continue
            j_rng = d["h"][j] - d["l"][j]
            j_body = abs(d["c"][j] - d["o"][j])
            if j_rng < JUMP_RANGE_ATR * atr or j_body < JUMP_BODY_ATR * atr:
                continue
            body_dir = d["c"][j] - d["o"][j]
            if body_dir == 0:
                continue
            side = -1 if body_dir > 0 else 1
            entry = float(d["o"][idx])
            if side < 0:
                sl = float(d["h"][j]) + SL_PAD_ATR * atr
            else:
                sl = float(d["l"][j]) - SL_PAD_ATR * atr
            risk = abs(entry - sl)
            if risk <= 0:
                continue
            tp = entry + side * RR * risk
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

    for pos in open_pos:
        d = data[pos["sym"]]
        closed.append(
            {
                "pnl": cash_pnl(pos["sym"], pos["side"], pos["entry"], float(d["c"][-1]), pos["lots"]),
                "reason": "eod",
                "sym": pos["sym"],
            }
        )
    pnls = [x["pnl"] for x in closed]
    detail = {"by_reason": {}, "by_sym": {}}
    for x in closed:
        detail["by_reason"][x["reason"]] = detail["by_reason"].get(x["reason"], 0) + 1
        detail["by_sym"][x["sym"]] = detail["by_sym"].get(x["sym"], 0) + 1
    return pnls, detail


def write_all(r, receipt):
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Thin3 → jump fade (OHLC microstructure proxy)",
                "",
                "## `HYP-FX3-H1-THIN3-JUMP-FADE-001`",
                "3 H1 bars with range <0.40 ATR, then jump (range≥1.25 ATR, body≥0.50 ATR)",
                "→ fade jump body at next open; SL beyond jump extreme+0.05ATR; RR=1.5; hold≤6.",
                "",
                "## ≠ shelves",
                "≠ consec3 impulse fade; ≠ weekend gap; ≠ TOM; ≠ LNY coil; ≠ XS/XAU z;",
                "≠ CORRA/AONIA densify; ≠ carry/anticarry; ≠ D1/swing/entry-state/RR2/FRED.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — thin3 jump fade",
                "",
                "| Object | Clearance |",
                "|---|---|",
                "| thin3→jump fade | Trigger=thin range then jump; ≠ consec direction impulse |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline — thin3 jump fade",
                "",
                f"Receipt `{receipt}`",
                f"## {r['hypothesis_id']}",
                f"- **{r['verdict']}** ({', '.join(r['fail_notes']) or 'pass'})",
                f"- N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
                f"x1.5={r['haircuts']['x1_5']['pf']}",
                f"- detail={json.dumps(r['detail'])}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    status = (
        "PROBE_SURVIVOR_PRESENT"
        if r["verdict"] == "PROBE_SURVIVOR"
        else "OFFLINE_KILL__NO_MODEL0"
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Closeout — thin3 jump fade greenfield",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                f"- `{r['hypothesis_id']}` → **{r['verdict']}**",
                "Do not densify thin/jump ATR/RR. Next: research-grade cost or next greenfield.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — thin3 jump fade",
                f"- `{status}`",
                f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}",
                "- Không densify thin/jump. Best shelf RR2 `194548`. Login không headline.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_reg(r, receipt):
    with REG.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "record_type": "candidate",
                    "schema_version": 1,
                    "hypothesis_id": r["hypothesis_id"],
                    "state": "killed" if r["verdict"] != "PROBE_SURVIVOR" else "probe_survivor",
                    "parent_candidate": "post_aonia_unlock_greenfield_20260715",
                    "feature_family": "greenfield_thin3_jump_fade",
                    "lane": "greenfield_thin3_jump_20260715",
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
                        "offline_probe": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                        "receipt_sha256": receipt,
                        "status": r["verdict"],
                    },
                    "verdict": r["verdict"],
                    "reason": ",".join(r["fail_notes"]) or "offline_pass",
                    "updated_at": "2026-07-15",
                },
                ensure_ascii=True,
            )
            + "\n"
        )


def patch_hot(r, receipt):
    status = (
        "PROBE_SURVIVOR_PRESENT"
        if r["verdict"] == "PROBE_SURVIVOR"
        else "OFFLINE_KILL__NO_MODEL0"
    )
    stamp = datetime.now().strftime("%H:%M")
    block = [
        f"- **GREENFIELD THIN3 JUMP FADE CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Independent greenfield outside densify shelves (post AONIA unlock).",
        "  Offline joint screen:",
        f"  1. `{r['hypothesis_id']}` → **{r['verdict']}** "
        f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
        f"x1.5={r['haircuts']['x1_5']['pf']}).",
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_THIN3_JUMP_FADE_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_GREENFIELD_THIN3_JUMP_FADE_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify thin / jump ATR / RR.",
        "  Next: research-grade cost/tick or next true greenfield — not densify shelves.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Thin3 jump greenfield "
            f"{status.split('__')[0]}; Real on; GOAL unmet"
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
            d = load(s, mt5.TIMEFRAME_H1)
            d["atr"] = atr_arr(d["h"], d["l"], d["c"], 14)
            fx[s] = d
        pnls, detail = probe_thin3_jump(fx)
        m, hc = metrics(pnls), haircuts(pnls)
        v, notes = joint_verdict(m, hc)
        r = {
            "hypothesis_id": "HYP-FX3-H1-THIN3-JUMP-FADE-001",
            "setup_type": "3 thin H1 then jump ≥1.25ATR → fade; SL pad0.05 RR1.5 ≤6",
            "symbol": "EURUSD,GBPUSD,USDJPY",
            "timeframe": "H1",
            "metrics": m,
            "haircuts": hc,
            "verdict": v,
            "fail_notes": notes,
            "detail": detail,
        }
        payload = {
            "schema": "greenfield_thin3_jump_fade_offline_probes.v1",
            "generated_at_utc": utc_now(),
            "base_cost_usd": BASE_COST,
            "results": [r],
            "any_survivor": v == "PROBE_SURVIVOR",
            "model0_authorized": v == "PROBE_SURVIVOR",
            "receipt_sha256": None,
        }
        OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        write_all(r, receipt)
        append_reg(r, receipt)
        patch_hot(r, receipt)
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "result": {
                        "id": r["hypothesis_id"],
                        "verdict": v,
                        **m,
                        "x15": hc["x1_5"]["pf"],
                        "notes": notes,
                        "detail": detail,
                    },
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
