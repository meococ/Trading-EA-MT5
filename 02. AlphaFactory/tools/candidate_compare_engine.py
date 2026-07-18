#!/usr/bin/env python3
"""Compare a Sonic R candidate run against a frozen AlphaFactory baseline."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


SCRIPT_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = SCRIPT_DIR.parent
RUNS_ROOT = ALPHA_ROOT / "runs"
DEFAULT_EA = "EA_SonicR"
DEFAULT_BASELINE = "20260501_000718"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-16"))


def safe_num(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def run_dir_for(value: str, ea_name: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


def artifact(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": str(path),
        "exists": exists,
        "bytes": path.stat().st_size if exists and path.is_file() else 0,
    }


def pass_count(validation_summary: dict[str, Any] | None) -> tuple[int, int, str]:
    if not validation_summary:
        return 0, 0, "MISSING"
    return (
        safe_int(validation_summary.get("gates_passed")),
        safe_int(validation_summary.get("gates_total")),
        str(validation_summary.get("verdict") or ""),
    )


def collect_run(run_dir: Path) -> dict[str, Any]:
    analysis = run_dir / "analysis"
    manifest = load_json(run_dir / "run_manifest.json")
    summary = load_json(analysis / "enhanced_summary.json")
    validation = load_json(analysis / "validation_summary.json")
    monthly = load_json(analysis / "monthly_fitness.json")
    overnight = load_json(analysis / "overnight_exposure.json")
    slippage = load_json(analysis / "slippage_summary.json")
    weaknesses = load_json(analysis / "weaknesses.json")

    gates_passed, gates_total, validation_verdict = pass_count(validation)
    months = monthly.get("months", []) if monthly else []
    positive_months = sum(1 for row in months if safe_num(row.get("net_profit")) > 0)
    negative_months = sum(1 for row in months if safe_num(row.get("net_profit")) < 0)
    total_months = safe_int((monthly or {}).get("monthly_window", {}).get("total_months"), len(months))
    active_months = safe_int((monthly or {}).get("monthly_window", {}).get("active_months"))
    monthly_mean_pct = safe_num((monthly or {}).get("gross_monthly", {}).get("mean_return_pct"))
    target_classification = str((monthly or {}).get("target_band", {}).get("classification") or "")
    overnight_ratios = (overnight or {}).get("ratios", {})

    return {
        "run_dir": str(run_dir),
        "run_id": (manifest or {}).get("run_id") or run_dir.name,
        "ea_name": (manifest or {}).get("ea_name") or DEFAULT_EA,
        "symbol": (manifest or {}).get("symbol") or (monthly or {}).get("symbol") or "",
        "period": (manifest or {}).get("period") or (monthly or {}).get("period") or "",
        "from": (manifest or {}).get("from") or "",
        "to": (manifest or {}).get("to") or "",
        "model": safe_int((manifest or {}).get("model")),
        "overrides": (manifest or {}).get("overrides") or "",
        "metrics": {
            "n_trades": safe_int((summary or {}).get("n_trades")),
            "net_profit": safe_num((summary or {}).get("net_profit")),
            "profit_factor": safe_num((summary or {}).get("profit_factor")),
            "win_rate_pct": safe_num((summary or {}).get("win_rate_pct")),
            "max_drawdown_pct": safe_num((summary or {}).get("max_drawdown_pct")),
            "max_drawdown_abs": safe_num((summary or {}).get("max_drawdown_abs")),
            "expectancy_per_trade": safe_num((summary or {}).get("expectancy_per_trade")),
            "positive_months": positive_months,
            "negative_months": negative_months,
            "total_months": total_months,
            "active_months": active_months,
            "positive_month_ratio": safe_num((monthly or {}).get("consistency", {}).get("positive_month_ratio")),
            "monthly_mean_return_pct": monthly_mean_pct,
            "annualized_from_mean_pct": safe_num(
                (monthly or {}).get("gross_monthly", {}).get("annualized_from_mean_pct")
            ),
            "overnight_pct": safe_num(overnight_ratios.get("overnight_pct")),
            "weekend_crossing_pct": safe_num(overnight_ratios.get("weekend_crossing_pct")),
            "validation_gates_passed": gates_passed,
            "validation_gates_total": gates_total,
        },
        "status": {
            "validation_verdict": validation_verdict,
            "monthly_target_classification": target_classification,
            "slippage_status": str((slippage or {}).get("status") or "MISSING"),
            "weaknesses_count": len(weaknesses) if isinstance(weaknesses, list) else safe_int((summary or {}).get("weaknesses_count")),
        },
        "artifacts": {
            "run_manifest": artifact(run_dir / "run_manifest.json"),
            "report": artifact(run_dir / "report.html"),
            "enhanced_summary": artifact(analysis / "enhanced_summary.json"),
            "validation_summary": artifact(analysis / "validation_summary.json"),
            "monthly_fitness": artifact(analysis / "monthly_fitness.json"),
            "overnight_exposure": artifact(analysis / "overnight_exposure.json"),
            "slippage_summary": artifact(analysis / "slippage_summary.json"),
        },
    }


def deltas(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, float]:
    keys = [
        "n_trades",
        "net_profit",
        "profit_factor",
        "win_rate_pct",
        "max_drawdown_pct",
        "expectancy_per_trade",
        "positive_months",
        "active_months",
        "monthly_mean_return_pct",
        "annualized_from_mean_pct",
        "validation_gates_passed",
    ]
    result: dict[str, float] = {}
    base_metrics = baseline["metrics"]
    cand_metrics = candidate["metrics"]
    for key in keys:
        result[key] = round(safe_num(cand_metrics.get(key)) - safe_num(base_metrics.get(key)), 6)
    return result


def gate_findings(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    cm = candidate["metrics"]
    bm = baseline["metrics"]
    status = candidate["status"]

    for key in ("symbol", "period", "from", "to", "model"):
        if candidate.get(key) != baseline.get(key):
            findings.append(f"identity_mismatch:{key}:{baseline.get(key)}!={candidate.get(key)}")
    if status["validation_verdict"].upper() != "PASS":
        findings.append(f"validation_not_passed:{status['validation_verdict']}")
    if cm["profit_factor"] < 1.30:
        findings.append("pf_below_1_30")
    if cm["net_profit"] <= bm["net_profit"]:
        findings.append("net_not_above_baseline")
    if cm["max_drawdown_pct"] > 5.0:
        findings.append("dd_above_5pct")
    if cm["active_months"] < cm["total_months"]:
        findings.append("inactive_months_present")
    if cm["positive_months"] < 15:
        findings.append("positive_months_below_demo_floor")
    if cm["overnight_pct"] > 0 or cm["weekend_crossing_pct"] > 0:
        findings.append("overnight_or_weekend_exposure")
    if status["slippage_status"].upper() != "OK":
        findings.append(f"slippage_not_ok:{status['slippage_status']}")
    return findings


def compare(args: argparse.Namespace) -> dict[str, Any]:
    baseline_dir = run_dir_for(args.baseline, args.ea)
    candidate_dir = run_dir_for(args.candidate, args.ea)
    baseline = collect_run(baseline_dir)
    candidate = collect_run(candidate_dir)
    missing = []
    for label, run in (("baseline", baseline), ("candidate", candidate)):
        for key, info in run["artifacts"].items():
            if key in {"run_manifest", "report", "enhanced_summary"} and not info["exists"]:
                missing.append(f"{label}:{key}:{info['path']}")
    verdict = "REVIEW"
    findings = gate_findings(baseline, candidate)
    if missing:
        verdict = "INVALID"
    elif not findings:
        verdict = "RESEARCH_PASS"

    return {
        "schema_version": "sonic_candidate_compare.v1",
        "baseline": baseline,
        "candidate": candidate,
        "delta": deltas(baseline, candidate),
        "findings": missing + findings,
        "verdict": verdict,
        "note": "Research comparator only. It does not promote demo/prop/live.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare EA_SonicR run artifacts against a frozen baseline.")
    ap.add_argument("candidate", help="Candidate run id or run directory.")
    ap.add_argument("--baseline", default=DEFAULT_BASELINE, help=f"Baseline run id or path (default: {DEFAULT_BASELINE}).")
    ap.add_argument("--ea", default=DEFAULT_EA, help=f"EA name under AlphaFactory runs (default: {DEFAULT_EA}).")
    ap.add_argument("--out", default="", help="Optional JSON output path.")
    args = ap.parse_args()

    result = compare(args)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    print(text)
    # REVIEW is intentionally nonzero: callers must never treat a completed
    # comparison process as proof that the challenger beat its control.
    return 0 if result["verdict"] == "RESEARCH_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
