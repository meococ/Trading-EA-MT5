#!/usr/bin/env python3
"""Cost-ladder diagnostic — RR2 shelf 194548 + clean PRIMARY book + FVG cite.

Honest labels only:
  RESEARCH-GRADE = a priori frozen +$12 (and x1.5 stress of that screen)
  DIAGNOSTIC     = tester-only / a priori $8 / Real-QFSI partials

Do NOT claim GOAL / confirmed / freeze-eligible from DIAGNOSTIC rows.
Cost freeze still GAP (deals≪30, quote days≪90, slip MISSING≠0).
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
RUNS = ROOT / "02. AlphaFactory" / "runs"
HOT = ROOT / "04. Project Control" / "ai" / "hot.md"

STEM = "20260715_COST_LADDER_DIAGNOSTIC_RR2_CLEANBOOK"
OUT_JSON = PRE / f"{STEM}.json"
OUT_MD = READ / f"{STEM}.md"
OUT_VN = READ / "20260715_COST_LADDER_AND_HARD_PIVOT_W12_VN_ACTION_BRIEF.md"

WINDOW_START = datetime(2021, 1, 1)
WINDOW_END = datetime(2025, 12, 31)
CORR_CAP = 0.35
OVERLAP_FRAC_CAP = 0.05

# Verified from preflight artifacts (do not invent).
REAL_P50_USDJPY = 2.6167623676303218  # QFSI table canonical_usdjpy_trade_cost_p50
REAL_P90_USDJPY = 2.925143551445483  # QFSI table canonical_usdjpy_trade_cost_p90
REAL_STRESS_JSON = PRE / "20260714_COSTSTRESS_RR2_SHELF_20260714_194548_REAL_P50_W7CONT.json"
QFSI_TABLE = PRE / "20260714_BROKER_SPREAD_COST_TABLE_QFSI.json"
FVG_PROBE_JSON = PRE / "20260715_HARD_PIVOT_ENTRYSTATE_REBUILD_OFFLINE_PROBES.json"

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

# Ladder rows: (key, usd_haircut, grade, provenance_note)
LADDER = [
    ("tester_only", 0.0, "DIAGNOSTIC", "raw tester report PnL; NOT full cost"),
    (
        "real_qfsi_partial_p50",
        REAL_P50_USDJPY,
        "DIAGNOSTIC",
        "FivePercentOnline-Real PARTIAL; USDJPY unit_p50@$0.5lot; slip MISSING≠0; NOT freeze-eligible",
    ),
    (
        "real_qfsi_partial_p90",
        REAL_P90_USDJPY,
        "DIAGNOSTIC",
        "same provenance as P50; P90 spread+EURUSD commission clue; NOT freeze-eligible",
    ),
    ("apriori_8", 8.0, "DIAGNOSTIC", "a priori alternate haircut; NOT the frozen research screen"),
    ("apriori_12", 12.0, "RESEARCH-GRADE", "frozen a priori +$12 research screen (binding)"),
    ("apriori_12_x1_5", 18.0, "RESEARCH-GRADE", "a priori +$12 ×1.5 stress of research screen"),
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
                    "pnl_raw": pnl,
                    "symbol": d["symbol"] or (entry["symbol"] if entry else ""),
                }
            )
    return trades


def profit_factor(pnls: list[float]) -> float | None:
    gp = sum(x for x in pnls if x > 0)
    gl = sum(x for x in pnls if x < 0)
    if gl == 0:
        return None if gp == 0 else float("inf")
    return gp / abs(gl)


def elapsed_weeks(start: datetime, end: datetime) -> float:
    return max((end - start).days / 7.0, 1e-9)


def floor_m15(dt: datetime) -> datetime:
    return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)


def weekly_series(trades: list[dict], start: datetime, end: datetime, pnl_key: str) -> list[float]:
    buckets: dict[tuple[int, int], float] = defaultdict(float)
    for tr in trades:
        et = tr["entry_time"]
        if et < start or et > end:
            continue
        iso = et.isocalendar()
        buckets[(iso.year, iso.week)] += tr[pnl_key]
    cur = start - timedelta(days=start.weekday())
    end_week = end - timedelta(days=end.weekday())
    series = []
    while cur <= end_week:
        iso = cur.isocalendar()
        series.append(buckets.get((iso.year, iso.week), 0.0))
        cur += timedelta(days=7)
    return series


def pearson(a: list[float], b: list[float]) -> float | None:
    n = len(a)
    if n != len(b) or n < 2:
        return None
    ma = sum(a) / n
    mb = sum(b) / n
    da = [x - ma for x in a]
    db = [y - mb for y in b]
    num = sum(x * y for x, y in zip(da, db))
    den = math.sqrt(sum(x * x for x in da) * sum(y * y for y in db))
    if den == 0:
        return None
    return num / den


def load_sleeve(key: str, meta: dict) -> dict[str, Any]:
    run_dir = RUNS / meta["ea"] / meta["run_id"]
    report = run_dir / "report.html"
    if not report.exists():
        raise FileNotFoundError(report)
    trades = deals_to_trades(parse_deals_html(report), key)
    for t in trades:
        t["priority"] = meta["priority"]
        t["bar"] = floor_m15(t["entry_time"])
        t["heat_key"] = (t.get("symbol") or "UNK", t["bar"])
    return {
        "key": key,
        **meta,
        "run_dir": str(run_dir.as_posix()),
        "report_sha256": file_sha256(report),
        "n": len(trades),
        "tpw": len(trades) / elapsed_weeks(WINDOW_START, WINDOW_END),
        "trades": trades,
        "trade_source": "report_deals",
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


def metrics_at(pnls: list[float], haircut: float) -> dict[str, Any]:
    cut = [p - haircut for p in pnls]
    pf = profit_factor(cut)
    n = len(cut)
    net = sum(cut)
    return {
        "n": n,
        "pf": None if pf is None else round(float(pf), 4),
        "net": round(net, 2),
        "exp": round(net / n, 4) if n else None,
        "tpw": round(n / elapsed_weeks(WINDOW_START, WINDOW_END), 4) if n else None,
        "haircut_usd": haircut,
    }


def goal_screen_flags(m: dict[str, Any], grade: str) -> dict[str, Any]:
    pf = m["pf"] or 0.0
    tpw = m["tpw"] or 0.0
    pf_ok = pf > 1.30
    tpw_ok = 2.0 <= tpw <= 5.0
    return {
        "pf_gt_1_30": pf_ok,
        "tpw_2_to_5": tpw_ok,
        "would_pass_goal_shape": bool(pf_ok and tpw_ok),
        "claim_allowed": False if grade == "DIAGNOSTIC" else False,
        "note": "DIAGNOSTIC rows never claim GOAL; RESEARCH-GRADE +$12 still GOAL_SCREEN only if pf&tpw pass — clean book historically fails pf>1.30",
    }


def ladder_object(name: str, pnls: list[float], extra: dict | None = None) -> dict[str, Any]:
    rows = []
    for key, hc, grade, note in LADDER:
        m = metrics_at(pnls, hc)
        rows.append(
            {
                "ladder_key": key,
                "grade": grade,
                "provenance": note,
                "metrics": m,
                "goal_shape": goal_screen_flags(m, grade),
            }
        )
    out = {"object": name, "n_raw": len(pnls), "ladder": rows}
    if extra:
        out.update(extra)
    return out


def load_prior_real_stress() -> dict[str, Any]:
    if not REAL_STRESS_JSON.exists():
        return {"present": False}
    data = json.loads(REAL_STRESS_JSON.read_text(encoding="utf-8"))
    return {
        "present": True,
        "path": str(REAL_STRESS_JSON.as_posix()),
        "sha256": file_sha256(REAL_STRESS_JSON),
        "cost_assumption": data.get("cost_assumption"),
        "verdict": data.get("verdict"),
        "scenarios": data.get("scenarios"),
        "honesty": [
            "report_only_cost_stress",
            "PARTIAL_REAL_CAPTURE",
            "slippage_MISSING_neq_0",
            "NOT_FULL_QFSI",
            "NOT_CONFIRMED_COST_PROVENANCE",
        ],
    }


def load_fvg_cite() -> dict[str, Any]:
    """Cite existing offline FVG haircuts; cannot rebuild Real P50 without trade list."""
    if not FVG_PROBE_JSON.exists():
        return {"present": False, "reason": "probe json missing"}
    data = json.loads(FVG_PROBE_JSON.read_text(encoding="utf-8"))
    row = None
    for r in data.get("results", data.get("probes", [])):
        if r.get("hypothesis_id") == "HYP-SB-FVG-RETEST-ACCEPT-DELAY-001":
            row = r
            break
    if row is None:
        # fallback scan any list-like
        for key in ("results", "probes", "objects"):
            for r in data.get(key, []) or []:
                if "FVG" in str(r.get("hypothesis_id", "")):
                    row = r
                    break
    if row is None:
        return {"present": False, "reason": "FVG row not found"}
    m = row.get("metrics", {})
    hc = row.get("haircuts", {})
    return {
        "present": True,
        "hypothesis_id": row.get("hypothesis_id"),
        "grade_note": "Prior offline probe under a priori +$12 — RESEARCH-GRADE screen numbers only; densify FORBIDDEN; Real/QFSI ladder NOT reconstructable (no trade list).",
        "metrics": m,
        "haircuts_apriori12": hc,
        "verdict": row.get("verdict"),
        "ladder_reconstructable": False,
        "source_json": str(FVG_PROBE_JSON.as_posix()),
        "source_sha256": file_sha256(FVG_PROBE_JSON),
    }


def main() -> None:
    sleeves = {k: load_sleeve(k, v) for k, v in SLEEVES.items()}
    rr2 = sleeves["A_RR2"]
    spark = sleeves["B_SPARK"]

    rr2_ladder = ladder_object(
        "RR2_SHELF_194548",
        [t["pnl_raw"] for t in rr2["trades"]],
        {
            "run_id": rr2["run_id"],
            "hypothesis_id": rr2["hypothesis_id"],
            "report_sha256": rr2["report_sha256"],
            "tpw_raw": round(rr2["tpw"], 4),
        },
    )

    # PRIMARY clean book: pool after heat at each haircut independently for PF,
    # but heat uses raw priority (same as freeze) — apply heat on raw trades once.
    pooled, dropped = apply_heat_priority(rr2["trades"] + spark["trades"])
    book_ladder = ladder_object(
        "CLEAN_BOOK_PRIMARY_RR2SPARK",
        [t["pnl_raw"] for t in pooled],
        {
            "sleeves": ["A_RR2", "B_SPARK"],
            "dropped_heat": dropped,
            "pair_caps": {
                "weekly_corr_raw": pearson(
                    weekly_series(rr2["trades"], WINDOW_START, WINDOW_END, "pnl_raw"),
                    weekly_series(spark["trades"], WINDOW_START, WINDOW_END, "pnl_raw"),
                ),
                "overlap_frac": (
                    len({t["bar"] for t in rr2["trades"]} & {t["bar"] for t in spark["trades"]})
                    / max(1, min(len({t["bar"] for t in rr2["trades"]}), len({t["bar"] for t in spark["trades"]})))
                ),
                "corr_cap": CORR_CAP,
                "overlap_cap": OVERLAP_FRAC_CAP,
            },
        },
    )
    # round corr
    if book_ladder["pair_caps"]["weekly_corr_raw"] is not None:
        book_ladder["pair_caps"]["weekly_corr_raw"] = round(book_ladder["pair_caps"]["weekly_corr_raw"], 4)
    book_ladder["pair_caps"]["overlap_frac"] = round(book_ladder["pair_caps"]["overlap_frac"], 4)

    prior_real = load_prior_real_stress()
    fvg = load_fvg_cite()
    qfsi_sha = file_sha256(QFSI_TABLE) if QFSI_TABLE.exists() else None

    # Decision memo from numbers
    rr2_by = {r["ladder_key"]: r for r in rr2_ladder["ladder"]}
    book_by = {r["ladder_key"]: r for r in book_ladder["ladder"]}
    decision = {
        "binding_research_screen": "apriori_12",
        "rr2_pf_tester": rr2_by["tester_only"]["metrics"]["pf"],
        "rr2_pf_real_p50": rr2_by["real_qfsi_partial_p50"]["metrics"]["pf"],
        "rr2_pf_apriori_8": rr2_by["apriori_8"]["metrics"]["pf"],
        "rr2_pf_apriori_12": rr2_by["apriori_12"]["metrics"]["pf"],
        "book_pf_tester": book_by["tester_only"]["metrics"]["pf"],
        "book_pf_real_p50": book_by["real_qfsi_partial_p50"]["metrics"]["pf"],
        "book_pf_apriori_8": book_by["apriori_8"]["metrics"]["pf"],
        "book_pf_apriori_12": book_by["apriori_12"]["metrics"]["pf"],
        "book_tpw": book_by["apriori_12"]["metrics"]["tpw"],
        "verdict_en": (
            "$12 remains the binding RESEARCH-GRADE screen. DIAGNOSTIC Real/QFSI partials "
            f"(~${REAL_P50_USDJPY:.2f} P50) show RR2/clean-book PF much higher than under $12, "
            "so $12 is punitive vs thin Real sample — BUT freeze still GAP (11 deals, ≪90 quote days, "
            "slip MISSING). Do NOT relax GOAL/confirmed from DIAGNOSTIC. Keep +$12 as kill/survive "
            "screen until research-grade cost freeze exists."
        ),
    }

    payload = {
        "schema_version": "sonic_cost_ladder_diagnostic.v1",
        "generated_at_utc": utc_now(),
        "honesty": [
            "DIAGNOSTIC_ROWS_NOT_GOAL",
            "DIAGNOSTIC_ROWS_NOT_CONFIRMED",
            "COST_FREEZE_STILL_GAP",
            "REAL_QFSI_PARTIAL_ONLY",
            "SLIPPAGE_MISSING_NEQ_0",
            "FVG_LADDER_NOT_RECONSTRUCTABLE",
        ],
        "cost_sources": {
            "real_p50_usdjpy": REAL_P50_USDJPY,
            "real_p90_usdjpy": REAL_P90_USDJPY,
            "qfsi_table": str(QFSI_TABLE.as_posix()) if QFSI_TABLE.exists() else None,
            "qfsi_table_sha256": qfsi_sha,
            "prior_rr2_real_stress": prior_real,
        },
        "objects": [rr2_ladder, book_ladder],
        "fvg_near_miss_cite": fvg,
        "decision": decision,
    }
    raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    receipt = sha256_bytes(raw)
    payload["receipt_sha256"] = receipt
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def row_md(r: dict) -> str:
        m = r["metrics"]
        g = r["goal_shape"]
        return (
            f"| `{r['ladder_key']}` | **{r['grade']}** | {m['haircut_usd']:.4f} | "
            f"{m['pf']} | {m['tpw']} | {m['net']} | "
            f"{'Y' if g['would_pass_goal_shape'] else 'N'} | {r['provenance'][:60]} |"
        )

    lines = [
        "# Cost-ladder diagnostic — RR2 `194548` + clean PRIMARY + FVG cite",
        "",
        f"Generated: {payload['generated_at_utc']}",
        f"Receipt SHA256: `{receipt}`",
        "",
        "## Honesty",
        "",
        "- DIAGNOSTIC ≠ GOAL / confirmed / freeze-eligible.",
        "- RESEARCH-GRADE = a priori +$12 (binding kill/survive screen) and ×1.5 stress.",
        f"- Real/QFSI partial USDJPY trade-cost P50=`{REAL_P50_USDJPY:.4f}` P90=`{REAL_P90_USDJPY:.4f}` "
        "(verified from QFSI table + prior W7CONT stress JSON).",
        "- Cost freeze still GAP (live deals≈11; quote days≪90; slip MISSING≠0).",
        "",
        "## RR2 shelf `194548`",
        "",
        "| Ladder | Grade | $/trade | PF | tpw | net | goal-shape? | Note |",
        "|---|---|---:|---:|---:|---:|:---:|---|",
    ]
    lines.extend(row_md(r) for r in rr2_ladder["ladder"])
    lines += [
        "",
        "## Clean book PRIMARY (RR2+Spark, heat-pooled)",
        "",
        f"Dropped heat: {dropped}. Corr(raw)={book_ladder['pair_caps']['weekly_corr_raw']} "
        f"overlap={book_ladder['pair_caps']['overlap_frac']}.",
        "",
        "| Ladder | Grade | $/trade | PF | tpw | net | goal-shape? | Note |",
        "|---|---|---:|---:|---:|---:|:---:|---|",
    ]
    lines.extend(row_md(r) for r in book_ladder["ladder"])
    lines += [
        "",
        "## FVG near-miss (cite only)",
        "",
    ]
    if fvg.get("present"):
        lines += [
            f"- `{fvg['hypothesis_id']}` N={fvg['metrics'].get('n')} PF={fvg['metrics'].get('pf')} "
            f"tpw={fvg['metrics'].get('tpw')} PF@$12={fvg['haircuts_apriori12'].get('x1', {}).get('pf')} "
            f"x1.5={fvg['haircuts_apriori12'].get('x1_5', {}).get('pf')} → {fvg.get('verdict')}",
            f"- {fvg['grade_note']}",
            "- Densify FORBIDDEN.",
        ]
    else:
        lines.append(f"- FVG cite unavailable: {fvg.get('reason')}")
    lines += [
        "",
        "## Decision",
        "",
        decision["verdict_en"],
        "",
        f"JSON: `preflight/{OUT_JSON.name}`",
        "",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": receipt, "decision": decision, "out": str(OUT_JSON)}, indent=2))


if __name__ == "__main__":
    main()
