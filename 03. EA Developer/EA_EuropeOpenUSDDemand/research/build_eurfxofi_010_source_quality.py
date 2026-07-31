#!/usr/bin/env python3
"""HYP010 source-quality runner preserving paid and live empty dates."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-010"
PARENT_ID = "HYP-EURFXOFI-EURUSD-M1-006"
ATTEMPT_ID = "EURFXOFI010-SOURCE-QUALITY-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXOFI-EURUSD-M1-010_SOURCE_QUALITY_PLAN.md"
BUILDER_REL = BASE_REL + "build_eurfxofi_010_source_quality.py"
TEST_REL = BASE_REL + "tests/test_build_eurfxofi_010_source_quality.py"
HYP009_BUILDER_REL = BASE_REL + "build_eurfxofi_009_source_quality.py"
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
    "HYP-EURFXOFI-EURUSD-M1-010/EURFXOFI010-SOURCE-QUALITY-001"
)
EVIDENCE_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
PLAN_SHA256 = "70C7A0095AFAB896C74286752A5FD4A3A75363F220507C7D4690C2418055AD84"
HYP009_BUILDER_SHA256 = "358E7050C187D72668F6277D34238FD159FE66D6F41B7057C934D4452654707E"
PARENT_MANIFEST_SHA256 = "C2FA31D39970200DD05AF35A3E23BAE3941F1083BE870D77A4A24E4A709DF820"
LEDGER_SHA256 = "EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF"
EXPECTED_FILES = 1356
EXPECTED_POSITIVE_FILES = 1338
EXPECTED_PAID_EMPTY = 18
EXPECTED_LIVE_EMPTY = 3
EXPECTED_ROWS = 1359
FEATURE_NAME = "source_features.parquet"
SUMMARY_NAME = "source_quality_summary.json"
ARTIFACT_MANIFEST_NAME = "artifact_manifest.json"
READOUT_NAME = "HYP-EURFXOFI-EURUSD-M1-010_SOURCE_QUALITY_READOUT.md"


REVIEWED_REGISTRY_ROW_SHA256: str | None = "93077A6631290AC687A61DD6BC3C42FDE7DEBBA29DCE5FC8881C9EA51CF691D3"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class SourceQualityError(RuntimeError):
    pass


def workspace() -> Path:
    return Path(__file__).resolve().parents[3]


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
    matches = [i for i, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
    if len(matches) != 1:
        raise SourceQualityError("builder must contain exactly one review sentinel")
    index = matches[0]
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise SourceQualityError(f"{label} must stay on D:, got {resolved}")
    return resolved


def load_hyp009(root: Path) -> Any:
    path = root / HYP009_BUILDER_REL
    if not path.is_file() or sha256_file(path) != HYP009_BUILDER_SHA256:
        raise SourceQualityError("HYP009 orchestration foundation hash mismatch")
    spec = importlib.util.spec_from_file_location("eurfxofi010_hyp009_foundation", path)
    if spec is None or spec.loader is None:
        raise SourceQualityError("cannot load HYP009 orchestration foundation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def latest_registry_row(path: Path, hypothesis_id: str) -> tuple[dict[str, Any], bytes]:
    latest: tuple[dict[str, Any], bytes] | None = None
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row.get("hypothesis_id") == hypothesis_id:
                latest = (row, raw + b"\n")
    if latest is None:
        raise SourceQualityError(f"registry missing {hypothesis_id}")
    return latest


def verify_authority(root: Path) -> dict[str, str]:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise SourceQualityError("registry sentinel is not armed")
    plan = root / PLAN_REL
    builder = root / BUILDER_REL
    test = root / TEST_REL
    ledger = root / LEDGER_REL
    manifest = root / SOURCE_REL / "download_manifest.json"
    expected = {
        plan: PLAN_SHA256,
        ledger: LEDGER_SHA256,
        manifest: PARENT_MANIFEST_SHA256,
    }
    for path, digest in expected.items():
        if not path.is_file() or sha256_file(path) != digest:
            raise SourceQualityError(f"authority binding mismatch: {path}")
    payload = builder.read_bytes()
    base_hash = normalized_builder_base_sha256(payload)
    test_hash = sha256_file(test)
    registry = root / REGISTRY_REL
    row, raw = latest_registry_row(registry, HYPOTHESIS_ID)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    row_hash = sha256_bytes(raw)
    if row_hash != REVIEWED_REGISTRY_ROW_SHA256:
        raise SourceQualityError("sentinel does not bind latest HYP010 row")
    if row.get("state") != "probe" or row.get("prereg_sha256") != PLAN_SHA256:
        raise SourceQualityError("HYP010 state/plan not eligible")
    if validation.get("source_run_authorized") is not True or validation.get("source_build_authorized") is not False:
        raise SourceQualityError("HYP010 one-shot source authority absent")
    if validation.get("reviewed_builder_path") != BUILDER_REL or validation.get("reviewed_builder_base_sha256") != base_hash:
        raise SourceQualityError("reviewed HYP010 builder binding mismatch")
    if validation.get("reviewed_test_path") != TEST_REL or validation.get("reviewed_test_sha256") != test_hash:
        raise SourceQualityError("reviewed HYP010 test binding mismatch")
    if metrics.get("source_runs_executed") != 0 or row.get("run_ids") != []:
        raise SourceQualityError("HYP010 attempt already consumed")
    for key in (
        "network_authorized",
        "paid_requests_authorized",
        "economics_authorized",
        "performance_metrics_authorized",
        "post_entry_price_projection_authorized",
        "mql5_authorized",
        "mt5_authorized",
        "model0_authorized",
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
    ):
        if validation.get(key) is not False:
            raise SourceQualityError(f"forbidden authority open: {key}")
    parent, _ = latest_registry_row(registry, PARENT_ID)
    if parent.get("state") != "parked" or parent.get("validation", {}).get("final_manifest_sha256") != PARENT_MANIFEST_SHA256:
        raise SourceQualityError("HYP006 terminal manifest binding absent")
    return {
        "registry_row_sha256": row_hash,
        "builder_base_sha256": base_hash,
        "builder_file_sha256": sha256_bytes(payload),
        "test_sha256": test_hash,
    }


def reconcile_manifest_010(
    v1: Any,
    manifest: dict[str, Any],
    ledger: dict[str, dict[str, str]],
    raw_root: Path,
    original_decode: Any,
) -> list[Any]:
    if manifest.get("status") != v1.FINAL_PARENT_STATUS or manifest.get("in_flight") not in (None, {}):
        raise SourceQualityError("parent manifest is not terminal")
    if manifest.get("outcome_fields_used") is not False:
        raise SourceQualityError("parent manifest opened outcomes")
    downloads = manifest.get("downloads", [])
    live_empty = manifest.get("source_empty_windows", [])
    paid_empty = [item for item in downloads if item.get("source_empty") is True]
    positive = [item for item in downloads if item.get("source_empty") is False]
    if (len(downloads), len(positive), len(paid_empty), len(live_empty)) != (
        EXPECTED_FILES,
        EXPECTED_POSITIVE_FILES,
        EXPECTED_PAID_EMPTY,
        EXPECTED_LIVE_EMPTY,
    ):
        raise SourceQualityError("terminal source-availability cardinality mismatch")
    specs: list[Any] = []
    seen_ids: set[str] = set()
    seen_files: set[str] = set()
    for item in downloads:
        request_id = str(item.get("request_id", ""))
        filename = str(item.get("filename", ""))
        if request_id not in ledger or request_id in seen_ids or not filename or filename in seen_files:
            raise SourceQualityError(f"unknown/duplicate paid identity: {request_id}")
        if str(item.get("local_date")) != ledger[request_id]["local_date"] or str(item.get("split")) != ledger[request_id]["split"]:
            raise SourceQualityError(f"paid date/split mismatch: {request_id}")
        source_empty = item.get("source_empty") is True
        records = int(item.get("records", -1))
        if source_empty != (records == 0):
            raise SourceQualityError(f"paid empty/record mismatch: {request_id}")
        spec = v1.WindowSpec(
            request_id=request_id,
            local_date=ledger[request_id]["local_date"],
            split=ledger[request_id]["split"],
            start=str(item.get("start")),
            end=str(item.get("end")),
            filename=filename,
            source_empty=source_empty,
            expected_bytes=int(item.get("bytes", -1)),
            expected_sha256=str(item.get("sha256", "")),
            expected_records=records,
        )
        if source_empty:
            original_decode(raw_root / filename, spec)
        specs.append(spec)
        seen_ids.add(request_id)
        seen_files.add(filename)
    for item in live_empty:
        request_id = str(item.get("request_id", ""))
        if request_id not in ledger or request_id in seen_ids:
            raise SourceQualityError(f"unknown/duplicate live-empty identity: {request_id}")
        specs.append(
            v1.WindowSpec(
                request_id=request_id,
                local_date=ledger[request_id]["local_date"],
                split=ledger[request_id]["split"],
                start=str(item.get("start")),
                end=str(item.get("end")),
                filename=None,
                source_empty=True,
                expected_bytes=0,
                expected_sha256=None,
                expected_records=0,
            )
        )
        seen_ids.add(request_id)
    if len(seen_ids) != EXPECTED_ROWS or seen_ids != set(ledger):
        raise SourceQualityError("manifest/ledger union mismatch")
    actual_files = {path.name for path in raw_root.glob("*.dbn.zst")}
    if actual_files != seen_files or list(raw_root.glob("*.partial")):
        raise SourceQualityError("raw file set or partial-file mismatch")
    return sorted(specs, key=lambda item: item.local_date)


def configure_foundations(root: Path) -> tuple[Any, Any]:
    hyp009 = load_hyp009(root)
    v1 = hyp009.load_v1(root)
    hyp009.HYPOTHESIS_ID = HYPOTHESIS_ID
    hyp009.PARENT_ID = PARENT_ID
    hyp009.ATTEMPT_ID = ATTEMPT_ID
    hyp009.PLAN_REL = PLAN_REL
    hyp009.BUILDER_REL = BUILDER_REL
    hyp009.TEST_REL = TEST_REL
    hyp009.LEDGER_REL = LEDGER_REL
    hyp009.SOURCE_REL = SOURCE_REL
    hyp009.OUTPUT_REL = OUTPUT_REL
    hyp009.EVIDENCE_REL = EVIDENCE_REL
    hyp009.PLAN_SHA256 = PLAN_SHA256
    hyp009.PARENT_MANIFEST_SHA256 = PARENT_MANIFEST_SHA256
    hyp009.LEDGER_SHA256 = LEDGER_SHA256
    hyp009.FEATURE_NAME = FEATURE_NAME
    hyp009.SUMMARY_NAME = SUMMARY_NAME
    hyp009.ARTIFACT_MANIFEST_NAME = ARTIFACT_MANIFEST_NAME
    hyp009.READOUT_NAME = READOUT_NAME
    hyp009.REVIEWED_REGISTRY_ROW_SHA256 = REVIEWED_REGISTRY_ROW_SHA256
    hyp009.verify_authority = verify_authority

    v1.HYPOTHESIS_ID = HYPOTHESIS_ID
    v1.PLAN_REL = PLAN_REL
    v1.TOOL_REL = BUILDER_REL
    v1.LEDGER_REL = LEDGER_REL
    v1.SOURCE_REL = SOURCE_REL
    v1.OUTPUT_REL = OUTPUT_REL
    v1.PLAN_SHA256 = PLAN_SHA256
    v1.LEDGER_SHA256 = LEDGER_SHA256
    v1.READOUT_NAME = READOUT_NAME
    original_decode = v1.validate_and_decode_file
    original_empty = v1.empty_feature_row
    original_summary = v1.source_summary
    original_render = v1.render

    def empty_row(spec: Any) -> dict[str, Any]:
        row = original_empty(spec)
        row["filename"] = spec.filename
        row["source_empty_kind"] = "paid_payload_empty" if spec.filename else "live_quote_empty"
        return row

    def decoded_row(path: Path, spec: Any) -> dict[str, Any]:
        row = original_decode(path, spec)
        row["source_empty_kind"] = "none"
        return row

    def reconcile(manifest: dict[str, Any], ledger: dict[str, dict[str, str]], raw_root: Path) -> list[Any]:
        return reconcile_manifest_010(v1, manifest, ledger, raw_root, original_decode)

    def summary(rows: Any, manifest: dict[str, Any], manifest_hash: str) -> dict[str, Any]:
        payload = original_summary(rows, manifest, manifest_hash)
        counts = {str(k): int(v) for k, v in rows.groupby("source_empty_kind").size().to_dict().items()}
        payload["source_empty_kind_counts"] = counts
        payload["positive_record_windows"] = counts.get("none", 0)
        payload["paid_payload_empty_windows"] = counts.get("paid_payload_empty", 0)
        payload["live_quote_empty_windows"] = counts.get("live_quote_empty", 0)
        payload["total_explicit_empty_windows"] = payload["paid_payload_empty_windows"] + payload["live_quote_empty_windows"]
        payload["gates"].update(
            {
                "exact_positive_record_windows": payload["positive_record_windows"] == EXPECTED_POSITIVE_FILES,
                "exact_paid_payload_empty_windows": payload["paid_payload_empty_windows"] == EXPECTED_PAID_EMPTY,
                "exact_live_quote_empty_windows": payload["live_quote_empty_windows"] == EXPECTED_LIVE_EMPTY,
            }
        )
        payload["verdict"] = "PASS_SOURCE_QUALITY" if all(payload["gates"].values()) else "FAIL_SOURCE_QUALITY_INVALID"
        return payload

    def render_with_empty_provenance() -> Path:
        output = original_render()
        _render_coverage_by_empty_kind(v1, root / OUTPUT_REL)
        artifact_paths = [
            root / OUTPUT_REL / FEATURE_NAME,
            root / OUTPUT_REL / SUMMARY_NAME,
            root / OUTPUT_REL / READOUT_NAME,
            *[root / OUTPUT_REL / name for name in v1.CHART_NAMES],
        ]
        v1.write_json_atomic(
            root / OUTPUT_REL / ARTIFACT_MANIFEST_NAME,
            {
                "schema_version": "eurfxofi010_artifact_manifest.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "generated_at_utc": v1.utc_now(),
                "outcome_fields_used": False,
                "artifacts": [
                    {
                        "path": str(path.relative_to(root)).replace("\\", "/"),
                        "bytes": path.stat().st_size,
                        "sha256": v1.sha256_file(path),
                    }
                    for path in artifact_paths
                ],
            },
        )
        return output

    v1.empty_feature_row = empty_row
    v1.validate_and_decode_file = decoded_row
    v1.reconcile_manifest = reconcile
    v1.source_summary = summary
    v1.render = render_with_empty_provenance
    hyp009.load_v1 = lambda _root: v1
    return hyp009, v1


def _render_coverage_by_empty_kind(v1: Any, output_root: Path) -> None:
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    frame = pd.read_parquet(output_root / FEATURE_NAME)
    frame["year"] = frame["local_date"].str[:4]
    counts = frame.groupby(["year", "source_empty_kind"]).size().unstack(fill_value=0)
    records = frame.groupby("year")["records"].sum()
    volume = frame.groupby("year")["total_volume"].sum()
    fig = make_subplots(rows=2, cols=2, subplot_titles=("Window provenance", "Decoded records", "Aggressive volume", "Explicit empty windows"))
    colors = {"none": "#1a9850", "paid_payload_empty": "#fdae61", "live_quote_empty": "#d73027"}
    for kind in ("none", "paid_payload_empty", "live_quote_empty"):
        values = counts[kind] if kind in counts else [0] * len(counts)
        fig.add_trace(go.Bar(x=counts.index, y=values, name=kind, marker_color=colors[kind]), row=1, col=1)
    fig.add_trace(go.Bar(x=records.index, y=records.values, name="records"), row=1, col=2)
    fig.add_trace(go.Bar(x=volume.index, y=volume.values, name="contracts"), row=2, col=1)
    empty = counts.get("paid_payload_empty", 0) + counts.get("live_quote_empty", 0)
    fig.add_trace(go.Bar(x=counts.index, y=empty, name="all empty"), row=2, col=2)
    fig.update_layout(barmode="stack", title=f"HYP010 source coverage and empty provenance | n={len(frame):,}")
    v1._write_plot(fig, output_root / "01_coverage_by_year.png")


def extract() -> Path:
    root = workspace()
    foundation, _ = configure_foundations(root)
    return foundation.extract()


def render() -> Path:
    root = workspace()
    foundation, _ = configure_foundations(root)
    foundation_terminal = foundation.render()
    evidence_root = root / EVIDENCE_REL
    final = evidence_root / "source_quality_terminal_hyp010.json"
    foundation_payload = json.loads(foundation_terminal.read_text(encoding="utf-8"))
    foundation_payload["schema_version"] = "eurfxofi010_source_quality_terminal.v1"
    foundation_payload["foundation_terminal_path"] = str(foundation_terminal.relative_to(root)).replace("\\", "/")
    foundation_payload["foundation_terminal_sha256"] = sha256_file(foundation_terminal)
    final.write_text(json.dumps(foundation_payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    binding = evidence_root / "artifact_binding_hyp010.json"
    binding.write_text(
        json.dumps(
            {
                "schema_version": "eurfxofi010_evidence_binding.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "outcome_fields_used": False,
                "terminal_path": str(final.relative_to(root)).replace("\\", "/"),
                "terminal_sha256": sha256_file(final),
                "output_artifact_manifest_path": f"{OUTPUT_REL}/{ARTIFACT_MANIFEST_NAME}",
                "output_artifact_manifest_sha256": sha256_file(root / OUTPUT_REL / ARTIFACT_MANIFEST_NAME),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"EURFXOFI010_RENDER_OK terminal={final}")
    return final


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("extract", "render"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = extract() if args.command == "extract" else render()
    except Exception as exc:
        print(f"EURFXOFI010_ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
