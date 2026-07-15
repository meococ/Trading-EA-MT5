#!/usr/bin/env python3
"""Second greenfield pack after calendar/liq ALL_KILL + CAD CORRA cadence kill.

Outside shelves: ≠ carry densify, ≠ calendar TOM/gap densify, ≠ D1/swing/entry/exit,
≠ FRED/LNY/XS, ≠ 6J/USBILL, ≠ CORRA bp densify.

A priori (≥2), +$12:
  1) HYP-FX3-H4-CONSEC3-IMPULSE-FADE-001
  2) HYP-XAUUSD-H1-USD-BETA-RESID-FADE-001
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

OUT_JSON = PRE / "20260715_GREENFIELD_IMPULSE_METAL_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_GREENFIELD_IMPULSE_METAL_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_GREENFIELD_IMPULSE_METAL_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_GREENFIELD_IMPULSE_METAL_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_GREENFIELD_IMPULSE_METAL_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_GREENFIELD_IMPULSE_METAL_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
FX3 = ("EURUSD", "GBPUSD", "USDJPY")

CONSEC = 3
IMPULSE_ATR = 1.2
FADE_SL = 1.2
FADE_RR = 1.5
FADE_HOLD = 4
FADE_MAX_OPEN = 2

BETA_LB = 60
Z_ENTRY = 1.5
METAL_SL_ATR = 1.4
METAL_RR = 1.8
METAL_HOLD = 10


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
        return 0.01 if "XAU" in symbol or "JPY" in symbol else 0.0001
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


def sim_path(h, l, c, i0, side, entry, sl, tp, max_hold):
    exit_px, reason = c[min(i0 + max_hold - 1, len(c) - 1)], "time"
    end = min(i0 + max_hold, len(c))
    for k in range(i0, end):
        if side > 0:
            if l[k] <= sl:
                return sl, "sl", k
            if h[k] >= tp:
                return tp, "tp", k
        else:
            if h[k] >= sl:
                return sl, "sl", k
            if l[k] <= tp:
                return tp, "tp", k
        exit_px, reason = c[k], "time"
    return exit_px, reason, end - 1


def probe_impulse_fade(data):
    closed = []
    # clock = EURUSD H4
    clock = data["EURUSD"]["t"]
    open_pos = []
    for i, ts in enumerate(clock):
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        # exits
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
            if exit_px is None and pos["bars"] >= FADE_HOLD:
                exit_px, reason = d["c"][idx], "time"
            if exit_px is not None:
                closed.append({"pnl": cash_pnl(sym, pos["side"], pos["entry"], exit_px, pos["lots"]), "reason": reason, "sym": sym})
            else:
                still.append(pos)
        open_pos = still

        if dt.weekday() >= 5 or dt.hour < 8:
            continue
        if len(open_pos) >= FADE_MAX_OPEN:
            continue
        open_syms = {p["sym"] for p in open_pos}
        for sym in FX3:
            if sym in open_syms or len(open_pos) >= FADE_MAX_OPEN:
                continue
            d = data[sym]
            idx = int(np.searchsorted(d["t"], ts, side="left"))
            if idx < CONSEC + 20 or d["t"][idx] != ts:
                continue
            atr = d["atr"][idx]
            if not np.isfinite(atr) or atr <= 0:
                continue
            # signal on closed bars idx-CONSEC .. idx-1; enter at open idx
            rets = d["c"][idx - CONSEC : idx] - d["o"][idx - CONSEC : idx]
            if not (np.all(rets > 0) or np.all(rets < 0)):
                continue
            impulse = float(np.sum(rets))
            if abs(impulse) < IMPULSE_ATR * atr:
                continue
            side = -1 if impulse > 0 else 1
            entry = float(d["o"][idx])
            sl = entry - side * FADE_SL * atr
            tp = entry + side * FADE_RR * FADE_SL * atr
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


def probe_metal_resid(xau, eurusd, usdjpy):
    # Align by timestamp intersection H1
    te, tx, tj = eurusd["t"], xau["t"], usdjpy["t"]
    # map time->idx
    me = {int(t): i for i, t in enumerate(te)}
    mj = {int(t): i for i, t in enumerate(tj)}
    common = [int(t) for t in tx if int(t) in me and int(t) in mj]
    if len(common) < BETA_LB + 50:
        return [], {"error": "align_fail", "n": len(common)}

    # log returns
    def lr(arr, idx):
        return math.log(arr[idx] / arr[idx - 1]) if arr[idx - 1] > 0 else 0.0

    x_idx = {int(t): i for i, t in enumerate(tx)}
    r_x, r_u = [], []
    times = []
    for t in common:
        ix, ie, ij = x_idx[t], me[t], mj[t]
        if ix < 1 or ie < 1 or ij < 1:
            continue
        # USD factor proxy: -eurusd_ret + usdjpy_ret (USD up)
        usd = -lr(eurusd["c"], ie) + lr(usdjpy["c"], ij)
        r_x.append(lr(xau["c"], ix))
        r_u.append(usd)
        times.append(t)

    r_x = np.array(r_x)
    r_u = np.array(r_u)
    atr = atr_arr(xau["h"], xau["l"], xau["c"], 14)
    closed = []
    pos = None
    for i in range(BETA_LB + 1, len(times)):
        t = times[i]
        ix = x_idx[t]
        dt = datetime.fromtimestamp(t, tz=timezone.utc)
        # rolling OLS beta
        y = r_x[i - BETA_LB : i]
        x = r_u[i - BETA_LB : i]
        x = x - x.mean()
        y0 = y - y.mean()
        den = float(np.dot(x, x))
        if den <= 1e-12:
            continue
        beta = float(np.dot(x, y0) / den)
        resid = y0 - beta * x
        mu, sd = float(resid.mean()), float(resid.std(ddof=1))
        if sd <= 1e-12:
            continue
        z = (resid[-1] - mu) / sd

        if pos is not None:
            exit_px, reason, _ = sim_path(
                xau["h"], xau["l"], xau["c"], ix, pos["side"], pos["entry"], pos["sl"], pos["tp"], METAL_HOLD - pos["bars"]
            )
            # simpler bar-by-bar
            exit_px = None
            reason = None
            if pos["side"] > 0:
                if xau["l"][ix] <= pos["sl"]:
                    exit_px, reason = pos["sl"], "sl"
                elif xau["h"][ix] >= pos["tp"]:
                    exit_px, reason = pos["tp"], "tp"
            else:
                if xau["h"][ix] >= pos["sl"]:
                    exit_px, reason = pos["sl"], "sl"
                elif xau["l"][ix] <= pos["tp"]:
                    exit_px, reason = pos["tp"], "tp"
            pos["bars"] += 1
            if exit_px is None and pos["bars"] >= METAL_HOLD:
                exit_px, reason = xau["c"][ix], "time"
            # z mean-revert exit
            if exit_px is None and abs(z) < 0.25:
                exit_px, reason = xau["c"][ix], "zflat"
            if exit_px is not None:
                closed.append({"pnl": cash_pnl("XAUUSD", pos["side"], pos["entry"], exit_px, pos["lots"]), "reason": reason})
                pos = None

        if pos is not None:
            continue
        if dt.weekday() >= 5:
            continue
        if abs(z) < Z_ENTRY:
            continue
        if not np.isfinite(atr[ix]) or atr[ix] <= 0:
            continue
        # fade residual: z>0 gold rich vs USD → short
        side = -1 if z > 0 else 1
        entry = float(xau["o"][ix]) if ix + 0 == ix else float(xau["c"][ix])
        # enter next bar open to avoid same-bar lookahead on z computed including current close
        if ix + 1 >= len(xau["c"]):
            continue
        entry = float(xau["o"][ix + 1])
        a = atr[ix]
        sl = entry - side * METAL_SL_ATR * a
        tp = entry + side * METAL_RR * METAL_SL_ATR * a
        pos = {
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "lots": risk_lots("XAUUSD", entry, sl),
            "bars": 0,
            "entry_ix": ix + 1,
        }

    if pos is not None:
        closed.append(
            {
                "pnl": cash_pnl("XAUUSD", pos["side"], pos["entry"], float(xau["c"][-1]), pos["lots"]),
                "reason": "eod",
            }
        )
    pnls = [x["pnl"] for x in closed]
    detail = {"by_reason": {}}
    for x in closed:
        detail["by_reason"][x["reason"]] = detail["by_reason"].get(x["reason"], 0) + 1
    return pnls, detail


def write_all(results, receipt, any_surv):
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — Greenfield impulse-fade + XAU USD-beta residual",
                "",
                "## 1 `HYP-FX3-H4-CONSEC3-IMPULSE-FADE-001`",
                "3 same-dir H4 bodies, |sum|≥1.2 ATR → fade next H4 open; SL1.2 RR1.5 hold≤4.",
                "",
                "## 2 `HYP-XAUUSD-H1-USD-BETA-RESID-FADE-001`",
                "Rolling 60 H1 OLS residual of XAU vs (−EURUSD+USDJPY) USD factor; |z|≥1.5 fade.",
                "",
                "## ≠ shelves",
                "≠ calendar TOM/gap; ≠ carry/CORRA densify; ≠ XS residual FX book; ≠ LNY; ≠ D1 breakout.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — impulse/metal greenfield",
                "",
                "| Object | Clearance |",
                "|---|---|",
                "| consec3 impulse fade | ≠ swing ADX/thrust densify; ≠ engul/outside; ≠ NR7 |",
                "| XAU USD-beta resid | ≠ XS FX residual book; ≠ FRED displace; metal sleeve |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [f"# Offline — impulse/metal\n\nReceipt `{receipt}`\n"]
    for r in results:
        lines.append(
            f"## {r['hypothesis_id']}\n\n"
            f"- **{r['verdict']}** ({', '.join(r['fail_notes']) or 'pass'})\n"
            f"- N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']}\n"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Closeout — impulse/metal greenfield",
                f"Status: `{status}`",
                f"Receipt: `{receipt}`",
                *[f"- `{r['hypothesis_id']}` → **{r['verdict']}**" for r in results],
                "Do not densify consec/z/ATR. Next: Owner cost/tick or RBA CSV; not densify shelves.",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — impulse/metal greenfield",
                f"- `{status}`",
                *[
                    f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                    f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}"
                    for r in results
                ],
                "- Không densify consec/z. Best shelf RR2 `194548`. Login không headline.",
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
                        "state": "killed" if r["verdict"] != "PROBE_SURVIVOR" else "probe_survivor",
                        "parent_candidate": "post_calendar_corra_greenfield_20260715",
                        "feature_family": "greenfield_impulse_metal",
                        "lane": "greenfield_impulse_metal_20260715",
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


def patch_hot(results, receipt, any_surv):
    status = "PROBE_SURVIVOR_PRESENT" if any_surv else "OFFLINE_ALL_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    block = [
        f"- **GREENFIELD IMPULSE/METAL CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  Post calendar/liq + CAD CORRA cadence kill; true greenfield pack.",
        "  Offline joint screen:",
    ]
    for i, r in enumerate(results, 1):
        block.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
            f"x1.5={r['haircuts']['x1_5']['pf']})."
        )
    block += [
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_GREENFIELD_IMPULSE_METAL_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_GREENFIELD_IMPULSE_METAL_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify consec / residual z / ATR.",
        "  Next: Owner-led cost/tick or RBA CSV drop — not densify kill shelves.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | Impulse/metal greenfield "
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
        for s in list(FX3) + ["XAUUSD"]:
            mt5.symbol_select(s, True)
        fx = {}
        for s in FX3:
            d = load(s, mt5.TIMEFRAME_H4)
            d["atr"] = atr_arr(d["h"], d["l"], d["c"], 14)
            fx[s] = d
        pnls1, det1 = probe_impulse_fade(fx)
        m1, h1 = metrics(pnls1), haircuts(pnls1)
        v1, n1 = joint_verdict(m1, h1)
        results = [
            {
                "hypothesis_id": "HYP-FX3-H4-CONSEC3-IMPULSE-FADE-001",
                "setup_type": "3 consec H4 impulse ≥1.2ATR → fade; SL1.2 RR1.5 ≤4",
                "symbol": "EURUSD,GBPUSD,USDJPY",
                "timeframe": "H4",
                "metrics": m1,
                "haircuts": h1,
                "verdict": v1,
                "fail_notes": n1,
                "detail": det1,
            }
        ]
        xau = load("XAUUSD", mt5.TIMEFRAME_H1)
        eu = load("EURUSD", mt5.TIMEFRAME_H1)
        uj = load("USDJPY", mt5.TIMEFRAME_H1)
        pnls2, det2 = probe_metal_resid(xau, eu, uj)
        m2, h2 = metrics(pnls2), haircuts(pnls2)
        v2, n2 = joint_verdict(m2, h2)
        results.append(
            {
                "hypothesis_id": "HYP-XAUUSD-H1-USD-BETA-RESID-FADE-001",
                "setup_type": "XAU vs USD-factor residual |z|≥1.5 fade; SL1.4 RR1.8 ≤10",
                "symbol": "XAUUSD",
                "timeframe": "H1",
                "metrics": m2,
                "haircuts": h2,
                "verdict": v2,
                "fail_notes": n2,
                "detail": det2,
            }
        )
        any_surv = any(r["verdict"] == "PROBE_SURVIVOR" for r in results)
        payload = {
            "schema": "greenfield_impulse_metal_offline_probes.v1",
            "generated_at_utc": utc_now(),
            "base_cost_usd": BASE_COST,
            "results": results,
            "any_survivor": any_surv,
            "model0_authorized": any_surv,
            "receipt_sha256": None,
        }
        OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt = sha256_bytes(OUT_JSON.read_bytes())
        payload["receipt_sha256"] = receipt
        OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_all(results, receipt, any_surv)
        append_reg(results, receipt)
        patch_hot(results, receipt, any_surv)
        print(json.dumps({"receipt": receipt, "results": [
            {"id": r["hypothesis_id"], "verdict": r["verdict"], **r["metrics"], "x15": r["haircuts"]["x1_5"]["pf"]}
            for r in results
        ]}, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
