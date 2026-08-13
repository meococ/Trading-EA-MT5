

#!/usr/bin/env python3
"""Run frozen HYP012 source quality using the reviewed HYP007 foundation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any


HYPOTHESIS_ID = "HYP-EVENT-AGGFLOW-EURUSD-TICK-012"
ATTEMPT_ID = "EVENTAGGFLOW012-SOURCE-QUALITY-001"
PARENT_HYPOTHESIS_ID = "HYP-EVENT-AGGFLOW-EURUSD-TICK-010"
PARENT_ACQUISITION_ID = "EVENTAGGFLOW010-TRADES-DESIGN-SOURCE-001"
BASE_REL = "03. EA Developer/EA_EventAggressorFlow/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_QUALITY_PLAN.md"
AUTHORITY_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_AUTHORITY.json"
TOOL_REL = BASE_REL + "build_event_aggflow_012_source_quality.py"
TEST_REL = BASE_REL + "tests/test_build_event_aggflow_012_source_quality.py"
FOUNDATION_REL = BASE_REL + "build_event_aggflow_007_source_quality.py"
PARENT_ROOT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_aggflow/"
    f"{PARENT_HYPOTHESIS_ID}/{PARENT_ACQUISITION_ID}"
)
OUTPUT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
PLAN_SHA256 = "D405EDD53B3CED1E13BC475A7EDFEC404F6842C6EA3951A6EC19E7FE7675CD4E"
FOUNDATION_SHA256 = "427D453D54D921493DECC148219404907F80FFD209C957E2803543810B5A1EC0"
OWNER_CEILING_USD = 1.0


class WrapperError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def load_foundation(workspace: Path) -> Any:
    path = (workspace / FOUNDATION_REL).resolve()
    if sha256_file(path) != FOUNDATION_SHA256:
        raise WrapperError("reviewed HYP007 source foundation drifted")
    spec = importlib.util.spec_from_file_location("event_aggflow_012_foundation", path)
    if spec is None or spec.loader is None:
        raise WrapperError("cannot load source-quality foundation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    overrides = {
        "HYPOTHESIS_ID": HYPOTHESIS_ID,
        "ATTEMPT_ID": ATTEMPT_ID,
        "PARENT_HYPOTHESIS_ID": PARENT_HYPOTHESIS_ID,
        "PARENT_ACQUISITION_ID": PARENT_ACQUISITION_ID,
        "PLAN_REL": PLAN_REL,
        "AUTHORITY_REL": AUTHORITY_REL,
        "TOOL_REL": TOOL_REL,
        "TEST_REL": TEST_REL,
        "PARENT_ROOT_REL": PARENT_ROOT_REL,
        "OUTPUT_REL": OUTPUT_REL,
        "PLAN_SHA256": PLAN_SHA256,
    }
    for key, value in overrides.items():
        setattr(module, key, value)

    original_validate_parent = module.validate_parent

    def validate_hyp012_parent(
        source_workspace: Path, authority: dict[str, Any]
    ) -> dict[str, Any]:
        root = module.require_d(
            source_workspace / module.PARENT_ROOT_REL, "parent acquisition root"
        )
        plan_path = root / "acquisition_plan.json"
        manifest_path = root / "download_manifest.json"
        receipt_path = root / "paid_acquisition_receipt.json"
        for path, key in (
            (plan_path, "parent_live_plan_sha256"),
            (manifest_path, "parent_download_manifest_sha256"),
            (receipt_path, "parent_paid_acquisition_receipt_sha256"),
        ):
            if not path.is_file() or sha256_file(path) != authority.get(key):
                raise module.SourceQualityError(f"parent artifact drift: {key}")
        plan = module.load_json(plan_path, "parent live plan")
        manifest = module.load_json(manifest_path, "parent download manifest")
        receipt = module.load_json(receipt_path, "parent paid acquisition receipt")
        windows = plan.get("windows")
        downloads = manifest.get("downloads")
        empties = manifest.get("source_empty_windows")
        if (
            plan.get("hypothesis_id") != module.PARENT_HYPOTHESIS_ID
            or plan.get("acquisition_id") != module.PARENT_ACQUISITION_ID
            or plan.get("dataset") != module.DATASET
            or plan.get("schema") != module.SCHEMA
            or plan.get("symbol") != module.SYMBOL
            or plan.get("request_count") != module.EXPECTED_EVENTS
            or float(plan.get("live_estimated_total_usd")) > OWNER_CEILING_USD
            or not isinstance(windows, list)
            or len(windows) != module.EXPECTED_EVENTS
            or manifest.get("status") != "DOWNLOADED_RAW_SOURCE_QUALITY_REQUIRED"
            or manifest.get("coverage_count") != module.EXPECTED_EVENTS
            or manifest.get("in_flight") is not None
            or not isinstance(downloads, list)
            or not isinstance(empties, list)
            or len(downloads) + len(empties) != module.EXPECTED_EVENTS
            or receipt.get("status") != "COMPLETE_RAW_SOURCE_QUALITY_REQUIRED"
        ):
            raise module.SourceQualityError("parent terminal acquisition contract mismatch")
        if (
            plan.get("source_transform_authorized") is not False
            or plan.get("outcome_prices_authorized") is not False
            or plan.get("validation_source_authorized") is not False
            or manifest.get("outcome_fields_used") is not False
            or manifest.get("price_data_read") is not False
            or manifest.get("validation_source_read") is not False
            or receipt.get("outcome_fields_used") is not False
            or receipt.get("price_data_read") is not False
            or receipt.get("validation_source_read") is not False
        ):
            raise module.SourceQualityError("parent outcome/validation boundary opened")
        identities = [item.get("request_id") for item in windows]
        if identities != sorted(identities) or len(set(identities)) != module.EXPECTED_EVENTS:
            raise module.SourceQualityError("parent live identities invalid")
        parent = {
            "root": root,
            "raw": (root / "raw").resolve(),
            "plan": plan,
            "manifest": manifest,
            "receipt": receipt,
            "windows": {item["request_id"]: item for item in windows},
            "plan_path": plan_path,
            "manifest_path": manifest_path,
            "receipt_path": receipt_path,
        }
        root = Path(parent["root"])
        plan = parent["plan"]
        manifest = parent["manifest"]
        receipt = parent["receipt"]
        worst_values = (
            plan.get("worst_case_aggregate_usd"),
            manifest.get("worst_case_aggregate_usd"),
            receipt.get("worst_case_aggregate_usd"),
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) > OWNER_CEILING_USD
            for value in worst_values
        ):
            raise module.SourceQualityError("parent worst-case Owner ceiling mismatch")
        if (root / ".paid_acquisition.lock").exists():
            raise module.SourceQualityError("parent acquisition lock still exists")
        partials = list((root / "raw").glob("*.partial")) + list(
            (root / "raw").glob("*.inherit")
        )
        if partials:
            raise module.SourceQualityError("parent raw root has partial files")
        if manifest.get("manual_retry_recovery_request_calls") != 1:
            raise module.SourceQualityError("parent manual EVT0081 retry provenance mismatch")
        if manifest.get("inherited_parent_paid_timeseries_calls") != 265:
            raise module.SourceQualityError("parent inherited-file provenance mismatch")
        if receipt.get("manual_retry_recovery_request_calls") != 1:
            raise module.SourceQualityError("parent receipt retry provenance mismatch")
        if manifest.get("inherited_parent_source_empty_windows") != 2:
            raise module.SourceQualityError("parent inherited zero-byte provenance mismatch")
        if plan.get("source_condition_caveat") != (
            "GLBX.MDP3_2020-02-28_DEGRADED_EVT0198_408_RECORDS"
        ):
            raise module.SourceQualityError("parent inherited condition caveat mismatch")
        if plan.get("source_condition_caveat_filter_authorized") is not False:
            raise module.SourceQualityError("parent condition filter boundary opened")
        launch = root / "detached_launch_receipt.json"
        stderr = root / "worker.stderr.log"
        if not launch.is_file() or not stderr.is_file():
            raise module.SourceQualityError("parent detached evidence is absent")
        if authority.get("parent_detached_launch_receipt_sha256") != sha256_file(launch):
            raise module.SourceQualityError("parent detached launch receipt drifted")
        if authority.get("parent_worker_stderr_sha256") != sha256_file(stderr):
            raise module.SourceQualityError("parent worker stderr drifted")
        warning = stderr.read_text(encoding="utf-8")
        if "2020-07-01 (degraded)" not in warning or "BentoServerError" in warning:
            raise module.SourceQualityError("parent terminal condition-warning contract mismatch")
        return parent

    module.validate_parent = validate_hyp012_parent
    return module


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    if sha256_file(workspace / PLAN_REL) != PLAN_SHA256:
        raise WrapperError("HYP012 plan drifted")
    foundation = load_foundation(workspace)
    return foundation.execute(workspace)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        summary_path = execute(args.workspace.resolve())
        summary = json.loads(summary_path.read_text(encoding="ascii"))
        print(
            "EVENTAGGFLOW012_SOURCE_QUALITY_OK "
            f"pass={summary['source_feasibility_pass']} "
            f"events={summary['event_count']} "
            f"direct={summary['events_with_direct_side']} "
            f"nonzero={summary['nonzero_signed_flow_events']} "
            f"buy={summary['buyer_dominant_events']} "
            f"sell={summary['seller_dominant_events']}"
        )
        print(f"SUMMARY {summary_path}")
        return 0
    except (WrapperError, Exception) as exc:
        print(
            f"EVENTAGGFLOW012_SOURCE_QUALITY_BLOCKED "
            f"reason={type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
