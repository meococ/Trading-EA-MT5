#!/usr/bin/env python3
"""Fail-closed validator for the frozen HYP008 random-100 chart artifact."""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
PKG = ROOT / "03. EA Developer" / "EA_VRAS_VolatilityNormalizedStop"
RESEARCH = PKG / "research"
EVIDENCE = RESEARCH / "evidence" / "HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100"
SELECTION_PATH = EVIDENCE / "selection_manifest.json"
CASES_PATH = EVIDENCE / "cases_random_100.csv"
MANIFEST_PATH = EVIDENCE / "chart_manifest.json"
DECISION_DIR = EVIDENCE / "charts" / "decision_asof"
ANATOMY_DIR = EVIDENCE / "charts" / "anatomy"
EXPECTED_SCHEMA = "vras_hyp008_random100_charts.v1"
EXPECTED_HYPOTHESIS = "HYP-VRAS-EURUSD-M5-008"
EXPECTED_RUN = "20260722_233420"
FORBIDDEN_DECISION_KEYS = {
    "label", "net_usd", "net_r", "exit_time_server", "exit_time_utc", "exit",
    "exact_exit_class", "exact_exit_comment", "active_stop_at_exit", "anatomy_path",
    "holding_minutes", "close_deal_id",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def fail(message: str) -> None:
    raise RuntimeError(message)


def workspace_path(path_text: str) -> Path:
    path = (ROOT / Path(path_text)).resolve()
    if ROOT.resolve() not in path.parents and path != ROOT.resolve():
        fail(f"Manifest path escapes workspace: {path_text}")
    return path


def load_cases() -> list[dict[str, str]]:
    with CASES_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(str(key) for key in value)
        for nested in value.values():
            keys.update(collect_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(collect_keys(nested))
    return keys


def renderer_case_fields(renderer: Path, functions: set[str]) -> set[str]:
    tree = ast.parse(renderer.read_text(encoding="utf-8"), filename=str(renderer))
    fields: set[str] = set()
    found: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name not in functions:
            continue
        found.add(node.name)
        for child in ast.walk(node):
            if not isinstance(child, ast.Subscript):
                continue
            if not isinstance(child.value, ast.Name) or child.value.id != "case":
                continue
            slice_node = child.slice
            if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                fields.add(slice_node.value)
    if found != functions:
        fail(f"Renderer source missing audited decision functions: {sorted(functions - found)}")
    return fields


def validate_png(path: Path, expected_contract: dict[str, Any], forbidden_tokens: list[str]) -> None:
    if not path.is_file():
        fail(f"Missing image: {path}")
    with Image.open(path) as image:
        if image.format != "PNG":
            fail(f"Not a PNG: {path}")
        if image.width < 2000 or image.height < 1200:
            fail(f"Image resolution too small: {path} {image.size}")
        image.verify()
    with Image.open(path) as image:
        description = image.info.get("Description")
        if not description:
            fail(f"PNG contract metadata missing: {path}")
        try:
            contract = json.loads(description)
        except json.JSONDecodeError as exc:
            fail(f"Invalid PNG contract metadata for {path}: {exc}")
        if contract != expected_contract:
            fail(f"PNG contract metadata mismatch: {path}")
        searchable = "\n".join(str(value) for value in image.info.values())
        for token in forbidden_tokens:
            if token and token in searchable:
                fail(f"Decision PNG metadata leaks forbidden token {token!r}: {path}")


def main() -> int:
    if not MANIFEST_PATH.is_file():
        fail(f"Missing chart manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    cases = load_cases()

    if manifest.get("schema_version") != EXPECTED_SCHEMA:
        fail("Chart manifest schema mismatch")
    if manifest.get("hypothesis_id") != EXPECTED_HYPOTHESIS or manifest.get("run_id") != EXPECTED_RUN:
        fail("Chart manifest hypothesis/run mismatch")
    if manifest.get("forensic_only") is not True:
        fail("Chart manifest must remain forensic_only")
    counts = (
        manifest.get("case_count"), manifest.get("image_count"),
        manifest.get("decision_image_count"), manifest.get("anatomy_image_count"),
    )
    if counts != (100, 200, 100, 100):
        fail(f"Manifest counts are not exact 100/200: {counts}")
    if len(cases) != 100 or selection.get("sample_size") != 100:
        fail("Frozen CSV/selection no longer contains exactly 100 cases")

    frozen_ids = selection.get("case_ids")
    frozen_positions = selection.get("position_ids")
    csv_ids = [case["case_id"] for case in cases]
    csv_positions = [int(case["position_id"]) for case in cases]
    if csv_ids != frozen_ids or csv_positions != frozen_positions:
        fail("CSV order differs from frozen selection")
    if manifest.get("case_ids") != frozen_ids or manifest.get("position_ids") != frozen_positions:
        fail("Chart manifest order differs from frozen selection")

    bindings = manifest.get("input_bindings", {})
    required_bindings = {
        "selection_manifest", "cases_csv", "run_manifest", "lifecycle", "decision_telemetry",
        "run_meta", "source", "tester_report", "bars_m1", "bars_h1", "renderer_source",
    }
    if not required_bindings.issubset(bindings):
        fail(f"Chart bindings missing: {sorted(required_bindings - set(bindings))}")
    for name in sorted(required_bindings):
        binding = bindings[name]
        path = workspace_path(binding["path"])
        if not path.is_file():
            fail(f"Missing bound input {name}: {path}")
        actual = sha256(path)
        if actual != binding["sha256"]:
            fail(f"Input hash mismatch {name}: {actual} != {binding['sha256']}")
    if bindings["selection_manifest"]["sha256"] != sha256(SELECTION_PATH):
        fail("Selection-manifest binding mismatch")
    if bindings["cases_csv"]["sha256"] != sha256(CASES_PATH):
        fail("Cases-CSV binding mismatch")

    decision_contract = manifest.get("decision_contract", {})
    if decision_contract.get("outcome_blind") is not True or decision_contract.get("post_entry_bars") != 0:
        fail("Decision contract is not outcome-blind/no-future")
    if set(decision_contract.get("forbidden", [])) != {
        "label", "net_usd", "net_r", "exit_time_server", "exit_time_utc", "exit",
        "exact_exit_class", "exact_exit_comment", "active_stop_at_exit", "anatomy_path",
    }:
        fail("Decision forbidden-field contract drifted")
    if decision_contract.get("exact_authority") != "ORDER_ACCEPTED_DECISION_TELEMETRY":
        fail("Decision exact authority drifted")
    if manifest.get("parity_summary", {}).get("status") != "PASS":
        fail("Exact parity summary is not PASS")

    renderer = workspace_path(bindings["renderer_source"]["path"])
    source_fields = renderer_case_fields(renderer, {"decision_diagnostics", "render_decision"})
    leaked_source_fields = source_fields & FORBIDDEN_DECISION_KEYS
    if leaked_source_fields:
        fail(f"Decision renderer reads forbidden outcome fields: {sorted(leaked_source_fields)}")

    records = manifest.get("cases", [])
    if len(records) != 100:
        fail(f"Manifest has {len(records)} case records, expected 100")
    record_ids = [record.get("case_id") for record in records]
    record_positions = [record.get("position_id") for record in records]
    if record_ids != frozen_ids or record_positions != frozen_positions:
        fail("Case records do not preserve frozen draw order")
    if len(set(record_ids)) != 100 or len(set(record_positions)) != 100:
        fail("Duplicate case/position record")

    csv_by_id = {case["case_id"]: case for case in cases}
    decision_ids: set[str] = set()
    anatomy_ids: set[str] = set()
    expected_decision_paths: set[Path] = set()
    expected_anatomy_paths: set[Path] = set()
    for index, record in enumerate(records, 1):
        case_id = record["case_id"]
        case = csv_by_id[case_id]
        if record.get("draw_index") != index:
            fail(f"Draw-index mismatch for {case_id}")
        if record.get("parity", {}).get("status") != "PASS":
            fail(f"Exact parity not PASS for {case_id}")
        decision = record.get("decision_asof", {})
        anatomy = record.get("anatomy", {})
        if decision.get("case_id") != case_id or anatomy.get("case_id") != case_id:
            fail(f"Decision/anatomy case mismatch for {case_id}")
        decision_ids.add(decision["case_id"])
        anatomy_ids.add(anatomy["case_id"])

        leaked_keys = collect_keys(decision) & FORBIDDEN_DECISION_KEYS
        if leaked_keys:
            fail(f"Decision manifest payload leaks outcomes for {case_id}: {sorted(leaked_keys)}")
        if decision.get("outcome_hidden") is not True or decision.get("post_entry_bars") != 0:
            fail(f"Decision future/outcome flags fail for {case_id}")
        entry = pd.Timestamp(decision["entry_time_server"])
        for key in ("latest_m5_bar_end_server", "latest_m15_bar_end_server", "latest_h1_bar_end_server"):
            if pd.Timestamp(decision[key]) > entry:
                fail(f"Decision chart includes a post-entry bar for {case_id}: {key}")
        diagnostic = decision.get("diagnostic", {})
        if diagnostic.get("computed_paths_status") != "NON_PARITY_DIAGNOSTIC":
            fail(f"Computed decision path not labelled diagnostic for {case_id}")
        if pd.Timestamp(diagnostic["signal_bar_end_server"]) > entry:
            fail(f"Trigger bar is not closed at entry for {case_id}")
        if decision.get("telemetry", {}).get("status") != "ORDER_ACCEPTED":
            fail(f"Decision telemetry is not ORDER_ACCEPTED for {case_id}")

        decision_path = workspace_path(decision["path"])
        anatomy_path = workspace_path(anatomy["path"])
        if decision_path.parent != DECISION_DIR.resolve() or anatomy_path.parent != ANATOMY_DIR.resolve():
            fail(f"Image path outside canonical chart folders for {case_id}")
        if decision_path.name != f"{case_id}_decision_asof.png":
            fail(f"Decision filename mismatch for {case_id}")
        if anatomy_path.name != f"{case_id}_anatomy.png":
            fail(f"Anatomy filename mismatch for {case_id}")
        if sha256(decision_path) != decision["sha256"] or sha256(anatomy_path) != anatomy["sha256"]:
            fail(f"Image hash mismatch for {case_id}")

        forbidden_png_tokens = [
            case.get("label", ""), case.get("exit_time_server", ""), case.get("exit_time_utc", ""),
            case.get("exact_exit_class", ""), case.get("exact_exit_comment", ""),
            anatomy_path.name,
        ]
        validate_png(decision_path, decision["png_contract"], forbidden_png_tokens)
        validate_png(anatomy_path, anatomy["png_contract"], [])
        expected_decision_paths.add(decision_path)
        expected_anatomy_paths.add(anatomy_path)

        if anatomy.get("exact_exit_class") != case["exact_exit_class"]:
            fail(f"Anatomy exact exit class mismatch for {case_id}")
        if anatomy.get("exact_exit_comment") != case["exact_exit_comment"]:
            fail(f"Anatomy exact exit comment mismatch for {case_id}")
        excursions = anatomy.get("excursions", {})
        if excursions.get("status") != "M1_OHLC_DIAGNOSTIC":
            fail(f"MFE/MAE provenance mismatch for {case_id}")
        if excursions.get("intraminute_first_passage") not in {
            "AMBIGUOUS_NOT_INFERRED", "NOT_REQUIRED_FROM_OHLC"
        }:
            fail(f"Invalid first-passage claim for {case_id}")

    if decision_ids != set(frozen_ids) or anatomy_ids != set(frozen_ids) or decision_ids != anatomy_ids:
        fail("Decision/anatomy case union is not the exact frozen 100")
    actual_decisions = {path.resolve() for path in DECISION_DIR.glob("*.png")}
    actual_anatomy = {path.resolve() for path in ANATOMY_DIR.glob("*.png")}
    if actual_decisions != expected_decision_paths:
        fail("Decision folder coverage has missing or extra PNGs")
    if actual_anatomy != expected_anatomy_paths:
        fail("Anatomy folder coverage has missing or extra PNGs")
    if len(actual_decisions | actual_anatomy) != 200:
        fail("Image union is not exactly 200 unique PNGs")

    print(json.dumps({
        "status": "HYP008_RANDOM100_CHARTS_VALID",
        "manifest": MANIFEST_PATH.resolve().relative_to(ROOT.resolve()).as_posix(),
        "manifest_sha256": sha256(MANIFEST_PATH),
        "case_count": 100,
        "image_count": 200,
        "decision_outcome_leakage": "PASS_STATIC_SOURCE_AND_PNG_METADATA_CONTRACT",
        "exact_case_union": "PASS",
        "hash_revalidation": "PASS",
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"HYP008_RANDOM100_VALIDATE_FAIL: {exc}", file=sys.stderr)
        raise
