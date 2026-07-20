#!/usr/bin/env python3
"""Fail-closed validation for the frozen public EA comparison cohort."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


FORBIDDEN_FREEZE_KEYS = {
    "profit",
    "return",
    "monthly_returns",
    "profit_factor",
    "pf",
    "win_rate",
    "drawdown",
    "sharpe",
    "sortino",
    "calmar",
    "rank",
    "ranking",
}
REQUIRED_LEDGER_FIELDS = {
    "candidate_id",
    "access_date",
    "source_grade",
    "evidence_urls",
    "months_observed",
    "closed_trades",
    "history_complete",
    "custom_start_absent",
    "cashflows_observable",
    "verification",
    "reproducibility",
    "delisted_or_terminated",
    "decision",
    "rejection_reasons",
    "confidence",
}


class EvidenceError(ValueError):
    pass


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_utc(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise EvidenceError(f"{field} must be ISO-8601 UTC") from exc
    if parsed.tzinfo is None:
        raise EvidenceError(f"{field} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _all_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key).lower())
            keys.update(_all_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_all_keys(child))
    return keys


def validate_freeze(freeze: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if freeze.get("study_id") != "STUDY-FVG-COMPARE-EURUSD-M5-001":
        raise EvidenceError("unexpected study_id")
    frozen_at = _parse_utc(freeze.get("frozen_at_utc", ""), "frozen_at_utc")
    pass2_started = freeze.get("pass2_started_at_utc")
    if pass2_started and frozen_at >= _parse_utc(pass2_started, "pass2_started_at_utc"):
        raise EvidenceError("cohort was not frozen before pass 2")
    candidates = freeze.get("candidates")
    if not isinstance(candidates, list) or not 10 <= len(candidates) <= 20:
        raise EvidenceError("frozen cohort must contain 10-20 candidates")
    forbidden = _all_keys(candidates) & FORBIDDEN_FREEZE_KEYS
    if forbidden:
        raise EvidenceError(f"performance fields leaked into pass-1 freeze: {sorted(forbidden)}")

    indexed: dict[str, dict[str, Any]] = {}
    urls: set[str] = set()
    for row in candidates:
        if not isinstance(row, dict):
            raise EvidenceError("candidate row must be an object")
        candidate_id = str(row.get("candidate_id", "")).strip()
        name = str(row.get("name", "")).strip()
        url = str(row.get("primary_url", "")).strip()
        if not re.fullmatch(r"EA-[A-Z0-9-]+", candidate_id):
            raise EvidenceError(f"invalid candidate_id: {candidate_id!r}")
        if not name or not url.startswith("https://"):
            raise EvidenceError(f"candidate {candidate_id} lacks name/HTTPS URL")
        if candidate_id in indexed or url in urls:
            raise EvidenceError(f"duplicate candidate or URL: {candidate_id}")
        if row.get("instrument_scope") not in {"FX", "FX_AND_METALS"}:
            raise EvidenceError(f"candidate {candidate_id} is outside frozen FX scope")
        if row.get("product_type") != "MT5_EA":
            raise EvidenceError(f"candidate {candidate_id} is not an MT5 EA")
        indexed[candidate_id] = row
        urls.add(url)
    return indexed


def _is_eligible(row: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    grade = row["source_grade"]
    if grade not in {"A", "B", "C"}:
        reasons.append("INVALID_SOURCE_GRADE")
    if grade == "C":
        reasons.append("GRADE_C_FEATURE_ONLY")
    if float(row["months_observed"]) < 36:
        reasons.append("LT_36_MONTHS")
    if int(row["closed_trades"]) < 200:
        reasons.append("LT_200_CLOSED_TRADES")
    if not row["history_complete"]:
        reasons.append("HISTORY_NOT_COMPLETE")
    if not row["custom_start_absent"]:
        reasons.append("CUSTOM_START_OR_UNKNOWN")
    if not row["cashflows_observable"]:
        reasons.append("CASHFLOWS_NOT_OBSERVABLE")

    verification = row["verification"]
    reproducibility = row["reproducibility"]
    if grade == "A":
        myfxbook_ok = bool(
            verification.get("myfxbook_track_record")
            and verification.get("myfxbook_trading_privileges")
        )
        mql5_ok = bool(
            verification.get("mql5_real_monitored")
            and verification.get("mql5_full_history")
        )
        if not (myfxbook_ok or mql5_ok):
            reasons.append("LIVE_VERIFICATION_INCOMPLETE")
    elif grade == "B":
        if not (
            reproducibility.get("source_or_demo_available")
            and reproducibility.get("data_hash_bound")
            and reproducibility.get("procedure_reproducible")
        ):
            reasons.append("REPRODUCIBILITY_INCOMPLETE")

    return not reasons, reasons


def validate_ledger(
    freeze_index: dict[str, dict[str, Any]], ledger: dict[str, Any]
) -> tuple[list[str], list[dict[str, Any]]]:
    if ledger.get("study_id") != "STUDY-FVG-COMPARE-EURUSD-M5-001":
        raise EvidenceError("ledger study_id mismatch")
    rows = ledger.get("entities")
    if not isinstance(rows, list):
        raise EvidenceError("ledger entities must be a list")
    if len(rows) != len(freeze_index):
        raise EvidenceError("ledger must preserve every frozen entity exactly once")

    seen: set[str] = set()
    eligible: list[str] = []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        missing = REQUIRED_LEDGER_FIELDS - set(row)
        if missing:
            raise EvidenceError(f"ledger row missing fields: {sorted(missing)}")
        candidate_id = row["candidate_id"]
        if candidate_id not in freeze_index or candidate_id in seen:
            raise EvidenceError(f"ledger entity not uniquely frozen: {candidate_id}")
        seen.add(candidate_id)
        try:
            date.fromisoformat(row["access_date"])
        except (TypeError, ValueError) as exc:
            raise EvidenceError(f"invalid access_date for {candidate_id}") from exc
        if not isinstance(row["evidence_urls"], list) or not row["evidence_urls"]:
            raise EvidenceError(f"no evidence URL for {candidate_id}")
        computed, computed_reasons = _is_eligible(row)
        declared = row["decision"] == "PERFORMANCE_ELIGIBLE"
        if declared != computed:
            raise EvidenceError(
                f"decision mismatch for {candidate_id}: computed={computed}, "
                f"reasons={computed_reasons}"
            )
        declared_reasons = set(row["rejection_reasons"])
        if not computed and not set(computed_reasons).issubset(declared_reasons):
            raise EvidenceError(f"incomplete rejection reasons for {candidate_id}")
        if row["confidence"] not in {"high", "medium", "low"}:
            raise EvidenceError(f"invalid confidence for {candidate_id}")
        if computed:
            eligible.append(candidate_id)
        normalized.append(
            {
                "candidate_id": candidate_id,
                "source_grade": row["source_grade"],
                "eligible": computed,
                "reasons": computed_reasons,
            }
        )
    return eligible, normalized


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    try:
        freeze_index = validate_freeze(_read_json(args.freeze))
        eligible, entities = validate_ledger(freeze_index, _read_json(args.ledger))
        result = {
            "schema_version": "public_verification_readout.v1",
            "study_id": "STUDY-FVG-COMPARE-EURUSD-M5-001",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "frozen_candidates": len(freeze_index),
            "eligible_grade_a_or_b": len(eligible),
            "eligible_candidate_ids": eligible,
            "verdict": (
                "READY_FOR_NORMALIZED_PERFORMANCE_COMPARISON"
                if len(eligible) >= 5
                else "INSUFFICIENT_VERIFIED_DATA"
            ),
            "entities": entities,
        }
    except (EvidenceError, KeyError, TypeError, ValueError) as exc:
        result = {
            "schema_version": "public_verification_readout.v1",
            "study_id": "STUDY-FVG-COMPARE-EURUSD-M5-001",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "verdict": "INVALID_EVIDENCE_PACKAGE",
            "error": str(exc),
        }
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 2

    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

