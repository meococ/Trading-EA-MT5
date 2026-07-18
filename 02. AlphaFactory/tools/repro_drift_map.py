#!/usr/bin/env python3
"""Map reproducibility drift across EA_SonicR AlphaFactory runs.

This is a research/control-plane tool. It compares run identity, tester inputs,
cache guard metadata, and headline performance so a cadence change is not
mistaken for strategy improvement before the setup/source drift is explained.
"""

from __future__ import annotations

import argparse
import hashlib
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
DEFAULT_RUNS = ["20260501_000718", "20260501_150443", "20260501_150910", "20260501_151422"]


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-16"))
    except json.JSONDecodeError:
        return None


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


def sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_dir_for(value: str, ea_name: str) -> Path:
    path = Path(value)
    if path.exists():
        return path.resolve()
    return (RUNS_ROOT / ea_name / value).resolve()


def parse_override_text(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in text.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def parse_tester_inputs(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff") or b"\x00" in raw[:200]:
        text = raw.decode("utf-16", errors="replace")
    else:
        text = raw.decode("utf-8-sig", errors="replace")
    in_inputs = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            in_inputs = line.lower() == "[testerinputs]"
            continue
        if not in_inputs or "=" not in line:
            continue
        key, rest = line.split("=", 1)
        result[key.strip()] = rest.split("||", 1)[0].strip()
    return result


def collect_run(run_dir: Path) -> dict[str, Any]:
    manifest = load_json(run_dir / "run_manifest.json") or {}
    cache_guard = load_json(run_dir / "cache_guard.json") or {}
    analysis = run_dir / "analysis"
    summary = load_json(analysis / "enhanced_summary.json") or {}
    validation = load_json(analysis / "validation_summary.json") or {}
    monthly = load_json(analysis / "monthly_fitness.json") or {}
    cost_050 = load_json(analysis / "sonic_cost_stress_report_only_050.json") or {}
    evidence = load_json(analysis / "evidence_audit.json") or {}
    overrides = parse_override_text(str(manifest.get("overrides") or ""))
    tester_inputs = parse_tester_inputs(run_dir / "config.ini")
    months = (monthly.get("monthly_window") or {}) if isinstance(monthly, dict) else {}

    trade_identity = {
        "ea_name": str(manifest.get("ea_name") or ""),
        "symbol": str(manifest.get("symbol") or ""),
        "period": str(manifest.get("period") or ""),
        "from": str(manifest.get("from") or ""),
        "to": str(manifest.get("to") or ""),
        "model": safe_int(manifest.get("model")),
        "execution_mode": safe_int(manifest.get("execution_mode")),
    }
    runtime_identity = {
        **trade_identity,
        "timeout_sec": safe_int(manifest.get("timeout_sec")),
    }

    return {
        "run_id": str(manifest.get("run_id") or run_dir.name),
        "run_dir": str(run_dir),
        "trade_identity": trade_identity,
        "runtime_identity": runtime_identity,
        "identity": runtime_identity,
        "metrics": {
            "n_trades": safe_int(summary.get("n_trades")),
            "net_profit": round(safe_num(summary.get("net_profit")), 2),
            "profit_factor": round(safe_num(summary.get("profit_factor")), 6),
            "win_rate_pct": round(safe_num(summary.get("win_rate_pct")), 6),
            "expectancy_per_trade": round(safe_num(summary.get("expectancy_per_trade")), 6),
            "max_drawdown_pct": round(safe_num(summary.get("max_drawdown_pct")), 6),
            "active_months": safe_int(months.get("active_months")),
            "total_months": safe_int(months.get("total_months")),
            "validation_verdict": str(validation.get("verdict") or "MISSING"),
            "validation_gates_passed": safe_int(validation.get("gates_passed")),
            "validation_gates_total": safe_int(validation.get("gates_total")),
        },
        "cost_050": summarize_cost(cost_050),
        "artifact_status": {
            "report_exists": (run_dir / "report.html").exists(),
            "summary_exists": (analysis / "enhanced_summary.json").exists(),
            "validation_exists": (analysis / "validation_summary.json").exists(),
            "evidence_status": str(evidence.get("status") or ""),
        },
        "fingerprints": {
            "config_ini_sha256": str(cache_guard.get("config_ini_sha256") or sha256_file(run_dir / "config.ini")),
            "overrides_sha256": hashlib.sha256(
                str(manifest.get("overrides") or "").encode("utf-8", errors="replace")
            ).hexdigest(),
            "report_sha256": sha256_file(run_dir / "report.html"),
            "report_bytes": (run_dir / "report.html").stat().st_size if (run_dir / "report.html").exists() else 0,
            "override_count": safe_int(cache_guard.get("override_count"), len(overrides)),
            "tester_inputs_verified": bool(cache_guard.get("tester_inputs_verified")),
            "sidecar_hygiene_ok": bool(cache_guard.get("sidecar_hygiene_ok")),
            "expected_variant_tag": str(cache_guard.get("expected_variant_tag") or ""),
        },
        "overrides": overrides,
        "tester_inputs": tester_inputs,
        "cache_guard": {
            "tester_cache_purged_items": safe_int(cache_guard.get("tester_cache_purged_items")),
            "tester_set_purged_files": safe_int(cache_guard.get("tester_set_purged_files")),
            "common_files_purged_files": safe_int(cache_guard.get("common_files_purged_files")),
            "accepted_telemetry_run_ids": cache_guard.get("accepted_telemetry_run_ids") or [],
            "single_telemetry_token": bool(cache_guard.get("single_telemetry_token")),
            "ambient_runmeta_detected": bool(cache_guard.get("ambient_runmeta_detected")),
        },
    }


def summarize_cost(cost_report: dict[str, Any]) -> dict[str, Any]:
    if not cost_report:
        return {"available": False}
    scenarios = cost_report.get("scenarios") or []
    x1 = next((row for row in scenarios if row.get("scenario") == "cost_x1_00"), None)
    return {
        "available": True,
        "verdict": cost_report.get("verdict") or "",
        "stress_mode": cost_report.get("stress_mode") or "",
        "cost_x1_00_pf": safe_num((x1 or {}).get("profit_factor")),
        "cost_x1_00_net": safe_num((x1 or {}).get("net_profit")),
        "findings": cost_report.get("findings") or [],
    }


def diff_dict(left: dict[str, str], right: dict[str, str]) -> dict[str, Any]:
    keys = sorted(set(left) | set(right))
    changed = []
    only_left = []
    only_right = []
    for key in keys:
        if key not in right:
            only_left.append(key)
        elif key not in left:
            only_right.append(key)
        elif left[key] != right[key]:
            changed.append({"key": key, "left": left[key], "right": right[key]})
    return {
        "changed": changed,
        "only_left": only_left,
        "only_right": only_right,
        "changed_count": len(changed),
        "only_left_count": len(only_left),
        "only_right_count": len(only_right),
    }


def metric_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "n_trades",
        "net_profit",
        "profit_factor",
        "win_rate_pct",
        "expectancy_per_trade",
        "max_drawdown_pct",
        "active_months",
        "validation_gates_passed",
    ]
    return {key: round(safe_num(right["metrics"].get(key)) - safe_num(left["metrics"].get(key)), 6) for key in keys}


def pair_compare(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {
        "left": left["run_id"],
        "right": right["run_id"],
        "trade_identity_same": left["trade_identity"] == right["trade_identity"],
        "runtime_identity_same": left["runtime_identity"] == right["runtime_identity"],
        "identity_same": left["trade_identity"] == right["trade_identity"],
        "fingerprint_same": {
            "config_ini_sha256": left["fingerprints"]["config_ini_sha256"] == right["fingerprints"]["config_ini_sha256"],
            "overrides_sha256": left["fingerprints"]["overrides_sha256"] == right["fingerprints"]["overrides_sha256"],
            "report_sha256": left["fingerprints"]["report_sha256"] == right["fingerprints"]["report_sha256"],
        },
        "metrics_delta": metric_delta(left, right),
        "override_diff": diff_dict(left["overrides"], right["overrides"]),
        "tester_input_diff": diff_dict(left["tester_inputs"], right["tester_inputs"]),
        "interpretation": interpret_pair(left, right),
    }


def interpret_pair(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    delta = metric_delta(left, right)
    override_diff = diff_dict(left["overrides"], right["overrides"])
    changed_keys = {row["key"] for row in override_diff["changed"]}
    added_keys = set(override_diff["only_right"])

    if left["trade_identity"] != right["trade_identity"]:
        notes.append("trade identity differs; this is not a clean reproducibility comparison")
    elif left["runtime_identity"] != right["runtime_identity"]:
        notes.append("trade identity is stable; runtime-only metadata differs")
    if abs(delta["n_trades"]) >= 20 and override_diff["changed_count"] == 0 and override_diff["only_right_count"] <= 2:
        notes.append("large trade-count drift with near-identical overrides; suspect source/default semantic drift or tester data state")
    if "InpUseOpportunityScoreGate" in changed_keys:
        notes.append("opportunity score gate change explains a major cadence delta and must be isolated before strategy conclusions")
    if {"InpEnableTelemetry", "InpEnableOpportunityLogger", "InpEnableShadowNarrative"} & changed_keys:
        if abs(delta["n_trades"]) <= 1 and abs(delta["net_profit"]) <= 0.01:
            notes.append("telemetry/logger/shadow toggles did not change trade economics in this pair")
        else:
            notes.append("telemetry/logger/shadow pair changed economics; inspect side effects before reusing artifacts")
    if "InpOrderCalcRiskFailClosed" in added_keys and abs(delta["n_trades"]) >= 20:
        notes.append("new OrderCalcRiskFailClosed override is present, but a false value should not explain fewer signals by itself")
    if right["metrics"]["validation_verdict"].upper() != "PASS":
        notes.append(f"right validation remains {right['metrics']['validation_verdict']}; research-only")
    return notes


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    runs = [collect_run(run_dir_for(run, args.ea)) for run in args.runs]
    pairs = [pair_compare(runs[index], runs[index + 1]) for index in range(len(runs) - 1)]
    findings = build_findings(runs, pairs)
    return {
        "schema_version": "sonic_repro_drift_map.v1",
        "ea_name": args.ea,
        "runs": runs,
        "pairs": pairs,
        "findings": findings,
        "status": "REVIEW" if findings else "PASS",
        "note": "This tool maps reproducibility drift only. It does not promote any EA candidate.",
    }


def build_findings(runs: list[dict[str, Any]], pairs: list[dict[str, Any]]) -> list[str]:
    findings: list[str] = []
    by_id = {run["run_id"]: run for run in runs}
    first = runs[0]
    for run in runs:
        if run["trade_identity"] != first["trade_identity"]:
            findings.append(f"identity_mismatch:{first['run_id']}:{run['run_id']}")
        if run["metrics"]["validation_verdict"].upper() != "PASS":
            findings.append(f"validation_not_passed:{run['run_id']}:{run['metrics']['validation_verdict']}")

    if "20260501_000718" in by_id and "20260501_150443" in by_id:
        delta = metric_delta(by_id["20260501_000718"], by_id["20260501_150443"])
        if delta["n_trades"] <= -100:
            findings.append("baseline_repro_drift:20260501_000718_to_20260501_150443:trade_count_drop")

    if "20260501_150443" in by_id and "20260501_150910" in by_id:
        delta = metric_delta(by_id["20260501_150443"], by_id["20260501_150910"])
        if delta["n_trades"] >= 100:
            findings.append("score_gate_controls_cadence:20260501_150443_to_20260501_150910")

    if "20260501_150910" in by_id and "20260501_151422" in by_id:
        delta = metric_delta(by_id["20260501_150910"], by_id["20260501_151422"])
        if abs(delta["n_trades"]) <= 1 and abs(delta["net_profit"]) <= 0.01:
            findings.append("telemetry_no_economic_delta:20260501_150910_to_20260501_151422")

    for pair in pairs:
        for note in pair["interpretation"]:
            token = note.replace(" ", "_").replace(";", "").replace(",", "").lower()
            if token not in findings:
                findings.append(token)
    return findings


def write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Sonic R Repro Drift Map",
        "",
        f"- Status: `{result['status']}`",
        f"- EA: `{result['ea_name']}`",
        f"- Note: {result['note']}",
        "",
        "## Runs",
        "",
        "| run | trades | PF | net | DD% | validation | config sha | override count |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- | ---: |",
    ]
    for run in result["runs"]:
        metrics = run["metrics"]
        fp = run["fingerprints"]
        lines.append(
            "| {run} | {trades} | {pf:.4f} | {net:.2f} | {dd:.2f} | {val} | `{sha}` | {count} |".format(
                run=run["run_id"],
                trades=metrics["n_trades"],
                pf=metrics["profit_factor"],
                net=metrics["net_profit"],
                dd=metrics["max_drawdown_pct"],
                val=metrics["validation_verdict"],
                sha=str(fp["config_ini_sha256"])[:12],
                count=fp["override_count"],
            )
        )
    lines.extend(["", "## Pair Deltas", ""])
    for pair in result["pairs"]:
        delta = pair["metrics_delta"]
        lines.extend(
            [
                f"### `{pair['left']}` -> `{pair['right']}`",
                "",
                (
                    f"- Trades delta: `{delta['n_trades']}`; net delta: `{delta['net_profit']}`; "
                    f"PF delta: `{delta['profit_factor']}`"
                ),
                f"- Identity same: `{pair['identity_same']}`",
                f"- Override changes: `{pair['override_diff']['changed_count']}` changed, "
                f"`{pair['override_diff']['only_right_count']}` added, "
                f"`{pair['override_diff']['only_left_count']}` removed",
                "",
            ]
        )
        if pair["override_diff"]["changed"] or pair["override_diff"]["only_right"] or pair["override_diff"]["only_left"]:
            lines.append("Changed/added/removed inputs:")
            for row in pair["override_diff"]["changed"]:
                lines.append(f"- `{row['key']}`: `{row['left']}` -> `{row['right']}`")
            for key in pair["override_diff"]["only_right"]:
                lines.append(f"- added `{key}` = `{result_input_value(pair['right'], key, result)}`")
            for key in pair["override_diff"]["only_left"]:
                lines.append(f"- removed `{key}`")
            lines.append("")
        if pair["interpretation"]:
            lines.append("Interpretation:")
            for note in pair["interpretation"]:
                lines.append(f"- {note}")
            lines.append("")
    lines.extend(["## Findings", ""])
    for finding in result["findings"]:
        lines.append(f"- `{finding}`")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def result_input_value(run_id: str, key: str, result: dict[str, Any]) -> str:
    for run in result["runs"]:
        if run["run_id"] == run_id:
            return str(run["overrides"].get(key, ""))
    return ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", nargs="*", default=DEFAULT_RUNS, help="Run ids or directories in comparison order.")
    parser.add_argument("--ea", default=DEFAULT_EA, help=f"EA name under AlphaFactory runs (default: {DEFAULT_EA}).")
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument("--out-md", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_result(args)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(text + "\n", encoding="utf-8")
    if args.out_md:
        write_markdown(result, args.out_md)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
