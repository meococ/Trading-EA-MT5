#!/usr/bin/env python3
"""Render clock-corrected HYP-001 charts without resampling the frozen cases."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


MODULE_PATH = Path(__file__).resolve()
PACKAGE = MODULE_PATH.parents[1]
WORKSPACE = MODULE_PATH.parents[3]
ROOT = PACKAGE / "research" / "evidence" / "HYP-CME6E-RAWBREAK-BOOKSTATE-001_CHART_FORENSICS"
CASE_PATH = ROOT / "case_selection.csv"
TRACE_PATH = ROOT / "book_traces.csv"
BARS_PATH = WORKSPACE / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD" / "EURUSD_M1_2015_now.parquet"
OLD_MANIFEST_PATH = ROOT / "chart_manifest.json"
MANIFEST_PATH = ROOT / "chart_manifest_clock_v2.json"
BASE_PATH = PACKAGE / "research" / "analyze_raw_break_book_chart_forensics.py"

CASE_SHA256 = "6A13A3739A02AC57995BCD57E9231D2B4ADC570A227E81400339621DCC4B98F6"
TRACE_SHA256 = "6A63683ECD071054DC861DACA317379DF2204D0F379CDBF5AD0F86F6C5AFB537"
BARS_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
OLD_MANIFEST_SHA256 = "5FB608CA480182B49CD914A0B44DC9CA5F770368DB14F08C87B4924143F2C3C0"
BASE_SHA256 = "5DE0157F883E1041B7887A3539B0E3AFD1DFF209864199DB11C1475CE63A5367"


class CorrectionError(RuntimeError):
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
        raise CorrectionError(f"SHA mismatch for {path}: expected={expected} actual={actual}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CorrectionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clock_semantics(case: dict[str, Any] | pd.Series) -> dict[str, Any]:
    feature_cutoff = pd.Timestamp(case["decision_time_utc"])
    actual_decision = pd.Timestamp(case["entry_time_utc"])
    lag_seconds = (actual_decision - feature_cutoff).total_seconds()
    return {
        "feature_cutoff_role": "BREAK_BAR_OPEN",
        "actual_closed_bar_decision_role": "NEXT_BAR_OPEN_ENTRY",
        "feature_cutoff_utc": feature_cutoff.isoformat(),
        "actual_closed_bar_decision_utc": actual_decision.isoformat(),
        "feature_cutoff_to_actual_decision_seconds": lag_seconds,
        "feature_window_contains_break_bar": False,
        "feature_window_is_immediately_pre_entry": False,
    }


def add_clock_markers(ax, frame: pd.DataFrame, case: pd.Series) -> None:
    feature_t = pd.Timestamp(case["decision_time_utc"])
    entry_t = pd.Timestamp(case["entry_time_utc"])
    feature_x = int((frame["time_utc"] - feature_t).abs().argmin())
    entry_x = len(frame) - 0.5 if entry_t >= frame["time_utc"].max() else int((frame["time_utc"] - entry_t).abs().argmin())
    ax.axvline(feature_x, color="#6a1b9a", linestyle=":", linewidth=1.2, label="Feature cutoff / break-bar open")
    ax.axvline(entry_x, color="#1565c0", linestyle="-.", linewidth=1.1, label="Actual closed-bar decision / entry")


def draw_book_corrected(ax, trace: pd.DataFrame, case: pd.Series) -> None:
    ordered = trace.sort_values("seconds_before_decision", ascending=False)
    x = -ordered["seconds_before_decision"]
    ax.plot(x, ordered["aligned_i5"], color="#6a1b9a", linewidth=0.7, alpha=0.75)
    rolling = ordered["aligned_i5"].rolling(25, min_periods=1).median()
    ax.plot(x, rolling, color="#ff8f00", linewidth=1.3, label="25-event median")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.axvline(0, color="#6a1b9a", linestyle=":", linewidth=1.0, label="Feature cutoff = break-bar open")
    semantics = clock_semantics(case)
    lag = semantics["feature_cutoff_to_actual_decision_seconds"]
    ax.text(
        0.99, 0.04,
        f"Actual closed-bar decision/entry is +{lag:.0f}s, outside this CME window",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=8,
        color="#b71c1c", bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "#b71c1c"},
    )
    ax.set_xlim(-120, 2)
    ax.set_ylabel("Direction-aligned I5")
    ax.set_xlabel("Seconds relative to feature cutoff / BREAK-bar OPEN")
    ax.set_title(f"CME 6E trace | frozen score={float(case['book_alignment_score']):+.4f} | does NOT cover the M5 break bar", fontsize=9)
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", fontsize=7)


def json_write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def main() -> int:
    for path, expected in (
        (CASE_PATH, CASE_SHA256),
        (TRACE_PATH, TRACE_SHA256),
        (BARS_PATH, BARS_SHA256),
        (OLD_MANIFEST_PATH, OLD_MANIFEST_SHA256),
        (BASE_PATH, BASE_SHA256),
    ):
        require_sha(path, expected)
    if MANIFEST_PATH.exists():
        raise CorrectionError("clock-corrected chart manifest already exists")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    base = load_module(BASE_PATH, "base_chart_forensics")
    cases = pd.read_csv(CASE_PATH, dtype={"position_id": str}, parse_dates=["decision_time_utc", "entry_time_utc", "exit_time_utc"])
    traces = pd.read_csv(TRACE_PATH, dtype={"position_id": str})
    bars = pd.read_parquet(BARS_PATH, columns=["time_utc", "open", "high", "low", "close"])
    bars["time_utc"] = pd.to_datetime(bars["time_utc"])
    bars = bars.drop_duplicates("time_utc", keep=False).sort_values("time_utc")
    decision_dir = ROOT / "charts_decision_clock_v2"
    outcome_dir = ROOT / "charts_outcome_clock_v2"
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
        context_source = bars[bars["time_utc"] < entry_t].set_index("time_utc")[["open", "high", "low", "close"]]
        h1 = context_source.resample("1h", label="left", closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna().tail(36).reset_index()
        trace = traces[traces["case_id"] == case["case_id"]]
        semantics = clock_semantics(case)

        decision_path = decision_dir / f"{case['case_id']}_decision_clock_v2.png"
        fig, axes = plt.subplots(3, 1, figsize=(13, 12), gridspec_kw={"height_ratios":[2.0, 1.25, 1.25]})
        base.draw_candles(axes[0], decision_price)
        base.add_trade_lines(axes[0], case, outcome=False, price_frame=decision_price)
        add_clock_markers(axes[0], decision_price, case)
        axes[0].set_title(f"{case['case_id']} | PID {case['position_id']} | {case['direction']} | actual entry decision as-of (future hidden)")
        axes[0].legend(loc="upper left", fontsize=7, ncol=2)
        base.draw_candles(axes[1], h1)
        axes[1].set_title("EURUSD H1 context available at actual decision/entry")
        draw_book_corrected(axes[2], trace, case)
        fig.tight_layout()
        fig.savefig(decision_path, dpi=150)
        plt.close(fig)

        outcome_path = outcome_dir / f"{case['case_id']}_outcome_clock_v2.png"
        fig, axes = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={"height_ratios":[2.2, 1.0]})
        base.draw_candles(axes[0], outcome_price)
        base.add_trade_lines(axes[0], case, outcome=True, price_frame=outcome_price)
        add_clock_markers(axes[0], outcome_price, case)
        axes[0].set_title(f"{case['case_id']} | {case['stratum']} | R={float(case['realized_r']):+.3f} | outcome-disclosing")
        axes[0].legend(loc="upper left", fontsize=7, ncol=2)
        draw_book_corrected(axes[1], trace, case)
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
                "clock_semantics": semantics,
                "decision_chart": str(decision_path.relative_to(WORKSPACE)).replace("\\", "/"),
                "decision_sha256": sha256_file(decision_path),
                "outcome_chart": str(outcome_path.relative_to(WORKSPACE)).replace("\\", "/"),
                "outcome_sha256": sha256_file(outcome_path),
            }
        )
    decision_sheet = ROOT / "decision_contact_sheet_clock_v2.png"
    outcome_sheet = ROOT / "outcome_contact_sheet_clock_v2.png"
    base.render_contact_sheet(decision_paths, decision_sheet, "HYP-001 CLOCK V2 — feature cutoff precedes actual decision by ~5 minutes")
    base.render_contact_sheet(outcome_paths, outcome_sheet, "HYP-001 CLOCK V2 outcome anatomy")
    lags = [result["clock_semantics"]["feature_cutoff_to_actual_decision_seconds"] for result in results]
    manifest = {
        "schema_version": "cme6e_raw_break_book_chart_manifest.clock_v2",
        "hypothesis_id": "HYP-CME6E-RAWBREAK-BOOKSTATE-001",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "PASS_CLOCK_SEMANTICS_CORRECTED",
        "supersedes_invalid_manifest_path": str(OLD_MANIFEST_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
        "supersedes_invalid_manifest_sha256": OLD_MANIFEST_SHA256,
        "invalidity_reason": "old charts mislabeled break-bar open time as the actual closed-bar decision",
        "source_code_evidence": {
            "detect_closed_bar": "EA_SweepCascadeContinuation.mq5 lines 960-995 uses CopyRates shift=1 and detects bars[0]",
            "stored_clock": "lines 530-552 stores bar.time (break-bar open) then enters immediately on next-bar tick",
        },
        "case_sha256": CASE_SHA256,
        "book_trace_sha256": TRACE_SHA256,
        "bars_sha256": BARS_SHA256,
        "render_tool_sha256": sha256_file(MODULE_PATH),
        "feature_cutoff_to_actual_decision_seconds": {
            "min": min(lags), "median": statistics_median(lags), "max": max(lags),
        },
        "decision_contact_sheet": str(decision_sheet.relative_to(WORKSPACE)).replace("\\", "/"),
        "decision_contact_sheet_sha256": sha256_file(decision_sheet),
        "outcome_contact_sheet": str(outcome_sheet.relative_to(WORKSPACE)).replace("\\", "/"),
        "outcome_contact_sheet_sha256": sha256_file(outcome_sheet),
        "results": results,
        "charts_rendered": 24,
        "oos_opened": False,
    }
    json_write(MANIFEST_PATH, manifest)
    print(f"BOOK_CHART_CLOCK_V2_OK cases=12 charts=24 manifest_sha256={sha256_file(MANIFEST_PATH)}")
    return 0


def statistics_median(values: list[float]) -> float:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2 if len(ordered) % 2 == 0 else ordered[midpoint]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CorrectionError as exc:
        print(f"BOOK_CHART_CLOCK_V2_FAIL_CLOSED error={exc}")
        raise SystemExit(2)
