#!/usr/bin/env python3
"""Build a fail-closed, lineage-aware view of the candidate registry frontier."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


RESEARCH_DIR = Path(__file__).resolve().parent
DEFAULT_REGISTRY = RESEARCH_DIR / "CANDIDATE_REGISTRY.jsonl"
DEFAULT_LINEAGE_OVERRIDES = RESEARCH_DIR / "CANDIDATE_LINEAGE_OVERRIDES.json"

TERMINAL_STATES = {"parked", "killed", "rejected"}
SOURCE_AUTHORITY_KEYS = {"source_build_authorized", "source_run_authorized"}
COLLECTION_AUTHORITY_KEYS = {
    "artifact_collection_authorized",
    "data_acquisition_authorized",
    "model0_data_acquisition_authorized",
    "model4_data_acquisition_authorized",
}
HYPOTHESIS_ID_RE = re.compile(r"\bHYP-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")


class RegistryAuditError(ValueError):
    """Raised when the append-only registry cannot be audited safely."""


def load_registry(path: Path) -> tuple[list[dict[str, Any]], str]:
    raw = path.read_bytes()
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RegistryAuditError(
                f"line {line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(row, dict):
            raise RegistryAuditError(f"line {line_number}: row must be an object")
        hypothesis_id = row.get("hypothesis_id")
        if not isinstance(hypothesis_id, str) or not hypothesis_id.startswith("HYP-"):
            raise RegistryAuditError(
                f"line {line_number}: missing or invalid hypothesis_id"
            )
        annotated = dict(row)
        annotated["_line_number"] = line_number
        rows.append(annotated)
    if not rows:
        raise RegistryAuditError("registry contains no hypothesis rows")
    return rows, hashlib.sha256(raw).hexdigest().upper()


def _last_by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if isinstance(value, str) and value:
            latest[value] = row
    return latest


def extract_parent_ids(parent_candidate: Any) -> set[str]:
    if not isinstance(parent_candidate, str):
        return set()
    return set(HYPOTHESIS_ID_RE.findall(parent_candidate.upper()))


def _authority_true(row: dict[str, Any], keys: set[str]) -> bool:
    validation = row.get("validation")
    scopes = [row]
    if isinstance(validation, dict):
        scopes.append(validation)
    return any(scope.get(key) is True for scope in scopes for key in keys)


def _economic_authority_ready(row: dict[str, Any]) -> bool:
    """Require a coherent last-row economic execution authority, not one flag."""
    return (
        _authority_true(row, {"economics_authorized"})
        and _authority_true(row, {"performance_metrics_authorized"})
        and _authority_true(
            row,
            {
                "model0_authorized",
                "model0_performance_authorized",
                "mt5_train_run_authorized",
            },
        )
    )


def _compact(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "line": row["_line_number"],
        "hypothesis_id": row.get("hypothesis_id"),
        "ea_name": row.get("ea_name"),
        "state": row.get("state"),
        "verdict": row.get("verdict"),
        "symbol": row.get("symbol"),
        "timeframe": row.get("timeframe"),
        "feature_family": row.get("feature_family"),
        "reason": row.get("reason"),
    }


def load_lineage_overrides(
    path: Path,
    registry_sha256: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, str]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema") != "alphafactory_candidate_lineage_overrides.v1":
        raise RegistryAuditError("lineage overrides schema mismatch")
    if data.get("registry_sha256") != registry_sha256:
        raise RegistryAuditError(
            "lineage overrides registry SHA256 does not match current registry"
        )
    known_ids = {row["hypothesis_id"] for row in rows}
    workspace = RESEARCH_DIR.parents[1].resolve()
    edges = data.get("edges")
    if not isinstance(edges, list):
        raise RegistryAuditError("lineage overrides edges must be a list")
    validated: list[dict[str, str]] = []
    for index, edge in enumerate(edges, 1):
        if not isinstance(edge, dict):
            raise RegistryAuditError(f"lineage override {index} must be an object")
        parent_id = edge.get("parent_hypothesis_id")
        successor_id = edge.get("superseding_hypothesis_id")
        if parent_id not in known_ids or successor_id not in known_ids:
            raise RegistryAuditError(
                f"lineage override {index} references an unknown hypothesis"
            )
        if parent_id == successor_id:
            raise RegistryAuditError(f"lineage override {index} is self-referential")
        receipt_relative = edge.get("authority_receipt_path")
        receipt_sha256 = edge.get("authority_receipt_sha256")
        if not isinstance(receipt_relative, str) or not receipt_relative:
            raise RegistryAuditError(
                f"lineage override {index} missing authority receipt path"
            )
        receipt = (workspace / receipt_relative).resolve()
        if not receipt.is_relative_to(workspace) or not receipt.is_file():
            raise RegistryAuditError(
                f"lineage override {index} authority receipt is unavailable"
            )
        actual_receipt_sha256 = hashlib.sha256(receipt.read_bytes()).hexdigest().upper()
        if actual_receipt_sha256 != receipt_sha256:
            raise RegistryAuditError(
                f"lineage override {index} authority receipt SHA256 mismatch"
            )
        validated.append(
            {
                "parent_hypothesis_id": parent_id,
                "superseding_hypothesis_id": successor_id,
                "authority_receipt_path": receipt_relative,
                "authority_receipt_sha256": receipt_sha256,
            }
        )
    return validated


def build_frontier(
    rows: list[dict[str, Any]],
    registry_sha256: str,
    lineage_overrides: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    latest_by_hypothesis = _last_by(rows, "hypothesis_id")
    latest_by_ea = _last_by(rows, "ea_name")

    children: dict[str, set[str]] = defaultdict(set)
    for child_id, row in latest_by_hypothesis.items():
        for parent_id in extract_parent_ids(row.get("parent_candidate")):
            if parent_id in latest_by_hypothesis and parent_id != child_id:
                children[parent_id].add(child_id)

    for edge in lineage_overrides or []:
        children[edge["parent_hypothesis_id"]].add(
            edge["superseding_hypothesis_id"]
        )

    leaf_ids = {
        hypothesis_id
        for hypothesis_id in latest_by_hypothesis
        if not children.get(hypothesis_id)
    }
    leaf_rows = [latest_by_hypothesis[hypothesis_id] for hypothesis_id in leaf_ids]
    leaf_rows.sort(key=lambda row: row["_line_number"])

    open_economic: list[dict[str, Any]] = []
    collection_only: list[dict[str, Any]] = []
    source_only: list[dict[str, Any]] = []
    stale_nonterminal: list[dict[str, Any]] = []
    parked_leaves: list[dict[str, Any]] = []

    for row in leaf_rows:
        state = str(row.get("state") or "unknown").lower()
        if state in TERMINAL_STATES:
            parked_leaves.append(_compact(row))
            continue

        has_economic_authority = _economic_authority_ready(row)
        has_collection_authority = _authority_true(row, COLLECTION_AUTHORITY_KEYS)
        has_source_authority = _authority_true(row, SOURCE_AUTHORITY_KEYS)
        routing_text = " ".join(
            str(row.get(key) or "") for key in ("verdict", "lane", "reason")
        ).upper()

        if has_economic_authority:
            open_economic.append(_compact(row))
        elif has_collection_authority or any(
            token in routing_text
            for token in ("COLLECTION", "DATA_ACQUISITION", "DATA EPOCH")
        ):
            collection_only.append(_compact(row))
        elif has_source_authority or "SOURCE" in routing_text:
            source_only.append(_compact(row))
        else:
            stale_nonterminal.append(_compact(row))

    latest_ea_state_counts = Counter(
        str(row.get("state") or "unknown").lower() for row in latest_by_ea.values()
    )
    latest_hypothesis_state_counts = Counter(
        str(row.get("state") or "unknown").lower()
        for row in latest_by_hypothesis.values()
    )
    leaf_state_counts = Counter(
        str(row.get("state") or "unknown").lower() for row in leaf_rows
    )

    return {
        "schema": "alphafactory_candidate_frontier_audit.v1",
        "registry_sha256": registry_sha256,
        "rows": len(rows),
        "hypotheses": len(latest_by_hypothesis),
        "ea_names": len(latest_by_ea),
        "graph_leaves": len(leaf_rows),
        "applied_lineage_override_count": len(lineage_overrides or []),
        "latest_ea_state_counts": dict(sorted(latest_ea_state_counts.items())),
        "latest_hypothesis_state_counts": dict(
            sorted(latest_hypothesis_state_counts.items())
        ),
        "leaf_state_counts": dict(sorted(leaf_state_counts.items())),
        "open_economic": open_economic,
        "collection_only": collection_only,
        "source_only": source_only,
        "stale_nonterminal": stale_nonterminal,
        "terminal_frontier_count": len(parked_leaves),
        "verdict": (
            "OPEN_ECONOMIC_CANDIDATE_PRESENT"
            if open_economic
            else "NO_OPEN_ECONOMIC_CANDIDATE"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit the current append-only candidate frontier by lineage."
    )
    parser.add_argument(
        "--registry", type=Path, default=DEFAULT_REGISTRY, help="Registry JSONL path"
    )
    parser.add_argument(
        "--lineage-overrides",
        type=Path,
        default=DEFAULT_LINEAGE_OVERRIDES,
        help="Hash-bound explicit lineage override file",
    )
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        rows, registry_sha256 = load_registry(args.registry.resolve())
        lineage_overrides = load_lineage_overrides(
            args.lineage_overrides.resolve(), registry_sha256, rows
        )
        result = build_frontier(rows, registry_sha256, lineage_overrides)
    except (OSError, json.JSONDecodeError, RegistryAuditError) as exc:
        print(f"CANDIDATE_FRONTIER_AUDIT_FAIL: {exc}")
        return 1
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
