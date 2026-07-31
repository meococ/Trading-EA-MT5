#!/usr/bin/env python3
"""Prepare, extract and render the frozen HYP-001 chart-forensics campaign."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).resolve()
PACKAGE = MODULE_PATH.parents[1]
WORKSPACE = MODULE_PATH.parents[3]
HYPOTHESIS_ID = "HYP-CME6E-RAWBREAK-BOOKSTATE-001"
THRESHOLD = -0.005025602742083225
PLAN_PATH = PACKAGE / "research" / f"{HYPOTHESIS_ID}_CHART_FORENSICS_PLAN.md"
PLAN_SHA256 = "66BB8F6DA9D88F5D7068ED4FC653A7C8A28DCFA33A5DFAE823C24C198C97BEA2"
EVIDENCE_ROOT = PACKAGE / "research" / "evidence" / f"{HYPOTHESIS_ID}_CHART_FORENSICS"
PROBE_ROOT = PACKAGE / "research" / "evidence" / f"{HYPOTHESIS_ID}_DESIGN"
JOINED_PATH = PROBE_ROOT / "joined_design_trades.csv"
JOINED_SHA256 = "A28B47392E295C6D6296E4C7CC851C226C2F3060673014B37959F12407AC99B2"
CONTROL_PATH = WORKSPACE / "03. EA Developer" / "EA_SweepCascadeContinuation" / "research" / "evidence" / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS" / "control_trades.csv"
CONTROL_SHA256 = "07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9"
BARS_PATH = WORKSPACE / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
BARS_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
CLOCK_PATH = WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
FEATURE_EXTRACTOR_PATH = PACKAGE / "research" / "extract_cme6e_raw_break_features.py"
FEATURE_EXTRACTOR_SHA256 = "34A668CF89FEB9ED5A0D74E41E35B6C6B19E810E5BF6CC02AA6F36EE4FDBC4BB"
RAW_ROOT = WORKSPACE / "02. AlphaFactory" / "data" / "databento" / "cme_6e_raw_break_design" / "raw"
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def classify_exit(row: dict[str, Any] | pd.Series) -> str:
    sign = 1.0 if str(row["direction"]).upper() == "BUY" else -1.0
    exit_price = float(row["exit"])
    stop = float(row["planned_stop"])
    target = float(row["planned_target"])
    tolerance = 2e-5
    if sign * (exit_price - target) >= -tolerance:
        return "TP_LIKE"
    if sign * (exit_price - stop) <= tolerance:
        return "SL_LIKE"
    return "TIMEOUT_OR_OTHER"


def basic_metrics(rows: pd.DataFrame) -> dict[str, Any]:
    nets = rows["net"].astype(float)
    realized = rows["realized_r"].astype(float)
    wins = nets[nets > 0]
    losses = nets[nets <= 0]
    gross_profit = float(wins.sum())
    gross_loss_abs = float(-losses[losses < 0].sum())
    average_win = float(wins.mean()) if len(wins) else None
    average_loss_abs = float(-losses.mean()) if len(losses) else None
    payoff = average_win / average_loss_abs if average_win and average_loss_abs else None
    return {
        "count": int(len(rows)),
        "wins": int((nets > 0).sum()),
        "losses": int((nets <= 0).sum()),
        "win_rate": float((nets > 0).mean()) if len(rows) else None,
        "gross_profit": gross_profit,
        "gross_loss_abs": gross_loss_abs,
        "net": float(nets.sum()),
        "profit_factor": gross_profit / gross_loss_abs if gross_loss_abs > 0 else None,
        "expectancy_account": float(nets.mean()) if len(rows) else None,
        "mean_realized_r": float(realized.mean()) if len(rows) else None,
        "median_realized_r": float(realized.median()) if len(rows) else None,
        "average_win": average_win,
        "average_loss_abs": average_loss_abs,
        "realized_payoff_ratio": payoff,
        "implied_breakeven_win_rate": 1.0 / (1.0 + payoff) if payoff else None,
    }


def path_geometry(bars: pd.DataFrame, *, direction: str, entry: float, risk_price: float) -> dict[str, float | None]:
    if bars.empty or risk_price <= 0:
        return {"mfe_r": None, "mae_r": None}
    if direction.upper() == "BUY":
        mfe = (float(bars["high"].max()) - entry) / risk_price
        mae = (entry - float(bars["low"].min())) / risk_price
    else:
        mfe = (entry - float(bars["low"].min())) / risk_price
        mae = (float(bars["high"].max()) - entry) / risk_price
    return {"mfe_r": mfe, "mae_r": mae}


def _sort_pid(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["_pid_int"] = out["position_id"].astype(int)
    return out


def select_cases(population: pd.DataFrame) -> pd.DataFrame:
    required = {
        "position_id", "direction", "book_alignment_score", "realized_r", "net",
        "stop_pips", "volume", "entry_minute_utc",
    }
    if not required.issubset(population.columns):
        raise ForensicError(f"sampling fields missing: {sorted(required - set(population.columns))}")
    work = _sort_pid(population)
    selected: list[tuple[str, pd.Series]] = []
    used: set[str] = set()

    def take(stratum: str, frame: pd.DataFrame, count: int) -> None:
        candidates = frame[~frame["position_id"].astype(str).isin(used)]
        if len(candidates) < count:
            raise ForensicError(f"insufficient rows for {stratum}")
        for _, row in candidates.head(count).iterrows():
            position_id = str(row["position_id"])
            selected.append((stratum, row))
            used.add(position_id)

    take("EXTREME_WIN", work.sort_values(["realized_r", "_pid_int"], ascending=[False, True]), 2)
    take("EXTREME_LOSS", work.sort_values(["realized_r", "_pid_int"], ascending=[True, True]), 2)

    wins = work[work["net"].astype(float) > 0].copy()
    losses = work[work["net"].astype(float) <= 0].copy()
    wins["_median_distance"] = (wins["realized_r"] - wins["realized_r"].median()).abs()
    losses["_median_distance"] = (losses["realized_r"] - losses["realized_r"].median()).abs()
    take("MEDIAN_WIN", wins.sort_values(["_median_distance", "_pid_int"]), 2)
    take("MEDIAN_LOSS", losses.sort_values(["_median_distance", "_pid_int"]), 2)

    median_score = float(work["book_alignment_score"].median())
    scale_fields = ["book_alignment_score", "stop_pips", "volume", "entry_minute_utc"]
    scales = {field: float(work[field].astype(float).std(ddof=0)) or 1.0 for field in scale_fields}
    for direction in ("BUY", "SELL"):
        remaining_wins = work[
            (work["direction"] == direction)
            & (work["net"].astype(float) > 0)
            & (~work["position_id"].astype(str).isin(used))
        ].copy()
        remaining_wins["_score_distance"] = (remaining_wins["book_alignment_score"] - median_score).abs()
        winner = remaining_wins.sort_values(["_score_distance", "_pid_int"]).iloc[0]
        winner_stratum = f"MATCHED_{direction}_WIN"
        selected.append((winner_stratum, winner))
        used.add(str(winner["position_id"]))

        candidates = work[
            (work["direction"] == direction)
            & (work["net"].astype(float) <= 0)
            & (~work["position_id"].astype(str).isin(used))
        ].copy()
        distance = np.zeros(len(candidates))
        for field in scale_fields:
            distance += ((candidates[field].astype(float) - float(winner[field])) / scales[field]) ** 2
        candidates["_match_distance"] = np.sqrt(distance)
        loser = candidates.sort_values(["_match_distance", "_pid_int"]).iloc[0]
        selected.append((f"MATCHED_{direction}_LOSS", loser))
        used.add(str(loser["position_id"]))

    rows: list[dict[str, Any]] = []
    for rank, (stratum, row) in enumerate(selected, start=1):
        payload = row.drop(labels=[column for column in row.index if column.startswith("_")]).to_dict()
        payload["stratum"] = stratum
        payload["case_id"] = f"F{rank:03d}_PID{int(row['position_id']):09d}"
        rows.append(payload)
    result = pd.DataFrame(rows)
    if len(result) != 12 or result["position_id"].astype(str).nunique() != 12:
        raise ForensicError("frozen sample must contain 12 unique cases")
    return result


def load_control_rows(allowed_ids: set[str]) -> list[dict[str, str]]:
    materialized: list[dict[str, str]] = []
    seen: set[str] = set()
    with CONTROL_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            position_id = str(row["position_id"])
            if position_id in allowed_ids:
                if position_id in seen:
                    raise ForensicError(f"duplicate control identity {position_id}")
                materialized.append(dict(row))
                seen.add(position_id)
                if seen == allowed_ids:
                    break
            elif datetime.strptime(row["decision_time"], "%Y.%m.%d %H:%M:%S").year > 2020:
                raise ForensicError("missing DESIGN row before OOS boundary")
    if seen != allowed_ids:
        raise ForensicError("control/design identity mismatch")
    return materialized


def enrich_population() -> pd.DataFrame:
    require_sha(PLAN_PATH, PLAN_SHA256)
    require_sha(JOINED_PATH, JOINED_SHA256)
    require_sha(CONTROL_PATH, CONTROL_SHA256)
    require_sha(BARS_PATH, BARS_SHA256)
    require_sha(CLOCK_PATH, CLOCK_SHA256)
    joined = pd.read_csv(JOINED_PATH, dtype={"position_id": str})
    joined["quality_eligible"] = joined["quality_eligible"].astype(str).str.lower().eq("true")
    challenger = joined[
        joined["quality_eligible"] & (joined["book_alignment_score"] >= THRESHOLD)
    ].copy()
    if len(challenger) != 230:
        raise ForensicError(f"challenger population mismatch: {len(challenger)}")
    full = pd.DataFrame(load_control_rows(set(challenger["position_id"].astype(str))), dtype=str)
    full["position_id"] = full["position_id"].astype(str)
    outcome_columns = [
        "position_id", "open_time", "close_time", "decision_time", "direction",
        "volume", "entry", "exit", "planned_stop", "planned_target", "risk_points",
        "initial_risk_account", "net", "realized_r",
    ]
    merged = challenger.drop(columns=[column for column in ("volume", "net", "realized_r", "initial_risk_account") if column in challenger]).merge(
        full[outcome_columns], on=["position_id", "direction"], how="inner", validate="one_to_one"
    )
    clock = load_module(CLOCK_PATH, "forensic_clock")

    def server_utc(value: str) -> pd.Timestamp:
        raw = datetime.strptime(value, "%Y.%m.%d %H:%M:%S")
        return pd.Timestamp(clock.server_to_utc(raw))

    merged["decision_time_utc"] = merged["decision_time"].map(server_utc)
    merged["entry_time_utc"] = merged["open_time"].map(server_utc)
    merged["exit_time_utc"] = merged["close_time"].map(server_utc)
    expected_decision = pd.to_datetime(merged["end"], utc=True).dt.tz_convert(None)
    if not (merged["decision_time_utc"].reset_index(drop=True) == expected_decision.reset_index(drop=True)).all():
        raise ForensicError("decision clock mismatch")
    numeric = ["volume", "entry", "exit", "planned_stop", "planned_target", "risk_points", "initial_risk_account", "net", "realized_r"]
    for column in numeric:
        merged[column] = merged[column].astype(float)
    merged["stop_pips"] = (merged["entry"] - merged["planned_stop"]).abs() / 0.0001
    merged["target_pips"] = (merged["planned_target"] - merged["entry"]).abs() / 0.0001
    merged["hold_minutes"] = (merged["exit_time_utc"] - merged["entry_time_utc"]).dt.total_seconds() / 60.0
    merged["decision_entry_lag_minutes"] = (merged["entry_time_utc"] - merged["decision_time_utc"]).dt.total_seconds() / 60.0
    merged["entry_minute_utc"] = merged["entry_time_utc"].dt.hour * 60 + merged["entry_time_utc"].dt.minute
    merged["entry_hour_utc"] = merged["entry_time_utc"].dt.hour
    merged["entry_weekday"] = merged["entry_time_utc"].dt.day_name()
    merged["entry_month"] = merged["entry_time_utc"].dt.strftime("%Y-%m")
    merged["entry_year"] = merged["entry_time_utc"].dt.year
    merged["exit_class"] = merged.apply(classify_exit, axis=1)
    return merged.sort_values(["entry_time_utc", "position_id"]).reset_index(drop=True)


def grouped_metrics(frame: pd.DataFrame, field: str) -> dict[str, Any]:
    return {str(key): basic_metrics(group) for key, group in frame.groupby(field, observed=True)}


def add_path_geometry(frame: pd.DataFrame) -> pd.DataFrame:
    bars = pd.read_parquet(BARS_PATH, columns=["time_utc", "open", "high", "low", "close"])
    bars["time_utc"] = pd.to_datetime(bars["time_utc"])
    bars = bars.drop_duplicates("time_utc", keep=False).set_index("time_utc").sort_index()
    rows: list[dict[str, Any]] = []
    for _, trade in frame.iterrows():
        entry_t = pd.Timestamp(trade["entry_time_utc"]).floor("min")
        exit_t = pd.Timestamp(trade["exit_time_utc"]).floor("min")
        risk = abs(float(trade["entry"]) - float(trade["planned_stop"]))
        trade_bars = bars.loc[entry_t:exit_t]
        geometry = path_geometry(trade_bars, direction=str(trade["direction"]), entry=float(trade["entry"]), risk_price=risk)
        payload = trade.to_dict()
        payload.update(geometry)
        for minutes in (5, 15, 30):
            fixed = bars.loc[entry_t:entry_t + pd.Timedelta(minutes=minutes - 1)]
            values = path_geometry(fixed, direction=str(trade["direction"]), entry=float(trade["entry"]), risk_price=risk)
            payload[f"mfe_{minutes}m_r"] = values["mfe_r"]
            payload[f"mae_{minutes}m_r"] = values["mae_r"]
        rows.append(payload)
    return pd.DataFrame(rows)


def prepare() -> None:
    if any(path.exists() for path in (CASE_PATH, SAMPLE_MANIFEST_PATH, POPULATION_PATH, ANALYSIS_PATH)):
        raise ForensicError("forensic selection evidence already exists; refusing implicit resample")
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    population = add_path_geometry(enrich_population())
    selected = select_cases(population)
    population.to_csv(POPULATION_PATH, index=False)
    selected.to_csv(CASE_PATH, index=False)

    eligible = pd.read_csv(JOINED_PATH, dtype={"position_id": str})
    eligible["quality_eligible"] = eligible["quality_eligible"].astype(str).str.lower().eq("true")
    eligible = eligible[eligible["quality_eligible"]].copy()
    eligible["score_decile"] = pd.qcut(eligible["book_alignment_score"], 10, labels=False, duplicates="drop")
    eligible_deciles = grouped_metrics(eligible, "score_decile")
    population["stop_width_quartile"] = pd.qcut(population["stop_pips"], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
    population["hold_bucket"] = pd.cut(population["hold_minutes"], [-np.inf, 15, 60, 120, np.inf], labels=["LE15", "15_TO_60", "60_TO_120", "GT120"])
    nets = population["net"].astype(float)
    worst10 = population.nsmallest(10, "net")
    best10 = population.nlargest(10, "net")
    analysis = {
        "schema_version": "cme6e_raw_break_book_chart_forensics_analysis.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "epistemic_class": "POST_OUTCOME_DESCRIPTIVE_NO_RULE_AUTHORITY",
        "population": basic_metrics(population),
        "decision_entry_lag_minutes": {
            "min": float(population["decision_entry_lag_minutes"].min()),
            "median": float(population["decision_entry_lag_minutes"].median()),
            "max": float(population["decision_entry_lag_minutes"].max()),
        },
        "rank_association": {
            "score_vs_realized_r_spearman": finite_or_none(population["book_alignment_score"].corr(population["realized_r"], method="spearman")),
            "score_vs_net_spearman": finite_or_none(population["book_alignment_score"].corr(population["net"], method="spearman")),
        },
        "path_geometry": {
            "winner_median_mfe_r": float(population.loc[nets > 0, "mfe_r"].median()),
            "loser_median_mfe_r": float(population.loc[nets <= 0, "mfe_r"].median()),
            "winner_median_mae_r": float(population.loc[nets > 0, "mae_r"].median()),
            "loser_median_mae_r": float(population.loc[nets <= 0, "mae_r"].median()),
            "winner_median_mfe_5m_r": float(population.loc[nets > 0, "mfe_5m_r"].median()),
            "loser_median_mfe_5m_r": float(population.loc[nets <= 0, "mfe_5m_r"].median()),
            "winner_median_mae_5m_r": float(population.loc[nets > 0, "mae_5m_r"].median()),
            "loser_median_mae_5m_r": float(population.loc[nets <= 0, "mae_5m_r"].median()),
        },
        "tail_contribution": {
            "worst_10_net": float(worst10["net"].sum()),
            "best_10_net": float(best10["net"].sum()),
            "worst_10_share_of_absolute_loss": float(-worst10["net"].sum() / -nets[nets < 0].sum()),
            "best_10_share_of_gross_profit": float(best10["net"].sum() / nets[nets > 0].sum()),
        },
        "buckets": {
            "year": grouped_metrics(population, "entry_year"),
            "month": grouped_metrics(population, "entry_month"),
            "weekday": grouped_metrics(population, "entry_weekday"),
            "utc_hour": grouped_metrics(population, "entry_hour_utc"),
            "direction": grouped_metrics(population, "direction"),
            "exit_class": grouped_metrics(population, "exit_class"),
            "hold": grouped_metrics(population, "hold_bucket"),
            "stop_width_quartile": grouped_metrics(population, "stop_width_quartile"),
            "eligible_score_decile": eligible_deciles,
        },
        "source_hashes": {
            "plan": PLAN_SHA256,
            "joined": JOINED_SHA256,
            "control": CONTROL_SHA256,
            "bars": BARS_SHA256,
            "clock": CLOCK_SHA256,
        },
        "oos_opened": False,
    }
    json_write(ANALYSIS_PATH, analysis)
    manifest = {
        "schema_version": "cme6e_raw_break_book_chart_sample.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sampling_plan_path": str(PLAN_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
        "sampling_plan_sha256": PLAN_SHA256,
        "population_rows": 230,
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
        "oos_opened": False,
    }
    json_write(SAMPLE_MANIFEST_PATH, manifest)
    print(f"BOOK_CHART_FORENSICS_PREPARE_OK population=230 sample=12 manifest_sha256={sha256_file(SAMPLE_MANIFEST_PATH)}")


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
    extractor = load_module(FEATURE_EXTRACTOR_PATH, "bound_feature_extractor")
    require_sha(FEATURE_EXTRACTOR_PATH, FEATURE_EXTRACTOR_SHA256)
    rows: list[dict[str, Any]] = []
    raw_bindings: dict[str, str] = {}
    for _, case in cases.iterrows():
        filename = str(case["filename"])
        if "2021" in filename or "2022" in filename:
            raise ForensicError("sealed OOS filename in selected sample")
        path = RAW_ROOT / filename
        raw_bindings[filename] = sha256_file(path)
        decision_ns = int(pd.Timestamp(case["decision_time_utc"]).timestamp() * 1_000_000_000)
        sign = 1.0 if case["direction"] == "BUY" else -1.0
        for message in db.DBNStore.from_file(path):
            observation = extractor._observation(message)
            if observation is None:
                continue
            if observation["ts_event"] >= decision_ns or observation["ts_recv"] >= decision_ns:
                continue
            rows.append(
                {
                    "case_id": case["case_id"],
                    "position_id": str(case["position_id"]),
                    "ts_recv_utc": pd.Timestamp(int(observation["ts_recv"]), unit="ns", tz="UTC").isoformat(),
                    "seconds_before_decision": (decision_ns - observation["ts_recv"]) / 1_000_000_000.0,
                    "raw_i5": observation["imbalance"],
                    "aligned_i5": sign * observation["imbalance"],
                    "spread_ticks": observation["spread_ticks"],
                }
            )
    traces = pd.DataFrame(rows).sort_values(["case_id", "seconds_before_decision"], ascending=[True, False])
    traces.to_csv(BOOK_TRACE_PATH, index=False)
    receipt = {
        "schema_version": "cme6e_book_trace_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "cases": int(traces["case_id"].nunique()),
        "rows": int(len(traces)),
        "trace_path": str(BOOK_TRACE_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
        "trace_sha256": sha256_file(BOOK_TRACE_PATH),
        "feature_extractor_sha256": FEATURE_EXTRACTOR_SHA256,
        "raw_source_sha256": raw_bindings,
        "causal_cutoff_enforced": True,
        "oos_opened": False,
    }
    json_write(BOOK_RECEIPT_PATH, receipt)
    print(f"BOOK_CHART_FORENSICS_TRACE_OK cases=12 rows={len(traces)} receipt_sha256={sha256_file(BOOK_RECEIPT_PATH)}")


def draw_candles(ax, frame: pd.DataFrame) -> None:
    for index, (_, row) in enumerate(frame.iterrows()):
        color = "#2e7d32" if row["close"] >= row["open"] else "#c62828"
        ax.vlines(index, row["low"], row["high"], color=color, linewidth=0.7)
        low, high = sorted((row["open"], row["close"]))
        ax.add_patch(__import__("matplotlib").patches.Rectangle((index - 0.35, low), 0.7, max(high - low, 1e-8), facecolor=color, edgecolor=color, linewidth=0.4))
    ax.set_xlim(-1, len(frame))
    ticks = list(range(0, len(frame), max(1, len(frame) // 7)))
    ax.set_xticks(ticks)
    ax.set_xticklabels([frame["time_utc"].iloc[index].strftime("%m-%d %H:%M") for index in ticks], rotation=25, ha="right", fontsize=7)
    ax.grid(alpha=0.15)


def add_trade_lines(ax, case: pd.Series, *, outcome: bool, price_frame: pd.DataFrame) -> None:
    ax.axhline(float(case["entry"]), color="#1565c0", linewidth=1.0, label="Entry")
    ax.axhline(float(case["planned_stop"]), color="#c62828", linestyle="--", linewidth=0.9, label="SL")
    ax.axhline(float(case["planned_target"]), color="#2e7d32", linestyle="--", linewidth=0.9, label="TP")
    if outcome:
        entry_t = pd.Timestamp(case["entry_time_utc"])
        exit_t = pd.Timestamp(case["exit_time_utc"])
        entry_x = int((price_frame["time_utc"] - entry_t).abs().argmin())
        exit_x = int((price_frame["time_utc"] - exit_t).abs().argmin())
        ax.scatter([entry_x], [float(case["entry"])], marker="^" if case["direction"] == "BUY" else "v", color="#1565c0", zorder=8)
        ax.scatter([exit_x], [float(case["exit"])], marker="x", color="#6a1b9a", s=55, zorder=8)
    ax.legend(loc="upper left", fontsize=7, ncol=3)


def draw_book(ax, trace: pd.DataFrame, case: pd.Series) -> None:
    ordered = trace.sort_values("seconds_before_decision", ascending=False)
    ax.plot(-ordered["seconds_before_decision"], ordered["aligned_i5"], color="#6a1b9a", linewidth=0.7, alpha=0.75)
    rolling = ordered["aligned_i5"].rolling(25, min_periods=1).median()
    ax.plot(-ordered["seconds_before_decision"], rolling, color="#ff8f00", linewidth=1.3, label="25-event median")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.axvline(0, color="#1565c0", linestyle="--", linewidth=0.9, label="BREAK decision")
    ax.set_xlim(-120, 2)
    ax.set_ylabel("Direction-aligned I5")
    ax.set_xlabel("Seconds relative to raw BREAK decision")
    ax.set_title(f"CME 6E five-level displayed-depth trace | frozen score={float(case['book_alignment_score']):+.4f}", fontsize=9)
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", fontsize=7)


def render_contact_sheet(paths: list[Path], output: Path, title: str) -> None:
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 4, figsize=(20, 13))
    for ax, path in zip(axes.flat, paths):
        ax.imshow(plt.imread(path))
        ax.set_title(path.stem, fontsize=8)
        ax.axis("off")
    fig.suptitle(title, fontsize=15)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(output, dpi=130)
    plt.close(fig)


def render() -> None:
    if CHART_MANIFEST_PATH.exists():
        raise ForensicError("chart manifest already exists")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cases = pd.read_csv(CASE_PATH, dtype={"position_id": str}, parse_dates=["decision_time_utc", "entry_time_utc", "exit_time_utc"])
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
        decision_price = bars[(bars["time_utc"] >= entry_t - pd.Timedelta(minutes=120)) & (bars["time_utc"] < entry_t)].copy()
        outcome_price = bars[(bars["time_utc"] >= entry_t - pd.Timedelta(minutes=60)) & (bars["time_utc"] <= exit_t + pd.Timedelta(minutes=30))].copy()
        context_source = bars[(bars["time_utc"] < entry_t)].set_index("time_utc")[["open", "high", "low", "close"]]
        h1 = context_source.resample("1h", label="left", closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().tail(36).reset_index()
        trace = traces[traces["case_id"] == case["case_id"]]

        decision_path = decision_dir / f"{case['case_id']}_decision.png"
        fig, axes = plt.subplots(3, 1, figsize=(13, 12), gridspec_kw={"height_ratios":[2.0, 1.25, 1.25]})
        draw_candles(axes[0], decision_price)
        add_trade_lines(axes[0], case, outcome=False, price_frame=decision_price)
        axes[0].set_title(f"{case['case_id']} | PID {case['position_id']} | {case['direction']} | EURUSD M1 decision-as-of (future hidden)")
        draw_candles(axes[1], h1)
        axes[1].set_title("EURUSD H1 context available at entry")
        draw_book(axes[2], trace, case)
        fig.tight_layout()
        fig.savefig(decision_path, dpi=150)
        plt.close(fig)

        outcome_path = outcome_dir / f"{case['case_id']}_outcome.png"
        fig, axes = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={"height_ratios":[2.2, 1.0]})
        draw_candles(axes[0], outcome_price)
        add_trade_lines(axes[0], case, outcome=True, price_frame=outcome_price)
        axes[0].set_title(f"{case['case_id']} | {case['stratum']} | R={float(case['realized_r']):+.3f} | outcome-disclosing")
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
                "net_r": float(case["realized_r"]),
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
    render_contact_sheet(decision_paths, decision_sheet, "HYP-001 frozen decision charts — future hidden")
    render_contact_sheet(outcome_paths, outcome_sheet, "HYP-001 frozen outcome anatomy charts")
    manifest = {
        "schema_version": "cme6e_raw_break_book_chart_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "case_sha256": sha256_file(CASE_PATH),
        "book_trace_sha256": sha256_file(BOOK_TRACE_PATH),
        "bars_sha256": BARS_SHA256,
        "decision_contact_sheet": str(decision_sheet.relative_to(WORKSPACE)).replace("\\", "/"),
        "decision_contact_sheet_sha256": sha256_file(decision_sheet),
        "outcome_contact_sheet": str(outcome_sheet.relative_to(WORKSPACE)).replace("\\", "/"),
        "outcome_contact_sheet_sha256": sha256_file(outcome_sheet),
        "results": results,
        "charts_rendered": len(results) * 2,
        "oos_opened": False,
    }
    json_write(CHART_MANIFEST_PATH, manifest)
    print(f"BOOK_CHART_FORENSICS_RENDER_OK cases=12 charts=24 manifest_sha256={sha256_file(CHART_MANIFEST_PATH)}")


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
        print(f"BOOK_CHART_FORENSICS_FAIL_CLOSED error={exc}")
        raise SystemExit(2)
