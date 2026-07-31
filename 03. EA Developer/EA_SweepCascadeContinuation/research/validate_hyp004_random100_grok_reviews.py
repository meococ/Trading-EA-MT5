#!/usr/bin/env python3
"""Validate 20 accepted Grok batches and build the random-100 review dataset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def binding(workspace: Path, path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(workspace).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("inf")


def iter_string_values(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from iter_string_values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_string_values(nested)


def has_forbidden_visual_claim(review: dict[str, object]) -> bool:
    """Detect affirmative hallucinated-panel claims without flagging negations.

    Word boundaries are material: for example, the letters "rsi" occur inside
    the ordinary word "reversion" and must not be treated as an RSI claim.
    """

    panel_pattern = re.compile(
        r"\b(?:m15|macd|rsi|adx|fvg)\b|"
        r"\border[- ]block\b|"
        r"\bconfluence label\b|"
        r"\bhtf bias marker\b",
        flags=re.IGNORECASE,
    )
    negative_pattern = re.compile(
        r"\b(?:no|not|without|absent|unsupported)\b|"
        r"\bnot_requested\b|"
        r"\bonly\s+(?:m5|m5\s*(?:and|\+|/)\s*h1)\b",
        flags=re.IGNORECASE,
    )
    for text in iter_string_values(review):
        for clause in re.split(r"(?<=[.;])|\bbut\b|\bhowever\b", text):
            if panel_pattern.search(clause) and not negative_pattern.search(clause):
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--random-root",
        type=Path,
        help="Optional corrected-casebook root; defaults to random100_forensics.",
    )
    parser.add_argument(
        "--context-root",
        type=Path,
        help="Optional Grok context root; defaults to .context/scc-hyp004-random100-gfi.",
    )
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[3]
    evidence = (
        workspace
        / "03. EA Developer"
        / "EA_SweepCascadeContinuation"
        / "research"
        / "evidence"
        / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS"
    )
    random_root = (
        args.random_root.resolve()
        if args.random_root is not None
        else evidence / "random100_forensics"
    )
    context_root = (
        args.context_root.resolve()
        if args.context_root is not None
        else workspace / ".context" / "scc-hyp004-random100-gfi"
    )
    output_root = random_root / "grok_review"
    output_root.mkdir(parents=True, exist_ok=True)

    sample_csv = random_root / "random100_cases.csv"
    sample_manifest_path = random_root / "random100_sample_manifest.json"
    decision_manifest_path = random_root / "decision_asof" / "cases_manifest.json"
    pair_analysis_path = evidence / "pair_analysis.json"
    with sample_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        sample_rows = list(csv.DictReader(handle))
    sample_by_id = {row["case_id"]: row for row in sample_rows}
    decision_manifest = json.loads(
        decision_manifest_path.read_text(encoding="utf-8-sig")
    )
    decision_by_id = {
        str(row["case_id"]): row for row in decision_manifest["results"]
    }
    expected_ids = [row["case_id"] for row in sample_rows]
    if len(expected_ids) != len(set(expected_ids)) or len(expected_ids) != 100:
        raise SystemExit("Frozen sample is not 100 unique cases")

    errors: list[str] = []
    accepted_batches: list[dict[str, object]] = []
    combined_rows: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    accepted_cost = 0.0

    for number in range(1, 21):
        batch_id = f"batch{number:02d}"
        batch_dir = context_root / batch_id
        request_path = batch_dir / "grok-request.json"
        request = json.loads(request_path.read_text(encoding="utf-8-sig"))
        expected_batch_ids = request["meta"]["case_ids"]
        accepted_candidates: list[
            tuple[Path, dict[str, object], dict[str, object], dict[str, object]]
        ] = []
        for run_dir in sorted(
            (path for path in batch_dir.glob("run*") if path.is_dir()),
            key=lambda path: (len(path.name), path.name),
        ):
            summary_path = run_dir / "summary.json"
            response_path = run_dir / "grok-response.json"
            if not summary_path.is_file() or not response_path.is_file():
                continue
            summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
            actual_request_path = Path(str(summary.get("request_file") or ""))
            if not actual_request_path.is_file():
                continue
            actual_request = json.loads(
                actual_request_path.read_text(encoding="utf-8-sig")
            )
            prompt_blocks = summary.get("prompt_blocks") or {}
            expected_prompt_sha = str(
                actual_request.get("prompt_blocks_sha256") or ""
            )
            retry_contract_ok = (
                "recovery" not in actual_request
                or (
                    (actual_request.get("recovery") or {}).get(
                        "contract_changed"
                    )
                    is False
                    and Path(
                        str(
                            (actual_request.get("recovery") or {}).get(
                                "source_request"
                            )
                            or ""
                        )
                    ).resolve()
                    == request_path.resolve()
                    and str(
                        (actual_request.get("recovery") or {}).get(
                            "source_request_sha256"
                        )
                        or ""
                    ).casefold()
                    == sha256(request_path).casefold()
                )
            )
            if (
                summary.get("success") is True
                and summary.get("response_useful") is True
                and "EndTurn" in str(summary.get("stop_reason"))
                and (summary.get("structured_output_validation") or {}).get("passed")
                is True
                and summary.get("prompt_transport") == "acp_blocks_file"
                and prompt_blocks.get("image_count") == 10
                and prompt_blocks.get("block_count") == 11
                and str(prompt_blocks.get("sha256") or "").casefold()
                == expected_prompt_sha.casefold()
                and (actual_request.get("meta") or {}).get("case_ids")
                == expected_batch_ids
                and retry_contract_ok
            ):
                response = json.loads(response_path.read_text(encoding="utf-8-sig"))
                try:
                    payload = json.loads(response["output_text"])
                except (KeyError, json.JSONDecodeError):
                    continue
                reviews = payload.get("case_reviews")
                if not isinstance(reviews, list) or len(reviews) != 5:
                    continue
                by_case = {
                    str(review.get("case_id")): review
                    for review in reviews
                    if isinstance(review, dict)
                }
                semantic_ok = set(by_case) == set(expected_batch_ids)
                for case_id in expected_batch_ids:
                    truth = sample_by_id[case_id]
                    review = by_case.get(case_id, {})
                    all_text = json.dumps(review, ensure_ascii=False).lower()
                    generic_text = any(
                        token in all_text
                        for token in (
                            "placeholder",
                            "decision image opened",
                            "anatomy image opened",
                            '"pending"',
                        )
                    )
                    forbidden_visual_claim = has_forbidden_visual_claim(review)
                    expected_direction = (
                        "LONG" if truth["direction_label"] == "BUY" else "SHORT"
                    )
                    expected_range_position = float(
                        decision_by_id[case_id]["context"]["metrics"][
                            "range_position_20"
                        ]
                    )
                    semantic_ok = semantic_ok and (
                        int(review.get("sample_rank", -1)) == int(truth["sample_rank"])
                        and int(review.get("position_id", -1)) == int(truth["position_id"])
                        and review.get("decision_image_opened") is True
                        and review.get("anatomy_image_opened") is True
                        and review.get("visible_direction") == expected_direction
                        and abs(
                            safe_float(review.get("visible_entry_price"))
                            - float(truth["entry"])
                        )
                        <= 0.00002
                        and abs(
                            safe_float(review.get("visible_exit_price"))
                            - float(truth["exit"])
                        )
                        <= 0.00002
                        and review.get("visible_exit_class") == truth["reason"]
                        and abs(
                            safe_float(review.get("visible_h1_range_position"))
                            - expected_range_position
                        )
                        <= 0.002
                        and review.get("decision_future_hidden_seen") is True
                        and review.get("anatomy_outcome_region_seen") is True
                        and review.get("unsupported_indicator_panels_claimed") is False
                        and not generic_text
                        and not forbidden_visual_claim
                    )
                if semantic_ok:
                    accepted_candidates.append((run_dir, summary, response, payload))
        if len(accepted_candidates) != 1:
            errors.append(
                f"{batch_id}: expected one accepted response, got {len(accepted_candidates)}"
            )
            continue

        run_dir, summary, response, payload = accepted_candidates[0]
        response_path = run_dir / "grok-response.json"
        accepted_source = run_dir.name
        accepted_request_path = Path(str(summary["request_file"])).resolve()
        if not accepted_request_path.is_file():
            errors.append(f"{batch_id}: accepted request artifact is missing")
            continue
        if payload.get("batch_id") != batch_id:
            errors.append(f"{batch_id}: response batch ID mismatch")
        coverage = payload.get("coverage") or {}
        for key in (
            "expected_cases",
            "reviewed_cases",
            "decision_images_opened",
            "anatomy_images_opened",
        ):
            if coverage.get(key) != 5:
                errors.append(f"{batch_id}: coverage {key} != 5")
        if payload.get("no_tuning_applied") is not True:
            errors.append(f"{batch_id}: no_tuning_applied is not true")
        reviews = payload.get("case_reviews")
        if not isinstance(reviews, list) or len(reviews) != 5:
            errors.append(f"{batch_id}: expected five case reviews")
            continue
        response_ids = [str(row.get("case_id")) for row in reviews]
        if set(response_ids) != set(expected_batch_ids) or len(set(response_ids)) != 5:
            errors.append(
                f"{batch_id}: response IDs differ from request IDs "
                f"expected={expected_batch_ids} actual={response_ids}"
            )
        for review in reviews:
            case_id = str(review["case_id"])
            if case_id in seen_ids:
                errors.append(f"Duplicate reviewed case: {case_id}")
                continue
            seen_ids.add(case_id)
            truth = sample_by_id.get(case_id)
            if truth is None:
                errors.append(f"Unknown reviewed case: {case_id}")
                continue
            if review.get("decision_image_opened") is not True:
                errors.append(f"{case_id}: decision image not opened")
            if review.get("anatomy_image_opened") is not True:
                errors.append(f"{case_id}: anatomy image not opened")
            if int(review["sample_rank"]) != int(truth["sample_rank"]):
                errors.append(f"{case_id}: sample rank mismatch")
            if int(review["position_id"]) != int(truth["position_id"]):
                errors.append(f"{case_id}: position ID mismatch")
            combined_rows.append(
                {
                    "case_id": case_id,
                    "batch_id": batch_id,
                    "accepted_run_dir": accepted_source,
                    "sample_rank": int(truth["sample_rank"]),
                    "position_id": int(truth["position_id"]),
                    "direction": truth["direction_label"],
                    "entry_time_utc": truth["entry_time_utc"],
                    "exit_time_utc": truth["exit_time_utc"],
                    "net_account": float(truth["net_account"]),
                    "net_R": float(truth["net_R"]),
                    "outcome": "WIN" if float(truth["net_account"]) > 0 else "LOSS",
                    "exit_class": truth["reason"],
                    "hold_minutes": float(truth["hold_minutes"]),
                    "risk_points": float(truth["risk_points"]),
                    "mechanism": review["mechanism"],
                    "evidence_class": review["evidence_class"],
                    "decision_observations": review["decision_observations"],
                    "anatomy_observations": review["anatomy_observations"],
                    "data_quality_note": review["data_quality_note"],
                }
            )
        accepted_cost += float(summary.get("total_cost_usd") or 0.0)
        accepted_batches.append(
            {
                "batch_id": batch_id,
                "accepted_run_dir": accepted_source,
                "request": binding(workspace, accepted_request_path),
                "response": binding(workspace, response_path),
                "summary": binding(workspace, run_dir / "summary.json"),
                "case_ids": response_ids,
                "turns": summary.get("num_turns"),
                "elapsed_seconds": summary.get("elapsed_seconds"),
                "cost_usd": summary.get("total_cost_usd"),
            }
        )

    if seen_ids != set(expected_ids):
        errors.append(
            f"Global coverage mismatch missing={sorted(set(expected_ids)-seen_ids)} "
            f"extra={sorted(seen_ids-set(expected_ids))}"
        )
    if len(combined_rows) != 100:
        errors.append(f"Expected 100 combined reviews, got {len(combined_rows)}")
    if errors:
        for error in errors[:100]:
            print(f"SCC_RANDOM100_GROK_ERROR {error}")
        raise SystemExit(1)

    combined_rows.sort(key=lambda row: int(row["sample_rank"]))
    jsonl_path = output_root / "random100_grok_case_reviews.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in combined_rows:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")

    csv_path = output_root / "random100_grok_case_reviews.csv"
    csv_fields = [
        "case_id",
        "batch_id",
        "accepted_run_dir",
        "sample_rank",
        "position_id",
        "direction",
        "entry_time_utc",
        "exit_time_utc",
        "net_account",
        "net_R",
        "outcome",
        "exit_class",
        "hold_minutes",
        "risk_points",
        "mechanism",
        "evidence_class",
        "data_quality_note",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(combined_rows)

    mechanism_counts = Counter(row["mechanism"] for row in combined_rows)
    evidence_counts = Counter(row["evidence_class"] for row in combined_rows)
    mechanism_by_outcome: dict[str, dict[str, int]] = defaultdict(
        lambda: {"WIN": 0, "LOSS": 0}
    )
    mechanism_by_direction: dict[str, dict[str, int]] = defaultdict(
        lambda: {"BUY": 0, "SELL": 0}
    )
    mechanism_by_exit: dict[str, Counter[str]] = defaultdict(Counter)
    for row in combined_rows:
        mechanism = str(row["mechanism"])
        mechanism_by_outcome[mechanism][str(row["outcome"])] += 1
        mechanism_by_direction[mechanism][str(row["direction"])] += 1
        mechanism_by_exit[mechanism][str(row["exit_class"])] += 1

    pair = json.loads(pair_analysis_path.read_text(encoding="utf-8-sig"))
    sample_manifest = json.loads(sample_manifest_path.read_text(encoding="utf-8-sig"))
    stats = {
        "schema_version": "scc_random100_grok_descriptive_stats.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004",
        "run_id": "20260725_210811",
        "coverage": {
            "batches": 20,
            "cases": 100,
            "decision_images_opened": 100,
            "anatomy_images_opened": 100,
            "total_images_opened": 200,
        },
        "population_metrics": {
            "trades": pair["challenger"]["native"]["n"],
            "win_rate_pct": pair["challenger"]["native"]["win_rate_pct"],
            "profit_factor": pair["challenger"]["native"]["profit_factor"],
            "net_account": pair["challenger"]["native"]["net"],
            "mean_realized_r": pair["challenger"]["realized_r"]["mean"],
            "cadence_per_elapsed_week": pair["challenger"][
                "cadence_per_elapsed_week"
            ],
        },
        "random_sample_metrics": sample_manifest["sample"]["metrics_after_selection"],
        "mechanism_counts": dict(mechanism_counts),
        "mechanism_by_outcome": dict(mechanism_by_outcome),
        "mechanism_by_direction": dict(mechanism_by_direction),
        "mechanism_by_exit_class": {
            key: dict(value) for key, value in mechanism_by_exit.items()
        },
        "evidence_class_counts": dict(evidence_counts),
        "interpretation_boundary": (
            "Mechanism labels use outcome-disclosing anatomy images. Their cross-tabs "
            "describe realized paths and are not decision-time predictive filters."
        ),
    }
    stats_path = output_root / "random100_grok_descriptive_stats.json"
    stats_path.write_text(
        json.dumps(stats, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    qc = {
        "schema_version": "scc_random100_grok_batch_qc.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004",
        "run_id": "20260725_210811",
        "status": "PASS",
        "accepted_batches": 20,
        "unique_cases": 100,
        "decision_images_opened": 100,
        "anatomy_images_opened": 100,
        "total_images_opened": 200,
        "accepted_cost_usd": accepted_cost,
        "accepted_runs": accepted_batches,
        "outputs": {
            "case_reviews_jsonl": binding(workspace, jsonl_path),
            "case_reviews_csv": binding(workspace, csv_path),
            "descriptive_stats": binding(workspace, stats_path),
        },
        "errors": [],
    }
    qc_path = output_root / "random100_grok_batch_qc.json"
    qc_path.write_text(
        json.dumps(qc, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        "SCC_RANDOM100_GROK_QC_OK "
        f"batches=20 cases=100 images=200 qc_sha256={sha256(qc_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
