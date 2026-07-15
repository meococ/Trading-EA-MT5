#!/usr/bin/env python3
"""AUD AONIA−USD level-follow child on frozen DBnomics panel.

Wedge expand INTENDED_EMPTY (AONIA≈target; N=0). This is the ONE viable
AUD differential object ≠ CORRA Δbp densify / wedge densify.

A priori:
  HYP-AUDUSD-AONIA-USD-LEVEL-FOLLOW-H4-001
  available-at |AONIA−USD| ≥ 0.25pp → trade AUDUSD WITH AUD richness;
  H4≥08; one new entry/day; SL1.5 ATR; RR2; hold≤10.

Model 0 only if PROBE_SURVIVOR. +$12.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"
EXO = PRE / "v8_exogenous"
PANEL = EXO / "panels" / "aud_usd_aonia_overnight_d1_v1.csv"
AONIA = EXO / "raw" / "g10_overnight" / "rba_aonia_firmmcrid_dbnomics.csv"

OUT_JSON = PRE / "20260715_AUD_AONIA_USD_LEVEL_OFFLINE_PROBES.json"
OUT_MD = READ / "20260715_AUD_AONIA_USD_LEVEL_OFFLINE_PROBES.md"
OUT_DEDUP = READ / "20260715_AUD_AONIA_USD_LEVEL_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / "20260715_AUD_AONIA_USD_LEVEL_DESIGN_MEMO.md"
OUT_CLOSE = READ / "20260715_AUD_AONIA_USD_LEVEL_SESSION_CLOSEOUT.md"
OUT_VN = READ / "20260715_AUD_AONIA_USD_LEVEL_VN_ACTION_BRIEF.md"
OUT_SESSION_VN = READ / "20260715_G10_ALT_GREENFIELD_SESSION_VN_BRIEF.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0
DEPOSIT = 100_000.0
RISK_FRAC = 0.005
SYMBOL = "AUDUSD"

LEVEL_PP = 0.25  # |AONIA-USD| threshold in percentage points
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


def business_lag_map(series: dict[date, float], lag: int) -> dict[date, float]:
    keys = sorted(series)
    avail = {}
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


def load_panel_available() -> tuple[dict[date, dict[str, float]], dict]:
    raw = {}
    with PANEL.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            d = date.fromisoformat(row["date"])
            raw[d] = {
                "aonia": float(row["aud_aonia"]),
                "usd": float(row["usd"]),
                "diff": float(row["diff_pp"]),
            }
    aonia = {d: v["aonia"] for d, v in raw.items()}
    usd = {d: v["usd"] for d, v in raw.items()}
    aonia_a = business_lag_map(aonia, LAG_BD)
    usd_a = business_lag_map(usd, LAG_BD)
    panel = {}
    for d in sorted(set(aonia_a) & set(usd_a)):
        diff = aonia_a[d] - usd_a[d]
        panel[d] = {"aonia": aonia_a[d], "usd": usd_a[d], "diff": diff}
    meta = {
        "panel_path": str(PANEL.relative_to(ROOT)).replace("\\", "/"),
        "panel_sha256": sha256_file(PANEL),
        "aonia_sha256": sha256_file(AONIA) if AONIA.exists() else None,
        "panel_rows": len(raw),
        "available_at_rows": len(panel),
        "lag_business_days": LAG_BD,
        "level_pp": LEVEL_PP,
        "authority": (
            "DBnomics FIRMMCRID AONIA + carry USD; +1bd lag. "
            "Level-follow |diff|≥0.25pp WITH AUD richness. "
            "≠ CORRA Δbp densify; ≠ AONIA−Target wedge densify (wedge INTENDED_EMPTY)."
        ),
    }
    return panel, meta


def pip_size(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        return 0.0001
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


def probe(panel):
    rates = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_H4, FROM, TO)
    if rates is None or len(rates) < 200:
        raise RuntimeError(f"AUDUSD H4 fail: {mt5.last_error()}")
    t = rates["time"].astype(np.int64)
    o = rates["open"].astype(float)
    h = rates["high"].astype(float)
    l = rates["low"].astype(float)
    c = rates["close"].astype(float)
    atr = atr_arr(h, l, c, 14)

    closed = []
    pos = None
    last_entry_day = None

    for i in range(20, len(t)):
        dt = datetime.fromtimestamp(int(t[i]), tz=timezone.utc)
        d = dt.date()
        if pos is not None:
            exit_px = reason = None
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
                closed.append(
                    {
                        "pnl": cash_pnl(SYMBOL, pos["side"], pos["entry"], exit_px, pos["lots"]),
                        "reason": reason,
                    }
                )
                pos = None

        if pos is not None:
            continue
        if d.weekday() >= 5 or dt.hour < 8:
            continue
        if last_entry_day == d:
            continue
        row = panel.get(d)
        if not row:
            continue
        diff = row["diff"]
        if abs(diff) < LEVEL_PP:
            continue
        # AUD richer → LONG AUDUSD
        side = 1 if diff > 0 else -1
        if not np.isfinite(atr[i]) or atr[i] <= 0:
            continue
        entry = float(o[i])
        sl = entry - side * SL_ATR * atr[i]
        tp = entry + side * RR * SL_ATR * atr[i]
        pos = {
            "side": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "lots": risk_lots(SYMBOL, entry, sl),
            "bars": 0,
        }
        last_entry_day = d

    if pos is not None:
        closed.append(
            {
                "pnl": cash_pnl(SYMBOL, pos["side"], pos["entry"], float(c[-1]), pos["lots"]),
                "reason": "eod",
            }
        )
    pnls = [x["pnl"] for x in closed]
    detail = {"by_reason": {}}
    for x in closed:
        detail["by_reason"][x["reason"]] = detail["by_reason"].get(x["reason"], 0) + 1
    return pnls, detail


def write_docs(r, receipt, meta):
    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design — AUD AONIA−USD level-follow (AUDUSD)",
                "",
                "Context: AONIA−Target wedge INTENDED_EMPTY (AONIA≈target; N=0).",
                "This child uses cross-currency level on frozen DBnomics panel.",
                "",
                f"`HYP-AUDUSD-AONIA-USD-LEVEL-FOLLOW-H4-001`",
                f"|AONIA−USD|≥{LEVEL_PP}pp → WITH AUD richness; H4≥08; SL{SL_ATR} RR{RR} ≤{MAX_HOLD}.",
                "",
                "## ≠ shelves",
                "≠ CORRA Δdiff expand densify; ≠ wedge bp densify; ≠ V8 Menkhoff vol-gate;",
                "≠ anticarry (direction is WITH rate differential).",
                "",
                f"Panel SHA `{meta.get('panel_sha256')}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# Dedup — AONIA−USD level-follow",
                "",
                "| Object | Clearance |",
                "|---|---|",
                "| AONIA−USD level WITH | ≠ CORRA Δbp; ≠ wedge; ≠ anticarry flip |",
                "",
            ]
        ),
        encoding="utf-8",
    )
    OUT_MD.write_text(
        "\n".join(
            [
                "# Offline — AONIA−USD level-follow",
                f"Receipt `{receipt}`",
                f"Verdict **{r['verdict']}** ({', '.join(r['fail_notes']) or 'pass'})",
                f"N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']}",
                f"x1.5={r['haircuts']['x1_5']['pf']} detail={json.dumps(r['detail'])}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    status = "PROBE_SURVIVOR_PRESENT" if r["verdict"] == "PROBE_SURVIVOR" else "OFFLINE_KILL__NO_MODEL0"
    next_line = (
        "Model 0 prereg for survivor."
        if r["verdict"] == "PROBE_SURVIVOR"
        else "Do not densify AONIA level pp / hold / RR. Next: research-grade cost or next greenfield."
    )
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Closeout — AONIA−USD level-follow",
                f"Status `{status}`",
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
                "# VN brief — AONIA−USD level-follow",
                f"- Panel AONIA READY. Wedge child đã INTENDED_EMPTY.",
                f"- `{r['hypothesis_id']}`: N={r['metrics']['n']} PF={r['metrics']['pf']} "
                f"tpw={r['metrics']['tpw']} x1.5={r['haircuts']['x1_5']['pf']} → {r['verdict']}",
                f"- Next: {next_line}",
                "- Best shelf RR2 `194548`.",
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
                    "parent_candidate": "g10_altsource_aud_aonia_dbnomics_20260715",
                    "feature_family": "aud_aonia_usd_level_follow",
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
                },
                ensure_ascii=True,
            )
            + "\n"
        )


def patch_hot(r, receipt, meta):
    status = "PROBE_SURVIVOR_PRESENT" if r["verdict"] == "PROBE_SURVIVOR" else "OFFLINE_KILL__NO_MODEL0"
    stamp = datetime.now().strftime("%H:%M")
    block = [
        f"- **AUD AONIA−USD LEVEL CLOSEOUT (2026-07-15 ~{stamp} ICT) — "
        f"`EXO_FRED_DISPLACE_SPAM_PAUSED` / `{status}`.**",
        "  AONIA panel READY (DBnomics); wedge expand INTENDED_EMPTY → level-follow child:",
        f"  1. `{r['hypothesis_id']}` → **{r['verdict']}** "
        f"(N={r['metrics']['n']} PF={r['metrics']['pf']} tpw={r['metrics']['tpw']} "
        f"x1.5={r['haircuts']['x1_5']['pf']}).",
        f"  Receipt `{receipt}` panel SHA `{meta.get('panel_sha256','')[:16]}…`",
        "  `preflight/20260715_AUD_AONIA_USD_LEVEL_OFFLINE_PROBES.json`;",
        "  VN `readouts/20260715_AUD_AONIA_USD_LEVEL_VN_ACTION_BRIEF.md`.",
        "  Do **not** densify AONIA level pp / wedge bp / CORRA bp / hold / RR.",
        "  Next: research-grade cost/tick or next true greenfield — not densify shelves.",
        "  Best shelf RR2 `194548`. Cost freeze GAP; login not headline. GOAL unmet.",
        "",
    ]
    lines = HOT.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# Hot Cache"):
        lines[1] = (
            f"Updated: 2026-07-15 ~{stamp} ICT | AONIA−USD level "
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


def write_session_vn(r_aud, r_thin, aud_receipt, thin_receipt, meta):
    OUT_SESSION_VN.write_text(
        "\n".join(
            [
                "# VN brief — G10 AONIA unlock + greenfield continue",
                "",
                "Thời điểm: 2026-07-15 (continue R&D, no Owner idle)",
                "",
                "## Track 1 — RBA/AONIA alt-source EXHAUST",
                "- rba.gov.au CSV/XLS vẫn **403**; OECD 404; GitHub readrba raw 404.",
                "- **DBnomics** `RBA/F1/FIRMMCRID` (AONIA) + `FIRMMCRTD` (target) **OK + SHA-freeze**.",
                "- BIS CBPOL AU daily cũng OK (policy step).",
                f"- Panel AUD+USD AONIA READY rows={meta.get('panel_rows')} "
                f"SHA `{meta.get('panel_sha256','')[:16]}…`.",
                "- Child wedge `HYP-AUDUSD-AONIA-TARGET-WEDGE-EXPAND-H4-001` → "
                "**INTENDED_EMPTY/KILL** (AONIA≈target; N=0) — không densify wedge bp.",
                f"- Child level `{r_aud['hypothesis_id']}` → **{r_aud['verdict']}** "
                f"(N={r_aud['metrics']['n']} PF={r_aud['metrics']['pf']} "
                f"tpw={r_aud['metrics']['tpw']} x1.5={r_aud['haircuts']['x1_5']['pf']}).",
                f"  Receipt `{aud_receipt}`",
                "",
                "## Track 2 — Independent greenfield",
                f"- `{r_thin['hypothesis_id']}` → **{r_thin['verdict']}** "
                f"(N={r_thin['metrics']['n']} PF={r_thin['metrics']['pf']} "
                f"tpw={r_thin['metrics']['tpw']} x1.5={r_thin['haircuts']['x1_5']['pf']}) "
                "— PF ok, N/cadence chết; **không densify** thin/jump.",
                f"  Receipt `{thin_receipt}`",
                "",
                "## Quyết định",
                "- **Zero Model 0** trừ khi level child = PROBE_SURVIVOR (check metrics).",
                "- Không densify: CORRA bp / AONIA wedge / AONIA level / thin3 / TOM / gap / consec / XAU.",
                "- Best shelf RR2 `194548`. Cost freeze GAP. Microstructure blocked.",
                "- Next EV: research-grade cost/tick **hoặc** next true greenfield — AONIA đã unlock.",
                "",
                "Login không phải headline. GOAL unmet.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main():
    panel, meta = load_panel_available()
    if not mt5.initialize():
        raise SystemExit(mt5.last_error())
    try:
        if not mt5.symbol_select(SYMBOL, True):
            raise SystemExit("AUDUSD select fail")
        pnls, detail = probe(panel)
        m, hc = metrics(pnls), haircuts(pnls)
        v, notes = joint_verdict(m, hc)
        r = {
            "hypothesis_id": "HYP-AUDUSD-AONIA-USD-LEVEL-FOLLOW-H4-001",
            "setup_type": f"|AONIA−USD|≥{LEVEL_PP}pp WITH AUD; H4 SL{SL_ATR} RR{RR} ≤{MAX_HOLD}",
            "metrics": m,
            "haircuts": hc,
            "verdict": v,
            "fail_notes": notes,
            "detail": detail,
        }
        payload = {
            "schema": "aud_aonia_usd_level_offline_probes.v1",
            "generated_at_utc": utc_now(),
            "panel": meta,
            "base_cost_usd": BASE_COST,
            "prior_wedge": {
                "hypothesis_id": "HYP-AUDUSD-AONIA-TARGET-WEDGE-EXPAND-H4-001",
                "status": "INTENDED_EMPTY_KILL",
                "note": "AONIA tracks target; |Δwedge|≥5bp almost never fires",
            },
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

        write_docs(r, receipt, meta)
        append_reg(r, receipt)
        patch_hot(r, receipt, meta)

        # pull thin3 result for session VN
        thin_json = PRE / "20260715_GREENFIELD_THIN3_JUMP_FADE_OFFLINE_PROBES.json"
        thin = json.loads(thin_json.read_text(encoding="utf-8"))
        r_thin = thin["results"][0]
        write_session_vn(r, r_thin, receipt, thin.get("receipt_sha256"), meta)

        print(
            json.dumps(
                {
                    "receipt": receipt,
                    "panel_rows": meta["panel_rows"],
                    "result": {
                        "id": r["hypothesis_id"],
                        "verdict": v,
                        **m,
                        "x15": hc["x1_5"]["pf"],
                        "notes": notes,
                        "detail": detail,
                    },
                    "model0": v == "PROBE_SURVIVOR",
                },
                indent=2,
            )
        )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
