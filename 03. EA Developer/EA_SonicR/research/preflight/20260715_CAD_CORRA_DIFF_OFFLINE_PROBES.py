#!/usr/bin/env python3
"""ONE new carry/differential child on newly frozen BoC CORRA (alt-source).

Panel: CAD CORRA (BoC AVG.INTWO) + USD from carry_rates_d1; +1bd lag.
NOT densify of Mon→Thu harvest / flush-MR / anticarry×vol / V8 weekly-daily-5bp-vol.

A priori:
  1) HYP-USDCAD-CORRA-USD-DIFF-EXPAND-H4-001

Model 0 only if PROBE_SURVIVOR. A priori +$12.
"""
from __future__ import annotations

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
EXO = PRE / "v8_exogenous"
RATES_USD = ROOT / "03. EA Developer" / "EA_CarryPublicRates" / "carry_rates_d1.csv"
CORRA = EXO / "raw" / "g10_overnight" / "boc_corra_avg_intwo.csv"
PANEL = EXO / "panels" / "cad_usd_corra_overnight_d1_v1.csv"
CONTRACT = EXO / "contracts" / "20260715_CAD_USD_CORRA_AVAILABLE_AT_UTC_V1.json"
MAN = EXO / "manifests" / "20260715_CAD_USD_CORRA_PANEL_V1.json"

OUT_JSON = PRE / "20260715_CAD_CORRA_DIFF_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_CAD_CORRA_DIFF_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_CAD_CORRA_DIFF_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_CAD_CORRA_DIFF_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_CAD_CORRA_DIFF_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_CAD_CORRA_DIFF_VN_ACTION_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
SYMBOL = "USDCAD"

DIFF_BP_MIN = 5.0  # |Δ(CORRA-USD)| in basis points
SL_ATR = 1.5
RR = 2.0
MAX_HOLD = 10
LAG_BD = 1


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


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
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0:
        notes.append("cadence_fail")
    x15 = hc["x1_5"]["pf"]
    if x15 is None or x15 < 1.25:
        notes.append("stress_fail")
    if notes:
        return "KILLED_AT_OFFLINE_PROBE", notes
    return "PROBE_SURVIVOR", []


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


def parse_boc_corra(path: Path) -> dict[date, float]:
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[date, float] = {}
    for ln in text.splitlines():
        ln = ln.strip().strip('"')
        if not ln or not ln[0].isdigit():
            continue
        parts = [p.strip().strip('"') for p in ln.split(",")]
        if len(parts) < 2:
            continue
        try:
            out[date.fromisoformat(parts[0])] = float(parts[1])
        except ValueError:
            continue
    return out


def parse_usd(path: Path) -> dict[date, float]:
    out: dict[date, float] = {}
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                out[date.fromisoformat(row["date"])] = float(row["usd"])
            except (KeyError, ValueError):
                continue
    return out


def business_lag_map(series: dict[date, float], lag: int) -> dict[date, float]:
    """available-at date -> value known after `lag` business days from observation date."""
    keys = sorted(series)
    # build business calendar from series keys union forward
    avail: dict[date, float] = {}
    for i, d in enumerate(keys):
        # find date lag BD later
        j = i
        bd = 0
        cur = d
        while bd < lag:
            cur = cur + timedelta(days=1)
            if cur.weekday() < 5:
                bd += 1
            if bd > 20:
                break
        avail[cur] = series[d]
    return avail


def build_panel() -> tuple[dict[date, dict[str, float]], dict]:
    corra = parse_boc_corra(CORRA)
    usd = parse_usd(RATES_USD)
    if len(corra) < 500:
        raise SystemExit(f"CORRA too short: {len(corra)}")
    # raw aligned
    days = sorted(set(corra) & set(usd))
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    with PANEL.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "cad_corra", "usd", "diff_pp"])
        for d in days:
            diff = corra[d] - usd[d]
            w.writerow([d.isoformat(), f"{corra[d]:.6f}", f"{usd[d]:.6f}", f"{diff:.6f}"])
    # lagged available-at
    corra_a = business_lag_map(corra, LAG_BD)
    usd_a = business_lag_map(usd, LAG_BD)
    adays = sorted(set(corra_a) & set(usd_a))
    panel_a: dict[date, dict[str, float]] = {}
    prev_diff: float | None = None
    for d in adays:
        diff = corra_a[d] - usd_a[d]
        d_bp = None if prev_diff is None else (diff - prev_diff) * 100.0
        panel_a[d] = {"cad": corra_a[d], "usd": usd_a[d], "diff": diff, "d_diff_bp": d_bp}
        prev_diff = diff

    meta = {
        "schema": "cad_usd_corra_available_at_utc.v1",
        "generated_at_utc": utc_now(),
        "status": "PANEL_READY",
        "corra_rows_raw": len(corra),
        "usd_rows_raw": len(usd),
        "panel_rows": len(days),
        "available_at_rows": len(panel_a),
        "lag_business_days": LAG_BD,
        "panel_path": str(PANEL.relative_to(ROOT)).replace("\\", "/"),
        "panel_sha256": sha256_file(PANEL),
        "corra_sha256": sha256_file(CORRA),
        "usd_source": str(RATES_USD.relative_to(ROOT)).replace("\\", "/"),
        "authority": (
            "BoC Valet AVG.INTWO = CORRA overnight (daily). USD = public carry panel "
            "short-rate proxy. +1bd lag for available-at. Not RBA/AONIA; AUD still blocked."
        ),
    }
    CONTRACT.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    man = {
        "schema": "cad_usd_corra_panel.v1",
        "generated_at_utc": utc_now(),
        "contract_path": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "contract_sha256": sha256_file(CONTRACT),
        **{k: meta[k] for k in ("status", "panel_path", "panel_sha256", "panel_rows")},
    }
    MAN.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    return panel_a, meta


def pip_size(symbol: str) -> float:
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.0001
    return info.point * (10 if info.digits in (3, 5) else 1)


def cash_pnl(symbol: str, side: int, entry: float, exit_px: float, lots: float) -> float:
    info = mt5.symbol_info(symbol)
    tick_val = float(info.trade_tick_value) if info else 1.0
    tick_size = float(info.trade_tick_size) if info else pip_size(symbol)
    if tick_size <= 0:
        tick_size = pip_size(symbol)
    move = (exit_px - entry) * side
    return move / tick_size * tick_val * lots


def risk_lots(symbol: str, entry: float, sl: float) -> float:
    info = mt5.symbol_info(symbol)
    risk = DEPOSIT * RISK_FRAC
    dist = abs(entry - sl)
    if dist <= 0 or info is None:
        return 0.01
    tick_val = float(info.trade_tick_value) or 1.0
    tick_size = float(info.trade_tick_size) or pip_size(symbol)
    loss_per_lot = dist / tick_size * tick_val
    if loss_per_lot <= 0:
        return 0.01
    lots = max(0.01, math.floor(risk / loss_per_lot * 100) / 100)
    return min(lots, 5.0)


def probe(panel: dict[date, dict[str, float]]) -> tuple[list[float], dict]:
    rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_H4, FROM, TO)
    if rates is None or len(rates) < 200:
        raise RuntimeError(f"USDCAD H4 fail: {mt5.last_error()}")
    t = rates["time"].astype(np.int64)
    o = rates["open"].astype(float)
    h = rates["high"].astype(float)
    l = rates["low"].astype(float)
    c = rates["close"].astype(float)
    atr = atr_arr(h, l, c, 14)

    closed: list[dict] = []
    pos = None
    last_event_day: date | None = None

    for i in range(20, len(t)):
        dt = datetime.fromtimestamp(int(t[i]), tz=timezone.utc)
        d = dt.date()
        # manage open
        if pos is not None:
            exit_px = None
            reason = None
            if pos["side"] > 0:
                if l[i] <= pos["sl"]:
                    exit_px, reason = pos["sl"], "sl"
                elif h[i] >= pos["tp"]:
                    exit_px, reason = pos["tp"], "tp"
            else:
                if h[i] >= pos["sl"]:
                    exit_px, reason = pos["sl"], "sl"
                elif l[i] <= pos["tp"]:
                    exit_px, reason = pos["tp"], "tp"
            pos["bars"] += 1
            if exit_px is None and pos["bars"] >= MAX_HOLD:
                exit_px, reason = c[i], "time"
            if exit_px is not None:
                pnl = cash_pnl(SYMBOL, pos["side"], pos["entry"], exit_px, pos["lots"])
                closed.append({"pnl": pnl, "reason": reason, "entry_t": pos["entry_t"]})
                pos = None

        if pos is not None:
            continue
        if d.weekday() >= 5:
            continue
        if dt.hour < 8:
            continue
        row = panel.get(d)
        if not row or row["d_diff_bp"] is None:
            continue
        d_bp = row["d_diff_bp"]
        if abs(d_bp) < DIFF_BP_MIN:
            continue
        if last_event_day == d:
            continue
        # CAD-USD diff up → CAD funding richer → SHORT USDCAD
        side = -1 if d_bp > 0 else 1
        if not np.isfinite(atr[i]) or atr[i] <= 0:
            continue
        entry = float(o[i])
        sl = entry - side * SL_ATR * atr[i]
        tp = entry + side * RR * SL_ATR * atr[i]
        lots = risk_lots(SYMBOL, entry, sl)
        pos = {
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "lots": lots,
            "entry_t": int(t[i]),
            "bars": 0,
        }
        last_event_day = d

    if pos is not None:
        pnl = cash_pnl(SYMBOL, pos["side"], pos["entry"], float(c[-1]), pos["lots"])
        closed.append({"pnl": pnl, "reason": "eod", "entry_t": pos["entry_t"]})

    pnls = [x["pnl"] for x in closed]
    detail = {"by_reason": {}, "events": len(closed)}
    for x in closed:
        detail["by_reason"][x["reason"]] = detail["by_reason"].get(x["reason"], 0) + 1
    return pnls, detail


def write_docs(r: dict, receipt: str, panel_meta: dict) -> None:
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — CAD CORRA vs USD differential expand (USDCAD)",
                "",
                "Date: 2026-07-15",
                "Data: BoC CORRA AVG.INTWO alt-source freeze + G3 USD; +1bd lag.",
                "",
                "## Design",
                "`HYP-USDCAD-CORRA-USD-DIFF-EXPAND-H4-001`",
                f"|Δ(CORRA−USD)|≥{DIFF_BP_MIN}bp available-at → trade USDCAD with CAD richness;",
                f"H4≥08; SL {SL_ATR}×ATR; RR={RR}; hold≤{MAX_HOLD}.",
                "",
                "## ≠ kill shelf",
                "≠ FX3 Mon→Thu fundproxy; ≠ flush-MR; ≠ anticarry×vol;",
                "≠ V8 weekly/daily/5bp/vol on G3; ≠ USBILL; ≠ WTI-USDCAD commodity.",
                "",
                f"Panel SHA: `{panel_meta.get('panel_sha256')}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — CAD CORRA differential",
                "",
                "| Object | Vs banned |",
                "|---|---|",
                "| CORRA−USD expand USDCAD | New CORRA series; event Δdiff ≠ multi-day harvest/flush/anticarry |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probe — CAD CORRA differential",
                "",
                f"Receipt: `{receipt}`",
                f"Verdict: **{r['verdict']}** ({', '.join(r['fail_notes']) or 'pass'})",
                f"N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']}",
                f"x1.5={r['haircuts']['x1_5']['pf']} x2={r['haircuts']['x2']['pf']}",
                f"detail={json.dumps(r['detail'])}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    status = "PROBE_SURVIVOR_PRESENT" if r["verdict"] == "PROBE_SURVIVOR" else "OFFLINE_KILL__NO_MODEL0"
    next_line = (
        "Model 0 prereg for survivor."
        if r["verdict"] == "PROBE_SURVIVOR"
        else (
            "AUD/RBA still blocked (403/BIS500); do not densify CORRA bp/hold. "
            "Next true greenfield outside calendar densify."
        )
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Closeout — CAD CORRA differential",
                "",
                f"Status: `{status}`",
                f"`{r['hypothesis_id']}` → **{r['verdict']}**",
                f"Receipt `{receipt}`",
                f"Next: {next_line}",
                "Best shelf RR2 `194548`. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_VN.write_text(
        "\n".join(
            [
                "# VN brief — CAD CORRA differential",
                "",
                f"- Panel CAD+USD CORRA: READY (AUD vẫn BLOCKED).",
                f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}",
                f"- Next: {next_line}",
                "- Best shelf RR2 `194548`. Login không headline.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_reg(r: dict, receipt: str) -> None:
    row = {
        "record_type": "candidate",
        "schema_version": 1,
        "hypothesis_id": r["hypothesis_id"],
        "state": "killed" if r["verdict"] != "PROBE_SURVIVOR" else "probe_survivor",
        "parent_candidate": "g10_altsource_cad_corra_20260715",
        "feature_family": "cad_corra_usd_diff_expand",
        "lane": "g10_altsource_cad_20260715",
        "setup_type": r["setup_type"],
        "symbol": SYMBOL,
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
        "reason": ",".join(r["fail_notes"]) or "offline_pass",
        "updated_at": "2026-07-15",
    }
    with REG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=True) + "\n")


def patch_hot(r: dict, receipt: str, panel_meta: dict) -> None:
    status = "PROBE_SURVIVOR_PRESENT" if r["verdict"] == "PROBE_SURVIVOR" else "OFFLINE_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    block = [
        f"- **CAD CORRA DIFF CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  G10 alt-source: BoC CORRA `AVG.INTWO` frozen; AUD/RBA still 403/BIS500;",
        f"  CAD+USD panel READY rows={panel_meta.get('panel_rows')} SHA `{panel_meta.get('panel_sha256','')[:16]}…`.",
        "  ONE new differential child (≠ Mon→Thu/flush/anticarry densify):",
        f"  1. `{r['hypothesis_id']}` → **{r['verdict']}** "
        f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
        f"x1.5={r['haircuts']['x1_5']['pf']}).",
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_CAD_CORRA_DIFF_OFFLINE_PROBES.json`;",
        "  acquire `manifests/20260715_G10_OVERNIGHT_ALTSOURCE_ACQUIRE_V2.json`;",
        "  VN `readouts/20260715_CAD_CORRA_DIFF_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify CORRA bp / hold / RR. AUD still blocked.",
        "  Next: true greenfield outside calendar densify OR Owner RBA CSV drop.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) > 1 and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | CAD CORRA diff offline "
            f"{status.split('__')[0]}; Real on; GOAL unmet"
        )
    out: list[str] = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if not inserted and ln.strip() == "## Active Truth":
            out.extend(block)
            inserted = True
    HOT.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    panel, panel_meta = build_panel()
    if not mt5.initialize():
        raise SystemExit(f"mt5 init fail: {mt5.last_error()}")
    try:
        if not mt5.symbol_select(SYMBOL, True):
            raise SystemExit("USDCAD select fail")
        pnls, detail = probe(panel)
        m, hc = metrics(pnls), haircuts(pnls)
        v, notes = joint_verdict(m, hc)
        r = {
            "hypothesis_id": "HYP-USDCAD-CORRA-USD-DIFF-EXPAND-H4-001",
            "setup_type": "CORRA-USD |Δdiff|≥5bp → USDCAD with CAD richness; H4 SL1.5 RR2 ≤10",
            "metrics": m,
            "haircuts": hc,
            "verdict": v,
            "fail_notes": notes,
            "detail": detail,
        }
        payload = {
            "schema": "cad_corra_diff_offline_probes.v1",
            "generated_at_utc": utc_now(),
            "panel": panel_meta,
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

        write_docs(r, receipt, panel_meta)
        append_reg(r, receipt)
        patch_hot(r, receipt, panel_meta)
        print(json.dumps({"receipt": receipt, "panel_rows": panel_meta["panel_rows"], "result": {
            "id": r["hypothesis_id"], "verdict": v, **m, "x15": hc["x1_5"]["pf"], "notes": notes
        }}, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
