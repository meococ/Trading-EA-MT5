#!/usr/bin/env python3
"""Offline SilverBullet A1 + SparkAsian portfolio composition probe (no new EA).

Frozen universe = Phase 0 exact identity already bound in hot.md /
HYP-PORTFOLIO-COMPOSE-001 attach (not PF-ranked after Spark+ITSM fail):
  - EA_SilverBullet / 20260714_192304  (HYP-SB-WEEKEND-FLAT-001 challenger A1)
  - EA_M15SparkAsian / 20260714_002614 (HYP-SPARK-ASIAN-M15-001 twin)

Selection rule: Phase 0 subset IDs only. ITSM / LondonORB / USBILL excluded.
Tester-current cost only — NOT confirmed / NOT Real QFSI.
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
SB_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_SilverBullet" / "20260714_192304"
SPARK_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_M15SparkAsian" / "20260714_002614"
OUT_JSON = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "20260714_OFFLINE_SB_MAXKZ2_SPARK_COMPOSE_PROBE_V1.json"
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


def count_near(a: list[datetime], b: list[datetime], minutes: int) -> int:
    b_sorted = sorted(b)
    near = 0
    for t in a:
        for u in b_sorted:
            if abs((t - u).total_seconds()) <= minutes * 60:
                near += 1
                break
            if u > t + timedelta(minutes=minutes):
                break
    return near


def main() -> int:
    window_start = datetime(2021, 1, 1)
    window_end = datetime(2025, 12, 31)
    weeks = elapsed_weeks(window_start, window_end)

    sb_summary, sb_deals, sb_trades, sb_report_sha = sleeve_from_report(SB_DIR)
    spark_summary, spark_deals, spark_trades, spark_report_sha = sleeve_from_report(SPARK_DIR)

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
    bar_overlap = len({floor_m15(t) for t in sb_entries} & {floor_m15(t) for t in spark_entries})
    day_overlap = len({t.date() for t in sb_entries} & {t.date() for t in spark_entries})
    sb_near_spark_60 = count_near(sb_entries, spark_entries, 60)
    spark_near_sb_60 = count_near(spark_entries, sb_entries, 60)

    sb_weekly = weekly_pnl_series(sb_trades, window_start, window_end)
    spark_weekly = weekly_pnl_series(spark_trades, window_start, window_end)
    corr_weekly = pearson(sb_weekly, spark_weekly)

    sb_active = [1 if abs(x) > 1e-12 else 0 for x in sb_weekly]
    spark_active = [1 if abs(x) > 1e-12 else 0 for x in spark_weekly]
    both_active = sum(1 for a, b in zip(sb_active, spark_active) if a and b)
    sb_only = sum(1 for a, b in zip(sb_active, spark_active) if a and not b)
    spark_only = sum(1 for a, b in zip(sb_active, spark_active) if b and not a)

    sb_tpw = sb_n / weeks
    spark_tpw = spark_n / weeks

    cadence_ok = pooled_tpw is not None and 2.0 <= pooled_tpw <= 5.0
    pf_ok = pooled_pf_report is not None and pooled_pf_report > 1.30
    if cadence_ok and pf_ok:
        verdict = "PROBE_NEAR_GOAL_CADENCE_AND_PF_BUT_COST_UNCONFIRMED"
        worth_coding = True
        note = (
            "Pooled cadence and PF both clear research bars on tester-current cost; "
            "still NOT confirmed without Real QFSI. Portfolio sleeve coding is worth "
            "considering only as research scaffold after Owner freeze — not promotion."
        )
    elif cadence_ok and not pf_ok:
        verdict = "FAIL_POOLED_PF_BELOW_1_30_CADENCE_OK"
        worth_coding = False
        note = (
            "Pooled elapsed-calendar cadence lands in 2-5/wk, but pooled PF stays "
            "below 1.30. Coding a combined portfolio EA sleeve is NOT worth it from "
            "this probe alone."
        )
    elif pf_ok and not cadence_ok:
        verdict = "FAIL_POOLED_CADENCE_OUTSIDE_2_5"
        worth_coding = False
        note = "Pooled PF clears 1.30 but cadence does not land in 2-5/wk."
    else:
        verdict = "FAIL_BOTH_CADENCE_AND_PF"
        worth_coding = False
        note = "Neither pooled cadence nor pooled PF meets GOAL research bars."

    result = {
        "probe_id": "OFFLINE_SB_MAXKZ2_SPARK_COMPOSE_PROBE_V1",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "gpt_status": "GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY",
        "universe_frozen": {
            "members": [
                {
                    "ea": "EA_SilverBullet",
                    "run_id": "20260714_192304",
                    "hypothesis_id": "HYP-SB-WEEKEND-FLAT-001",
                    "role": "weekend_flat_challenger_A1",
                    "symbol": "USDJPY",
                    "period": "M15",
                    "path": str(SB_DIR),
                    "report_sha256": sb_report_sha,
                },
                {
                    "ea": "EA_M15SparkAsian",
                    "run_id": "20260714_002614",
                    "hypothesis_id": "HYP-SPARK-ASIAN-M15-001",
                    "role": "phase0_twin_of_002821",
                    "symbol": "USDJPY",
                    "period": "M15",
                    "path": str(SPARK_DIR),
                    "report_sha256": spark_report_sha,
                    "authoritative_twin_run_id": "20260714_002821",
                    "expected_report_sha256_manifest": (
                        "7CAE7A9332B551FE58360E2B89022835F23E7706345ED2E7DC02F5122D80001A"
                    ),
                },
            ],
            "selection_rule": (
                "Phase 0 HYP-PORTFOLIO-COMPOSE-001 exact subset IDs already bound "
                "(SB 002505 + Spark 002614); NOT a post-hoc swap after Spark+ITSM fail"
            ),
            "excluded_explicitly": [
                "EA_ITSM",
                "EA_M15LondonORB",
                "EA_UsBillSlopeBasket",
                "any other shelf EA",
            ],
            "phase0_subset_universe_sha256": (
                "B1A04F9C1CD7E2A7B0C8B6463AE4438A52A45DD5645046B5AA682A2F69D4D138"
            ),
        },
        "window": {
            "from": "2021.01.01",
            "to": "2025.12.31",
            "elapsed_calendar_days": (window_end - window_start).days,
            "elapsed_calendar_weeks": weeks,
            "overlap": "full identical tester window",
        },
        "cost_caveat": {
            "status": "tester_current_spread_only",
            "confirmed": False,
            "broker_observed": "MetaQuotes-Demo",
            "fivepercent_real_login_present": False,
            "note": "Missing/zero commission fields do not mean cost=0. Not Real QFSI.",
        },
        "sleeve_metrics": {
            "sb_a1": {
                **sb_summary,
                "trades_parsed": len(sb_trades),
                "deals_parsed": len(sb_deals),
                "trades_per_week_elapsed": sb_tpw,
                "trade_level_pf": profit_factor(sb_pnls),
            },
            "spark": {
                **spark_summary,
                "trades_parsed": len(spark_trades),
                "deals_parsed": len(spark_deals),
                "trades_per_week_elapsed": spark_tpw,
                "trade_level_pf": profit_factor(spark_pnls),
            },
        },
        "pooled": {
            "n_trades": pooled_n,
            "net_profit": pooled_net,
            "gross_profit": pooled_gp,
            "gross_loss_abs": pooled_gl,
            "pf_from_report_gross": pooled_pf_report,
            "pf_from_trade_pnls": pooled_pf_trades,
            "trades_per_week_elapsed": pooled_tpw,
            "expectancy_pooled_naive": (pooled_net / pooled_n) if pooled_n else None,
        },
        "correlation_overlap": {
            "exact_same_entry_timestamp_count": exact_overlap,
            "same_m15_bar_entry_overlap_count": bar_overlap,
            "same_calendar_day_entry_overlap_count": day_overlap,
            "sb_entries_near_spark_within_60m": sb_near_spark_60,
            "spark_entries_near_sb_within_60m": spark_near_sb_60,
            "sb_entry_count": len(sb_entries),
            "spark_entry_count": len(spark_entries),
            "weekly_pnl_pearson": corr_weekly,
            "weeks_both_active": both_active,
            "weeks_sb_only": sb_only,
            "weeks_spark_only": spark_only,
            "weekly_series_len": len(sb_weekly),
        },
        "goal_screen_research_only": {
            "need_pooled_tpw_2_to_5": cadence_ok,
            "need_pooled_pf_gt_1_30": pf_ok,
            "verdict": verdict,
            "worth_coding_portfolio_ea_sleeve_next": worth_coding,
            "note": note,
        },
        "path_a_blockers": {
            "real_qfsi": "BLOCKED_NO_FIVEPERCENTONLINE_REAL_LOGIN",
            "phase0_prereg_freeze": "BLOCKED_NOT_READY_FOR_PREREG_FREEZE",
            "matched_control_disabled_signal": (
                "MATCHED_CONTROL_PREREG_GAP_DISABLED_SIGNAL_OR_RANDOM_HOUR"
            ),
        },
    }

    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    print(f"\nWrote {OUT_JSON}", file=sys.stderr)
    print(f"RESULT_SHA256={file_sha256(OUT_JSON)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
