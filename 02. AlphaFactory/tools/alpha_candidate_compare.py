#!/usr/bin/env python3
"""Compare a generic AlphaFactory challenger with its frozen matched control.

Absolute acceptance gates belong to the frozen preregistration and unified
validator.  This comparator enforces only identity parity and control-relative
improvement, so it does not smuggle Sonic-specific strategy thresholds into a
generic EA lane.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
RUNS_ROOT = TOOLS_DIR.parent / "runs"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"required artifact is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def finite(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def integer(value: Any, label: str) -> int:
    number = finite(value, label)
    if not number.is_integer():
        raise ValueError(f"{label} must be an integer")
    return int(number)


def resolve_run(value: str, ea_name: str) -> Path:
    supplied = Path(value)
    if supplied.exists():
        return supplied.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


def collect(run_dir: Path, expected_ea: str) -> dict[str, Any]:
    manifest = load_json(run_dir / "run_manifest.json")
    summary = load_json(run_dir / "analysis" / "enhanced_summary.json")
    validation = load_json(run_dir / "analysis" / "validation_summary.json")
    ea_name = str(manifest.get("ea_name") or "")
    if ea_name != expected_ea:
        raise ValueError(f"EA identity mismatch in {run_dir}: {ea_name!r} != {expected_ea!r}")
    metrics = {
        "n_trades": integer(summary.get("n_trades"), "n_trades"),
        "net_profit": finite(summary.get("net_profit"), "net_profit"),
        "profit_factor": finite(summary.get("profit_factor"), "profit_factor"),
        "max_drawdown_abs": finite(summary.get("max_drawdown_abs"), "max_drawdown_abs"),
        "max_drawdown_pct": finite(summary.get("max_drawdown_pct"), "max_drawdown_pct"),
        "expectancy_per_trade": finite(summary.get("expectancy_per_trade"), "expectancy_per_trade"),
    }
    drawdown = abs(metrics["max_drawdown_abs"])
    metrics["net_to_drawdown"] = (
        metrics["net_profit"] / drawdown
        if drawdown > 0
        else (float("inf") if metrics["net_profit"] > 0 else 0.0)
    )
    return {
        "run_id": str(manifest.get("run_id") or run_dir.name),
        "run_dir": str(run_dir),
        "ea_name": ea_name,
        "symbol": str(manifest.get("symbol") or ""),
        "period": str(manifest.get("period") or ""),
        "from": str(manifest.get("from") or ""),
        "to": str(manifest.get("to") or ""),
        "model": integer(manifest.get("model"), "model"),
        "metrics": metrics,
        "validation_verdict": str(validation.get("verdict") or "").upper(),
    }


def compare(candidate: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    for key in ("ea_name", "symbol", "period", "from", "to", "model"):
        if candidate[key] != baseline[key]:
            findings.append(f"identity_mismatch:{key}")
    if baseline["validation_verdict"] != "PASS":
        findings.append(f"baseline_validation_not_passed:{baseline['validation_verdict']}")
    if candidate["validation_verdict"] != "PASS":
        findings.append(f"candidate_validation_not_passed:{candidate['validation_verdict']}")

    cm = candidate["metrics"]
    bm = baseline["metrics"]
    if cm["n_trades"] <= 0:
        findings.append("candidate_has_no_trades")
    if cm["net_profit"] <= bm["net_profit"]:
        findings.append("net_profit_not_above_control")
    if cm["profit_factor"] <= bm["profit_factor"]:
        findings.append("profit_factor_not_above_control")
    if cm["net_to_drawdown"] < bm["net_to_drawdown"]:
        findings.append("net_to_drawdown_below_control")
    return findings


def json_safe(value: Any) -> Any:
    if isinstance(value, float) and math.isinf(value):
        return "INF"
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare an AlphaFactory EA challenger with a matched control.")
    parser.add_argument("candidate", help="Candidate run id or run directory")
    parser.add_argument("--baseline", required=True, help="Matched-control run id or run directory")
    parser.add_argument("--ea", required=True, help="Canonical EA package name")
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    try:
        candidate = collect(resolve_run(args.candidate, args.ea), args.ea)
        baseline = collect(resolve_run(args.baseline, args.ea), args.ea)
        findings = compare(candidate, baseline)
        result = {
            "schema_version": "alphafactory_candidate_compare.v1",
            "comparison_policy": "generic-control-improvement-v1",
            "baseline": baseline,
            "candidate": candidate,
            "delta": {
                key: candidate["metrics"][key] - baseline["metrics"][key]
                for key in ("n_trades", "net_profit", "profit_factor", "max_drawdown_abs", "max_drawdown_pct", "expectancy_per_trade")
            },
            "findings": findings,
            "verdict": "RESEARCH_PASS" if not findings else "REVIEW",
            "note": "Relative research comparison only; promotion remains governed by frozen preregistration and validation gates.",
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "schema_version": "alphafactory_candidate_compare.v1",
            "comparison_policy": "generic-control-improvement-v1",
            "findings": [f"invalid_evidence:{exc}"],
            "verdict": "INVALID",
        }

    safe_result = json_safe(result)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(safe_result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(safe_result, indent=2, ensure_ascii=False))
    return 0 if safe_result["verdict"] == "RESEARCH_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
