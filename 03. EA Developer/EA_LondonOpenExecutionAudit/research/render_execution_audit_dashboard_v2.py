from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

import render_execution_audit_dashboard as base
import validate_execution_audit_v2 as validator


SCENARIOS = tuple(base.SCENARIOS)


def validate_validator_payload(payload: dict[str, Any], run_dirs: dict[str, Path]) -> None:
    expected_top = {
        "schema_version": "lomx_execution_audit.v2",
        "hypothesis_id": validator.HYPOTHESIS_ID,
        "audit_only": True,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "parent_economic_verdict_unchanged": "KILLED",
        "passed": True,
    }
    for key, expected in expected_top.items():
        if payload.get(key) != expected:
            raise RuntimeError(
                f"validator V2 {key} mismatch actual={payload.get(key)!r} expected={expected!r}"
            )
    rows = payload.get("scenario_results")
    if not isinstance(rows, list):
        raise RuntimeError("validator V2 scenario_results is not a list")
    by_scenario = {str(row.get("scenario")): row for row in rows}
    if set(by_scenario) != set(SCENARIOS):
        raise RuntimeError("validator V2 scenario set mismatch")
    for scenario, run_dir in run_dirs.items():
        row = by_scenario[scenario]
        if row.get("passed") is not True or row.get("errors") != []:
            raise RuntimeError(f"validator V2 did not pass {scenario}")
        if Path(str(row.get("run_dir"))).resolve() != run_dir.resolve():
            raise RuntimeError(f"validator V2 run identity mismatch for {scenario}")


def label_minutes(value: float) -> str:
    value = int(round(value))
    return f"{value // 60:02d}:{value % 60:02d}"


def main() -> int:
    parser = argparse.ArgumentParser()
    for scenario in SCENARIOS:
        parser.add_argument(f"--{scenario.lower().replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--validator-v2", required=True, type=Path)
    parser.add_argument("--json-out", required=True, type=Path)
    parser.add_argument("--png-out", required=True, type=Path)
    args = parser.parse_args()

    run_dirs = {scenario: getattr(args, scenario.lower()).resolve() for scenario in SCENARIOS}
    validator_payload = json.loads(args.validator_v2.read_text(encoding="utf-8-sig"))
    validate_validator_payload(validator_payload, run_dirs)

    live_results = {
        scenario: validator.validate_scenario_v2(scenario, run_dir)
        for scenario, run_dir in run_dirs.items()
    }
    live_failures = {
        scenario: result.errors for scenario, result in live_results.items() if not result.passed
    }
    if live_failures:
        raise RuntimeError(f"live V2 revalidation failed: {live_failures}")

    results = []
    spreads_by_scenario = []
    entry_slippage = []
    exit_slippage = []
    stored_by_scenario = {
        row["scenario"]: row for row in validator_payload["scenario_results"]
    }
    for scenario, run_dir in run_dirs.items():
        result, spreads, entry_adverse, exit_adverse = base.analyze(scenario, run_dir)
        result.pop("economics_diagnostic_only", None)
        result["canonical_alpha_analyzer_status"] = (
            "UNSUPPORTED_NA_FOR_DECISIONTELEMETRY_LIFECYCLEV3"
        )
        stored = stored_by_scenario[scenario]
        if result["run_manifest_sha256"] != stored["provenance"]["manifest_sha256"]:
            raise RuntimeError(f"manifest changed after validator V2 for {scenario}")
        if result["report_sha256"] != stored["provenance"]["report_sha256"]:
            raise RuntimeError(f"report changed after validator V2 for {scenario}")
        results.append(result)
        spreads_by_scenario.append(spreads)
        entry_slippage.append(entry_adverse)
        exit_slippage.append(exit_adverse)

    payload = {
        "schema_version": "lomx_execution_audit_dashboard.v2",
        "hypothesis_id": validator.HYPOTHESIS_ID,
        "audit_only": True,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "parent_economic_verdict_unchanged": "KILLED",
        "pass_authority": "LIVE_REVALIDATED_PROVENANCE_IDENTITY_AND_RULE_CONTRACT_V2",
        "validator_v2_path": str(args.validator_v2.resolve()),
        "validator_v2_sha256": base.sha256(args.validator_v2),
        "canonical_alpha_analyzer_status": (
            "UNSUPPORTED_NA_FOR_DECISIONTELEMETRY_LIFECYCLEV3"
        ),
        "first_eligible_tick_claim_authorized": False,
        "total_completed_lifecycles": sum(
            item["counts"]["lifecycle_final_closes"] for item in results
        ),
        "all_execution_contracts_passed": True,
        "scenarios": results,
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    names = [
        item["scenario"].replace("GBPUSD_", "GBP ").replace("EURUSD_", "EUR ")
        for item in results
    ]
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.subplots_adjust(left=0.07, right=0.98, top=0.90, bottom=0.15, hspace=0.36, wspace=0.30)
    fig.suptitle(
        "HYP-LOMX-EXEC-AUDIT-M1-003 | V2 provenance + deal-identity audit",
        fontsize=16,
        weight="bold",
    )

    ax = axes[0, 0]
    x = np.arange(len(names))
    width = 0.18
    for idx, key in enumerate(
        ["signals", "entry_deals", "exit_deals", "lifecycle_final_closes"]
    ):
        ax.bar(x + (idx - 1.5) * width, [r["counts"][key] for r in results], width, label=key)
    ax.axhline(1000, color="#b22222", linestyle="--", linewidth=1.3, label="frozen floor=1000")
    ax.set_title("Exact-ID reconciled population")
    ax.set_xticks(x, names, rotation=12, ha="right")
    ax.set_ylabel("rows / completed lifecycles")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[0, 1]
    for idx, result in enumerate(results):
        timings = result["time_compliance"]
        values = [
            timings["signal_minute_min_median_max"][1],
            timings["entry_minute_min_median_max"][1],
            timings["exit_minute_min_median_max"][1],
        ]
        ax.plot(values, [idx] * 3, "o-", linewidth=2, markersize=7)
        if values[0] == values[1]:
            labels = [(values[0], "signal + entry", 0), (values[2], "exit", 0)]
        else:
            labels = [
                (values[0], "signal", 0),
                (values[1], "entry", -14),
                (values[2], "exit", 14),
            ]
        for value, stage, x_offset in labels:
            ax.annotate(
                f"{stage} {label_minutes(value)}",
                (value, idx),
                xytext=(x_offset, 8),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )
    ax.set_yticks(range(len(names)), names)
    ticks = sorted({511, 720, 930, 960, 990})
    ax.set_xticks(ticks, [label_minutes(v) for v in ticks], rotation=25, ha="right")
    ax.set_xlim(8 * 60, 17 * 60)
    ax.set_title("London-time event sequence (descriptive)")
    ax.grid(axis="x", alpha=0.3)

    ax = axes[1, 0]
    ax.boxplot(spreads_by_scenario, tick_labels=names, showfliers=False)
    ax.set_title("Executable spread at entry request")
    ax.set_ylabel("pips")
    ax.tick_params(axis="x", rotation=12)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1, 1]
    entry_p95 = [float(series.quantile(0.95)) for series in entry_slippage]
    exit_p95 = [float(series.quantile(0.95)) for series in exit_slippage]
    ax.bar(x - 0.15, entry_p95, 0.3, label="entry adverse p95")
    ax.bar(x + 0.15, exit_p95, 0.3, label="exit adverse p95")
    if max([abs(value) for value in entry_p95 + exit_p95], default=0.0) < 1e-12:
        ax.set_ylim(-0.05, 0.05)
        for index in x:
            ax.annotate(
                "entry/exit p95 = 0.000",
                (index, 0.0),
                xytext=(0, 8),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )
    ax.set_xticks(x, names, rotation=12, ha="right")
    ax.set_ylabel("pips")
    ax.set_title("Request-to-deal adverse fill delta")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)

    fig.text(
        0.5,
        0.025,
        "AUDIT ONLY - PASS comes from live V2 provenance + exact deal-ID reconciliation; economics/deploy authority remain FALSE.",
        ha="center",
        color="#b22222",
        weight="bold",
    )
    args.png_out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.png_out, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(
        json.dumps(
            {
                "all_execution_contracts_passed": True,
                "total_completed_lifecycles": payload["total_completed_lifecycles"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
