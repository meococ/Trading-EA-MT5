#!/usr/bin/env python3
"""Run frozen HYP009 source quality using the reviewed HYP007 foundation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any


HYPOTHESIS_ID = "HYP-EVENT-AGGFLOW-EURUSD-TICK-009"
ATTEMPT_ID = "EVENTAGGFLOW009-SOURCE-QUALITY-001"
PARENT_HYPOTHESIS_ID = "HYP-EVENT-AGGFLOW-EURUSD-TICK-008"
PARENT_ACQUISITION_ID = "EVENTAGGFLOW008-TRADES-DESIGN-SOURCE-001"
BASE_REL = "03. EA Developer/EA_EventAggressorFlow/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_QUALITY_PLAN.md"
AUTHORITY_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_AUTHORITY.json"
TOOL_REL = BASE_REL + "build_event_aggflow_009_source_quality.py"
TEST_REL = BASE_REL + "tests/test_build_event_aggflow_009_source_quality.py"
FOUNDATION_REL = BASE_REL + "build_event_aggflow_007_source_quality.py"
PARENT_ROOT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_aggflow/"
    f"{PARENT_HYPOTHESIS_ID}/{PARENT_ACQUISITION_ID}"
)
OUTPUT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
PLAN_SHA256 = "19BC99CCF44A2730A0986BA867640187A54DFD0CC7602BB3E066B5827938003E"
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
    spec = importlib.util.spec_from_file_location("event_aggflow_009_foundation", path)
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

    def validate_hyp009_parent(
        source_workspace: Path, authority: dict[str, Any]
    ) -> dict[str, Any]:
        parent = original_validate_parent(source_workspace, authority)
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
        if manifest.get("manual_retry_evt0081_calls") != 1:
            raise module.SourceQualityError("parent manual EVT0081 retry provenance mismatch")
        if manifest.get("inherited_parent_paid_timeseries_calls") != 80:
            raise module.SourceQualityError("parent inherited-file provenance mismatch")
        if receipt.get("manual_retry_evt0081_calls") != 1:
            raise module.SourceQualityError("parent receipt retry provenance mismatch")
        launch = root / "detached_launch_receipt.json"
        if not launch.is_file():
            raise module.SourceQualityError("parent detached launch receipt is absent")
        if authority.get("parent_detached_launch_receipt_sha256") != sha256_file(launch):
            raise module.SourceQualityError("parent detached launch receipt drifted")
        return parent

    module.validate_parent = validate_hyp009_parent
    return module


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    if sha256_file(workspace / PLAN_REL) != PLAN_SHA256:
        raise WrapperError("HYP009 plan drifted")
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
            "EVENTAGGFLOW009_SOURCE_QUALITY_OK "
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
            f"EVENTAGGFLOW009_SOURCE_QUALITY_BLOCKED "
            f"reason={type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
