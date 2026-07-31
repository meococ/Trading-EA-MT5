#!/usr/bin/env python3
"""Plan, quote, and (only with later authority) acquire CME 6E event CLOB data.

``plan`` is offline. ``quote`` is metadata-only and uses only the free remote
methods frozen in the source task packet amendments. ``download`` is a future
operator command: it requires the exact immutable plan ID and a positive USD
ceiling, re-quotes every window before the first paid call, journals each paid
request as ``in_flight``, and never automatically retries an unresolved or
empty response.

This utility never reads EURUSD prices or economic outcomes. It reuses the
workspace's tested Databento key/client, atomic JSON, D-side root, and full DBN
validation helpers from the bounded SCC acquisition utility.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


SCHEMA_VERSION = "event_clob_cme6e_mbp10_acquisition.v1"
DESIGN_SCHEMA_VERSION = "event_clob_cme6e_mbp10_design_segments_acquisition.v1"
RECEIPT_SCHEMA_VERSION = "event_clob_cme6e_mbp10_metadata_quote_receipt.v1"
DESIGN_STORAGE_SCHEMA_VERSION = "event_clob_design_segment_storage_assessment.v1"
DESIGN_EVIDENCE_SCHEMA_VERSION = "event_clob_design_segment_quote_evidence.v1"
DOWNLOAD_SCHEMA_VERSION = "event_clob_cme6e_mbp10_download_manifest.v1"
HYPOTHESIS_ID = "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001"
DESIGN_HYPOTHESIS_ID = "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002"
PARENT_PROFILE = "parent-full-window"
DESIGN_SEGMENTS_PROFILE = "design-segments"
DATASET = "GLBX.MDP3"
SCHEMA = "mbp-10"
SYMBOL = "6E.v.0"
STYPE_IN = "continuous"
STYPE_OUT = "instrument_id"
COST_MODE = "historical-streaming"
DATABENTO_SDK_VERSION = "0.54.0"
EXPECTED_CLOCKS = 630
DESIGN_CLOCKS = 329
DESIGN_REQUESTS = 658
DESIGN_REQUESTED_SECONDS = 19_740
WINDOW_START_OFFSET_SECONDS = -60
WINDOW_END_OFFSET_SECONDS = 60

WORKSPACE = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
DATA_ROOT = WORKSPACE / "02. AlphaFactory" / "data"
DEFAULT_ROOT = DATA_ROOT / "databento" / "cme_6e_event_clob"
DESIGN_SEGMENTS_ROOT = (
    DATA_ROOT / "databento" / "cme_6e_event_clob_design_segments"
)
PLAN_NAME = "acquisition_plan.json"
QUOTE_RECEIPT_NAME = "metadata_quote_receipt.json"
DESIGN_QUOTE_RECEIPT_NAME = "quote_receipt.json"
DESIGN_STORAGE_ASSESSMENT_NAME = "storage_assessment.json"
DESIGN_FINALIZE_LOCK_NAME = ".design_quote_finalize.lock"
LIVE_REQUOTE_PLAN_NAME = "live_requote_plan.json"
LIVE_REQUOTE_RECEIPT_NAME = "live_requote_receipt.json"
ACQUISITION_AUTHORITY_RECEIPT_NAME = "acquisition_authority_receipt.json"
DOWNLOAD_MANIFEST_NAME = "download_manifest.json"
PAID_LOCK_NAME = ".event_clob_paid_download.lock"

REGISTRY_PATH = WORKSPACE / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
REGISTRY_VALIDATOR_PATH = (
    WORKSPACE / "04. Memory" / "research" / "validate_candidate_registry.py"
)
PROBE_PLAN_PATH = (
    PACKAGE / "research" / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001_PROBE_PLAN.md"
)
CLOCK_PATH = PACKAGE / "research" / "source" / "point_release_clocks_2019_2022.csv"
CLOCK_MANIFEST_PATH = (
    PACKAGE / "research" / "source" / "point_release_clock_manifest.json"
)
TASK_PACKET_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001_SOURCE_TASK_PACKET.json"
)
TASK_PACKET_V2_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001_SOURCE_TASK_PACKET_V2.json"
)
TASK_PACKET_V3_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001_SOURCE_TASK_PACKET_V3.json"
)
TASK_PACKET_V4_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001_SOURCE_TASK_PACKET_V4.json"
)
TASK_PACKET_V5_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001_SOURCE_TASK_PACKET_V5.json"
)
TASK_PACKET_V6_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001_SOURCE_TASK_PACKET_V6.json"
)
TASK_PACKET_V7_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001_SOURCE_TASK_PACKET_V7.json"
)
TASK_PACKET_V8_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001_SOURCE_TASK_PACKET_V8.json"
)
TASK_PACKET_V9_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-001_SOURCE_TASK_PACKET_V9.json"
)
TASK_PACKET_V10_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_SOURCE_TASK_PACKET_V10.json"
)
TASK_PACKET_V11_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_SOURCE_TASK_PACKET_V11.json"
)
TASK_PACKET_V12_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_SOURCE_TASK_PACKET_V12.json"
)
TASK_PACKET_V13_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_SOURCE_TASK_PACKET_V13.json"
)
TASK_PACKET_V14_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_SOURCE_TASK_PACKET_V14.json"
)
DESIGN_FAILURE_EVIDENCE_PATH = (
    PACKAGE
    / "research"
    / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_SOURCE_QUOTE_ATTEMPT_01_FAILURE.json"
)
DESIGN_PREREG_PATH = (
    PACKAGE / "research" / "HYP-EVENT-CLOB-PERSIST-EURUSD-M1-002_PROBE_PLAN.md"
)
FOUNDATION_PATH = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SweepCascadeContinuation"
    / "research"
    / "acquire_cme6e_mbp10_windows.py"
)

QUOTE_EVIDENCE_ROOT = (
    DEFAULT_ROOT / "evidence" / "FREE_QUOTE_F8CC5869"
)
QUOTE_EVIDENCE_MANIFEST_PATH = QUOTE_EVIDENCE_ROOT / "manifest.json"
DESIGN_QUOTE_EVIDENCE_ROOT = (
    DESIGN_SEGMENTS_ROOT / "evidence" / "FREE_QUOTE_DEDDE7F2"
)
DESIGN_QUOTE_EVIDENCE_MANIFEST_PATH = DESIGN_QUOTE_EVIDENCE_ROOT / "manifest.json"

REGISTRY_SHA256 = "C0C3BFA3328CBD83DC5335E06F774A3C3800A6418C4363A8A27F140F2DCC4739"
ORIGIN_ROW_SHA256 = "F120C70E6D8AEB1C7194D599E970721946C32DACFA2EEDA6BAE0C4B4B811FAA3"
PROBE_TRANSITION_ROW_SHA256 = "1859C425800FE94327AF4FE34D3D36769E4D3A4E063CE80E5F8814A87592F082"
LATEST_ROW_SHA256 = "15DAF05F86AAC2777925589ABE35725A274746A80C94F067A40FC333EB8643E3"
BOUND_EVENT_ROW_SHA256_SEQUENCE = (
    ORIGIN_ROW_SHA256,
    PROBE_TRANSITION_ROW_SHA256,
    LATEST_ROW_SHA256,
)
LATEST_STATE = "parked"
LATEST_VERDICT = "PARK_SOURCE_PAYMENT_AUTHORITY_UNMET"
HYPOTHESIS_ROW_SHA256 = ORIGIN_ROW_SHA256
PROBE_PLAN_SHA256 = "D47615E32F1E374D3CBFB23EA2DD9ABF594A85F2E22BF1C3CD5B08D60B6F5011"
CLOCK_SHA256 = "5C30F99FF0E1341D680C2747315E2FF4DFF99C5FBE01C2C5C4036BC101375E7B"
CLOCK_MANIFEST_SHA256 = "B61CDFA6DCAE82308E4CD2A60DAFF195C297FD8523D41CDCA0788694657AC636"
TASK_PACKET_SHA256 = "FB670F5C84772E531E13F3DBF6EDF06FB46856848925CDBC4B86224A9AC942EA"
TASK_PACKET_V2_SHA256 = "DC54B2CCA0C43F62C0B6A1B0C6239232B6892076BC13D70EBCCA1D294CE74D31"
TASK_PACKET_V3_SHA256 = "5BF086A0DACE26C898279D5D402135A2B92E18DC823D0A43DC6EB2A9085ED853"
TASK_PACKET_V4_SHA256 = "DB71C24864E01782BDB7F02D6DC46B2F54AC26EB38B11C0B9A0ACCF4079FDC74"
TASK_PACKET_V5_SHA256 = "9E3FA3B7A95376DF6098E79ED2BFCFAFAD863032AD9B52051888CF0873D74A75"
TASK_PACKET_V6_SHA256 = "B1B7A87200FAFAACD2BFFFB4A94C01D57534BE7DBE8D76CB6F86A8C4CF1F1009"
TASK_PACKET_V7_SHA256 = "9D8C118583108ABFEB719E82D805C41643447AD29284677EC6BBFA29B2193BD6"
TASK_PACKET_V8_SHA256 = "5208D76C2F95BE3BDD6E4C7EB4B44A769CA323936F6F4B6AE931CA6525E8A2CC"
TASK_PACKET_V9_SHA256 = "5B14A5CAA6DFBC888D5795F34A16B0D64FD50643898442C482A883A618D10578"
TASK_PACKET_V10_SHA256 = "2DED3AE4DE5DABF7D6FCF54F234E72BE2B8CAFC9FD410AEE30ECCE9C741CD161"
TASK_PACKET_V11_SHA256 = "715536B316414F674B7BAD13FE2744B2569F66C62034BE41FC2B07394BAF3764"
TASK_PACKET_V12_SHA256 = "81D2A9DD4016F29D2A4BDFC041633D179D4623C743F65773E1FDC70B22F450CC"
TASK_PACKET_V13_SHA256 = "63EEF71F0EF3747184DDC00B6179B6F6BD79BCBB30FA36292866146F6CAB9D7A"
TASK_PACKET_V14_SHA256 = "E752003D652DD1B204DAE2EEC84F0149DF89C70BC4C42C80C089D6CD923F730D"
DESIGN_FAILURE_EVIDENCE_SHA256 = "6B3863373881624467A720AC05E6708D0D8C07E851C6B66B3831E2429F473930"
DESIGN_PREREG_SHA256 = "62A3AB66C64083D9967D91A0D634DEF29641AE7F3A05D3C59CBC153AAF4B3CBF"
DESIGN_SUCCESSOR_ROW_SHA256_SEQUENCE = (
    "B352E22DE06889E3FDF139A7857CEAECB123944E42CDF1564C9CE3B54AF01F3D",
    "8B88B70C26060FF8A2A13F506990ADE3C6A27C2860C5618E51FBD77115B109CF",
    "AAE0F493502C13EB8C75C9105C83C6B6F325043D59BBB120075063401C907C45",
)
DESIGN_LATEST_STATE = "parked"
DESIGN_LATEST_VERDICT = "PARK_DESIGN_SOURCE_PAYMENT_AUTHORITY_UNMET"
FOUNDATION_SHA256 = "1F7E38F8326743206CEDE0AE3AEA8760B6C1C4590E4DD7D7E544058CB5A8E78A"
QUOTE_EVIDENCE_MANIFEST_SHA256 = "2AE3A6CE134653F452FBA62677A1141E0F561ED686028BF9C5940BB149EEAA71"
QUOTE_EVIDENCE_PLAN_ID = "F8CC58697DAF05713DCD4A4D0DDF1AA3DE9684A3DF646AE9C8F424F645851BDB"
QUOTE_EVIDENCE_CHILD_SHA256 = {
    "acquisition_plan.json": "969AD05FEC3F99D6219C8387F9BE3F7C1C5A44624816E3106ADFB2FD1716DDAB",
    "metadata_quote_receipt.json": "0CCF146D9C3E2DB0E7ABFE00BD3C405D59F2A46871985B2FCA8B0DD80AAC4107",
    "predownload_storage_assessment.json": "AAFF8417D6E58738E1A826595E8BABE256EFE6429B98658CA97429337AA09006",
}
DESIGN_QUOTE_EVIDENCE_MANIFEST_SHA256 = "9C9AFE1898BB6A9155D693F44DB704C5B8984775A593BE3213411BBDC1AFB5E5"
DESIGN_QUOTE_EVIDENCE_PLAN_ID = "DEDDE7F292738C16A200C59903F7839C85B728818805AA09D46D3E7F188E0C16"
DESIGN_QUOTE_EVIDENCE_CHILD_SHA256 = {
    "acquisition_plan.json": "F8924545E7A7F1DFD450AD683AB090DDF9F7334B6DC4B29E005A473025961015",
    "quote_receipt.json": "4B0F152F80C497C94651589606A97561CB289CC76E0A5E6CE7E99FCA963CC812",
    "storage_assessment.json": "822D30A4C9B05CA1FE256B01FE4936417CA5F9BA41C53253AED0B68FA6F0796E",
}
DESIGN_QUOTE_EVIDENCE_TOTALS = {
    "requests": 658,
    "estimated_total_usd": 3.141317501659,
    "estimated_total_billable_bytes": 6_745_927_968,
    "metadata_get_cost_attempts": 658,
    "metadata_get_billable_size_attempts": 658,
    "timeseries_calls": 0,
    "paid_request_made": False,
}
HISTORICAL_DESIGN_REGISTRY_SHA256 = "824EA0DB704443B12D6FA52C0E3F2E1F549BEAE9BB07F98A1958AC7F72E6FDE0"
HISTORICAL_DESIGN_ROW_SHA256_SEQUENCE = DESIGN_SUCCESSOR_ROW_SHA256_SEQUENCE[:2]
HISTORICAL_DESIGN_TOOL_SHA256 = "AAE2FFCFDBEEA06CB759D6F36458EF36194073D942BDA2A94342A45FC2574BDE"
DESIGN_APPROVED_MAX_USD = 3.5
OWNER_AUTHORIZATION_VERBATIM_SHA256 = "F77ECBE11D07A84E3B1A1112FC93AB7992720815EBC1B9C34ED874A86E4A89A0"
DESIGN_CAPACITY_RESERVE_BYTES = 1_073_741_824
V14_REGISTRY_PREFIX_ROWS = 272
V14_REGISTRY_PREFIX_SHA256 = "C0C3BFA3328CBD83DC5335E06F774A3C3800A6418C4363A8A27F140F2DCC4739"
V14_REGISTRY_CONFLICT_TOKENS = (
    "HYP-EVENT-CLOB",
    "EA_EventCLOBPersistence",
    "EVENT-CLOB",
    "event_clob",
    "cme_6e_event_clob_design_segments",
    DESIGN_QUOTE_EVIDENCE_PLAN_ID,
    DESIGN_LATEST_VERDICT,
)
_V14_VALIDATOR_PASS_BY_REGISTRY_SHA256: dict[str, str] = {}

FREE_METADATA_RETRY_METHODS = (
    "metadata.get_cost",
    "metadata.get_billable_size",
)
FREE_METADATA_TRANSIENT_HTTP_STATUSES = (429, 500, 502, 503, 504)
FREE_METADATA_MAX_ATTEMPTS = 3
FREE_METADATA_RETRY_BACKOFF_SECONDS = (0.25, 1.0)

REMOTE_ALLOWLIST = (
    "metadata.get_cost",
    "metadata.get_billable_size",
    "metadata.get_dataset_range",
    "symbology.resolve",
)
REMOTE_DENYLIST = (
    "timeseries.get_range",
    "batch.submit_job",
    "batch.download",
)


class AcquisitionError(RuntimeError):
    """Fail-closed source acquisition error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _workspace_path(path: Path) -> str:
    return str(path.relative_to(WORKSPACE)).replace("\\", "/")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcquisitionError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AcquisitionError(f"expected JSON object in {path}")
    return payload


def _load_foundation():
    if sha256_file(FOUNDATION_PATH) != FOUNDATION_SHA256:
        raise AcquisitionError("reused acquisition foundation SHA mismatch")
    spec = importlib.util.spec_from_file_location(
        "event_clob_cme6e_acquisition_foundation", FOUNDATION_PATH
    )
    if spec is None or spec.loader is None:
        raise AcquisitionError("cannot load reused acquisition foundation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Reuse the tested crash-safe workspace JSON writer."""

    _load_foundation().write_json_atomic(path, payload)


def ensure_output_root(root: Path) -> Path:
    resolved = root.resolve()
    if resolved.drive.upper() != "D:":
        raise AcquisitionError(f"output root must be on D:, got {resolved}")
    try:
        resolved.relative_to(DATA_ROOT.resolve())
    except ValueError as exc:
        raise AcquisitionError(
            f"output root must remain under {DATA_ROOT.resolve()}, got {resolved}"
        ) from exc
    return resolved


def ensure_design_segments_output_root(root: Path) -> Path:
    resolved = ensure_output_root(root)
    expected = DESIGN_SEGMENTS_ROOT.resolve()
    if resolved != expected:
        raise AcquisitionError(
            f"design-segments output root must be exactly {expected}, got {resolved}"
        )
    return resolved


def _is_reparse_path(path: Path) -> bool:
    """Detect symlinks, junctions, mount points, and other Windows reparse paths."""

    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if callable(is_junction) and is_junction():
            return True
        if not path.exists():
            return False
        attributes = int(
            getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
        )
    except OSError as exc:
        raise AcquisitionError(f"cannot inspect path topology: {path}") from exc
    return bool(
        attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    )


def _validated_design_raw_root(root: Path, *, create: bool) -> Path:
    """Return the lexical raw root only when it cannot redirect outside root."""

    approved_root = root.resolve()
    if not approved_root.is_dir() or _is_reparse_path(approved_root):
        raise AcquisitionError("approved design root must be a real non-reparse directory")
    raw_root = approved_root / "raw"
    if raw_root.parent != approved_root or raw_root.parent.resolve() != approved_root:
        raise AcquisitionError("raw path parent is not the exact approved design root")
    if _is_reparse_path(raw_root):
        raise AcquisitionError("design raw root is a junction or Windows reparse point")
    if raw_root.exists():
        if not raw_root.is_dir() or raw_root.resolve() != raw_root:
            raise AcquisitionError("design raw root is not a real contained directory")
    elif create:
        try:
            raw_root.mkdir()
        except OSError as exc:
            raise AcquisitionError(f"cannot create exact design raw root: {raw_root}") from exc
        if (
            _is_reparse_path(raw_root)
            or not raw_root.is_dir()
            or raw_root.resolve() != raw_root
        ):
            raise AcquisitionError("created design raw root failed topology validation")
    return raw_root


def _validated_design_raw_artifacts(
    *, root: Path, filename: str, require_raw_root: bool
) -> tuple[Path, Path]:
    """Validate every component used for a final and partial DBN path."""

    raw_root = _validated_design_raw_root(root, create=False)
    if require_raw_root and not raw_root.is_dir():
        raise AcquisitionError("design raw root is missing")
    relative = Path(filename)
    if (
        not filename
        or relative.is_absolute()
        or len(relative.parts) != 1
        or relative.name != filename
        or filename in {".", ".."}
    ):
        raise AcquisitionError("design DBN filename is not a single contained component")
    output = raw_root / filename
    partial = output.with_suffix(output.suffix + ".partial")
    for label, candidate in (("final", output), ("partial", partial)):
        if candidate.parent != raw_root:
            raise AcquisitionError(f"design DBN {label} parent escaped raw root")
        if _is_reparse_path(candidate):
            raise AcquisitionError(f"design DBN {label} is a Windows reparse point")
        try:
            resolved = candidate.resolve(strict=False)
        except OSError as exc:
            raise AcquisitionError(
                f"cannot resolve design DBN {label} path: {candidate}"
            ) from exc
        if resolved != candidate:
            raise AcquisitionError(f"design DBN {label} path escaped raw root")
    return output, partial


def _event_row_bindings(snapshot: bytes) -> dict[str, Any]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in snapshot.splitlines():
        if not raw:
            continue
        try:
            row = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AcquisitionError("EVENT-CLOB registry history contains invalid JSONL") from exc
        if isinstance(row, dict) and row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((raw, row))
    if len(matches) != len(BOUND_EVENT_ROW_SHA256_SEQUENCE):
        raise AcquisitionError(
            "EVENT-CLOB registry history must contain exactly "
            f"{len(BOUND_EVENT_ROW_SHA256_SEQUENCE)} rows, got {len(matches)}"
        )
    row_hashes = tuple(
        hashlib.sha256(raw).hexdigest().upper() for raw, _row in matches
    )
    if row_hashes != BOUND_EVENT_ROW_SHA256_SEQUENCE:
        raise AcquisitionError(
            "EVENT-CLOB registry history row SHA sequence mismatch"
        )
    latest = matches[-1][1]
    if latest.get("state") != LATEST_STATE or latest.get("verdict") != LATEST_VERDICT:
        raise AcquisitionError("EVENT-CLOB registry history latest state/verdict mismatch")
    return {
        "origin_row_sha256": row_hashes[0],
        "probe_transition_row_sha256": row_hashes[1],
        "latest_row_sha256": row_hashes[-1],
        "event_row_sha256_sequence": list(row_hashes),
        "latest_state": latest["state"],
        "latest_verdict": latest["verdict"],
        "event_row_count": len(matches),
    }


def _design_successor_row_bindings(snapshot: bytes) -> dict[str, Any]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in snapshot.splitlines():
        if not raw:
            continue
        try:
            row = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AcquisitionError(
                "EVENT-CLOB successor registry history contains invalid JSONL"
            ) from exc
        if isinstance(row, dict) and row.get("hypothesis_id") == DESIGN_HYPOTHESIS_ID:
            matches.append((raw, row))
    if len(matches) != len(DESIGN_SUCCESSOR_ROW_SHA256_SEQUENCE):
        raise AcquisitionError(
            "EVENT-CLOB successor registry history must contain exactly "
            f"{len(DESIGN_SUCCESSOR_ROW_SHA256_SEQUENCE)} rows, got {len(matches)}"
        )
    row_hashes = tuple(
        hashlib.sha256(raw).hexdigest().upper() for raw, _row in matches
    )
    if row_hashes != DESIGN_SUCCESSOR_ROW_SHA256_SEQUENCE:
        raise AcquisitionError(
            "EVENT-CLOB successor registry history row SHA sequence mismatch"
        )
    latest = matches[-1][1]
    if (
        latest.get("state") != DESIGN_LATEST_STATE
        or latest.get("verdict") != DESIGN_LATEST_VERDICT
    ):
        raise AcquisitionError(
            "EVENT-CLOB successor registry history latest state/verdict mismatch"
        )
    return {
        "successor_row_sha256_sequence": list(row_hashes),
        "latest_row_sha256": row_hashes[-1],
        "latest_state": latest["state"],
        "latest_verdict": latest["verdict"],
        "successor_row_count": len(matches),
    }


def _registry_snapshot() -> bytes:
    try:
        return REGISTRY_PATH.read_bytes()
    except OSError as exc:
        raise AcquisitionError(f"cannot snapshot registry: {REGISTRY_PATH}") from exc


def verify_immutable_quote_evidence() -> dict[str, Any]:
    if not QUOTE_EVIDENCE_MANIFEST_PATH.is_file():
        raise AcquisitionError(
            f"immutable free quote evidence manifest is missing: {QUOTE_EVIDENCE_MANIFEST_PATH}"
        )
    manifest_sha256 = sha256_file(QUOTE_EVIDENCE_MANIFEST_PATH)
    if manifest_sha256 != QUOTE_EVIDENCE_MANIFEST_SHA256:
        raise AcquisitionError("immutable free quote evidence manifest SHA mismatch")
    manifest = _load_json(QUOTE_EVIDENCE_MANIFEST_PATH)
    if (
        manifest.get("hypothesis_id") != HYPOTHESIS_ID
        or manifest.get("plan_id") != QUOTE_EVIDENCE_PLAN_ID
        or manifest.get("immutable_snapshot") is not True
    ):
        raise AcquisitionError("immutable free quote evidence identity mismatch")
    file_entries = manifest.get("files")
    if not isinstance(file_entries, list):
        raise AcquisitionError("immutable free quote evidence file ledger is invalid")
    try:
        manifest_children = {
            str(entry["path"]): str(entry["sha256"]) for entry in file_entries
        }
    except (KeyError, TypeError) as exc:
        raise AcquisitionError("immutable free quote evidence file ledger is invalid") from exc
    if len(manifest_children) != len(file_entries) or manifest_children != QUOTE_EVIDENCE_CHILD_SHA256:
        raise AcquisitionError("immutable free quote evidence child ledger mismatch")
    disk_names = {path.name for path in QUOTE_EVIDENCE_ROOT.iterdir()}
    expected_disk_names = {"manifest.json", *QUOTE_EVIDENCE_CHILD_SHA256}
    if disk_names != expected_disk_names:
        raise AcquisitionError("immutable free quote evidence directory contents changed")
    for filename, expected_sha256 in QUOTE_EVIDENCE_CHILD_SHA256.items():
        child = QUOTE_EVIDENCE_ROOT / filename
        if not child.is_file() or sha256_file(child) != expected_sha256:
            raise AcquisitionError(
                f"immutable free quote evidence child SHA mismatch: {filename}"
            )
    return {
        "manifest_path": _workspace_path(QUOTE_EVIDENCE_MANIFEST_PATH),
        "manifest_sha256": manifest_sha256,
        "plan_id": QUOTE_EVIDENCE_PLAN_ID,
        "child_sha256": dict(QUOTE_EVIDENCE_CHILD_SHA256),
    }


def verify_immutable_design_quote_evidence(
    *, root: Path | None = None
) -> dict[str, Any]:
    """Verify the frozen V11 design quote without rebinding it to V12 source."""

    evidence_root = DESIGN_QUOTE_EVIDENCE_ROOT if root is None else Path(root)
    if not evidence_root.is_dir() or evidence_root.is_symlink():
        raise AcquisitionError("immutable design quote evidence root is invalid")
    resolved_root = evidence_root.resolve()
    manifest_path = evidence_root / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise AcquisitionError("immutable design quote evidence manifest is missing")
    manifest_sha256 = sha256_file(manifest_path)
    if manifest_sha256 != DESIGN_QUOTE_EVIDENCE_MANIFEST_SHA256:
        raise AcquisitionError("immutable design quote evidence manifest SHA mismatch")

    disk_names = {item.name for item in evidence_root.iterdir()}
    expected_disk_names = {"manifest.json", *DESIGN_QUOTE_EVIDENCE_CHILD_SHA256}
    if disk_names != expected_disk_names:
        raise AcquisitionError("immutable design quote evidence directory contents changed")

    manifest = _load_json(manifest_path)
    identity = {
        "schema_version": DESIGN_EVIDENCE_SCHEMA_VERSION,
        "status": "IMMUTABLE_DESIGN_FREE_QUOTE_COMPLETE_NO_PAID_REQUEST",
        "profile": DESIGN_SEGMENTS_PROFILE,
        "hypothesis_id": DESIGN_HYPOTHESIS_ID,
        "plan_id": DESIGN_QUOTE_EVIDENCE_PLAN_ID,
        "immutable_snapshot": True,
        "raw_dbn_files": 0,
    }
    if {key: manifest.get(key) for key in identity} != identity:
        raise AcquisitionError("immutable design quote evidence identity mismatch")
    if manifest.get("quote") != DESIGN_QUOTE_EVIDENCE_TOTALS:
        raise AcquisitionError("immutable design quote evidence totals mismatch")
    if (
        manifest.get("parent_quote_evidence_manifest_sha256")
        != QUOTE_EVIDENCE_MANIFEST_SHA256
    ):
        raise AcquisitionError("immutable design quote evidence parent F8 binding mismatch")

    file_entries = manifest.get("files")
    if not isinstance(file_entries, list):
        raise AcquisitionError("immutable design quote evidence file ledger is invalid")
    manifest_children: dict[str, str] = {}
    for entry in file_entries:
        if not isinstance(entry, dict):
            raise AcquisitionError("immutable design quote evidence file ledger is invalid")
        filename = entry.get("path")
        expected_sha256 = entry.get("sha256")
        if not isinstance(filename, str) or not isinstance(expected_sha256, str):
            raise AcquisitionError("immutable design quote evidence file ledger is invalid")
        relative = Path(filename)
        if (
            relative.is_absolute()
            or len(relative.parts) != 1
            or relative.parts[0] in {"", ".", ".."}
        ):
            raise AcquisitionError("immutable design quote evidence child path escapes root")
        child = evidence_root / relative
        if child.is_symlink():
            raise AcquisitionError("immutable design quote evidence child path is a symlink")
        resolved_child = child.resolve()
        try:
            resolved_child.relative_to(resolved_root)
        except ValueError as exc:
            raise AcquisitionError(
                "immutable design quote evidence child path escapes root"
            ) from exc
        if resolved_child.parent != resolved_root:
            raise AcquisitionError("immutable design quote evidence child path escapes root")
        if filename in manifest_children:
            raise AcquisitionError("immutable design quote evidence file ledger is invalid")
        manifest_children[filename] = expected_sha256
    if manifest_children != DESIGN_QUOTE_EVIDENCE_CHILD_SHA256:
        raise AcquisitionError("immutable design quote evidence child ledger mismatch")

    for filename, expected_sha256 in DESIGN_QUOTE_EVIDENCE_CHILD_SHA256.items():
        child = evidence_root / filename
        if not child.is_file() or sha256_file(child) != expected_sha256:
            raise AcquisitionError(
                f"immutable design quote evidence child SHA mismatch: {filename}"
            )

    plan = _load_json(evidence_root / PLAN_NAME)
    receipt = _load_json(evidence_root / DESIGN_QUOTE_RECEIPT_NAME)
    storage = _load_json(evidence_root / DESIGN_STORAGE_ASSESSMENT_NAME)
    historical_tool = {
        "path": _workspace_path(Path(__file__).resolve()),
        "sha256": HISTORICAL_DESIGN_TOOL_SHA256,
    }
    if plan.get("tool") != historical_tool:
        raise AcquisitionError("historical design quote tool binding mismatch")
    bindings = plan.get("bindings")
    if not isinstance(bindings, dict):
        raise AcquisitionError("historical design quote bindings are missing")
    historical_binding = {
        "registry_sha256": HISTORICAL_DESIGN_REGISTRY_SHA256,
        "successor_row_sha256_sequence": list(
            HISTORICAL_DESIGN_ROW_SHA256_SEQUENCE
        ),
        "latest_row_sha256": HISTORICAL_DESIGN_ROW_SHA256_SEQUENCE[-1],
        "latest_state": "probe",
        "latest_verdict": "FROZEN_DESIGN_SEGMENT_PLAN_AND_FREE_QUOTE_AUTHORIZED",
        "successor_row_count": 2,
        "task_packet_v11_sha256": TASK_PACKET_V11_SHA256,
        "failure_evidence_sha256": DESIGN_FAILURE_EVIDENCE_SHA256,
    }
    if {key: bindings.get(key) for key in historical_binding} != historical_binding:
        raise AcquisitionError("historical design quote start bindings mismatch")
    if (
        bindings.get("parent_v9", {})
        .get("immutable_quote_evidence", {})
        .get("manifest_sha256")
        != QUOTE_EVIDENCE_MANIFEST_SHA256
    ):
        raise AcquisitionError("historical design quote parent F8 binding mismatch")

    expected_plan_identity = {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "status": "QUOTED_DESIGN_SEGMENTS_METADATA_ONLY_NOT_DOWNLOADED",
        "profile": DESIGN_SEGMENTS_PROFILE,
        "hypothesis_id": DESIGN_HYPOTHESIS_ID,
        "parent_hypothesis_id": HYPOTHESIS_ID,
        "plan_id": DESIGN_QUOTE_EVIDENCE_PLAN_ID,
        "databento_sdk_version": DATABENTO_SDK_VERSION,
    }
    if {key: plan.get(key) for key in expected_plan_identity} != expected_plan_identity:
        raise AcquisitionError("historical design quote plan identity mismatch")
    if plan_id(plan) != DESIGN_QUOTE_EVIDENCE_PLAN_ID:
        raise AcquisitionError("historical design quote plan ID does not reconcile")
    canonical_requests, canonical_coverage = _read_design_segment_requests()
    if plan.get("requests") != canonical_requests or plan.get("coverage") != canonical_coverage:
        raise AcquisitionError("historical design quote requests are not canonical")
    quotes = plan.get("quotes")
    if not isinstance(quotes, list) or len(quotes) != DESIGN_REQUESTS:
        raise AcquisitionError("historical design quote identity coverage mismatch")
    for request, quote in zip(canonical_requests, quotes):
        expected_identity = {
            key: request[key]
            for key in ("request_id", "event_clock_id", "segment", "start", "end")
        }
        if {key: quote.get(key) for key in expected_identity} != expected_identity:
            raise AcquisitionError("historical design quote identity/bounds mismatch")
    total_usd = sum(float(item.get("estimated_usd", -1)) for item in quotes)
    total_bytes = sum(int(item.get("billable_bytes", -1)) for item in quotes)
    if not math.isclose(
        total_usd,
        float(DESIGN_QUOTE_EVIDENCE_TOTALS["estimated_total_usd"]),
        abs_tol=1e-12,
    ) or total_bytes != DESIGN_QUOTE_EVIDENCE_TOTALS["estimated_total_billable_bytes"]:
        raise AcquisitionError("historical design quote child totals do not reconcile")
    if (
        not math.isclose(
            float(plan.get("estimated_total_usd", -1)), total_usd, abs_tol=1e-12
        )
        or plan.get("estimated_total_billable_bytes") != total_bytes
        or plan.get("quote_coverage")
        != {"quoted_identities": DESIGN_REQUESTS, "expected_identities": DESIGN_REQUESTS}
    ):
        raise AcquisitionError("historical design quote plan totals mismatch")

    expected_counters = _zero_api_counters()
    expected_counters["metadata.get_cost"] = DESIGN_REQUESTS
    expected_counters["metadata.get_billable_size"] = DESIGN_REQUESTS
    if plan.get("api_method_counters") != expected_counters:
        raise AcquisitionError("historical design quote plan counters mismatch")
    if (
        receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION
        or receipt.get("status") != "FREE_METADATA_QUOTE_COMPLETE_NO_PAID_REQUEST"
        or receipt.get("profile") != DESIGN_SEGMENTS_PROFILE
        or receipt.get("hypothesis_id") != DESIGN_HYPOTHESIS_ID
        or receipt.get("plan_id") != DESIGN_QUOTE_EVIDENCE_PLAN_ID
        or receipt.get("receipt_id") != plan_id(receipt)
        or receipt.get("quotes") != quotes
        or receipt.get("api_method_counters") != expected_counters
        or not math.isclose(
            float(receipt.get("estimated_total_usd", -1)), total_usd, abs_tol=1e-12
        )
        or receipt.get("estimated_total_billable_bytes") != total_bytes
    ):
        raise AcquisitionError("historical design quote receipt does not reconcile")

    for payload in (plan, receipt):
        if (
            payload.get("timeseries_calls") != 0
            or payload.get("paid_request_made") is not False
            or payload.get("outcome_fields_used") is not False
            or payload.get("price_data_read") is not False
        ):
            raise AcquisitionError("historical design quote crossed a sealed boundary")
    expected_storage = {
        "schema_version": DESIGN_STORAGE_SCHEMA_VERSION,
        "status": "DESIGN_QUOTE_STORAGE_ASSESSED_NO_DOWNLOAD",
        "profile": DESIGN_SEGMENTS_PROFILE,
        "hypothesis_id": DESIGN_HYPOTHESIS_ID,
        "plan_id": DESIGN_QUOTE_EVIDENCE_PLAN_ID,
        "estimated_total_usd": DESIGN_QUOTE_EVIDENCE_TOTALS[
            "estimated_total_usd"
        ],
        "estimated_total_billable_bytes": DESIGN_QUOTE_EVIDENCE_TOTALS[
            "estimated_total_billable_bytes"
        ],
        "estimated_bytes_fit": True,
        "raw_dbn_files": 0,
        "timeseries_calls": 0,
        "paid_request_made": False,
        "outcome_fields_used": False,
    }
    if {key: storage.get(key) for key in expected_storage} != expected_storage:
        raise AcquisitionError("historical design quote storage assessment mismatch")

    parent_evidence = verify_immutable_quote_evidence()
    if parent_evidence.get("manifest_sha256") != QUOTE_EVIDENCE_MANIFEST_SHA256:
        raise AcquisitionError("immutable design quote evidence parent F8 drift")
    return {
        "manifest_path": _workspace_path(DESIGN_QUOTE_EVIDENCE_MANIFEST_PATH)
        if root is None
        else str(manifest_path),
        "manifest_sha256": manifest_sha256,
        "plan_id": DESIGN_QUOTE_EVIDENCE_PLAN_ID,
        "child_sha256": dict(DESIGN_QUOTE_EVIDENCE_CHILD_SHA256),
        "quote": dict(DESIGN_QUOTE_EVIDENCE_TOTALS),
        "historical_tool_sha256": HISTORICAL_DESIGN_TOOL_SHA256,
        "historical_registry_sha256": HISTORICAL_DESIGN_REGISTRY_SHA256,
        "parent_quote_evidence_manifest_sha256": parent_evidence[
            "manifest_sha256"
        ],
    }


def _validate_canonical_registry() -> str:
    try:
        spec = importlib.util.spec_from_file_location(
            "event_clob_canonical_registry_validator", REGISTRY_VALIDATOR_PATH
        )
        if spec is None or spec.loader is None:
            raise AcquisitionError("cannot load canonical registry validator")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        errors = validator.validate_registry(REGISTRY_PATH, validator.DEFAULT_SCHEMA)
    except ModuleNotFoundError:
        python = shutil.which("python")
        if not python or Path(python).resolve() == Path(sys.executable).resolve():
            raise AcquisitionError(
                "canonical registry validator runtime with jsonschema is unavailable"
            )
        completed = subprocess.run(
            [
                python,
                "-X",
                "utf8",
                str(REGISTRY_VALIDATOR_PATH),
                "--registry",
                str(REGISTRY_PATH),
            ],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise AcquisitionError(f"canonical registry validator failed: {detail}")
        result = completed.stdout.strip().splitlines()[-1]
        if not result.startswith("CANDIDATE_REGISTRY_OK "):
            raise AcquisitionError("canonical registry validator returned no PASS receipt")
        return result
    except AcquisitionError:
        raise
    except Exception as exc:
        raise AcquisitionError(f"canonical registry validator failed: {exc}") from exc
    if errors:
        raise AcquisitionError(
            "canonical registry validator failed: " + " | ".join(errors)
        )
    snapshot = _registry_snapshot()
    rows = [raw for raw in snapshot.splitlines() if raw.strip()]
    hypotheses = {
        json.loads(raw.decode("utf-8"))["hypothesis_id"] for raw in rows
    }
    return f"CANDIDATE_REGISTRY_OK rows={len(rows)} hypotheses={len(hypotheses)}"


class _ImmutableRegistrySnapshot:
    """Path-like read-only adapter that never re-opens the live registry."""

    def __init__(self, payload: bytes) -> None:
        self._payload = bytes(payload)

    def is_file(self) -> bool:
        return True

    def read_text(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        return self._payload.decode(encoding, errors)

    def __str__(self) -> str:
        return "<immutable-registry-snapshot>"


def _snapshot_registry_validator_receipt(snapshot: bytes) -> str:
    try:
        rows = snapshot.decode("utf-8-sig").splitlines()
        hypotheses = {
            json.loads(raw)["hypothesis_id"] for raw in rows if raw.strip()
        }
    except (UnicodeDecodeError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise AcquisitionError(
            "canonical registry validator receipt snapshot is malformed"
        ) from exc
    return f"CANDIDATE_REGISTRY_OK rows={len(rows)} hypotheses={len(hypotheses)}"


def _validate_canonical_registry_snapshot(
    snapshot: bytes, *, allow_external_runtime: bool = True
) -> str:
    """Validate and receipt the exact immutable bytes bound to a V14 SHA."""

    if not isinstance(snapshot, bytes):
        raise AcquisitionError("canonical registry snapshot must be immutable bytes")
    try:
        spec = importlib.util.spec_from_file_location(
            "event_clob_canonical_registry_snapshot_validator",
            REGISTRY_VALIDATOR_PATH,
        )
        if spec is None or spec.loader is None:
            raise AcquisitionError("cannot load canonical registry validator")
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        errors = validator.validate_registry(
            _ImmutableRegistrySnapshot(snapshot), validator.DEFAULT_SCHEMA
        )
    except ModuleNotFoundError:
        python = shutil.which("python")
        if (
            not allow_external_runtime
            or not python
            or Path(python).resolve() == Path(sys.executable).resolve()
        ):
            raise AcquisitionError(
                "canonical registry snapshot validator runtime with jsonschema "
                "is unavailable"
            )
        helper = (
            "import importlib.util,sys\n"
            "from pathlib import Path\n"
            "source=Path(sys.argv[1]).resolve()\n"
            "spec=importlib.util.spec_from_file_location('event_clob_snapshot_helper',source)\n"
            "module=importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "print(module._validate_canonical_registry_snapshot("
            "sys.stdin.buffer.read(),allow_external_runtime=False))\n"
        )
        completed = subprocess.run(
            [
                python,
                "-B",
                "-X",
                "utf8",
                "-c",
                helper,
                str(Path(__file__).resolve()),
            ],
            cwd=WORKSPACE,
            input=snapshot,
            capture_output=True,
            timeout=120,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).decode(
                "utf-8", errors="replace"
            ).strip()
            raise AcquisitionError(
                f"canonical registry validator failed: {detail}"
            )
        result = completed.stdout.decode("utf-8", errors="replace").strip().splitlines()[-1]
        if not result.startswith("CANDIDATE_REGISTRY_OK "):
            raise AcquisitionError(
                "canonical registry snapshot validator returned no PASS receipt"
            )
        return result
    except AcquisitionError:
        raise
    except Exception as exc:
        raise AcquisitionError(f"canonical registry validator failed: {exc}") from exc
    if errors:
        raise AcquisitionError(
            "canonical registry validator failed: " + " | ".join(errors)
        )
    return _snapshot_registry_validator_receipt(snapshot)


def _v14_registry_prefix_hash_indices(snapshot: bytes) -> dict[str, int]:
    lines = snapshot.splitlines(keepends=True)
    if len(lines) < V14_REGISTRY_PREFIX_ROWS:
        raise AcquisitionError("V14 registry prefix is truncated")
    hashes: dict[str, int] = {}
    payload = b""
    for index, raw in enumerate(lines, start=1):
        if not raw.endswith(b"\n") or raw.endswith(b"\r\n"):
            raise AcquisitionError("V14 registry prefix/newline contract drifted")
        payload += raw
        if index >= V14_REGISTRY_PREFIX_ROWS:
            hashes[hashlib.sha256(payload).hexdigest().upper()] = index
    if (
        hashlib.sha256(b"".join(lines[:V14_REGISTRY_PREFIX_ROWS]))
        .hexdigest()
        .upper()
        != V14_REGISTRY_PREFIX_SHA256
    ):
        raise AcquisitionError("V14 registry exact 272-row prefix SHA mismatch")
    return hashes


def _reject_v14_nonfinite_json(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _reject_v14_duplicate_json_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key is forbidden: {key}")
        result[key] = value
    return result


def _load_v14_strict_json_row(raw: bytes) -> dict[str, Any]:
    try:
        serialized = raw.decode("utf-8")
        row = json.loads(
            serialized,
            parse_constant=_reject_v14_nonfinite_json,
            object_pairs_hook=_reject_v14_duplicate_json_keys,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise AcquisitionError("V14 appended registry row is invalid strict JSON") from exc
    if not isinstance(row, dict):
        raise AcquisitionError("V14 appended registry row is not an object")
    return row


def _iter_v14_decoded_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _iter_v14_decoded_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_v14_decoded_strings(item)


def _verify_v14_registry_authority(
    *, snapshot: bytes | None = None
) -> dict[str, Any]:
    current = _registry_snapshot() if snapshot is None else snapshot
    prefix_hashes = _v14_registry_prefix_hash_indices(current)
    registry_sha256 = hashlib.sha256(current).hexdigest().upper()
    validator_result = _V14_VALIDATOR_PASS_BY_REGISTRY_SHA256.get(registry_sha256)
    if validator_result is None:
        validator_result = _validate_canonical_registry_snapshot(current)
    if not validator_result.startswith("CANDIDATE_REGISTRY_OK "):
        raise AcquisitionError("V14 canonical registry validator returned no PASS")
    lines = current.splitlines(keepends=True)
    try:
        receipt_fields = dict(
            item.split("=", 1) for item in validator_result.split()[1:]
        )
        receipt_rows = int(receipt_fields["rows"])
        receipt_hypotheses = int(receipt_fields["hypotheses"])
        snapshot_hypotheses = len(
            {
                json.loads(raw.decode("utf-8"))["hypothesis_id"]
                for raw in current.splitlines()
                if raw
            }
        )
    except (KeyError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcquisitionError("V14 canonical registry validator receipt is malformed") from exc
    if receipt_rows != len(lines) or receipt_hypotheses != snapshot_hypotheses:
        raise AcquisitionError(
            "V14 registry snapshot changed across canonical validator boundary"
        )
    appended = lines[V14_REGISTRY_PREFIX_ROWS:]
    lowered_tokens = tuple(token.casefold() for token in V14_REGISTRY_CONFLICT_TOKENS)
    for raw in appended:
        if not raw or not raw.endswith(b"\n") or raw.endswith(b"\r\n"):
            raise AcquisitionError("V14 appended registry row is not strict LF JSONL")
        row = _load_v14_strict_json_row(raw[:-1])
        conflict = next(
            (
                token
                for decoded in _iter_v14_decoded_strings(row)
                for token in lowered_tokens
                if token in decoded.casefold()
            ),
            None,
        )
        if conflict is not None:
            raise AcquisitionError(
                f"V14 appended registry row contains EventCLOB conflict token: {conflict}"
            )
        if row.get("hypothesis_id") in {HYPOTHESIS_ID, DESIGN_HYPOTHESIS_ID}:
            raise AcquisitionError("V14 appended registry row changes EventCLOB history")
    _V14_VALIDATOR_PASS_BY_REGISTRY_SHA256[registry_sha256] = validator_result
    return {
        "baseline_row_count": V14_REGISTRY_PREFIX_ROWS,
        "prefix_sha256": V14_REGISTRY_PREFIX_SHA256,
        "registry_sha256": registry_sha256,
        "registry_row_count": len(lines),
        "appended_row_count": len(appended),
        "validator_result": validator_result,
        "safe_prefix_hash_indices": prefix_hashes,
    }


def _validate_append_only_registry_drift(start: bytes, end: bytes) -> bool:
    if end == start:
        return False
    if not start.endswith(b"\n") or not end.startswith(start):
        raise AcquisitionError("global registry drift is not append-only")
    appended = end[len(start) :]
    if not appended:
        raise AcquisitionError("global registry append-only drift has no appended rows")
    for raw in appended.splitlines():
        if not raw:
            continue
        try:
            row = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AcquisitionError("global registry append contains invalid JSONL") from exc
        if not isinstance(row, dict):
            raise AcquisitionError("global registry append contains a non-object row")
    return True


def verify_bound_contract(*, require_global_registry: bool = True) -> dict[str, Any]:
    bindings = (
        (TASK_PACKET_PATH, TASK_PACKET_SHA256, "original task packet"),
        (TASK_PACKET_V2_PATH, TASK_PACKET_V2_SHA256, "V2 task packet"),
        (TASK_PACKET_V3_PATH, TASK_PACKET_V3_SHA256, "V3 task packet"),
        (TASK_PACKET_V4_PATH, TASK_PACKET_V4_SHA256, "V4 task packet"),
        (TASK_PACKET_V5_PATH, TASK_PACKET_V5_SHA256, "V5 task packet"),
        (TASK_PACKET_V6_PATH, TASK_PACKET_V6_SHA256, "V6 task packet"),
        (TASK_PACKET_V7_PATH, TASK_PACKET_V7_SHA256, "V7 task packet"),
        (TASK_PACKET_V8_PATH, TASK_PACKET_V8_SHA256, "V8 task packet"),
        (TASK_PACKET_V9_PATH, TASK_PACKET_V9_SHA256, "V9 task packet"),
        (PROBE_PLAN_PATH, PROBE_PLAN_SHA256, "frozen probe plan"),
        (CLOCK_PATH, CLOCK_SHA256, "frozen event clock"),
        (CLOCK_MANIFEST_PATH, CLOCK_MANIFEST_SHA256, "clock manifest"),
        (FOUNDATION_PATH, FOUNDATION_SHA256, "reused acquisition foundation"),
    )
    actuals: dict[str, str] = {}
    for path, expected, label in bindings:
        if not path.is_file():
            raise AcquisitionError(f"missing {label}: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise AcquisitionError(
                f"{label} SHA mismatch: expected {expected}, got {actual}"
            )
        actuals[label] = actual

    registry_snapshot = _registry_snapshot()
    registry_actual = hashlib.sha256(registry_snapshot).hexdigest().upper()
    event_history = _event_row_bindings(registry_snapshot)
    quote_evidence = verify_immutable_quote_evidence()
    registry_authority = (
        _verify_v14_registry_authority(snapshot=registry_snapshot)
        if require_global_registry
        else None
    )
    return {
        "all_match": event_history["origin_row_sha256"] == ORIGIN_ROW_SHA256
        and event_history["latest_row_sha256"] == LATEST_ROW_SHA256,
        "registry_sha256": registry_actual,
        "registry_prefix_sha256": V14_REGISTRY_PREFIX_SHA256,
        "registry_validator_result": (
            registry_authority["validator_result"] if registry_authority else None
        ),
        "hypothesis_row_sha256": event_history["origin_row_sha256"],
        **event_history,
        "probe_plan_sha256": actuals["frozen probe plan"],
        "clock_sha256": actuals["frozen event clock"],
        "clock_manifest_sha256": actuals["clock manifest"],
        "task_packet_v3_sha256": actuals["V3 task packet"],
        "task_packet_v4_sha256": actuals["V4 task packet"],
        "task_packet_v5_sha256": actuals["V5 task packet"],
        "task_packet_v6_sha256": actuals["V6 task packet"],
        "task_packet_v7_sha256": actuals["V7 task packet"],
        "task_packet_v8_sha256": actuals["V8 task packet"],
        "task_packet_v9_sha256": actuals["V9 task packet"],
        "immutable_quote_evidence": quote_evidence,
        "foundation_sha256": actuals["reused acquisition foundation"],
    }


def _verify_v13_owner_authorization() -> dict[str, Any]:
    packet = _load_json(TASK_PACKET_V13_PATH)
    owner = packet.get("owner_authorization")
    if not isinstance(owner, dict):
        raise AcquisitionError("V13 Owner authorization is missing")
    verbatim = owner.get("verbatim")
    if not isinstance(verbatim, str) or hashlib.sha256(
        verbatim.encode("utf-8")
    ).hexdigest().upper() != OWNER_AUTHORIZATION_VERBATIM_SHA256:
        raise AcquisitionError("V13 Owner authorization verbatim mismatch")
    if (
        owner.get("authorization_basis_plan_id")
        != DESIGN_QUOTE_EVIDENCE_PLAN_ID
        or owner.get("approved_max_usd") != DESIGN_APPROVED_MAX_USD
        or owner.get("scope")
        != "one serial paid acquisition of exactly the 658 frozen 2019-2020 design PRE/LATE request identities only, after a fresh free live re-quote"
    ):
        raise AcquisitionError("V13 Owner authorization scope mismatch")
    return {
        "verbatim_sha256": OWNER_AUTHORIZATION_VERBATIM_SHA256,
        "authorization_basis_plan_id": DESIGN_QUOTE_EVIDENCE_PLAN_ID,
        "approved_max_usd": DESIGN_APPROVED_MAX_USD,
    }


def _verify_v14_owner_authorization() -> dict[str, Any]:
    v13_owner = _verify_v13_owner_authorization()
    packet = _load_json(TASK_PACKET_V14_PATH)
    owner = packet.get("owner_authorization_unchanged")
    if not isinstance(owner, dict):
        raise AcquisitionError("V14 unchanged Owner authorization is missing")
    verbatim = owner.get("verbatim")
    if not isinstance(verbatim, str) or hashlib.sha256(
        verbatim.encode("utf-8")
    ).hexdigest().upper() != OWNER_AUTHORIZATION_VERBATIM_SHA256:
        raise AcquisitionError("V14 Owner authorization verbatim mismatch")
    if (
        owner.get("authorization_basis_plan_id")
        != DESIGN_QUOTE_EVIDENCE_PLAN_ID
        or owner.get("approved_max_usd") != DESIGN_APPROVED_MAX_USD
    ):
        raise AcquisitionError("V14 Owner authorization scope mismatch")
    authority = {
        "verbatim_sha256": OWNER_AUTHORIZATION_VERBATIM_SHA256,
        "authorization_basis_plan_id": DESIGN_QUOTE_EVIDENCE_PLAN_ID,
        "approved_max_usd": DESIGN_APPROVED_MAX_USD,
    }
    if authority != v13_owner:
        raise AcquisitionError("V14 Owner authorization drifted from V13")
    return authority


def verify_design_segments_bound_contract(
    *, require_global_registry: bool = True
) -> dict[str, Any]:
    # V14 deliberately keeps the parent/EventCLOB row hashes exact while the
    # global ledger may receive validator-clean unrelated append-only rows.
    parent = verify_bound_contract(require_global_registry=False)
    bindings = (
        (TASK_PACKET_V10_PATH, TASK_PACKET_V10_SHA256, "V10 task packet"),
        (TASK_PACKET_V11_PATH, TASK_PACKET_V11_SHA256, "V11 task packet"),
        (TASK_PACKET_V12_PATH, TASK_PACKET_V12_SHA256, "V12 task packet"),
        (TASK_PACKET_V13_PATH, TASK_PACKET_V13_SHA256, "V13 task packet"),
        (TASK_PACKET_V14_PATH, TASK_PACKET_V14_SHA256, "V14 task packet"),
        (
            DESIGN_FAILURE_EVIDENCE_PATH,
            DESIGN_FAILURE_EVIDENCE_SHA256,
            "design quote failure evidence",
        ),
        (DESIGN_PREREG_PATH, DESIGN_PREREG_SHA256, "design preregistration"),
    )
    actuals: dict[str, str] = {}
    for path, expected, label in bindings:
        if not path.is_file():
            raise AcquisitionError(f"missing {label}: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise AcquisitionError(
                f"{label} SHA mismatch: expected {expected}, got {actual}"
            )
        actuals[label] = actual
    snapshot = _registry_snapshot()
    registry_sha256 = hashlib.sha256(snapshot).hexdigest().upper()
    if registry_sha256 != parent["registry_sha256"]:
        raise AcquisitionError("global registry changed while design bindings were verified")
    registry_authority = _verify_v14_registry_authority(snapshot=snapshot)
    if registry_authority["registry_sha256"] != registry_sha256:
        raise AcquisitionError("global registry changed during V14 authority validation")
    successor = _design_successor_row_bindings(snapshot)
    design_quote_evidence = verify_immutable_design_quote_evidence()
    owner_authorization = _verify_v14_owner_authorization()
    return {
        "all_match": parent["all_match"]
        and successor["successor_row_sha256_sequence"]
        == list(DESIGN_SUCCESSOR_ROW_SHA256_SEQUENCE),
        "profile": DESIGN_SEGMENTS_PROFILE,
        "hypothesis_id": DESIGN_HYPOTHESIS_ID,
        "registry_sha256": registry_sha256,
        "registry_prefix_sha256": registry_authority["prefix_sha256"],
        "registry_baseline_rows": registry_authority["baseline_row_count"],
        "registry_appended_row_count": registry_authority["appended_row_count"],
        "registry_validator_result": registry_authority["validator_result"],
        **successor,
        "prereg_sha256": actuals["design preregistration"],
        "task_packet_v10_sha256": actuals["V10 task packet"],
        "task_packet_v11_sha256": actuals["V11 task packet"],
        "task_packet_v12_sha256": actuals["V12 task packet"],
        "task_packet_v13_sha256": actuals["V13 task packet"],
        "task_packet_v14_sha256": actuals["V14 task packet"],
        "failure_evidence_sha256": actuals["design quote failure evidence"],
        "immutable_design_quote_evidence": design_quote_evidence,
        "owner_authorization": owner_authorization,
        "clock_sha256": parent["clock_sha256"],
        "parent_v9": parent,
    }


def _iso_millis(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise AcquisitionError("event clock timestamp is not UTC")
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _filename(event_clock_id: str, start: datetime, end: datetime) -> str:
    return (
        f"{event_clock_id}_{start.strftime('%Y%m%dT%H%M%S')}Z_"
        f"{end.strftime('%Y%m%dT%H%M%S')}Z.dbn.zst"
    )


def _read_clock_windows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    with CLOCK_PATH.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"event_clock_id", "event_time_utc"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise AcquisitionError(f"event clock is missing fields {sorted(required)}")
        for raw in reader:
            event_clock_id = str(raw["event_clock_id"])
            try:
                clock = datetime.fromisoformat(
                    str(raw["event_time_utc"]).replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise AcquisitionError(
                    f"invalid UTC timestamp for {event_clock_id}"
                ) from exc
            start = clock + timedelta(seconds=WINDOW_START_OFFSET_SECONDS)
            end = clock + timedelta(seconds=WINDOW_END_OFFSET_SECONDS)
            rows.append(
                {
                    "event_clock_id": event_clock_id,
                    "event_time_utc": _iso_millis(clock),
                    "start": _iso_millis(start),
                    "end": _iso_millis(end),
                    "filename": _filename(event_clock_id, start, end),
                }
            )
    rows.sort(key=lambda item: (item["event_time_utc"], item["event_clock_id"]))
    identities = [item["event_clock_id"] for item in rows]
    clocks = [item["event_time_utc"] for item in rows]
    if len(rows) != EXPECTED_CLOCKS:
        raise AcquisitionError(f"event clock coverage is {len(rows)}/{EXPECTED_CLOCKS}")
    if len(identities) != len(set(identities)) or len(clocks) != len(set(clocks)):
        raise AcquisitionError("event clock contains duplicate identities or timestamps")

    overlaps: list[dict[str, Any]] = []
    for index, left in enumerate(rows):
        left_end = datetime.fromisoformat(left["end"].replace("Z", "+00:00"))
        left_clock = datetime.fromisoformat(
            left["event_time_utc"].replace("Z", "+00:00")
        )
        for right in rows[index + 1 :]:
            right_start = datetime.fromisoformat(right["start"].replace("Z", "+00:00"))
            if right_start >= left_end:
                break
            right_clock = datetime.fromisoformat(
                right["event_time_utc"].replace("Z", "+00:00")
            )
            overlaps.append(
                {
                    "left_event_clock_id": left["event_clock_id"],
                    "right_event_clock_id": right["event_clock_id"],
                    "clock_delta_seconds": int((right_clock - left_clock).total_seconds()),
                }
            )
    return rows, overlaps


def _design_segment_filename(
    request_id: str, start: datetime, end: datetime
) -> str:
    return (
        f"{request_id}_{start.strftime('%Y%m%dT%H%M%S')}_"
        f"{end.strftime('%Y%m%dT%H%M%S')}.dbn.zst"
    )


def _read_design_segment_requests() -> tuple[list[dict[str, Any]], dict[str, int]]:
    parent_windows, parent_overlaps = _read_clock_windows()
    design_clocks = [
        item for item in parent_windows if _parse_utc(item["event_time_utc"]).year <= 2020
    ]
    expected_ids = [f"EVT{index:04d}" for index in range(1, DESIGN_CLOCKS + 1)]
    if [item["event_clock_id"] for item in design_clocks] != expected_ids:
        raise AcquisitionError("design clock selection is not exactly EVT0001 through EVT0329")
    requests: list[dict[str, Any]] = []
    segment_contract = (
        ("PRE", -60, -15),
        ("LATE", 45, 60),
    )
    for item in design_clocks:
        clock = _parse_utc(item["event_time_utc"])
        for segment, start_offset, end_offset in segment_contract:
            start = clock + timedelta(seconds=start_offset)
            end = clock + timedelta(seconds=end_offset)
            request_id = f"{item['event_clock_id']}_{segment}"
            requests.append(
                {
                    "request_id": request_id,
                    "event_clock_id": item["event_clock_id"],
                    "segment": segment,
                    "event_time_utc": item["event_time_utc"],
                    "start": _iso_millis(start),
                    "end": _iso_millis(end),
                    "duration_seconds": int((end - start).total_seconds()),
                    "filename": _design_segment_filename(request_id, start, end),
                }
            )
    intervals = sorted(
        (
            _parse_utc(item["start"]),
            _parse_utc(item["end"]),
            item["request_id"],
        )
        for item in requests
    )
    request_overlap_count = sum(
        1 for left, right in zip(intervals, intervals[1:]) if right[0] < left[1]
    )
    design_ids = set(expected_ids)
    parent_clock_overlap_count = sum(
        1
        for item in parent_overlaps
        if item["left_event_clock_id"] in design_ids
        and item["right_event_clock_id"] in design_ids
    )
    coverage = {
        "design_clock_count": len(design_clocks),
        "validation_clock_count": 0,
        "validation_request_count": 0,
        "request_identity_count": len(requests),
        "requested_duration_seconds": sum(
            item["duration_seconds"] for item in requests
        ),
        "request_overlap_count": request_overlap_count,
        "parent_clock_overlap_count": parent_clock_overlap_count,
    }
    expected_coverage = {
        "design_clock_count": DESIGN_CLOCKS,
        "validation_clock_count": 0,
        "validation_request_count": 0,
        "request_identity_count": DESIGN_REQUESTS,
        "requested_duration_seconds": DESIGN_REQUESTED_SECONDS,
        "request_overlap_count": 0,
        "parent_clock_overlap_count": 1,
    }
    if coverage != expected_coverage:
        raise AcquisitionError(
            f"design segment coverage does not match frozen contract: {coverage}"
        )
    return requests, coverage


def _stable_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {
            key: _stable_payload(value)
            for key, value in payload.items()
            if key not in {"generated_at_utc", "quoted_at_utc", "plan_id", "receipt_id"}
        }
    if isinstance(payload, list):
        return [_stable_payload(item) for item in payload]
    return payload


def plan_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        _stable_payload(payload), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _zero_api_counters() -> dict[str, int]:
    return {method: 0 for method in (*REMOTE_ALLOWLIST, *REMOTE_DENYLIST)}


def _free_metadata_retry_policy() -> dict[str, Any]:
    return {
        "methods": list(FREE_METADATA_RETRY_METHODS),
        "transient_http_statuses": list(FREE_METADATA_TRANSIENT_HTTP_STATUSES),
        "transient_exception_kinds": ["timeout", "connection"],
        "max_attempts_per_call": FREE_METADATA_MAX_ATTEMPTS,
        "backoff_seconds": list(FREE_METADATA_RETRY_BACKOFF_SECONDS),
        "dataset_range_and_symbology_single_attempt": True,
        "paid_and_batch_retry_authorized": False,
    }


def build_offline_plan() -> dict[str, Any]:
    bindings = verify_bound_contract(require_global_registry=True)
    windows, overlaps = _read_clock_windows()
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "status": "PLANNED_NOT_QUOTED_NOT_DOWNLOADED",
        "profile": PARENT_PROFILE,
        "hypothesis_id": HYPOTHESIS_ID,
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbol": SYMBOL,
        "stype_in": STYPE_IN,
        "stype_out": STYPE_OUT,
        "cost_mode": COST_MODE,
        "free_metadata_retry_policy": _free_metadata_retry_policy(),
        "window_offsets_seconds": {
            "start": WINDOW_START_OFFSET_SECONDS,
            "end": WINDOW_END_OFFSET_SECONDS,
        },
        "clock": {"path": _workspace_path(CLOCK_PATH), "sha256": CLOCK_SHA256},
        "bindings": bindings,
        "tool": {
            "path": _workspace_path(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "reused_foundation": {
            "path": _workspace_path(FOUNDATION_PATH),
            "sha256": FOUNDATION_SHA256,
        },
        "coverage": {
            "clock_identities": len(windows),
            "overlapping_pair_count": len(overlaps),
            "overlapping_pairs": overlaps,
        },
        "windows": windows,
        "quotes": [],
        "quote_coverage": {"quoted_identities": 0, "expected_identities": EXPECTED_CLOCKS},
        "estimated_total_usd": None,
        "estimated_total_billable_bytes": None,
        "databento_sdk_version": None,
        "dataset_range": None,
        "symbology": None,
        "registry_quote_boundary": None,
        "registry_validator_boundary": None,
        "api_method_counters": _zero_api_counters(),
        "outcome_fields_used": False,
        "price_data_read": False,
        "timeseries_calls": 0,
        "paid_request_made": False,
        "download_authorized": False,
        "remote_method_allowlist": list(REMOTE_ALLOWLIST),
        "remote_method_denylist": list(REMOTE_DENYLIST),
    }
    payload["plan_id"] = plan_id(payload)
    validate_plan(payload, require_quote=False)
    return payload


def build_design_segments_plan() -> dict[str, Any]:
    bindings = verify_design_segments_bound_contract(require_global_registry=True)
    requests, coverage = _read_design_segment_requests()
    payload: dict[str, Any] = {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "status": "PLANNED_DESIGN_SEGMENTS_NOT_QUOTED_NOT_DOWNLOADED",
        "profile": DESIGN_SEGMENTS_PROFILE,
        "hypothesis_id": DESIGN_HYPOTHESIS_ID,
        "parent_hypothesis_id": HYPOTHESIS_ID,
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbol": SYMBOL,
        "stype_in": STYPE_IN,
        "stype_out": STYPE_OUT,
        "cost_mode": COST_MODE,
        "free_metadata_retry_policy": _free_metadata_retry_policy(),
        "segment_offsets_seconds": {
            "PRE": {"start": -60, "end": -15},
            "LATE": {"start": 45, "end": 60},
        },
        "interval_semantics": "half-open_[start,end)",
        "clock": {"path": _workspace_path(CLOCK_PATH), "sha256": CLOCK_SHA256},
        "bindings": bindings,
        "tool": {
            "path": _workspace_path(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "output_root": _workspace_path(DESIGN_SEGMENTS_ROOT),
        "coverage": coverage,
        "requests": requests,
        "quotes": [],
        "quote_coverage": {
            "quoted_identities": 0,
            "expected_identities": DESIGN_REQUESTS,
        },
        "estimated_total_usd": None,
        "estimated_total_billable_bytes": None,
        "databento_sdk_version": None,
        "dataset_range": None,
        "symbology": None,
        "registry_quote_boundary": None,
        "registry_validator_boundary": None,
        "api_method_counters": _zero_api_counters(),
        "outcome_fields_used": False,
        "price_data_read": False,
        "timeseries_calls": 0,
        "paid_request_made": False,
        "download_authorized": False,
        "validation_source_sealed": True,
        "remote_method_allowlist": list(FREE_METADATA_RETRY_METHODS),
        "remote_method_denylist": list(REMOTE_DENYLIST),
    }
    payload["plan_id"] = plan_id(payload)
    validate_design_segments_plan(payload, require_quote=False)
    return payload


def _parse_utc(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AcquisitionError(f"invalid UTC timestamp {value!r}") from exc
    if parsed.utcoffset() != timedelta(0):
        raise AcquisitionError(f"timestamp is not UTC: {value!r}")
    return parsed


def validate_plan(plan: dict[str, Any], *, require_quote: bool) -> None:
    if plan.get("schema_version") != SCHEMA_VERSION:
        raise AcquisitionError("acquisition plan schema mismatch")
    if plan.get("profile") != PARENT_PROFILE:
        raise AcquisitionError("acquisition plan parent profile mismatch")
    if plan.get("hypothesis_id") != HYPOTHESIS_ID:
        raise AcquisitionError("acquisition plan hypothesis mismatch")
    if (plan.get("dataset"), plan.get("schema"), plan.get("symbol")) != (
        DATASET,
        SCHEMA,
        SYMBOL,
    ):
        raise AcquisitionError("acquisition plan Databento contract mismatch")
    if plan.get("cost_mode") != COST_MODE:
        raise AcquisitionError("acquisition plan cost mode mismatch")
    if plan.get("free_metadata_retry_policy") != _free_metadata_retry_policy():
        raise AcquisitionError("acquisition plan free metadata retry policy mismatch")
    if plan.get("clock", {}).get("sha256") != CLOCK_SHA256:
        raise AcquisitionError("acquisition plan clock SHA mismatch")
    tool = plan.get("tool")
    if not isinstance(tool, dict) or tool.get("sha256") != sha256_file(
        Path(__file__).resolve()
    ):
        raise AcquisitionError("acquisition plan tool SHA mismatch")
    if plan.get("plan_id") != plan_id(plan):
        raise AcquisitionError("acquisition plan ID mismatch")
    if plan.get("paid_request_made") is not False or plan.get("timeseries_calls") != 0:
        raise AcquisitionError("acquisition plan does not prove zero paid calls")
    if plan.get("outcome_fields_used") is not False or plan.get("price_data_read") is not False:
        raise AcquisitionError("acquisition plan crossed the outcome boundary")

    windows = plan.get("windows")
    if not isinstance(windows, list) or len(windows) != EXPECTED_CLOCKS:
        raise AcquisitionError(f"acquisition plan must contain {EXPECTED_CLOCKS} windows")
    identities: set[str] = set()
    filenames: set[str] = set()
    for item in windows:
        if not isinstance(item, dict):
            raise AcquisitionError("acquisition plan contains invalid window")
        event_clock_id = str(item.get("event_clock_id", ""))
        if event_clock_id in identities:
            raise AcquisitionError("acquisition plan contains duplicate event clock identity")
        identities.add(event_clock_id)
        filename = str(item.get("filename", ""))
        if not filename or filename in filenames:
            raise AcquisitionError("acquisition plan contains duplicate output filename")
        filenames.add(filename)
        clock = _parse_utc(item.get("event_time_utc"))
        start = _parse_utc(item.get("start"))
        end = _parse_utc(item.get("end"))
        if start != clock + timedelta(seconds=WINDOW_START_OFFSET_SECONDS):
            raise AcquisitionError("acquisition window start does not match frozen offset")
        if end != clock + timedelta(seconds=WINDOW_END_OFFSET_SECONDS):
            raise AcquisitionError("acquisition window end does not match frozen offset")

    canonical_windows, canonical_overlaps = _read_clock_windows()
    if windows != canonical_windows:
        raise AcquisitionError(
            "acquisition plan windows do not match the canonical frozen clock byte-for-byte"
        )
    canonical_coverage = {
        "clock_identities": EXPECTED_CLOCKS,
        "overlapping_pair_count": len(canonical_overlaps),
        "overlapping_pairs": canonical_overlaps,
    }
    if plan.get("coverage") != canonical_coverage:
        raise AcquisitionError(
            "acquisition plan coverage does not match the canonical frozen clock"
        )

    counters = plan.get("api_method_counters")
    if not isinstance(counters, dict):
        raise AcquisitionError("acquisition plan lacks API method counters")
    for forbidden in REMOTE_DENYLIST:
        if counters.get(forbidden) != 0:
            raise AcquisitionError(f"forbidden API counter is nonzero: {forbidden}")

    quotes = plan.get("quotes")
    if not require_quote:
        if quotes != [] or plan.get("quote_coverage", {}).get("quoted_identities") != 0:
            raise AcquisitionError("offline plan unexpectedly contains metadata quotes")
        if plan.get("registry_quote_boundary") is not None:
            raise AcquisitionError("offline plan unexpectedly contains a quote registry boundary")
        if plan.get("registry_validator_boundary") is not None:
            raise AcquisitionError(
                "offline plan unexpectedly contains a registry validator boundary"
            )
        return
    if not isinstance(quotes, list) or len(quotes) != EXPECTED_CLOCKS:
        raise AcquisitionError(f"metadata quote must cover {EXPECTED_CLOCKS} identities")
    quote_ids = {str(item.get("event_clock_id")) for item in quotes if isinstance(item, dict)}
    if quote_ids != identities or len(quote_ids) != EXPECTED_CLOCKS:
        raise AcquisitionError("metadata quote identity coverage mismatch")
    for window, quote in zip(windows, quotes):
        expected_identity = {
            "event_clock_id": window["event_clock_id"],
            "start": window["start"],
            "end": window["end"],
        }
        if {key: quote.get(key) for key in expected_identity} != expected_identity:
            raise AcquisitionError("metadata quote is not canonically bound to its window")
        cost = float(quote.get("estimated_usd", -1))
        size = int(quote.get("billable_bytes", -1))
        if not math.isfinite(cost) or cost < 0 or size < 0:
            raise AcquisitionError("metadata quote has invalid cost or billable bytes")
    total_cost = sum(float(item["estimated_usd"]) for item in quotes)
    total_bytes = sum(int(item["billable_bytes"]) for item in quotes)
    if not math.isclose(total_cost, float(plan.get("estimated_total_usd", -1)), abs_tol=1e-12):
        raise AcquisitionError("metadata quote USD total does not reconcile")
    if total_bytes != int(plan.get("estimated_total_billable_bytes", -1)):
        raise AcquisitionError("metadata quote billable bytes do not reconcile")
    maximum_free_attempts = EXPECTED_CLOCKS * FREE_METADATA_MAX_ATTEMPTS
    for method in FREE_METADATA_RETRY_METHODS:
        attempts = counters.get(method)
        if (
            not isinstance(attempts, int)
            or isinstance(attempts, bool)
            or not EXPECTED_CLOCKS <= attempts <= maximum_free_attempts
        ):
            raise AcquisitionError(
                f"{method} attempt counter must be between "
                f"{EXPECTED_CLOCKS} and {maximum_free_attempts}"
            )
    if counters.get("metadata.get_dataset_range") != 1 or counters.get("symbology.resolve") != 1:
        raise AcquisitionError("metadata capability counters are incomplete")
    boundary = plan.get("registry_quote_boundary")
    if not isinstance(boundary, dict):
        raise AcquisitionError("metadata quote lacks registry boundary evidence")
    start_sha = boundary.get("start_sha256")
    end_sha = boundary.get("end_sha256")
    if start_sha != plan.get("bindings", {}).get("registry_sha256"):
        raise AcquisitionError("metadata quote registry start SHA does not match bindings")
    if not isinstance(end_sha, str) or len(end_sha) != 64:
        raise AcquisitionError("metadata quote registry end SHA is invalid")
    if boundary.get("append_only_drift_observed") != (start_sha != end_sha):
        raise AcquisitionError("metadata quote registry drift flag is inconsistent")
    validator_boundary = plan.get("registry_validator_boundary")
    if not isinstance(validator_boundary, dict):
        raise AcquisitionError("metadata quote lacks registry validator boundary evidence")
    if set(validator_boundary) != {"start_result", "end_result"}:
        raise AcquisitionError("metadata quote registry validator boundary is malformed")
    for field in ("start_result", "end_result"):
        result = validator_boundary.get(field)
        if not isinstance(result, str) or not result.startswith("CANDIDATE_REGISTRY_OK "):
            raise AcquisitionError(
                f"metadata quote canonical registry validator did not pass at {field}"
            )


def _without_registry_sha256(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_registry_sha256(item)
            for key, item in value.items()
            if key
            not in {
                "registry_sha256",
                "registry_appended_row_count",
                "registry_validator_result",
            }
        }
    if isinstance(value, list):
        return [_without_registry_sha256(item) for item in value]
    return value


def _validate_design_bindings(
    plan: dict[str, Any], *, require_quote: bool
) -> None:
    bindings = plan.get("bindings")
    if not isinstance(bindings, dict):
        raise AcquisitionError("design-segments bindings are missing")
    current = verify_design_segments_bound_contract(require_global_registry=True)
    if _without_registry_sha256(bindings) != _without_registry_sha256(current):
        raise AcquisitionError(
            "design-segments bindings do not match V14 frozen rows/artifacts"
        )
    snapshot = _registry_snapshot()
    safe_hashes = _v14_registry_prefix_hash_indices(snapshot)
    start_sha = bindings.get("registry_sha256")
    parent_start_sha = bindings.get("parent_v9", {}).get("registry_sha256")
    current_sha = current.get("registry_sha256")
    if (
        not isinstance(start_sha, str)
        or start_sha != parent_start_sha
        or start_sha not in safe_hashes
        or current_sha not in safe_hashes
        or safe_hashes[start_sha] > safe_hashes[current_sha]
    ):
        raise AcquisitionError("design-segments bindings violate V14 registry prefix order")
    if not require_quote:
        return

    parent_current_sha = current.get("parent_v9", {}).get("registry_sha256")
    if (
        current_sha != parent_current_sha
    ):
        raise AcquisitionError("design-segments bindings contain inconsistent registry SHAs")
    boundary = plan.get("registry_quote_boundary")
    if not isinstance(boundary, dict):
        raise AcquisitionError("design-segments bindings lack quote boundary evidence")
    if (
        boundary.get("start_sha256") != start_sha
    ):
        raise AcquisitionError("design-segments bindings do not reconcile registry boundary")
    end_sha = boundary.get("end_sha256")
    if (
        not isinstance(end_sha, str)
        or end_sha not in safe_hashes
        or safe_hashes[start_sha] > safe_hashes[end_sha]
        or safe_hashes[end_sha] > safe_hashes[current_sha]
    ):
        raise AcquisitionError("design-segments quote boundary violates V14 prefix order")
    drift = start_sha != end_sha
    if boundary.get("append_only_drift_observed") is not drift:
        raise AcquisitionError("design-segments bindings registry drift flag is inconsistent")


def validate_design_segments_plan(
    plan: dict[str, Any], *, require_quote: bool
) -> None:
    if plan.get("schema_version") != DESIGN_SCHEMA_VERSION:
        raise AcquisitionError("design-segments plan schema mismatch")
    if plan.get("profile") != DESIGN_SEGMENTS_PROFILE:
        raise AcquisitionError("design-segments profile mismatch")
    if plan.get("hypothesis_id") != DESIGN_HYPOTHESIS_ID:
        raise AcquisitionError("design-segments hypothesis mismatch")
    if plan.get("parent_hypothesis_id") != HYPOTHESIS_ID:
        raise AcquisitionError("design-segments parent hypothesis mismatch")
    expected_status = (
        "QUOTED_DESIGN_SEGMENTS_METADATA_ONLY_NOT_DOWNLOADED"
        if require_quote
        else "PLANNED_DESIGN_SEGMENTS_NOT_QUOTED_NOT_DOWNLOADED"
    )
    if plan.get("status") != expected_status:
        raise AcquisitionError("design-segments status does not match validation state")
    expected_sdk_version = DATABENTO_SDK_VERSION if require_quote else None
    if plan.get("databento_sdk_version") != expected_sdk_version:
        raise AcquisitionError("design-segments SDK version does not match validation state")
    if (plan.get("dataset"), plan.get("schema"), plan.get("symbol")) != (
        DATASET,
        SCHEMA,
        SYMBOL,
    ) or (plan.get("stype_in"), plan.get("stype_out")) != (STYPE_IN, STYPE_OUT):
        raise AcquisitionError("design-segments Databento contract mismatch")
    if plan.get("cost_mode") != COST_MODE:
        raise AcquisitionError("design-segments cost mode mismatch")
    if plan.get("free_metadata_retry_policy") != _free_metadata_retry_policy():
        raise AcquisitionError("design-segments retry policy mismatch")
    if plan.get("segment_offsets_seconds") != {
        "PRE": {"start": -60, "end": -15},
        "LATE": {"start": 45, "end": 60},
    } or plan.get("interval_semantics") != "half-open_[start,end)":
        raise AcquisitionError("design-segments interval contract mismatch")
    if plan.get("clock", {}).get("sha256") != CLOCK_SHA256:
        raise AcquisitionError("design-segments clock SHA mismatch")
    if plan.get("output_root") != _workspace_path(DESIGN_SEGMENTS_ROOT):
        raise AcquisitionError("design-segments output root mismatch")
    tool = plan.get("tool")
    if not isinstance(tool, dict) or tool.get("sha256") != sha256_file(
        Path(__file__).resolve()
    ):
        raise AcquisitionError("design-segments tool SHA mismatch")
    _validate_design_bindings(plan, require_quote=require_quote)
    if plan.get("plan_id") != plan_id(plan):
        raise AcquisitionError("design-segments plan ID mismatch")
    if (
        plan.get("paid_request_made") is not False
        or plan.get("timeseries_calls") != 0
        or plan.get("download_authorized") is not False
    ):
        raise AcquisitionError("design-segments plan does not prove zero paid authority")
    if (
        plan.get("outcome_fields_used") is not False
        or plan.get("price_data_read") is not False
        or plan.get("validation_source_sealed") is not True
    ):
        raise AcquisitionError("design-segments plan crossed a sealed boundary")
    if plan.get("remote_method_allowlist") != list(FREE_METADATA_RETRY_METHODS):
        raise AcquisitionError("design-segments remote allowlist mismatch")
    if plan.get("remote_method_denylist") != list(REMOTE_DENYLIST):
        raise AcquisitionError("design-segments remote denylist mismatch")

    canonical_requests, canonical_coverage = _read_design_segment_requests()
    requests = plan.get("requests")
    if requests != canonical_requests:
        raise AcquisitionError(
            "design-segments requests do not match canonical half-open bounds"
        )
    if plan.get("coverage") != canonical_coverage:
        raise AcquisitionError("design-segments coverage mismatch")
    request_ids = [item["request_id"] for item in canonical_requests]
    if len(request_ids) != DESIGN_REQUESTS or len(set(request_ids)) != DESIGN_REQUESTS:
        raise AcquisitionError("design-segments request identities are not unique")

    counters = plan.get("api_method_counters")
    if not isinstance(counters, dict):
        raise AcquisitionError("design-segments plan lacks API attempt counters")
    expected_counter_keys = set(_zero_api_counters())
    if set(counters) != expected_counter_keys:
        raise AcquisitionError("design-segments API counter key set mismatch")
    for forbidden in REMOTE_DENYLIST:
        if counters.get(forbidden) != 0:
            raise AcquisitionError(f"forbidden API counter is nonzero: {forbidden}")
    if plan.get("dataset_range") is not None or plan.get("symbology") is not None:
        raise AcquisitionError("design-segments quote used a non-allowlisted metadata method")

    quotes = plan.get("quotes")
    if not require_quote:
        if quotes != [] or plan.get("quote_coverage") != {
            "quoted_identities": 0,
            "expected_identities": DESIGN_REQUESTS,
        }:
            raise AcquisitionError("offline design-segments plan contains quotes")
        if any(counters.get(method) != 0 for method in counters):
            raise AcquisitionError("offline design-segments plan contains API attempts")
        if (
            plan.get("registry_quote_boundary") is not None
            or plan.get("registry_validator_boundary") is not None
        ):
            raise AcquisitionError("offline design-segments plan contains quote evidence")
        return

    if not isinstance(quotes, list) or len(quotes) != DESIGN_REQUESTS:
        raise AcquisitionError(
            f"design-segments metadata quote must cover {DESIGN_REQUESTS} requests"
        )
    for request, quote in zip(canonical_requests, quotes):
        expected_identity = {
            key: request[key]
            for key in ("request_id", "event_clock_id", "segment", "start", "end")
        }
        if {key: quote.get(key) for key in expected_identity} != expected_identity:
            raise AcquisitionError("design-segments quote identity/bounds mismatch")
        cost = float(quote.get("estimated_usd", -1))
        size = int(quote.get("billable_bytes", -1))
        if not math.isfinite(cost) or cost < 0 or size < 0:
            raise AcquisitionError("design-segments quote cost or size is invalid")
    if plan.get("quote_coverage") != {
        "quoted_identities": DESIGN_REQUESTS,
        "expected_identities": DESIGN_REQUESTS,
    }:
        raise AcquisitionError("design-segments quote coverage mismatch")
    total_cost = sum(float(item["estimated_usd"]) for item in quotes)
    total_bytes = sum(int(item["billable_bytes"]) for item in quotes)
    if not math.isclose(
        total_cost, float(plan.get("estimated_total_usd", -1)), abs_tol=1e-12
    ) or total_bytes != int(plan.get("estimated_total_billable_bytes", -1)):
        raise AcquisitionError("design-segments quote totals do not reconcile")
    maximum_attempts = DESIGN_REQUESTS * FREE_METADATA_MAX_ATTEMPTS
    for method in FREE_METADATA_RETRY_METHODS:
        attempts = counters.get(method)
        if (
            not isinstance(attempts, int)
            or isinstance(attempts, bool)
            or not DESIGN_REQUESTS <= attempts <= maximum_attempts
        ):
            raise AcquisitionError(
                f"{method} attempt counter must be between "
                f"{DESIGN_REQUESTS} and {maximum_attempts}"
            )
    if counters.get("metadata.get_dataset_range") != 0 or counters.get("symbology.resolve") != 0:
        raise AcquisitionError("design-segments quote called a non-allowlisted endpoint")
    boundary = plan.get("registry_quote_boundary")
    if not isinstance(boundary, dict):
        raise AcquisitionError("design-segments quote lacks registry boundary evidence")
    start_sha = boundary.get("start_sha256")
    end_sha = boundary.get("end_sha256")
    if start_sha != plan.get("bindings", {}).get("registry_sha256"):
        raise AcquisitionError("design-segments quote registry start SHA mismatch")
    if not isinstance(end_sha, str) or len(end_sha) != 64:
        raise AcquisitionError("design-segments quote registry end SHA is invalid")
    if boundary.get("append_only_drift_observed") != (start_sha != end_sha):
        raise AcquisitionError("design-segments registry drift flag is inconsistent")
    validator_boundary = plan.get("registry_validator_boundary")
    if not isinstance(validator_boundary, dict) or set(validator_boundary) != {
        "start_result",
        "end_result",
    }:
        raise AcquisitionError("design-segments validator boundary is malformed")
    for result in validator_boundary.values():
        if not isinstance(result, str) or not result.startswith("CANDIDATE_REGISTRY_OK "):
            raise AcquisitionError("design-segments canonical registry validator did not pass")


def _validate_profile_plan(plan: dict[str, Any], *, require_quote: bool) -> None:
    if plan.get("profile") == DESIGN_SEGMENTS_PROFILE:
        validate_design_segments_plan(plan, require_quote=require_quote)
    else:
        validate_plan(plan, require_quote=require_quote)


def _exception_chain(exc: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        chain.append(current)
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return chain


def _http_status(exc: BaseException) -> int | None:
    for candidate in _exception_chain(exc):
        values = [
            getattr(candidate, "http_status", None),
            getattr(candidate, "status_code", None),
        ]
        response = getattr(candidate, "response", None)
        if response is not None:
            values.extend(
                [getattr(response, "status_code", None), getattr(response, "status", None)]
            )
        for value in values:
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


def _is_transient_free_metadata_error(exc: BaseException) -> bool:
    status = _http_status(exc)
    if status is not None:
        return status in FREE_METADATA_TRANSIENT_HTTP_STATUSES
    for candidate in _exception_chain(exc):
        if isinstance(candidate, (TimeoutError, ConnectionError)):
            return True
        names = {base.__name__.lower() for base in type(candidate).__mro__}
        if any("timeout" in name for name in names):
            return True
        if any(
            name in {"connectionerror", "connecterror"}
            or name.endswith("connectionerror")
            for name in names
        ):
            return True
    return False


def _call_free_metadata_with_retry(
    method: str,
    operation: Callable[[], Any],
    request_context: dict[str, Any] | None = None,
) -> tuple[Any, int]:
    if method not in FREE_METADATA_RETRY_METHODS:
        raise AcquisitionError(f"retry is not authorized for method {method}")
    terminal_message: str | None = None
    for attempt in range(1, FREE_METADATA_MAX_ATTEMPTS + 1):
        try:
            return operation(), attempt
        except Exception as exc:
            retryable = _is_transient_free_metadata_error(exc)
            if not retryable or attempt == FREE_METADATA_MAX_ATTEMPTS:
                attempts_label = "attempt" if attempt == 1 else "attempts"
                disposition = (
                    "transient_retry_budget_exhausted"
                    if retryable
                    else "non_transient_fail_fast"
                )
                context = request_context or {}
                identity_fields = []
                for field in (
                    "request_id",
                    "event_clock_id",
                    "segment",
                    "start",
                    "end",
                ):
                    if field in context:
                        identity_fields.append(f"{field}={context[field]}")
                identity = " ".join(identity_fields)
                status = _http_status(exc)
                terminal_message = (
                    f"{method} failed after {attempt} {attempts_label}; "
                    "free metadata terminal failure "
                    f"method={method} {identity} attempt_count={attempt} "
                    f"http_status={status if status is not None else 'none'} "
                    f"disposition={disposition} exception_type={type(exc).__name__}"
                )
            else:
                time.sleep(FREE_METADATA_RETRY_BACKOFF_SECONDS[attempt - 1])
                continue
        break
    if terminal_message is not None:
        # Construct and raise only after leaving the handler so the sanitized
        # public error has no implicit __context__ link to the SDK exception.
        raise AcquisitionError(terminal_message)
    raise AssertionError("unreachable free metadata retry state")


def _request_args(window: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbols": [SYMBOL],
        "stype_in": STYPE_IN,
        "start": window["start"],
        "end": window["end"],
    }


def _timeseries_request_args(window: dict[str, Any]) -> dict[str, Any]:
    return {**_request_args(window), "stype_out": STYPE_OUT}


def _quote_windows(
    client: Any,
    windows: list[dict[str, Any]],
    *,
    client_factory: Callable[[], Any] | None,
    workers: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if workers < 1 or workers > 16:
        raise AcquisitionError("metadata quote workers must be between 1 and 16")
    local = threading.local()

    def quote(window: dict[str, Any]) -> tuple[dict[str, Any], int, int]:
        metadata = client.metadata
        if client_factory is not None:
            if not hasattr(local, "client"):
                local.client = client_factory()
            metadata = local.client.metadata
        args = _request_args(window)
        request_context = {
            key: window[key]
            for key in ("request_id", "event_clock_id", "segment", "start", "end")
            if key in window
        }
        cost_raw, cost_attempts = _call_free_metadata_with_retry(
            "metadata.get_cost",
            lambda: metadata.get_cost(mode=COST_MODE, **args),
            request_context,
        )
        cost = float(cost_raw)
        # SDK 0.54.0 get_billable_size has no mode parameter. Every data-shaping
        # argument is byte-for-byte identical to the historical-streaming quote.
        size_raw, size_attempts = _call_free_metadata_with_retry(
            "metadata.get_billable_size",
            lambda: metadata.get_billable_size(**args),
            request_context,
        )
        size = int(size_raw)
        if not math.isfinite(cost) or cost < 0 or size < 0:
            raise AcquisitionError(
                f"invalid free quote for {window['event_clock_id']}: cost={cost}, size={size}"
            )
        identity = {"event_clock_id": window["event_clock_id"]}
        if "request_id" in window:
            identity.update(
                {
                    "request_id": window["request_id"],
                    "segment": window["segment"],
                }
            )
        return (
            {
                **identity,
                "start": window["start"],
                "end": window["end"],
                "estimated_usd": cost,
                "billable_bytes": size,
            },
            cost_attempts,
            size_attempts,
        )

    if workers == 1:
        results = [quote(window) for window in windows]
    else:
        if client_factory is None:
            raise AcquisitionError("parallel metadata quote requires a per-thread client factory")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(quote, windows))
    return (
        [result[0] for result in results],
        {
            "metadata.get_cost": sum(result[1] for result in results),
            "metadata.get_billable_size": sum(result[2] for result in results),
        },
    )


def quote_plan(
    *,
    client: Any,
    plan: dict[str, Any],
    sdk_version: str,
    billable_size_authorized: bool,
    client_factory: Callable[[], Any] | None = None,
    workers: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Production quote entrypoint with fail-closed design authority."""

    if plan.get("profile") == DESIGN_SEGMENTS_PROFILE:
        if not billable_size_authorized:
            raise AcquisitionError("metadata.get_billable_size is not authorized")
        request_items = plan.get("requests")
        if not isinstance(request_items, list):
            raise AcquisitionError("acquisition plan lacks canonical request items")
        bindings = verify_design_segments_bound_contract(
            require_global_registry=True
        )
        if sha256_file(REGISTRY_PATH) != bindings["registry_sha256"]:
            raise AcquisitionError(
                "global registry changed while the quote start was binding"
            )
        _validate_profile_plan(plan, require_quote=False)
        if plan.get("bindings") != bindings:
            raise AcquisitionError(
                "offline plan bindings do not match the quote start contract"
            )
        if sdk_version != DATABENTO_SDK_VERSION:
            raise AcquisitionError(
                "Databento SDK version mismatch: required "
                f"{DATABENTO_SDK_VERSION}, got {sdk_version}"
            )
        # This guard must remain before the canonical validator and every use of
        # client, client_factory, metadata counters or filesystem state.
        _require_design_remote_reopen(bindings)
    return _quote_plan_after_authority_check(
        client=client,
        plan=plan,
        sdk_version=sdk_version,
        billable_size_authorized=billable_size_authorized,
        client_factory=client_factory,
        workers=workers,
    )


def _quote_plan_after_authority_check(
    *,
    client: Any,
    plan: dict[str, Any],
    sdk_version: str,
    billable_size_authorized: bool,
    client_factory: Callable[[], Any] | None = None,
    workers: int = 1,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Lower-level historical quote mechanics; production uses quote_plan()."""

    if not billable_size_authorized:
        raise AcquisitionError("metadata.get_billable_size is not authorized")
    is_design = plan.get("profile") == DESIGN_SEGMENTS_PROFILE
    verify_profile = (
        verify_design_segments_bound_contract if is_design else verify_bound_contract
    )
    request_items = plan.get("requests") if is_design else plan.get("windows")
    expected_identities = DESIGN_REQUESTS if is_design else EXPECTED_CLOCKS
    if not isinstance(request_items, list):
        raise AcquisitionError("acquisition plan lacks canonical request items")
    bindings = verify_profile(require_global_registry=True)
    registry_at_start = _registry_snapshot()
    if sha256_file(REGISTRY_PATH) != bindings["registry_sha256"]:
        raise AcquisitionError("global registry changed while the quote start was binding")
    _validate_profile_plan(plan, require_quote=False)
    if plan.get("bindings") != bindings:
        raise AcquisitionError("offline plan bindings do not match the quote start contract")
    if sdk_version != DATABENTO_SDK_VERSION:
        raise AcquisitionError(
            f"Databento SDK version mismatch: required {DATABENTO_SDK_VERSION}, got {sdk_version}"
        )

    # This is deliberately the final local operation before the first remote call.
    validator_start = _validate_canonical_registry()
    dataset_range: dict[str, Any] | None = None
    symbology_summary: dict[str, Any] | None = None
    metadata_capability_counters = {
        "metadata.get_dataset_range": 0,
        "symbology.resolve": 0,
    }
    if not is_design:
        dataset_range = client.metadata.get_dataset_range(dataset=DATASET)
        first_date = str(request_items[0]["start"])[:10]
        last_end = _parse_utc(request_items[-1]["end"])
        resolve_end = (last_end.date() + timedelta(days=1)).isoformat()
        symbology = client.symbology.resolve(
            dataset=DATASET,
            symbols=[SYMBOL],
            stype_in=STYPE_IN,
            stype_out=STYPE_OUT,
            start_date=first_date,
            end_date=resolve_end,
        )
        if not isinstance(symbology, dict):
            raise AcquisitionError("symbology.resolve returned an invalid payload")
        if SYMBOL in {str(item) for item in symbology.get("not_found", [])}:
            raise AcquisitionError(f"continuous symbol did not resolve: {SYMBOL}")
        if not symbology.get("result"):
            raise AcquisitionError(f"continuous symbol resolution is empty: {SYMBOL}")
        symbology_summary = {
            "result_key_count": len(symbology.get("result", {})),
            "partial_count": len(symbology.get("partial", [])),
            "not_found": symbology.get("not_found", []),
            "continuous_symbol_resolved": True,
        }
        metadata_capability_counters = {
            "metadata.get_dataset_range": 1,
            "symbology.resolve": 1,
        }

    quotes, free_metadata_attempts = _quote_windows(
        client,
        list(request_items),
        client_factory=client_factory,
        workers=workers,
    )
    # A free quote may survive unrelated append-only registry activity, but the
    # bound hypothesis row and every frozen artifact remain exact.
    end_bindings = verify_profile(require_global_registry=False)
    validator_end = _validate_canonical_registry()
    registry_at_end = _registry_snapshot()
    if hashlib.sha256(registry_at_end).hexdigest().upper() != end_bindings["registry_sha256"]:
        raise AcquisitionError("global registry changed while quote completion was binding")
    drift_observed = _validate_append_only_registry_drift(
        registry_at_start, registry_at_end
    )
    registry_boundary = {
        "start_sha256": bindings["registry_sha256"],
        "end_sha256": end_bindings["registry_sha256"],
        "append_only_drift_observed": drift_observed,
    }
    registry_validator_boundary = {
        "start_result": validator_start,
        "end_result": validator_end,
    }

    quoted = copy.deepcopy(plan)
    quoted["generated_at_utc"] = utc_now()
    quoted["quoted_at_utc"] = utc_now()
    quoted["status"] = (
        "QUOTED_DESIGN_SEGMENTS_METADATA_ONLY_NOT_DOWNLOADED"
        if is_design
        else "QUOTED_METADATA_ONLY_NOT_DOWNLOADED"
    )
    quoted["bindings"] = bindings
    quoted["registry_quote_boundary"] = registry_boundary
    quoted["registry_validator_boundary"] = registry_validator_boundary
    quoted["quotes"] = quotes
    quoted["quote_coverage"] = {
        "quoted_identities": len(quotes),
        "expected_identities": expected_identities,
    }
    quoted["estimated_total_usd"] = sum(item["estimated_usd"] for item in quotes)
    quoted["estimated_total_billable_bytes"] = sum(
        item["billable_bytes"] for item in quotes
    )
    quoted["databento_sdk_version"] = sdk_version
    quoted["dataset_range"] = dataset_range
    quoted["symbology"] = symbology_summary
    counters = _zero_api_counters()
    counters.update(
        {
            **free_metadata_attempts,
            **metadata_capability_counters,
        }
    )
    quoted["api_method_counters"] = counters
    quoted["plan_id"] = plan_id(quoted)
    _validate_profile_plan(quoted, require_quote=True)

    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "status": "FREE_METADATA_QUOTE_COMPLETE_NO_PAID_REQUEST",
        "profile": quoted["profile"],
        "hypothesis_id": quoted["hypothesis_id"],
        "plan_id": quoted["plan_id"],
        "clock": quoted["clock"],
        "bindings": bindings,
        "registry_quote_boundary": copy.deepcopy(registry_boundary),
        "registry_validator_boundary": copy.deepcopy(registry_validator_boundary),
        "databento_sdk_version": sdk_version,
        "dataset": DATASET,
        "schema": SCHEMA,
        "symbol": SYMBOL,
        "stype_in": STYPE_IN,
        "stype_out": STYPE_OUT,
        "cost_mode": COST_MODE,
        "free_metadata_retry_policy": copy.deepcopy(
            quoted["free_metadata_retry_policy"]
        ),
        "dataset_range": copy.deepcopy(dataset_range),
        "symbology": copy.deepcopy(quoted["symbology"]),
        "quote_coverage": copy.deepcopy(quoted["quote_coverage"]),
        "quotes": copy.deepcopy(quotes),
        "estimated_total_usd": quoted["estimated_total_usd"],
        "estimated_total_billable_bytes": quoted["estimated_total_billable_bytes"],
        "api_method_counters": counters,
        "timeseries_calls": 0,
        "batch_calls": 0,
        "paid_request_made": False,
        "outcome_fields_used": False,
        "price_data_read": False,
        "api_key_stored": False,
    }
    receipt["receipt_id"] = plan_id(receipt)
    validate_quote_receipt(receipt, quoted)
    return quoted, receipt


def validate_quote_receipt(receipt: dict[str, Any], plan: dict[str, Any]) -> None:
    _validate_profile_plan(plan, require_quote=True)
    if receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise AcquisitionError("metadata quote receipt schema mismatch")
    if receipt.get("plan_id") != plan.get("plan_id"):
        raise AcquisitionError("metadata quote receipt plan ID mismatch")
    if receipt.get("receipt_id") != plan_id(receipt):
        raise AcquisitionError("metadata quote receipt ID mismatch")
    exact_fields = {
        "status": "FREE_METADATA_QUOTE_COMPLETE_NO_PAID_REQUEST",
        "profile": plan["profile"],
        "hypothesis_id": plan["hypothesis_id"],
        "plan_id": plan["plan_id"],
        "clock": plan["clock"],
        "bindings": plan["bindings"],
        "registry_quote_boundary": plan["registry_quote_boundary"],
        "registry_validator_boundary": plan["registry_validator_boundary"],
        "databento_sdk_version": plan["databento_sdk_version"],
        "dataset": plan["dataset"],
        "schema": plan["schema"],
        "symbol": plan["symbol"],
        "stype_in": plan["stype_in"],
        "stype_out": plan["stype_out"],
        "cost_mode": plan["cost_mode"],
        "free_metadata_retry_policy": plan["free_metadata_retry_policy"],
        "dataset_range": plan["dataset_range"],
        "symbology": plan["symbology"],
        "quote_coverage": plan["quote_coverage"],
        "quotes": plan["quotes"],
        "estimated_total_usd": plan["estimated_total_usd"],
        "estimated_total_billable_bytes": plan["estimated_total_billable_bytes"],
        "api_method_counters": plan["api_method_counters"],
        "timeseries_calls": plan["timeseries_calls"],
        "paid_request_made": plan["paid_request_made"],
        "outcome_fields_used": plan["outcome_fields_used"],
        "price_data_read": plan["price_data_read"],
    }
    for field, expected in exact_fields.items():
        if receipt.get(field) != expected:
            raise AcquisitionError(
                f"metadata quote receipt exact reconciliation mismatch: {field}"
            )
    expected_identities = (
        DESIGN_REQUESTS
        if plan.get("profile") == DESIGN_SEGMENTS_PROFILE
        else EXPECTED_CLOCKS
    )
    if len(receipt["quotes"]) != expected_identities:
        raise AcquisitionError("metadata quote receipt exact reconciliation mismatch: coverage")
    if receipt.get("timeseries_calls") != 0 or receipt.get("batch_calls") != 0:
        raise AcquisitionError("metadata quote receipt contains forbidden call counters")
    if receipt.get("paid_request_made") is not False:
        raise AcquisitionError("metadata quote receipt does not prove zero paid requests")
    if receipt.get("api_key_stored") is not False:
        raise AcquisitionError("metadata quote receipt claims API key persistence")


def _resolve_within_exact_design_root(
    path: Path, *, root: Path, label: str
) -> Path:
    root_resolved = root.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise AcquisitionError(
            f"{label} escapes exact design root: {resolved}"
        ) from exc
    return resolved


@contextmanager
def exclusive_design_finalize_lock(root: Path):
    root = ensure_design_segments_output_root(root)
    lock_path = _resolve_within_exact_design_root(
        root / DESIGN_FINALIZE_LOCK_NAME,
        root=root,
        label="design finalize lock",
    )
    token = uuid.uuid4().hex
    payload = json.dumps(
        {"token": token, "pid": os.getpid(), "acquired_at_utc": utc_now()},
        sort_keys=True,
    ).encode("utf-8")
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise AcquisitionError(
            f"exclusive design finalize lock is already held: {lock_path}"
        ) from exc
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        yield lock_path
    finally:
        try:
            safe_lock_path = _resolve_within_exact_design_root(
                lock_path, root=root, label="design finalize lock"
            )
            current = json.loads(safe_lock_path.read_text(encoding="utf-8"))
            if current.get("token") != token:
                raise AcquisitionError("exclusive design finalize lock ownership changed")
            safe_lock_path.unlink()
        except AcquisitionError:
            raise
        except Exception as exc:
            raise AcquisitionError(
                f"cannot safely release exclusive design finalize lock: {lock_path}"
            ) from exc


def _build_design_storage_assessment(
    *, root: Path, quoted: dict[str, Any]
) -> dict[str, Any]:
    usage = shutil.disk_usage(root)
    estimated_bytes = int(quoted["estimated_total_billable_bytes"])
    return {
        "schema_version": DESIGN_STORAGE_SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "status": "DESIGN_QUOTE_STORAGE_ASSESSED_NO_DOWNLOAD",
        "profile": DESIGN_SEGMENTS_PROFILE,
        "hypothesis_id": DESIGN_HYPOTHESIS_ID,
        "plan_id": quoted["plan_id"],
        "output_root": str(root),
        "estimated_total_usd": quoted["estimated_total_usd"],
        "estimated_total_billable_bytes": estimated_bytes,
        "free_bytes_at_assessment": usage.free,
        "estimated_bytes_fit": usage.free >= estimated_bytes,
        "raw_dbn_files": 0,
        "timeseries_calls": 0,
        "paid_request_made": False,
        "outcome_fields_used": False,
    }


def _finalize_design_quote_artifacts_locked(
    *, root: Path, quoted: dict[str, Any], receipt: dict[str, Any]
) -> dict[str, Any]:
    """Read back a reconciled design quote, then snapshot immutable local evidence."""

    root = ensure_design_segments_output_root(root)
    validate_design_segments_plan(quoted, require_quote=True)
    validate_quote_receipt(receipt, quoted)
    active_plan_path = root / PLAN_NAME
    active_receipt_path = root / DESIGN_QUOTE_RECEIPT_NAME
    if not active_plan_path.is_file() or not active_receipt_path.is_file():
        raise AcquisitionError("design quote active plan/receipt readback is incomplete")
    active_plan = _load_json(active_plan_path)
    active_receipt = _load_json(active_receipt_path)
    if active_plan != quoted or active_receipt != receipt:
        raise AcquisitionError("design quote active plan/receipt readback mismatch")
    validate_design_segments_plan(active_plan, require_quote=True)
    validate_quote_receipt(active_receipt, active_plan)
    parent_evidence = verify_immutable_quote_evidence()

    evidence_name = f"FREE_QUOTE_{quoted['plan_id'][:8]}"
    evidence_parent = root / "evidence"
    evidence_root = evidence_parent / evidence_name
    _resolve_within_exact_design_root(
        evidence_parent, root=root, label="design evidence parent"
    )
    _resolve_within_exact_design_root(
        evidence_root, root=root, label="design evidence destination"
    )
    if evidence_parent.exists() and not evidence_parent.is_dir():
        raise AcquisitionError("design evidence parent is not a directory")
    if evidence_root.exists():
        raise AcquisitionError(
            f"immutable design quote evidence exists and cannot be overwritten: {evidence_root}"
        )
    assessment = _build_design_storage_assessment(root=root, quoted=quoted)
    assessment_path = root / DESIGN_STORAGE_ASSESSMENT_NAME
    write_json_atomic(assessment_path, assessment)
    assessment_readback = _load_json(assessment_path)
    if assessment_readback != assessment:
        raise AcquisitionError("design storage assessment readback mismatch")

    evidence_parent.mkdir(parents=True, exist_ok=True)
    _resolve_within_exact_design_root(
        evidence_parent, root=root, label="design evidence parent"
    )
    partial = evidence_parent / f".{evidence_name}.{uuid.uuid4().hex}.partial"
    _resolve_within_exact_design_root(
        partial, root=root, label="design evidence partial"
    )
    partial.mkdir()
    _resolve_within_exact_design_root(
        partial, root=root, label="design evidence partial"
    )
    try:
        child_payloads = {
            PLAN_NAME: active_plan,
            DESIGN_QUOTE_RECEIPT_NAME: active_receipt,
            DESIGN_STORAGE_ASSESSMENT_NAME: assessment_readback,
        }
        for filename, payload in child_payloads.items():
            write_json_atomic(partial / filename, payload)
        files = [
            {
                "path": filename,
                "sha256": sha256_file(partial / filename),
            }
            for filename in (
                PLAN_NAME,
                DESIGN_QUOTE_RECEIPT_NAME,
                DESIGN_STORAGE_ASSESSMENT_NAME,
            )
        ]
        manifest = {
            "schema_version": DESIGN_EVIDENCE_SCHEMA_VERSION,
            "created_at_utc": utc_now(),
            "status": "IMMUTABLE_DESIGN_FREE_QUOTE_COMPLETE_NO_PAID_REQUEST",
            "profile": DESIGN_SEGMENTS_PROFILE,
            "hypothesis_id": DESIGN_HYPOTHESIS_ID,
            "plan_id": quoted["plan_id"],
            "files": files,
            "quote": {
                "requests": DESIGN_REQUESTS,
                "estimated_total_usd": quoted["estimated_total_usd"],
                "estimated_total_billable_bytes": quoted[
                    "estimated_total_billable_bytes"
                ],
                "metadata_get_cost_attempts": quoted["api_method_counters"][
                    "metadata.get_cost"
                ],
                "metadata_get_billable_size_attempts": quoted[
                    "api_method_counters"
                ]["metadata.get_billable_size"],
                "timeseries_calls": 0,
                "paid_request_made": False,
            },
            "parent_quote_evidence_manifest_sha256": parent_evidence[
                "manifest_sha256"
            ],
            "raw_dbn_files": 0,
            "immutable_snapshot": True,
        }
        write_json_atomic(partial / "manifest.json", manifest)
        manifest_readback = _load_json(partial / "manifest.json")
        if manifest_readback != manifest:
            raise AcquisitionError("design quote evidence manifest readback mismatch")
        for item in files:
            if sha256_file(partial / item["path"]) != item["sha256"]:
                raise AcquisitionError(
                    f"design quote evidence child hash mismatch: {item['path']}"
                )
        safe_partial = _resolve_within_exact_design_root(
            partial, root=root, label="design evidence partial"
        )
        safe_destination = _resolve_within_exact_design_root(
            evidence_root, root=root, label="design evidence destination"
        )
        safe_partial.rename(safe_destination)
    except Exception:
        if partial.exists():
            safe_partial = _resolve_within_exact_design_root(
                partial, root=root, label="design evidence partial cleanup"
            )
            shutil.rmtree(safe_partial)
        raise
    verify_immutable_quote_evidence()
    return {
        "storage_assessment_path": str(assessment_path),
        "storage_assessment_sha256": sha256_file(assessment_path),
        "evidence_root": str(evidence_root),
        "manifest_path": str(evidence_root / "manifest.json"),
        "manifest_sha256": sha256_file(evidence_root / "manifest.json"),
    }


def finalize_design_quote_artifacts(
    *, root: Path, quoted: dict[str, Any], receipt: dict[str, Any]
) -> dict[str, Any]:
    root = ensure_design_segments_output_root(root)
    with exclusive_design_finalize_lock(root):
        return _finalize_design_quote_artifacts_locked(
            root=root, quoted=quoted, receipt=receipt
        )


def validate_download_authority(
    *, plan: dict[str, Any], expected_plan_id: str, approve_max_usd: float
) -> None:
    if expected_plan_id != plan.get("plan_id"):
        raise AcquisitionError(
            f"download requires expected plan ID {plan.get('plan_id')}, got {expected_plan_id}"
        )
    if not math.isfinite(approve_max_usd) or approve_max_usd <= 0:
        raise AcquisitionError("approved USD ceiling must be a positive finite number")


def _require_paid_download_reopen(bindings: dict[str, Any]) -> None:
    if (
        bindings.get("latest_state") == LATEST_STATE
        and bindings.get("latest_verdict") == LATEST_VERDICT
        and bindings.get("latest_row_sha256") == LATEST_ROW_SHA256
    ):
        raise AcquisitionError(
            "payment authority unmet: EVENT-CLOB is parked; a new Owner-authorized "
            "amendment with an explicit USD ceiling must rebind the latest registry state"
        )
    raise AcquisitionError(
        "payment authority unmet: V9 grants no paid download authority"
    )


def _require_design_remote_reopen(bindings: dict[str, Any]) -> None:
    if (
        bindings.get("latest_state") == DESIGN_LATEST_STATE
        and bindings.get("latest_verdict") == DESIGN_LATEST_VERDICT
        and bindings.get("latest_row_sha256")
        == DESIGN_SUCCESSOR_ROW_SHA256_SEQUENCE[-1]
        and bindings.get("task_packet_v14_sha256") == TASK_PACKET_V14_SHA256
    ):
        raise AcquisitionError(
            "payment authority unmet: V14 permits remote design source access only "
            "through the exact design-acquire command; direct quote/download is blocked"
        )
    raise AcquisitionError(
        "payment authority unmet: exact V14 design acquisition authority is absent"
    )


def _verify_design_acquisition_authority(
    *,
    plan: dict[str, Any],
    authorization_basis_plan_id: str,
    approve_max_usd: float,
    root: Path,
    sdk_version: str,
) -> dict[str, Any]:
    bindings = verify_design_segments_bound_contract(require_global_registry=True)
    if (
        bindings.get("task_packet_v14_sha256") != TASK_PACKET_V14_SHA256
        or bindings.get("latest_state") != DESIGN_LATEST_STATE
        or bindings.get("latest_verdict") != DESIGN_LATEST_VERDICT
        or bindings.get("successor_row_sha256_sequence")
        != list(DESIGN_SUCCESSOR_ROW_SHA256_SEQUENCE)
        or bindings.get("immutable_design_quote_evidence", {}).get("plan_id")
        != DESIGN_QUOTE_EVIDENCE_PLAN_ID
        or bindings.get("owner_authorization")
        != {
            "verbatim_sha256": OWNER_AUTHORIZATION_VERBATIM_SHA256,
            "authorization_basis_plan_id": DESIGN_QUOTE_EVIDENCE_PLAN_ID,
            "approved_max_usd": DESIGN_APPROVED_MAX_USD,
        }
    ):
        raise AcquisitionError("exact V14 design acquisition bindings are absent")
    if authorization_basis_plan_id != DESIGN_QUOTE_EVIDENCE_PLAN_ID:
        raise AcquisitionError("V14 authorization basis plan ID mismatch")
    if (
        isinstance(approve_max_usd, bool)
        or not isinstance(approve_max_usd, (int, float))
        or not math.isfinite(float(approve_max_usd))
        or float(approve_max_usd) != DESIGN_APPROVED_MAX_USD
    ):
        raise AcquisitionError("V14 approved aggregate ceiling must be exactly USD 3.50")
    if Path(root).resolve() != DESIGN_SEGMENTS_ROOT.resolve():
        raise AcquisitionError("V14 design acquisition root must be the exact D-side root")
    if sdk_version != DATABENTO_SDK_VERSION:
        raise AcquisitionError(
            f"Databento SDK version mismatch: required {DATABENTO_SDK_VERSION}, got {sdk_version}"
    )
    _validate_profile_plan(plan, require_quote=False)
    if _without_registry_sha256(plan.get("bindings")) != _without_registry_sha256(
        bindings
    ):
        raise AcquisitionError("active offline plan does not carry exact V14 bindings")
    return bindings


@contextmanager
def exclusive_paid_download_lock(root: Path):
    """Hold an atomic, fail-closed single-writer lock for the paid lane."""

    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = (root / PAID_LOCK_NAME).resolve()
    try:
        lock_path.relative_to(root)
    except ValueError as exc:
        raise AcquisitionError("paid download lock escaped the approved data root") from exc
    token = uuid.uuid4().hex
    payload = json.dumps(
        {"token": token, "pid": os.getpid(), "acquired_at_utc": utc_now()},
        sort_keys=True,
    ).encode("utf-8")
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise AcquisitionError(
            f"exclusive paid download lock is already held: {lock_path}"
        ) from exc
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        yield lock_path
    finally:
        try:
            current = json.loads(lock_path.read_text(encoding="utf-8"))
            if current.get("token") != token:
                raise AcquisitionError("exclusive paid download lock ownership changed")
            lock_path.unlink()
        except AcquisitionError:
            raise
        except Exception as exc:
            raise AcquisitionError(
                f"cannot safely release exclusive paid download lock: {lock_path}"
            ) from exc


def _quote_basis_from_live_files(
    *, plan_path: Path, receipt_path: Path
) -> dict[str, Any]:
    """Capture exact live quote bytes before the single live files are replaced."""

    for label, path in (("plan", plan_path), ("receipt", receipt_path)):
        if _is_reparse_path(path) or not path.is_file():
            raise AcquisitionError(
                f"historical live quote {label} evidence is missing or reparse-backed"
            )
    try:
        plan_bytes = plan_path.read_bytes()
        receipt_bytes = receipt_path.read_bytes()
        plan_raw = plan_bytes.decode("utf-8")
        receipt_raw = receipt_bytes.decode("utf-8")
        plan = json.loads(plan_raw)
        receipt = json.loads(receipt_raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AcquisitionError("historical live quote evidence is unreadable") from exc
    if not isinstance(plan, dict) or not isinstance(receipt, dict):
        raise AcquisitionError("historical live quote evidence is not a JSON object")
    try:
        validate_design_segments_plan(plan, require_quote=True)
        validate_quote_receipt(receipt, plan)
    except AcquisitionError as exc:
        raise AcquisitionError(
            "historical live quote evidence validation failed"
        ) from exc
    return {
        "schema_version": "event_clob_design_embedded_quote_basis.v1",
        "plan_id": plan["plan_id"],
        "plan_sha256": hashlib.sha256(plan_bytes).hexdigest().upper(),
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(),
        "plan_json_utf8": plan_raw,
        "receipt_json_utf8": receipt_raw,
    }


def _validate_embedded_quote_basis(entry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if entry.get("schema_version") != "event_clob_design_embedded_quote_basis.v1":
        raise AcquisitionError("historical quote evidence schema mismatch")
    plan_raw = entry.get("plan_json_utf8")
    receipt_raw = entry.get("receipt_json_utf8")
    if not isinstance(plan_raw, str) or not isinstance(receipt_raw, str):
        raise AcquisitionError("historical quote evidence lacks exact JSON bytes")
    plan_bytes = plan_raw.encode("utf-8")
    receipt_bytes = receipt_raw.encode("utf-8")
    if (
        entry.get("plan_sha256")
        != hashlib.sha256(plan_bytes).hexdigest().upper()
        or entry.get("receipt_sha256")
        != hashlib.sha256(receipt_bytes).hexdigest().upper()
    ):
        raise AcquisitionError("historical quote evidence embedded SHA mismatch")
    try:
        plan = json.loads(plan_raw)
        receipt = json.loads(receipt_raw)
    except json.JSONDecodeError as exc:
        raise AcquisitionError("historical quote evidence embedded JSON is invalid") from exc
    if not isinstance(plan, dict) or not isinstance(receipt, dict):
        raise AcquisitionError("historical quote evidence embedded JSON is not an object")
    try:
        validate_design_segments_plan(plan, require_quote=True)
        validate_quote_receipt(receipt, plan)
    except AcquisitionError as exc:
        raise AcquisitionError("historical quote evidence validation failed") from exc
    if entry.get("plan_id") != plan.get("plan_id"):
        raise AcquisitionError("historical quote evidence plan ID mismatch")
    return plan, receipt


def _append_quote_basis_history(
    manifest: dict[str, Any], basis: dict[str, Any]
) -> None:
    history = manifest.setdefault("quote_basis_history", [])
    if not isinstance(history, list):
        raise AcquisitionError("download manifest quote basis history is invalid")
    matching = [item for item in history if item.get("plan_id") == basis.get("plan_id")]
    if matching:
        if len(matching) != 1:
            raise AcquisitionError("historical quote evidence plan ID was rebound")
        historical_plan, historical_receipt = _validate_embedded_quote_basis(
            matching[0]
        )
        current_plan, current_receipt = _validate_embedded_quote_basis(basis)
        if (
            _stable_payload(historical_plan) != _stable_payload(current_plan)
            or _stable_payload(historical_receipt)
            != _stable_payload(current_receipt)
        ):
            raise AcquisitionError("historical quote evidence plan ID was rebound")
        return
    history.append(copy.deepcopy(basis))


def _bind_completed_downloads_to_quote_basis(
    *, manifest: dict[str, Any], basis: dict[str, Any]
) -> None:
    plan, _receipt = _validate_embedded_quote_basis(basis)
    _append_quote_basis_history(manifest, basis)
    quote_by_id = {item["request_id"]: item for item in plan["quotes"]}
    for download in manifest.get("downloads", []):
        # Only a legacy pre-history entry may be attached to the current live
        # files. An entry already bound to A must remain byte-unchanged when a
        # later resume's latest live file is B; its own history entry is the
        # sole authority for estimate reconciliation.
        if download.get("quote_basis_plan_id") is not None:
            continue
        request_id = str(download.get("request_id", ""))
        quote = quote_by_id.get(request_id)
        if quote is None:
            raise AcquisitionError(
                "completed request is absent from historical live quote evidence"
            )
        if (
            download.get("estimated_usd") != quote.get("estimated_usd")
            or download.get("billable_bytes") != quote.get("billable_bytes")
        ):
            raise AcquisitionError(
                "completed estimate drifted from historical live quote evidence"
            )
        download["quote_basis_plan_id"] = plan["plan_id"]
    # Validate every pre-bound and newly migrated entry through its exact
    # history basis. This detects missing A/B history or estimate/hash drift
    # without rewriting any already-bound download dictionary.
    _completed_incurred_estimate(manifest)


def _completed_incurred_estimate(manifest: dict[str, Any]) -> float:
    downloads = manifest.get("downloads", [])
    if not downloads:
        return 0.0
    history = manifest.get("quote_basis_history")
    if not isinstance(history, list) or not history:
        raise AcquisitionError(
            "completed downloads lack historical quote evidence; manual authority required"
        )
    basis_by_id: dict[str, dict[str, Any]] = {}
    for entry in history:
        if not isinstance(entry, dict):
            raise AcquisitionError("historical quote evidence entry is invalid")
        plan, _receipt = _validate_embedded_quote_basis(entry)
        plan_id_value = str(plan["plan_id"])
        if plan_id_value in basis_by_id:
            raise AcquisitionError("historical quote evidence contains duplicate plan IDs")
        basis_by_id[plan_id_value] = plan
    total = 0.0
    for download in downloads:
        plan_id_value = str(download.get("quote_basis_plan_id", ""))
        basis_plan = basis_by_id.get(plan_id_value)
        if basis_plan is None:
            raise AcquisitionError(
                "completed request lacks bound historical quote evidence"
            )
        quote_by_id = {item["request_id"]: item for item in basis_plan["quotes"]}
        quote = quote_by_id.get(str(download.get("request_id", "")))
        if quote is None or (
            download.get("estimated_usd") != quote.get("estimated_usd")
            or download.get("billable_bytes") != quote.get("billable_bytes")
        ):
            raise AcquisitionError(
                "completed estimate drifted from bound historical quote evidence"
            )
        estimate = download.get("estimated_usd")
        if (
            not isinstance(estimate, (int, float))
            or isinstance(estimate, bool)
            or not math.isfinite(float(estimate))
            or float(estimate) < 0
        ):
            raise AcquisitionError("completed incurred estimate is invalid")
        total += float(estimate)
    return total


def validate_existing_download_manifest(
    *,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    root: Path,
    dbn_validator: Callable[..., int] | None = None,
    require_complete: bool = False,
) -> set[str]:
    """Strictly reconcile a resumable manifest and every adopted DBN file."""

    raw_root = _validated_design_raw_root(root, create=False)
    is_design = plan.get("profile") == DESIGN_SEGMENTS_PROFILE
    _validate_profile_plan(plan, require_quote=True)
    if manifest.get("schema_version") != DOWNLOAD_SCHEMA_VERSION:
        raise AcquisitionError("download manifest schema mismatch")
    if manifest.get("plan_id") != plan.get("plan_id"):
        raise AcquisitionError("download manifest plan ID mismatch")
    if manifest.get("in_flight") is not None:
        raise AcquisitionError(
            "unresolved in_flight paid request; manual reconciliation required, no retry"
        )
    if manifest.get("outcome_fields_used") is not False:
        raise AcquisitionError("download manifest crossed the outcome boundary")
    if is_design and (
        manifest.get("price_data_read") is not False
        or manifest.get("validation_source_sealed") is not True
    ):
        raise AcquisitionError("design download manifest crossed a sealed boundary")
    downloads = manifest.get("downloads")
    if not isinstance(downloads, list):
        raise AcquisitionError("download manifest downloads must be a list")
    if manifest.get("paid_requests_completed") != len(downloads):
        raise AcquisitionError("download manifest paid request count mismatch")
    if is_design and (
        manifest.get("timeseries_calls") != len(downloads)
        or manifest.get("paid_request_made") is not bool(downloads)
    ):
        raise AcquisitionError("design download manifest paid counters do not reconcile")
    if is_design:
        _completed_incurred_estimate(manifest)
    approved = manifest.get("approved_max_usd")
    live_total = manifest.get("live_estimated_total_usd")
    if not isinstance(approved, (int, float)) or not math.isfinite(float(approved)) or approved <= 0:
        raise AcquisitionError("download manifest approved USD ceiling is invalid")
    if not isinstance(live_total, (int, float)) or not math.isfinite(float(live_total)) or live_total < 0:
        raise AcquisitionError("download manifest live estimate is invalid")

    request_items = plan["requests"] if is_design else plan["windows"]
    identity_key = "request_id" if is_design else "event_clock_id"
    expected_count = DESIGN_REQUESTS if is_design else EXPECTED_CLOCKS
    canonical_by_id = {item[identity_key]: item for item in request_items}
    if len(canonical_by_id) != expected_count:
        raise AcquisitionError("download plan canonical identity count mismatch")
    seen_ids: set[str] = set()
    seen_filenames: set[str] = set()
    validator = dbn_validator or _load_foundation().validate_dbn_file
    for entry in downloads:
        if not isinstance(entry, dict):
            raise AcquisitionError("download manifest contains an invalid entry")
        canonical_id = str(entry.get(identity_key, ""))
        filename = str(entry.get("filename", ""))
        if canonical_id in seen_ids or filename in seen_filenames:
            raise AcquisitionError("download manifest contains duplicate canonical identity")
        canonical = canonical_by_id.get(canonical_id)
        if canonical is None:
            raise AcquisitionError("download manifest identity is absent from the canonical plan")
        if {key: entry.get(key) for key in canonical} != canonical:
            raise AcquisitionError("download manifest entry does not match its canonical plan window")
        seen_ids.add(canonical_id)
        seen_filenames.add(filename)

        output, _partial = _validated_design_raw_artifacts(
            root=root, filename=filename, require_raw_root=True
        )
        if not output.is_file():
            raise AcquisitionError(f"download manifest DBN file is missing: {output}")
        stated_bytes = entry.get("bytes")
        if not isinstance(stated_bytes, int) or isinstance(stated_bytes, bool):
            raise AcquisitionError("download manifest DBN byte count is invalid")
        if output.stat().st_size != stated_bytes:
            raise AcquisitionError(f"download manifest DBN byte count mismatch: {output}")
        if entry.get("sha256") != sha256_file(output):
            raise AcquisitionError(f"download manifest DBN SHA-256 mismatch: {output}")
        try:
            actual_records = int(validator(output, allow_zero=True))
        except Exception as exc:
            raise AcquisitionError(f"download manifest DBN validation failed: {output}") from exc
        if entry.get("records") != actual_records:
            raise AcquisitionError(f"download manifest DBN record count mismatch: {output}")
        source_empty = entry.get("source_empty")
        charged_empty = entry.get("charged_empty_evidence")
        if actual_records == 0:
            required_empty_evidence = {
                "paid_request_completed": True,
                "response_validated": True,
                "retry_prohibited": True,
            }
            if source_empty is not True or charged_empty != required_empty_evidence:
                raise AcquisitionError(
                    "download manifest empty response lacks charged-empty validation evidence"
                )
        elif source_empty is not False or charged_empty is not None:
            raise AcquisitionError("download manifest nonempty response flags are inconsistent")

    if raw_root.is_dir():
        disk_entries = list(raw_root.iterdir())
        for path in disk_entries:
            if (
                path.parent != raw_root
                or _is_reparse_path(path)
                or not path.is_file()
                or path.resolve(strict=False) != path
            ):
                raise AcquisitionError(
                    "download manifest raw directory contains invalid or reparse artifacts"
                )
        disk_files = {path.name for path in disk_entries}
        if disk_files != seen_filenames:
            raise AcquisitionError(
                "download manifest and on-disk DBN/partial file set do not reconcile"
            )
    elif downloads:
        raise AcquisitionError("download manifest raw directory is missing")

    complete_status = manifest.get("status") == "DOWNLOADED_FULL_DBN_VALIDATION_PASS"
    if (require_complete or complete_status) and len(seen_ids) != expected_count:
        raise AcquisitionError(
            f"download completion coverage is {len(seen_ids)}/{expected_count}"
        )
    return seen_ids


def _design_acquisition_receipt(
    *,
    status: str,
    bindings: dict[str, Any],
    live_plan: dict[str, Any],
    live_receipt: dict[str, Any],
    root: Path,
    timeseries_calls: int,
    paid_request_made: bool,
    download_manifest_sha256: str | None,
    capacity: dict[str, Any] | None = None,
    authorized_aggregate_usd: float | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "event_clob_design_acquisition_authority_receipt.v1",
        "generated_at_utc": utc_now(),
        "status": status,
        "profile": DESIGN_SEGMENTS_PROFILE,
        "hypothesis_id": DESIGN_HYPOTHESIS_ID,
        "task_packet_v13_sha256": TASK_PACKET_V13_SHA256,
        "task_packet_v14_sha256": TASK_PACKET_V14_SHA256,
        "owner_authorization_verbatim_sha256": OWNER_AUTHORIZATION_VERBATIM_SHA256,
        "authorization_basis_plan_id": DESIGN_QUOTE_EVIDENCE_PLAN_ID,
        "approved_max_usd": DESIGN_APPROVED_MAX_USD,
        "registry_sha256": bindings["registry_sha256"],
        "successor_row_sha256_sequence": list(DESIGN_SUCCESSOR_ROW_SHA256_SEQUENCE),
        "immutable_design_quote_manifest_sha256": (
            DESIGN_QUOTE_EVIDENCE_MANIFEST_SHA256
        ),
        "live_plan_id": live_plan["plan_id"],
        "live_plan_sha256": sha256_file(root / LIVE_REQUOTE_PLAN_NAME),
        "live_receipt_sha256": sha256_file(root / LIVE_REQUOTE_RECEIPT_NAME),
        "live_estimated_total_usd": live_plan["estimated_total_usd"],
        "live_estimated_total_billable_bytes": live_plan[
            "estimated_total_billable_bytes"
        ],
        "authorized_aggregate_usd": authorized_aggregate_usd,
        "download_manifest_sha256": download_manifest_sha256,
        "timeseries_calls": timeseries_calls,
        "paid_request_made": paid_request_made,
        "outcome_fields_used": False,
        "price_data_read": False,
        "validation_source_sealed": True,
        "capacity": capacity,
    }
    payload["receipt_id"] = plan_id(payload)
    return payload


def _raise_design_ceiling_blocker(
    *,
    bindings: dict[str, Any],
    live_plan: dict[str, Any],
    live_receipt: dict[str, Any],
    manifest: dict[str, Any],
    manifest_path: Path,
    authority_path: Path,
    root: Path,
    capacity: dict[str, Any] | None,
    authorized_aggregate_usd: float,
) -> None:
    completed = len(manifest.get("downloads", []))
    status = (
        "BLOCKED_LIVE_AGGREGATE_CEILING_NO_PAID_CALL"
        if completed == 0
        else "BLOCKED_LIVE_AGGREGATE_CEILING_BEFORE_NEXT_PAID_CALL"
    )
    receipt = _design_acquisition_receipt(
        status=status,
        bindings=bindings,
        live_plan=live_plan,
        live_receipt=live_receipt,
        root=root,
        timeseries_calls=completed,
        paid_request_made=completed > 0,
        download_manifest_sha256=sha256_file(manifest_path),
        capacity=capacity,
        authorized_aggregate_usd=authorized_aggregate_usd,
    )
    write_json_atomic(authority_path, receipt)
    raise AcquisitionError(
        "aggregate ceiling failure: completed incurred estimates plus fresh pending "
        f"estimates ${authorized_aggregate_usd:.12f} exceed USD 3.50"
    )


def _design_capacity_snapshot(root: Path, billable_bytes: int) -> dict[str, Any]:
    if billable_bytes < 0:
        raise AcquisitionError("capacity billable-byte basis is invalid")
    free_bytes = int(shutil.disk_usage(root).free)
    required_free_bytes = (2 * billable_bytes) + DESIGN_CAPACITY_RESERVE_BYTES
    return {
        "free_bytes": free_bytes,
        "billable_bytes_basis": billable_bytes,
        "required_free_bytes": required_free_bytes,
        "pass": free_bytes >= required_free_bytes,
    }


def _raise_design_capacity_blocker(
    *,
    bindings: dict[str, Any],
    live_plan: dict[str, Any],
    live_receipt: dict[str, Any],
    manifest: dict[str, Any],
    manifest_path: Path,
    authority_path: Path,
    root: Path,
    capacity: dict[str, Any],
    authorized_aggregate_usd: float,
) -> None:
    completed = len(manifest.get("downloads", []))
    status = (
        "BLOCKED_CAPACITY_RULE_NO_PAID_CALL"
        if completed == 0
        else "BLOCKED_CAPACITY_RULE_BEFORE_NEXT_PAID_CALL"
    )
    receipt = _design_acquisition_receipt(
        status=status,
        bindings=bindings,
        live_plan=live_plan,
        live_receipt=live_receipt,
        root=root,
        timeseries_calls=completed,
        paid_request_made=completed > 0,
        download_manifest_sha256=sha256_file(manifest_path),
        capacity=capacity,
        authorized_aggregate_usd=authorized_aggregate_usd,
    )
    write_json_atomic(authority_path, receipt)
    raise AcquisitionError(
        "capacity failure: free bytes are below 2x pending live billable bytes plus 1 GiB"
    )


def design_acquire(
    *,
    client: Any,
    metadata_client: Any,
    plan: dict[str, Any],
    authorization_basis_plan_id: str,
    approve_max_usd: float,
    root: Path,
    sdk_version: str,
) -> dict[str, Any]:
    """V13-only serial design acquisition under one quote-to-finish lock."""

    bindings = _verify_design_acquisition_authority(
        plan=plan,
        authorization_basis_plan_id=authorization_basis_plan_id,
        approve_max_usd=approve_max_usd,
        root=root,
        sdk_version=sdk_version,
    )
    safe_root = ensure_design_segments_output_root(root)
    safe_root.mkdir(parents=True, exist_ok=True)
    # Reject junction/reparse topology before lock, manifest initialization, or
    # any free/paid remote call. Resolving the raw path first would hide a
    # Windows junction and silently redirect writes outside the approved root.
    _validated_design_raw_root(safe_root, create=False)
    with exclusive_paid_download_lock(safe_root):
        live_plan_path = safe_root / LIVE_REQUOTE_PLAN_NAME
        live_receipt_path = safe_root / LIVE_REQUOTE_RECEIPT_NAME
        manifest_path = safe_root / DOWNLOAD_MANIFEST_NAME
        authority_path = safe_root / ACQUISITION_AUTHORITY_RECEIPT_NAME
        if authority_path.exists():
            raise AcquisitionError(
                "V13 acquisition authority receipt already exists; automatic rerun prohibited"
            )

        if manifest_path.is_file():
            if not live_plan_path.is_file() or not live_receipt_path.is_file():
                raise AcquisitionError(
                    "existing design manifest lacks historical live quote evidence; "
                    "manual reconciliation required"
                )
            existing_manifest = _load_json(manifest_path)
            historical_basis = _quote_basis_from_live_files(
                plan_path=live_plan_path, receipt_path=live_receipt_path
            )
            existing_live, _historical_receipt = _validate_embedded_quote_basis(
                historical_basis
            )
            # Preserve exact old plan/receipt bytes and bind every incurred
            # estimate before the single live quote files are overwritten.
            _bind_completed_downloads_to_quote_basis(
                manifest=existing_manifest, basis=historical_basis
            )
            write_json_atomic(manifest_path, existing_manifest)
            # This is intentionally before any new metadata quote. An unresolved
            # paid identity freezes the campaign for manual reconciliation.
            validate_existing_download_manifest(
                manifest=existing_manifest,
                plan=existing_live,
                root=safe_root,
            )
            manifest = existing_manifest
        else:
            manifest = {
                "schema_version": DOWNLOAD_SCHEMA_VERSION,
                "status": "LOCKED_NOT_REQUOTED",
                "profile": DESIGN_SEGMENTS_PROFILE,
                "hypothesis_id": DESIGN_HYPOTHESIS_ID,
                "authorization_basis_plan_id": DESIGN_QUOTE_EVIDENCE_PLAN_ID,
                "approved_max_usd": DESIGN_APPROVED_MAX_USD,
                "plan_id": None,
                "live_plan_id": None,
                "live_estimated_total_usd": 0.0,
                "live_estimated_total_billable_bytes": 0,
                "downloads": [],
                "in_flight": None,
                "paid_requests_completed": 0,
                "timeseries_calls": 0,
                "paid_request_made": False,
                "outcome_fields_used": False,
                "price_data_read": False,
                "validation_source_sealed": True,
                "quote_basis_history": [],
            }
            write_json_atomic(manifest_path, manifest)

        live_plan, live_receipt = _quote_plan_after_authority_check(
            client=metadata_client,
            plan=plan,
            sdk_version=sdk_version,
            billable_size_authorized=True,
            workers=1,
        )
        write_json_atomic(live_plan_path, live_plan)
        write_json_atomic(live_receipt_path, live_receipt)
        validate_design_segments_plan(live_plan, require_quote=True)
        validate_quote_receipt(live_receipt, live_plan)
        current_quote_basis = _quote_basis_from_live_files(
            plan_path=live_plan_path, receipt_path=live_receipt_path
        )
        _append_quote_basis_history(manifest, current_quote_basis)

        manifest["status"] = "LIVE_REQUOTE_COMPLETE_NOT_DOWNLOADED"
        manifest["plan_id"] = live_plan["plan_id"]
        manifest["live_plan_id"] = live_plan["plan_id"]
        manifest["live_estimated_total_usd"] = live_plan["estimated_total_usd"]
        manifest["live_estimated_total_billable_bytes"] = live_plan[
            "estimated_total_billable_bytes"
        ]
        manifest["active_quote_basis_plan_id"] = live_plan["plan_id"]
        write_json_atomic(manifest_path, manifest)

        # Rebind every frozen authority surface immediately before the first
        # paid call. The parent HYP-001 gate is deliberately not consulted.
        bindings = _verify_design_acquisition_authority(
            plan=plan,
            authorization_basis_plan_id=authorization_basis_plan_id,
            approve_max_usd=approve_max_usd,
            root=root,
            sdk_version=sdk_version,
        )
        historical_plan = _load_json(DESIGN_QUOTE_EVIDENCE_ROOT / PLAN_NAME)
        if (
            live_plan.get("requests") != historical_plan.get("requests")
            or len({item["request_id"] for item in live_plan["requests"]})
            != DESIGN_REQUESTS
        ):
            raise AcquisitionError("live design quote request identities drifted from DEDDE7F2")
        quote_by_id = {item["request_id"]: item for item in live_plan["quotes"]}
        completed_ids = {
            str(item.get("request_id", "")) for item in manifest["downloads"]
        }
        if not completed_ids.issubset(quote_by_id):
            raise AcquisitionError("completed request IDs drifted from fresh live quote")
        pending_requests = [
            item
            for item in live_plan["requests"]
            if item["request_id"] not in completed_ids
        ]
        completed_incurred_usd = _completed_incurred_estimate(manifest)
        pending_live_usd = sum(
            float(quote_by_id[item["request_id"]]["estimated_usd"])
            for item in pending_requests
        )
        authorized_aggregate_usd = completed_incurred_usd + pending_live_usd
        pending_live_bytes = sum(
            int(quote_by_id[item["request_id"]]["billable_bytes"])
            for item in pending_requests
        )
        capacity = _design_capacity_snapshot(safe_root, pending_live_bytes)
        if authorized_aggregate_usd > DESIGN_APPROVED_MAX_USD:
            _raise_design_ceiling_blocker(
                bindings=bindings,
                live_plan=live_plan,
                live_receipt=live_receipt,
                manifest=manifest,
                manifest_path=manifest_path,
                authority_path=authority_path,
                root=safe_root,
                capacity=capacity,
                authorized_aggregate_usd=authorized_aggregate_usd,
            )
        if not capacity["pass"]:
            _raise_design_capacity_blocker(
                bindings=bindings,
                live_plan=live_plan,
                live_receipt=live_receipt,
                manifest=manifest,
                manifest_path=manifest_path,
                authority_path=authority_path,
                root=safe_root,
                capacity=capacity,
                authorized_aggregate_usd=authorized_aggregate_usd,
            )

        raw_root = _validated_design_raw_root(safe_root, create=True)
        validated_ids = validate_existing_download_manifest(
            manifest=manifest,
            plan=live_plan,
            root=safe_root,
        )
        foundation = _load_foundation()
        pending_requests = [
            item
            for item in live_plan["requests"]
            if item["request_id"] not in validated_ids
        ]
        remaining_live_bytes = sum(
            int(quote_by_id[item["request_id"]]["billable_bytes"])
            for item in pending_requests
        )
        completed_incurred_usd = _completed_incurred_estimate(manifest)
        remaining_live_usd = sum(
            float(quote_by_id[item["request_id"]]["estimated_usd"])
            for item in pending_requests
        )
        for request in pending_requests:
            request_id = request["request_id"]
            filename = str(request["filename"])
            # Manifest validation may hash/decode a large existing corpus. Bind
            # every mutable authority surface and refresh capacity only after
            # that scan, immediately before each next journal/paid request.
            bindings = _verify_design_acquisition_authority(
                plan=plan,
                authorization_basis_plan_id=authorization_basis_plan_id,
                approve_max_usd=approve_max_usd,
                root=root,
                sdk_version=sdk_version,
            )
            authorized_aggregate_usd = completed_incurred_usd + remaining_live_usd
            if authorized_aggregate_usd > DESIGN_APPROVED_MAX_USD:
                _raise_design_ceiling_blocker(
                    bindings=bindings,
                    live_plan=live_plan,
                    live_receipt=live_receipt,
                    manifest=manifest,
                    manifest_path=manifest_path,
                    authority_path=authority_path,
                    root=safe_root,
                    capacity=None,
                    authorized_aggregate_usd=authorized_aggregate_usd,
                )
            capacity = _design_capacity_snapshot(safe_root, remaining_live_bytes)
            if not capacity["pass"]:
                _raise_design_capacity_blocker(
                    bindings=bindings,
                    live_plan=live_plan,
                    live_receipt=live_receipt,
                    manifest=manifest,
                    manifest_path=manifest_path,
                    authority_path=authority_path,
                    root=safe_root,
                    capacity=capacity,
                    authorized_aggregate_usd=authorized_aggregate_usd,
                )
            output, partial = _validated_design_raw_artifacts(
                root=safe_root, filename=filename, require_raw_root=True
            )
            if output.exists() or partial.exists():
                raise AcquisitionError(
                    f"unmanifested output exists; refusing possible charged retry: {output}"
                )
            live_quote = quote_by_id[request_id]
            manifest["status"] = "DOWNLOADING_SERIAL"
            manifest["in_flight"] = {
                "request_id": request_id,
                "event_clock_id": request["event_clock_id"],
                "segment": request["segment"],
                "filename": filename,
                "start": request["start"],
                "end": request["end"],
                "estimated_usd": live_quote["estimated_usd"],
                "billable_bytes": live_quote["billable_bytes"],
                "started_at_utc": utc_now(),
            }
            write_json_atomic(manifest_path, manifest)
            # The journal write is deliberately between two topology checks.
            # A directory can be swapped to a junction while the manifest is
            # flushed, so check the exact lexical raw/final/partial paths again
            # at the last local seam before invoking the paid SDK method.
            call_output, call_partial = _validated_design_raw_artifacts(
                root=safe_root, filename=filename, require_raw_root=True
            )
            if (
                call_output != output
                or call_partial != partial
                or call_output.exists()
                or call_partial.exists()
            ):
                raise AcquisitionError(
                    "design DBN path topology changed after journal before paid call"
                )
            paid_error_type: str | None = None
            try:
                client.timeseries.get_range(
                    **_timeseries_request_args(request), path=partial
                )
            except Exception as exc:
                paid_error_type = type(exc).__name__
            if paid_error_type is not None:
                raise AcquisitionError(
                    f"paid request failed for {request_id}; in_flight preserved, "
                    f"no retry; exception_type={paid_error_type}"
                )
            checked_output, checked_partial = _validated_design_raw_artifacts(
                root=safe_root, filename=filename, require_raw_root=True
            )
            if checked_output != output or checked_partial != partial:
                raise AcquisitionError("design DBN path topology changed after paid response")
            validation_error_type: str | None = None
            records = -1
            try:
                records = int(foundation.validate_dbn_file(partial, allow_zero=True))
            except Exception as exc:
                validation_error_type = type(exc).__name__
            if validation_error_type is not None or records < 0:
                raise AcquisitionError(
                    f"paid response DBN validation failed for {request_id}; "
                    "in_flight preserved, no retry"
                )
            checked_output, checked_partial = _validated_design_raw_artifacts(
                root=safe_root, filename=filename, require_raw_root=True
            )
            if checked_output != output or checked_partial != partial:
                raise AcquisitionError("design DBN path topology changed before final replace")
            os.replace(partial, output)
            checked_output, _checked_partial = _validated_design_raw_artifacts(
                root=safe_root, filename=filename, require_raw_root=True
            )
            if checked_output != output or not output.is_file():
                raise AcquisitionError("design DBN final path failed topology validation")
            manifest["downloads"].append(
                {
                    **request,
                    "bytes": output.stat().st_size,
                    "sha256": sha256_file(output),
                    "records": records,
                    "source_empty": records == 0,
                    "charged_empty_evidence": (
                        {
                            "paid_request_completed": True,
                            "response_validated": True,
                            "retry_prohibited": True,
                        }
                        if records == 0
                        else None
                    ),
                    "estimated_usd": live_quote["estimated_usd"],
                    "billable_bytes": live_quote["billable_bytes"],
                    "quote_basis_plan_id": live_plan["plan_id"],
                }
            )
            manifest["in_flight"] = None
            manifest["paid_requests_completed"] = len(manifest["downloads"])
            manifest["timeseries_calls"] = len(manifest["downloads"])
            manifest["paid_request_made"] = True
            write_json_atomic(manifest_path, manifest)
            remaining_live_bytes -= int(live_quote["billable_bytes"])
            completed_incurred_usd += float(live_quote["estimated_usd"])
            remaining_live_usd -= float(live_quote["estimated_usd"])

        manifest["status"] = "DOWNLOADED_FULL_DBN_VALIDATION_PASS"
        validate_existing_download_manifest(
            manifest=manifest,
            plan=live_plan,
            root=safe_root,
            require_complete=True,
        )
        write_json_atomic(manifest_path, manifest)
        validate_existing_download_manifest(
            manifest=_load_json(manifest_path),
            plan=live_plan,
            root=safe_root,
            require_complete=True,
        )
        authority_receipt = _design_acquisition_receipt(
            status="DESIGN_ACQUISITION_COMPLETE_AUTHORITY_RECONCILED",
            bindings=bindings,
            live_plan=live_plan,
            live_receipt=live_receipt,
            root=safe_root,
            timeseries_calls=DESIGN_REQUESTS,
            paid_request_made=True,
            download_manifest_sha256=sha256_file(manifest_path),
            capacity=capacity,
            authorized_aggregate_usd=completed_incurred_usd + remaining_live_usd,
        )
        write_json_atomic(authority_path, authority_receipt)
        return manifest


def download_windows(
    *,
    client: Any,
    metadata_client: Any,
    plan: dict[str, Any],
    expected_plan_id: str,
    approve_max_usd: float,
    root: Path,
    sdk_version: str,
) -> dict[str, Any]:
    """Future paid path. This function is intentionally not invoked by this task."""

    verify_profile = (
        verify_design_segments_bound_contract
        if plan.get("profile") == DESIGN_SEGMENTS_PROFILE
        else verify_bound_contract
    )
    bindings = verify_profile(require_global_registry=True)
    if plan.get("profile") == DESIGN_SEGMENTS_PROFILE:
        _require_design_remote_reopen(bindings)
    _require_paid_download_reopen(bindings)
    _validate_canonical_registry()
    _validate_profile_plan(plan, require_quote=True)
    validate_download_authority(
        plan=plan,
        expected_plan_id=expected_plan_id,
        approve_max_usd=approve_max_usd,
    )
    root = ensure_output_root(root)
    root.mkdir(parents=True, exist_ok=True)
    with exclusive_paid_download_lock(root):
        raw_root = root / "raw"
        raw_root.mkdir(parents=True, exist_ok=True)
        manifest_path = root / DOWNLOAD_MANIFEST_NAME
        if manifest_path.is_file():
            manifest = _load_json(manifest_path)
            validated_ids = validate_existing_download_manifest(
                manifest=manifest,
                plan=plan,
                root=root,
            )
            if manifest.get("approved_max_usd") != approve_max_usd:
                raise AcquisitionError("download manifest approved USD ceiling changed")
        else:
            manifest = {
                "schema_version": DOWNLOAD_SCHEMA_VERSION,
                "status": "LOCKED_NOT_REQUOTED",
                "plan_id": plan["plan_id"],
                "approved_max_usd": approve_max_usd,
                "live_estimated_total_usd": 0.0,
                "downloads": [],
                "in_flight": None,
                "paid_requests_completed": 0,
                "outcome_fields_used": False,
            }
            write_json_atomic(manifest_path, manifest)
            validated_ids = validate_existing_download_manifest(
                manifest=manifest,
                plan=plan,
                root=root,
            )

        offline = build_offline_plan()
        _validate_canonical_registry()
        requoted, _ = quote_plan(
            client=metadata_client,
            plan=offline,
            sdk_version=sdk_version,
            billable_size_authorized=True,
        )
        # Free-quote append tolerance never rolls into paid authority. Rebind the
        # exact V7 global registry immediately before any timeseries call.
        _validate_canonical_registry()
        verify_bound_contract(require_global_registry=True)
        live_total = float(requoted["estimated_total_usd"])
        if live_total > approve_max_usd:
            raise AcquisitionError(
                f"live metadata quote ${live_total:.12f} exceeds approved ceiling ${approve_max_usd:.12f}"
            )
        manifest["status"] = "LIVE_REQUOTE_PASS_NOT_DOWNLOADED"
        manifest["live_estimated_total_usd"] = live_total
        write_json_atomic(manifest_path, manifest)

        completed = {
            str(item["filename"])
            for item in manifest["downloads"]
            if item["event_clock_id"] in validated_ids
        }
        quote_by_id = {item["event_clock_id"]: item for item in requoted["quotes"]}
        foundation = _load_foundation()
        for window in plan["windows"]:
            filename = str(window["filename"])
            if filename in completed:
                continue
            output = raw_root / filename
            partial = output.with_suffix(output.suffix + ".partial")
            if output.exists() or partial.exists():
                raise AcquisitionError(
                    f"unmanifested output exists; refusing possible charged retry: {output}"
                )
            live_quote = quote_by_id[window["event_clock_id"]]
            manifest["status"] = "DOWNLOADING_SERIAL"
            manifest["in_flight"] = {
                "event_clock_id": window["event_clock_id"],
                "filename": filename,
                "start": window["start"],
                "end": window["end"],
                "estimated_usd": live_quote["estimated_usd"],
                "billable_bytes": live_quote["billable_bytes"],
                "started_at_utc": utc_now(),
            }
            write_json_atomic(manifest_path, manifest)
            try:
                client.timeseries.get_range(
                    **_timeseries_request_args(window), path=partial
                )
            except Exception as exc:
                raise AcquisitionError(
                    f"paid request failed for {window['event_clock_id']}; in_flight preserved, no retry: {exc}"
                ) from exc
            try:
                records = foundation.validate_dbn_file(partial, allow_zero=True)
            except Exception as exc:
                raise AcquisitionError(
                    f"paid response DBN validation failed for {window['event_clock_id']}; in_flight preserved, no retry"
                ) from exc
            os.replace(partial, output)
            manifest["downloads"].append(
                {
                    **window,
                    "bytes": output.stat().st_size,
                    "sha256": sha256_file(output),
                    "records": records,
                    "source_empty": records == 0,
                    "charged_empty_evidence": (
                        {
                            "paid_request_completed": True,
                            "response_validated": True,
                            "retry_prohibited": True,
                        }
                        if records == 0
                        else None
                    ),
                    "estimated_usd": live_quote["estimated_usd"],
                    "billable_bytes": live_quote["billable_bytes"],
                }
            )
            completed.add(filename)
            manifest["in_flight"] = None
            manifest["paid_requests_completed"] = len(manifest["downloads"])
            write_json_atomic(manifest_path, manifest)

        validate_existing_download_manifest(
            manifest=manifest,
            plan=plan,
            root=root,
            require_complete=True,
        )
        manifest["status"] = "DOWNLOADED_FULL_DBN_VALIDATION_PASS"
        write_json_atomic(manifest_path, manifest)
        validate_existing_download_manifest(
            manifest=manifest,
            plan=plan,
            root=root,
            require_complete=True,
        )
        return manifest


def make_client_from_local_key():
    foundation = _load_foundation()
    key = foundation.load_api_key()
    client = foundation.make_client(key)
    return client, key


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "plan",
            "quote",
            "download",
            "validate-quote",
            "design-plan",
            "design-quote",
            "design-download",
            "design-acquire",
            "validate-design-quote",
        ),
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--expected-plan-id")
    parser.add_argument("--approve-max-usd", type=float)
    parser.add_argument("--quote-workers", type=int, default=16)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.action in {"design-quote", "design-download"}:
            bindings = verify_design_segments_bound_contract(
                require_global_registry=True
            )
            _require_design_remote_reopen(bindings)
        if args.action == "design-acquire":
            bindings = verify_design_segments_bound_contract(
                require_global_registry=True
            )
            requested_design_root = (
                DESIGN_SEGMENTS_ROOT if args.root == DEFAULT_ROOT else args.root
            )
            if (
                args.expected_plan_id != DESIGN_QUOTE_EVIDENCE_PLAN_ID
                or args.approve_max_usd != DESIGN_APPROVED_MAX_USD
                or requested_design_root.resolve() != DESIGN_SEGMENTS_ROOT.resolve()
                or bindings.get("task_packet_v13_sha256") != TASK_PACKET_V13_SHA256
            ):
                raise AcquisitionError(
                    "design-acquire requires exact DEDDE7F2 basis, USD 3.50, V13 and D-side root"
                )
        design_action = args.action in {
            "design-plan",
            "design-quote",
            "design-download",
            "design-acquire",
            "validate-design-quote",
        }
        requested_root = (
            DESIGN_SEGMENTS_ROOT
            if design_action and args.root == DEFAULT_ROOT
            else args.root
        )
        root = (
            ensure_design_segments_output_root(requested_root)
            if design_action
            else ensure_output_root(requested_root)
        )
        plan_path = root / PLAN_NAME
        receipt_path = root / (
            DESIGN_QUOTE_RECEIPT_NAME if design_action else QUOTE_RECEIPT_NAME
        )
        if args.action in {"plan", "design-plan"}:
            plan = (
                build_design_segments_plan() if design_action else build_offline_plan()
            )
            root.mkdir(parents=True, exist_ok=True)
            write_json_atomic(plan_path, plan)
            population = (
                f"requests={len(plan['requests'])} design_clocks="
                f"{plan['coverage']['design_clock_count']}"
                if design_action
                else f"windows={len(plan['windows'])} "
                f"overlaps={plan['coverage']['overlapping_pair_count']}"
            )
            print(
                "EVENT_CLOB_PLAN "
                f"status={plan['status']} plan_id={plan['plan_id']} "
                f"profile={plan['profile']} {population} "
                "timeseries_calls=0 paid_request_made=false"
            )
            print(f"plan={plan_path}")
            return 0

        if not plan_path.is_file():
            raise AcquisitionError(f"acquisition plan is absent: {plan_path}")
        plan = _load_json(plan_path)
        if args.action in {"validate-quote", "validate-design-quote"}:
            _validate_profile_plan(plan, require_quote=True)
            receipt = _load_json(receipt_path)
            validate_quote_receipt(receipt, plan)
            if design_action:
                verify_design_segments_bound_contract(require_global_registry=True)
            else:
                verify_bound_contract(require_global_registry=True)
            print(
                "EVENT_CLOB_QUOTE_VALIDATE "
                f"status=PASS plan_id={plan['plan_id']} windows={len(plan['quotes'])} "
                f"estimated_total_usd={plan['estimated_total_usd']:.12f} "
                "timeseries_calls=0 paid_request_made=false"
            )
            return 0

        if args.action != "design-acquire" and (
            not args.expected_plan_id or args.expected_plan_id != plan.get("plan_id")
        ):
            raise AcquisitionError(
                f"{args.action} requires --expected-plan-id {plan.get('plan_id')}"
            )
        if args.action in {"quote", "design-quote"}:
            # Validate every local artifact and plan binding before loading an API
            # key or constructing a remote client.
            _validate_profile_plan(plan, require_quote=False)
        if args.action == "design-acquire":
            _verify_design_acquisition_authority(
                plan=plan,
                authorization_basis_plan_id=str(args.expected_plan_id),
                approve_max_usd=float(args.approve_max_usd),
                root=root,
                sdk_version=DATABENTO_SDK_VERSION,
            )
        client, key = make_client_from_local_key()
        if args.action == "design-acquire":
            result = design_acquire(
                client=client,
                metadata_client=client,
                plan=plan,
                authorization_basis_plan_id=str(args.expected_plan_id),
                approve_max_usd=float(args.approve_max_usd),
                root=root,
                sdk_version=DATABENTO_SDK_VERSION,
            )
            print(
                "EVENT_CLOB_DESIGN_ACQUIRE "
                f"status={result['status']} files={len(result['downloads'])} "
                f"plan_id={result['plan_id']} timeseries_calls={result['timeseries_calls']}"
            )
            return 0
        if args.action in {"quote", "design-quote"}:
            quoted, receipt = quote_plan(
                client=client,
                plan=plan,
                sdk_version=DATABENTO_SDK_VERSION,
                billable_size_authorized=True,
                client_factory=lambda: _load_foundation().make_client(key),
                workers=args.quote_workers,
            )
            write_json_atomic(plan_path, quoted)
            write_json_atomic(receipt_path, receipt)
            if design_action:
                finalize_design_quote_artifacts(
                    root=root,
                    quoted=quoted,
                    receipt=receipt,
                )
            print(
                "EVENT_CLOB_QUOTE "
                f"status={receipt['status']} plan_id={quoted['plan_id']} "
                f"windows={len(quoted['quotes'])} "
                f"estimated_total_usd={quoted['estimated_total_usd']:.12f} "
                f"billable_bytes={quoted['estimated_total_billable_bytes']} "
                "timeseries_calls=0 paid_request_made=false"
            )
            print(f"plan={plan_path}")
            print(f"receipt={receipt_path}")
            return 0

        if args.approve_max_usd is None:
            raise AcquisitionError("download requires --approve-max-usd")
        result = download_windows(
            client=client,
            metadata_client=client,
            plan=plan,
            expected_plan_id=args.expected_plan_id,
            approve_max_usd=args.approve_max_usd,
            root=root,
            sdk_version=DATABENTO_SDK_VERSION,
        )
        print(
            "EVENT_CLOB_DOWNLOAD "
            f"status={result['status']} files={len(result['downloads'])}"
        )
        return 0
    except AcquisitionError as exc:
        print(f"EVENT_CLOB_ACQUISITION_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
