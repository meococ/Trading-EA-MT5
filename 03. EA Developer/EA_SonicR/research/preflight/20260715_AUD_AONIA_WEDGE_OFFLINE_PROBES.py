#!/usr/bin/env python3
"""AUD AONIA unlock via DBnomics public mirror (RBA F1 FIRMMCRID/FIRMMCRTD).

SHA-freeze AONIA + cash-target; build AUD+USD panel; ONE differential child
≠ CORRA bp densify / Mon→Thu / flush / anticarry.

A priori:
  HYP-AUDUSD-AONIA-TARGET-WEDGE-EXPAND-H4-001
  |Δ(AONIA − CashTarget)| ≥ 5bp available-at (+1bd) → AUDUSD with MM-stress
  (AONIA rising vs target → SHORT AUDUSD).

Model 0 only if PROBE_SURVIVOR. +$12 cost screen.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
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
RAW = EXO / "raw" / "g10_overnight"
RATES_USD = ROOT / "03. EA Developer" / "EA_CarryPublicRates" / "carry_rates_d1.csv"

SRC_AONIA = RAW / "dbnomics_rba_firmmcrid.csv"
SRC_TARGET = RAW / "dbnomics_rba_firmmcrtd.csv"
AONIA = RAW / "rba_aonia_firmmcrid_dbnomics.csv"
TARGET = RAW / "rba_cash_target_firmmcrtd_dbnomics.csv"
PANEL = EXO / "panels" / "aud_usd_aonia_overnight_d1_v1.csv"
CONTRACT = EXO / "contracts" / "20260715_AUD_USD_AONIA_AVAILABLE_AT_UTC_V1.json"
MAN = EXO / "manifests" / "20260715_AUD_USD_AONIA_PANEL_V1.json"
ACQUIRE = EXO / "manifests" / "20260715_RBA_ALTSOURCE_EXHAUST_V3.json"

OUT_JSON = PRE / "20260715_AUD_AONIA_WEDGE_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_AUD_AONIA_WEDGE_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_AUD_AONIA_WEDGE_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_AUD_AONIA_WEDGE_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_AUD_AONIA_WEDGE_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_AUD_AONIA_WEDGE_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
SYMBOL = "AUDUSD"

WEDGE_BP_MIN = 5.0
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


def parse_dbnomics_csv(path: Path) -> dict[date, float]:
    out: dict[date, float] = {}
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r, None)
        for row in r:
            if len(row) < 2:
                continue
            val = row[1].strip()
            if val in ("", "NA", "nan", "None"):
                continue
            try:
                out[date.fromisoformat(row[0].strip())] = float(val)
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
    keys = sorted(series)
    avail: dict[date, float] = {}
    for d in keys:
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


def freeze_sources() -> dict[str, Any]:
    RAW.mkdir(parents=True, exist_ok=True)
    if not SRC_AONIA.exists() or not SRC_TARGET.exists():
        raise SystemExit("DBnomics AONIA/target CSV missing — re-run acquire")
    shutil.copy2(SRC_AONIA, AONIA)
    shutil.copy2(SRC_TARGET, TARGET)
    meta = {
        "schema": "rba_aonia_dbnomics_freeze.v1",
        "generated_at_utc": utc_now(),
        "sources": [
            {
                "note": "DBnomics RBA/F1/FIRMMCRID Interbank Overnight Cash Rate (AONIA)",
                "url": "https://api.db.nomics.world/v22/series/RBA/F1/FIRMMCRID.csv",
                "path": str(AONIA.relative_to(ROOT)).replace("\\", "/"),
                "bytes": AONIA.stat().st_size,
                "sha256": sha256_file(AONIA),
            },
            {
                "note": "DBnomics RBA/F1/FIRMMCRTD Cash Rate Target",
                "url": "https://api.db.nomics.world/v22/series/RBA/F1/FIRMMCRTD.csv",
                "path": str(TARGET.relative_to(ROOT)).replace("\\", "/"),
                "bytes": TARGET.stat().st_size,
                "sha256": sha256_file(TARGET),
            },
        ],
        "authority": (
            "Public DBnomics mirror of RBA Statistical Table F1. "
            "FIRMMCRID = Interbank Overnight Cash Rate (AONIA). "
            "FIRMMCRTD = Cash Rate Target. rba.gov.au direct still 403."
        ),
    }
    return meta


def build_panel() -> tuple[dict[date, dict[str, float]], dict]:
    freeze = freeze_sources()
    aonia = parse_dbnomics_csv(AONIA)
    target = parse_dbnomics_csv(TARGET)
    usd = parse_usd(RATES_USD)
    if len(aonia) < 500:
        raise SystemExit(f"AONIA too short: {len(aonia)}")
    days = sorted(set(aonia) & set(target) & set(usd))
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    with PANEL.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "aud_aonia", "aud_target", "usd", "wedge_pp", "diff_pp"])
        for d in days:
            wedge = aonia[d] - target[d]
            diff = aonia[d] - usd[d]
            w.writerow(
                [
                    d.isoformat(),
                    f"{aonia[d]:.6f}",
                    f"{target[d]:.6f}",
                    f"{usd[d]:.6f}",
                    f"{wedge:.6f}",
                    f"{diff:.6f}",
                ]
            )
    aonia_a = business_lag_map(aonia, LAG_BD)
    target_a = business_lag_map(target, LAG_BD)
    usd_a = business_lag_map(usd, LAG_BD)
    adays = sorted(set(aonia_a) & set(target_a) & set(usd_a))
    panel_a: dict[date, dict[str, float]] = {}
    prev_wedge: float | None = None
    for d in adays:
        wedge = aonia_a[d] - target_a[d]
        diff = aonia_a[d] - usd_a[d]
        d_wedge_bp = None if prev_wedge is None else (wedge - prev_wedge) * 100.0
        panel_a[d] = {
            "aonia": aonia_a[d],
            "target": target_a[d],
            "usd": usd_a[d],
            "wedge": wedge,
            "diff": diff,
            "d_wedge_bp": d_wedge_bp,
        }
        prev_wedge = wedge

    meta = {
        "schema": "aud_usd_aonia_available_at_utc.v1",
        "generated_at_utc": utc_now(),
        "status": "PANEL_READY",
        "aonia_rows_raw": len(aonia),
        "target_rows_raw": len(target),
        "usd_rows_raw": len(usd),
        "panel_rows": len(days),
        "available_at_rows": len(panel_a),
        "lag_business_days": LAG_BD,
        "panel_path": str(PANEL.relative_to(ROOT)).replace("\\", "/"),
        "panel_sha256": sha256_file(PANEL),
        "aonia_sha256": sha256_file(AONIA),
        "target_sha256": sha256_file(TARGET),
        "usd_source": str(RATES_USD.relative_to(ROOT)).replace("\\", "/"),
        "freeze": freeze,
        "authority": (
            "DBnomics RBA/F1 FIRMMCRID=AONIA overnight; FIRMMCRTD=cash target. "
            "USD=public carry panel short-rate proxy. +1bd available-at lag. "
            "≠ BoC CORRA densify; rba.gov.au direct still 403."
        ),
    }
    CONTRACT.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    man = {
        "schema": "aud_usd_aonia_panel.v1",
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
        raise RuntimeError(f"AUDUSD H4 fail: {mt5.last_error()}")
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
        if not row or row["d_wedge_bp"] is None:
            continue
        d_bp = row["d_wedge_bp"]
        if abs(d_bp) < WEDGE_BP_MIN:
            continue
        if last_event_day == d:
            continue
        # AONIA rising vs target → MM stress / AUD softens → SHORT AUDUSD
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
                "# Design memo — AUD AONIA vs Cash Target wedge expand (AUDUSD)",
                "",
                "Date: 2026-07-15",
                "Data: DBnomics RBA F1 FIRMMCRID/FIRMMCRTD freeze + G3 USD; +1bd lag.",
                "",
                "## Design",
                "`HYP-AUDUSD-AONIA-TARGET-WEDGE-EXPAND-H4-001`",
                f"|Δ(AONIA−Target)|≥{WEDGE_BP_MIN}bp available-at → AUDUSD with MM stress;",
                f"H4≥08; SL {SL_ATR}×ATR; RR={RR}; hold≤{MAX_HOLD}.",
                "",
                "## ≠ kill shelf",
                "≠ CORRA−USD Δdiff expand densify (different series + wedge object);",
                "≠ Mon→Thu fundproxy / flush-MR / anticarry×vol / V8 / USBILL.",
                "",
                f"Panel SHA: `{panel_meta.get('panel_sha256')}`",
                f"AONIA SHA: `{panel_meta.get('aonia_sha256')}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — AUD AONIA target wedge",
                "",
                "| Object | Vs banned |",
                "|---|---|",
                "| AONIA−Target wedge AUDUSD | New series (DBnomics); wedge ≠ CORRA bp densify |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline probe — AUD AONIA target wedge",
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
            "Do not densify AONIA wedge bp / hold / RR. "
            "Next: independent greenfield outside densify shelves or research-grade cost."
        )
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Closeout — AUD AONIA target wedge",
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
                "# VN brief — AUD AONIA target wedge",
                "",
                f"- AONIA DBnomics unlock: PANEL READY rows={panel_meta.get('panel_rows')}.",
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
        "parent_candidate": "g10_altsource_aud_aonia_dbnomics_20260715",
        "feature_family": "aud_aonia_target_wedge_expand",
        "lane": "g10_altsource_aud_20260715",
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
        f"- **AUD AONIA WEDGE CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  RBA unlocked via **DBnomics** mirror (rba.gov.au still 403):",
        f"  FIRMMCRID AONIA SHA `{panel_meta.get('aonia_sha256','')[:16]}…`; "
        f"panel rows={panel_meta.get('panel_rows')} SHA `{panel_meta.get('panel_sha256','')[:16]}…`.",
        "  ONE new AUD differential child (≠ CORRA bp densify):",
        f"  1. `{r['hypothesis_id']}` → **{r['verdict']}** "
        f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
        f"x1.5={r['haircuts']['x1_5']['pf']}).",
        f"  Receipt `{receipt}`",
        "  `preflight/20260715_AUD_AONIA_WEDGE_OFFLINE_PROBES.json`;",
        "  acquire `manifests/20260715_RBA_ALTSOURCE_EXHAUST_V3.json`;",
        "  VN `readouts/20260715_AUD_AONIA_WEDGE_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify AONIA wedge bp / hold / RR / CORRA bp.",
        "  Next: independent greenfield outside densify OR research-grade cost.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    text = HOT.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) > 1 and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | AUD AONIA DBnomics unlock + wedge "
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
            raise SystemExit("AUDUSD select fail")
        pnls, detail = probe(panel)
        m, hc = metrics(pnls), haircuts(pnls)
        v, notes = joint_verdict(m, hc)
        r = {
            "hypothesis_id": "HYP-AUDUSD-AONIA-TARGET-WEDGE-EXPAND-H4-001",
            "setup_type": "AONIA−Target |Δwedge|≥5bp → AUDUSD MM-stress; H4 SL1.5 RR2 ≤10",
            "metrics": m,
            "haircuts": hc,
            "verdict": v,
            "fail_notes": notes,
            "detail": detail,
        }
        payload = {
            "schema": "aud_aonia_wedge_offline_probes.v1",
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
        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "panel_rows": panel_meta["panel_rows"],
                    "aonia_sha": panel_meta["aonia_sha256"],
                    "result": {
                        "id": r["hypothesis_id"],
                        "verdict": v,
                        **m,
                        "x15": hc["x1_5"]["pf"],
                        "notes": notes,
                    },
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
