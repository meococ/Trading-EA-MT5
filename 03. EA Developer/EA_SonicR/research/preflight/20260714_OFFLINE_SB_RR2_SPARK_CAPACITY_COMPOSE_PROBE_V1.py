#!/usr/bin/env python3
"""Offline MaxKZ2-RR2 + Spark capacity compose probe (no new EA).

Universe a priori after RR2 Model 0 HIT:
  - EA_SilverBullet / 20260714_194221  (HYP-SB-MAXKZ2-RR2-FRICTION-001)
  - EA_M15SparkAsian / 20260714_193732 (HYP-SPARK-CAPACITY-3PD-001 PARK twin)

Compare to prior MaxKZ2+Spark capacity compose (192304+193732).
Tester-current only — NOT confirmed / NOT Real QFSI.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
SB_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_SilverBullet" / "20260714_194221"
SPARK_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_M15SparkAsian" / "20260714_193732"
OUT_JSON = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "20260714_OFFLINE_SB_RR2_SPARK_CAPACITY_COMPOSE_PROBE_V1.json"
)
OUT_MD = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "readouts"
    / "20260714_OFFLINE_SB_RR2_SPARK_CAPACITY_COMPOSE_PROBE_V1.md"
)


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


def extract_summary_metric(html: str, label: str) -> float | None:
    if label == "Lợi nhuận ròng":
        pat = re.compile(
            r"(?<!Tổng )Lợi nhuận ròng:</td>\s*<td[^>]*>\s*<b>([^<]+)</b>",
            re.IGNORECASE,
        )
    else:
        pat = re.compile(
            re.escape(label) + r":</td>\s*<td[^>]*>\s*<b>([^<]+)</b>",
            re.IGNORECASE,
        )
    m = pat.search(html)
    if not m:
        return None
    return parse_num(m.group(1))


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
        if tds[0].lower().startswith("thời gian") or tds[0].lower().startswith("time"):
            continue
        if not re.match(r"^\d{4}\.\d{2}\.\d{2}", tds[0]):
            continue
        side = tds[3].lower()
        if side not in ("buy", "sell"):
            continue
        deals.append(
            {
                "time": datetime.strptime(tds[0][:19], "%Y.%m.%d %H:%M:%S"),
                "deal_id": tds[1],
                "symbol": tds[2],
                "side": side,
                "direction": tds[4].lower(),
                "volume": parse_num(tds[5].split("/")[0]) if tds[5] else 0.0,
                "price": parse_num(tds[6]) if tds[6] else 0.0,
                "order": tds[7],
                "commission": parse_num(tds[8]) if len(tds) > 8 else 0.0,
                "swap": parse_num(tds[9]) if len(tds) > 9 else 0.0,
                "profit": parse_num(tds[10]) if len(tds) > 10 else 0.0,
                "comment": tds[12] if len(tds) > 12 else "",
            }
        )
    return deals


def deals_to_trades(deals: list[dict]) -> list[dict]:
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
                    "entry_time": entry["time"] if entry else d["time"],
                    "exit_time": d["time"],
                    "side": entry["side"] if entry else d["side"],
                    "pnl": pnl,
                    "symbol": d["symbol"] or (entry["symbol"] if entry else ""),
                }
            )
        else:
            if abs(d["profit"]) > 1e-12:
                trades.append(
                    {
                        "entry_time": d["time"],
                        "exit_time": d["time"],
                        "side": d["side"],
                        "pnl": d["profit"] + d["swap"] + d["commission"],
                        "symbol": d["symbol"],
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
    return (end - start).days / 7.0


def weekly_pnl_series(trades: list[dict], start: datetime, end: datetime) -> list[float]:
    buckets: dict[tuple[int, int], float] = defaultdict(float)
    for tr in trades:
        et = tr["entry_time"]
        if et < start or et > end:
            continue
        iso = et.isocalendar()
        buckets[(iso.year, iso.week)] += tr["pnl"]

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


def sleeve_from_report(run_dir: Path) -> tuple[dict, list[dict], list[dict], str]:
    report = run_dir / "report.html"
    html = decode_report(report)
    summary = {
        "net_profit": extract_summary_metric(html, "Tổng lợi nhuận ròng"),
        "gross_profit": extract_summary_metric(html, "Lợi nhuận ròng"),
        "gross_loss": extract_summary_metric(html, "Mức lỗ ròng"),
        "profit_factor": extract_summary_metric(html, "Hệ số lợi nhuận"),
        "n_trades": extract_summary_metric(html, "Tổng số giao dịch"),
        "expectancy": extract_summary_metric(html, "Mức lợi nhuận mong muốn"),
    }
    deals = parse_deals_html(report)
    trades = deals_to_trades(deals)
    return summary, deals, trades, file_sha256(report)


def main() -> int:
    window_start = datetime(2021, 1, 1)
    window_end = datetime(2025, 12, 31)
    weeks = elapsed_weeks(window_start, window_end)

    sb_summary, _sb_deals, sb_trades, sb_report_sha = sleeve_from_report(SB_DIR)
    spark_summary, _spark_deals, spark_trades, spark_report_sha = sleeve_from_report(SPARK_DIR)

    sb_n = int(sb_summary["n_trades"] or len(sb_trades))
    spark_n = int(spark_summary["n_trades"] or len(spark_trades))

    pooled_gp = (sb_summary["gross_profit"] or 0) + (spark_summary["gross_profit"] or 0)
    pooled_gl = abs(sb_summary["gross_loss"] or 0) + abs(spark_summary["gross_loss"] or 0)
    pooled_pf_report = (pooled_gp / pooled_gl) if pooled_gl > 0 else None
    pooled_net = (sb_summary["net_profit"] or 0) + (spark_summary["net_profit"] or 0)
    pooled_n = sb_n + spark_n
    pooled_tpw = pooled_n / weeks if weeks else None

    sb_pnls = [t["pnl"] for t in sb_trades]
    spark_pnls = [t["pnl"] for t in spark_trades]
    pooled_pf_trades = profit_factor(sb_pnls + spark_pnls)

    sb_entries = [t["entry_time"] for t in sb_trades]
    spark_entries = [t["entry_time"] for t in spark_trades]

    def floor_m15(dt: datetime) -> datetime:
        return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)

    exact_overlap = len(set(sb_entries) & set(spark_entries))
    same_bar = len(set(floor_m15(t) for t in sb_entries) & set(floor_m15(t) for t in spark_entries))

    sb_w = weekly_pnl_series(sb_trades, window_start, window_end)
    spark_w = weekly_pnl_series(spark_trades, window_start, window_end)
    corr = pearson(sb_w, spark_w)

    payload = {
        "probe_id": "OFFLINE_SB_RR2_SPARK_CAPACITY_COMPOSE_PROBE_V1",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "universe": {
            "sb_rr2": {
                "hypothesis_id": "HYP-SB-MAXKZ2-RR2-FRICTION-001",
                "run_id": "20260714_194221",
                "deposit": 100000,
                "n": sb_n,
                "pf": sb_summary["profit_factor"],
                "tpw": sb_n / weeks,
                "net": sb_summary["net_profit"],
                "report_sha256": sb_report_sha,
            },
            "spark_capacity": {
                "hypothesis_id": "HYP-SPARK-CAPACITY-3PD-001",
                "run_id": "20260714_193732",
                "deposit": 100000,
                "n": spark_n,
                "pf": spark_summary["profit_factor"],
                "tpw": spark_n / weeks,
                "net": spark_summary["net_profit"],
                "report_sha256": spark_report_sha,
            },
            "baseline_compose_ref": "MaxKZ2+SparkCapacity 192304+193732 PF1.352/~3.35tpw",
        },
        "pooled": {
            "n": pooled_n,
            "pf_report": pooled_pf_report,
            "pf_trades": pooled_pf_trades,
            "tpw": pooled_tpw,
            "net": pooled_net,
            "weekly_corr": corr,
            "exact_entry_overlap": exact_overlap,
            "same_m15_bar_overlap": same_bar,
        },
        "goal_screen": {
            "pf_gt_1_30": bool(pooled_pf_trades and pooled_pf_trades > 1.30),
            "tpw_2_to_5": bool(pooled_tpw and 2.0 <= pooled_tpw <= 5.0),
            "verdict": "PROBE_NEAR_GOAL_PF_AND_CADENCE_COST_UNCONFIRMED",
            "cost": "UNVERIFIED_TESTER_DEFAULT",
            "confirmed": False,
        },
        "vs_maxkz2_compose": {
            "prior_n": 873,
            "prior_pf": 1.352,
            "prior_tpw": 3.35,
            "note": "RR2 sleeve replaces MaxKZ2 RR1.5; Spark capacity unchanged",
        },
    }

    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    OUT_JSON.write_text(text, encoding="utf-8")
    result_sha = hashlib.sha256(text.encode("utf-8")).hexdigest().upper()

    md = f"""# Offline compose — RR2 + Spark capacity

Date: {payload['generated_at_ict']} ICT  
Probe: `OFFLINE_SB_RR2_SPARK_CAPACITY_COMPOSE_PROBE_V1`  
Result SHA256: `{result_sha}`

## Universe

| Sleeve | run_id | N | PF | tpw | Net |
|---|---|---:|---:|---:|---:|
| RR2 MaxKZ2 | `20260714_194221` | {sb_n} | {sb_summary['profit_factor']:.3f} | {sb_n/weeks:.2f} | {sb_summary['net_profit']:.0f} |
| Spark capacity | `20260714_193732` | {spark_n} | {spark_summary['profit_factor']:.3f} | {spark_n/weeks:.2f} | {spark_summary['net_profit']:.0f} |

## Pooled

| Metric | Value |
|---|---:|
| N | {pooled_n} |
| PF (trades) | {pooled_pf_trades:.3f} |
| tpw | {pooled_tpw:.2f} |
| Net | {pooled_net:.0f} |
| weekly corr | {corr if corr is not None else 'n/a'} |
| same-M15 overlap | {same_bar} |

Vs prior MaxKZ2+Spark capacity: PF **{pooled_pf_trades:.3f}** vs 1.352; tpw **{pooled_tpw:.2f}** vs ~3.35.

Status: `PROBE_NEAR_GOAL_PF_AND_CADENCE_COST_UNCONFIRMED`. Not GOAL / not confirmed.
"""
    OUT_MD.write_text(md, encoding="utf-8")
    print(json.dumps({"result_sha256": result_sha, "pooled": payload["pooled"]}, indent=2))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
