#!/usr/bin/env python3
"""HARD PIVOT W22 — architecture monetization after W1–W21 OHLC ALL_KILL.

Track 1 Deep Research: AUTH_BLOCKED (login wall) — receipt separate; do not stall.
Track 2: genuine architecture monetization NOT in W1–W21 and NOT densify of
killed entry objects / FVG / H4-retest / MaxKZ / BE@1R / exo displace spam.

A priori objects (offline; Model 0 only PROBE_SURVIVOR):
  A. HYP-RR2-SAMEDAY-FLAT-ARCH-001
     Inventory architecture: keep frozen RR2 trade iff exit calendar-day ==
     entry calendar-day (no overnight hold). ≠ weekend-flat Fri-only densify;
     ≠ MaxKZ; ≠ BE@1R; ≠ W1–W21 OHLC entry rebuild.
  B. HYP-BOOK-CLEAN-SEQSLOT-001
     Clean RR2+Spark book with hard sequential single open slot (drop later
     open while any prior trade still open). ≠ heat-pool same-bar; ≠ R29 oneslot
     FX3 CONT; ≠ MaxKZ densify.
  BOOK. HYP-BOOK-SAMEDAY-SEQSLOT-APRIORI-001
     A then B on the pooled stream (sameday on RR2 only, then seq-slot book).

+$12 research screen. Aim stress lift vs RR2/clean baselines.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
REG = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "CANDIDATE_REGISTRY.jsonl"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"
RUNS = ROOT / "02. AlphaFactory" / "runs"
DR_RECEIPT = PRE / "20260715_DEEP_RESEARCH_AUTH_CHECK_RECEIPT.json"
COST_STATUS = PRE / "20260715_COST_GRADE_PUSH_W13_STATUS.json"
QFSI_HB = PRE / "20260715_QFSI_007_WATCHER_HEARTBEAT.json"

STEM = "20260715_HARD_PIVOT_W22_ARCH_MONETIZE"
OUT_JSON = PRE / f"{STEM}_OFFLINE_PROBES.json"
OUT_MD = READ / f"{STEM}_OFFLINE_PROBES.md"
OUT_DEDUP = READ / f"{STEM}_DEDUP_CLEARANCE.md"
OUT_DESIGN = READ / f"{STEM}_DESIGN_MEMO.md"
OUT_PANEL = READ / f"{STEM}_3CRITIC_PANEL.md"
OUT_CLOSE = READ / f"{STEM}_SESSION_CLOSEOUT.md"
OUT_VN = READ / f"{STEM}_VN_ACTION_BRIEF.md"
OUT_COMBO_VN = READ / "20260715_COST_GRADE_AND_HARD_PIVOT_W22_VN_ACTION_BRIEF.md"
OUT_FREEZE = READ / f"{STEM}_APRIORI_FREEZE.md"

FROM = datetime(2021, 1, 1)
TO = datetime(2025, 12, 31, 23, 59)
WEEKS = (TO - FROM).days / 7.0
BASE_COST = 12.0

SLEEVES = {
    "A_RR2": {
        "hypothesis_id": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
        "run_id": "20260714_194548",
        "ea": "EA_SilverBullet",
        "priority": 1,
    },
    "B_SPARK": {
        "hypothesis_id": "HYP-SPARK-CAPACITY-3PD-001",
        "run_id": "20260714_193358",
        "ea": "EA_M15SparkAsian",
        "priority": 2,
    },
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def pf_of(pnls: list[float]) -> float | None:
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    if losses <= 0:
        return None if wins <= 0 else 999.99
    return wins / losses


def haircuts(pnls: list[float], base: float = BASE_COST) -> dict:
    out = {}
    for key, mult in (("x1", 1.0), ("x1_5", 1.5), ("x2", 2.0)):
        cut = [float(p) - base * mult for p in pnls]
        p = pf_of(cut)
        out[key] = {
            "pf": None if not cut else round(float(p or 0.0), 4),
            "net": round(float(sum(cut)), 2) if cut else 0.0,
            "exp": round(float(sum(cut) / len(cut)), 4) if cut else 0.0,
        }
    return out


def metrics(pnls: list[float]) -> dict:
    n = len(pnls)
    p = pf_of(pnls)
    net = float(sum(pnls)) if pnls else 0.0
    return {
        "n": int(n),
        "pf": None if p is None else round(float(p), 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(float(n / WEEKS), 4) if WEEKS else None,
    }


def joint_verdict(m: dict, hc: dict, baseline_x15: float | None = None) -> tuple[str, list[str]]:
    notes: list[str] = []
    n, pf, tpw = m["n"] or 0, m["pf"] or 0.0, m["tpw"] or 0.0
    pf12 = (hc.get("x1") or {}).get("pf") or 0.0
    x15 = (hc.get("x1_5") or {}).get("pf") or 0.0
    if n < 80:
        notes.append("n_fail")
    if pf is None or pf < 1.30:
        notes.append("pf_fail")
    if tpw is None or tpw < 2.0 or tpw > 5.0:
        notes.append("cadence_fail")
    if pf12 < 1.30:
        notes.append("pf12_fail")
    if x15 < 1.25:
        notes.append("stress_fail")
    if baseline_x15 is not None and x15 <= baseline_x15 + 0.01:
        notes.append("no_stress_lift_vs_baseline")
    if not notes:
        return "PROBE_SURVIVOR", []
    return "KILLED_AT_OFFLINE_PROBE", notes


def parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def decode_report(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-16", "utf-16-le", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def parse_num(s: str) -> float:
    s = (s or "").replace("\xa0", " ").replace(" ", "").replace(",", "")
    if not s or s == "-":
        return 0.0
    return float(s)


def parse_deals_html(report_path: Path) -> list[dict]:
    html = decode_report(report_path)
    m = re.search(r"<b>\s*(Giao dịch|Deals)\s*</b>", html, re.IGNORECASE)
    if not m:
        raise ValueError(f"Deals section missing: {report_path}")
    section = html[m.end() :]
    stop = re.search(r"<b>\s*(Orders|Lịch sử|History|Graph|Biểu đồ)\s*</b>", section, re.I)
    if stop:
        section = section[: stop.start()]
    tr_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.I | re.S)
    td_re = re.compile(r"<td[^>]*>(.*?)</td>", re.I | re.S)
    deals = []
    for row in tr_re.findall(section):
        tds = [re.sub(r"<[^>]+>", "", td).strip() for td in td_re.findall(row)]
        if len(tds) < 11:
            continue
        if tds[0].lower().startswith(("thời gian", "time")):
            continue
        if not re.match(r"^\d{4}\.\d{2}\.\d{2}", tds[0]):
            continue
        side = tds[3].lower()
        if side not in ("buy", "sell"):
            continue
        deals.append(
            {
                "time": datetime.strptime(tds[0][:19], "%Y.%m.%d %H:%M:%S"),
                "symbol": tds[2],
                "side": side,
                "direction": tds[4].lower(),
                "order": tds[7],
                "commission": parse_num(tds[8]) if len(tds) > 8 else 0.0,
                "swap": parse_num(tds[9]) if len(tds) > 9 else 0.0,
                "profit": parse_num(tds[10]) if len(tds) > 10 else 0.0,
            }
        )
    return deals


def deals_to_trades(deals: list[dict], sleeve: str) -> list[dict]:
    open_by_order: dict[str, dict] = {}
    trades: list[dict] = []
    for d in deals:
        direction = d["direction"]
        if direction in ("in", "vào", "vao"):
            open_by_order[d["order"]] = d
        elif direction in ("out", "ra"):
            entry = open_by_order.pop(d["order"], None)
            pnl = d["profit"] + d["swap"] + d["commission"]
            if entry is not None:
                pnl += entry["commission"] + entry["swap"]
            trades.append(
                {
                    "sleeve": sleeve,
                    "entry_time": entry["time"] if entry else d["time"],
                    "exit_time": d["time"],
                    "side": entry["side"] if entry else d["side"],
                    "pnl": pnl,
                    "symbol": d["symbol"] or (entry["symbol"] if entry else ""),
                    "risk_usd": None,
                }
            )
    return trades


def find_trades_csv(run_dir: Path) -> Path | None:
    hits = list(run_dir.glob("logs/*_Trades_*.csv"))
    if not hits:
        hits = list(run_dir.glob("**/logs/*_Trades_*.csv"))
    return sorted(hits)[0] if hits else None


def load_rr2_risk_from_csv(path: Path) -> dict[tuple[datetime, str], float]:
    """Map (open_time, side) → risk_usd from PX6 trades CSV."""
    opens: dict[str, dict] = {}
    out: dict[tuple[datetime, str], float] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = str(row.get("position_id") or "").strip()
            action = str(row.get("action") or "").upper()
            if action == "OPEN":
                opens[pid] = row
            elif action == "CLOSE" and str(row.get("is_final_close") or "0") in ("1", "true", "True"):
                op = opens.get(pid, {})
                entry = float(op.get("entry_price") or op.get("price") or 0)
                sl = float(op.get("sl") or op.get("initial_sl") or 0)
                vol = float(op.get("volume") or row.get("volume") or 0)
                side = str(op.get("order_type") or "").upper()
                side_s = "sell" if "SELL" in side else "buy"
                ot = parse_dt(op.get("event_time") or "")
                risk_pts = abs(entry - sl) if entry and sl else 0.0
                px = entry if entry else 150.0
                risk_usd = (vol * 100_000.0 * risk_pts) / px if px > 0 and vol > 0 and risk_pts > 0 else 0.0
                if ot is not None:
                    out[(ot, side_s)] = risk_usd
    return out


def floor_m15(dt: datetime) -> datetime:
    return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)


def load_closed_from_px6(path: Path, sleeve: str) -> list[dict]:
    """Prefer PX6 trades CSV when present — risk_usd is native (no join)."""
    opens: dict[str, dict] = {}
    closed: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = str(row.get("position_id") or "").strip()
            action = str(row.get("action") or "").upper()
            if action == "OPEN":
                opens[pid] = row
            elif action == "CLOSE" and str(row.get("is_final_close") or "0") in ("1", "true", "True"):
                op = opens.get(pid, {})
                try:
                    pnl = float(row.get("net_profit") or 0)
                except ValueError:
                    continue
                entry = float(op.get("entry_price") or op.get("price") or 0)
                sl = float(op.get("sl") or op.get("initial_sl") or 0)
                vol = float(op.get("volume") or row.get("volume") or 0)
                side_raw = str(op.get("order_type") or "").upper()
                side = "sell" if "SELL" in side_raw else "buy"
                risk_pts = abs(entry - sl) if entry and sl else 0.0
                px = entry if entry else 150.0
                risk_usd = (vol * 100_000.0 * risk_pts) / px if px > 0 and vol > 0 and risk_pts > 0 else 0.0
                ot = parse_dt(op.get("event_time") or "")
                xt = parse_dt(row.get("event_time") or "")
                if ot is None or xt is None:
                    continue
                closed.append(
                    {
                        "sleeve": sleeve,
                        "entry_time": ot,
                        "exit_time": xt,
                        "side": side,
                        "pnl": pnl,
                        "symbol": str(op.get("symbol") or row.get("symbol") or ""),
                        "risk_usd": float(risk_usd),
                    }
                )
    return closed


def load_sleeve(key: str, meta: dict) -> dict[str, Any]:
    run_dir = RUNS / meta["ea"] / meta["run_id"]
    report = run_dir / "report.html"
    if not report.exists():
        raise FileNotFoundError(report)
    csv_path = find_trades_csv(run_dir)
    # RR2: PX6 CSV is authoritative for risk geometry (ARCH rebuild contract).
    # Spark: report deals (PX6 may be absent or incomplete).
    if key == "A_RR2" and csv_path is not None:
        trades = load_closed_from_px6(csv_path, key)
        source = "px6_trades_csv"
    else:
        trades = deals_to_trades(parse_deals_html(report), key)
        source = "report_deals"
    matched = 0
    for t in trades:
        t["priority"] = meta["priority"]
        t["bar"] = floor_m15(t["entry_time"])
        t["heat_key"] = (t.get("symbol") or "UNK", t["bar"])
        if t.get("risk_usd") is not None and t["risk_usd"] > 0:
            matched += 1
    return {
        "key": key,
        **meta,
        "run_dir": str(run_dir.as_posix()),
        "report_sha256": sha256_file(report),
        "trades_csv": str(csv_path.as_posix()) if csv_path else None,
        "trade_source": source,
        "n": len(trades),
        "risk_matched": matched,
        "trades": trades,
    }


def apply_heat_priority(trades: list[dict]) -> tuple[list[dict], int]:
    best: dict[tuple, dict] = {}
    dropped = 0
    ordered = sorted(trades, key=lambda t: (t["priority"], t["entry_time"]))
    for t in ordered:
        k = t["heat_key"]
        if k not in best:
            best[k] = t
        else:
            dropped += 1
    kept = list(best.values())
    kept.sort(key=lambda t: t["entry_time"])
    return kept, dropped


def apply_seq_slot(trades: list[dict]) -> tuple[list[dict], int]:
    """Max 1 concurrent open: drop opens that start while another is still open."""
    ordered = sorted(trades, key=lambda t: (t["entry_time"], t["priority"]))
    kept: list[dict] = []
    open_until: datetime | None = None
    dropped = 0
    for t in ordered:
        et, xt = t["entry_time"], t["exit_time"]
        if open_until is not None and et < open_until:
            dropped += 1
            continue
        kept.append(t)
        open_until = xt
    return kept, dropped


def apply_sameday_flat(trades: list[dict]) -> tuple[list[dict], int]:
    """Keep trades that close on the same calendar day as entry (no overnight)."""
    kept = []
    dropped = 0
    for t in trades:
        et, xt = t["entry_time"], t["exit_time"]
        if et.date() == xt.date():
            kept.append(t)
        else:
            dropped += 1
    return kept, dropped


def result_block(
    hyp_id: str,
    family: str,
    trades: list[dict],
    baseline_x15: float | None,
    extra: dict | None = None,
) -> dict:
    pnls = [float(t["pnl"]) for t in trades]
    m = metrics(pnls)
    hc = haircuts(pnls)
    verdict, notes = joint_verdict(m, hc, baseline_x15=baseline_x15)
    out = {
        "hypothesis_id": hyp_id,
        "family": family,
        "metrics": m,
        "haircut_flat12": hc,
        "baseline_x15": baseline_x15,
        "stress_lift_vs_baseline": None
        if baseline_x15 is None
        else round(((hc.get("x1_5") or {}).get("pf") or 0.0) - baseline_x15, 4),
        "verdict": verdict,
        "notes": notes,
    }
    if extra:
        out["contract"] = extra
    return out


def write_docs(payload: dict) -> None:
    results = payload["results"]
    book = payload["book"]
    lines = [
        f"# Offline probes — HARD PIVOT W22 architecture monetization",
        "",
        f"Generated: `{payload['created_at_utc']}`",
        f"Deep Research: `{payload['deep_research']['verdict']}`",
        f"Receipt SHA: `{payload['receipt_sha256']}`",
        "",
        "| ID | N | PF | tpw | PF@$12 | x1.5 | Verdict | Notes |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in results + [book]:
        m, hc = r["metrics"], r["haircut_flat12"]
        lines.append(
            f"| `{r['hypothesis_id']}` | {m['n']} | {m['pf']} | {m['tpw']} | "
            f"{hc['x1']['pf']} | {hc['x1_5']['pf']} | "
            f"{r['verdict'].replace('KILLED_AT_OFFLINE_PROBE','KILL').replace('PROBE_SURVIVOR','SURV')} | "
            f"{','.join(r.get('notes') or [])} |"
        )
    lines += [
        "",
        "## Baselines",
        f"- RR2 alone PF@$12 x1/x1.5 = "
        f"{payload['baselines']['rr2']['haircut_flat12']['x1']['pf']} / "
        f"{payload['baselines']['rr2']['haircut_flat12']['x1_5']['pf']}",
        f"- Clean heat-pool PF@$12 x1/x1.5 = "
        f"{payload['baselines']['clean_heat']['haircut_flat12']['x1']['pf']} / "
        f"{payload['baselines']['clean_heat']['haircut_flat12']['x1_5']['pf']}",
        "",
        "Model 0 withheld unless PROBE_SURVIVOR. No densify W14/FVG/W1–W21.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    OUT_DEDUP.write_text(
        "\n".join(
            [
                "# De-dup clearance — HARD PIVOT W22 architecture monetization",
                "",
                "Date: 2026-07-15",
                "Authority: OHLC W1–W21 ALL_KILL; Deep Research auth-blocked; non-OHLC track",
                "",
                "## Objects",
                "",
                "| ID | Class | Independence claim |",
                "|---|---|---|",
                "| `HYP-RR2-SAMEDAY-FLAT-ARCH-001` | Same-day inventory flat on frozen RR2 | Keep exit.date==entry.date; **not** weekend-flat Fri-only; **not** MaxKZ; **not** BE@1R; **not** W1–W21 OHLC |",
                "| `HYP-BOOK-CLEAN-SEQSLOT-001` | Sequential single-open book | Max 1 concurrent across RR2+Spark; **not** heat-pool same-bar; **not** R29 oneslot FX3 CONT; **not** MaxKZ densify |",
                "| `HYP-BOOK-SAMEDAY-SEQSLOT-APRIORI-001` | Book of A→B | Composition of cleared objects only |",
                "",
                "## Banned collisions",
                "",
                "- W1–W21 OHLC densify / H4-retest / FVG / R10–R31 / exit / MaxKZ / ORB/IB",
                "- ARCH rebuild voltarget / H4-regime gate densify",
                "- EXO_FRED_DISPLACE_SPAM / SOFR−SONIA twin / AONIA/CORRA densify",
                "- Vacuous costfloor@$24 (all RR2 risk already >$24) — abandoned pre-freeze",
                "",
                "## Clearance",
                "",
                "**CLEARED** for offline probe only.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_DESIGN.write_text(
        "\n".join(
            [
                "# Design memo — W22 architecture monetization",
                "",
                "## Problem",
                "",
                "Local OHLC HARD PIVOT W1–W21 saturated ALL_KILL. Best near-miss W14",
                "H4-retest PF@$12=1.221 — densify forbidden. Thick edges miss cadence;",
                "dense edges die under +$12. Need architecture that changes **inventory**",
                "or **book concurrency**, not another OHLC entry template.",
                "",
                "## Design A — Same-day flat (no overnight inventory)",
                "",
                "GOAL scalp contract limits overnight exposure. On frozen RR2, keep only",
                "trades that close same calendar day. Tests whether overnight legs are",
                "friction sinks. ≠ `HYP-SB-WEEKEND-FLAT-001` (Fri-only).",
                "",
                "## Design B — Sequential single-open slot",
                "",
                "Clean heat-pool only collapses same (symbol, M15-bar). Concurrent",
                "overlap across sleeves still compounds friction + correlation.",
                "Hard seq-slot: refuse new open while any book trade is open.",
                "",
                "## Abandoned pre-freeze",
                "",
                "Costfloor risk_usd>=2×$12 is vacuous on 0.5-lot RR2 (all risk≳$38).",
                "Not probed as a claim; replaced by same-day flat.",
                "",
                "## Deep Research",
                "",
                "Browser ChatGPT session on login wall — packet not submitted.",
                "Continue Track 2 without waiting.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_PANEL.write_text(
        "\n".join(
            [
                "# 3-critic panel — W22 architecture monetization",
                "",
                "## Sonic trader critic",
                "Same-day flat is inventory architecture aligned with scalp contract.",
                "Seq-slot is portfolio risk architecture, not a fake OHLC edge.",
                "",
                "## Quant validation critic",
                "+$12 x1 / x1.5 gates bind. Require stress lift vs RR2/clean baselines.",
                "No post-hoc day/hour mining.",
                "",
                "## MQL5/MT5 systems critic",
                "Offline on frozen PX6 RR2 + Spark report deals. Closed-bar.",
                "Model 0 only if survivor.",
                "",
                "## Coordinator",
                "CLEARED offline. Deep Research auth-blocked recorded.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    status = payload["status"]
    OUT_CLOSE.write_text(
        "\n".join(
            [
                "# Session closeout — HARD PIVOT W22 architecture monetization",
                "",
                f"Status: `{status}`",
                f"Deep Research: `{payload['deep_research']['verdict']}`",
                f"Receipt: `{payload['receipt_sha256']}`",
                "",
                "## Results",
                "",
                *[
                    f"- `{r['hypothesis_id']}` → **{r['verdict']}** "
                    f"(N={r['metrics']['n']} PF@$12={r['haircut_flat12']['x1']['pf']} "
                    f"x1.5={r['haircut_flat12']['x1_5']['pf']})"
                    for r in results + [book]
                ],
                "",
                "## Non-actions",
                "",
                "- Do **not** densify W14 / FVG / W1–W21 / costfloor mult / seq rules from readout.",
                "- Do **not** Model 0 without PROBE_SURVIVOR.",
                "- Re-attempt Deep Research only after Owner ChatGPT login.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_VN.write_text(
        "\n".join(
            [
                "# VN action brief — HARD PIVOT W22 architecture monetization",
                "",
                f"- Deep Research: **login wall** — không submit; receipt `AUTH_BLOCKED`.",
                f"- W22 offline: `{status}`.",
                *[
                    f"  - `{r['hypothesis_id']}`: N={r['metrics']['n']} "
                    f"PF@$12={r['haircut_flat12']['x1']['pf']} "
                    f"x1.5={r['haircut_flat12']['x1_5']['pf']} → "
                    f"**{'SURV' if r['verdict']=='PROBE_SURVIVOR' else 'KILL'}**"
                    for r in results + [book]
                ],
                "- Không densify W14/FVG/W1–W21. R-series vẫn PAUSED. Cost freeze GAP.",
                "- Next: nếu ALL_KILL → surface/acquisition mới độc lập hoặc Owner login ChatGPT + QFSI deals.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_COMBO_VN.write_text(
        "\n".join(
            [
                "# VN — Cost-grade + HARD PIVOT W22",
                "",
                "## Cost-grade",
                "",
                f"- QFSI: `{payload['qfsi_spot']}`",
                f"- Freeze: still GAP (deals~11; quote days calendar-bound).",
                "",
                "## W22",
                "",
                f"- `{status}` / `NO_MODEL0` / Deep Research `{payload['deep_research']['verdict']}`.",
                "- Objects: same-day flat + seq-slot (architecture; not OHLC densify).",
                "- Clean book PRIMARY vẫn GOAL_SCREEN_FAIL (PF@$12=1.184).",
                "- Best shelf RR2 `194548`. Không densify W14/FVG.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    OUT_FREEZE.write_text(
        "\n".join(
            [
                "# A priori freeze — W22 architecture monetization",
                "",
                f"Frozen before probe. Receipt later binds to `{STEM}_OFFLINE_PROBES.json`.",
                "",
                "## Parameters (immutable this board)",
                "",
                f"- COSTFLOOR abandoned (vacuous on 0.5-lot RR2)",
                "- SAMEDAY: exit.date == entry.date on RR2",
                "- SEQSLOT: max 1 concurrent open across RR2+Spark",
                "- Window: 2021-01-01 → 2025-12-31 elapsed weeks",
                "- Screen: N≥80; PF≥1.30; tpw∈[2,5]; PF@$12≥1.30; x1.5≥1.25; stress lift vs baseline",
                "",
                "## Forbidden",
                "",
                "W1–W21 densify; FVG; H4-retest; MaxKZ/exit; SOFR−SONIA twin; day/hour mining after readout.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def append_registry(results: list[dict], book: dict, receipt: str) -> None:
    ts = utc_now()
    rows = []
    for r in results + [book]:
        rows.append(
            {
                "hypothesis_id": r["hypothesis_id"],
                "status": "killed" if r["verdict"] != "PROBE_SURVIVOR" else "probe",
                "family": r.get("family"),
                "created_at_utc": ts,
                "offline_probe": {
                    "receipt_sha256": receipt,
                    "verdict": r["verdict"],
                    "metrics": r["metrics"],
                    "haircut_flat12": r["haircut_flat12"],
                    "notes": r.get("notes"),
                },
                "board": "HARD_PIVOT_W22_ARCH_MONETIZE",
                "model0": "WITHHELD" if r["verdict"] != "PROBE_SURVIVOR" else "ELIGIBLE_PENDING_PREREG",
            }
        )
    with REG.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def update_hot(payload: dict) -> None:
    status = payload["status"]
    receipt = payload["receipt_sha256"]
    dr = payload["deep_research"]["verdict"]
    qfsi = payload["qfsi_spot"]
    bullets = []
    for i, r in enumerate(payload["results"] + [payload["book"]], 1):
        m, hc = r["metrics"], r["haircut_flat12"]
        bullets.append(
            f"  {i}. `{r['hypothesis_id']}` → **{r['verdict']}** "
            f"(N={m['n']} PF={m['pf']} tpw={m['tpw']} PF@$12={hc['x1']['pf']} "
            f"x1.5={hc['x1_5']['pf']})."
        )
    new_bullet = "\n".join(
        [
            f"- **HARD PIVOT W22 ARCH-MONETIZE + DEEP RESEARCH AUTH-CHECK (2026-07-15 ~17:50 ICT) — "
            f"`R_SERIES_OHLC_CAL_IND_EVENT_DENSIFY_PAUSED` / `{status}` / `{qfsi}` / `NO_MODEL0` / "
            f"`PHASE0_STILL_CONTAMINATED` / `DEEP_RESEARCH_{dr}`.**",
            "  Dual-track: (1) ChatGPT Deep Research auth check; (2) architecture monetization offline.",
            "  **Deep Research:** browser → `https://chatgpt.com/auth/login` — **LOGIN WALL**.",
            "  No Sol/Pro/Nghiên cứu sâu UI; packet NOT submitted; do not stall.",
            "  Receipt `preflight/20260715_DEEP_RESEARCH_AUTH_CHECK_RECEIPT.json`.",
            "  **Cost-grade** still GAP (deals~11; quote days calendar-bound); keep QFSI alive; do not invent cost.",
            "  Clean PRIMARY PF@$12=1.184 tpw=3.241; RealP50 DIAGNOSTIC only — do NOT promote GOAL.",
            "  **W22 offline** after W1–W21 OHLC ALL_KILL — architecture monetization (not OHLC densify):",
            *bullets,
            f"  Receipt `{receipt}`",
            f"  `preflight/{STEM}_OFFLINE_PROBES.json`;",
            "  VN `readouts/20260715_COST_GRADE_AND_HARD_PIVOT_W22_VN_ACTION_BRIEF.md`.",
            f"  Freeze sha={receipt[:16]}… QFSI spot-check `{qfsi}`; cost freeze GAP (11 deals); "
            "login wall is Deep Research headline this board",
            "  Do **not** densify W22 / W1–W21 / H4-retest / FVG / sameday/seq rules / R10–R31.",
            "  Clean book still GOAL_SCREEN_FAIL. PRIMARY PF@$12=1.184 tpw=3.241.",
            "  Next: if ALL_KILL → new independent acquisition OR Owner ChatGPT login for Deep Research;",
            "  keep R-series paused; +$12 screen holds.",
            "  Best shelf RR2 `194548`. Cost freeze GAP. GOAL unmet.",
            "",
            "",
        ]
    )
    old = HOT.read_text(encoding="utf-8")
    header = (
        "# Hot Cache\n"
        f"Updated: 2026-07-15 ~17:50 ICT | HARD PIVOT W22 arch-monetize + Deep Research auth-check; "
        f"R-series densify PAUSED; {status}; GOAL unmet\n\n"
        "## Active Truth\n\n"
    )
    idx = old.find("## Active Truth")
    if idx >= 0:
        rest = old[idx + len("## Active Truth") :].lstrip("\n")
        HOT.write_text(header + new_bullet + rest, encoding="utf-8")
    else:
        HOT.write_text(header + new_bullet + old, encoding="utf-8")


def qfsi_spot() -> str:
    if not QFSI_HB.exists():
        return "QFSI_HB_MISSING"
    try:
        hb = json.loads(QFSI_HB.read_text(encoding="utf-8"))
        alive = hb.get("watcher_alive") or hb.get("hb_alive") or hb.get("healthy")
        return "QFSI_007_HEALTHY" if alive else "QFSI_007_UNHEALTHY"
    except Exception:
        return "QFSI_HB_UNREADABLE"


def main() -> None:
    dr = json.loads(DR_RECEIPT.read_text(encoding="utf-8"))
    rr2 = load_sleeve("A_RR2", SLEEVES["A_RR2"])
    spark = load_sleeve("B_SPARK", SLEEVES["B_SPARK"])

    rr2_trades = list(rr2["trades"])
    spark_trades = list(spark["trades"])

    rr2_pnls = [t["pnl"] for t in rr2_trades]
    rr2_base = {"metrics": metrics(rr2_pnls), "haircut_flat12": haircuts(rr2_pnls)}
    rr2_x15 = rr2_base["haircut_flat12"]["x1_5"]["pf"] or 0.0

    pooled = rr2_trades + spark_trades
    heat, heat_drop = apply_heat_priority(pooled)
    heat_pnls = [t["pnl"] for t in heat]
    clean_base = {"metrics": metrics(heat_pnls), "haircut_flat12": haircuts(heat_pnls)}
    clean_x15 = clean_base["haircut_flat12"]["x1_5"]["pf"] or 0.0

    # A — same-day flat on RR2 only
    a_kept, a_drop = apply_sameday_flat(rr2_trades)
    res_a = result_block(
        "HYP-RR2-SAMEDAY-FLAT-ARCH-001",
        "architecture_monetize_sameday_flat",
        a_kept,
        baseline_x15=rr2_x15,
        extra={
            "rule": "exit_calendar_day == entry_calendar_day",
            "n_in": len(rr2_trades),
            "n_drop_overnight": a_drop,
            "not": "weekend-flat Fri-only / MaxKZ / BE@1R / W1-W21 OHLC densify",
        },
    )

    # B — seq slot on heat-pooled clean book
    seq_in, _ = apply_heat_priority(pooled)
    b_kept, b_drop = apply_seq_slot(seq_in)
    res_b = result_block(
        "HYP-BOOK-CLEAN-SEQSLOT-001",
        "architecture_monetize_seqslot_book",
        b_kept,
        baseline_x15=clean_x15,
        extra={
            "rule": "max_1_concurrent_open_across_RR2_Spark",
            "n_in_heat": len(seq_in),
            "n_drop_overlap": b_drop,
            "heat_dropped_same_bar": heat_drop,
            "not": "R29 oneslot FX3 / MaxKZ densify / heat-pool-only",
        },
    )

    # BOOK — sameday RR2 + full Spark, heat, then seq
    rr2_sd, _ = apply_sameday_flat(rr2_trades)
    book_pool = rr2_sd + spark_trades
    book_heat, book_heat_drop = apply_heat_priority(book_pool)
    book_kept, book_seq_drop = apply_seq_slot(book_heat)
    book = result_block(
        "HYP-BOOK-SAMEDAY-SEQSLOT-APRIORI-001",
        "architecture_monetize_book_apriori",
        book_kept,
        baseline_x15=clean_x15,
        extra={
            "pipeline": "RR2_sameday -> +Spark -> heat_pool -> seq_slot",
            "heat_drop": book_heat_drop,
            "seq_drop": book_seq_drop,
        },
    )

    results = [res_a, res_b]
    all_kill = all(r["verdict"] != "PROBE_SURVIVOR" for r in results + [book])
    status = "OFFLINE_ALL_KILL__NO_MODEL0" if all_kill else "OFFLINE_HAS_SURVIVOR__MODEL0_GATED"

    payload = {
        "schema": "hard_pivot_w22_arch_monetize_offline_probes.v1",
        "created_at_utc": utc_now(),
        "stem": STEM,
        "status": status,
        "hard_constraint": "ARCH_MONETIZE_NOT_OHLC_DENSIFY__NO_W14_FVG__PLUS12_SCREEN",
        "deep_research": {
            "verdict": dr.get("verdict"),
            "submitted": dr.get("deep_research_submitted"),
            "receipt": str(DR_RECEIPT.as_posix()),
        },
        "qfsi_spot": qfsi_spot(),
        "sleeves": {
            "rr2": {k: rr2[k] for k in ("run_dir", "report_sha256", "n", "risk_matched", "trades_csv", "trade_source")},
            "spark": {k: spark[k] for k in ("run_dir", "report_sha256", "n", "risk_matched", "trades_csv", "trade_source")},
        },
        "baselines": {"rr2": rr2_base, "clean_heat": clean_base},
        "results": results,
        "book": book,
        "abandoned_pre_freeze": {
            "HYP-RR2-COSTFLOOR-RISKADMIT-001": "vacuous: all RR2 risk_usd already > 2*$12 on 0.5-lot book",
        },
        "forbidden": [
            "W1-W21 OHLC densify",
            "H4-retest densify",
            "FVG densify",
            "MaxKZ/exit densify",
            "SOFR-SONIA twin",
            "sameday/seq mining from readout",
        ],
    }
    raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    receipt = sha256_bytes(raw)
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # re-hash file bytes
    receipt = sha256_file(OUT_JSON)
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    write_docs(payload)
    append_registry(results, book, receipt)
    update_hot(payload)
    print(json.dumps({"status": status, "receipt": receipt, "results": [
        {"id": r["hypothesis_id"], "verdict": r["verdict"], "pf12": r["haircut_flat12"]["x1"]["pf"], "x15": r["haircut_flat12"]["x1_5"]["pf"], "n": r["metrics"]["n"], "tpw": r["metrics"]["tpw"]}
        for r in results + [book]
    ]}, indent=2))


if __name__ == "__main__":
    main()
