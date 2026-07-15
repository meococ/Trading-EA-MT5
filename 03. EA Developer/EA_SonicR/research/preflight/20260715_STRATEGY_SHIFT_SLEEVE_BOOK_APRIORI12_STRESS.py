#!/usr/bin/env python3
"""STRATEGY SHIFT Track A — offline a priori +$12 sleeve stress (NOT Phase-0).

Universe and caps are frozen in:
  readouts/20260715_STRATEGY_SHIFT_PHASE0_SLEEVE_UNIVERSE_FREEZE.md

This script only evaluates the predeclared PRIMARY and EXTENDED books.
No sleeve substitution after metrics. No Model 0. Tester cost ≠ Real QFSI.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(r"d:\Trading EA MT5")
PRE = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "preflight"
READ = ROOT / "03. EA Developer" / "EA_SonicR" / "research" / "readouts"
RUNS = ROOT / "02. AlphaFactory" / "runs"

HAIRCUT = 12.0
CORR_CAP = 0.35
OVERLAP_FRAC_CAP = 0.05
WINDOW_START = datetime(2021, 1, 1)
WINDOW_END = datetime(2025, 12, 31)

# Frozen a priori (do not reorder by PF).
SLEEVES = {
    "A_RR2": {
        "hypothesis_id": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
        "run_id": "20260714_194548",
        "ea": "EA_SilverBullet",
        "priority": 1,
        "books": ("PRIMARY", "EXTENDED"),
    },
    "B_SPARK": {
        "hypothesis_id": "HYP-SPARK-CAPACITY-3PD-001",
        "run_id": "20260714_193358",
        "ea": "EA_M15SparkAsian",
        "priority": 2,
        "books": ("PRIMARY", "EXTENDED"),
    },
    "C_ITSM": {
        "hypothesis_id": "HYP-ITSM-PULLBACK-M15-001",
        "run_id": "20260714_003920",
        "ea": "EA_ITSM",
        "priority": 3,
        "books": ("EXTENDED",),
    },
}
EXCLUDED = {
    "MaxKZ2_192304": {
        "hypothesis_id": "HYP-SB-MAXKZ2-DENSITY-002",
        "run_id": "20260714_192304",
        "reason": "MAXKZ2_REAL_PATH_FAIL_CLOSED_A_PRIORI",
    },
    "Spark_193732": {
        "hypothesis_id": "HYP-SPARK-CAPACITY-3PD-001",
        "run_id": "20260714_193732",
        "reason": "PHASE0_NAMED_193358_TWIN_EXCLUDED_A_PRIORI",
    },
}

OUT_JSON = PRE / "20260715_STRATEGY_SHIFT_SLEEVE_BOOK_APRIORI12_STRESS.json"
OUT_MD = READ / "20260715_STRATEGY_SHIFT_SLEEVE_BOOK_APRIORI12_STRESS.md"
FREEZE_MD = READ / "20260715_STRATEGY_SHIFT_PHASE0_SLEEVE_UNIVERSE_FREEZE.md"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


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


def load_px6_trades(run_dir: Path, sleeve: str) -> list[dict] | None:
    candidates = list((run_dir / "logs").glob("*PX6_Trades*.csv")) + list(
        (run_dir / "analysis" / "logs").glob("*PX6_Trades*.csv")
    )
    if not candidates:
        return None
    path = max(candidates, key=lambda p: p.stat().st_mtime)
    trades: list[dict] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            # Prefer final closed rows if present.
            status = (row.get("status") or row.get("Status") or "").lower()
            if status and status not in ("closed", "close", "done", "filled"):
                continue
            entry_s = row.get("entry_time") or row.get("EntryTime") or row.get("open_time")
            exit_s = row.get("exit_time") or row.get("ExitTime") or row.get("close_time")
            pnl_s = row.get("pnl") or row.get("profit") or row.get("net_pnl") or row.get("Profit")
            if not entry_s or pnl_s is None:
                continue
            try:
                entry = datetime.strptime(str(entry_s)[:19].replace("-", ".").replace("T", " "), "%Y.%m.%d %H:%M:%S")
            except Exception:
                try:
                    entry = datetime.fromisoformat(str(entry_s).replace("Z", ""))
                except Exception:
                    continue
            exit_t = entry
            if exit_s:
                try:
                    exit_t = datetime.strptime(
                        str(exit_s)[:19].replace("-", ".").replace("T", " "), "%Y.%m.%d %H:%M:%S"
                    )
                except Exception:
                    try:
                        exit_t = datetime.fromisoformat(str(exit_s).replace("Z", ""))
                    except Exception:
                        exit_t = entry
            try:
                pnl = float(str(pnl_s).replace(",", ""))
            except Exception:
                continue
            trades.append(
                {
                    "sleeve": sleeve,
                    "entry_time": entry,
                    "exit_time": exit_t,
                    "side": (row.get("side") or row.get("Side") or "").lower(),
                    "pnl_raw": pnl,
                    "symbol": row.get("symbol") or row.get("Symbol") or "",
                    "source": path.name,
                }
            )
    return trades or None


def floor_m15(dt: datetime) -> datetime:
    return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)


def profit_factor(pnls: list[float]) -> float | None:
    gp = sum(x for x in pnls if x > 0)
    gl = sum(x for x in pnls if x < 0)
    if gl == 0:
        return None if gp == 0 else float("inf")
    return gp / abs(gl)


def elapsed_weeks(start: datetime, end: datetime) -> float:
    return max((end - start).days / 7.0, 1e-9)


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
    trades = load_px6_trades(run_dir, key)
    source = "px6"
    if not trades:
        trades = deals_to_trades(parse_deals_html(report), key)
        source = "report_deals"
    for t in trades:
        t["pnl_haircut"] = t["pnl_raw"] - HAIRCUT
        t["priority"] = meta["priority"]
        t["bar"] = floor_m15(t["entry_time"])
        t["heat_key"] = (t.get("symbol") or "UNK", t["bar"])
    return {
        "key": key,
        **meta,
        "run_dir": str(run_dir.as_posix()),
        "report_sha256": file_sha256(report),
        "n": len(trades),
        "pf_raw": profit_factor([t["pnl_raw"] for t in trades]),
        "pf_haircut": profit_factor([t["pnl_haircut"] for t in trades]),
        "tpw": len(trades) / elapsed_weeks(WINDOW_START, WINDOW_END),
        "net_raw": sum(t["pnl_raw"] for t in trades),
        "net_haircut": sum(t["pnl_haircut"] for t in trades),
        "trades": trades,
        "trade_source": source,
    }


def apply_heat_priority(trades: list[dict]) -> tuple[list[dict], int]:
    """Keep highest-priority trade per (symbol, M15 bar); drop others."""
    best: dict[tuple, dict] = {}
    dropped = 0
    # Stable: process high priority first so ties keep first-seen high prio.
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


def pairwise_overlap_frac(a: list[dict], b: list[dict]) -> float:
    if not a or not b:
        return 0.0
    sa = {t["bar"] for t in a}
    sb = {t["bar"] for t in b}
    inter = len(sa & sb)
    return inter / min(len(sa), len(sb))


def evaluate_book(name: str, sleeve_payloads: list[dict]) -> dict[str, Any]:
    weeks = elapsed_weeks(WINDOW_START, WINDOW_END)
    # Naive union then heat filter.
    all_trades = []
    for s in sleeve_payloads:
        all_trades.extend(s["trades"])
    filtered, dropped = apply_heat_priority(all_trades)
    pnls = [t["pnl_haircut"] for t in filtered]
    pf = profit_factor(pnls)
    n = len(filtered)
    tpw = n / weeks

    # Pairwise caps after heat filter, rebuilt per sleeve membership.
    by_sleeve: dict[str, list[dict]] = defaultdict(list)
    for t in filtered:
        by_sleeve[t["sleeve"]].append(t)

    pair_stats = []
    corr_fail = False
    overlap_fail = False
    keys = [s["key"] for s in sleeve_payloads]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            ka, kb = keys[i], keys[j]
            ta, tb = by_sleeve.get(ka, []), by_sleeve.get(kb, [])
            corr = pearson(
                weekly_series(ta, WINDOW_START, WINDOW_END, "pnl_haircut"),
                weekly_series(tb, WINDOW_START, WINDOW_END, "pnl_haircut"),
            )
            ov = pairwise_overlap_frac(ta, tb)
            if corr is not None and corr > CORR_CAP:
                corr_fail = True
            if ov > OVERLAP_FRAC_CAP:
                overlap_fail = True
            pair_stats.append(
                {
                    "a": ka,
                    "b": kb,
                    "weekly_corr": corr,
                    "same_m15_overlap_frac": ov,
                    "corr_cap_pass": corr is None or corr <= CORR_CAP,
                    "overlap_cap_pass": ov <= OVERLAP_FRAC_CAP,
                }
            )

    goal_pf = bool(pf is not None and pf > 1.30)
    goal_tpw = bool(2.0 <= tpw <= 5.0)
    caps_ok = (not corr_fail) and (not overlap_fail)
    if goal_pf and goal_tpw and caps_ok:
        verdict = "DIAGNOSTIC_PASS_RESEARCH_SCREEN__NOT_CONFIRMED__NOT_PHASE0"
    elif caps_ok and (goal_pf or goal_tpw):
        verdict = "DIAGNOSTIC_PARTIAL__CAPS_OK__GOAL_SCREEN_FAIL"
    elif not caps_ok:
        verdict = "DIAGNOSTIC_CAP_FAIL"
    else:
        verdict = "DIAGNOSTIC_FAIL_GOAL_SCREEN"

    return {
        "book": name,
        "sleeves": [
            {
                "key": s["key"],
                "run_id": s["run_id"],
                "hypothesis_id": s["hypothesis_id"],
                "n": s["n"],
                "pf_raw": s["pf_raw"],
                "pf_haircut": s["pf_haircut"],
                "tpw": s["tpw"],
                "net_haircut": s["net_haircut"],
                "trade_source": s["trade_source"],
                "report_sha256": s["report_sha256"],
            }
            for s in sleeve_payloads
        ],
        "pooled_after_heat": {
            "n": n,
            "dropped_heat": dropped,
            "pf_haircut": pf,
            "tpw": tpw,
            "net_haircut": sum(pnls),
        },
        "pair_caps": pair_stats,
        "caps": {
            "haircut_usd": HAIRCUT,
            "corr_cap": CORR_CAP,
            "overlap_frac_cap": OVERLAP_FRAC_CAP,
            "corr_fail": corr_fail,
            "overlap_fail_after_heat": overlap_fail,
            "caps_pass": caps_ok,
        },
        "goal_screen": {
            "pf_gt_1_30_after_12": goal_pf,
            "tpw_2_to_5": goal_tpw,
            "verdict": verdict,
            "confirmed": False,
            "phase0_ceremony": False,
            "cost": "APRIORI_HAIRCUT_12_TESTER_PROXY_NOT_QFSI",
        },
    }


def main() -> int:
    if not FREEZE_MD.exists():
        print("FATAL: freeze memo missing — refuse to compute metrics", file=sys.stderr)
        return 2

    loaded = {}
    for key, meta in SLEEVES.items():
        loaded[key] = load_sleeve(key, meta)

    primary = evaluate_book("PRIMARY_BOOK", [loaded["A_RR2"], loaded["B_SPARK"]])
    extended = evaluate_book(
        "EXTENDED_BOOK", [loaded["A_RR2"], loaded["B_SPARK"], loaded["C_ITSM"]]
    )

    payload = {
        "schema_version": "strategy_shift_sleeve_book_apriori12_stress.v1",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "DIAGNOSTIC_OFFLINE_NOT_PHASE0",
        "freeze_memo": str(FREEZE_MD.as_posix()),
        "freeze_sha256": file_sha256(FREEZE_MD),
        "excluded_a_priori": EXCLUDED,
        "window": {"start": WINDOW_START.isoformat(), "end": WINDOW_END.isoformat()},
        "books": {"PRIMARY_BOOK": primary, "EXTENDED_BOOK": extended},
        "non_claims": [
            "not_phase0_clearance",
            "not_confirmed",
            "not_goal",
            "not_portfolio_sleeve",
            "no_sleeve_rerank_after_metrics",
            "no_invented_spreads",
        ],
    }

    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    OUT_JSON.write_text(text, encoding="utf-8")
    result_sha = hashlib.sha256(text.encode("utf-8")).hexdigest().upper()

    def fmt_book(b: dict) -> str:
        lines = [
            f"### {b['book']}",
            "",
            "| Sleeve | run_id | N | PF raw | PF @$12 | tpw |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for s in b["sleeves"]:
            lines.append(
                f"| {s['key']} | `{s['run_id']}` | {s['n']} | "
                f"{s['pf_raw']:.4f} | {s['pf_haircut']:.4f} | {s['tpw']:.3f} |"
            )
        p = b["pooled_after_heat"]
        lines += [
            "",
            f"- Pooled N (after heat): **{p['n']}** (dropped {p['dropped_heat']})",
            f"- Pooled PF @$12: **{p['pf_haircut']:.4f}**",
            f"- Pooled tpw: **{p['tpw']:.3f}**",
            f"- Caps pass: **{b['caps']['caps_pass']}** (corr_fail={b['caps']['corr_fail']}, "
            f"overlap_fail={b['caps']['overlap_fail_after_heat']})",
            f"- Verdict: `{b['goal_screen']['verdict']}`",
            "",
            "Pair caps:",
            "",
            "| Pair | weekly corr | overlap frac |",
            "|---|---:|---:|",
        ]
        for pr in b["pair_caps"]:
            corr = "n/a" if pr["weekly_corr"] is None else f"{pr['weekly_corr']:.4f}"
            lines.append(
                f"| {pr['a']}×{pr['b']} | {corr} | {pr['same_m15_overlap_frac']:.4f} |"
            )
        lines.append("")
        return "\n".join(lines)

    md = f"""# STRATEGY SHIFT — Track A offline a priori +$12 sleeve stress

Date: {payload['generated_at_ict']} ICT  
Status: `DIAGNOSTIC_OFFLINE_NOT_PHASE0`  
Result SHA256: `{result_sha}`  
Freeze: `{FREEZE_MD.name}` (SHA `{payload['freeze_sha256'][:16]}…`)

## Exclusions (a priori; pre-metrics)

- MaxKZ2 `20260714_192304` — `MAXKZ2_REAL_PATH_FAIL_CLOSED`
- Spark twin `20260714_193732` — Phase-0 named `193358`

## Results

{fmt_book(primary)}
{fmt_book(extended)}

## Non-claims

Not Phase-0 clearance. Not confirmed. Not GOAL. No Model 0. Tester +$12 proxy ≠ QFSI.
No sleeve cherry-pick after seeing these numbers.
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(json.dumps({"result_sha256": result_sha, "primary": primary["goal_screen"], "extended": extended["goal_screen"]}, indent=2))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
