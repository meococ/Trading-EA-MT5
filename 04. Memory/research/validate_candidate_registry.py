#!/usr/bin/env python3
"""Validate the generic AlphaFactory append-only hypothesis registry."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema


RESEARCH_DIR = Path(__file__).resolve().parent
WORKSPACE = RESEARCH_DIR.parents[1]
DEFAULT_REGISTRY = RESEARCH_DIR / "CANDIDATE_REGISTRY.jsonl"
DEFAULT_SCHEMA = RESEARCH_DIR / "CANDIDATE_REGISTRY.schema.json"
EXECUTION_STATES = {"screened", "challenger", "confirmed", "portfolio-sleeve"}
TERMINAL_STATES = {"parked", "killed"}
TRANSITIONS = {
    "idea": {"probe", "screened", "parked", "killed"},
    "probe": {"screened", "parked", "killed"},
    "screened": {"challenger", "parked", "killed"},
    "challenger": {"confirmed", "parked", "killed"},
    "confirmed": {"portfolio-sleeve", "parked", "killed"},
    "portfolio-sleeve": {"parked", "killed"},
    "parked": set(),
    "killed": set(),
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def resolve_workspace_path(raw: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(raw, str) or not raw:
        errors.append(f"{label}: path must be a non-empty string")
        return None
    pure = PurePosixPath(raw)
    if (
        Path(raw).is_absolute()
        or pure.is_absolute()
        or "\\" in raw
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != raw
    ):
        errors.append(f"{label}: path must be normalized workspace-relative POSIX: {raw}")
        return None
    candidate = (WORKSPACE / Path(*pure.parts)).resolve()
    try:
        candidate.relative_to(WORKSPACE.resolve())
    except ValueError:
        errors.append(f"{label}: path escapes workspace: {raw}")
        return None
    if not candidate.is_file():
        errors.append(f"{label}: file is missing: {raw}")
        return None
    return candidate


def verify_binding(path_value: Any, hash_value: Any, label: str, errors: list[str]) -> Path | None:
    if path_value is None and hash_value is None:
        return None
    if path_value is None or hash_value is None:
        errors.append(f"{label}: path and SHA256 must be supplied together")
        return None
    path = resolve_workspace_path(path_value, label, errors)
    if path is None:
        return None
    if not isinstance(hash_value, str) or re.fullmatch(r"[A-Fa-f0-9]{64}", hash_value) is None:
        errors.append(f"{label}: SHA256 is invalid")
        return None
    actual = sha256_file(path)
    if actual != hash_value.upper():
        errors.append(f"{label}: SHA256 mismatch expected={hash_value.upper()} actual={actual}")
        return None
    return path


def validate_row_bindings(row: dict[str, Any], line: int, errors: list[str]) -> None:
    label = f"line {line} {row.get('hypothesis_id', '<unknown>')}"
    ea_name = str(row.get("ea_name") or "")
    expected_source = f"03. EA Developer/{ea_name}/{ea_name}.mq5"
    source_path = row.get("source_path")
    prereg_path = row.get("prereg_path")

    if source_path is not None and source_path != expected_source:
        errors.append(f"{label}: source_path must be canonical '{expected_source}'")
    source_file = verify_binding(source_path, row.get("source_hash"), f"{label} source", errors)
    prereg_file = verify_binding(prereg_path, row.get("prereg_sha256"), f"{label} prereg", errors)
    if prereg_path is not None:
        expected_prefix = f"03. EA Developer/{ea_name}/research/"
        if not str(prereg_path).startswith(expected_prefix):
            errors.append(f"{label}: prereg_path must be inside '{expected_prefix}'")
    if row.get("state") in EXECUTION_STATES:
        if row.get("model") != 0:
            errors.append(f"{label}: execution state requires Model 0")
        if source_file is None or prereg_file is None:
            errors.append(f"{label}: execution state requires hash-bound canonical source and prereg")
    if row.get("updated_at_utc") and not str(row["updated_at_utc"]).endswith("Z"):
        errors.append(f"{label}: updated_at_utc must use a Z timestamp")
    try:
        start = datetime.strptime(str(row["window"]["from"]), "%Y.%m.%d")
        end = datetime.strptime(str(row["window"]["to"]), "%Y.%m.%d")
        if start >= end:
            errors.append(f"{label}: window.from must be earlier than window.to")
    except (KeyError, TypeError, ValueError):
        pass
    acceptance = row.get("acceptance_contract")
    if isinstance(acceptance, dict):
        minimum = acceptance.get("min_trades_per_week")
        maximum = acceptance.get("max_trades_per_week")
        if isinstance(minimum, (int, float)) and isinstance(maximum, (int, float)) and minimum > maximum:
            errors.append(f"{label}: acceptance_contract min_trades_per_week exceeds max_trades_per_week")


def load_strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8-sig"),
        parse_constant=reject_nonfinite,
        object_pairs_hook=reject_duplicate_keys,
    )


def validate_registry(registry: Path, schema_path: Path) -> list[str]:
    errors: list[str] = []
    if not registry.is_file():
        return [f"registry is missing: {registry}"]
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

    latest: dict[str, tuple[int, dict[str, Any], datetime]] = {}
    rows = 0
    for line_number, raw in enumerate(registry.read_text(encoding="utf-8-sig").splitlines(), 1):
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
        validate_row_bindings(row, line_number, errors)
        hypothesis_id = row["hypothesis_id"]
        timestamp = datetime.fromisoformat(row["updated_at_utc"].replace("Z", "+00:00"))
        if hypothesis_id in latest:
            prior_line, prior, prior_timestamp = latest[hypothesis_id]
            for invariant in ("ea_name", "parent_candidate", "feature_family", "lane", "symbol", "timeframe"):
                if row[invariant] != prior[invariant]:
                    errors.append(
                        f"line {line_number} {hypothesis_id}: invariant '{invariant}' changed from line {prior_line}"
                    )
            if timestamp <= prior_timestamp:
                errors.append(f"line {line_number} {hypothesis_id}: timestamp must increase")
            prior_state = prior["state"]
            if prior_state != "idea":
                for frozen in ("window", "model", "exact_overrides", "acceptance_contract"):
                    if row[frozen] != prior[frozen]:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: frozen '{frozen}' changed from line {prior_line}"
                        )
            if prior_state in EXECUTION_STATES:
                for frozen in ("source_path", "source_hash", "prereg_path", "prereg_sha256"):
                    if row[frozen] != prior[frozen]:
                        errors.append(
                            f"line {line_number} {hypothesis_id}: execution-bound '{frozen}' changed from line {prior_line}"
                        )
            if row["state"] not in TRANSITIONS[prior_state]:
                errors.append(
                    f"line {line_number} {hypothesis_id}: illegal transition {prior_state}->{row['state']}"
                )
        latest[hypothesis_id] = (line_number, row, timestamp)

    if rows == 0:
        errors.append("registry must contain at least one row")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = parser.parse_args()
    registry = args.registry.resolve()
    schema = args.schema.resolve()
    errors = validate_registry(registry, schema)
    if errors:
        for error in errors:
            print(f"CANDIDATE_REGISTRY_ERROR {error}", file=sys.stderr)
        return 1
    row_count = len(registry.read_text(encoding="utf-8-sig").splitlines())
    hypotheses = {
        json.loads(line)["hypothesis_id"]
        for line in registry.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    }
    print(f"CANDIDATE_REGISTRY_OK rows={row_count} hypotheses={len(hypotheses)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
