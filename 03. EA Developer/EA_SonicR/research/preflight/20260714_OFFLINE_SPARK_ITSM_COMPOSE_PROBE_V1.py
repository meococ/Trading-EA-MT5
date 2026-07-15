#!/usr/bin/env python3
"""Offline SparkAsian + ITSM portfolio composition probe (no new EA).

Frozen universe (Owner task):
  - EA_M15SparkAsian / 20260714_002614
  - EA_ITSM / 20260714_003920
No PF-ranked cherry-pick of other EAs.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(r"d:\Trading EA MT5")
SPARK_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_M15SparkAsian" / "20260714_002614"
ITSM_DIR = ROOT / "02. AlphaFactory" / "runs" / "EA_ITSM" / "20260714_003920"
OUT_JSON = (
    ROOT
    / "03. EA Developer"
    / "EA_SonicR"
    / "research"
    / "preflight"
    / "20260714_OFFLINE_SPARK_ITSM_COMPOSE_PROBE_V1.json"
)


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
    # Vietnamese MT5: label cell then <b>value</b>.
    # "Lợi nhuận ròng" is a suffix of "Tổng lợi nhuận ròng" — require not preceded by "Tổng ".
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
    # Section after <b>Giao dịch</b> / <b>Deals</b>
    m = re.search(r"<b>\s*(Giao dịch|Deals)\s*</b>", html, re.IGNORECASE)
    if not m:
        raise ValueError(f"Deals section missing: {report_path}")
    section = html[m.end() :]
    # stop at next major section if present
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
    """Pair in/out deals into round-trip trades; pnl = exit profit + swap + commission on both legs."""
    open_by_order: dict[str, dict] = {}
    trades: list[dict] = []
    for d in deals:
        direction = d["direction"]
        # Vietnamese: "in"/"out" or "vào"/"ra" variants sometimes transliterated
        if direction in ("in", "vào", "vao"):
            open_by_order[d["order"]] = d
        elif direction in ("out", "ra"):
            entry = open_by_order.pop(d["order"], None)
            # pnl on exit deal already includes trade profit; add both legs fees if present
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
            # fallback: treat non-zero profit rows as exits without pairing
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


def parse_itsm_px6(csv_path: Path) -> list[dict]:
    trades = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        open_by_pos: dict[str, dict] = {}
        for row in reader:
            action = (row.get("action") or "").upper()
            t = datetime.strptime(row["event_time"][:19], "%Y.%m.%d %H:%M:%S")
            pos = row.get("position_id") or row.get("order") or ""
            if action == "OPEN":
                open_by_pos[pos] = {"entry_time": t, "side": row.get("order_type", "")}
            elif action == "CLOSE" and int(float(row.get("is_final_close") or 0)) == 1:
                entry = open_by_pos.pop(pos, None)
                pnl = float(row.get("net_profit") or 0) + float(row.get("swap") or 0) + float(
                    row.get("commission") or 0
                )
                trades.append(
                    {
                        "entry_time": entry["entry_time"] if entry else t,
                        "exit_time": t,
                        "side": entry["side"] if entry else row.get("order_type", ""),
                        "pnl": pnl,
                        "symbol": row.get("symbol") or "USDJPY",
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
    """ISO-week buckets over elapsed calendar from start to end (inclusive window)."""
    buckets: dict[tuple[int, int], float] = defaultdict(float)
    for tr in trades:
        et = tr["entry_time"]
        if et < start or et > end:
            continue
        iso = et.isocalendar()
        buckets[(iso.year, iso.week)] += tr["pnl"]

    # build complete week index from start to end
    cur = start - timedelta(days=start.weekday())  # Monday of start week
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


def main() -> int:
    spark_report = SPARK_DIR / "report.html"
    itsm_report = ITSM_DIR / "report.html"
    itsm_csv = next((ITSM_DIR / "logs").glob("*PX6_Trades*.csv"))

    spark_html = decode_report(spark_report)
    itsm_html = decode_report(itsm_report)

    spark_summary = {
        "net_profit": extract_summary_metric(spark_html, "Tổng lợi nhuận ròng"),
        "gross_profit": extract_summary_metric(spark_html, "Lợi nhuận ròng"),
        "gross_loss": extract_summary_metric(spark_html, "Mức lỗ ròng"),
        "profit_factor": extract_summary_metric(spark_html, "Hệ số lợi nhuận"),
        "n_trades": extract_summary_metric(spark_html, "Tổng số giao dịch"),
        "expectancy": extract_summary_metric(spark_html, "Mức lợi nhuận mong muốn"),
    }
    itsm_summary = {
        "net_profit": extract_summary_metric(itsm_html, "Tổng lợi nhuận ròng"),
        "gross_profit": extract_summary_metric(itsm_html, "Lợi nhuận ròng"),
        "gross_loss": extract_summary_metric(itsm_html, "Mức lỗ ròng"),
        "profit_factor": extract_summary_metric(itsm_html, "Hệ số lợi nhuận"),
        "n_trades": extract_summary_metric(itsm_html, "Tổng số giao dịch"),
        "expectancy": extract_summary_metric(itsm_html, "Mức lợi nhuận mong muốn"),
    }

    # Window from manifests / reports: 2021.01.01 - 2025.12.31
    window_start = datetime(2021, 1, 1)
    window_end = datetime(2025, 12, 31)
    weeks = elapsed_weeks(window_start, window_end)

    spark_deals = parse_deals_html(spark_report)
    spark_trades = deals_to_trades(spark_deals)
    itsm_trades = parse_itsm_px6(itsm_csv)

    # Sanity: prefer trade-count from summary if pairing drifts
    spark_n = int(spark_summary["n_trades"] or len(spark_trades))
    itsm_n = int(itsm_summary["n_trades"] or len(itsm_trades))

    # Pooled PF from report gross legs (authoritative report fields)
    pooled_gp = (spark_summary["gross_profit"] or 0) + (itsm_summary["gross_profit"] or 0)
    pooled_gl = abs(spark_summary["gross_loss"] or 0) + abs(itsm_summary["gross_loss"] or 0)
    pooled_pf_report = (pooled_gp / pooled_gl) if pooled_gl > 0 else None
    pooled_net = (spark_summary["net_profit"] or 0) + (itsm_summary["net_profit"] or 0)
    pooled_n = spark_n + itsm_n
    pooled_tpw = pooled_n / weeks if weeks else None

    # Trade-level PF from joined series (secondary)
    spark_pnls = [t["pnl"] for t in spark_trades]
    itsm_pnls = [t["pnl"] for t in itsm_trades]
    pooled_pf_trades = profit_factor(spark_pnls + itsm_pnls)

    # Entry-time overlap / correlation
    spark_entries = [t["entry_time"] for t in spark_trades]
    itsm_entries = [t["entry_time"] for t in itsm_trades]
    spark_entry_set = set(spark_entries)
    itsm_entry_set = set(itsm_entries)
    exact_overlap = len(spark_entry_set & itsm_entry_set)

    # Same M15 bar overlap (floor to 15-min)
    def floor_m15(dt: datetime) -> datetime:
        return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)

    spark_bars = {floor_m15(t) for t in spark_entries}
    itsm_bars = {floor_m15(t) for t in itsm_entries}
    bar_overlap = len(spark_bars & itsm_bars)

    # Same calendar day overlap
    spark_days = {t.date() for t in spark_entries}
    itsm_days = {t.date() for t in itsm_entries}
    day_overlap = len(spark_days & itsm_days)

    # Within +/- 60 minutes of any opposite entry
    def count_near(a: list[datetime], b: list[datetime], minutes: int) -> int:
        b_sorted = sorted(b)
        near = 0
        for t in a:
            # binary-ish linear scan is fine for N~1k
            for u in b_sorted:
                if abs((t - u).total_seconds()) <= minutes * 60:
                    near += 1
                    break
                if u > t + timedelta(minutes=minutes):
                    break
        return near

    spark_near_itsm_60 = count_near(spark_entries, itsm_entries, 60)
    itsm_near_spark_60 = count_near(itsm_entries, spark_entries, 60)

    spark_weekly = weekly_pnl_series(spark_trades, window_start, window_end)
    itsm_weekly = weekly_pnl_series(itsm_trades, window_start, window_end)
    corr_weekly = pearson(spark_weekly, itsm_weekly)

    # Active-week co-occurrence (weeks with trades)
    spark_active = [1 if abs(x) > 1e-12 else 0 for x in spark_weekly]
    itsm_active = [1 if abs(x) > 1e-12 else 0 for x in itsm_weekly]
    both_active = sum(1 for a, b in zip(spark_active, itsm_active) if a and b)
    spark_only = sum(1 for a, b in zip(spark_active, itsm_active) if a and not b)
    itsm_only = sum(1 for a, b in zip(spark_active, itsm_active) if b and not a)

    spark_tpw = spark_n / weeks
    itsm_tpw = itsm_n / weeks

    # GOAL research screen (tester cost only, not confirmed)
    cadence_ok = pooled_tpw is not None and 2.0 <= pooled_tpw <= 5.0
    pf_ok = pooled_pf_report is not None and pooled_pf_report > 1.30
    if cadence_ok and pf_ok:
        verdict = "PROBE_NEAR_GOAL_CADENCE_AND_PF_BUT_COST_UNCONFIRMED"
        worth_coding = True
        note = (
            "Pooled cadence and PF both clear research bars on tester-current cost; "
            "still NOT confirmed. Portfolio sleeve coding is worth considering only "
            "as research scaffold after Owner freeze — not promotion."
        )
    elif cadence_ok and not pf_ok:
        verdict = "FAIL_POOLED_PF_BELOW_1_30_CADENCE_OK"
        worth_coding = False
        note = (
            "Pooled elapsed-calendar cadence lands in 2-5/wk, but pooled PF is "
            "dominated by denser ITSM sleeve and stays below 1.30. Coding a "
            "combined portfolio EA sleeve is NOT worth it from this probe alone."
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
        "probe_id": "OFFLINE_SPARK_ITSM_COMPOSE_PROBE_V1",
        "generated_at_ict": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "gpt_status": "GPT_DEEP_RESEARCH_WAIVED / LOCAL_SELF_RESEARCH_ONLY",
        "universe_frozen": {
            "members": [
                {
                    "ea": "EA_M15SparkAsian",
                    "run_id": "20260714_002614",
                    "hypothesis_id": "HYP-SPARK-ASIAN-M15-001",
                    "symbol": "USDJPY",
                    "period": "M15",
                    "path": str(SPARK_DIR),
                    "report_sha256_manifest": "7CAE7A9332B551FE58360E2B89022835F23E7706345ED2E7DC02F5122D80001A",
                },
                {
                    "ea": "EA_ITSM",
                    "run_id": "20260714_003920",
                    "hypothesis_id": "HYP-ITSM-PULLBACK-M15-001",
                    "symbol": "USDJPY",
                    "period": "M15",
                    "path": str(ITSM_DIR),
                    "receipt_sha256": "0B5FBAB87648D9CA66EA168C1B891F1CCED852C7081D41A11D781DEF97FB9D31",
                },
            ],
            "selection_rule": "exact Owner-named run IDs; no PF-ranked cherry-pick",
            "excluded_explicitly": ["EA_SilverBullet", "any other shelf EA"],
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
            "note": "Missing/zero commission fields do not mean cost=0. Not Real QFSI.",
        },
        "sleeve_metrics": {
            "spark": {
                **spark_summary,
                "trades_parsed": len(spark_trades),
                "deals_parsed": len(spark_deals),
                "trades_per_week_elapsed": spark_tpw,
                "trade_level_pf": profit_factor(spark_pnls),
            },
            "itsm": {
                **itsm_summary,
                "trades_parsed": len(itsm_trades),
                "trades_per_week_elapsed": itsm_tpw,
                "trade_level_pf": profit_factor(itsm_pnls),
                "source": str(itsm_csv),
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
            "spark_entries_near_itsm_within_60m": spark_near_itsm_60,
            "itsm_entries_near_spark_within_60m": itsm_near_spark_60,
            "spark_entry_count": len(spark_entries),
            "itsm_entry_count": len(itsm_entries),
            "weekly_pnl_pearson": corr_weekly,
            "weeks_both_active": both_active,
            "weeks_spark_only": spark_only,
            "weeks_itsm_only": itsm_only,
            "weekly_series_len": len(spark_weekly),
        },
        "goal_screen_research_only": {
            "need_pooled_tpw_2_to_5": cadence_ok,
            "need_pooled_pf_gt_1_30": pf_ok,
            "verdict": verdict,
            "worth_coding_portfolio_ea_sleeve_next": worth_coding,
            "note": note,
        },
    }

    OUT_JSON.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    print(f"\nWrote {OUT_JSON}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
