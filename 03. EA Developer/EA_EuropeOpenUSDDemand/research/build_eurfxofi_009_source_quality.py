#!/usr/bin/env python3
"""One-shot HYP009 source-quality runner over HYP006 ``raw/`` DBN files."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-009"
PARENT_ID = "HYP-EURFXOFI-EURUSD-M1-006"
ATTEMPT_ID = "EURFXOFI009-SOURCE-QUALITY-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXOFI-EURUSD-M1-009_SOURCE_QUALITY_PLAN.md"
BUILDER_REL = BASE_REL + "build_eurfxofi_009_source_quality.py"
TEST_REL = BASE_REL + "tests/test_build_eurfxofi_009_source_quality.py"
V1_BUILDER_REL = BASE_REL + "build_eurfxofi_007_source_quality.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
LEDGER_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-002/EURFXOFI002-SIGNAL-DATE-SELECTION-001/"
    "signal_dates.jsonl"
)
SOURCE_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-006/EURFXOFI006-TBBO-SOURCE-001"
)
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-009/EURFXOFI009-SOURCE-QUALITY-001"
)
EVIDENCE_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
PLAN_SHA256 = "54930B9CAE0CAE8358378696D9D7D95B5F497B33AAF5B8DE5E6A16C64CE0A080"
V1_BUILDER_SHA256 = "FA221857CE4060015E9D5FDF0DAD560183A69B52045AA2A1C964F45BDF3F3E17"
LEDGER_SHA256 = "EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF"
PARENT_MANIFEST_SHA256 = "C2FA31D39970200DD05AF35A3E23BAE3941F1083BE870D77A4A24E4A709DF820"
FINAL_PARENT_STATUS = "DOWNLOADED_RAW_SOURCE_QUALITY_REQUIRED"
FEATURE_NAME = "source_features.parquet"
SUMMARY_NAME = "source_quality_summary.json"
ARTIFACT_MANIFEST_NAME = "artifact_manifest.json"
READOUT_NAME = "HYP-EURFXOFI-EURUSD-M1-009_SOURCE_QUALITY_READOUT.md"


REVIEWED_REGISTRY_ROW_SHA256: str | None = "2797EDD1B01E6F10DE5736969FA27C0395D3215B0BB5F1E033D377ED0A46CE94"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class SourceQualityError(RuntimeError):
    """Fail-closed source-quality authority or execution error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def workspace() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise SourceQualityError(f"{label} must stay on D:, got {resolved}")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def normalized_builder_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [
        index
        for index, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise SourceQualityError("builder must contain exactly one review sentinel")
    index = matches[0]
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_bytes(canonical_json(payload) + b"\n")
    os.replace(temp, path)


def load_v1(root: Path) -> Any:
    path = root / V1_BUILDER_REL
    if not path.is_file() or sha256_file(path) != V1_BUILDER_SHA256:
        raise SourceQualityError("hash-bound HYP007 transformation foundation mismatch")
    spec = importlib.util.spec_from_file_location("eurfxofi009_v1_foundation", path)
    if spec is None or spec.loader is None:
        raise SourceQualityError("cannot load HYP007 transformation foundation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.HYPOTHESIS_ID = HYPOTHESIS_ID
    module.PLAN_REL = PLAN_REL
    module.TOOL_REL = BUILDER_REL
    module.LEDGER_REL = LEDGER_REL
    module.SOURCE_REL = SOURCE_REL
    module.OUTPUT_REL = OUTPUT_REL
    module.PLAN_SHA256 = PLAN_SHA256
    module.LEDGER_SHA256 = LEDGER_SHA256
    module.FINAL_PARENT_STATUS = FINAL_PARENT_STATUS
    module.READOUT_NAME = READOUT_NAME
    return module


def latest_registry_row(path: Path, hypothesis_id: str) -> tuple[dict[str, Any], bytes]:
    latest: tuple[dict[str, Any], bytes] | None = None
    for raw in path.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == hypothesis_id:
            latest = (row, raw + b"\n")
    if latest is None:
        raise SourceQualityError(f"registry missing {hypothesis_id}")
    return latest


def raw_payload_root(source_root: Path) -> Path:
    return source_root / "raw"


def verify_authority(root: Path) -> dict[str, str]:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise SourceQualityError("registry sentinel is not armed")
    plan = root / PLAN_REL
    builder = root / BUILDER_REL
    test = root / TEST_REL
    ledger = root / LEDGER_REL
    parent_manifest = root / SOURCE_REL / "download_manifest.json"
    for label, path in (
        ("plan", plan),
        ("builder", builder),
        ("test", test),
        ("ledger", ledger),
        ("parent manifest", parent_manifest),
    ):
        if not path.is_file():
            raise SourceQualityError(f"missing {label}: {path}")
    bindings = {
        "plan": (plan, PLAN_SHA256),
        "ledger": (ledger, LEDGER_SHA256),
        "parent_manifest": (parent_manifest, PARENT_MANIFEST_SHA256),
    }
    for label, (path, expected) in bindings.items():
        actual = sha256_file(path)
        if actual != expected:
            raise SourceQualityError(f"{label} SHA mismatch: {actual}")
    payload = builder.read_bytes()
    base_hash = normalized_builder_base_sha256(payload)
    test_hash = sha256_file(test)
    registry = root / REGISTRY_REL
    row, raw = latest_registry_row(registry, HYPOTHESIS_ID)
    row_hash = sha256_bytes(raw)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    if row_hash != REVIEWED_REGISTRY_ROW_SHA256:
        raise SourceQualityError("sentinel does not bind latest HYP009 row")
    if row.get("state") != "probe" or row.get("prereg_sha256") != PLAN_SHA256:
        raise SourceQualityError("HYP009 state/plan is not eligible")
    if validation.get("source_run_authorized") is not True:
        raise SourceQualityError("HYP009 source run is not authorized")
    if validation.get("source_build_authorized") is not False:
        raise SourceQualityError("HYP009 builder must be frozen before run")
    if validation.get("reviewed_builder_path") != BUILDER_REL:
        raise SourceQualityError("reviewed builder path mismatch")
    if validation.get("reviewed_builder_base_sha256") != base_hash:
        raise SourceQualityError("reviewed builder base SHA mismatch")
    if validation.get("reviewed_test_path") != TEST_REL or validation.get("reviewed_test_sha256") != test_hash:
        raise SourceQualityError("reviewed test binding mismatch")
    if int(metrics.get("source_runs_executed", -1)) != 0 or row.get("run_ids") != []:
        raise SourceQualityError("HYP009 one-shot attempt already consumed")
    for key in (
        "economics_authorized",
        "performance_metrics_authorized",
        "post_entry_price_projection_authorized",
        "mql5_authorized",
        "model0_authorized",
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
        "network_authorized",
        "paid_requests_authorized",
    ):
        if validation.get(key) is not False:
            raise SourceQualityError(f"forbidden authority open: {key}")
    parent, _ = latest_registry_row(registry, PARENT_ID)
    parent_validation = parent.get("validation", {})
    if parent.get("state") != "parked" or parent_validation.get("final_manifest_sha256") != PARENT_MANIFEST_SHA256:
        raise SourceQualityError("HYP006 terminal manifest is not registry-bound")
    return {
        "registry_row_sha256": row_hash,
        "builder_base_sha256": base_hash,
        "builder_file_sha256": sha256_bytes(payload),
        "test_sha256": test_hash,
    }


def extract() -> Path:
    import pandas as pd

    root = workspace()
    authority = verify_authority(root)
    v1 = load_v1(root)
    source_root = require_d(root / SOURCE_REL, "source root")
    raw_root = require_d(raw_payload_root(source_root), "raw payload root")
    output_root = require_d(root / OUTPUT_REL, "output root")
    evidence_root = require_d(root / EVIDENCE_REL, "evidence root")
    if evidence_root.exists():
        raise SourceQualityError(f"one-shot evidence root exists: {evidence_root}")
    if output_root.exists() and any(output_root.iterdir()):
        raise SourceQualityError(f"one-shot output root is not empty: {output_root}")
    if not raw_root.is_dir():
        raise SourceQualityError(f"exact raw payload directory missing: {raw_root}")
    evidence_root.mkdir(parents=True)
    started = evidence_root / "attempt_started.json"
    write_new(
        started,
        canonical_json(
            {
                "schema_version": "eurfxofi009_attempt_started.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "started_at_utc": utc_now(),
                "plan_sha256": PLAN_SHA256,
                "parent_manifest_sha256": PARENT_MANIFEST_SHA256,
                "registry_row_sha256": authority["registry_row_sha256"],
                "builder_base_sha256": authority["builder_base_sha256"],
                "builder_file_sha256": authority["builder_file_sha256"],
                "test_sha256": authority["test_sha256"],
                "raw_subdirectory": "raw",
                "outcome_fields_used": False,
            }
        )
        + b"\n",
    )
    manifest_path = source_root / "download_manifest.json"
    manifest = v1.load_json(manifest_path)
    ledger = v1.load_ledger(root / LEDGER_REL)
    specs = v1.reconcile_manifest(manifest, ledger, raw_root)
    output_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(specs, 1):
        if item.source_empty:
            rows.append(v1.empty_feature_row(item))
        else:
            if item.filename is None:
                raise SourceQualityError(f"populated spec missing filename: {item.request_id}")
            rows.append(v1.validate_and_decode_file(raw_root / item.filename, item))
        if index % 100 == 0:
            print(f"SOURCE_QUALITY_PROGRESS {index}/{len(specs)}", flush=True)
    frame = pd.DataFrame(rows).sort_values("local_date").reset_index(drop=True)
    summary = v1.source_summary(frame, manifest, PARENT_MANIFEST_SHA256)
    features_path = output_root / FEATURE_NAME
    temp_features = features_path.with_suffix(".parquet.tmp")
    frame.to_parquet(temp_features, index=False)
    os.replace(temp_features, features_path)
    v1.write_json_atomic(output_root / SUMMARY_NAME, summary)
    write_new(
        evidence_root / "extract_completed.json",
        canonical_json(
            {
                "schema_version": "eurfxofi009_extract_completed.v1",
                "completed_at_utc": utc_now(),
                "rows": len(frame),
                "decoded_records": summary["decoded_records"],
                "source_verdict": summary["verdict"],
                "features_sha256": sha256_file(features_path),
                "summary_sha256": sha256_file(output_root / SUMMARY_NAME),
                "outcome_fields_used": False,
            }
        )
        + b"\n",
    )
    print(
        f"EURFXOFI009_EXTRACT_{summary['verdict']} rows={len(frame)} "
        f"records={summary['decoded_records']} output={output_root}"
    )
    return output_root


def render() -> Path:
    root = workspace()
    authority = verify_authority(root)
    v1 = load_v1(root)
    output_root = require_d(root / OUTPUT_REL, "output root")
    evidence_root = require_d(root / EVIDENCE_REL, "evidence root")
    started = evidence_root / "attempt_started.json"
    extracted = evidence_root / "extract_completed.json"
    terminal = evidence_root / "source_quality_terminal.json"
    if not started.is_file() or not extracted.is_file() or terminal.exists():
        raise SourceQualityError("render stage evidence boundary invalid")
    v1.render()
    summary_path = output_root / SUMMARY_NAME
    features_path = output_root / FEATURE_NAME
    artifact_manifest_path = output_root / ARTIFACT_MANIFEST_NAME
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    verdict = (
        "PASS_SOURCE_QUALITY_HANDOFF_TO_FRESH_TRAIN_ECONOMICS"
        if summary.get("verdict") == "PASS_SOURCE_QUALITY"
        else "FAIL_SOURCE_QUALITY_INVALID"
    )
    terminal_payload = {
        "schema_version": "eurfxofi009_source_quality_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": utc_now(),
        "verdict": verdict,
        "engineering_valid": verdict.startswith("PASS_"),
        "economic_edge_evaluated": False,
        "outcome_fields_used": False,
        "plan_sha256": PLAN_SHA256,
        "parent_manifest_sha256": PARENT_MANIFEST_SHA256,
        "registry_row_sha256": authority["registry_row_sha256"],
        "builder_base_sha256": authority["builder_base_sha256"],
        "builder_file_sha256": authority["builder_file_sha256"],
        "test_sha256": authority["test_sha256"],
        "attempt_started_sha256": sha256_file(started),
        "extract_completed_sha256": sha256_file(extracted),
        "source_features_path": FEATURE_REL_PATH(),
        "source_features_sha256": sha256_file(features_path),
        "source_quality_summary_path": SUMMARY_REL_PATH(),
        "source_quality_summary_sha256": sha256_file(summary_path),
        "artifact_manifest_path": ARTIFACT_MANIFEST_REL_PATH(),
        "artifact_manifest_sha256": sha256_file(artifact_manifest_path),
        "metrics": summary,
        "forbidden_counters": {
            "network_calls": 0,
            "paid_requests": 0,
            "target_returns_read": 0,
            "economics_executed": False,
            "mt5_launches": 0,
            "mql5_files_created": 0,
            "model0_runs": 0,
            "orders_submitted": 0,
        },
    }
    write_new(terminal, canonical_json(terminal_payload) + b"\n")
    evidence_manifest = evidence_root / "artifact_binding.json"
    evidence_paths = [started, extracted, terminal]
    write_new(
        evidence_manifest,
        canonical_json(
            {
                "schema_version": "eurfxofi009_evidence_binding.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "generated_at_utc": utc_now(),
                "output_artifact_manifest_path": ARTIFACT_MANIFEST_REL_PATH(),
                "output_artifact_manifest_sha256": sha256_file(artifact_manifest_path),
                "evidence": [
                    {
                        "path": str(path.relative_to(root)).replace("\\", "/"),
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    }
                    for path in evidence_paths
                ],
            }
        )
        + b"\n",
    )
    print(f"EURFXOFI009_RENDER_OK verdict={verdict} output={output_root}")
    return terminal


def FEATURE_REL_PATH() -> str:
    return f"{OUTPUT_REL}/{FEATURE_NAME}"


def SUMMARY_REL_PATH() -> str:
    return f"{OUTPUT_REL}/{SUMMARY_NAME}"


def ARTIFACT_MANIFEST_REL_PATH() -> str:
    return f"{OUTPUT_REL}/{ARTIFACT_MANIFEST_NAME}"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("extract", "render"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = extract() if args.command == "extract" else render()
    except (SourceQualityError, Exception) as exc:
        print(f"EURFXOFI009_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
