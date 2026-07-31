#!/usr/bin/env python3
"""Prepare and render frozen HYP-002 setup/chart forensics."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).resolve()
PACKAGE = MODULE_PATH.parents[1]
WORKSPACE = MODULE_PATH.parents[3]
HYPOTHESIS_ID = "HYP-CME6E-RAWBREAK-BOOKTRANSITION-002"
THRESHOLD = -0.012342488801680875

PLAN_PATH = PACKAGE / "research" / f"{HYPOTHESIS_ID}_CHART_FORENSICS_PLAN.md"
PLAN_SHA256 = "5E26798433E3837D9A6FAF59C5D310C919647BB495CCCA723CC0E32ADE7E09F8"
EVIDENCE_ROOT = PACKAGE / "research" / "evidence" / f"{HYPOTHESIS_ID}_CHART_FORENSICS"
PROBE_ROOT = PACKAGE / "research" / "evidence" / f"{HYPOTHESIS_ID}_DESIGN"
JOINED_PATH = PROBE_ROOT / "joined_design_trades.csv"
JOINED_SHA256 = "7B19591BED7802F70A15A9C628EE46D236B7AA7BE610BC49E9758FB8EBBE3069"
RESULT_PATH = PROBE_ROOT / "probe_result.json"
RESULT_SHA256 = "7736F456C2685AFCE15C6761C70AA5CFB75E4B29A009377B13B975BBD5E0265E"

RUN_ROOT = WORKSPACE / "02. AlphaFactory" / "runs" / "EA_SweepCascadeContinuation" / "20260725_210715"
MANIFEST_PATH = RUN_ROOT / "run_manifest.json"
MANIFEST_SHA256 = "6F88B403B869A010262953C5741E0F9856D2493ABDCC734FEA5E858BF3259D84"
REPORT_PATH = RUN_ROOT / "report.html"
REPORT_SHA256 = "FA8F40FBE0BF194486509548010B05D1BD7C64336601E97C5C5EFDC13F0D270F"
RUN_META_PATH = RUN_ROOT / "logs" / "EURUSD_RunMeta_HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_134509171.json"
RUN_META_SHA256 = "8DB131F7BAC833F9A48B2C2B84D607D201594210E818DA21299D3BAFB8E28E78"
LIFECYCLE_PATH = RUN_ROOT / "logs" / "EURUSD_LifecycleTrades_HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_134509171.csv"
LIFECYCLE_SHA256 = "515EFB5F5D4F86C54A2442206F9B508D1B2F7CDE5C0CF77A45F8250124A023C5"
TELEMETRY_PATH = RUN_ROOT / "logs" / "EURUSD_DecisionTelemetry_HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_134509171.csv"
TELEMETRY_SHA256 = "B5714589986D9B4E06B460C47AC38B7FB7C02FA30B1C36199157018314DA3C78"
SOURCE_PATH = RUN_ROOT / "snapshot" / "source" / "EA_SweepCascadeContinuation.mq5"
SOURCE_SHA256 = "9C03F4CB913E18B6CF660E48E7ADBD86034B1352A80167C32CC238BA7F7817B3"
OVERRIDES_PATH = RUN_ROOT / "overrides.txt"
OVERRIDES_SHA256 = "0FCE3AE70CB8241197547550760C148C078BF3A1DCDCA85E3FCD30ACA0C5762E"
NONREPAINT_PATH = RUN_ROOT / "analysis" / "nonrepaint_audit.json"
NONREPAINT_SHA256 = "A0FEA4EF075569A0776745A1680BD7FF334FADF275742FB531C14C0A9781A30E"

CONTROL_PATH = WORKSPACE / "03. EA Developer" / "EA_SweepCascadeContinuation" / "research" / "evidence" / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS" / "control_trades.csv"
CONTROL_SHA256 = "07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9"
BARS_PATH = WORKSPACE / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
BARS_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
CLOCK_PATH = WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
FEATURE_EXTRACTOR_PATH = PACKAGE / "research" / "extract_cme6e_breakbar_transition_features.py"
FEATURE_EXTRACTOR_SHA256 = "E1DA8963A05FFFCDF3745E02EB1051B5E54DADCCD998145B3B6DEE6A3DA1402B"
BASE_PATH = PACKAGE / "research" / "analyze_raw_break_book_chart_forensics.py"
BASE_SHA256 = "5DE0157F883E1041B7887A3539B0E3AFD1DFF209864199DB11C1475CE63A5367"
RAW_ROOT = WORKSPACE / "02. AlphaFactory" / "data" / "databento" / "cme_6e_breakbar_transition_design" / "raw"

CASE_PATH = EVIDENCE_ROOT / "case_selection.csv"
SAMPLE_MANIFEST_PATH = EVIDENCE_ROOT / "sample_manifest.json"
POPULATION_PATH = EVIDENCE_ROOT / "forensic_population.csv"
ANALYSIS_PATH = EVIDENCE_ROOT / "population_analysis.json"
BOOK_TRACE_PATH = EVIDENCE_ROOT / "book_traces.csv"
BOOK_RECEIPT_PATH = EVIDENCE_ROOT / "book_trace_receipt.json"
CHART_MANIFEST_PATH = EVIDENCE_ROOT / "chart_manifest.json"


class ForensicError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require_sha(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ForensicError(f"SHA mismatch for {path}: expected={expected} actual={actual}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ForensicError(f"cannot load module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def utc_session(hour: int) -> str:
    if 0 <= hour < 7:
        return "ASIA"
    if 7 <= hour < 13:
        return "LONDON"
    if 13 <= hour < 21:
        return "NEW_YORK"
    return "ROLLOVER"


def aggregate_lifecycle(lifecycle: pd.DataFrame) -> pd.DataFrame:
    frame = lifecycle.copy()
    frame["position_id"] = frame["position_id"].astype(str)
    numeric = [
        "deal_profit",
        "deal_commission",
        "deal_swap",
        "deal_fee",
        "deal_net",
        "is_final_close",
    ]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    grouped = frame.groupby("position_id", as_index=False).agg(
        lifecycle_rows=("position_id", "size"),
        price_profit_before_explicit_cost=("deal_profit", "sum"),
        lifecycle_commission=("deal_commission", "sum"),
        lifecycle_swap=("deal_swap", "sum"),
        lifecycle_fee=("deal_fee", "sum"),
        lifecycle_net=("deal_net", "sum"),
        final_close_rows=("is_final_close", "sum"),
    )
    grouped["explicit_cost_account"] = -(
        grouped["lifecycle_commission"]
        + grouped["lifecycle_swap"]
        + grouped["lifecycle_fee"]
    )
    return grouped


def compute_preentry_context(
    bars: pd.DataFrame, entry_time: pd.Timestamp, direction: str
) -> dict[str, Any]:
    frame = bars.copy()
    frame["time_utc"] = pd.to_datetime(frame["time_utc"])
    frame = frame[frame["time_utc"] < pd.Timestamp(entry_time)].sort_values("time_utc")
    if frame.empty:
        raise ForensicError(f"no pre-entry bars for {entry_time}")
    sign = 1.0 if str(direction).upper() == "BUY" else -1.0
    pre60 = frame[frame["time_utc"] >= pd.Timestamp(entry_time) - pd.Timedelta(minutes=60)]
    prior24 = frame[frame["time_utc"] >= pd.Timestamp(entry_time) - pd.Timedelta(hours=24)]
    if len(pre60) < 2 or prior24.empty:
        raise ForensicError(f"insufficient pre-entry context for {entry_time}")
    last_close = float(frame.iloc[-1]["close"])
    pre60_return = sign * (float(pre60.iloc[-1]["close"]) - float(pre60.iloc[0]["close"])) / 0.0001
    pre60_range = (float(pre60["high"].max()) - float(pre60["low"].min())) / 0.0001
    prior24_low = float(prior24["low"].min())
    prior24_high = float(prior24["high"].max())
    location = (
        (last_close - prior24_low) / (prior24_high - prior24_low)
        if prior24_high > prior24_low
        else 0.5
    )
    h1_source = frame[frame["time_utc"] >= pd.Timestamp(entry_time) - pd.Timedelta(hours=14)]
    h1 = (
        h1_source.set_index("time_utc")[["open", "high", "low", "close"]]
        .resample("1h", label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
    )
    h1_return = (
        sign * (float(h1.iloc[-1]["close"]) - float(h1.iloc[0]["close"])) / 0.0001
        if len(h1) >= 2
        else None
    )
    return {
        "context_last_bar_utc": pd.Timestamp(frame.iloc[-1]["time_utc"]).isoformat(),
        "pre60_aligned_return_pips": pre60_return,
        "pre60_range_pips": pre60_range,
        "entry_location_prior24h": location,
        "aligned_entry_location_prior24h": location if sign > 0 else 1.0 - location,
        "h1_12h_aligned_return_pips": h1_return,
    }


def grouped_metrics(base: Any, frame: pd.DataFrame, field: str) -> dict[str, Any]:
    return {
        str(key): base.basic_metrics(group)
        for key, group in frame.groupby(field, observed=True)
    }


def standardized_mean_difference(winners: pd.Series, losers: pd.Series) -> float | None:
    winners = pd.to_numeric(winners, errors="coerce").dropna()
    losers = pd.to_numeric(losers, errors="coerce").dropna()
    if len(winners) < 2 or len(losers) < 2:
        return None
    pooled = math.sqrt((float(winners.var(ddof=1)) + float(losers.var(ddof=1))) / 2.0)
    if pooled == 0:
        return 0.0
    return (float(winners.mean()) - float(losers.mean())) / pooled


def profit_factor(values: pd.Series) -> float | None:
    values = pd.to_numeric(values, errors="coerce").dropna()
    gross_profit = float(values[values > 0].sum())
    gross_loss = float(-values[values < 0].sum())
    return gross_profit / gross_loss if gross_loss > 0 else None


def validate_inputs() -> None:
    bindings = (
        (PLAN_PATH, PLAN_SHA256),
        (JOINED_PATH, JOINED_SHA256),
        (RESULT_PATH, RESULT_SHA256),
        (MANIFEST_PATH, MANIFEST_SHA256),
        (REPORT_PATH, REPORT_SHA256),
        (RUN_META_PATH, RUN_META_SHA256),
        (LIFECYCLE_PATH, LIFECYCLE_SHA256),
        (TELEMETRY_PATH, TELEMETRY_SHA256),
        (SOURCE_PATH, SOURCE_SHA256),
        (OVERRIDES_PATH, OVERRIDES_SHA256),
        (NONREPAINT_PATH, NONREPAINT_SHA256),
        (CONTROL_PATH, CONTROL_SHA256),
        (BARS_PATH, BARS_SHA256),
        (CLOCK_PATH, CLOCK_SHA256),
        (FEATURE_EXTRACTOR_PATH, FEATURE_EXTRACTOR_SHA256),
        (BASE_PATH, BASE_SHA256),
    )
    for path, expected in bindings:
        require_sha(path, expected)
    run_meta = json.loads(RUN_META_PATH.read_text(encoding="utf-8"))
    if run_meta.get("variant_tag") != "CONTROL_FIRST_CLOSE_BREAK":
        raise ForensicError("parent run active signal mode mismatch")
    if run_meta.get("hold_retest_enabled") is not False:
        raise ForensicError("parent run unexpectedly enabled HOLD/retest")
    audit = json.loads(NONREPAINT_PATH.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS" or audit.get("findings") != []:
        raise ForensicError("parent source non-repaint audit is not clean")


def load_control_rows(allowed_ids: set[str]) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    with CONTROL_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            position_id = str(row["position_id"])
            if position_id not in allowed_ids:
                continue
            if position_id in seen:
                raise ForensicError(f"duplicate control identity {position_id}")
            rows.append(dict(row))
            seen.add(position_id)
    if seen != allowed_ids:
        raise ForensicError("control/HYP-002 identity mismatch")
    return pd.DataFrame(rows, dtype=str)


def load_population() -> pd.DataFrame:
    validate_inputs()
    joined = pd.read_csv(JOINED_PATH, dtype={"position_id": str})
    joined["quality_eligible"] = joined["quality_eligible"].astype(str).str.lower().eq("true")
    challenger = joined[
        joined["quality_eligible"]
        & (joined["book_transition_score"].astype(float) >= THRESHOLD)
    ].copy()
    if len(challenger) != 258:
        raise ForensicError(f"challenger population mismatch: {len(challenger)}")

    allowed_ids = set(challenger["position_id"].astype(str))
    full = load_control_rows(allowed_ids)
    outcome_columns = [
        "position_id",
        "open_time",
        "close_time",
        "decision_time",
        "direction",
        "volume",
        "entry",
        "exit",
        "planned_stop",
        "planned_target",
        "risk_points",
        "initial_risk_account",
        "net",
        "realized_r",
    ]
    drop_overlap = [
        column
        for column in (
            "volume",
            "net",
            "realized_r",
            "initial_risk_account",
            "decision_time_server",
            "open_time_server",
            "break_bar_open_utc",
            "actual_decision_utc",
            "decision_year",
        )
        if column in challenger.columns
    ]
    merged = challenger.drop(columns=drop_overlap).merge(
        full[outcome_columns],
        on=["position_id", "direction"],
        how="inner",
        validate="one_to_one",
    )

    clock = load_module(CLOCK_PATH, "hyp002_forensic_clock")

    def server_utc(value: str) -> pd.Timestamp:
        raw = datetime.strptime(value, "%Y.%m.%d %H:%M:%S")
        return pd.Timestamp(clock.server_to_utc(raw))

    merged["decision_time_utc"] = merged["decision_time"].map(server_utc)
    merged["entry_time_utc"] = merged["open_time"].map(server_utc)
    merged["exit_time_utc"] = merged["close_time"].map(server_utc)
    expected_break = pd.to_datetime(merged["break_bar_open"], utc=True).dt.tz_convert(None)
    expected_entry = pd.to_datetime(merged["actual_decision"], utc=True).dt.tz_convert(None)
    if not (merged["decision_time_utc"].reset_index(drop=True) == expected_break.reset_index(drop=True)).all():
        raise ForensicError("break-bar clock mismatch")
    if not (merged["entry_time_utc"].reset_index(drop=True) == expected_entry.reset_index(drop=True)).all():
        raise ForensicError("actual-entry clock mismatch")

    numeric = [
        "volume",
        "entry",
        "exit",
        "planned_stop",
        "planned_target",
        "risk_points",
        "initial_risk_account",
        "net",
        "realized_r",
        "book_transition_score",
    ]
    for column in numeric:
        merged[column] = pd.to_numeric(merged[column], errors="raise")

    telemetry = pd.read_csv(TELEMETRY_PATH)
    telemetry = telemetry[
        (telemetry["event"] == "CONTROL_BREAK_ENTRY")
        & (telemetry["status"] == "ORDER_ACCEPTED")
    ].copy()
    telemetry["direction"] = telemetry["direction"].map({1: "BUY", -1: "SELL"})
    telemetry = telemetry.rename(
        columns={
            "server_time": "decision_time",
            "level": "break_level",
            "open": "break_open",
            "high": "break_high",
            "low": "break_low",
            "close": "break_close",
            "atr": "break_atr",
            "spread_pips": "entry_spread_pips",
        }
    )
    telemetry_fields = [
        "decision_time",
        "direction",
        "break_level",
        "break_open",
        "break_high",
        "break_low",
        "break_close",
        "break_atr",
        "entry_spread_pips",
    ]
    if telemetry.duplicated(["decision_time", "direction"]).any():
        raise ForensicError("duplicate accepted decision telemetry identity")
    merged = merged.merge(
        telemetry[telemetry_fields],
        on=["decision_time", "direction"],
        how="left",
        validate="one_to_one",
    )
    if merged["break_atr"].isna().any():
        raise ForensicError("accepted telemetry missing for HYP-002 population")
    for column in telemetry_fields[2:]:
        merged[column] = pd.to_numeric(merged[column], errors="raise")

    sign = merged["direction"].map({"BUY": 1.0, "SELL": -1.0})
    merged["stop_pips"] = (merged["entry"] - merged["planned_stop"]).abs() / 0.0001
    merged["target_pips"] = (merged["planned_target"] - merged["entry"]).abs() / 0.0001
    merged["hold_minutes"] = (
        merged["exit_time_utc"] - merged["entry_time_utc"]
    ).dt.total_seconds() / 60.0
    merged["entry_minute_utc"] = merged["entry_time_utc"].dt.hour * 60 + merged["entry_time_utc"].dt.minute
    merged["entry_hour_utc"] = merged["entry_time_utc"].dt.hour
    merged["entry_session_utc"] = merged["entry_hour_utc"].map(utc_session)
    merged["entry_weekday"] = merged["entry_time_utc"].dt.day_name()
    merged["entry_month"] = merged["entry_time_utc"].dt.strftime("%Y-%m")
    merged["entry_year"] = merged["entry_time_utc"].dt.year
    merged["break_range_pips"] = (merged["break_high"] - merged["break_low"]) / 0.0001
    merged["break_body_fraction"] = (
        (merged["break_close"] - merged["break_open"]).abs()
        / (merged["break_high"] - merged["break_low"]).replace(0, np.nan)
    )
    merged["break_close_location"] = (
        (merged["break_close"] - merged["break_low"])
        / (merged["break_high"] - merged["break_low"]).replace(0, np.nan)
    )
    merged["aligned_break_close_location"] = np.where(
        sign > 0,
        merged["break_close_location"],
        1.0 - merged["break_close_location"],
    )
    merged["break_atr_pips"] = merged["break_atr"] / 0.0001
    merged["break_range_atr"] = (
        merged["break_high"] - merged["break_low"]
    ) / merged["break_atr"]
    merged["close_beyond_pivot_pips"] = sign * (
        merged["break_close"] - merged["break_level"]
    ) / 0.0001
    merged["entry_gap_from_break_close_pips"] = sign * (
        merged["entry"] - merged["break_close"]
    ) / 0.0001

    base = load_module(BASE_PATH, "hyp002_forensic_base")
    merged["exit_class"] = merged.apply(base.classify_exit, axis=1)

    lifecycle = pd.read_csv(LIFECYCLE_PATH, dtype={"position_id": str})
    lifecycle = lifecycle[lifecycle["position_id"].isin(allowed_ids)]
    lifecycle_agg = aggregate_lifecycle(lifecycle)
    merged = merged.merge(lifecycle_agg, on="position_id", how="left", validate="one_to_one")
    if merged["lifecycle_net"].isna().any():
        raise ForensicError("lifecycle rows missing for HYP-002 population")
    if not np.allclose(merged["lifecycle_net"], merged["net"], atol=1e-8):
        raise ForensicError("lifecycle net does not reconcile to joined outcome")
    if not ((merged["lifecycle_rows"] == 2) & (merged["final_close_rows"] == 1)).all():
        raise ForensicError("partial or incomplete lifecycle detected")

    bars = pd.read_parquet(BARS_PATH, columns=["time_utc", "open", "high", "low", "close"])
    bars["time_utc"] = pd.to_datetime(bars["time_utc"])
    bars = bars.drop_duplicates("time_utc", keep=False).sort_values("time_utc")
    contexts = [
        compute_preentry_context(bars, row["entry_time_utc"], row["direction"])
        for _, row in merged.iterrows()
    ]
    merged = pd.concat([merged.reset_index(drop=True), pd.DataFrame(contexts)], axis=1)
    merged = base.add_path_geometry(merged)
    merged["book_alignment_score"] = merged["book_transition_score"]
    return merged.sort_values(["entry_time_utc", "position_id"]).reset_index(drop=True)


def context_comparison(population: pd.DataFrame) -> dict[str, Any]:
    winners = population[population["net"] > 0]
    losers = population[population["net"] <= 0]
    fields = (
        "book_transition_score",
        "aligned_imbalance_transition",
        "aligned_imbalance_median_late60",
        "aligned_persistence_full",
        "break_range_atr",
        "break_body_fraction",
        "aligned_break_close_location",
        "close_beyond_pivot_pips",
        "entry_gap_from_break_close_pips",
        "stop_pips",
        "entry_spread_pips",
        "pre60_aligned_return_pips",
        "pre60_range_pips",
        "aligned_entry_location_prior24h",
        "h1_12h_aligned_return_pips",
        "mfe_5m_r",
        "mae_5m_r",
        "mfe_r",
        "mae_r",
    )
    return {
        field: {
            "winner_count": int(winners[field].notna().sum()),
            "loser_count": int(losers[field].notna().sum()),
            "winner_median": finite_or_none(winners[field].median()),
            "loser_median": finite_or_none(losers[field].median()),
            "standardized_mean_difference": finite_or_none(
                standardized_mean_difference(winners[field], losers[field])
            ),
        }
        for field in fields
    }


def matched_comparisons(selected: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for direction in ("BUY", "SELL"):
        winner = selected[selected["stratum"] == f"MATCHED_{direction}_WIN"].iloc[0]
        loser = selected[selected["stratum"] == f"MATCHED_{direction}_LOSS"].iloc[0]
        rows.append(
            {
                "direction": direction,
                "winner_position_id": str(winner["position_id"]),
                "loser_position_id": str(loser["position_id"]),
                "winner_realized_r": float(winner["realized_r"]),
                "loser_realized_r": float(loser["realized_r"]),
                "winner_transition_score": float(winner["book_transition_score"]),
                "loser_transition_score": float(loser["book_transition_score"]),
                "winner_break_range_atr": float(winner["break_range_atr"]),
                "loser_break_range_atr": float(loser["break_range_atr"]),
                "winner_pre60_aligned_return_pips": float(winner["pre60_aligned_return_pips"]),
                "loser_pre60_aligned_return_pips": float(loser["pre60_aligned_return_pips"]),
                "winner_h1_12h_aligned_return_pips": finite_or_none(winner["h1_12h_aligned_return_pips"]),
                "loser_h1_12h_aligned_return_pips": finite_or_none(loser["h1_12h_aligned_return_pips"]),
            }
        )
    return rows


def prepare() -> None:
    if any(path.exists() for path in (CASE_PATH, SAMPLE_MANIFEST_PATH, POPULATION_PATH, ANALYSIS_PATH)):
        raise ForensicError("forensic selection evidence already exists; refusing implicit resample")
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    base = load_module(BASE_PATH, "hyp002_prepare_base")
    population = load_population()
    selected = base.select_cases(population)
    population.to_csv(POPULATION_PATH, index=False)
    selected.to_csv(CASE_PATH, index=False)

    population["stop_width_quartile"] = pd.qcut(
        population["stop_pips"], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop"
    )
    population["hold_bucket"] = pd.cut(
        population["hold_minutes"],
        [-np.inf, 15, 60, 120, np.inf],
        labels=["LE15", "15_TO_60", "60_TO_120", "GT120"],
    )
    all_eligible = pd.read_csv(JOINED_PATH, dtype={"position_id": str})
    all_eligible["quality_eligible"] = all_eligible["quality_eligible"].astype(str).str.lower().eq("true")
    all_eligible = all_eligible[all_eligible["quality_eligible"]].copy()
    all_eligible["score_decile"] = pd.qcut(
        all_eligible["book_transition_score"], 10, labels=False, duplicates="drop"
    )

    nets = population["net"].astype(float)
    worst10 = population.nsmallest(10, "net")
    best10 = population.nlargest(10, "net")
    before_cost = population["price_profit_before_explicit_cost"]
    analysis = {
        "schema_version": "cme6e_breakbar_transition_chart_forensics_analysis.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "epistemic_class": "POST_OUTCOME_DESCRIPTIVE_NO_RULE_AUTHORITY",
        "active_signal_mode": "CONTROL_FIRST_CLOSE_BREAK",
        "population": base.basic_metrics(population),
        "lifecycle_cost": {
            "positions_reconciled": int(len(population)),
            "lifecycle_rows": int(population["lifecycle_rows"].sum()),
            "partial_close_positions": int(((population["lifecycle_rows"] != 2) | (population["final_close_rows"] != 1)).sum()),
            "explicit_commission_swap_fee_total": float(population["explicit_cost_account"].sum()),
            "explicit_cost_per_trade_mean": float(population["explicit_cost_account"].mean()),
            "price_profit_before_explicit_cost_total": float(before_cost.sum()),
            "price_profit_before_explicit_cost_pf": profit_factor(before_cost),
            "native_net_after_explicit_cost": float(population["lifecycle_net"].sum()),
            "spread_provenance": "EMBEDDED_IN_EXECUTION_NOT_SEPARABLE_FROM_LEDGER",
            "cost_status": "UNVERIFIED_DIAGNOSTIC_ONLY",
            "rejected_tca_summary_reason": "filename discovery returned zero lifecycle rows",
        },
        "rank_association": {
            "score_vs_realized_r_spearman": finite_or_none(
                population["book_transition_score"].corr(population["realized_r"], method="spearman")
            ),
            "score_vs_net_spearman": finite_or_none(
                population["book_transition_score"].corr(population["net"], method="spearman")
            ),
        },
        "winner_loser_context": context_comparison(population),
        "matched_comparisons": matched_comparisons(selected),
        "tail_contribution": {
            "worst_10_net": float(worst10["net"].sum()),
            "best_10_net": float(best10["net"].sum()),
            "worst_10_share_of_absolute_loss": float(-worst10["net"].sum() / -nets[nets < 0].sum()),
            "best_10_share_of_gross_profit": float(best10["net"].sum() / nets[nets > 0].sum()),
        },
        "buckets": {
            "year": grouped_metrics(base, population, "entry_year"),
            "month": grouped_metrics(base, population, "entry_month"),
            "session_utc": grouped_metrics(base, population, "entry_session_utc"),
            "utc_hour": grouped_metrics(base, population, "entry_hour_utc"),
            "weekday": grouped_metrics(base, population, "entry_weekday"),
            "direction": grouped_metrics(base, population, "direction"),
            "exit_class": grouped_metrics(base, population, "exit_class"),
            "hold": grouped_metrics(base, population, "hold_bucket"),
            "stop_width_quartile": grouped_metrics(base, population, "stop_width_quartile"),
            "eligible_score_decile": grouped_metrics(base, all_eligible, "score_decile"),
        },
        "source_hashes": {
            "plan": PLAN_SHA256,
            "joined": JOINED_SHA256,
            "result": RESULT_SHA256,
            "run_manifest": MANIFEST_SHA256,
            "report": REPORT_SHA256,
            "run_meta": RUN_META_SHA256,
            "lifecycle": LIFECYCLE_SHA256,
            "telemetry": TELEMETRY_SHA256,
            "source": SOURCE_SHA256,
            "bars": BARS_SHA256,
            "clock": CLOCK_SHA256,
        },
        "terminal_verdict_changed": False,
    }
    json_write(ANALYSIS_PATH, analysis)
    manifest = {
        "schema_version": "cme6e_breakbar_transition_chart_sample.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sampling_plan_path": str(PLAN_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
        "sampling_plan_sha256": PLAN_SHA256,
        "population_rows": 258,
        "sample_rows": 12,
        "case_path": str(CASE_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
        "case_sha256": sha256_file(CASE_PATH),
        "population_path": str(POPULATION_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
        "population_sha256": sha256_file(POPULATION_PATH),
        "analysis_path": str(ANALYSIS_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
        "analysis_sha256": sha256_file(ANALYSIS_PATH),
        "position_ids_in_frozen_order": selected["position_id"].astype(str).tolist(),
        "strata_in_frozen_order": selected["stratum"].tolist(),
        "selection_written_before_chart_viewing": True,
        "terminal_verdict_changed": False,
    }
    json_write(SAMPLE_MANIFEST_PATH, manifest)
    print(
        "BREAKBAR_CHART_FORENSICS_PREPARE_OK "
        f"population=258 sample=12 manifest_sha256={sha256_file(SAMPLE_MANIFEST_PATH)}"
    )


def extract_book() -> None:
    if BOOK_TRACE_PATH.exists() or BOOK_RECEIPT_PATH.exists():
        raise ForensicError("book trace evidence already exists")
    require_sha(PLAN_PATH, PLAN_SHA256)
    cases = pd.read_csv(CASE_PATH, dtype={"position_id": str})
    manifest = json.loads(SAMPLE_MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("case_sha256") != sha256_file(CASE_PATH):
        raise ForensicError("sample manifest binding mismatch")
    try:
        import databento as db
    except ImportError as exc:
        raise ForensicError("Databento SDK required for book trace extraction") from exc
    extractor = load_module(FEATURE_EXTRACTOR_PATH, "hyp002_bound_feature_extractor")
    require_sha(FEATURE_EXTRACTOR_PATH, FEATURE_EXTRACTOR_SHA256)
    rows: list[dict[str, Any]] = []
    raw_bindings: dict[str, str] = {}
    for _, case in cases.iterrows():
        filename = str(case["filename"])
        path = RAW_ROOT / filename
        raw_bindings[filename] = sha256_file(path)
        start_ns = int(pd.Timestamp(case["break_bar_open"]).timestamp() * 1_000_000_000)
        end_ns = int(pd.Timestamp(case["actual_decision"]).timestamp() * 1_000_000_000)
        sign = 1.0 if case["direction"] == "BUY" else -1.0
        for message in db.DBNStore.from_file(path):
            observation = extractor._observation(message)
            if observation is None:
                continue
            if observation["ts_event"] < start_ns or observation["ts_recv"] < start_ns:
                continue
            if observation["ts_event"] >= end_ns or observation["ts_recv"] >= end_ns:
                continue
            rows.append(
                {
                    "case_id": case["case_id"],
                    "position_id": str(case["position_id"]),
                    "ts_recv_utc": pd.Timestamp(
                        int(observation["ts_recv"]), unit="ns", tz="UTC"
                    ).isoformat(),
                    "seconds_from_break_open": (observation["ts_recv"] - start_ns) / 1_000_000_000.0,
                    "seconds_before_entry": (end_ns - observation["ts_recv"]) / 1_000_000_000.0,
                    "raw_i5": observation["imbalance"],
                    "aligned_i5": sign * observation["imbalance"],
                    "spread_ticks": observation["spread_ticks"],
                }
            )
    traces = pd.DataFrame(rows).sort_values(
        ["case_id", "seconds_from_break_open"], ascending=[True, True]
    )
    if traces["case_id"].nunique() != 12:
        raise ForensicError("book trace extraction did not cover all frozen cases")
    traces.to_csv(BOOK_TRACE_PATH, index=False)
    receipt = {
        "schema_version": "cme6e_breakbar_transition_trace_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cases": int(traces["case_id"].nunique()),
        "rows": int(len(traces)),
        "trace_path": str(BOOK_TRACE_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
        "trace_sha256": sha256_file(BOOK_TRACE_PATH),
        "feature_extractor_sha256": FEATURE_EXTRACTOR_SHA256,
        "raw_source_sha256": raw_bindings,
        "causal_window_enforced": "break_bar_open<=ts_event_and_recv<actual_decision",
        "terminal_verdict_changed": False,
    }
    json_write(BOOK_RECEIPT_PATH, receipt)
    print(
        "BREAKBAR_CHART_FORENSICS_TRACE_OK "
        f"cases=12 rows={len(traces)} receipt_sha256={sha256_file(BOOK_RECEIPT_PATH)}"
    )


def add_clock_markers(ax: Any, frame: pd.DataFrame, case: pd.Series) -> None:
    break_t = pd.Timestamp(case["decision_time_utc"])
    entry_t = pd.Timestamp(case["entry_time_utc"])
    break_x = int((frame["time_utc"] - break_t).abs().argmin())
    entry_x = (
        len(frame) - 0.5
        if entry_t >= frame["time_utc"].max()
        else int((frame["time_utc"] - entry_t).abs().argmin())
    )
    ax.axvline(break_x, color="#6a1b9a", linestyle=":", linewidth=1.1, label="Break-bar open")
    ax.axvline(entry_x, color="#1565c0", linestyle="-.", linewidth=1.1, label="Actual entry")


def draw_book(ax: Any, trace: pd.DataFrame, case: pd.Series) -> None:
    ordered = trace.sort_values("seconds_from_break_open")
    duration = float(case["duration_seconds"])
    x = ordered["seconds_from_break_open"]
    ax.plot(x, ordered["aligned_i5"], color="#6a1b9a", linewidth=0.6, alpha=0.7)
    rolling = ordered["aligned_i5"].rolling(25, min_periods=1).median()
    ax.plot(x, rolling, color="#ff8f00", linewidth=1.2, label="25-event median")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.axvspan(0, 60, color="#90caf9", alpha=0.18, label="Early 60s")
    ax.axvspan(duration - 60, duration, color="#ffcc80", alpha=0.22, label="Late 60s")
    ax.axvline(duration, color="#1565c0", linestyle="--", linewidth=1.0, label="Actual entry")
    ax.set_xlim(0, duration + 2)
    ax.set_ylabel("Direction-aligned I5")
    ax.set_xlabel("Seconds from break-bar open")
    ax.set_title(
        "CME 6E full-break-bar trace | "
        f"early={float(case['aligned_imbalance_median_early60']):+.3f} "
        f"late={float(case['aligned_imbalance_median_late60']):+.3f} "
        f"score={float(case['book_transition_score']):+.3f}",
        fontsize=9,
    )
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", fontsize=7, ncol=4)


def render() -> None:
    if CHART_MANIFEST_PATH.exists():
        raise ForensicError("chart manifest already exists")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    base = load_module(BASE_PATH, "hyp002_render_base")
    cases = pd.read_csv(
        CASE_PATH,
        dtype={"position_id": str},
        parse_dates=["decision_time_utc", "entry_time_utc", "exit_time_utc"],
    )
    traces = pd.read_csv(BOOK_TRACE_PATH, dtype={"position_id": str})
    bars = pd.read_parquet(BARS_PATH, columns=["time_utc", "open", "high", "low", "close"])
    bars["time_utc"] = pd.to_datetime(bars["time_utc"])
    bars = bars.drop_duplicates("time_utc", keep=False).sort_values("time_utc")
    decision_dir = EVIDENCE_ROOT / "charts_decision"
    outcome_dir = EVIDENCE_ROOT / "charts_outcome"
    decision_dir.mkdir(parents=True, exist_ok=True)
    outcome_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    decision_paths: list[Path] = []
    outcome_paths: list[Path] = []
    for _, case in cases.iterrows():
        entry_t = pd.Timestamp(case["entry_time_utc"])
        exit_t = pd.Timestamp(case["exit_time_utc"])
        decision_price = bars[
            (bars["time_utc"] >= entry_t - pd.Timedelta(minutes=120))
            & (bars["time_utc"] < entry_t)
        ].copy()
        outcome_price = bars[
            (bars["time_utc"] >= entry_t - pd.Timedelta(minutes=60))
            & (bars["time_utc"] <= exit_t + pd.Timedelta(minutes=30))
        ].copy()
        context_source = bars[bars["time_utc"] < entry_t].set_index("time_utc")[["open", "high", "low", "close"]]
        h1 = (
            context_source.resample("1h", label="left", closed="left")
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna()
            .tail(36)
            .reset_index()
        )
        trace = traces[traces["case_id"] == case["case_id"]]

        decision_path = decision_dir / f"{case['case_id']}_decision.png"
        fig, axes = plt.subplots(3, 1, figsize=(13, 12), gridspec_kw={"height_ratios": [2.0, 1.25, 1.25]})
        base.draw_candles(axes[0], decision_price)
        base.add_trade_lines(axes[0], case, outcome=False, price_frame=decision_price)
        add_clock_markers(axes[0], decision_price, case)
        axes[0].set_title(
            f"{case['case_id']} | PID {case['position_id']} | {case['direction']} | decision-as-of, future hidden"
        )
        axes[0].legend(loc="upper left", fontsize=7, ncol=4)
        base.draw_candles(axes[1], h1)
        axes[1].set_title("EURUSD H1 context available at entry")
        draw_book(axes[2], trace, case)
        fig.tight_layout()
        fig.savefig(decision_path, dpi=150)
        plt.close(fig)

        outcome_path = outcome_dir / f"{case['case_id']}_outcome.png"
        fig, axes = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={"height_ratios": [2.2, 1.0]})
        base.draw_candles(axes[0], outcome_price)
        base.add_trade_lines(axes[0], case, outcome=True, price_frame=outcome_price)
        add_clock_markers(axes[0], outcome_price, case)
        axes[0].set_title(
            f"{case['case_id']} | {case['stratum']} | R={float(case['realized_r']):+.3f} | outcome-disclosing"
        )
        axes[0].legend(loc="upper left", fontsize=7, ncol=4)
        draw_book(axes[1], trace, case)
        fig.tight_layout()
        fig.savefig(outcome_path, dpi=150)
        plt.close(fig)

        decision_paths.append(decision_path)
        outcome_paths.append(outcome_path)
        results.append(
            {
                "case_id": case["case_id"],
                "stratum": case["stratum"],
                "position_id": str(case["position_id"]),
                "direction": case["direction"],
                "entry": float(case["entry"]),
                "exit": float(case["exit"]),
                "net_R": float(case["realized_r"]),
                "context_reason": "predeclared frozen sampling stratum",
                "decision_chart": str(decision_path.relative_to(WORKSPACE)).replace("\\", "/"),
                "decision_sha256": sha256_file(decision_path),
                "decision_future_hidden": True,
                "outcome_chart": str(outcome_path.relative_to(WORKSPACE)).replace("\\", "/"),
                "outcome_sha256": sha256_file(outcome_path),
                "outcome_visible": True,
            }
        )
    decision_sheet = EVIDENCE_ROOT / "decision_contact_sheet.png"
    outcome_sheet = EVIDENCE_ROOT / "outcome_contact_sheet.png"
    base.render_contact_sheet(
        decision_paths, decision_sheet, "HYP-002 frozen decision charts — future hidden"
    )
    base.render_contact_sheet(
        outcome_paths, outcome_sheet, "HYP-002 frozen outcome anatomy charts"
    )
    manifest = {
        "schema_version": "cme6e_breakbar_transition_chart_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_sha256": sha256_file(CASE_PATH),
        "book_trace_sha256": sha256_file(BOOK_TRACE_PATH),
        "bars_sha256": BARS_SHA256,
        "render_tool_sha256": sha256_file(MODULE_PATH),
        "decision_contact_sheet": str(decision_sheet.relative_to(WORKSPACE)).replace("\\", "/"),
        "decision_contact_sheet_sha256": sha256_file(decision_sheet),
        "outcome_contact_sheet": str(outcome_sheet.relative_to(WORKSPACE)).replace("\\", "/"),
        "outcome_contact_sheet_sha256": sha256_file(outcome_sheet),
        "results": results,
        "charts_rendered": len(results) * 2,
        "terminal_verdict_changed": False,
    }
    json_write(CHART_MANIFEST_PATH, manifest)
    print(
        "BREAKBAR_CHART_FORENSICS_RENDER_OK "
        f"cases=12 charts=24 manifest_sha256={sha256_file(CHART_MANIFEST_PATH)}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "extract-book", "render"))
    return parser.parse_args()


def main() -> int:
    command = parse_args().command
    if command == "prepare":
        prepare()
    elif command == "extract-book":
        extract_book()
    else:
        render()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ForensicError as exc:
        print(f"BREAKBAR_CHART_FORENSICS_FAIL_CLOSED error={exc}")
        raise SystemExit(2)
