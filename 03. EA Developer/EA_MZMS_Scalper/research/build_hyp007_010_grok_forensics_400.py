#!/usr/bin/env python3
"""Build honest 400-case indicator-rich visual forensics for HYP-MZMS-XAU-M5-007..010.

Read-only vs EA source / frozen prereg / registry / harness. No backtest or orders.

Execution truth remains MT5 StateTelemetry + Lifecycle. Offline recomputed
indicators/gates are visualization and near-miss ranking only — not MT5 parity.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "02. AlphaFactory" / "tools"))
from research.fivepercent_server_clock import server_to_utc  # noqa: E402
from research.indicators import atr_mt5, ema, rsi_wilder, sma  # noqa: E402

RESEARCH = Path(__file__).resolve().parent
OUT = RESEARCH / "evidence" / "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400"
SOURCE_SNAPSHOT = (
    RESEARCH / "source_snapshots" / "EA_MZMS_Scalper_HYP-MZMS-XAU-M5-007-010.mq5"
)
PREREG = RESEARCH / "HYP-MZMS-XAU-M5-007-010_FROZEN_PREREG.md"
DESIGN = RESEARCH / "HYP-MZMS-XAU-M5-007-010_GROK_DESIGN_CANDIDATE.md"
BARS_SOURCE = (
    RESEARCH
    / "evidence"
    / "HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_GROK_INDICATOR_FORENSICS_200"
    / "data"
    / "XAUUSD_M5_with_recomputed_strategy_indicators.parquet"
)
EXPECTED_BARS_SHA = "8D4FEEFDE69D130F80C8DA630E65178C8F48087FD392E3A6F339B57770D2A3CC"

POINT = 0.01
RR = 1.60
HISTORY_QUALITY_WATERMARK = "98% HISTORY QUALITY - DIAGNOSTIC ONLY"

RUNS: dict[str, dict[str, Any]] = {
    "HYP-MZMS-XAU-M5-007": {
        "run_id": "20260722_015121",
        "magic": "109955140",
        "mode": 2,
        "short": "007",
        "family": "Donchian20 impulse + EMA50 + ADX/DI + ATR/body expansion",
        "executed_target": 100,
        "near_miss_target": 0,
    },
    "HYP-MZMS-XAU-M5-008": {
        "run_id": "20260722_021353",
        "magic": "111305312",
        "mode": 3,
        "short": "008",
        "family": "EMA20/EMA100 pullback-reclaim + pivot + ADX",
        "executed_target": 80,
        "near_miss_target": 20,
    },
    "HYP-MZMS-XAU-M5-009": {
        "run_id": "20260722_023841",
        "magic": "112793906",
        "mode": 4,
        "short": "009",
        "family": "BB20/2 squeeze + EMA34 + ATR/breakout",
        "executed_target": 100,
        "near_miss_target": 0,
    },
    "HYP-MZMS-XAU-M5-010": {
        "run_id": "20260722_024229",
        "magic": "113022296",
        "mode": 5,
        "short": "010",
        "family": "RSI14 extreme + wick rejection + EMA50 + ADX roll",
        "executed_target": 2,
        "near_miss_target": 98,
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def parse_server_time(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%Y.%m.%d %H:%M:%S")


def fmt_server(dt: datetime) -> str:
    return dt.strftime("%Y.%m.%d %H:%M:%S")


def seed_for(hypothesis_id: str, run_id: str) -> int:
    material = f"{hypothesis_id}|{run_id}|GROK_FORENSICS_400"
    return int(hashlib.sha256(material.encode("utf-8")).hexdigest()[:8], 16)


def run_paths(hypothesis_id: str) -> dict[str, Path]:
    cfg = RUNS[hypothesis_id]
    run_dir = ROOT / "02. AlphaFactory" / "runs" / "EA_MZMS_Scalper" / cfg["run_id"]
    tag = f"XAUUSD_{{kind}}_HYP-MZMS-XAU-M5-{cfg['short']}_{cfg['magic']}"
    return {
        "run_dir": run_dir,
        "lifecycle": run_dir
        / "logs"
        / f"XAUUSD_LifecycleTrades_HYP-MZMS-XAU-M5-{cfg['short']}_{cfg['magic']}.csv",
        "telemetry": run_dir
        / "logs"
        / f"XAUUSD_StateTelemetry_HYP-MZMS-XAU-M5-{cfg['short']}_{cfg['magic']}.csv",
        "run_meta": run_dir
        / "logs"
        / f"XAUUSD_RunMeta_HYP-MZMS-XAU-M5-{cfg['short']}_{cfg['magic']}.json",
        "report": run_dir / "report.html",
        "manifest": run_dir / "run_manifest.json",
        "enhanced": run_dir / "analysis" / "enhanced_summary.json",
        "source_run_snapshot": run_dir / "snapshot" / "source" / "EA_MZMS_Scalper.mq5",
    }


def parse_report_metrics(report_path: Path) -> dict[str, Any]:
    text = report_path.read_bytes().decode("utf-16-le")
    out: dict[str, Any] = {}
    hq = re.search(r"History Quality:</td>\s*<td[^>]*><b>([^<]+)</b>", text)
    if hq:
        out["history_quality_raw"] = hq.group(1).strip()
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", hq.group(1))
        out["history_quality_pct"] = float(m.group(1)) if m else None
    net = re.search(r"Tổng lợi nhuận ròng:</td>\s*<td[^>]*><b>([^<]+)</b>", text)
    if net:
        out["report_net_profit"] = float(net.group(1).replace(" ", "").replace("\xa0", ""))
    pf = re.search(r"Hệ số lợi nhuận:</td>\s*<td[^>]*><b>([^<]+)</b>", text)
    if pf:
        out["report_profit_factor"] = float(pf.group(1).replace(" ", ""))
    trades = re.search(r"Tổng số giao dịch:</td>\s*<td[^>]*><b>([^<]+)</b>", text)
    if trades:
        out["report_total_trades"] = int(trades.group(1).replace(" ", ""))
    return out


def load_lifecycle_positions(lifecycle_path: Path) -> list[dict[str, Any]]:
    with lifecycle_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["position_id"]].append(row)
    positions: list[dict[str, Any]] = []
    for position_id, position_rows in grouped.items():
        position_rows.sort(key=lambda item: item["event_time"])
        opens = [row for row in position_rows if row["action"] == "OPEN"]
        closes = [row for row in position_rows if row["action"] == "CLOSE"]
        final_closes = [
            row
            for row in closes
            if str(row.get("is_final_close", "")).strip() in {"1", "true", "True"}
        ]
        if len(opens) != 1 or len(final_closes) != 1:
            raise RuntimeError(
                f"{lifecycle_path.name} position {position_id}: need one OPEN + one final CLOSE"
            )
        opened, closed = opens[0], final_closes[0]
        direction = 1 if opened["order_type"] == "BUY" else -1
        entry = float(opened["price"])
        risk_pts = float(opened["risk_pts"])
        risk_account = float(opened["initial_risk_account"])
        risk_price = risk_pts * POINT
        entry_time = parse_server_time(opened["event_time"])
        exit_time = parse_server_time(closed["event_time"])
        net = sum(float(row["deal_net"]) for row in position_rows)
        positions.append(
            {
                "position_id": int(position_id),
                "direction": direction,
                "side": opened["order_type"],
                "entry_time_server": opened["event_time"],
                "entry_time": entry_time,
                "entry": entry,
                "exit_time_server": closed["event_time"],
                "exit_time": exit_time,
                "exit": float(closed["price"]),
                "risk_pts": risk_pts,
                "initial_risk_account": risk_account,
                "net_usd": net,
                "net_R": (net / risk_account) if risk_account > 0.0 else None,
                "sl": entry - direction * risk_price if risk_pts > 0.0 else None,
                "tp": entry + direction * RR * risk_price if risk_pts > 0.0 else None,
                "hold_minutes": (exit_time - entry_time).total_seconds() / 60.0,
                "year": entry_time.year,
                "outcome_label": (
                    "WINNER" if net > 0.0 else ("LOSER" if net < 0.0 else "FLAT")
                ),
            }
        )
    positions.sort(key=lambda item: (item["entry_time"], item["position_id"]))
    return positions


def load_telemetry(telemetry_path: Path) -> list[dict[str, Any]]:
    with telemetry_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    accepted = [row for row in rows if str(row.get("accepted", "")).strip() == "1"]
    if len(accepted) != len(rows):
        raise RuntimeError(f"{telemetry_path.name}: non-accepted telemetry rows present")
    accepted.sort(key=lambda row: (row["server_time"], row["decision_bar_time"]))
    return accepted


def bind_positions_telemetry(
    positions: list[dict[str, Any]], telemetry: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if len(positions) != len(telemetry):
        raise RuntimeError(
            f"telemetry accepted={len(telemetry)} != lifecycle positions={len(positions)}"
        )
    bound: list[dict[str, Any]] = []
    for pos, tel in zip(positions, telemetry):
        if parse_server_time(tel["server_time"]) != pos["entry_time"]:
            # allow exact string match only; otherwise fail closed if order drifted
            if tel["server_time"] != pos["entry_time_server"]:
                raise RuntimeError(
                    f"position {pos['position_id']} server_time mismatch "
                    f"{tel['server_time']} vs {pos['entry_time_server']}"
                )
        direction = int(float(tel["direction"]))
        if direction != pos["direction"]:
            raise RuntimeError(
                f"position {pos['position_id']} direction mismatch telemetry/lifecycle"
            )
        item = dict(pos)
        item["telemetry"] = tel
        item["decision_bar_time_server"] = tel["decision_bar_time"]
        item["decision_utc"] = tel["utc_time"]
        item["planned_entry"] = float(tel["planned_entry"])
        item["planned_stop"] = float(tel["planned_stop"])
        item["planned_target"] = float(tel["planned_target"])
        # Prefer lifecycle-derived SL/TP geometry; keep planned as cross-check.
        if item["sl"] is None:
            item["sl"] = item["planned_stop"]
        if item["tp"] is None:
            item["tp"] = item["planned_target"]
        bound.append(item)
    return bound


def profit_factor(nets: list[float]) -> float | None:
    gains = sum(x for x in nets if x > 0.0)
    losses = -sum(x for x in nets if x < 0.0)
    if losses <= 0.0:
        return None if gains <= 0.0 else float("inf")
    return gains / losses


def reconcile_hypothesis(hypothesis_id: str) -> dict[str, Any]:
    paths = run_paths(hypothesis_id)
    positions = load_lifecycle_positions(paths["lifecycle"])
    telemetry = load_telemetry(paths["telemetry"])
    bound = bind_positions_telemetry(positions, telemetry)
    enhanced = json.loads(paths["enhanced"].read_text(encoding="utf-8"))
    report = parse_report_metrics(paths["report"])
    nets = [float(p["net_usd"]) for p in bound]
    wr = (
        100.0 * sum(1 for n in nets if n > 0.0) / len(nets) if nets else None
    )
    pf = profit_factor(nets)
    expectancy = (sum(nets) / len(nets)) if nets else None
    report_trades = report.get("report_total_trades")
    enhanced_trades = int(enhanced.get("n_trades", -1))
    exact = (
        len(bound) == len(telemetry)
        and report_trades == len(bound)
        and enhanced_trades == len(bound)
        and abs(sum(nets) - float(enhanced.get("net_profit", 0.0))) < 1e-6
    )
    return {
        "hypothesis_id": hypothesis_id,
        "run_id": RUNS[hypothesis_id]["run_id"],
        "mode": RUNS[hypothesis_id]["mode"],
        "positions": len(bound),
        "lifecycle_rows": len(bound) * 2,
        "state_telemetry_accepted_rows": len(telemetry),
        "report_total_trades": report_trades,
        "enhanced_n_trades": enhanced_trades,
        "exact_open_close_pairs": True,
        "telemetry_equals_entries": len(telemetry) == len(bound),
        "report_trades_equal_positions": report_trades == len(bound),
        "enhanced_trades_equal_positions": enhanced_trades == len(bound),
        "net_usd_lifecycle": sum(nets),
        "net_usd_enhanced": float(enhanced.get("net_profit")),
        "profit_factor_lifecycle": pf,
        "profit_factor_enhanced": float(enhanced.get("profit_factor")),
        "win_rate_pct_lifecycle": wr,
        "win_rate_pct_enhanced": float(enhanced.get("win_rate_pct")),
        "expectancy_per_trade_lifecycle": expectancy,
        "expectancy_per_trade_enhanced": float(enhanced.get("expectancy_per_trade")),
        "history_quality_pct": report.get("history_quality_pct"),
        "history_quality_raw": report.get("history_quality_raw"),
        "validity": "INVALID_ENGINEERING_RUN_HISTORY_QUALITY_98_BELOW_99",
        "economic_authority": "DIAGNOSTIC_ONLY",
        "exact_reconciliation": exact,
        "winners": sum(1 for n in nets if n > 0.0),
        "losers": sum(1 for n in nets if n < 0.0),
        "flats": sum(1 for n in nets if n == 0.0),
        "source_artifacts": {
            "lifecycle": str(paths["lifecycle"]),
            "lifecycle_sha256": sha256_file(paths["lifecycle"]),
            "telemetry": str(paths["telemetry"]),
            "telemetry_sha256": sha256_file(paths["telemetry"]),
            "run_meta": str(paths["run_meta"]),
            "run_meta_sha256": sha256_file(paths["run_meta"]),
            "report": str(paths["report"]),
            "report_sha256": sha256_file(paths["report"]),
            "enhanced_summary": str(paths["enhanced"]),
            "enhanced_summary_sha256": sha256_file(paths["enhanced"]),
            "run_manifest": str(paths["manifest"]),
            "run_manifest_sha256": sha256_file(paths["manifest"]),
        },
        "bound_positions": bound,
    }


def adx_di_mt5(df: pd.DataFrame, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return ADX, +DI, -DI under MT5 iADX EMA-of-per-bar-DI semantics."""
    h, l, c = df["high"], df["low"], df["close"]
    up = h.diff().to_numpy(float)
    dn = (-l.diff()).to_numpy(float)
    p = np.where(up > 0, up, 0.0)
    m = np.where(dn > 0, dn, 0.0)
    plus_dm = pd.Series(np.where(p > m, p, 0.0), index=df.index)
    minus_dm = pd.Series(np.where(m > p, m, 0.0), index=df.index)
    pc = c.shift(1)
    tr = pd.concat([h, pc], axis=1).max(axis=1) - pd.concat([l, pc], axis=1).min(axis=1)
    raw_p = (100.0 * plus_dm / tr).where(tr != 0.0, 0.0)
    raw_m = (100.0 * minus_dm / tr).where(tr != 0.0, 0.0)
    pdi = raw_p.iloc[1:].ewm(span=period, adjust=False).mean().reindex(df.index)
    mdi = raw_m.iloc[1:].ewm(span=period, adjust=False).mean().reindex(df.index)
    denom = pdi + mdi
    dx = (100.0 * (pdi - mdi).abs() / denom).where(denom != 0.0, 0.0)
    adx = dx.ewm(span=period, adjust=False).mean()
    return adx, pdi, mdi


def bollinger(close: pd.Series, period: int = 20, deviation: float = 2.0):
    mid = sma(close, period)
    std = close.rolling(period).std(ddof=0)
    return mid, mid + deviation * std, mid - deviation * std


def load_and_enrich_bars() -> pd.DataFrame:
    if not BARS_SOURCE.exists():
        raise FileNotFoundError(BARS_SOURCE)
    bars_sha = sha256_file(BARS_SOURCE)
    if bars_sha != EXPECTED_BARS_SHA:
        raise RuntimeError(
            f"bars SHA mismatch: got {bars_sha}, expected {EXPECTED_BARS_SHA}"
        )
    raw = pd.read_parquet(BARS_SOURCE).sort_values("time_utc").reset_index(drop=True)
    # time_utc is renderer-compat name; epochs align with lifecycle server clock.
    bars = raw[["time_utc", "open", "high", "low", "close"]].copy()
    bars = bars.rename(columns={"time_utc": "time_server"})
    bars["time_server"] = pd.to_datetime(bars["time_server"])
    ohlc = bars.rename(columns={"time_server": "time"})
    atr = atr_mt5(ohlc, 14)
    adx, pdi, mdi = adx_di_mt5(ohlc, 14)
    close = bars["close"].astype(float)
    high = bars["high"].astype(float)
    low = bars["low"].astype(float)
    open_ = bars["open"].astype(float)
    bb_mid, bb_up, bb_lo = bollinger(close, 20, 2.0)
    body = (close - open_).abs()
    bars["atr14"] = atr
    bars["adx14"] = adx
    bars["pdi14"] = pdi
    bars["mdi14"] = mdi
    bars["rsi14"] = rsi_wilder(close, 14)
    bars["ema20"] = ema(close, 20)
    bars["ema34"] = ema(close, 34)
    bars["ema50"] = ema(close, 50)
    bars["ema100"] = ema(close, 100)
    bars["bb_mid"] = bb_mid
    bars["bb_upper"] = bb_up
    bars["bb_lower"] = bb_lo
    bars["body"] = body
    bars["range"] = high - low
    bars["bb_width_atr"] = (bb_up - bb_lo) / atr.replace(0.0, np.nan)
    # Donchian of prior 20 bars excluding current (shifts 2..21 at decision on this bar as s1)
    # When bar i is shift1, donchian uses bars i-1 .. i-20.
    bars["donchian_high20_excl"] = high.shift(1).rolling(20).max()
    bars["donchian_low20_excl"] = low.shift(1).rolling(20).min()
    bars["body_median_10_prev"] = body.shift(1).rolling(10).median()
    # UTC for session filter
    utc_list = []
    for ts in bars["time_server"]:
        utc_list.append(server_to_utc(pd.Timestamp(ts).to_pydatetime()))
    bars["time_utc"] = pd.to_datetime(utc_list)
    bars["utc_hour"] = bars["time_utc"].dt.hour
    bars["in_session"] = (bars["utc_hour"] >= 8) & (bars["utc_hour"] < 17)
    # HTF closed M15/H1 for context panels
    bars = bars.reset_index(drop=True)
    return bars


def resample_htf(bars: pd.DataFrame, rule: str) -> pd.DataFrame:
    frame = bars.set_index("time_server")[["open", "high", "low", "close"]].copy()
    out = frame.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    )
    return out.dropna().reset_index()


def classify_anomaly(pos: dict[str, Any]) -> str | None:
    hold = float(pos["hold_minutes"])
    net_r = pos["net_R"]
    if net_r is None:
        return "UNDEFINED_R"
    if hold <= 5.0 and net_r < 0:
        return "FAST_STOP"
    if hold <= 15.0 and net_r <= -0.8:
        return "QUICK_ADVERSE"
    if 70.0 <= hold <= 80.0:
        return "TIME_EXIT_LIKE"
    if net_r <= -1.05:
        return "FULL_STOP_LIKE"
    if net_r >= 1.4:
        return "NEAR_FULL_TARGET"
    if abs(net_r) <= 0.05:
        return "SCRATCH"
    return None


def stratified_executed_sample(
    positions: list[dict[str, Any]],
    n: int,
    seed: int,
    take_all_if_leq: bool = True,
) -> list[dict[str, Any]]:
    if take_all_if_leq and len(positions) <= n:
        out = [dict(p) for p in positions]
        for p in out:
            p["case_kind"] = "EXECUTED"
            p["stratum"] = "POPULATION_FULL"
            p["anomaly_tag"] = classify_anomaly(p)
        return out

    rng = random.Random(seed)
    enriched = []
    for p in positions:
        item = dict(p)
        item["anomaly_tag"] = classify_anomaly(p)
        item["case_kind"] = "EXECUTED"
        enriched.append(item)

    anomalies = [p for p in enriched if p["anomaly_tag"]]
    winners = [p for p in enriched if p["outcome_label"] == "WINNER"]
    losers = [p for p in enriched if p["outcome_label"] == "LOSER"]
    # Target mix aligned with frozen forensics intent: ~30W/30L/20 anomaly/20 year-dir fill.
    target_anom = min(20, len(anomalies), n)
    target_w = min(30, len(winners), max(0, n - target_anom))
    target_l = min(30, len(losers), max(0, n - target_anom - target_w))

    def take(pool: list[dict[str, Any]], k: int, used: set[int]) -> list[dict[str, Any]]:
        eligible = [p for p in pool if p["position_id"] not in used]
        # year/direction stratification
        buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for p in eligible:
            buckets[(p["year"], p["side"])].append(p)
        for key in buckets:
            buckets[key].sort(key=lambda x: x["position_id"])
            rng.shuffle(buckets[key])
        keys = sorted(buckets)
        picked: list[dict[str, Any]] = []
        while len(picked) < k and any(buckets[key] for key in keys):
            for key in keys:
                if len(picked) >= k:
                    break
                if buckets[key]:
                    picked.append(buckets[key].pop())
        return picked

    used: set[int] = set()
    selected: list[dict[str, Any]] = []
    for p in take(anomalies, target_anom, used):
        p = dict(p)
        p["stratum"] = f"ANOMALY:{p['anomaly_tag']}"
        selected.append(p)
        used.add(p["position_id"])
    for p in take(winners, target_w, used):
        p = dict(p)
        p["stratum"] = "WINNER"
        selected.append(p)
        used.add(p["position_id"])
    for p in take(losers, target_l, used):
        p = dict(p)
        p["stratum"] = "LOSER"
        selected.append(p)
        used.add(p["position_id"])

    # Fill remainder across year x direction x outcome residual.
    if len(selected) < n:
        residual = [p for p in enriched if p["position_id"] not in used]
        for p in take(residual, n - len(selected), used):
            p = dict(p)
            p["stratum"] = f"FILL:{p['outcome_label']}"
            selected.append(p)
            used.add(p["position_id"])

    if len(selected) != n:
        raise RuntimeError(f"stratified sample size {len(selected)} != {n}")
    selected.sort(key=lambda p: (p["entry_time"], p["position_id"]))
    return selected


@dataclass
class GateEval:
    direction: int
    failed: int
    active: int
    distance: float
    gates: dict[str, bool]
    meta: dict[str, Any]


def _fail_dist(ok: bool, raw_dist: float) -> float:
    return 0.0 if ok else abs(float(raw_dist))


def eval_007_at(i: int, bars: pd.DataFrame) -> GateEval | None:
    if i < 21:
        return None
    row = bars.iloc[i]
    atr1 = float(row.atr14)
    atr3 = float(bars.iloc[i - 2].atr14)
    adx1 = float(row.adx14)
    adx2 = float(bars.iloc[i - 1].adx14)
    pdi1 = float(row.pdi14)
    mdi1 = float(row.mdi14)
    ema50 = float(row.ema50)
    body1 = float(row.body)
    body_med = float(row.body_median_10_prev)
    range1 = float(row.range)
    c1, o1 = float(row.close), float(row.open)
    d_hi = float(row.donchian_high20_excl)
    d_lo = float(row.donchian_low20_excl)
    if any(math.isnan(x) for x in [atr1, atr3, adx1, adx2, pdi1, mdi1, ema50, body_med, d_hi, d_lo]):
        return None
    g_common = {
        "atr_pos": atr1 > 0.0,
        "range_pos": range1 > 0.0,
        "adx_band": 16.0 <= adx1 <= 32.0,
        "adx_rise": adx1 > adx2,
        "atr_exp": atr1 > atr3,
        "body_exp": body_med > 0.0 and body1 >= 1.20 * body_med,
    }
    # long
    g_long = dict(g_common)
    g_long.update(
        {
            "donchian": c1 > d_hi,
            "candle": c1 > o1,
            "ema_side": c1 > ema50,
            "di": pdi1 > mdi1,
            "outer_close": range1 > 0.0 and c1 >= o1 + 0.55 * range1,
        }
    )
    g_short = dict(g_common)
    g_short.update(
        {
            "donchian": c1 < d_lo,
            "candle": c1 < o1,
            "ema_side": c1 < ema50,
            "di": mdi1 > pdi1,
            "outer_close": range1 > 0.0 and c1 <= o1 - 0.55 * range1,
        }
    )

    def score(gates: dict[str, bool], direction: int) -> GateEval:
        failed = sum(1 for v in gates.values() if not v)
        dist = 0.0
        dist += _fail_dist(gates["adx_band"], min(abs(adx1 - 16.0), abs(adx1 - 32.0)) / 16.0)
        dist += _fail_dist(gates["adx_rise"], max(0.0, adx2 - adx1) / max(adx2, 1e-9))
        dist += _fail_dist(gates["atr_exp"], max(0.0, atr3 - atr1) / max(atr3, 1e-9))
        dist += _fail_dist(
            gates["body_exp"],
            max(0.0, 1.20 * body_med - body1) / max(body_med, 1e-9),
        )
        if direction > 0:
            dist += _fail_dist(gates["donchian"], max(0.0, d_hi - c1) / max(atr1, 1e-9))
            dist += _fail_dist(gates["ema_side"], max(0.0, ema50 - c1) / max(atr1, 1e-9))
            dist += _fail_dist(gates["di"], max(0.0, mdi1 - pdi1) / 100.0)
        else:
            dist += _fail_dist(gates["donchian"], max(0.0, c1 - d_lo) / max(atr1, 1e-9))
            dist += _fail_dist(gates["ema_side"], max(0.0, c1 - ema50) / max(atr1, 1e-9))
            dist += _fail_dist(gates["di"], max(0.0, pdi1 - mdi1) / 100.0)
        return GateEval(direction, failed, len(gates), dist, gates, {"atr1": atr1, "adx1": adx1})

    long_s = score(g_long, 1)
    short_s = score(g_short, -1)
    if long_s.failed < short_s.failed or (
        long_s.failed == short_s.failed and long_s.distance <= short_s.distance
    ):
        return long_s
    return short_s


def eval_008_at(i: int, bars: pd.DataFrame) -> GateEval | None:
    if i < 12:
        return None
    row = bars.iloc[i]
    atr1 = float(row.atr14)
    adx1 = float(row.adx14)
    pdi1 = float(row.pdi14)
    mdi1 = float(row.mdi14)
    ema20 = float(row.ema20)
    ema100 = float(row.ema100)
    c1, o1, c2 = float(row.close), float(row.open), float(bars.iloc[i - 1].close)
    if any(math.isnan(x) for x in [atr1, adx1, pdi1, mdi1, ema20, ema100]) or atr1 <= 0:
        return None
    trend_long = ema20 > ema100 and c1 > ema100 and adx1 >= 20.0 and pdi1 > mdi1
    trend_short = ema20 < ema100 and c1 < ema100 and adx1 >= 20.0 and mdi1 > pdi1

    def pivot_low(center_shift: int) -> bool:
        # center_shift is p; center index = i - (p - 1)
        c = i - (center_shift - 1)
        if c - 2 < 0 or c + 2 >= len(bars):
            return False
        lp = float(bars.iloc[c].low)
        return (
            lp < float(bars.iloc[c - 1].low)
            and lp < float(bars.iloc[c - 2].low)
            and lp < float(bars.iloc[c + 1].low)
            and lp < float(bars.iloc[c + 2].low)
        )

    def pivot_high(center_shift: int) -> bool:
        c = i - (center_shift - 1)
        if c - 2 < 0 or c + 2 >= len(bars):
            return False
        hp = float(bars.iloc[c].high)
        return (
            hp > float(bars.iloc[c - 1].high)
            and hp > float(bars.iloc[c - 2].high)
            and hp > float(bars.iloc[c + 1].high)
            and hp > float(bars.iloc[c + 2].high)
        )

    candidates: list[GateEval] = []
    for want_long, want_short, direction in (
        (trend_long, False, 1),
        (False, trend_short, -1),
    ):
        if not (want_long or want_short):
            continue
        p_star = -1
        for p in range(3, 9):
            if want_long and pivot_low(p):
                p_star = p
                break
            if want_short and pivot_high(p):
                p_star = p
                break
        gates = {
            "trend": True,
            "pivot_found": p_star > 0,
            "depth": False,
            "ema_tag": False,
            "no_slow_break": False,
            "reclaim": False,
            "anti_break": False,
            "candle": False,
            "above_fast": False,
            "prior_interact": False,
        }
        meta: dict[str, Any] = {"p_star": p_star}
        dist = 0.0
        dist += _fail_dist(adx1 >= 20.0, max(0.0, 20.0 - adx1) / 20.0)
        if p_star < 0:
            dist += 5.0
            candidates.append(GateEval(direction, sum(1 for v in gates.values() if not v), len(gates), dist, gates, meta))
            continue
        c_idx = i - (p_star - 1)
        ema20_p = float(bars.iloc[c_idx].ema20)
        ema100_p = float(bars.iloc[c_idx].ema100)
        if want_long:
            pivot_price = float(bars.iloc[c_idx].low)
            href = max(float(bars.iloc[j].high) for j in range(c_idx, min(len(bars), c_idx + 4)))
            depth = (href - pivot_price) / atr1
            depth_ok = 0.40 <= depth <= 1.80
            tag_ok = pivot_price <= ema20_p + 0.15 * atr1
            no_break = pivot_price >= ema100_p - 0.25 * atr1
            max_h4 = max(float(bars.iloc[i - k].high) for k in range(1, 5))
            anti = c1 <= max_h4
            bull = c1 > o1
            reclaim = (
                c1 > pivot_price + 0.05 * atr1
                and bull
                and c1 > ema20
                and c2 <= pivot_price + 0.15 * atr1
                and anti
            )
            gates.update(
                {
                    "depth": depth_ok,
                    "ema_tag": tag_ok,
                    "no_slow_break": no_break,
                    "reclaim": reclaim,
                    "anti_break": anti,
                    "candle": bull,
                    "above_fast": c1 > ema20,
                    "prior_interact": c2 <= pivot_price + 0.15 * atr1,
                }
            )
            dist += _fail_dist(depth_ok, min(abs(depth - 0.40), abs(depth - 1.80)))
            dist += _fail_dist(tag_ok, max(0.0, pivot_price - (ema20_p + 0.15 * atr1)) / atr1)
            dist += _fail_dist(reclaim, max(0.0, (pivot_price + 0.05 * atr1) - c1) / atr1)
            meta.update({"pivot_price": pivot_price, "depth": depth})
        else:
            pivot_price = float(bars.iloc[c_idx].high)
            lref = min(float(bars.iloc[j].low) for j in range(c_idx, min(len(bars), c_idx + 4)))
            depth = (pivot_price - lref) / atr1
            depth_ok = 0.40 <= depth <= 1.80
            tag_ok = pivot_price >= ema20_p - 0.15 * atr1
            no_break = pivot_price <= ema100_p + 0.25 * atr1
            min_l4 = min(float(bars.iloc[i - k].low) for k in range(1, 5))
            anti = c1 >= min_l4
            bear = c1 < o1
            reclaim = (
                c1 < pivot_price - 0.05 * atr1
                and bear
                and c1 < ema20
                and c2 >= pivot_price - 0.15 * atr1
                and anti
            )
            gates.update(
                {
                    "depth": depth_ok,
                    "ema_tag": tag_ok,
                    "no_slow_break": no_break,
                    "reclaim": reclaim,
                    "anti_break": anti,
                    "candle": bear,
                    "above_fast": c1 < ema20,
                    "prior_interact": c2 >= pivot_price - 0.15 * atr1,
                }
            )
            dist += _fail_dist(depth_ok, min(abs(depth - 0.40), abs(depth - 1.80)))
            dist += _fail_dist(tag_ok, max(0.0, (ema20_p - 0.15 * atr1) - pivot_price) / atr1)
            dist += _fail_dist(reclaim, max(0.0, c1 - (pivot_price - 0.05 * atr1)) / atr1)
            meta.update({"pivot_price": pivot_price, "depth": depth})
        # trend already true for this branch
        failed = sum(1 for v in gates.values() if not v)
        candidates.append(GateEval(direction, failed, len(gates), dist, gates, meta))

    if not candidates:
        # both trends fail — score a neutral long-side trend failure
        gates = {
            "trend": False,
            "pivot_found": False,
            "depth": False,
            "ema_tag": False,
            "no_slow_break": False,
            "reclaim": False,
            "anti_break": False,
            "candle": False,
            "above_fast": False,
            "prior_interact": False,
        }
        return GateEval(0, len(gates), len(gates), 10.0, gates, {})
    candidates.sort(key=lambda g: (g.failed, g.distance, -abs(g.direction)))
    return candidates[0]


def eval_009_at(i: int, bars: pd.DataFrame) -> GateEval | None:
    if i < 35:
        return None
    row = bars.iloc[i]
    prev = bars.iloc[i - 1]
    atr1 = float(row.atr14)
    atr2 = float(prev.atr14)
    adx1 = float(row.adx14)
    adx2 = float(prev.adx14)
    ema34 = float(row.ema34)
    c1, o1, c2 = float(row.close), float(row.open), float(prev.close)
    bb_u1, bb_l1 = float(row.bb_upper), float(row.bb_lower)
    bb_u2, bb_l2 = float(prev.bb_upper), float(prev.bb_lower)
    if any(math.isnan(x) for x in [atr1, atr2, adx1, adx2, ema34, bb_u1, bb_l1, bb_u2, bb_l2]):
        return None
    if atr1 <= 0 or atr2 <= 0:
        return None
    atr_rank = 0
    for j in range(3, 35):
        atr_j = float(bars.iloc[i - (j - 1)].atr14)
        if not math.isnan(atr_j) and atr_j <= atr2:
            atr_rank += 1
    widths = []
    for k in range(3, 23):
        b = bars.iloc[i - (k - 1)]
        atr_k = float(b.atr14)
        if atr_k <= 0 or math.isnan(atr_k):
            return None
        widths.append((float(b.bb_upper) - float(b.bb_lower)) / atr_k)
    width_med = float(np.median(widths))
    bb_width2 = (bb_u2 - bb_l2) / atr2
    squeeze = (
        atr_rank <= 8
        and bb_width2 <= 0.85 * width_med
        and adx2 <= 28.0
        and bb_u2 > bb_l2
    )
    range1 = float(row.range)
    body1 = float(row.body)
    body_ok = range1 > 0 and body1 >= 0.50 * range1
    adx_ok = adx1 < 35.0
    long_break = (
        c1 > bb_u1 + 0.05 * atr1
        and c1 > o1
        and c1 > ema34
        and c1 > c2
        and adx_ok
        and body_ok
    )
    short_break = (
        c1 < bb_l1 - 0.05 * atr1
        and c1 < o1
        and c1 < ema34
        and c1 < c2
        and adx_ok
        and body_ok
    )
    g_long = {
        "squeeze_pre": squeeze,
        "break": long_break,
        "bull": c1 > o1,
        "ema_tilt": c1 > ema34,
        "continuation": c1 > c2,
        "adx_not_vertical": adx_ok,
        "body_ok": body_ok,
    }
    g_short = {
        "squeeze_pre": squeeze,
        "break": short_break,
        "bull": c1 < o1,
        "ema_tilt": c1 < ema34,
        "continuation": c1 < c2,
        "adx_not_vertical": adx_ok,
        "body_ok": body_ok,
    }

    def score(gates: dict[str, bool], direction: int) -> GateEval:
        failed = sum(1 for v in gates.values() if not v)
        dist = 0.0
        dist += _fail_dist(gates["squeeze_pre"], max(0, atr_rank - 8) / 8.0 + max(0.0, bb_width2 - 0.85 * width_med))
        if direction > 0:
            dist += _fail_dist(gates["break"], max(0.0, (bb_u1 + 0.05 * atr1) - c1) / atr1)
        else:
            dist += _fail_dist(gates["break"], max(0.0, c1 - (bb_l1 - 0.05 * atr1)) / atr1)
        return GateEval(
            direction,
            failed,
            len(gates),
            dist,
            gates,
            {"atr_rank": atr_rank, "bb_width2": bb_width2},
        )

    long_s, short_s = score(g_long, 1), score(g_short, -1)
    if long_s.failed < short_s.failed or (
        long_s.failed == short_s.failed and long_s.distance <= short_s.distance
    ):
        return long_s
    return short_s


def eval_010_at(i: int, bars: pd.DataFrame) -> GateEval | None:
    if i < 4:
        return None
    row = bars.iloc[i]
    atr1 = float(row.atr14)
    adx1 = float(row.adx14)
    adx2 = float(bars.iloc[i - 1].adx14)
    rsi1 = float(row.rsi14)
    rsi2 = float(bars.iloc[i - 1].rsi14)
    ema50 = float(row.ema50)
    c1, o1 = float(row.close), float(row.open)
    h1, l1 = float(row.high), float(row.low)
    h2, l2 = float(bars.iloc[i - 1].high), float(bars.iloc[i - 1].low)
    if any(math.isnan(x) for x in [atr1, adx1, adx2, rsi1, rsi2, ema50]) or atr1 <= 0:
        return None
    bull2 = float(bars.iloc[i - 1].close) > float(bars.iloc[i - 1].open)
    bull3 = float(bars.iloc[i - 2].close) > float(bars.iloc[i - 2].open)
    bull4 = float(bars.iloc[i - 3].close) > float(bars.iloc[i - 3].open)
    bear2 = float(bars.iloc[i - 1].close) < float(bars.iloc[i - 1].open)
    bear3 = float(bars.iloc[i - 2].close) < float(bars.iloc[i - 2].open)
    bear4 = float(bars.iloc[i - 3].close) < float(bars.iloc[i - 3].open)
    range1 = h1 - l1
    run_up = bull2 and bull3 and bull4
    run_down = bear2 and bear3 and bear4
    ext_up = h1 >= ema50 + 1.20 * atr1 and rsi1 >= 70.0 and rsi1 >= rsi2
    ext_down = l1 <= ema50 - 1.20 * atr1 and rsi1 <= 30.0 and rsi1 <= rsi2
    reject_up = (
        range1 > 0
        and (h1 - max(o1, c1)) >= 0.55 * range1
        and c1 < h2
        and c1 <= o1
        and adx1 >= 14.0
        and adx1 < adx2
        and c1 > ema50 - 0.30 * atr1
    )
    reject_down = (
        range1 > 0
        and (min(o1, c1) - l1) >= 0.55 * range1
        and c1 > l2
        and c1 >= o1
        and adx1 >= 14.0
        and adx1 < adx2
        and c1 < ema50 + 0.30 * atr1
    )
    g_short = {
        "run": run_up,
        "ext": ext_up,
        "reject": reject_up,
        "rsi_extreme": rsi1 >= 70.0,
        "adx_roll": adx1 < adx2 and adx1 >= 14.0,
        "wick": range1 > 0 and (h1 - max(o1, c1)) >= 0.55 * range1,
    }
    g_long = {
        "run": run_down,
        "ext": ext_down,
        "reject": reject_down,
        "rsi_extreme": rsi1 <= 30.0,
        "adx_roll": adx1 < adx2 and adx1 >= 14.0,
        "wick": range1 > 0 and (min(o1, c1) - l1) >= 0.55 * range1,
    }

    def score(gates: dict[str, bool], direction: int) -> GateEval:
        failed = sum(1 for v in gates.values() if not v)
        dist = 0.0
        if direction < 0:
            dist += _fail_dist(gates["rsi_extreme"], max(0.0, 70.0 - rsi1) / 70.0)
            dist += _fail_dist(gates["ext"], max(0.0, (ema50 + 1.20 * atr1) - h1) / atr1)
            dist += _fail_dist(gates["adx_roll"], max(0.0, adx1 - adx2) / max(adx2, 1e-9))
            dist += _fail_dist(
                gates["wick"],
                max(0.0, 0.55 * range1 - (h1 - max(o1, c1))) / max(range1, 1e-9),
            )
        else:
            dist += _fail_dist(gates["rsi_extreme"], max(0.0, rsi1 - 30.0) / 30.0)
            dist += _fail_dist(gates["ext"], max(0.0, l1 - (ema50 - 1.20 * atr1)) / atr1)
            dist += _fail_dist(gates["adx_roll"], max(0.0, adx1 - adx2) / max(adx2, 1e-9))
            dist += _fail_dist(
                gates["wick"],
                max(0.0, 0.55 * range1 - (min(o1, c1) - l1)) / max(range1, 1e-9),
            )
        return GateEval(direction, failed, len(gates), dist, gates, {"rsi1": rsi1, "adx1": adx1})

    short_s, long_s = score(g_short, -1), score(g_long, 1)
    if short_s.failed < long_s.failed or (
        short_s.failed == long_s.failed and short_s.distance <= long_s.distance
    ):
        return short_s
    return long_s


EVALUATORS = {
    "HYP-MZMS-XAU-M5-007": eval_007_at,
    "HYP-MZMS-XAU-M5-008": eval_008_at,
    "HYP-MZMS-XAU-M5-009": eval_009_at,
    "HYP-MZMS-XAU-M5-010": eval_010_at,
}


def actual_signal_bar_indices(
    bars: pd.DataFrame, positions: list[dict[str, Any]]
) -> set[int]:
    times = bars["time_server"].to_numpy(dtype="datetime64[ns]")
    out: set[int] = set()
    for pos in positions:
        entry = np.datetime64(pos["entry_time"])
        entry_index = int(np.searchsorted(times, entry, side="left"))
        # signal/decision closed bar is previous M5 bar
        sig = entry_index - 1
        if sig >= 0:
            out.add(sig)
    return out


def rank_near_misses(
    hypothesis_id: str,
    bars: pd.DataFrame,
    exclude_indices: set[int],
    n: int,
    seed: int,
) -> list[dict[str, Any]]:
    evaluator = EVALUATORS[hypothesis_id]
    # Sample candidate pool densely but deterministically for speed on 008/010.
    # Evaluate every 1st bar in-session from 2018 onward with warm-up.
    start_ts = pd.Timestamp("2018-01-01")
    candidates: list[dict[str, Any]] = []
    # Stride keeps ranking tractable while remaining deterministic.
    stride = 1 if hypothesis_id.endswith("010") else 3
    for i in range(40, len(bars), stride):
        if i in exclude_indices:
            continue
        row = bars.iloc[i]
        if row.time_server < start_ts:
            continue
        if not bool(row.in_session):
            continue
        ev = evaluator(i, bars)
        if ev is None or ev.direction == 0:
            continue
        # Near-miss: not a full offline pass, or full pass but not executed.
        full_pass = ev.failed == 0
        if full_pass and i in exclude_indices:
            continue
        # Prefer few failed gates (0..3). Discard hopeless rows.
        if ev.failed > 3 and not full_pass:
            continue
        if full_pass:
            # offline full signal that was not executed (guards/cooldown)
            rank_failed = 0
        else:
            rank_failed = ev.failed
            if rank_failed == 0:
                continue
        candidates.append(
            {
                "bar_index": i,
                "time_server": fmt_server(pd.Timestamp(row.time_server).to_pydatetime()),
                "time_utc": fmt_server(pd.Timestamp(row.time_utc).to_pydatetime()),
                "direction": int(ev.direction),
                "side": "BUY" if ev.direction > 0 else "SELL",
                "failed_gates": int(rank_failed),
                "active_gates": int(ev.active),
                "normalized_distance": float(ev.distance),
                "gates": {k: bool(v) for k, v in ev.gates.items()},
                "meta": ev.meta,
                "case_kind": "OFFLINE_NEAR_MISS_DIAGNOSTIC",
                "offline_full_signal_unexecuted": bool(full_pass),
            }
        )
    candidates.sort(
        key=lambda c: (
            c["failed_gates"],
            c["normalized_distance"],
            c["bar_index"],
        )
    )
    # Time-diversify: greedy min spacing + year coverage.
    min_gap = 288  # ~1 trading day of M5
    selected: list[dict[str, Any]] = []
    year_counts: dict[int, int] = defaultdict(int)
    max_per_year = max(3, n // 6)
    for cand in candidates:
        if len(selected) >= n:
            break
        year = int(str(cand["time_server"])[:4])
        if year_counts[year] >= max_per_year and len(selected) < n - 2:
            # keep some room; soft constraint until late fill
            if any(abs(cand["bar_index"] - s["bar_index"]) < min_gap for s in selected):
                continue
            if year_counts[year] >= max_per_year * 2:
                continue
        if any(abs(cand["bar_index"] - s["bar_index"]) < min_gap for s in selected):
            continue
        selected.append(cand)
        year_counts[year] += 1
    # Fill if short without year cap.
    if len(selected) < n:
        for cand in candidates:
            if len(selected) >= n:
                break
            if any(c["bar_index"] == cand["bar_index"] for c in selected):
                continue
            if any(abs(cand["bar_index"] - s["bar_index"]) < min_gap // 2 for s in selected):
                continue
            selected.append(cand)
    if len(selected) < n:
        raise RuntimeError(
            f"{hypothesis_id}: only {len(selected)} near-miss candidates for target {n}"
        )
    selected = selected[:n]
    selected.sort(key=lambda c: c["bar_index"])
    # attach deterministic rank index
    for rank, item in enumerate(
        sorted(selected, key=lambda c: (c["failed_gates"], c["normalized_distance"], c["bar_index"])),
        1,
    ):
        item["near_miss_rank"] = rank
    selected.sort(key=lambda c: c["near_miss_rank"])
    _ = seed  # seed reserved for future stochastic tie breaks; ranking is fully deterministic
    return selected


def draw_candles(ax: Any, frame: pd.DataFrame) -> None:
    for index, row in enumerate(frame.itertuples(index=False)):
        up = row.close >= row.open
        color = "#15803d" if up else "#dc2626"
        ax.vlines(index, row.low, row.high, color=color, linewidth=0.7, zorder=2)
        lower = min(row.open, row.close)
        height = max(abs(row.close - row.open), 1e-8)
        ax.add_patch(
            plt.Rectangle(
                (index - 0.34, lower),
                0.68,
                height,
                facecolor=color,
                edgecolor=color,
                linewidth=0.35,
                zorder=3,
            )
        )
    ax.set_xlim(-1, len(frame))


def time_ticks(ax: Any, frame: pd.DataFrame, col: str = "time_server") -> None:
    step = max(1, len(frame) // 6)
    ticks = list(range(0, len(frame), step))
    ax.set_xticks(ticks)
    ax.set_xticklabels(
        [pd.Timestamp(frame[col].iloc[i]).strftime("%m-%d %H:%M") for i in ticks],
        rotation=20,
        ha="right",
        fontsize=7,
    )


def watermark(fig: Any) -> None:
    fig.text(
        0.5,
        0.5,
        HISTORY_QUALITY_WATERMARK,
        ha="center",
        va="center",
        fontsize=28,
        color="#b91c1c",
        alpha=0.12,
        rotation=25,
        fontweight="bold",
        zorder=0,
    )
    fig.text(
        0.5,
        0.01,
        HISTORY_QUALITY_WATERMARK
        + " | recomputed offline indicators are visual/near-miss only, NOT MT5 parity",
        ha="center",
        fontsize=8,
        color="#7f1d1d",
    )


def render_case(
    hypothesis_id: str,
    case: dict[str, Any],
    bars: pd.DataFrame,
    m15: pd.DataFrame,
    h1: pd.DataFrame,
    image_path: Path,
) -> dict[str, Any]:
    times = bars["time_server"].to_numpy(dtype="datetime64[ns]")
    is_near = case["case_kind"] == "OFFLINE_NEAR_MISS_DIAGNOSTIC"
    if is_near:
        decision_index = int(case["bar_index"])
        decision_time = pd.Timestamp(bars.iloc[decision_index].time_server)
        # outcome-blind future context only (no invented trade)
        future_end = min(len(bars), decision_index + 1 + 36)
        decision = bars.iloc[max(0, decision_index - 160) : decision_index + 1].copy().reset_index(drop=True)
        future = bars.iloc[max(0, decision_index - 24) : future_end].copy().reset_index(drop=True)
        cut_x = len(decision) - 1
    else:
        entry_t = np.datetime64(case["entry_time"])
        exit_t = np.datetime64(case["exit_time"])
        entry_index = int(np.searchsorted(times, entry_t, side="left"))
        exit_index = int(np.searchsorted(times, exit_t, side="right"))
        decision_index = entry_index - 1
        decision = bars.iloc[max(0, decision_index - 159) : decision_index + 1].copy().reset_index(drop=True)
        future = bars.iloc[max(0, entry_index - 36) : min(len(bars), exit_index + 12)].copy().reset_index(drop=True)
        decision_time = pd.Timestamp(bars.iloc[decision_index].time_server) if decision_index >= 0 else pd.Timestamp(case["entry_time"])
        cut_x = None

    fig = plt.figure(figsize=(20, 15), constrained_layout=True)
    grid = fig.add_gridspec(5, 2, height_ratios=[3.2, 1.0, 0.9, 0.95, 1.05])
    left = [fig.add_subplot(grid[r, 0]) for r in range(5)]
    right = [fig.add_subplot(grid[r, 1]) for r in range(5)]

    def panel(axes: list[Any], frame: pd.DataFrame, outcome: bool) -> None:
        price_ax, ind_ax, osc_ax, adx_ax, htf_ax = axes
        draw_candles(price_ax, frame)
        mode = RUNS[hypothesis_id]["mode"]
        x = range(len(frame))
        if mode == 2:
            price_ax.plot(x, frame["ema50"], color="#2563eb", lw=1.1, label="EMA50 recomputed")
            price_ax.plot(x, frame["donchian_high20_excl"], color="#0f766e", lw=0.9, ls="--", label="DonchianH excl")
            price_ax.plot(x, frame["donchian_low20_excl"], color="#b45309", lw=0.9, ls="--", label="DonchianL excl")
            ind_ax.plot(x, frame["body"], color="#334155", lw=0.9, label="Body")
            ind_ax.plot(x, frame["body_median_10_prev"] * 1.20, color="#f59e0b", lw=0.9, label="1.2x med body")
            osc_ax.plot(x, frame["pdi14"], color="#16a34a", lw=0.9, label="+DI")
            osc_ax.plot(x, frame["mdi14"], color="#dc2626", lw=0.9, label="-DI")
        elif mode == 3:
            price_ax.plot(x, frame["ema20"], color="#2563eb", lw=1.1, label="EMA20")
            price_ax.plot(x, frame["ema100"], color="#7c3aed", lw=1.1, label="EMA100")
            ind_ax.plot(x, frame["ema20"] - frame["ema100"], color="#0f766e", lw=0.9, label="EMA20-100")
            ind_ax.axhline(0, color="black", lw=0.5)
            osc_ax.plot(x, frame["pdi14"], color="#16a34a", lw=0.9, label="+DI")
            osc_ax.plot(x, frame["mdi14"], color="#dc2626", lw=0.9, label="-DI")
        elif mode == 4:
            price_ax.plot(x, frame["bb_upper"], color="#0f766e", lw=0.9, label="BB upper")
            price_ax.plot(x, frame["bb_mid"], color="#64748b", lw=0.8, label="BB mid")
            price_ax.plot(x, frame["bb_lower"], color="#b45309", lw=0.9, label="BB lower")
            price_ax.plot(x, frame["ema34"], color="#2563eb", lw=1.0, label="EMA34")
            ind_ax.plot(x, frame["bb_width_atr"], color="#7c3aed", lw=0.9, label="BB width/ATR")
            osc_ax.plot(x, frame["atr14"], color="#f97316", lw=0.9, label="ATR14")
        else:
            price_ax.plot(x, frame["ema50"], color="#2563eb", lw=1.1, label="EMA50")
            ind_ax.plot(x, frame["rsi14"], color="#7c3aed", lw=1.0, label="RSI14")
            ind_ax.axhline(70, color="#dc2626", ls=":", lw=0.8)
            ind_ax.axhline(30, color="#16a34a", ls=":", lw=0.8)
            ind_ax.set_ylim(0, 100)
            osc_ax.plot(x, (frame["high"] - frame[["open", "close"]].max(axis=1)) / frame["range"].replace(0, np.nan), color="#dc2626", lw=0.8, label="upper wick frac")
            osc_ax.plot(x, (frame[["open", "close"]].min(axis=1) - frame["low"]) / frame["range"].replace(0, np.nan), color="#16a34a", lw=0.8, label="lower wick frac")
        adx_ax.plot(x, frame["adx14"], color="#0f766e", lw=1.0, label="ADX14")
        if mode == 2:
            adx_ax.axhline(16, color="#0f766e", ls=":", lw=0.7)
            adx_ax.axhline(32, color="#b91c1c", ls=":", lw=0.7)
        elif mode == 3:
            adx_ax.axhline(20, color="#0f766e", ls=":", lw=0.7)
        atr_ax = adx_ax.twinx()
        atr_ax.plot(x, frame["atr14"], color="#f97316", lw=0.8, alpha=0.85, label="ATR14")
        atr_ax.set_ylabel("ATR", fontsize=8, color="#f97316")

        # HTF context: last closed M15/H1 bars at/before decision end of frame
        end_t = pd.Timestamp(frame["time_server"].iloc[-1])
        m15_win = m15[m15["time_server"] <= end_t].tail(40)
        h1_win = h1[h1["time_server"] <= end_t].tail(30)
        if len(m15_win):
            htf_ax.plot(range(len(m15_win)), m15_win["close"], color="#2563eb", lw=1.0, label="M15 close")
        if len(h1_win):
            # map h1 onto same x by reindex visual
            xs = np.linspace(0, max(len(m15_win) - 1, 1), len(h1_win))
            htf_ax.plot(xs, h1_win["close"], color="#7c3aed", lw=1.1, label="H1 close")
        htf_ax.set_ylabel("HTF", fontsize=8)
        htf_ax.legend(loc="upper left", fontsize=6)
        htf_ax.grid(alpha=0.15)

        if not is_near and not outcome:
            # decision cutoff marker at last bar
            for ax in axes:
                ax.axvline(len(frame) - 1, color="#1d4ed8", ls="--", lw=0.8, alpha=0.75)
        if is_near and not outcome:
            for ax in axes:
                ax.axvline(len(frame) - 1, color="#b45309", ls="--", lw=0.9, alpha=0.8)
            price_ax.annotate(
                "DECISION BAR\nOFFLINE_NEAR_MISS",
                (len(frame) - 1, float(frame["close"].iloc[-1])),
                xytext=(-90, 20),
                textcoords="offset points",
                fontsize=8,
                color="#b45309",
                fontweight="bold",
                arrowprops={"arrowstyle": "->", "color": "#b45309"},
            )
        if not is_near:
            entry = float(case["entry"])
            sl = case.get("sl")
            tp = case.get("tp")
            price_ax.axhline(entry, color="#1d4ed8", ls="--", lw=1.0, label="Entry")
            if sl is not None:
                price_ax.axhline(float(sl), color="#dc2626", ls=":", lw=1.0, label="Initial SL")
            if tp is not None:
                price_ax.axhline(float(tp), color="#15803d", ls=":", lw=1.0, label="Target 1.6R")
            if outcome:
                exit_p = float(case["exit"])
                price_ax.axhline(exit_p, color="#7e22ce", ls="-.", lw=0.9, label="Exit")
                # markers
                ent_x = int(
                    frame["time_server"].to_numpy(dtype="datetime64[ns]").searchsorted(
                        np.datetime64(case["entry_time"])
                    )
                )
                ent_x = min(max(ent_x, 0), len(frame) - 1)
                ex_x = int(
                    frame["time_server"].to_numpy(dtype="datetime64[ns]").searchsorted(
                        np.datetime64(case["exit_time"])
                    )
                )
                ex_x = min(max(ex_x, 0), len(frame) - 1)
                price_ax.scatter(
                    [ent_x],
                    [entry],
                    marker="^" if int(case["direction"]) > 0 else "v",
                    s=80,
                    color="#1d4ed8",
                    edgecolor="black",
                    zorder=7,
                )
                price_ax.scatter([ex_x], [exit_p], marker="X", s=90, color="#7e22ce", edgecolor="black", zorder=8)
        if is_near and outcome:
            # future context split — no trade geometry
            split = None
            for j, ts in enumerate(frame["time_server"]):
                if pd.Timestamp(ts) > decision_time:
                    split = j
                    break
            if split is not None:
                for ax in axes:
                    ax.axvline(split - 0.5, color="#b45309", ls="-", lw=1.0, alpha=0.7)
                price_ax.axvspan(split - 0.5, len(frame), color="#fde68a", alpha=0.18, label="FUTURE CONTEXT")
            price_ax.text(
                0.99,
                0.02,
                "NO entry/SL/TP/PnL invented\nOFFLINE_NEAR_MISS_DIAGNOSTIC",
                transform=price_ax.transAxes,
                ha="right",
                va="bottom",
                fontsize=8,
                family="monospace",
                bbox={"boxstyle": "round,pad=0.3", "fc": "#fff7ed", "ec": "#b45309", "alpha": 0.95},
            )

        title = (
            "DECISION (closed bars / outcome-blind)"
            if not outcome
            else ("OUTCOME anatomy" if not is_near else "FUTURE CONTEXT (not a trade outcome)")
        )
        price_ax.set_title(title, fontsize=10, fontweight="bold")
        price_ax.legend(loc="upper left", fontsize=6, ncol=3)
        price_ax.grid(alpha=0.18)
        ind_ax.grid(alpha=0.15)
        osc_ax.grid(alpha=0.15)
        adx_ax.grid(alpha=0.15)
        ind_ax.legend(loc="upper left", fontsize=6)
        osc_ax.legend(loc="upper left", fontsize=6)
        adx_ax.legend(loc="upper left", fontsize=6)
        for ax in axes[:-1]:
            ax.tick_params(labelbottom=False)
        time_ticks(htf_ax, frame)

    panel(left, decision, outcome=False)
    panel(right, future, outcome=True)

    if is_near:
        title = (
            f"{case['case_id']} | {hypothesis_id} | OFFLINE_NEAR_MISS_DIAGNOSTIC | "
            f"{case['side']} | decision_bar server {case['time_server']} / UTC {case['time_utc']} | "
            f"failed_gates={case['failed_gates']}/{case['active_gates']} dist={case['normalized_distance']:.4f}"
        )
    else:
        net_r = "N/A" if case.get("net_R") is None else f"{float(case['net_R']):.3f}R"
        title = (
            f"{case['case_id']} | {hypothesis_id} | EXECUTED P{case['position_id']} | {case['side']} | "
            f"entry {case['entry_time_server']} @ {float(case['entry']):.2f} | "
            f"exit {case['exit_time_server']} @ {float(case['exit']):.2f} | "
            f"net {float(case['net_usd']):.2f} USD / {net_r} | hold {float(case['hold_minutes']):.1f}m"
        )
    fig.suptitle(title, fontsize=11, fontweight="bold")
    fig.text(
        0.5,
        0.035,
        f"Active surface: {RUNS[hypothesis_id]['family']} | source snapshot bound | "
        f"execution truth = StateTelemetry+Lifecycle | "
        f"decision_server={decision_time.strftime('%Y.%m.%d %H:%M:%S')}",
        ha="center",
        fontsize=8,
        color="#334155",
    )
    watermark(fig)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(image_path, dpi=110, facecolor="white")
    plt.close(fig)
    size = image_path.stat().st_size
    if size < 5_000:
        raise RuntimeError(f"blank/too-small image: {image_path} size={size}")
    return {
        "case_id": case["case_id"],
        "image": image_path.name,
        "path": str(image_path),
        "sha256": sha256_file(image_path),
        "size_bytes": size,
        "case_kind": case["case_kind"],
        "decision_bars": len(decision),
        "context_bars": len(future),
    }


def case_row_for_csv(case: dict[str, Any]) -> dict[str, Any]:
    is_near = case["case_kind"] == "OFFLINE_NEAR_MISS_DIAGNOSTIC"
    base = {
        "case_id": case["case_id"],
        "case_kind": case["case_kind"],
        "hypothesis_id": case["hypothesis_id"],
        "run_id": case.get("run_id", ""),
        "side": case.get("side", ""),
        "direction": case.get("direction", ""),
        "stratum": case.get("stratum", ""),
        "anomaly_tag": case.get("anomaly_tag", ""),
        "image": case.get("image", ""),
        "image_sha256": case.get("image_sha256", ""),
    }
    if is_near:
        base.update(
            {
                "position_id": "",
                "entry_time_server": "",
                "entry": "",
                "sl": "",
                "tp": "",
                "exit_time_server": "",
                "exit": "",
                "net_usd": "",
                "net_R": "",
                "hold_minutes": "",
                "decision_bar_server": case["time_server"],
                "decision_bar_utc": case["time_utc"],
                "failed_gates": case["failed_gates"],
                "active_gates": case["active_gates"],
                "normalized_distance": case["normalized_distance"],
                "near_miss_rank": case.get("near_miss_rank", ""),
                "offline_full_signal_unexecuted": case.get("offline_full_signal_unexecuted", False),
                "trade_fields_forbidden": True,
            }
        )
    else:
        base.update(
            {
                "position_id": case["position_id"],
                "entry_time_server": case["entry_time_server"],
                "entry": case["entry"],
                "sl": case.get("sl", ""),
                "tp": case.get("tp", ""),
                "exit_time_server": case["exit_time_server"],
                "exit": case["exit"],
                "net_usd": case["net_usd"],
                "net_R": case.get("net_R", ""),
                "hold_minutes": case["hold_minutes"],
                "decision_bar_server": case.get("decision_bar_time_server", ""),
                "decision_bar_utc": case.get("decision_utc", ""),
                "failed_gates": "",
                "active_gates": "",
                "normalized_distance": "",
                "near_miss_rank": "",
                "offline_full_signal_unexecuted": "",
                "trade_fields_forbidden": False,
                "telemetry_planned_stop": case.get("planned_stop", ""),
                "telemetry_planned_target": case.get("planned_target", ""),
            }
        )
    return base


def freeze_and_render(hypotheses: list[str] | None = None, render: bool = True) -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    hyp_list = hypotheses or list(RUNS.keys())
    print("LOADING bars + recomputing mechanism indicators...", flush=True)
    bars = load_and_enrich_bars()
    m15 = resample_htf(bars, "15min")
    h1 = resample_htf(bars, "1h")
    bars_out = OUT / "data" / "XAUUSD_M5_recomputed_007_010_indicators.parquet"
    bars_out.parent.mkdir(parents=True, exist_ok=True)
    # store a compact enriched subset
    store_cols = [
        "time_server",
        "time_utc",
        "open",
        "high",
        "low",
        "close",
        "atr14",
        "adx14",
        "pdi14",
        "mdi14",
        "rsi14",
        "ema20",
        "ema34",
        "ema50",
        "ema100",
        "bb_mid",
        "bb_upper",
        "bb_lower",
        "bb_width_atr",
        "body",
        "range",
        "donchian_high20_excl",
        "donchian_low20_excl",
        "body_median_10_prev",
        "in_session",
    ]
    bars[store_cols].to_parquet(bars_out, index=False)

    reconciliations: dict[str, Any] = {}
    selection: dict[str, Any] = {
        "schema_version": "mzms_hyp007_010_forensics_selection.v1",
        "campaign": "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400",
        "selection_frozen_before_chart_rendering": True,
        "selection_frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "history_quality_boundary": HISTORY_QUALITY_WATERMARK,
        "bars_source": {
            "path": str(BARS_SOURCE),
            "sha256": EXPECTED_BARS_SHA,
            "fidelity": "OHLC hash-bound; indicators recomputed offline for visualization/near-miss only",
        },
        "enriched_bars": {
            "path": str(bars_out),
            "sha256": sha256_file(bars_out),
            "row_count": len(bars),
        },
        "source_snapshot": {
            "path": str(SOURCE_SNAPSHOT),
            "sha256": sha256_file(SOURCE_SNAPSHOT),
        },
        "prereg": {"path": str(PREREG), "sha256": sha256_file(PREREG)},
        "design": {"path": str(DESIGN), "sha256": sha256_file(DESIGN)},
        "hypotheses": {},
    }

    all_case_results: list[dict[str, Any]] = []
    campaign_metrics: dict[str, Any] = {
        "schema_version": "mzms_hyp007_010_campaign_metrics.v1",
        "history_quality_pct": 98,
        "economic_authority": "DIAGNOSTIC_ONLY",
        "hypotheses": {},
    }

    for hypothesis_id in hyp_list:
        cfg = RUNS[hypothesis_id]
        print(f"RECONCILE {hypothesis_id} ...", flush=True)
        recon = reconcile_hypothesis(hypothesis_id)
        bound = recon.pop("bound_positions")
        reconciliations[hypothesis_id] = recon
        seed = seed_for(hypothesis_id, cfg["run_id"])
        # Full population when N <= target (008=80, 010=2); else stratified sample.
        executed = stratified_executed_sample(
            bound,
            cfg["executed_target"],
            seed=seed,
            take_all_if_leq=True,
        )
        if len(bound) <= cfg["executed_target"]:
            for p in executed:
                p["stratum"] = p.get("stratum") or "POPULATION_FULL"

        exclude = actual_signal_bar_indices(bars, bound)
        near: list[dict[str, Any]] = []
        if cfg["near_miss_target"] > 0:
            print(
                f"NEAR-MISS rank {hypothesis_id} target={cfg['near_miss_target']} ...",
                flush=True,
            )
            near = rank_near_misses(
                hypothesis_id, bars, exclude, cfg["near_miss_target"], seed=seed
            )

        cases: list[dict[str, Any]] = []
        for idx, pos in enumerate(executed, 1):
            case = dict(pos)
            case["hypothesis_id"] = hypothesis_id
            case["run_id"] = cfg["run_id"]
            case["case_id"] = f"{cfg['short']}-E{idx:03d}-P{pos['position_id']}"
            # serialize times
            case["entry_time"] = pos["entry_time"]
            case["exit_time"] = pos["exit_time"]
            cases.append(case)
        for idx, nm in enumerate(near, 1):
            case = dict(nm)
            case["hypothesis_id"] = hypothesis_id
            case["run_id"] = cfg["run_id"]
            case["case_id"] = f"{cfg['short']}-N{idx:03d}-B{nm['bar_index']}"
            cases.append(case)

        if len(cases) != 100:
            raise RuntimeError(f"{hypothesis_id}: expected 100 cases, got {len(cases)}")

        hyp_dir = OUT / hypothesis_id
        chart_dir = hyp_dir / "charts"
        chart_dir.mkdir(parents=True, exist_ok=True)

        image_records: list[dict[str, Any]] = []
        if render:
            for i, case in enumerate(cases, 1):
                image_path = chart_dir / f"{case['case_id']}_forensics.png"
                rec = render_case(hypothesis_id, case, bars, m15, h1, image_path)
                case["image"] = rec["image"]
                case["image_sha256"] = rec["sha256"]
                image_records.append(rec)
                if i % 10 == 0 or i == len(cases):
                    print(f"RENDER {hypothesis_id} {i}/{len(cases)}", flush=True)
        else:
            for case in cases:
                case["image"] = ""
                case["image_sha256"] = ""

        # write cases.csv
        csv_path = hyp_dir / "cases.csv"
        rows = [case_row_for_csv(c) for c in cases]
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        selection["hypotheses"][hypothesis_id] = {
            "run_id": cfg["run_id"],
            "seed": seed,
            "seed_material": f"{hypothesis_id}|{cfg['run_id']}|GROK_FORENSICS_400",
            "executed_count": len(executed),
            "near_miss_count": len(near),
            "total_cases": len(cases),
            "population_positions": recon["positions"],
            "sampling": (
                "full population"
                if len(bound) <= cfg["executed_target"]
                else "stratified winner/loser/year/direction/anomaly"
            ),
            "near_miss_method": (
                "fewest failed active gates, then normalized distance; "
                "time-diversified min_gap=288 M5 bars; exclude actual entry signal bars; "
                "label OFFLINE_NEAR_MISS_DIAGNOSTIC; no invented entry/SL/TP/PnL"
                if near
                else "n/a"
            ),
            "case_ids": [c["case_id"] for c in cases],
            "executed_position_ids": [int(c["position_id"]) for c in executed],
            "near_miss_bar_indices": [int(c["bar_index"]) for c in near],
            "cases_csv": str(csv_path),
            "cases_csv_sha256": sha256_file(csv_path),
            "charts_dir": str(chart_dir),
        }

        campaign_metrics["hypotheses"][hypothesis_id] = {
            "run_id": cfg["run_id"],
            "positions": recon["positions"],
            "net_usd": recon["net_usd_lifecycle"],
            "profit_factor": recon["profit_factor_lifecycle"],
            "win_rate_pct": recon["win_rate_pct_lifecycle"],
            "expectancy_per_trade": recon["expectancy_per_trade_lifecycle"],
            "history_quality_pct": recon["history_quality_pct"],
            "winners": recon["winners"],
            "losers": recon["losers"],
            "flats": recon["flats"],
            "selected_executed": len(executed),
            "selected_near_miss": len(near),
            "exact_reconciliation": recon["exact_reconciliation"],
        }

        for rec in image_records:
            rec["hypothesis_id"] = hypothesis_id
            all_case_results.append(rec)

    recon_path = OUT / "lifecycle_reconciliation.json"
    # strip non-serializable if any
    recon_path.write_text(json.dumps(reconciliations, indent=2, default=str), encoding="utf-8")
    sel_path = OUT / "selection_manifest.json"
    # cases detail without raw telemetry blobs
    sel_serializable = json.loads(json.dumps(selection, default=str))
    sel_path.write_text(json.dumps(sel_serializable, indent=2), encoding="utf-8")

    casebook = {
        "schema_version": "mzms_hyp007_010_casebook.v1",
        "campaign": "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400",
        "history_quality_watermark": HISTORY_QUALITY_WATERMARK,
        "indicator_fidelity_boundary": (
            "Offline recomputed atr_mt5/adx_mt5/rsi_wilder/ema/BB/Donchian from hash-bound "
            "M5 OHLC for visualization and near-miss ranking only. Not MT5 CopyBuffer parity. "
            "Execution truth = StateTelemetry + Lifecycle."
        ),
        "source_snapshot_sha256": sha256_file(SOURCE_SNAPSHOT),
        "prereg_sha256": sha256_file(PREREG),
        "design_sha256": sha256_file(DESIGN),
        "bars_source_sha256": EXPECTED_BARS_SHA,
        "enriched_bars_sha256": sha256_file(bars_out),
        "selection_manifest": str(sel_path),
        "selection_manifest_sha256": sha256_file(sel_path),
        "lifecycle_reconciliation": str(recon_path),
        "lifecycle_reconciliation_sha256": sha256_file(recon_path),
        "image_count": len(all_case_results),
        "expected_image_count": 400 if render and len(hyp_list) == 4 else len(hyp_list) * 100 if render else 0,
        "results": all_case_results,
        "per_hypothesis_counts": {
            hid: {
                "executed": selection["hypotheses"][hid]["executed_count"],
                "near_miss": selection["hypotheses"][hid]["near_miss_count"],
                "pngs": sum(1 for r in all_case_results if r["hypothesis_id"] == hid),
            }
            for hid in hyp_list
        },
    }
    casebook_path = OUT / "casebook_manifest.json"
    casebook_path.write_text(json.dumps(casebook, indent=2), encoding="utf-8")

    campaign_metrics["artifact_paths"] = {
        "out_dir": str(OUT),
        "selection_manifest": str(sel_path),
        "lifecycle_reconciliation": str(recon_path),
        "casebook_manifest": str(casebook_path),
        "enriched_bars": str(bars_out),
    }
    metrics_path = OUT / "campaign_metrics.json"
    metrics_path.write_text(json.dumps(campaign_metrics, indent=2), encoding="utf-8")

    if render:
        validate_corpus(hyp_list)

    summary = {
        "out": str(OUT),
        "reconciliations": {k: {kk: vv for kk, vv in v.items() if kk != "source_artifacts"} for k, v in reconciliations.items()},
        "counts": casebook["per_hypothesis_counts"],
        "selection_manifest": str(sel_path),
        "casebook_manifest": str(casebook_path),
        "campaign_metrics": str(metrics_path),
    }
    print(json.dumps(summary, indent=2, default=str))
    return summary


def validate_corpus(hypotheses: list[str] | None = None) -> None:
    hyp_list = hypotheses or list(RUNS.keys())
    casebook = json.loads((OUT / "casebook_manifest.json").read_text(encoding="utf-8"))
    selection = json.loads((OUT / "selection_manifest.json").read_text(encoding="utf-8"))
    all_ids: set[str] = set()
    for hid in hyp_list:
        cfg = RUNS[hid]
        hyp_dir = OUT / hid
        csv_path = hyp_dir / "cases.csv"
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 100:
            raise RuntimeError(f"{hid}: cases.csv rows {len(rows)} != 100")
        executed = [r for r in rows if r["case_kind"] == "EXECUTED"]
        near = [r for r in rows if r["case_kind"] == "OFFLINE_NEAR_MISS_DIAGNOSTIC"]
        if len(executed) != cfg["executed_target"] or len(near) != cfg["near_miss_target"]:
            raise RuntimeError(
                f"{hid}: executed/near-miss {len(executed)}/{len(near)} != "
                f"{cfg['executed_target']}/{cfg['near_miss_target']}"
            )
        for r in near:
            for field in ("entry", "sl", "tp", "exit", "net_usd", "net_R", "position_id"):
                if str(r.get(field, "")).strip() not in {"", "None"}:
                    raise RuntimeError(f"{hid}: near-miss {r['case_id']} has fake field {field}={r.get(field)}")
        pngs = list((hyp_dir / "charts").glob("*.png"))
        if len(pngs) != 100:
            raise RuntimeError(f"{hid}: png count {len(pngs)} != 100")
        for r in rows:
            cid = r["case_id"]
            if cid in all_ids:
                raise RuntimeError(f"duplicate case_id {cid}")
            all_ids.add(cid)
            img = hyp_dir / "charts" / r["image"]
            if not img.exists() or img.stat().st_size < 5000:
                raise RuntimeError(f"missing/blank image for {cid}")
        # selection counts
        sel = selection["hypotheses"][hid]
        if sel["executed_count"] != cfg["executed_target"]:
            raise RuntimeError(f"{hid}: selection executed mismatch")
        if sel["near_miss_count"] != cfg["near_miss_target"]:
            raise RuntimeError(f"{hid}: selection near-miss mismatch")
    if len(hyp_list) == 4 and len(all_ids) != 400:
        raise RuntimeError(f"unique case ids {len(all_ids)} != 400")
    print(f"VALIDATE_OK hypotheses={hyp_list} unique_cases={len(all_ids)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hypotheses",
        nargs="*",
        default=None,
        help="Optional subset of hypothesis IDs",
    )
    parser.add_argument("--no-render", action="store_true", help="Freeze selection only")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        validate_corpus(args.hypotheses)
        return
    freeze_and_render(args.hypotheses, render=not args.no_render)


if __name__ == "__main__":
    main()
