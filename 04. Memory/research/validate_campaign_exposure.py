#!/usr/bin/env python3
"""Validate the append-only AlphaFactory campaign exposure ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import jsonschema


RESEARCH_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = RESEARCH_DIR.parents[1]
DEFAULT_LEDGER = RESEARCH_DIR / "CAMPAIGN_EXPOSURE.jsonl"
DEFAULT_SCHEMA = RESEARCH_DIR / "CAMPAIGN_EXPOSURE.schema.json"
SPLIT_RANK = {"SEALED": 0, "AUTHORIZED": 1, "OPENED": 2}
PHASE_RANK = {f"P{index}": index for index in range(13)}
MANDATORY_SYMBOLS = [
    "XAUUSD",
    "BTCUSD",
    "EURUSD",
    "USDJPY",
    "GBPUSD",
    "USDCHF",
    "USDCAD",
    "AUDUSD",
    "NZDUSD",
]
HYPOTHESIS_ONLY_FIELDS = {
    "acceptance_contract",
    "ea_name",
    "exact_overrides",
    "feature_family",
    "hypothesis_id",
    "lane",
    "metrics",
    "model",
    "parent_candidate",
    "prereg_path",
    "prereg_sha256",
    "run_ids",
    "source_hash",
    "source_path",
    "source_provenance",
    "symbol",
    "timeframe",
    "validation",
    "verdict",
    "window",
}


def reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def load_strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8-sig"),
        parse_constant=reject_nonfinite,
        object_pairs_hook=reject_duplicate_keys,
    )


def _workspace_artifact(
    raw_path: Any,
    raw_sha: Any,
    label: str,
    errors: list[str],
) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path or Path(raw_path).is_absolute():
        errors.append(f"{label}: path must be workspace-relative")
        return None
    path = (WORKSPACE_ROOT / raw_path).resolve()
    try:
        path.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError:
        errors.append(f"{label}: path escapes workspace")
        return None
    if not path.is_file():
        errors.append(f"{label}: file is missing: {path}")
        return None
    actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    if raw_sha != actual:
        errors.append(f"{label}: SHA256 mismatch expected={raw_sha} actual={actual}")
    return path


def _latest_registry_row(
    hypothesis_id: str,
    *,
    as_of: datetime | None = None,
) -> dict[str, Any] | None:
    registry = RESEARCH_DIR / "CANDIDATE_REGISTRY.jsonl"
    if not registry.is_file():
        return None
    latest: dict[str, Any] | None = None
    for raw in registry.read_text(encoding="utf-8-sig").splitlines():
        try:
            row = json.loads(
                raw,
                parse_constant=reject_nonfinite,
                object_pairs_hook=reject_duplicate_keys,
            )
        except Exception:
            continue
        if not (isinstance(row, dict) and row.get("hypothesis_id") == hypothesis_id):
            continue
        if as_of is not None:
            try:
                row_time = datetime.fromisoformat(
                    str(row["updated_at_utc"]).replace("Z", "+00:00")
                )
            except (KeyError, ValueError):
                continue
            if row_time > as_of:
                continue
        latest = row
    return latest


def _execution_receipts_before(
    hypothesis_id: str,
    cutoff: datetime,
) -> list[tuple[Path, dict[str, Any], datetime]]:
    runtime = WORKSPACE_ROOT / "02. AlphaFactory/runtime"
    matches: list[tuple[Path, dict[str, Any], datetime]] = []
    if not runtime.is_dir():
        return matches
    for path in sorted(runtime.glob("ea_execution_receipt_*.json")):
        try:
            receipt = load_strict_json(path)
            generated = datetime.fromisoformat(
                str(receipt["generated_at_utc"]).replace("Z", "+00:00")
            )
        except Exception:
            continue
        if (
            isinstance(receipt, dict)
            and receipt.get("hypothesis_id") == hypothesis_id
            and generated <= cutoff
        ):
            matches.append((path, receipt, generated))
    return matches


def _validate_data_repair(
    row: dict[str, Any],
    prior_row: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    repair = row.get("data_repair")
    bound = row.get("bound_data")
    prior_bound = prior_row.get("bound_data")
    if not isinstance(repair, dict) or not isinstance(bound, dict) or not isinstance(prior_bound, dict):
        return
    if row.get("schema_version") != "alphafactory_campaign_exposure.v2":
        errors.append(f"{label}: DATA_REPAIR requires schema v2")
    if row.get("state") != "ACTIVE" or row.get("phase") != "P4":
        errors.append(f"{label}: DATA_REPAIR requires ACTIVE/P4")
    if row.get("active_hypothesis_id") is not None:
        errors.append(f"{label}: DATA_REPAIR requires null active_hypothesis_id")
    for field in ("campaign_id", "generation", "charter", "budget", "viewed_arms", "split"):
        if row.get(field) != prior_row.get(field):
            errors.append(f"{label}: DATA_REPAIR cannot change {field}")
    for current, name in ((prior_row, "prior"), (row, "current")):
        budget = current.get("budget")
        split = current.get("split")
        if not (
            isinstance(budget, dict)
            and budget.get("trial_spent") == 0
            and budget.get("alpha_ppm_spent") == 0
            and current.get("viewed_arms") == []
            and isinstance(split, dict)
            and split.get("state") == "SEALED"
            and split.get("opened_count") == 0
        ):
            errors.append(f"{label}: DATA_REPAIR {name} exposure must remain zero and split SEALED/0")
    if prior_bound.get("status") != "BOUND" or bound.get("status") != "BOUND":
        errors.append(f"{label}: DATA_REPAIR requires BOUND->BOUND")
    for field in ("multiplicity", "reopen_condition"):
        if bound.get(field) != prior_bound.get(field):
            errors.append(f"{label}: DATA_REPAIR cannot change bound_data.{field}")
    changed = [
        field
        for field in ("epoch", "manifest_path", "manifest_sha256")
        if bound.get(field) != prior_bound.get(field)
    ]
    if changed != ["epoch", "manifest_path", "manifest_sha256"]:
        errors.append(
            f"{label}: DATA_REPAIR must replace epoch, manifest_path and manifest_sha256 together"
        )
    predecessor = repair.get("predecessor_bound_data")
    expected_predecessor = {
        "epoch": prior_bound.get("epoch"),
        "manifest_path": prior_bound.get("manifest_path"),
        "manifest_sha256": prior_bound.get("manifest_sha256"),
    }
    if predecessor != expected_predecessor:
        errors.append(f"{label}: data_repair.predecessor_bound_data must equal prior binding")
    for field, expected in {
        "classification": "INVALID_REPAIR_ZERO_ECONOMICS",
        "economic_trials_consumed": 0,
        "data_acquisition_authorized": True,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
    }.items():
        if repair.get(field) != expected:
            errors.append(f"{label}: data_repair.{field} must equal {expected}")

    closeout_ref = repair.get("predecessor_closeout")
    if isinstance(closeout_ref, dict):
        closeout_path = _workspace_artifact(
            closeout_ref.get("path"),
            closeout_ref.get("sha256"),
            f"{label}: predecessor_closeout",
            errors,
        )
        if closeout_path is not None:
            try:
                closeout = load_strict_json(closeout_path)
            except Exception as exc:
                errors.append(f"{label}: predecessor closeout invalid JSON: {exc}")
                closeout = None
            if isinstance(closeout, dict):
                symbols = closeout.get("symbols")
                expected_runs = len(symbols) if isinstance(symbols, list) else None
                for field, expected in {
                    "status": "PARKED_DATA_QUALITY_CONTRACT_FAIL",
                    "selected_pass_count": repair.get("prior_selected_pass_count"),
                    "required_pass_count": len(MANDATORY_SYMBOLS),
                    "economic_trials_consumed": 0,
                    "trades_authorized": False,
                    "performance_metrics_authorized": False,
                    "economics_authorized": False,
                    "market_edge_claim_authorized": False,
                }.items():
                    if closeout.get(field) != expected:
                        errors.append(f"{label}: predecessor closeout {field} mismatch")
                if expected_runs != repair.get("prior_diagnostic_runs"):
                    errors.append(f"{label}: prior_diagnostic_runs must equal closeout symbol runs")
                if not isinstance(symbols, list) or [item.get("symbol") for item in symbols if isinstance(item, dict)] != MANDATORY_SYMBOLS:
                    errors.append(f"{label}: predecessor closeout must cover exact mandatory symbols")

    prereg_ref = repair.get("replacement_prereg")
    if isinstance(prereg_ref, dict):
        prereg_path = _workspace_artifact(
            prereg_ref.get("path"),
            prereg_ref.get("sha256"),
            f"{label}: replacement_prereg",
            errors,
        )
        hypothesis_id = prereg_ref.get("hypothesis_id")
        if prereg_path is not None:
            text = prereg_path.read_text(encoding="utf-8-sig")
            required_tokens = [
                str(hypothesis_id),
                "Tester model: integer `4`",
                "DATA_ACQUISITION_ONLY_NO_PERFORMANCE",
                "no trading",
            ]
            for token in required_tokens:
                if token not in text:
                    errors.append(f"{label}: replacement prereg lacks frozen token {token!r}")
        if isinstance(hypothesis_id, str):
            try:
                repair_time = datetime.fromisoformat(
                    str(row["updated_at_utc"]).replace("Z", "+00:00")
                )
            except (KeyError, ValueError):
                repair_time = None
            registry_row = _latest_registry_row(hypothesis_id, as_of=repair_time)
            if registry_row is None:
                errors.append(f"{label}: replacement hypothesis is absent from registry")
            else:
                validation = registry_row.get("validation")
                if (
                    registry_row.get("state") != "screened"
                    or registry_row.get("model") != 4
                    or registry_row.get("run_ids") != []
                    or registry_row.get("prereg_sha256") != prereg_ref.get("sha256")
                    or not isinstance(validation, dict)
                    or validation.get("performance_metrics_authorized") is not False
                    or validation.get("economics_authorized") is not False
                    or validation.get("model4_data_acquisition_authorized") is not True
                    or validation.get("model4_performance_authorized") is not False
                ):
                    errors.append(f"{label}: replacement registry row is not screened data-only Model4")

    manifest_path = _workspace_artifact(
        bound.get("manifest_path"),
        bound.get("manifest_sha256"),
        f"{label}: replacement bound_data",
        errors,
    )
    if manifest_path is not None:
        try:
            manifest = load_strict_json(manifest_path)
        except Exception as exc:
            errors.append(f"{label}: replacement manifest invalid JSON: {exc}")
            manifest = None
        if isinstance(manifest, dict):
            expected_manifest = {
                "campaign_id": row.get("campaign_id"),
                "generation": row.get("generation"),
                "generation_id": f"T{row.get('generation')}",
                "charter": row.get("charter"),
                "timeframe": "M5",
                "tester_model": 4,
                "requested_from": "1970.01.01",
                "history_quality": {"operator": "gt", "threshold_pct": 97.0},
                "no_skip": True,
                "mandatory_symbols": MANDATORY_SYMBOLS,
            }
            for field, expected in expected_manifest.items():
                if manifest.get(field) != expected:
                    errors.append(f"{label}: replacement manifest {field} mismatch")


def _validate_governance_correction(
    row: dict[str, Any],
    prior_row: dict[str, Any],
    prior_line: int,
    prior_sha256: str,
    label: str,
    errors: list[str],
) -> None:
    correction = row.get("governance_correction")
    bound = row.get("bound_data")
    prior_bound = prior_row.get("bound_data")
    prior_repair = prior_row.get("data_repair")
    if not all(
        isinstance(value, dict)
        for value in (correction, bound, prior_bound, prior_repair)
    ):
        return
    if row.get("schema_version") != "alphafactory_campaign_exposure.v3":
        errors.append(f"{label}: GOVERNANCE_CORRECTION requires schema v3")
    if row.get("state") != "ACTIVE" or row.get("phase") != "P4":
        errors.append(f"{label}: GOVERNANCE_CORRECTION requires ACTIVE/P4")
    if row.get("active_hypothesis_id") is not None:
        errors.append(f"{label}: GOVERNANCE_CORRECTION requires null active_hypothesis_id")
    if prior_row.get("event") != "DATA_REPAIR":
        errors.append(f"{label}: GOVERNANCE_CORRECTION must immediately follow DATA_REPAIR")
    for field in ("campaign_id", "generation", "charter", "budget", "viewed_arms", "split"):
        if row.get(field) != prior_row.get(field):
            errors.append(f"{label}: GOVERNANCE_CORRECTION cannot change {field}")
    budget = row.get("budget")
    split = row.get("split")
    if not (
        isinstance(budget, dict)
        and budget.get("trial_spent") == 0
        and budget.get("alpha_ppm_spent") == 0
        and row.get("viewed_arms") == []
        and isinstance(split, dict)
        and split.get("state") == "SEALED"
        and split.get("opened_count") == 0
    ):
        errors.append(
            f"{label}: GOVERNANCE_CORRECTION must preserve zero exposure and split SEALED/0"
        )

    invalid_event = correction.get("invalid_event")
    replacement = prior_repair.get("replacement_prereg")
    hypothesis_id = (
        replacement.get("hypothesis_id") if isinstance(replacement, dict) else None
    )
    expected_invalid_event = {
        "line": prior_line,
        "raw_sha256": prior_sha256,
        "event": "DATA_REPAIR",
        "hypothesis_id": hypothesis_id,
        "updated_at_utc": prior_row.get("updated_at_utc"),
    }
    if invalid_event != expected_invalid_event:
        errors.append(
            f"{label}: governance_correction.invalid_event must identify the exact prior DATA_REPAIR row"
        )

    predecessor = prior_repair.get("predecessor_bound_data")
    expected_bound = (
        {
            "status": "BOUND",
            "epoch": predecessor.get("epoch"),
            "manifest_path": predecessor.get("manifest_path"),
            "manifest_sha256": predecessor.get("manifest_sha256"),
            "multiplicity": prior_bound.get("multiplicity"),
            "reopen_condition": prior_bound.get("reopen_condition"),
        }
        if isinstance(predecessor, dict)
        else None
    )
    if bound != expected_bound:
        errors.append(
            f"{label}: GOVERNANCE_CORRECTION must restore the pre-DATA_REPAIR bound_data exactly"
        )

    receipt_ref = correction.get("execution_receipt")
    receipt: dict[str, Any] | None = None
    if isinstance(receipt_ref, dict):
        receipt_path = _workspace_artifact(
            receipt_ref.get("path"),
            receipt_ref.get("sha256"),
            f"{label}: execution_receipt",
            errors,
        )
        if receipt_path is not None:
            try:
                loaded = load_strict_json(receipt_path)
                receipt = loaded if isinstance(loaded, dict) else None
            except Exception as exc:
                errors.append(f"{label}: execution receipt invalid JSON: {exc}")
    if receipt is not None:
        try:
            receipt_time = datetime.fromisoformat(
                str(receipt["generated_at_utc"]).replace("Z", "+00:00")
            )
            invalid_time = datetime.fromisoformat(
                str(prior_row["updated_at_utc"]).replace("Z", "+00:00")
            )
        except (KeyError, ValueError):
            errors.append(f"{label}: execution receipt has invalid generated_at_utc")
        else:
            if receipt_time >= invalid_time:
                errors.append(
                    f"{label}: execution receipt must predate the invalid DATA_REPAIR row"
                )
        binding = receipt.get("binding")
        if (
            receipt.get("hypothesis_id") != hypothesis_id
            or receipt.get("authority") != "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
            or not isinstance(binding, dict)
            or binding.get("hypothesis_id") != hypothesis_id
            or binding.get("model") != 4
            or binding.get("symbol") != "XAUUSD"
            or binding.get("period") != "M5"
        ):
            errors.append(
                f"{label}: execution receipt must prove the exact HYP004 XAUUSD/M5 Model4 launch"
            )

    failed_ref = correction.get("failed_loop")
    failed: dict[str, Any] | None = None
    if isinstance(failed_ref, dict):
        failed_path = _workspace_artifact(
            failed_ref.get("path"),
            failed_ref.get("sha256"),
            f"{label}: failed_loop",
            errors,
        )
        if failed_path is not None:
            try:
                loaded = load_strict_json(failed_path)
                failed = loaded if isinstance(loaded, dict) else None
            except Exception as exc:
                errors.append(f"{label}: failed-loop snapshot invalid JSON: {exc}")
    if failed is not None:
        if (
            failed.get("hypothesis_id") != hypothesis_id
            or "D0 series proof" not in str(failed.get("error"))
            or not isinstance(failed.get("state_transitions"), list)
        ):
            errors.append(
                f"{label}: failed-loop snapshot must prove the exact D0 series-proof failure"
            )

    closeout_ref = correction.get("terminal_closeout")
    closeout: dict[str, Any] | None = None
    if isinstance(closeout_ref, dict):
        closeout_path = _workspace_artifact(
            closeout_ref.get("path"),
            closeout_ref.get("sha256"),
            f"{label}: terminal_closeout",
            errors,
        )
        if closeout_path is not None:
            try:
                loaded = load_strict_json(closeout_path)
                closeout = loaded if isinstance(loaded, dict) else None
            except Exception as exc:
                errors.append(f"{label}: terminal closeout invalid JSON: {exc}")
    if closeout is not None:
        expected_closeout = {
            "hypothesis_id": hypothesis_id,
            "status": "INVALID_GOVERNANCE_PRE_BIND_MT5_LAUNCH",
            "mt5_launches": 1,
            "trades_executed": 0,
            "economic_trials_consumed": 0,
            "performance_metrics_authorized": False,
            "economics_authorized": False,
            "market_edge_claim_authorized": False,
        }
        for field, expected in expected_closeout.items():
            if closeout.get(field) != expected:
                errors.append(f"{label}: terminal closeout {field} mismatch")
        artifacts = closeout.get("artifacts")
        if not isinstance(artifacts, dict):
            errors.append(f"{label}: terminal closeout artifacts must be an object")
        else:
            for field, expected in (
                ("execution_receipt", receipt_ref),
                ("failed_loop", failed_ref),
            ):
                if artifacts.get(field) != expected:
                    errors.append(
                        f"{label}: terminal closeout artifacts.{field} mismatch"
                    )

    for field, expected in {
        "classification": "POST_OUTCOME_BINDING_INVALIDATED_ZERO_ECONOMICS",
        "mt5_launches": 1,
        "symbols_started": ["XAUUSD"],
        "trades_executed": 0,
        "economic_trials_consumed": 0,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
        "fresh_hypothesis_required": True,
    }.items():
        if correction.get(field) != expected:
            errors.append(f"{label}: governance_correction.{field} must equal {expected}")


def _validate_data_repair_chronology(
    rows: list[tuple[int, dict[str, Any], datetime, str]],
    errors: list[str],
) -> None:
    next_by_campaign: dict[int, tuple[int, dict[str, Any], datetime, str] | None] = {}
    latest_index: dict[str, int] = {}
    for index in range(len(rows) - 1, -1, -1):
        campaign_id = str(rows[index][1].get("campaign_id"))
        next_index = latest_index.get(campaign_id)
        next_by_campaign[index] = rows[next_index] if next_index is not None else None
        latest_index[campaign_id] = index

    for index, (line, row, timestamp, raw_sha256) in enumerate(rows):
        if row.get("event") != "DATA_REPAIR":
            continue
        repair = row.get("data_repair")
        prereg = repair.get("replacement_prereg") if isinstance(repair, dict) else None
        hypothesis_id = prereg.get("hypothesis_id") if isinstance(prereg, dict) else None
        if not isinstance(hypothesis_id, str):
            continue
        prior_receipts = _execution_receipts_before(hypothesis_id, timestamp)
        if not prior_receipts:
            continue
        successor = next_by_campaign[index]
        corrected = False
        if successor is not None:
            successor_row = successor[1]
            correction = successor_row.get("governance_correction")
            invalid_event = (
                correction.get("invalid_event") if isinstance(correction, dict) else None
            )
            corrected = (
                successor_row.get("event") == "GOVERNANCE_CORRECTION"
                and isinstance(invalid_event, dict)
                and invalid_event.get("line") == line
                and invalid_event.get("raw_sha256") == raw_sha256
                and invalid_event.get("hypothesis_id") == hypothesis_id
            )
        if not corrected:
            receipts = ", ".join(path.name for path, _, _ in prior_receipts)
            errors.append(
                f"line {line} {row.get('campaign_id')} campaign exposure: "
                f"DATA_REPAIR is post-launch for {hypothesis_id}; pre-existing receipts={receipts}; "
                "an immediate hash-bound GOVERNANCE_CORRECTION is required"
            )


def _validate_budget(row: dict[str, Any], label: str, errors: list[str]) -> None:
    budget = row.get("budget")
    if not isinstance(budget, dict):
        return
    if (
        isinstance(budget.get("trial_total"), int)
        and isinstance(budget.get("trial_spent"), int)
        and isinstance(budget.get("trial_remaining"), int)
        and budget["trial_spent"] + budget["trial_remaining"] != budget["trial_total"]
    ):
        errors.append(f"{label}: trial budget spent+remaining must equal total")
    if (
        isinstance(budget.get("alpha_ppm_total"), int)
        and isinstance(budget.get("alpha_ppm_spent"), int)
        and isinstance(budget.get("alpha_ppm_remaining"), int)
        and budget["alpha_ppm_spent"] + budget["alpha_ppm_remaining"] != budget["alpha_ppm_total"]
    ):
        errors.append(f"{label}: alpha_ppm budget spent+remaining must equal total")


def _validate_split(row: dict[str, Any], label: str, errors: list[str]) -> None:
    split = row.get("split")
    if not isinstance(split, dict):
        return
    split_state = split.get("state")
    opened_count = split.get("opened_count")
    if split_state in {"SEALED", "AUTHORIZED"} and opened_count != 0:
        errors.append(f"{label}: {split_state} split requires opened_count=0")
    if split_state == "OPENED" and isinstance(opened_count, int) and opened_count < 1:
        errors.append(f"{label}: OPENED split requires opened_count>=1")


def _validate_first_row(row: dict[str, Any], label: str, errors: list[str]) -> None:
    if row.get("generation") != 1:
        errors.append(f"{label}: first row generation must be 1")
    if row.get("state") != "ACTIVE":
        errors.append(f"{label}: first row must start ACTIVE")
    if row.get("event") != "OPEN":
        errors.append(f"{label}: first row must use OPEN event")
    if row.get("phase") != "P0":
        errors.append(f"{label}: first row must start at P0")
    if row.get("active_hypothesis_id") is not None:
        errors.append(f"{label}: first row active_hypothesis_id must be null")
    if row.get("viewed_arms") != []:
        errors.append(f"{label}: first row viewed_arms must be []")
    split = row.get("split")
    if not (
        isinstance(split, dict)
        and split.get("state") == "SEALED"
        and split.get("opened_count") == 0
    ):
        errors.append(f"{label}: first row split must be SEALED/0")
    bound = row.get("bound_data")
    if not (
        isinstance(bound, dict)
        and bound.get("status") == "UNBOUND"
        and bound.get("epoch") is None
        and bound.get("manifest_path") is None
        and bound.get("manifest_sha256") is None
    ):
        errors.append(f"{label}: first row bound_data must be UNBOUND with null epoch/manifest")
    budget = row.get("budget")
    if isinstance(budget, dict):
        if budget.get("trial_spent") != 0:
            errors.append(f"{label}: first row trial_spent must be 0")
        if budget.get("alpha_ppm_spent") != 0:
            errors.append(f"{label}: first row alpha_ppm_spent must be 0")
        if budget.get("trial_remaining") != budget.get("trial_total"):
            errors.append(f"{label}: first row trial_remaining must equal trial_total")
        if budget.get("alpha_ppm_remaining") != budget.get("alpha_ppm_total"):
            errors.append(f"{label}: first row alpha_ppm_remaining must equal alpha_ppm_total")


def _validate_transition(
    row: dict[str, Any],
    line: int,
    prior: tuple[int, dict[str, Any], datetime, str] | None,
    active_campaign: list[tuple[int, str, int] | None],
    errors: list[str],
) -> None:
    campaign_id = str(row.get("campaign_id") or "<unknown>")
    label = f"line {line} {campaign_id} campaign exposure"
    leaked = sorted(HYPOTHESIS_ONLY_FIELDS & set(row))
    if leaked:
        errors.append(f"{label}: campaign row contains hypothesis-only fields {leaked}")
    try:
        timestamp = datetime.fromisoformat(str(row["updated_at_utc"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return
    if row.get("updated_at_utc") and not str(row["updated_at_utc"]).endswith("Z"):
        errors.append(f"{label}: updated_at_utc must use a Z timestamp")

    _validate_budget(row, label, errors)
    _validate_split(row, label, errors)
    budget = row.get("budget")
    viewed = row.get("viewed_arms")
    if isinstance(budget, dict) and isinstance(viewed, list) and budget.get("trial_spent") != len(viewed):
        errors.append(f"{label}: trial_spent must equal len(viewed_arms)")
    if row.get("state") == "CLOSED":
        if row.get("event") != "GENERATION_CLOSE":
            errors.append(f"{label}: CLOSED row must use GENERATION_CLOSE event")
        if row.get("phase") != "P12":
            errors.append(f"{label}: CLOSED row must be phase P12")
    elif row.get("event") == "GENERATION_CLOSE" or row.get("phase") == "P12":
        errors.append(f"{label}: GENERATION_CLOSE/P12 requires CLOSED state")

    generation = row.get("generation")
    if row.get("state") == "ACTIVE" and isinstance(generation, int):
        active = active_campaign[0]
        if active is not None and (active[1], active[2]) != (campaign_id, generation):
            errors.append(f"{label}: one active campaign/generation already exists at line {active[0]}")
        active_campaign[0] = (line, campaign_id, generation)
    elif row.get("state") == "CLOSED" and isinstance(generation, int):
        active = active_campaign[0]
        if active is not None and (active[1], active[2]) == (campaign_id, generation):
            active_campaign[0] = None

    if prior is None:
        if row.get("prior_campaign_row_sha256") is not None:
            errors.append(f"{label}: first campaign row prior_campaign_row_sha256 must be null")
        _validate_first_row(row, label, errors)
        return

    prior_line, prior_row, prior_timestamp, prior_sha256 = prior
    if row.get("event") == "OPEN":
        errors.append(f"{label}: OPEN event is allowed only on the first row")
    if row.get("prior_campaign_row_sha256") != prior_sha256:
        errors.append(f"{label}: prior_campaign_row_sha256 must equal raw SHA256 of line {prior_line}")
    if timestamp <= prior_timestamp:
        errors.append(f"{label}: timestamp must increase")

    prior_generation = prior_row.get("generation")
    same_generation = generation == prior_generation
    if isinstance(prior_generation, int) and isinstance(generation, int):
        if generation < prior_generation:
            errors.append(f"{label}: generation cannot decrease from line {prior_line}")
        if generation > prior_generation:
            if generation != prior_generation + 1:
                errors.append(f"{label}: generation can only advance by one from line {prior_line}")
            if prior_row.get("state") != "CLOSED":
                errors.append(f"{label}: prior generation must be CLOSED before reopen")
            if row.get("state") != "ACTIVE":
                errors.append(f"{label}: reopened generation must start ACTIVE")
            if row.get("event") != "EPOCH_REOPEN":
                errors.append(f"{label}: reopened generation must use EPOCH_REOPEN event")
            if row.get("viewed_arms") != []:
                errors.append(f"{label}: reopened generation must reset viewed_arms to []")
            split = row.get("split")
            if not (
                isinstance(split, dict)
                and split.get("state") == "SEALED"
                and split.get("opened_count") == 0
            ):
                errors.append(f"{label}: reopened generation must reset split to SEALED/0")
            if row.get("active_hypothesis_id") is not None:
                errors.append(f"{label}: reopened generation must reset active_hypothesis_id to null")
            if row.get("phase") != "P0":
                errors.append(f"{label}: reopened generation must reset phase to P0")
            bound = row.get("bound_data")
            if not (
                isinstance(bound, dict)
                and bound.get("status") == "UNBOUND"
                and bound.get("epoch") is None
                and bound.get("manifest_path") is None
                and bound.get("manifest_sha256") is None
            ):
                errors.append(f"{label}: reopened generation must reset bound_data to UNBOUND/null")
            budget = row.get("budget")
            if isinstance(budget, dict):
                if budget.get("trial_spent") != 0 or budget.get("trial_remaining") != budget.get("trial_total"):
                    errors.append(f"{label}: reopened generation must reset trial budget")
                if (
                    budget.get("alpha_ppm_spent") != 0
                    or budget.get("alpha_ppm_remaining") != budget.get("alpha_ppm_total")
                ):
                    errors.append(f"{label}: reopened generation must reset alpha_ppm budget")
        elif prior_row.get("state") == "CLOSED" and row.get("state") == "ACTIVE":
            errors.append(f"{label}: CLOSED generation cannot resurrect as ACTIVE")
        elif prior_row.get("state") == "CLOSED":
            errors.append(f"{label}: no rows may follow CLOSED in the same generation")
    if row.get("event") == "EPOCH_REOPEN" and same_generation:
        errors.append(f"{label}: EPOCH_REOPEN is allowed only on generation+1")
    if same_generation:
        prior_phase = PHASE_RANK.get(str(prior_row.get("phase")))
        phase = PHASE_RANK.get(str(row.get("phase")))
        if prior_phase is not None and phase is not None and phase < prior_phase:
            errors.append(f"{label}: phase cannot move backward within generation")

    prior_budget = prior_row.get("budget")
    if isinstance(budget, dict) and isinstance(prior_budget, dict):
        for field in ("trial_total", "alpha_ppm_total"):
            if same_generation and budget.get(field) != prior_budget.get(field):
                errors.append(f"{label}: budget {field} changed within generation")
        for field in ("trial_spent", "alpha_ppm_spent"):
            if (
                same_generation
                and isinstance(budget.get(field), int)
                and isinstance(prior_budget.get(field), int)
                and budget[field] < prior_budget[field]
            ):
                errors.append(f"{label}: budget {field} cannot decrease within generation")
        for field in ("trial_remaining", "alpha_ppm_remaining"):
            if (
                same_generation
                and isinstance(budget.get(field), int)
                and isinstance(prior_budget.get(field), int)
                and budget[field] > prior_budget[field]
            ):
                errors.append(f"{label}: budget {field} cannot increase within generation")
        prior_debt = prior_budget.get("carry_debt_ppm")
        debt = budget.get("carry_debt_ppm")
        if isinstance(prior_debt, int) and isinstance(debt, int) and debt < prior_debt:
            errors.append(f"{label}: budget carry_debt_ppm cannot decrease from line {prior_line}")
        if not same_generation and isinstance(prior_debt, int) and debt != prior_debt:
            errors.append(f"{label}: reopened generation must carry carry_debt_ppm exactly")

    prior_viewed = prior_row.get("viewed_arms")
    if same_generation and isinstance(viewed, list) and isinstance(prior_viewed, list):
        if viewed[: len(prior_viewed)] != prior_viewed:
            errors.append(f"{label}: viewed_arms must be append-only from line {prior_line}")

    split = row.get("split")
    prior_split = prior_row.get("split")
    if same_generation and isinstance(split, dict) and isinstance(prior_split, dict):
        prior_split_state = str(prior_split.get("state"))
        split_state = str(split.get("state"))
        if SPLIT_RANK.get(str(split.get("state")), -1) < SPLIT_RANK.get(str(prior_split.get("state")), -1):
            errors.append(f"{label}: split state cannot move backward from line {prior_line}")
        if prior_split_state == "SEALED" and split_state == "AUTHORIZED" and row.get("event") != "AUTHORIZE_ATTEMPT":
            errors.append(f"{label}: SEALED->AUTHORIZED split requires AUTHORIZE_ATTEMPT")
        if prior_split_state in {"SEALED", "AUTHORIZED"} and split_state == "OPENED" and row.get("event") != "ATTEMPT_TERMINAL":
            errors.append(f"{label}: split OPENED requires ATTEMPT_TERMINAL")
        if (
            isinstance(split.get("opened_count"), int)
            and isinstance(prior_split.get("opened_count"), int)
            and split["opened_count"] < prior_split["opened_count"]
        ):
            errors.append(f"{label}: split opened_count cannot decrease from line {prior_line}")

    bound = row.get("bound_data")
    prior_bound = prior_row.get("bound_data")
    if same_generation and isinstance(bound, dict) and isinstance(prior_bound, dict):
        for field in ("multiplicity", "reopen_condition"):
            if bound.get(field) != prior_bound.get(field):
                errors.append(f"{label}: bound_data.{field} changed within generation")
        if prior_bound.get("status") == "UNBOUND" and bound.get("status") == "BOUND":
            if row.get("event") != "DATA_BIND":
                errors.append(f"{label}: DATA_BIND is required for UNBOUND->BOUND")
            if row.get("phase") != "P4":
                errors.append(f"{label}: DATA_BIND must occur at P4")
        elif row.get("event") == "DATA_BIND":
            errors.append(f"{label}: DATA_BIND is allowed only for UNBOUND->BOUND")
        if prior_bound.get("status") == "BOUND":
            if row.get("event") == "DATA_REPAIR":
                _validate_data_repair(row, prior_row, label, errors)
            elif row.get("event") == "GOVERNANCE_CORRECTION":
                _validate_governance_correction(
                    row,
                    prior_row,
                    prior_line,
                    prior_sha256,
                    label,
                    errors,
                )
            else:
                for field in ("status", "epoch", "manifest_path", "manifest_sha256", "multiplicity", "reopen_condition"):
                    if bound.get(field) != prior_bound.get(field):
                        errors.append(f"{label}: bound_data.{field} changed after BOUND from line {prior_line}")
        elif row.get("event") == "DATA_REPAIR":
            errors.append(f"{label}: DATA_REPAIR is allowed only for BOUND->BOUND")
        elif row.get("event") == "GOVERNANCE_CORRECTION":
            errors.append(
                f"{label}: GOVERNANCE_CORRECTION is allowed only after a BOUND DATA_REPAIR"
            )

    prior_active_hypothesis = prior_row.get("active_hypothesis_id")
    active_hypothesis = row.get("active_hypothesis_id")
    if same_generation:
        if prior_active_hypothesis is not None and active_hypothesis != prior_active_hypothesis:
            errors.append(f"{label}: active_hypothesis_id cannot change after binding")
        if prior_active_hypothesis is None and active_hypothesis is not None:
            if row.get("event") != "BIND_HYPOTHESIS":
                errors.append(f"{label}: BIND_HYPOTHESIS is required for null->ID")
            if row.get("phase") != "P5":
                errors.append(f"{label}: BIND_HYPOTHESIS must occur at P5")
            if not isinstance(bound, dict) or bound.get("status") != "BOUND":
                errors.append(f"{label}: BIND_HYPOTHESIS requires bound data")
        elif row.get("event") == "BIND_HYPOTHESIS":
            errors.append(f"{label}: BIND_HYPOTHESIS is allowed only for null->ID")

    if row.get("event") == "AUTHORIZE_ATTEMPT":
        split = row.get("split")
        if not isinstance(bound, dict) or bound.get("status") != "BOUND":
            errors.append(f"{label}: AUTHORIZE_ATTEMPT requires bound data")
        if active_hypothesis is None:
            errors.append(f"{label}: AUTHORIZE_ATTEMPT requires active_hypothesis_id")
        if not isinstance(split, dict) or split.get("state") != "AUTHORIZED":
            errors.append(f"{label}: AUTHORIZE_ATTEMPT requires split AUTHORIZED")
    if row.get("event") == "ATTEMPT_TERMINAL":
        split = row.get("split")
        if not isinstance(bound, dict) or bound.get("status") != "BOUND":
            errors.append(f"{label}: ATTEMPT_TERMINAL requires bound data")
        if active_hypothesis is None:
            errors.append(f"{label}: ATTEMPT_TERMINAL requires active_hypothesis_id")
        if not isinstance(split, dict) or split.get("state") != "OPENED":
            errors.append(f"{label}: ATTEMPT_TERMINAL requires split OPENED")

    if same_generation and row.get("charter") != prior_row.get("charter"):
        errors.append(f"{label}: charter cannot change within generation")


def _validate_bound_manifest(row: dict[str, Any], label: str, errors: list[str]) -> None:
    bound = row.get("bound_data")
    if not isinstance(bound, dict) or bound.get("status") != "BOUND":
        return
    raw_path = bound.get("manifest_path")
    if not isinstance(raw_path, str) or not raw_path or Path(raw_path).is_absolute():
        errors.append(f"{label}: bound_data.manifest_path must be a workspace-relative path")
        return
    candidate = (WORKSPACE_ROOT / raw_path).resolve()
    try:
        candidate.relative_to(WORKSPACE_ROOT.resolve())
    except ValueError:
        errors.append(f"{label}: bound_data.manifest_path escapes the workspace")
        return
    if not candidate.is_file():
        errors.append(f"{label}: bound_data manifest is missing: {candidate}")
        return
    actual_sha = hashlib.sha256(candidate.read_bytes()).hexdigest().upper()
    if actual_sha != bound.get("manifest_sha256"):
        errors.append(
            f"{label}: bound_data.manifest_sha256 mismatch expected "
            f"{bound.get('manifest_sha256')} actual {actual_sha}"
        )


def validate_ledger(ledger: Path, schema_path: Path, *, verify_bound_artifacts: bool = True) -> list[str]:
    errors: list[str] = []
    if not ledger.is_file():
        return [f"campaign exposure ledger is missing: {ledger}"]
    if not schema_path.is_file():
        return [f"schema is missing: {schema_path}"]
    try:
        schema = load_strict_json(schema_path)
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema, format_checker=jsonschema.FormatChecker()
        )
    except Exception as exc:
        return [f"schema is invalid: {exc}"]

    rows = 0
    parsed_rows: list[tuple[int, dict[str, Any], datetime, str]] = []
    latest_by_campaign: dict[str, tuple[int, dict[str, Any], datetime, str]] = {}
    active_campaign: list[tuple[int, str, int] | None] = [None]
    records = ledger.read_bytes().splitlines(keepends=True)
    for line_number, record in enumerate(records, 1):
        if not record.endswith(b"\n") or record.count(b"\n") != 1:
            errors.append(f"line {line_number}: ledger rows require exactly one terminal LF")
            continue
        body = record[:-1]
        try:
            raw = body.decode("utf-8-sig" if line_number == 1 else "utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            errors.append(f"line {line_number}: invalid UTF-8: {exc}")
            continue
        if not raw.strip():
            errors.append(f"line {line_number}: blank rows are forbidden")
            continue
        rows += 1
        try:
            row = json.loads(
                raw,
                parse_constant=reject_nonfinite,
                object_pairs_hook=reject_duplicate_keys,
            )
        except Exception as exc:
            errors.append(f"line {line_number}: invalid strict JSON: {exc}")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {line_number}: row root must be an object")
            continue
        issues = sorted(validator.iter_errors(row), key=lambda item: str(list(item.path)))
        for issue in issues:
            location = ".".join(str(part) for part in issue.path) or "<root>"
            errors.append(f"line {line_number} {location}: {issue.message}")
        if issues:
            continue
        campaign_id = str(row["campaign_id"])
        _validate_transition(
            row,
            line_number,
            latest_by_campaign.get(campaign_id),
            active_campaign,
            errors,
        )
        if verify_bound_artifacts:
            _validate_bound_manifest(
                row,
                f"line {line_number} {campaign_id} campaign exposure",
                errors,
            )
        timestamp = datetime.fromisoformat(row["updated_at_utc"].replace("Z", "+00:00"))
        parsed = (
            line_number,
            row,
            timestamp,
            hashlib.sha256(body).hexdigest().upper(),
        )
        latest_by_campaign[campaign_id] = parsed
        parsed_rows.append(parsed)

    if rows == 0:
        errors.append("campaign exposure ledger must contain at least one row")
    _validate_data_repair_chronology(parsed_rows, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()
    ledger = args.ledger.resolve()
    schema = args.schema.resolve()
    errors = validate_ledger(ledger, schema)
    if errors:
        for error in errors:
            print(f"CAMPAIGN_EXPOSURE_ERROR {error}", file=sys.stderr)
        return 1
    row_count = len(ledger.read_text(encoding="utf-8-sig").splitlines())
    print(f"CAMPAIGN_EXPOSURE_OK rows={row_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
