#!/usr/bin/env python3
"""Build the deterministic Phase-0 artifact-sufficiency decision.

This preflight is intentionally outcome blind. Candidate runs must be named
exactly in the frozen spec. The only permitted inspections are exact-path
existence, identity-manifest fields, the first CSV header line, and SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


SPEC_SCHEMA_VERSION = "phase0_artifact_sufficiency_spec.v1"
RESULT_SCHEMA_VERSION = "phase0_artifact_sufficiency.v1"
ATTESTATION_SCHEMA_VERSION = "phase0_coordination_contamination_attestation.v1"
FROZEN_SPEC_SHA256 = "156995947c34f9ed40d1c8aa69b1bb603c5d925ef87ad9d1898803ef21eb976f"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
HASH_FIELD_PATTERN = re.compile(r"^[a-z][a-z0-9_]*_sha256$")
WILDCARD_MARKERS = ("*", "?", "[", "]", "{", "}")
FORBIDDEN_SELECTOR_KEYS = {
    "best",
    "best_run",
    "cadence",
    "candidate_glob",
    "candidate_pattern",
    "column_selector",
    "columns_selector",
    "filter",
    "glob",
    "metric_selector",
    "metric_selectors",
    "metrics",
    "min_pf",
    "minimum_trades",
    "net",
    "net_profit",
    "outcome_selector",
    "outcome_selectors",
    "outcomes",
    "pattern",
    "pf",
    "profit_factor",
    "query",
    "rank",
    "rank_by",
    "rglob",
    "row_filter",
    "row_filters",
    "row_selector",
    "row_selectors",
    "top_n",
    "trades",
    "where",
}
FORBIDDEN_ARTIFACT_MARKERS = (
    "enhanced_summary",
    "report.html",
    "analysis_report",
    "trades_summary",
    "overnight_exposure",
    "runmeta",
)
IDENTITY_KEYS = ("run_id", "ea_name", "symbol", "period", "model")


class SpecValidationError(ValueError):
    """Raised before candidate filesystem access when a spec is unsafe."""


class ArtifactInspectionError(RuntimeError):
    """Raised when a permitted inspection cannot be completed safely."""


class LocalFileSystem:
    """Narrow filesystem API: deliberately no discovery/list/glob methods."""

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    @staticmethod
    def _stat_identity(value: os.stat_result) -> tuple[int, int, int, int]:
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

    @classmethod
    def _assert_stable_snapshot(
        cls,
        path: Path,
        before: os.stat_result,
        after: os.stat_result,
    ) -> None:
        try:
            current = path.stat()
        except OSError as exc:
            raise ArtifactInspectionError(
                f"artifact disappeared after snapshot: {path}"
            ) from exc
        if not (
            cls._stat_identity(before)
            == cls._stat_identity(after)
            == cls._stat_identity(current)
        ):
            raise ArtifactInspectionError(f"artifact changed during snapshot: {path}")

    def inspect_json_and_sha256(self, path: Path) -> tuple[dict[str, Any], str]:
        with path.open("rb", buffering=0) as handle:
            before = os.fstat(handle.fileno())
            payload = handle.read()
            after = os.fstat(handle.fileno())
        self._assert_stable_snapshot(path, before, after)
        try:
            value = json.loads(payload.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArtifactInspectionError(f"invalid JSON metadata: {path}") from exc
        if not isinstance(value, dict):
            raise ArtifactInspectionError(f"expected JSON object: {path}")
        return value, hashlib.sha256(payload).hexdigest()

    def inspect_header_and_sha256(
        self, path: Path, max_bytes: int
    ) -> tuple[bytes, str]:
        # The whole file is streamed only into SHA-256. Only the first line is
        # retained for schema inspection, so result rows are never parsed.
        header = bytearray()
        header_complete = False
        digest = hashlib.sha256()
        with path.open("rb", buffering=0) as handle:
            before = os.fstat(handle.fileno())
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                if not header_complete:
                    newline = chunk.find(b"\n")
                    if newline >= 0:
                        header.extend(chunk[:newline])
                        header_complete = True
                    else:
                        header.extend(chunk)
                    if len(header) > max_bytes:
                        raise ArtifactInspectionError(
                            f"CSV header exceeds frozen byte limit ({max_bytes}): {path}"
                        )
            after = os.fstat(handle.fileno())
        self._assert_stable_snapshot(path, before, after)
        if len(header) > max_bytes:
            raise ArtifactInspectionError(
                f"CSV header exceeds frozen byte limit ({max_bytes}): {path}"
            )
        return bytes(header).rstrip(b"\r"), digest.hexdigest()

    def sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb", buffering=0) as handle:
            before = os.fstat(handle.fileno())
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
            after = os.fstat(handle.fileno())
        self._assert_stable_snapshot(path, before, after)
        return digest.hexdigest()


def _require_exact_keys(
    value: dict[str, Any], expected: set[str], context: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise SpecValidationError(
            f"{context} keys mismatch; missing={missing}, extra={extra}"
        )


def _walk_spec(value: Any):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key, nested
            yield from _walk_spec(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_spec(nested)


def _reject_outcome_selectors(spec: dict[str, Any]) -> None:
    for key, value in _walk_spec(spec):
        if key.lower() in FORBIDDEN_SELECTOR_KEYS:
            raise SpecValidationError(f"forbidden selector key: {key}")
        if isinstance(value, str):
            lowered = value.replace("\\", "/").lower()
            if any(marker in lowered for marker in FORBIDDEN_ARTIFACT_MARKERS):
                raise SpecValidationError(
                    f"forbidden artifact reference in spec field {key}: {value}"
                )


def _validate_exact_relative_path(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise SpecValidationError(f"{context} must be an exact relative path")
    windows_path = PureWindowsPath(value)
    if (
        "\\" in value
        or ":" in value
        or windows_path.drive
        or windows_path.root
        or any(marker in value for marker in WILDCARD_MARKERS)
    ):
        raise SpecValidationError(f"{context} must be an exact relative path: {value}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise SpecValidationError(f"{context} must be an exact relative path: {value}")
    if str(path) != value:
        raise SpecValidationError(f"{context} must be an exact relative path: {value}")
    return value


def _validate_sha256(value: Any, context: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise SpecValidationError(f"{context} must be lowercase SHA-256")
    return value


def validate_spec(spec: Any) -> dict[str, Any]:
    """Validate every spec rule before any candidate filesystem operation."""

    if not isinstance(spec, dict):
        raise SpecValidationError("spec must be a JSON object")

    # Security ordering is intentional: selectors are rejected before schema
    # traversal can ever lead to a candidate filesystem operation.
    _reject_outcome_selectors(spec)

    _require_exact_keys(
        spec,
        {
            "schema_version",
            "as_of_date",
            "run_root",
            "coordination_session_attestation",
            "policy",
            "probes",
        },
        "spec",
    )
    if spec["schema_version"] != SPEC_SCHEMA_VERSION:
        raise SpecValidationError("unsupported spec schema_version")
    if spec["as_of_date"] != "2026-07-11":
        raise SpecValidationError("as_of_date must remain frozen at 2026-07-11")
    _validate_exact_relative_path(spec["run_root"], "run_root")

    attestation_ref = spec["coordination_session_attestation"]
    if not isinstance(attestation_ref, dict):
        raise SpecValidationError("coordination_session_attestation must be an object")
    _require_exact_keys(
        attestation_ref,
        {"path", "sha256"},
        "coordination_session_attestation",
    )
    _validate_exact_relative_path(
        attestation_ref["path"], "coordination_session_attestation.path"
    )
    _validate_sha256(
        attestation_ref["sha256"], "coordination_session_attestation.sha256"
    )

    policy = spec["policy"]
    if not isinstance(policy, dict):
        raise SpecValidationError("policy must be an object")
    _require_exact_keys(
        policy,
        {
            "candidate_selection",
            "auto_discovery",
            "semantic_data_access",
            "allowed_inspections",
            "hash_algorithm",
            "header_max_bytes",
        },
        "policy",
    )
    if policy["candidate_selection"] != "EXACT_LIST_ONLY":
        raise SpecValidationError("candidate_selection must be EXACT_LIST_ONLY")
    if policy["auto_discovery"] is not False:
        raise SpecValidationError("auto_discovery must be false")
    if policy["semantic_data_access"] != "FORBIDDEN":
        raise SpecValidationError("semantic_data_access must be FORBIDDEN")
    if policy["allowed_inspections"] != [
        "EXACT_PATH",
        "COORDINATION_ATTESTATION",
        "IDENTITY_MANIFEST",
        "CSV_HEADER",
        "SHA256",
    ]:
        raise SpecValidationError("allowed_inspections must remain frozen")
    if policy["hash_algorithm"] != "sha256":
        raise SpecValidationError("hash_algorithm must be sha256")
    if not isinstance(policy["header_max_bytes"], int) or not (
        1 <= policy["header_max_bytes"] <= 16384
    ):
        raise SpecValidationError("header_max_bytes must be between 1 and 16384")

    probes = spec["probes"]
    if not isinstance(probes, list) or len(probes) != 2:
        raise SpecValidationError("spec must contain exactly PROBE_A and PROBE_B")
    if [probe.get("probe_id") for probe in probes if isinstance(probe, dict)] != [
        "PROBE_A",
        "PROBE_B",
    ]:
        raise SpecValidationError("probe order must be PROBE_A then PROBE_B")

    probe_a = probes[0]
    if not isinstance(probe_a, dict):
        raise SpecValidationError("PROBE_A must be an object")
    _require_exact_keys(
        probe_a,
        {"probe_id", "hypothesis_id", "candidate_runs", "empty_candidate_reason"},
        "PROBE_A",
    )
    if probe_a["hypothesis_id"] != "HYP-PORTFOLIO-COMPOSE-001":
        raise SpecValidationError("PROBE_A hypothesis_id is not frozen")
    if probe_a["candidate_runs"] != []:
        raise SpecValidationError(
            "PROBE_A candidate_runs must remain empty until an exact universe is frozen"
        )
    if (
        probe_a["empty_candidate_reason"]
        != "BLOCKED_PROBE_A_EXACT_UNIVERSE_NOT_FROZEN"
    ):
        raise SpecValidationError("PROBE_A empty-candidate reason is not frozen")

    probe_b = probes[1]
    if not isinstance(probe_b, dict):
        raise SpecValidationError("PROBE_B must be an object")
    _require_exact_keys(
        probe_b,
        {"probe_id", "hypothesis_id", "candidate_runs", "donor"},
        "PROBE_B",
    )
    if probe_b["hypothesis_id"] != "HYP-SB-WEEKEND-FLAT-001":
        raise SpecValidationError("PROBE_B hypothesis_id is not frozen")
    candidate_runs = probe_b["candidate_runs"]
    if not isinstance(candidate_runs, list) or not candidate_runs:
        raise SpecValidationError("PROBE_B candidate_runs must be a non-empty exact list")
    for index, candidate in enumerate(candidate_runs):
        _validate_exact_relative_path(candidate, f"PROBE_B candidate_runs[{index}]")
    if len(set(candidate_runs)) != len(candidate_runs) or candidate_runs != sorted(
        candidate_runs
    ):
        raise SpecValidationError("PROBE_B candidate_runs must be unique and sorted")
    if candidate_runs != ["EA_SilverBullet/20260628_131343"]:
        raise SpecValidationError("PROBE_B exact donor candidate is not frozen")

    donor = probe_b["donor"]
    if not isinstance(donor, dict):
        raise SpecValidationError("PROBE_B donor must be an object")
    _require_exact_keys(
        donor,
        {"run", "identity_manifests", "trade_header", "required_hash_bindings"},
        "PROBE_B donor",
    )
    _validate_exact_relative_path(donor["run"], "PROBE_B donor run")
    if donor["run"] not in candidate_runs:
        raise SpecValidationError("PROBE_B donor run must be in candidate_runs")

    manifests = donor["identity_manifests"]
    if not isinstance(manifests, list) or not manifests:
        raise SpecValidationError("identity_manifests must be a non-empty list")
    manifest_paths: list[str] = []
    for index, manifest in enumerate(manifests):
        if not isinstance(manifest, dict):
            raise SpecValidationError(f"identity_manifests[{index}] must be an object")
        _require_exact_keys(
            manifest, {"path", "expected_identity"}, f"identity_manifests[{index}]"
        )
        manifest_paths.append(
            _validate_exact_relative_path(
                manifest["path"], f"identity_manifests[{index}].path"
            )
        )
        expected_identity = manifest["expected_identity"]
        if not isinstance(expected_identity, dict):
            raise SpecValidationError("expected_identity must be an object")
        _require_exact_keys(
            expected_identity, set(IDENTITY_KEYS), f"identity_manifests[{index}] identity"
        )
    if len(set(manifest_paths)) != len(manifest_paths):
        raise SpecValidationError("identity manifest paths must be unique")

    trade_header = donor["trade_header"]
    if not isinstance(trade_header, dict):
        raise SpecValidationError("trade_header must be an object")
    _require_exact_keys(
        trade_header, {"path", "expected_header_sha256"}, "trade_header"
    )
    _validate_exact_relative_path(trade_header["path"], "trade_header.path")
    _validate_sha256(
        trade_header["expected_header_sha256"], "trade_header.expected_header_sha256"
    )

    bindings = donor["required_hash_bindings"]
    if not isinstance(bindings, list) or not bindings:
        raise SpecValidationError("required_hash_bindings must be a non-empty list")
    check_ids: list[str] = []
    blocked_reasons: list[str] = []
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            raise SpecValidationError(f"required_hash_bindings[{index}] must be an object")
        _require_exact_keys(
            binding,
            {
                "check_id",
                "manifest_path",
                "hash_field",
                "target_path",
                "blocked_reason",
            },
            f"required_hash_bindings[{index}]",
        )
        if not isinstance(binding["check_id"], str) or not binding["check_id"]:
            raise SpecValidationError("hash-binding check_id must be non-empty")
        check_ids.append(binding["check_id"])
        _validate_exact_relative_path(
            binding["manifest_path"], f"required_hash_bindings[{index}].manifest_path"
        )
        _validate_exact_relative_path(
            binding["target_path"], f"required_hash_bindings[{index}].target_path"
        )
        if not isinstance(binding["hash_field"], str) or HASH_FIELD_PATTERN.fullmatch(
            binding["hash_field"]
        ) is None:
            raise SpecValidationError("hash_field must name a SHA-256 binding field")
        reason = binding["blocked_reason"]
        if not isinstance(reason, str) or not reason.startswith("BLOCKED_PROBE_B_"):
            raise SpecValidationError("hash-binding blocked_reason is invalid")
        blocked_reasons.append(reason)
    if len(set(check_ids)) != len(check_ids):
        raise SpecValidationError("hash-binding check_id values must be unique")
    if len(set(blocked_reasons)) != len(blocked_reasons):
        raise SpecValidationError("hash-binding blocked reasons must be unique")

    actual_spec_sha256 = _canonical_json_sha256(spec)
    if actual_spec_sha256 != FROZEN_SPEC_SHA256:
        raise SpecValidationError(
            "spec does not match the frozen spec SHA-256; create a new spec version"
        )

    return spec


def _canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _join_posix(root: Path, relative: str) -> Path:
    path = root
    for part in PurePosixPath(relative).parts:
        path = path / part
    return path


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def _is_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath([_path_key(path), _path_key(root)]) == _path_key(root)
    except ValueError:
        return False


def _resolve_contained_path(
    root: Path,
    relative: str,
    *,
    require_exists: bool = False,
    require_directory: bool = False,
) -> Path:
    """Resolve one exact path without permitting drive, ADS, or reparse escape."""

    lexical = Path(os.path.abspath(_join_posix(root, relative)))
    try:
        resolved = lexical.resolve(strict=require_exists)
    except OSError as exc:
        raise ArtifactInspectionError(f"required exact path is missing: {lexical}") from exc
    if not _is_within(resolved, root):
        raise ArtifactInspectionError(f"exact path escapes its allowed root: {lexical}")
    if _path_key(resolved) != _path_key(lexical):
        raise ArtifactInspectionError(
            f"exact path traverses a symlink, junction, or reparse point: {lexical}"
        )
    if require_directory and not resolved.is_dir():
        raise ArtifactInspectionError(f"required exact directory is missing: {resolved}")
    return resolved


def _display_path(*parts: str) -> str:
    return str(PurePosixPath(*parts))


def _blocked_attestation(
    reference: dict[str, Any], reason: str, actual_sha256: str | None = None
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "BLOCKED",
        "review_status": "UNKNOWN",
        "input_path": reference["path"],
        "expected_input_sha256": reference["sha256"],
        "reasons": [reason],
    }
    if actual_sha256 is not None:
        result["actual_input_sha256"] = actual_sha256
    return result


def _load_coordination_attestation(
    reference: dict[str, Any], workspace_root: Path, filesystem: Any
) -> dict[str, Any]:
    path = _resolve_contained_path(workspace_root, reference["path"])
    if not filesystem.is_file(path):
        return _blocked_attestation(
            reference, "BLOCKED_COORDINATION_ATTESTATION_MISSING"
        )
    try:
        payload, actual_sha256 = filesystem.inspect_json_and_sha256(path)
    except (OSError, ArtifactInspectionError):
        return _blocked_attestation(
            reference, "BLOCKED_COORDINATION_ATTESTATION_UNREADABLE"
        )
    if actual_sha256 != reference["sha256"]:
        return _blocked_attestation(
            reference,
            "BLOCKED_COORDINATION_ATTESTATION_HASH_MISMATCH",
            actual_sha256,
        )

    required = {
        "schema_version",
        "attestation_id",
        "session_id",
        "review_status",
        "scope",
        "artifact_path",
        "artifact_sha256",
        "access_mode",
        "producer_semantic_outcome_accessed",
        "outcome_values_used",
        "reviewed_by",
        "reviewed_at",
        "clearance_effect",
    }
    if set(payload) != required:
        return _blocked_attestation(
            reference, "BLOCKED_COORDINATION_ATTESTATION_SCHEMA_MISMATCH", actual_sha256
        )
    scalar_fields = (
        "attestation_id",
        "session_id",
        "scope",
        "artifact_path",
        "access_mode",
        "reviewed_by",
        "reviewed_at",
        "clearance_effect",
    )
    if (
        payload.get("schema_version") != ATTESTATION_SCHEMA_VERSION
        or payload.get("review_status") not in {"CONTAMINATED", "CLEAN_REVIEWED"}
        or any(
            not isinstance(payload.get(field), str) or not payload[field]
            for field in scalar_fields
        )
        or not isinstance(payload.get("artifact_sha256"), str)
        or SHA256_PATTERN.fullmatch(payload["artifact_sha256"]) is None
        or payload.get("producer_semantic_outcome_accessed") is not False
        or payload.get("outcome_values_used") is not False
    ):
        return _blocked_attestation(
            reference, "BLOCKED_COORDINATION_ATTESTATION_INVALID", actual_sha256
        )
    try:
        _validate_exact_relative_path(
            payload["artifact_path"], "coordination attestation artifact_path"
        )
    except SpecValidationError:
        return _blocked_attestation(
            reference, "BLOCKED_COORDINATION_ATTESTATION_INVALID_PATH", actual_sha256
        )

    status = "PASS" if payload["review_status"] == "CLEAN_REVIEWED" else "BLOCKED"
    result = dict(payload)
    result.update(
        {
            "status": status,
            "input_path": reference["path"],
            "input_sha256": actual_sha256,
            "reasons": []
            if status == "PASS"
            else [payload["clearance_effect"]],
        }
    )
    return result


def _build_probe_a(probe: dict[str, Any]) -> dict[str, Any]:
    reason = probe["empty_candidate_reason"]
    return {
        "probe_id": probe["probe_id"],
        "hypothesis_id": probe["hypothesis_id"],
        "candidate_runs": [],
        "status": "BLOCKED",
        "reasons": [reason],
        "producer_semantic_outcome_accessed": False,
        "checks": [
            {
                "check_id": "exact_candidate_universe_frozen",
                "status": "BLOCKED",
                "candidate_count": 0,
                "blocked_reason": reason,
            }
        ],
    }


def _build_probe_b(
    probe: dict[str, Any],
    run_root: Path,
    header_max_bytes: int,
    filesystem: Any,
) -> dict[str, Any]:
    donor = probe["donor"]
    donor_run = donor["run"]
    donor_root = _resolve_contained_path(
        run_root,
        donor_run,
        require_exists=True,
        require_directory=True,
    )
    checks: list[dict[str, Any]] = []
    reasons: list[str] = []

    exists_cache: dict[str, bool] = {}
    hash_cache: dict[str, str] = {}
    json_cache: dict[str, tuple[dict[str, Any], str]] = {}
    header_cache: dict[str, tuple[bytes, str]] = {}
    binding_manifest_fields: dict[str, set[str]] = {}
    for binding in donor["required_hash_bindings"]:
        binding_manifest_fields.setdefault(binding["manifest_path"], set()).add(
            binding["hash_field"]
        )

    def exact_file(relative: str) -> Path:
        return _resolve_contained_path(donor_root, relative)

    def is_file(relative: str) -> bool:
        if relative not in exists_cache:
            exists_cache[relative] = filesystem.is_file(exact_file(relative))
        return exists_cache[relative]

    def file_hash(relative: str) -> str:
        if relative in json_cache:
            return json_cache[relative][1]
        if relative in header_cache:
            return header_cache[relative][1]
        if relative not in hash_cache:
            hash_cache[relative] = filesystem.sha256(exact_file(relative))
        return hash_cache[relative]

    def json_snapshot(relative: str) -> tuple[dict[str, Any], str]:
        if relative not in json_cache:
            json_cache[relative] = filesystem.inspect_json_and_sha256(
                exact_file(relative)
            )
        return json_cache[relative]

    def header_snapshot(relative: str) -> tuple[bytes, str]:
        if relative not in header_cache:
            header_cache[relative] = filesystem.inspect_header_and_sha256(
                exact_file(relative), header_max_bytes
            )
        return header_cache[relative]

    for manifest_spec in donor["identity_manifests"]:
        relative = manifest_spec["path"]
        display = _display_path(probe["candidate_runs"][0], relative)
        check: dict[str, Any] = {
            "check_id": f"identity_manifest:{relative}",
            "inspection": "IDENTITY_MANIFEST",
            "path": display,
        }
        if not is_file(relative):
            reason = f"BLOCKED_PROBE_B_IDENTITY_MANIFEST_MISSING:{relative}"
            check.update(
                {"status": "BLOCKED", "present": False, "blocked_reason": reason}
            )
            reasons.append(reason)
        else:
            manifest, manifest_sha256 = json_snapshot(relative)
            actual_identity = {key: manifest.get(key) for key in IDENTITY_KEYS}
            identity_matches = actual_identity == manifest_spec["expected_identity"]
            check.update(
                {
                    "present": True,
                    "sha256": manifest_sha256,
                    "identity": actual_identity,
                    "identity_matches": identity_matches,
                    "status": "PASS" if identity_matches else "BLOCKED",
                }
            )
            if not identity_matches:
                reason = f"BLOCKED_PROBE_B_IDENTITY_MANIFEST_MISMATCH:{relative}"
                check["blocked_reason"] = reason
                reasons.append(reason)
        checks.append(check)

    trade_header = donor["trade_header"]
    trade_relative = trade_header["path"]
    trade_display = _display_path(probe["candidate_runs"][0], trade_relative)
    trade_check: dict[str, Any] = {
        "check_id": "trade_header",
        "inspection": "CSV_HEADER_AND_SHA256",
        "path": trade_display,
    }
    if not is_file(trade_relative):
        reason = "BLOCKED_PROBE_B_TRADE_ARTIFACT_MISSING"
        trade_check.update(
            {"status": "BLOCKED", "present": False, "blocked_reason": reason}
        )
        reasons.append(reason)
    else:
        header_bytes, trade_sha256 = header_snapshot(trade_relative)
        header_sha256 = hashlib.sha256(header_bytes).hexdigest()
        header_matches = header_sha256 == trade_header["expected_header_sha256"]
        trade_check.update(
            {
                "present": True,
                "sha256": trade_sha256,
                "header_sha256": header_sha256,
                "header_matches": header_matches,
                "status": "PASS" if header_matches else "BLOCKED",
            }
        )
        if not header_matches:
            reason = "BLOCKED_PROBE_B_TRADE_HEADER_MISMATCH"
            trade_check["blocked_reason"] = reason
            reasons.append(reason)
    checks.append(trade_check)

    for binding in donor["required_hash_bindings"]:
        manifest_relative = binding["manifest_path"]
        target_relative = binding["target_path"]
        manifest_present = is_file(manifest_relative)
        target_present = is_file(target_relative)
        manifest_sha256: str | None = None
        bound_sha256: Any = None
        manifest_schema_matches: bool | None = None
        if manifest_present:
            manifest_payload, manifest_sha256 = json_snapshot(manifest_relative)
            manifest_schema_matches = set(manifest_payload) == binding_manifest_fields[
                manifest_relative
            ]
            if manifest_schema_matches:
                bound_sha256 = manifest_payload.get(binding["hash_field"])
        target_sha256 = file_hash(target_relative) if target_present else None
        hash_matches = bool(
            target_present
            and isinstance(bound_sha256, str)
            and SHA256_PATTERN.fullmatch(bound_sha256)
            and bound_sha256 == target_sha256
        )
        binding_check: dict[str, Any] = {
            "check_id": binding["check_id"],
            "inspection": "SHA256_BINDING",
            "manifest_path": _display_path(donor_run, manifest_relative),
            "manifest_present": manifest_present,
            "manifest_schema_matches": manifest_schema_matches,
            "hash_field": binding["hash_field"],
            "target_path": _display_path(donor_run, target_relative),
            "target_present": target_present,
            "hash_matches": hash_matches,
            "status": "PASS" if hash_matches else "BLOCKED",
        }
        if manifest_sha256 is not None:
            binding_check["manifest_sha256"] = manifest_sha256
        if target_sha256 is not None:
            binding_check["target_sha256"] = target_sha256
        if isinstance(bound_sha256, str):
            binding_check["bound_sha256"] = bound_sha256
        if not hash_matches:
            reason = binding["blocked_reason"]
            binding_check["blocked_reason"] = reason
            reasons.append(reason)
        checks.append(binding_check)

    return {
        "probe_id": probe["probe_id"],
        "hypothesis_id": probe["hypothesis_id"],
        "candidate_runs": list(probe["candidate_runs"]),
        "status": "BLOCKED" if reasons else "READY",
        "reasons": reasons,
        "producer_semantic_outcome_accessed": False,
        "checks": checks,
    }


def build_result(
    spec: dict[str, Any],
    workspace_root: Path | str,
    *,
    filesystem: Any | None = None,
) -> dict[str, Any]:
    """Build a result using only the exact paths frozen in ``spec``."""

    validated = validate_spec(spec)
    fs = filesystem if filesystem is not None else LocalFileSystem()
    try:
        root = Path(workspace_root).resolve(strict=True)
    except OSError as exc:
        raise ArtifactInspectionError(
            f"workspace root does not exist: {workspace_root}"
        ) from exc
    if not root.is_dir():
        raise ArtifactInspectionError(f"workspace root is not a directory: {root}")
    run_root = _resolve_contained_path(
        root,
        validated["run_root"],
        require_exists=True,
        require_directory=True,
    )
    attestation = _load_coordination_attestation(
        validated["coordination_session_attestation"], root, fs
    )
    probe_a = _build_probe_a(validated["probes"][0])
    probe_b = _build_probe_b(
        validated["probes"][1],
        run_root,
        validated["policy"]["header_max_bytes"],
        fs,
    )
    probes = [probe_a, probe_b]
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "as_of_date": validated["as_of_date"],
        "spec_sha256": _canonical_json_sha256(validated),
        "status": "BLOCKED"
        if attestation["status"] != "PASS"
        or any(probe["status"] == "BLOCKED" for probe in probes)
        else "READY",
        "producer_semantic_outcome_accessed": False,
        "coordination_session_attestation": attestation,
        "deterministic": True,
        "policy": {
            "candidate_selection": "EXACT_LIST_ONLY",
            "auto_discovery_used": False,
            "semantic_data_access": "FORBIDDEN",
            "inspections_performed": [
                "EXACT_PATH",
                "COORDINATION_ATTESTATION",
                "IDENTITY_MANIFEST",
                "CSV_HEADER",
                "SHA256",
            ],
        },
        "probes": probes,
    }


def render_result(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    with args.spec.open("r", encoding="utf-8") as handle:
        spec = json.load(handle)
    result = build_result(spec, args.workspace_root)
    args.output.write_text(render_result(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
