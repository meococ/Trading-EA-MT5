#!/usr/bin/env python3
"""Build a compact Sonic R casebook analysis index for one AlphaFactory run."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path, help="AlphaFactory run directory.")
    parser.add_argument("--out-json", type=Path, help="Default: <run>/analysis/casebook_analysis_index.json")
    parser.add_argument("--out-md", type=Path, help="Default: <run>/analysis/casebook_analysis_readout.md")
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def first_existing(paths: List[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def glob_one(directory: Path, pattern: str) -> Optional[Path]:
    matches = sorted(directory.glob(pattern))
    return matches[0] if matches else None


def rel(path: Optional[Path], root: Path) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def count_csv_rows(path: Optional[Path]) -> int:
    if path is None or not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def pick_cost_scenario(cost: Dict[str, Any], scenario: str) -> Dict[str, Any]:
    for row in cost.get("scenarios", []):
        if row.get("scenario") == scenario:
            return row
    return {}


def build_index(run_dir: Path) -> Dict[str, Any]:
    run_dir = run_dir.resolve()
    analysis = run_dir / "analysis"

    enhanced_path = analysis / "enhanced_summary.json"
    validation_path = analysis / "validation_summary.json"
    monthly_path = analysis / "monthly_fitness.json"
    slippage_path = analysis / "slippage_summary.json"
    tca_path = analysis / "tca_summary.json"
    trades_summary_path = analysis / "datalog" / "trades_summary.json"
    signals_summary_path = analysis / "datalog" / "signals_summary.json"
    outcome_manifest_path = analysis / "evidence_lite" / "manifest.json"
    outcome_summary_path = analysis / "evidence_lite" / "summary.json"
    asof_manifest_path = analysis / "entry_asof_casebook" / "manifest.json"
    state_manifest_path = analysis / "sonic_state" / "sonic_state_manifest.json"
    opportunity_analysis_path = analysis / "sonic_opportunity_analysis.json"
    opportunity_labels_path = analysis / "opportunity_labels.csv"
    trade_mfe_mae_path = analysis / "trade_mfe_mae_labels.csv"
    label_audit_path = analysis / "sonic_state" / "sonic_state_label_audit.json"
    machine_labels_path = analysis / "sonic_state" / "sonic_state_machine_labels.csv"
    population_summary_path = analysis / "sonic_population" / "population_summary.json"
    population_readout_path = analysis / "sonic_population" / "population_readout.md"
    population_features_path = analysis / "sonic_population" / "population_features.csv"
    native_mt5_manifest_path = analysis / "native_mt5_casebook" / "manifest.json"
    native_mt5_cases_path = analysis / "native_mt5_casebook" / "cases.csv"
    compare_path = glob_one(analysis, "sonic_candidate_compare_vs_*.json")
    cost_path = first_existing(sorted(analysis.glob("sonic_cost_stress_*.json")))

    enhanced = load_json(enhanced_path)
    validation = load_json(validation_path)
    monthly = load_json(monthly_path)
    slippage = load_json(slippage_path)
    tca = load_json(tca_path)
    trades_summary = load_json(trades_summary_path)
    signals_summary = load_json(signals_summary_path)
    outcome_manifest = load_json(outcome_manifest_path)
    outcome_summary = load_json(outcome_summary_path)
    asof_manifest = load_json(asof_manifest_path)
    state_manifest = load_json(state_manifest_path)
    opportunity_analysis = load_json(opportunity_analysis_path)
    label_audit = load_json(label_audit_path)
    population_summary = load_json(population_summary_path)
    native_mt5_manifest = load_json(native_mt5_manifest_path)
    compare = load_json(compare_path) if compare_path else {}
    cost = load_json(cost_path) if cost_path else {}

    state_outputs = state_manifest.get("output_files", {})
    cases_csv = Path(state_outputs.get("audit_cases", "")) if state_outputs.get("audit_cases") else None
    blind_csv = Path(state_outputs.get("blinded_label_input", "")) if state_outputs.get("blinded_label_input") else None

    x1_cost = pick_cost_scenario(cost, "cost_x1_00")
    x150_cost = pick_cost_scenario(cost, "cost_x1_50")
    x2_cost = pick_cost_scenario(cost, "cost_x2_00")

    return {
        "schema_version": "sonic_casebook_analysis_index.v1",
        "run_id": run_dir.name,
        "role": "post_backtest_casebook_and_trade_stats_index",
        "verdict": "REVIEW_ONLY",
        "promotion_blocked": True,
        "promotion_block_reason": "casebook is evidence for research; validation and robustness are not PASS",
        "artifact_groups": {
            "entry_asof_visual_context": {
                "purpose": "pre-entry chart review without future bars",
                "html": rel(Path(asof_manifest.get("outputs", {}).get("casebook_html", "")) if asof_manifest else None, run_dir),
                "cases_csv": rel(Path(asof_manifest.get("outputs", {}).get("cases_csv", "")) if asof_manifest else None, run_dir),
                "manifest": rel(asof_manifest_path if asof_manifest else None, run_dir),
                "visual_mode": asof_manifest.get("visual_mode", ""),
                "pre_bars": asof_manifest.get("pre_bars", ""),
                "post_bars": asof_manifest.get("post_bars", ""),
                "case_count": asof_manifest.get("case_count", 0),
                "size_cap_pass": asof_manifest.get("size_cap_pass", False),
            },
            "outcome_anatomy_visual_context": {
                "purpose": "post-entry win/loss anatomy; not allowed for pre-entry setup labeling",
                "html": rel(Path(outcome_manifest.get("outputs", {}).get("casebook_html", "")) if outcome_manifest else None, run_dir),
                "cases_csv": rel(Path(outcome_manifest.get("outputs", {}).get("cases_csv", "")) if outcome_manifest else None, run_dir),
                "manifest": rel(outcome_manifest_path if outcome_manifest else None, run_dir),
                "pre_bars": outcome_manifest.get("pre_bars", ""),
                "post_bars": outcome_manifest.get("post_bars", ""),
                "case_count": outcome_manifest.get("case_count", 0),
                "size_cap_pass": outcome_manifest.get("size_cap_pass", False),
            },
            "manual_label_set": {
                "audit_cases_csv": rel(cases_csv, run_dir),
                "blinded_label_input_csv": rel(blind_csv, run_dir),
                "machine_suggested_labels_csv": rel(machine_labels_path if machine_labels_path.exists() else None, run_dir),
                "machine_label_audit_json": rel(label_audit_path if label_audit else None, run_dir),
                "manifest": rel(state_manifest_path if state_manifest else None, run_dir),
                "audit_cases": count_csv_rows(cases_csv),
                "blinded_cases": count_csv_rows(blind_csv),
                "machine_suggested_labels": count_csv_rows(machine_labels_path if machine_labels_path.exists() else None),
                "label_leakage_guard": state_manifest.get("label_leakage_guard", {}),
                "selection_summary": state_manifest.get("selection_summary", {}),
            },
            "forward_mfe_mae_labels": {
                "opportunity_analysis_json": rel(opportunity_analysis_path if opportunity_analysis else None, run_dir),
                "opportunity_labels_csv": rel(opportunity_labels_path if opportunity_labels_path.exists() else None, run_dir),
                "trade_mfe_mae_labels_csv": rel(trade_mfe_mae_path if trade_mfe_mae_path.exists() else None, run_dir),
                "opportunity_labels": count_csv_rows(opportunity_labels_path if opportunity_labels_path.exists() else None),
                "trade_labels": count_csv_rows(trade_mfe_mae_path if trade_mfe_mae_path.exists() else None),
                "opportunity_label_summary": opportunity_analysis.get("opportunity_labels", {}),
                "trade_mfe_mae_summary": opportunity_analysis.get("mfe_mae", {}),
            },
            "population_feature_audit": {
                "summary_json": rel(population_summary_path if population_summary else None, run_dir),
                "readout_md": rel(population_readout_path if population_readout_path.exists() else None, run_dir),
                "features_csv": rel(population_features_path if population_features_path.exists() else None, run_dir),
                "population_rows": population_summary.get("population_rows"),
                "research_population_rows": population_summary.get("research_population_rows"),
                "verdict": population_summary.get("verdict"),
                "feature_stability": population_summary.get("feature_stability", []),
            },
            "native_mt5_screenshots": {
                "purpose": "sampled MT5-native visual audit; not a promotion gate",
                "manifest": rel(native_mt5_manifest_path if native_mt5_manifest else None, run_dir),
                "cases_csv": rel(native_mt5_cases_path if native_mt5_cases_path.exists() else None, run_dir),
                "selected_cases": native_mt5_manifest.get("selected_cases"),
                "capture_status": native_mt5_manifest.get("capture_status"),
                "mt5_files_dir": native_mt5_manifest.get("mt5_files_dir", ""),
                "expected_shots_csv": native_mt5_manifest.get("expected_shots_csv", ""),
            },
            "verified_trade_stats": {
                "enhanced_summary": rel(enhanced_path, run_dir),
                "datalog_trades_summary": rel(trades_summary_path, run_dir),
                "datalog_signals_summary": rel(signals_summary_path, run_dir),
                "tca_summary": rel(tca_path, run_dir),
                "slippage_summary": rel(slippage_path, run_dir),
            },
        },
        "run_metrics": {
            "trades": enhanced.get("n_trades"),
            "net_profit": enhanced.get("net_profit"),
            "profit_factor": enhanced.get("profit_factor"),
            "win_rate_pct": enhanced.get("win_rate_pct"),
            "expectancy_per_trade": enhanced.get("expectancy_per_trade"),
            "max_drawdown_pct": enhanced.get("max_drawdown_pct"),
            "active_months": monthly.get("monthly_window", {}).get("active_months"),
            "positive_month_ratio": monthly.get("consistency", {}).get("positive_month_ratio"),
            "monthly_mean_return_pct": monthly.get("gross_monthly", {}).get("mean_return_pct"),
            "validation_verdict": validation.get("verdict"),
            "validation_gates_passed": validation.get("gates_passed"),
            "validation_gates_total": validation.get("gates_total"),
        },
        "route_and_exit_stats": {
            "trade_reasons": outcome_summary.get("trade_reasons", []),
            "trade_reason_population": state_manifest.get("selection_summary", {}).get("trade_reason_population", {}),
            "by_close_reason": trades_summary.get("by_close_reason", []),
            "by_close_source": trades_summary.get("by_close_source", []),
            "achieved_r": trades_summary.get("achieved_r", {}),
            "canonical_trade_file_policy": trades_summary.get("canonical_trade_file_policy", ""),
            "excluded_duplicate_event_files": trades_summary.get("excluded_duplicate_event_files", []),
        },
        "signal_and_blocker_stats": {
            "signals_total": signals_summary.get("total"),
            "signals_executed": signals_summary.get("executed"),
            "signals_skipped": signals_summary.get("skipped"),
            "top_skip_reasons": signals_summary.get("skip_reason", [])[:20],
            "opportunity_outcomes": outcome_summary.get("opportunity_outcomes", []),
            "opportunity_block_reasons": outcome_summary.get("opportunity_block_reasons", [])[:20],
        },
        "execution_and_cost": {
            "slippage_status": slippage.get("status"),
            "slippage_pts": slippage.get("slippage_pts", {}),
            "execution_quality": slippage.get("execution_quality", {}),
            "tca_exec": tca.get("exec", {}),
            "cost_stress_file": rel(cost_path, run_dir),
            "cost_x1_00": x1_cost,
            "cost_x1_50": x150_cost,
            "cost_x2_00": x2_cost,
            "cost_findings": cost.get("findings", []),
        },
        "baseline_comparison": {
            "file": rel(compare_path, run_dir),
            "verdict": compare.get("verdict"),
            "delta": compare.get("delta", {}),
            "findings": compare.get("findings", []),
        },
        "gates": {
            "visual_no_hindsight_entry_review": asof_manifest.get("post_bars") == 0,
            "outcome_visual_marked_preview_only": outcome_manifest.get("verdict") == "PREVIEW_ONLY",
            "evidence_size_cap_pass": bool(asof_manifest.get("size_cap_pass")) and bool(outcome_manifest.get("size_cap_pass")),
            "blind_label_csv_present": bool(blind_csv and blind_csv.exists()),
            "opportunity_mfe_mae_labels_present": count_csv_rows(opportunity_labels_path if opportunity_labels_path.exists() else None) > 0,
            "trade_mfe_mae_labels_present": count_csv_rows(trade_mfe_mae_path if trade_mfe_mae_path.exists() else None) > 0,
            "machine_label_audit_present": bool(label_audit),
            "population_feature_audit_present": bool(population_summary),
            "population_feature_passed": any(item.get("pass_research_stability") for item in population_summary.get("feature_stability", [])),
            "native_mt5_request_present": bool(native_mt5_manifest),
            "canonical_trade_count_matches_report": enhanced.get("n_trades") == trades_summary.get("total"),
            "validation_passed": validation.get("verdict") == "PASS",
            "cost_stress_pf_gt_125_at_x150": (x150_cost.get("profit_factor") or 0) > 1.25,
        },
        "limitations": [
            "Entry-as-of charts are SVG reconstructions from post-run OHLC/PVSRA sidecar, not raw MT5 screenshots.",
            "Outcome anatomy charts include post-entry bars and must not be used for blind setup-quality labels.",
            "Forward MFE/MAE labels are audit/outcome evidence and must not be used for blind pre-entry setup labels.",
            "Machine labels are heuristic suggestions only; human/pro-quant labels are still required before coding a state filter.",
            "This index is a research aid and does not change EA behavior or promote readiness.",
        ],
    }


def render_md(index: Dict[str, Any]) -> str:
    m = index["run_metrics"]
    route_stats = index["route_and_exit_stats"]
    exec_cost = index["execution_and_cost"]
    gates = index["gates"]
    population = index["artifact_groups"].get("population_feature_audit", {})
    native_mt5 = index["artifact_groups"].get("native_mt5_screenshots", {})
    lines = [
        "# Sonic R Casebook Analysis Readout",
        "",
        f"- Run: `{index['run_id']}`",
        f"- Verdict: `{index['verdict']}`; promotion blocked: `{index['promotion_block_reason']}`",
        f"- Trades: `{m.get('trades')}` | PF `{m.get('profit_factor'):.4f}` | net `{m.get('net_profit'):.2f}` | DD `{m.get('max_drawdown_pct'):.2f}%`",
        f"- Active months: `{m.get('active_months')}` | positive month ratio `{m.get('positive_month_ratio')}` | monthly mean return `{m.get('monthly_mean_return_pct')}%`",
        f"- Validation: `{m.get('validation_verdict')}` `{m.get('validation_gates_passed')}/{m.get('validation_gates_total')}`",
        "",
        "## Visual Evidence",
        "",
        f"- Entry-as-of chart HTML: `{index['artifact_groups']['entry_asof_visual_context']['html']}`",
        f"- Outcome anatomy chart HTML: `{index['artifact_groups']['outcome_anatomy_visual_context']['html']}`",
        f"- Label input CSV: `{index['artifact_groups']['manual_label_set']['blinded_label_input_csv']}`",
        f"- Audit cases CSV: `{index['artifact_groups']['manual_label_set']['audit_cases_csv']}`",
        f"- Machine label audit: `{index['artifact_groups']['manual_label_set']['machine_label_audit_json']}`",
        f"- Opportunity MFE/MAE labels: `{index['artifact_groups']['forward_mfe_mae_labels']['opportunity_labels_csv']}`",
        f"- Trade MFE/MAE labels: `{index['artifact_groups']['forward_mfe_mae_labels']['trade_mfe_mae_labels_csv']}`",
        f"- Population feature audit: `{population.get('readout_md')}`",
        f"- Population rows: `{population.get('population_rows')}` | research population `{population.get('research_population_rows')}` | verdict `{population.get('verdict')}`",
        f"- Native MT5 snapshot request: `{native_mt5.get('manifest')}` | status `{native_mt5.get('capture_status')}` | cases `{native_mt5.get('selected_cases')}`",
        "",
        "## Trade Stats",
        "",
        f"- Routes: `{route_stats.get('trade_reasons')}`",
        f"- Close reasons: `{route_stats.get('by_close_reason')}`",
        f"- AchievedR: `{route_stats.get('achieved_r')}`",
        f"- Canonical trade policy: `{route_stats.get('canonical_trade_file_policy') or 'single canonical trade file'}`",
        "",
        "## Execution And Cost",
        "",
        f"- Slippage status: `{exec_cost.get('slippage_status')}` | points `{exec_cost.get('slippage_pts')}`",
        f"- Cost x1.50 PF: `{(exec_cost.get('cost_x1_50') or {}).get('profit_factor')}` | net `{(exec_cost.get('cost_x1_50') or {}).get('net_profit')}`",
        f"- Cost findings: `{exec_cost.get('cost_findings')}`",
        "",
        "## Gates",
        "",
    ]
    for key, value in gates.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Limitations", ""])
    for item in index.get("limitations", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    analysis = run_dir / "analysis"
    out_json = args.out_json or (analysis / "casebook_analysis_index.json")
    out_md = args.out_md or (analysis / "casebook_analysis_readout.md")
    index = build_index(run_dir)
    out_json.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    out_md.write_text(render_md(index), encoding="utf-8")
    print(json.dumps({"status": "ok", "json": str(out_json), "markdown": str(out_md)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
