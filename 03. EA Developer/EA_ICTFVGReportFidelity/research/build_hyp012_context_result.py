#!/usr/bin/env python3
"""Reconcile and compare the frozen HYP-012 matched Model-0 pair."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(r"D:\Trading EA MT5")
HYPOTHESIS_ID = "HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012"
SOURCE_SHA256 = "8B1C9E283B97716C91F61FCDB2A74B6168CC0671DAE896A941F0F181674E6CE1"
RUNS = {
    "control": "20260719_161929",
    "challenger": "20260719_162104",
}
OUT = ROOT / "02. AlphaFactory" / "runtime" / "ictfvg_hyp012_context_result"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def profit_factor(values: pd.Series) -> float | None:
    gross_profit = float(values[values > 0].sum())
    gross_loss = float(-values[values < 0].sum())
    return gross_profit / gross_loss if gross_loss > 0 else None


def finite(value: object) -> float | None:
    if value is None or pd.isna(value) or not math.isfinite(float(value)):
        return None
    return float(value)


def reconcile(lifecycle_path: Path) -> pd.DataFrame:
    lifecycle = pd.read_csv(lifecycle_path)
    lifecycle["event_time"] = pd.to_datetime(
        lifecycle["event_time"], format="%Y.%m.%d %H:%M:%S"
    )
    numeric = [
        "volume", "price", "risk_pts", "initial_risk_account", "deal",
        "deal_profit", "deal_commission", "deal_swap", "deal_fee", "deal_net",
        "is_final_close",
    ]
    for column in numeric:
        lifecycle[column] = pd.to_numeric(lifecycle[column], errors="coerce")
    records: list[dict[str, object]] = []
    for position_id, group in lifecycle.groupby("position_id", sort=True):
        group = group.sort_values(["event_time", "deal"])
        opened = group[group["action"] == "OPEN"]
        final = group[group["is_final_close"] == 1]
        if len(opened) != 1 or len(final) != 1:
            raise SystemExit(
                f"position {position_id}: opens={len(opened)} final_closes={len(final)}"
            )
        first = opened.iloc[0]
        last = final.iloc[-1]
        risk_account = float(first["initial_risk_account"])
        gross = float(
            (group["deal_profit"] + group["deal_swap"] + group["deal_fee"]).sum()
        )
        commission = float(group["deal_commission"].sum())
        net = float(group["deal_net"].sum())
        if not math.isclose(net, gross + commission, abs_tol=1e-7):
            raise SystemExit(f"position {position_id}: lifecycle PnL does not reconcile")
        records.append(
            {
                "position_id": int(position_id),
                "side": str(first["order_type"]),
                "entry_time_server": first["event_time"],
                "exit_time_server": last["event_time"],
                "entry": float(first["price"]),
                "exit": float(last["price"]),
                "volume": float(first["volume"]),
                "risk_pts": float(first["risk_pts"]),
                "initial_risk_account": risk_account,
                "gross_before_commission": gross,
                "commission": commission,
                "net": net,
                "r_gross": gross / risk_account if risk_account > 0 else np.nan,
                "r_net": net / risk_account if risk_account > 0 else np.nan,
                "hold_minutes": (
                    last["event_time"] - first["event_time"]
                ).total_seconds()
                / 60.0,
            }
        )
    return pd.DataFrame.from_records(records)


def aggregate(frame: pd.DataFrame, elapsed_weeks: float) -> dict[str, object]:
    net = frame["net"].astype(float)
    r = frame["r_net"].dropna().astype(float)
    return {
        "positions": int(len(frame)),
        "defined_risk_positions": int(len(r)),
        "zero_initial_risk_positions": int(frame["r_net"].isna().sum()),
        "wins": int((net > 0).sum()),
        "win_rate_pct": finite((net > 0).mean() * 100.0),
        "net": float(net.sum()),
        "gross_before_commission": float(frame["gross_before_commission"].sum()),
        "commission": float(frame["commission"].sum()),
        "profit_factor_money": finite(profit_factor(net)),
        "profit_factor_r": finite(profit_factor(r)),
        "expectancy_money": finite(net.mean()),
        "expectancy_r": finite(r.mean()),
        "median_r": finite(r.median()),
        "trades_per_elapsed_week": float(len(frame) / elapsed_weeks),
        "median_risk_pips": finite(frame["risk_pts"].median() / 10.0),
        "median_hold_minutes": finite(frame["hold_minutes"].median()),
    }


def yearly(frame: pd.DataFrame) -> list[dict[str, object]]:
    rows = []
    for year, group in frame.groupby(frame["entry_time_server"].dt.year, sort=True):
        row = aggregate(group, 1.0)
        row["year"] = int(year)
        row.pop("trades_per_elapsed_week")
        rows.append(row)
    return rows


def report_identity(report_path: Path) -> dict[str, int]:
    text = report_path.read_text(encoding="utf-16", errors="ignore")
    if "History Quality:" not in text:
        text = report_path.read_text(encoding="utf-8", errors="ignore")

    def number(pattern: str) -> int:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            raise SystemExit(f"report field missing: {pattern}")
        return int(match.group(1))

    return {
        "history_quality_pct": number(r"History Quality:</td>\s*<td[^>]*><b>(\d+)%"),
        "bars": number(r">Thanh:</td>\s*<td[^>]*><b>(\d+)</b>"),
        "ticks": number(r">Ticks:</td>\s*<td[^>]*><b>(\d+)</b>"),
    }


def read_run(role: str, run_id: str, elapsed_weeks: float) -> dict[str, object]:
    run = ROOT / "02. AlphaFactory" / "runs" / "EA_ICTFVGReportFidelity" / run_id
    manifest_path = run / "run_manifest.json"
    report_path = run / "report.html"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest["hypothesis_id"] != HYPOTHESIS_ID or manifest["run_role"] != role:
        raise SystemExit(f"{run_id}: manifest identity/role mismatch")
    if manifest["source_sha256"] != SOURCE_SHA256:
        raise SystemExit(f"{run_id}: source hash mismatch")
    log_dir = run / "logs"
    lifecycle_paths = list(log_dir.glob("*_LifecycleTrades_*.csv"))
    runmeta_paths = list(log_dir.glob("*_RunMeta_*.json"))
    if len(lifecycle_paths) != 1 or len(runmeta_paths) != 1:
        raise SystemExit(f"{run_id}: expected exactly one lifecycle and RunMeta")
    runmeta = json.loads(runmeta_paths[0].read_text(encoding="utf-8"))
    if runmeta["hypothesis_id"] != HYPOTHESIS_ID:
        raise SystemExit(f"{run_id}: RunMeta identity mismatch")
    positions = reconcile(lifecycle_paths[0])
    summary = aggregate(positions, elapsed_weeks)
    if summary["positions"] != int(runmeta["diagnostic"]["entries_opened"]):
        raise SystemExit(f"{run_id}: lifecycle does not match RunMeta entries")
    output_path = OUT / f"positions_{role}.csv"
    positions.to_csv(output_path, index=False, date_format="%Y-%m-%dT%H:%M:%S")
    return {
        "run_id": run_id,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "report_path": str(report_path),
        "report_sha256": sha256(report_path),
        "source_sha256": manifest["source_sha256"],
        "ex5_sha256": manifest["ex5_sha256"],
        "contract_receipt_sha256": manifest["contract_receipt_sha256"],
        "report_identity": report_identity(report_path),
        "lifecycle_path": str(lifecycle_paths[0]),
        "lifecycle_sha256": sha256(lifecycle_paths[0]),
        "runmeta_path": str(runmeta_paths[0]),
        "runmeta_sha256": sha256(runmeta_paths[0]),
        "runmeta_diagnostic": runmeta["diagnostic"],
        "summary": summary,
        "yearly": yearly(positions),
        "positions_output": str(output_path),
        "positions_output_sha256": sha256(output_path),
        "overrides": manifest["overrides"],
    }


def overrides_map(value: str) -> dict[str, str]:
    return dict(item.split("=", 1) for item in value.split(";") if item)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    from_date = pd.Timestamp("2018-01-01")
    to_date = pd.Timestamp("2026-07-19")
    elapsed_weeks = float((to_date - from_date).days / 7.0)
    runs = {
        role: read_run(role, run_id, elapsed_weeks)
        for role, run_id in RUNS.items()
    }
    control_overrides = overrides_map(runs["control"]["overrides"])
    challenger_overrides = overrides_map(runs["challenger"]["overrides"])
    differences = {
        key: [control_overrides.get(key), challenger_overrides.get(key)]
        for key in control_overrides.keys() | challenger_overrides.keys()
        if control_overrides.get(key) != challenger_overrides.get(key)
    }
    if differences != {
        "InpMagic": ["5600722", "5600723"],
        "InpSignalMode": ["0", "2"],
    }:
        raise SystemExit(f"matched-preset drift: {differences}")

    challenger_diag = runs["challenger"]["runmeta_diagnostic"]
    funnel_total = sum(
        int(challenger_diag[key])
        for key in (
            "context_duplicate_rejections",
            "context_acceptance_invalidations",
            "context_timeouts",
            "context_confirmations",
        )
    )
    if funnel_total != int(challenger_diag["sweeps"]):
        raise SystemExit(
            f"context funnel mismatch: classified={funnel_total} sweeps={challenger_diag['sweeps']}"
        )

    control = runs["control"]["summary"]
    challenger = runs["challenger"]["summary"]
    result = {
        "schema_version": "ictfvg_hyp012_context_result.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": HYPOTHESIS_ID,
        "scope": "matched_diagnostic_no_tuning_no_rerun_no_promotion",
        "elapsed_calendar_weeks": elapsed_weeks,
        "matched_override_differences": differences,
        "runs": runs,
        "comparison": {
            "profit_factor_money_delta": (
                challenger["profit_factor_money"] - control["profit_factor_money"]
            ),
            "profit_factor_r_delta": (
                challenger["profit_factor_r"] - control["profit_factor_r"]
            ),
            "expectancy_r_delta": challenger["expectancy_r"] - control["expectancy_r"],
            "net_delta": challenger["net"] - control["net"],
            "positions_delta": challenger["positions"] - control["positions"],
            "max_drawdown_pct_report_control": 6.014351927328834,
            "max_drawdown_pct_report_challenger": 3.33456474053305,
        },
        "context_funnel": {
            "raw_sweeps": int(challenger_diag["sweeps"]),
            "duplicate_active_state": int(challenger_diag["context_duplicate_rejections"]),
            "acceptance_invalidations": int(challenger_diag["context_acceptance_invalidations"]),
            "three_bar_timeouts": int(challenger_diag["context_timeouts"]),
            "closed_bar_confirmations": int(challenger_diag["context_confirmations"]),
            "entries_opened": int(challenger_diag["entries_opened"]),
            "funnel_reconciles": True,
        },
        "frozen_gate_results": {
            "history_quality_100_pct": False,
            "cadence_2_to_5_per_week": (
                2.0 <= challenger["trades_per_elapsed_week"] <= 5.0
            ),
            "at_least_800_positions": challenger["positions"] >= 800,
            "profit_factor_at_least_1_30": challenger["profit_factor_money"] >= 1.30,
            "profit_factor_delta_at_least_0_20": (
                challenger["profit_factor_money"] - control["profit_factor_money"] >= 0.20
            ),
            "expectancy_r_at_least_0_05": challenger["expectancy_r"] >= 0.05,
            "expectancy_r_delta_at_least_0_15": (
                challenger["expectancy_r"] - control["expectancy_r"] >= 0.15
            ),
            "at_least_6_positive_years": sum(
                row["profit_factor_money"] is not None
                and row["profit_factor_money"] > 1.0
                for row in runs["challenger"]["yearly"]
            )
            >= 6,
        },
        "verdict": "INVALID_DIAGNOSTIC_HISTORY_QUALITY_99_PERCENT_AND_KILL_CONTEXT_NO_EDGE",
        "promotion_eligible": False,
    }
    result_path = OUT / "hyp012_context_result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    outputs = [
        result_path,
        OUT / "positions_control.csv",
        OUT / "positions_challenger.csv",
    ]
    manifest = {
        "schema_version": "ictfvg_hyp012_context_result_manifest.v1",
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256(Path(__file__).resolve()),
        "outputs": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in outputs
        ],
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "HYP012_CONTEXT_RESULT PASS "
        f"control_n={control['positions']} challenger_n={challenger['positions']} "
        f"challenger_pf={challenger['profit_factor_money']:.4f} "
        f"challenger_exp_r={challenger['expectancy_r']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
