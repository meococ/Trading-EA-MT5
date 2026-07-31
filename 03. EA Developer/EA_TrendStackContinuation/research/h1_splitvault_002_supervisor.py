"""Outcome-blind HYP006 source supervisor helpers.

Production remains disarmed until a reviewed one-shot packet supplies the
reviewed packet SHA.  These helpers validate metadata-only date selection and
build the sealed child payload without feature fields.
"""

from __future__ import annotations

import sys as _bootstrap_sys


_PROTECTED_BOOTSTRAP_MODULES = ("dataclasses", "pathlib", "pyarrow", "pyarrow.parquet")
_PROTECTED_PRELOAD_AT_BOOTSTRAP = tuple(
    name for name in _PROTECTED_BOOTSTRAP_MODULES if name in _bootstrap_sys.modules
)
_PRODUCTION_BOOTSTRAP_ELIGIBLE = not _PROTECTED_PRELOAD_AT_BOOTSTRAP

import builtins
import ctypes
import datetime as _trusted_datetime
import hashlib
import importlib.machinery
import importlib.util
import json
import math
import os
import stat
import sys
import types
import weakref
import __future__ as _trusted_future
import _strptime as _trusted_strptime


def _bootstrap_load_canonical(name: str, search_path):
    if name in _bootstrap_sys.modules:
        raise ImportError("protected dependency was preloaded")
    spec = importlib.machinery.PathFinder.find_spec(name, search_path)
    if (
        spec is None
        or type(spec.origin) is not str
        or not spec.origin
        or spec.loader is None
        or not callable(getattr(spec.loader, "exec_module", None))
    ):
        raise ImportError("canonical dependency spec unavailable")
    module = importlib.util.module_from_spec(spec)
    _bootstrap_sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if _bootstrap_sys.modules.get(name) is module:
            del _bootstrap_sys.modules[name]
        raise
    if (
        _bootstrap_sys.modules.get(name) is not module
        or getattr(module, "__spec__", None) is not spec
        or module.__spec__.loader is not spec.loader
        or module.__spec__.origin != spec.origin
    ):
        raise ImportError("canonical dependency load drift")
    return module, spec


_BOOTSTRAP_CANONICAL_SPECS = {}
if _PRODUCTION_BOOTSTRAP_ELIGIBLE:
    _trusted_dataclasses, _BOOTSTRAP_CANONICAL_SPECS["dataclasses"] = _bootstrap_load_canonical(
        "dataclasses", _bootstrap_sys.path
    )
    _trusted_pathlib, _BOOTSTRAP_CANONICAL_SPECS["pathlib"] = _bootstrap_load_canonical(
        "pathlib", _bootstrap_sys.path
    )
    _trusted_pyarrow, _BOOTSTRAP_CANONICAL_SPECS["pyarrow"] = _bootstrap_load_canonical(
        "pyarrow", _bootstrap_sys.path
    )
    _trusted_pyarrow_parquet, _BOOTSTRAP_CANONICAL_SPECS["pyarrow.parquet"] = _bootstrap_load_canonical(
        "pyarrow.parquet", _trusted_pyarrow.__path__
    )
    _trusted_pyarrow.parquet = _trusted_pyarrow_parquet
else:
    import dataclasses as _trusted_dataclasses
    import pathlib as _trusted_pathlib
    import pyarrow as _trusted_pyarrow
    import pyarrow.parquet as _trusted_pyarrow_parquet

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator, Mapping


PUBLIC_ERROR = "INVALID_SUPERVISOR"
COLLECTION_ID = "DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002"
HYPOTHESIS_ID = "HYP-TRENDSTACK-EURUSD-H1-006"
REGISTRY_ROW_INDEX = 282
REGISTRY_ROW_SHA256 = "5251227378A4192AB58364591603B2C1B1EED306DCC3BD4976DB943FDFDC8A1E"
FROZEN_DESIGN_DATE_COUNT = 1297
FROZEN_DESIGN_DATE_SET_SHA256 = "4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A"
DESIGN_DATE_SET_PREFIX = b"trendstack_002_design_date_set.v1\n"
REVIEWED_RUN_PACKET_SHA256: str | None = None
ARM_MANIFEST_NAME = "HYP-TRENDSTACK-EURUSD-H1-006_SOURCE_RUN_ARM_MANIFEST.json"
SOURCE_PREP_TASK_PACKET_V9_SHA256 = "268577BC3F4C91FFBD1DB8C16AE32D4BF9713C8E0AD08C0EC3295AB6B89DC351"
SOURCE_PREP_TASK_PACKET_V9_PATH = (
    "03. EA Developer/EA_TrendStackContinuation/research/"
    "HYP-TRENDSTACK-EURUSD-H1-006_SOURCE_PREP_TASK_PACKET_V9.json"
)
OWNER_GOAL = "COMPLETE_HYP006_END_TO_END_WITHOUT_ECONOMIC_SHORTCUTS"
_HEX = frozenset("0123456789ABCDEF")
_SELECTION_FIELDS = {"date", "schema_version"}
_SELECTION_SCHEMA = "trendstack_006_design_date_selection.v1"
_PUBLIC_MANIFEST_FIELDS = {"bytes", "date", "relative_path", "rows", "schema_version", "sha256"}
_PUBLIC_MANIFEST_SCHEMA = "h1_splitvault_002_public_design_shard.v1"
_FORBIDDEN_FIELDS = {
    "m252",
    "m6",
    "atr20",
    "arm",
    "direction",
    "signals",
    "feature",
    "feature_value",
    "feature_values",
    "alignment",
    "eligibility",
    "return",
    "pnl",
    "gate",
    "source_path",
    "output_path",
    "path_capability",
}
_PACKET_FIELDS = {
    "authority",
    "schema_version",
    "collection_id",
    "hypothesis_id",
    "registry_row_index",
    "registry_row_sha256",
    "review_base_supervisor_sha256",
    "runtime_supervisor_sha256",
    "reviewed_run_packet_sha256",
    "source_attempt_id",
    "network_allowed",
    "subprocess_allowed",
    "economics_authorized",
    "validation_authorized",
    "holdout_authorized",
    "performance_metrics_authorized",
}
_DETACHED_PACKET_EXCLUDED = frozenset({"runtime_supervisor_sha256", "reviewed_run_packet_sha256"})
_SOURCE_RUN_AUTHORITY_FIELDS = frozenset(
    {
        "schema_version",
        "owner_goal",
        "owner_goal_path",
        "owner_goal_sha256",
        "source_run_authorized",
        "one_shot_only",
        "raw_source_open_limit",
        "registry_mutation_allowed",
        "network_allowed",
        "subprocess_allowed",
        "economics_authorized",
        "validation_authorized",
        "holdout_authorized",
        "performance_metrics_authorized",
        "mt5_authorized",
        "model0_authorized",
        "promotion_authorized",
        "paper_authorized",
        "live_authorized",
        "deploy_authorized",
        "trading_mutation",
        "collection_id",
        "hypothesis_id",
        "source_attempt_id",
        "registry_row_index",
        "registry_row_sha256",
        "collection_plan_v1_sha256",
        "collection_plan_v2_sha256",
        "probe_plan_v1_sha256",
        "probe_plan_v2_sha256",
        "custodian_tool_sha256",
        "supervisor_review_base_sha256",
        "design_builder_tool_sha256",
        "validator_tool_sha256",
        "custodian_test_sha256",
        "supervisor_test_sha256",
        "design_builder_test_sha256",
        "validator_test_sha256",
        "source_prep_task_packet_path",
        "source_prep_task_packet_sha256",
        "source_path",
        "source_manifest_path",
        "clock_path",
        "selection_manifest_path",
        "splitvault_output_root",
        "design_source_output_root",
        "detached_packet_sha256",
    }
)
_FULL_PACKET_EXTRA_FIELDS = {
    "owner_goal_path",
    "owner_goal_sha256",
    "collection_plan_v1_path",
    "collection_plan_v1_sha256",
    "collection_plan_v2_path",
    "collection_plan_v2_sha256",
    "probe_plan_v1_path",
    "probe_plan_v1_sha256",
    "probe_plan_v2_path",
    "probe_plan_v2_sha256",
    "registry_path",
    "registry_sha256",
    "source_path",
    "source_sha256",
    "source_bytes",
    "source_rows",
    "source_row_groups",
    "source_footer_length",
    "source_footer_start",
    "source_footer_sha256",
    "source_manifest_path",
    "source_manifest_sha256",
    "clock_path",
    "clock_sha256",
    "custodian_tool_path",
    "custodian_tool_sha256",
    "supervisor_tool_path",
    "supervisor_review_base_sha256",
    "design_builder_tool_path",
    "design_builder_tool_sha256",
    "validator_tool_path",
    "validator_tool_sha256",
    "custodian_test_path",
    "custodian_test_sha256",
    "supervisor_test_path",
    "supervisor_test_sha256",
    "design_builder_test_path",
    "design_builder_test_sha256",
    "validator_test_path",
    "validator_test_sha256",
    "packet_review_receipt_path",
    "packet_review_receipt_sha256",
    "parent_hyp005_failure_manifest_sha256",
    "hyp002_failure_manifest_sha256",
    "parent_stage0_ledger_path",
    "parent_stage0_ledger_sha256",
    "parent_stage0_receipt_path",
    "parent_stage0_receipt_sha256",
    "attempt_evidence_root",
    "custody_stage_path",
    "splitvault_output_root",
    "selection_manifest_path",
    "selection_manifest_sha256",
    "design_stage_path",
    "design_source_output_root",
    "expected_design_dates",
    "expected_rows_per_day",
    "expected_total_rows",
    "expected_raw_opens",
    "expected_selected_opens",
    "expected_unselected_opens",
    "one_shot_custody_source_attempt_authorized",
    "mt5_authorized",
    "model0_authorized",
    "promotion_authorized",
    "paper_authorized",
    "live_authorized",
    "deploy_authorized",
    "trading_mutation",
}
FULL_PACKET_FIELDS = frozenset(_PACKET_FIELDS | _FULL_PACKET_EXTRA_FIELDS)
FROZEN_PACKET_VALUES: dict[str, object] = {
    "owner_goal_path": "01. GOAL/GOAL.md",
    "owner_goal_sha256": "0A282604297137360707254F599944D81B846E80DBE0CE03E9E649489036D096",
    "collection_plan_v1_path": "03. EA Developer/EA_TrendStackContinuation/research/DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002_PLAN.md",
    "collection_plan_v1_sha256": "A8A768D529A4569BDD508BFA0722BFA1ACEF25C3098A91FF78B98EA209E3510F",
    "collection_plan_v2_path": "03. EA Developer/EA_TrendStackContinuation/research/DATASET-FIVEPERCENT-EURUSD-H1-SPLITVAULT-002_PLAN_V2.md",
    "collection_plan_v2_sha256": "E8E364ECBCD27321C4F51A0B7564E13FD88AB748E72F3859E36E40CA29B32F63",
    "probe_plan_v1_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-006_PROBE_PLAN.md",
    "probe_plan_v1_sha256": "2BFB0E0B3CF5F929ABE6320433A10C9DC84731A35E327E94F8D46D08CFD00FF4",
    "probe_plan_v2_path": "03. EA Developer/EA_TrendStackContinuation/research/HYP-TRENDSTACK-EURUSD-H1-006_PROBE_PLAN_V2.md",
    "probe_plan_v2_sha256": "78771B09C8BB8A259E5F372E36407C342194491208E1D374B10EA8FE05755428",
    "registry_path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
    "source_path": "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_H1_2015_now.parquet",
    "source_sha256": "71860016AF1BD1B17353B043AFF799233A787E9DF3F587913FCD2F5328BB1E08",
    "source_bytes": 2781897,
    "source_rows": 71785,
    "source_row_groups": 1,
    "source_footer_length": 5392,
    "source_footer_start": 2776497,
    "source_footer_sha256": "01C090CF494A45AC99603E8A4BBE3447884253DEF3828964AE5555086FF91E3B",
    "source_manifest_path": "02. AlphaFactory/data/fivepercent/EURUSD/manifest.json",
    "source_manifest_sha256": "2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54",
    "clock_path": "02. AlphaFactory/tools/research/fivepercent_server_clock.py",
    "clock_sha256": "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52",
    "parent_stage0_ledger_sha256": "3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7",
    "parent_stage0_receipt_sha256": "5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE",
    "expected_design_dates": 1297,
    "expected_rows_per_day": 7,
    "expected_total_rows": 9079,
    "expected_raw_opens": 1,
    "expected_selected_opens": 1297,
    "expected_unselected_opens": 0,
}

_FILE_BINDINGS = {
    "owner_goal_path": "owner_goal_sha256",
    "collection_plan_v1_path": "collection_plan_v1_sha256",
    "collection_plan_v2_path": "collection_plan_v2_sha256",
    "probe_plan_v1_path": "probe_plan_v1_sha256",
    "probe_plan_v2_path": "probe_plan_v2_sha256",
    "registry_path": "registry_sha256",
    "source_manifest_path": "source_manifest_sha256",
    "clock_path": "clock_sha256",
    "custodian_tool_path": "custodian_tool_sha256",
    "supervisor_tool_path": "runtime_supervisor_sha256",
    "design_builder_tool_path": "design_builder_tool_sha256",
    "validator_tool_path": "validator_tool_sha256",
    "custodian_test_path": "custodian_test_sha256",
    "supervisor_test_path": "supervisor_test_sha256",
    "design_builder_test_path": "design_builder_test_sha256",
    "validator_test_path": "validator_test_sha256",
    "packet_review_receipt_path": "packet_review_receipt_sha256",
    "parent_stage0_ledger_path": "parent_stage0_ledger_sha256",
    "parent_stage0_receipt_path": "parent_stage0_receipt_sha256",
    "selection_manifest_path": "selection_manifest_sha256",
}


class InvalidSupervisor(RuntimeError):
    pass


@dataclass(frozen=True)
class SelectionPreflight:
    dates: tuple[str, ...]
    date_set_sha256: str
    manifest_sha256: str
    metadata_rows: int
    payload: bytes


@dataclass(frozen=True)
class SelectionMapping:
    payload: bytes
    sha256: str
    dates: tuple[str, ...]
    mapping: dict[str, dict[str, object]]
    extra_date_count: int


@dataclass(frozen=True)
class VerifiedRunPacket(Mapping[str, object]):
    """Canonical packet bytes that passed their detached SHA and full schema."""

    _values: dict[str, object]
    detached_sha256: str
    canonical_bytes: bytes

    def __getitem__(self, key: str) -> object:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def as_dict(self) -> dict[str, object]:
        return dict(self._values)


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(char in _HEX for char in value)


def _valid_attempt_id(value: object) -> bool:
    prefix = "HYP006-SOURCE-ATTEMPT-"
    return (
        type(value) is str
        and value.startswith(prefix)
        and len(value) == len(prefix) + 16
        and all(char in _HEX for char in value[len(prefix) :])
    )


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _normalized_detached_packet(packet: Mapping[str, object]) -> dict[str, object]:
    """Return the arm-independent authority object hashed by the sentinel.

    The runtime SHA, the copy of this digest in the packet, and the nested copy
    in ``authority`` are populated only after the digest is known.  No strategy,
    source, tool, path, permission, attempt, or governance binding is excluded.
    """

    if not isinstance(packet, Mapping):
        raise ValueError
    normalized = {
        key: value
        for key, value in packet.items()
        if key not in _DETACHED_PACKET_EXCLUDED
    }
    authority = normalized.get("authority")
    if type(authority) is dict:
        normalized["authority"] = {
            key: value for key, value in authority.items() if key != "detached_packet_sha256"
        }
    return normalized


def compute_detached_packet_sha256(packet: Mapping[str, object]) -> str:
    try:
        return _digest(canonical_json(_normalized_detached_packet(packet)) + b"\n")
    except Exception as exc:
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def _expected_source_run_authority(packet: Mapping[str, object], detached_sha256: str) -> dict[str, object]:
    return {
        "schema_version": "trendstack_006_detached_source_run_authority.v1",
        "owner_goal": OWNER_GOAL,
        "owner_goal_path": packet["owner_goal_path"],
        "owner_goal_sha256": packet["owner_goal_sha256"],
        "source_run_authorized": True,
        "one_shot_only": True,
        "raw_source_open_limit": 1,
        "registry_mutation_allowed": False,
        "network_allowed": False,
        "subprocess_allowed": False,
        "economics_authorized": False,
        "validation_authorized": False,
        "holdout_authorized": False,
        "performance_metrics_authorized": False,
        "mt5_authorized": False,
        "model0_authorized": False,
        "promotion_authorized": False,
        "paper_authorized": False,
        "live_authorized": False,
        "deploy_authorized": False,
        "trading_mutation": False,
        "collection_id": packet["collection_id"],
        "hypothesis_id": packet["hypothesis_id"],
        "source_attempt_id": packet["source_attempt_id"],
        "registry_row_index": packet["registry_row_index"],
        "registry_row_sha256": packet["registry_row_sha256"],
        "collection_plan_v1_sha256": packet["collection_plan_v1_sha256"],
        "collection_plan_v2_sha256": packet["collection_plan_v2_sha256"],
        "probe_plan_v1_sha256": packet["probe_plan_v1_sha256"],
        "probe_plan_v2_sha256": packet["probe_plan_v2_sha256"],
        "custodian_tool_sha256": packet["custodian_tool_sha256"],
        "supervisor_review_base_sha256": packet["supervisor_review_base_sha256"],
        "design_builder_tool_sha256": packet["design_builder_tool_sha256"],
        "validator_tool_sha256": packet["validator_tool_sha256"],
        "custodian_test_sha256": packet["custodian_test_sha256"],
        "supervisor_test_sha256": packet["supervisor_test_sha256"],
        "design_builder_test_sha256": packet["design_builder_test_sha256"],
        "validator_test_sha256": packet["validator_test_sha256"],
        "source_prep_task_packet_path": SOURCE_PREP_TASK_PACKET_V9_PATH,
        "source_prep_task_packet_sha256": SOURCE_PREP_TASK_PACKET_V9_SHA256,
        "source_path": packet["source_path"],
        "source_manifest_path": packet["source_manifest_path"],
        "clock_path": packet["clock_path"],
        "selection_manifest_path": packet["selection_manifest_path"],
        "splitvault_output_root": packet["splitvault_output_root"],
        "design_source_output_root": packet["design_source_output_root"],
        "detached_packet_sha256": detached_sha256,
    }


def source_run_authority_template(packet: Mapping[str, object], detached_sha256: str) -> dict[str, object]:
    """Build the exact V6 authority object for an offline packet author."""

    try:
        if not _valid_sha(detached_sha256):
            raise ValueError
        return _expected_source_run_authority(packet, detached_sha256)
    except Exception as exc:
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def canonical_selection_bytes(dates: tuple[str, ...] | list[str]) -> bytes:
    try:
        if type(dates) not in (tuple, list) or len(dates) == 0:
            raise ValueError
        previous: str | None = None
        lines: list[bytes] = []
        for day in dates:
            if type(day) is not str or datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day:
                raise ValueError
            if day < "2016-01-04" or day >= "2021-01-01":
                raise ValueError
            if previous is not None and day <= previous:
                raise ValueError
            previous = day
            lines.append(day.encode("ascii") + b"\n")
        return DESIGN_DATE_SET_PREFIX + b"".join(lines)
    except Exception as exc:
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def _parse_jsonl(payload: bytes) -> list[dict[str, object]]:
    if type(payload) is not bytes or not payload or not payload.endswith(b"\n"):
        raise ValueError
    rows = []
    for raw in payload.splitlines():
        value = json.loads(raw)
        if type(value) is not dict or canonical_json(value) != raw:
            raise ValueError
        rows.append(value)
    return rows


def _parse_object(payload: bytes) -> dict[str, object]:
    if type(payload) is not bytes or not payload.endswith(b"\n") or payload.count(b"\n") != 1:
        raise ValueError
    value = json.loads(payload)
    if type(value) is not dict or canonical_json(value) + b"\n" != payload:
        raise ValueError
    return value


def _reject_forbidden_recursive(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if lowered in _FORBIDDEN_FIELDS:
                raise ValueError
            _reject_forbidden_recursive(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_forbidden_recursive(child)


def preflight_selection_manifest(
    manifest_payload: bytes,
    *,
    expected_count: int = FROZEN_DESIGN_DATE_COUNT,
    expected_date_set_sha256: str = FROZEN_DESIGN_DATE_SET_SHA256,
) -> SelectionPreflight:
    try:
        if type(expected_count) is not int or expected_count <= 0 or not _valid_sha(expected_date_set_sha256):
            raise ValueError
        rows = _parse_jsonl(manifest_payload)
        dates: list[str] = []
        for row in rows:
            if set(row) != _SELECTION_FIELDS or row.get("schema_version") != _SELECTION_SCHEMA:
                raise ValueError
            _reject_forbidden_recursive(row)
            day = row.get("date")
            if type(day) is not str:
                raise ValueError
            dates.append(day)
        date_bytes = canonical_selection_bytes(tuple(dates))
        if len(dates) != expected_count or _digest(date_bytes) != expected_date_set_sha256:
            raise ValueError
        return SelectionPreflight(tuple(dates), _digest(date_bytes), _digest(manifest_payload), len(rows), bytes(manifest_payload))
    except Exception as exc:
        if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def validate_selection_mapping(
    mapping_payload: bytes,
    selected_dates: tuple[str, ...],
) -> SelectionMapping:
    try:
        if type(selected_dates) is not tuple or selected_dates != tuple(sorted(set(selected_dates))):
            raise ValueError
        rows = _parse_jsonl(mapping_payload)
        all_mapping: dict[str, dict[str, object]] = {}
        expected_fields = {"bytes", "date", "relative_path", "schema_version", "sha256"}
        for row in rows:
            if set(row) != expected_fields or row["schema_version"] != "trendstack_006_selected_design_shard.v1":
                raise ValueError
            day = row["date"]
            relative = row["relative_path"]
            if (
                type(day) is not str
                or datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day
                or day < "2016-01-04"
                or day >= "2021-01-01"
                or day in all_mapping
                or type(relative) is not str
                or relative.startswith("/")
                or "\\" in relative
                or ".." in relative.split("/")
                or relative != f"public/DESIGN/{day}/h1.parquet"
                or type(row["bytes"]) is not int
                or row["bytes"] <= 0
                or not _valid_sha(row["sha256"])
            ):
                raise ValueError
            all_mapping[day] = dict(row)
        mapping = {day: all_mapping[day] for day in selected_dates if day in all_mapping}
        actual_extra_dates = len(all_mapping) - len(mapping)
        if (
            tuple(all_mapping) != tuple(sorted(all_mapping))
            or tuple(mapping) != selected_dates
            or type(actual_extra_dates) is not int
            or actual_extra_dates < 0
        ):
            raise ValueError
        return SelectionMapping(
            bytes(mapping_payload),
            _digest(mapping_payload),
            selected_dates,
            mapping,
            actual_extra_dates,
        )
    except Exception as exc:
        if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


class NarrowDesignCapability:
    """Selected DESIGN shards only; extra DESIGN dates remain unreachable."""

    def __init__(
        self,
        *,
        available_dates: tuple[str, ...],
        selected_dates: tuple[str, ...],
        selected_hashes: dict[str, str],
        day_reader: Callable[[str], bytes],
        public_receipt: bytes,
        public_manifest: bytes,
        selection_preflight: SelectionPreflight | None = None,
        selection_mapping: SelectionMapping | None = None,
        selection_manifest: bytes | None = None,
        actual_extra_design_dates: int | None = None,
        upstream_open_counts=None,
    ) -> None:
        derived_extra_dates = len(set(available_dates)) - len(set(selected_dates))
        actual_extra = derived_extra_dates if actual_extra_design_dates is None else actual_extra_design_dates
        if (
            type(available_dates) is not tuple
            or available_dates != tuple(sorted(set(available_dates)))
            or type(selected_dates) is not tuple
            or type(selected_hashes) is not dict
            or set(selected_dates) - set(available_dates)
            or tuple(sorted(selected_dates)) != selected_dates
            or any(not _valid_sha(value) for value in selected_hashes.values())
            or set(selected_hashes) != set(selected_dates)
            or not callable(day_reader)
            or type(public_receipt) is not bytes
            or type(public_manifest) is not bytes
            or (selection_preflight is not None and type(selection_preflight) is not SelectionPreflight)
            or (selection_mapping is not None and type(selection_mapping) is not SelectionMapping)
            or (selection_preflight is not None and selection_preflight.dates != selected_dates)
            or (selection_mapping is not None and selection_mapping.dates != selected_dates)
            or (selection_manifest is not None and type(selection_manifest) is not bytes)
            or type(actual_extra) is not int
            or actual_extra < 0
            or actual_extra != derived_extra_dates
            or (upstream_open_counts is not None and not callable(upstream_open_counts))
        ):
            raise InvalidSupervisor(PUBLIC_ERROR)
        self._available = available_dates
        self._selected = selected_dates
        self._unselected = tuple(day for day in available_dates if day not in set(selected_dates))
        self._actual_extra_design_dates = actual_extra
        self._hashes = dict(selected_hashes)
        self._reader = day_reader
        self._upstream_open_counts = upstream_open_counts
        self._receipt = bytes(public_receipt)
        self._manifest = bytes(public_manifest)
        self._opened: set[str] = set()
        self._attempted = {day: 0 for day in selected_dates}
        self._selection_preflight = selection_preflight
        self._selection_mapping = selection_mapping
        self._selection_manifest = bytes(selection_manifest) if selection_manifest is not None else None
        self._bytes = (
            {day: int(selection_mapping.mapping[day]["bytes"]) for day in selected_dates}
            if selection_mapping is not None
            else {}
        )
        if selection_mapping is not None and any(
            selection_mapping.mapping[day]["sha256"] != self._hashes[day]
            for day in selected_dates
        ):
            raise InvalidSupervisor(PUBLIC_ERROR)
        if self._upstream_open_counts is not None and any(self._validated_upstream_open_counts().values()):
            raise InvalidSupervisor(PUBLIC_ERROR)

    def design_dates(self) -> tuple[str, ...]:
        return self._selected

    def read_design_day(self, day: str) -> bytes:
        try:
            if day not in self._hashes or day in self._opened:
                raise ValueError
            self._opened.add(day)
            self._attempted[day] += 1
            payload = self._reader(day)
            if (
                type(payload) is not bytes
                or _digest(payload) != self._hashes[day]
                or (day in self._bytes and len(payload) != self._bytes[day])
            ):
                raise ValueError
            return payload
        except Exception as exc:
            raise InvalidSupervisor(PUBLIC_ERROR) from exc

    def public_receipt_bytes(self) -> bytes:
        return self._receipt

    def public_manifest_bytes(self) -> bytes:
        return self._manifest

    def actual_extra_design_dates(self) -> int:
        return self._actual_extra_design_dates

    def selection_manifest_bytes(self) -> bytes:
        if self._selection_manifest is None:
            raise InvalidSupervisor(PUBLIC_ERROR)
        return self._selection_manifest

    def selection_mapping_bytes(self) -> bytes:
        if self._selection_mapping is None:
            raise InvalidSupervisor(PUBLIC_ERROR)
        return self._selection_mapping.payload

    def open_count_summary(self) -> dict[str, int]:
        if self._upstream_open_counts is not None:
            upstream = self._validated_upstream_open_counts()
            if (
                any(upstream[day] != self._attempted[day] for day in self._selected)
                or any(upstream[day] != 0 for day in self._unselected)
            ):
                raise InvalidSupervisor(PUBLIC_ERROR)
        return {
            "raw_source_opens": 1,
            "selected_shard_opens": sum(self._attempted.values()),
            "unselected_shard_opens": 0,
        }

    def attempted_open_count(self) -> int:
        return sum(self._attempted.values())

    def attempted_open_counts(self) -> dict[str, int]:
        return dict(self._attempted)

    def _validated_upstream_open_counts(self) -> dict[str, int]:
        try:
            counts = self._upstream_open_counts()
            if (
                type(counts) is not dict
                or set(counts) != set(self._available)
                or any(type(value) is not int or value < 0 for value in counts.values())
            ):
                raise ValueError
            return dict(counts)
        except Exception as exc:
            raise InvalidSupervisor(PUBLIC_ERROR) from exc


_PUBLIC_RECEIPT_FIELDS = frozenset(
    {
        "collection_id",
        "design_dates",
        "design_manifest_sha256",
        "raw_source_opens",
        "research_holdout_opened",
        "research_validation_opened",
        "schema_version",
        "source_attempt_id",
        "source_rows",
        "unselected_shard_opens",
        "verdict",
    }
)


def prepare_narrow_design_capability(
    custody_capability,
    selection_preflight: SelectionPreflight,
    *,
    expected_source_attempt_id: str,
) -> NarrowDesignCapability:
    """Bind custody metadata before exposing any selected payload reader."""

    try:
        if (
            type(selection_preflight) is not SelectionPreflight
            or not _valid_attempt_id(expected_source_attempt_id)
        ):
            raise ValueError
        manifest_payload = custody_capability.public_manifest_bytes()
        receipt_payload = custody_capability.public_receipt_bytes()
        receipt = _parse_object(receipt_payload)
        _reject_forbidden_recursive(receipt)
        if (
            set(receipt) != _PUBLIC_RECEIPT_FIELDS
            or receipt["collection_id"] != COLLECTION_ID
            or receipt["schema_version"] != "h1_splitvault_002_public_receipt.v1"
            or receipt["source_attempt_id"] != expected_source_attempt_id
            or receipt["verdict"] != "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"
            or receipt["design_manifest_sha256"] != _digest(manifest_payload)
            or type(receipt["design_dates"]) is not int
            or receipt["raw_source_opens"] != 1
            or receipt["unselected_shard_opens"] != 0
            or receipt["research_validation_opened"] is not False
            or receipt["research_holdout_opened"] is not False
            or type(receipt["source_rows"]) is not int
            or receipt["source_rows"] <= 0
        ):
            raise ValueError
        actual_extra_design_dates = receipt["design_dates"] - len(selection_preflight.dates)
        if type(actual_extra_design_dates) is not int or actual_extra_design_dates < 0:
            raise ValueError
        public_rows = _parse_jsonl(manifest_payload)
        public_by_date: dict[str, dict[str, object]] = {}
        for row in public_rows:
            day = row.get("date")
            if (
                set(row) != _PUBLIC_MANIFEST_FIELDS
                or row.get("schema_version") != _PUBLIC_MANIFEST_SCHEMA
                or type(day) is not str
                or day in public_by_date
                or datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day
                or day < "2016-01-04"
                or day >= "2021-01-01"
                or row.get("relative_path") != f"public/DESIGN/{day}/h1.parquet"
                or type(row.get("bytes")) is not int
                or int(row["bytes"]) <= 0
                or type(row.get("rows")) is not int
                or int(row["rows"]) <= 0
                or not _valid_sha(row.get("sha256"))
            ):
                raise ValueError
            public_by_date[day] = row
        available_dates = tuple(public_by_date)
        if available_dates != tuple(sorted(available_dates)):
            raise ValueError
        if (
            len(public_by_date) != receipt["design_dates"]
            or not set(selection_preflight.dates).issubset(public_by_date)
            or len(public_by_date) - len(selection_preflight.dates) != actual_extra_design_dates
        ):
            raise ValueError
        full_mapping_payload = b"".join(
            canonical_json(
                {
                    "bytes": public_by_date[day]["bytes"],
                    "date": day,
                    "relative_path": public_by_date[day]["relative_path"],
                    "schema_version": "trendstack_006_selected_design_shard.v1",
                    "sha256": public_by_date[day]["sha256"],
                }
            )
            + b"\n"
            for day in available_dates
        )
        full_mapping = validate_selection_mapping(full_mapping_payload, selection_preflight.dates)
        if full_mapping.extra_date_count != actual_extra_design_dates:
            raise ValueError
        mapping_payload = b"".join(
            canonical_json(full_mapping.mapping[day]) + b"\n"
            for day in selection_preflight.dates
        )
        mapping = SelectionMapping(
            mapping_payload,
            _digest(mapping_payload),
            selection_preflight.dates,
            dict(full_mapping.mapping),
            actual_extra_design_dates,
        )
        hashes = {
            day: str(mapping.mapping[day]["sha256"])
            for day in selection_preflight.dates
        }
        return NarrowDesignCapability(
            available_dates=available_dates,
            selected_dates=selection_preflight.dates,
            selected_hashes=hashes,
            day_reader=custody_capability.read_design_day,
            public_receipt=receipt_payload,
            public_manifest=manifest_payload,
            selection_preflight=selection_preflight,
            selection_mapping=mapping,
            selection_manifest=selection_preflight.payload,
            actual_extra_design_dates=actual_extra_design_dates,
            upstream_open_counts=custody_capability.open_counts,
        )
    except Exception as exc:
        if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def build_child_payload(capability: NarrowDesignCapability, *, selection_manifest: bytes, contract: dict[str, object]) -> dict[str, object]:
    try:
        if type(capability) is not NarrowDesignCapability or type(selection_manifest) is not bytes or type(contract) is not dict:
            raise ValueError
        required = {"collection_id", "hypothesis_id", "source_attempt_id", "stage_role", "output_capability"}
        if set(contract) != required:
            raise ValueError
        for key, value in contract.items():
            if key == "output_capability":
                if value != "trendstack_006_design_h1":
                    raise ValueError
            else:
                _reject_forbidden_recursive({key: value})
        if (
            contract["collection_id"] != COLLECTION_ID
            or contract["hypothesis_id"] != HYPOTHESIS_ID
            or not _valid_attempt_id(contract["source_attempt_id"])
            or contract["stage_role"] != "DESIGN"
        ):
            raise ValueError
        if capability._selection_preflight is not None:
            accepted = preflight_selection_manifest(
                selection_manifest,
                expected_count=len(capability._selected),
                expected_date_set_sha256=capability._selection_preflight.date_set_sha256,
            )
            if accepted != capability._selection_preflight:
                raise ValueError
        selected = capability.design_dates()
        shards = []
        for day in selected:
            payload = capability.read_design_day(day)
            shards.append({"date": day, "payload": payload, "sha256": _digest(payload)})
        return {
            "collection_id": COLLECTION_ID,
            "hypothesis_id": HYPOTHESIS_ID,
            "actual_extra_design_dates": capability.actual_extra_design_dates(),
            "design_dates": selected,
            "selection_manifest": bytes(selection_manifest),
            "custody_receipt": capability.public_receipt_bytes(),
            "custody_manifest": capability.public_manifest_bytes(),
            "selected_shards": tuple(shards),
            "contract": dict(contract),
        }
    except Exception as exc:
        if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


class BoundChildCapability:
    """In-memory sealed handoff; it exposes only builder-approved DESIGN bytes."""

    def __init__(self, payload: dict[str, object], selection_mapping: SelectionMapping) -> None:
        try:
            if type(payload) is not dict or type(selection_mapping) is not SelectionMapping:
                raise ValueError
            expected = {
                "actual_extra_design_dates", "collection_id", "contract", "custody_manifest", "custody_receipt",
                "design_dates", "hypothesis_id", "selected_shards", "selection_manifest",
            }
            if (
                set(payload) != expected
                or tuple(payload["design_dates"]) != selection_mapping.dates
                or type(payload["actual_extra_design_dates"]) is not int
                or payload["actual_extra_design_dates"] < 0
                or payload["actual_extra_design_dates"] != selection_mapping.extra_date_count
            ):
                raise ValueError
            shards = tuple(payload["selected_shards"])
            if len(shards) != len(selection_mapping.dates):
                raise ValueError
            self._payloads: dict[str, bytes] = {}
            for day, item in zip(selection_mapping.dates, shards):
                if (
                    type(item) is not dict
                    or set(item) != {"date", "payload", "sha256"}
                    or item["date"] != day
                    or type(item["payload"]) is not bytes
                    or item["sha256"] != _digest(item["payload"])
                    or item["sha256"] != selection_mapping.mapping[day]["sha256"]
                    or len(item["payload"]) != selection_mapping.mapping[day]["bytes"]
                ):
                    raise ValueError
                self._payloads[day] = item["payload"]
            self._dates = selection_mapping.dates
            self._actual_extra_design_dates = int(payload["actual_extra_design_dates"])
            self._selection = bytes(payload["selection_manifest"])
            self._mapping = bytes(selection_mapping.payload)
            self._receipt = bytes(payload["custody_receipt"])
            self._manifest = bytes(payload["custody_manifest"])
            self._opened: set[str] = set()
        except Exception as exc:
            raise InvalidSupervisor(PUBLIC_ERROR) from exc

    def design_dates(self) -> tuple[str, ...]:
        return self._dates

    def read_design_day(self, day: str) -> bytes:
        if day not in self._payloads or day in self._opened:
            raise InvalidSupervisor(PUBLIC_ERROR)
        self._opened.add(day)
        return self._payloads[day]

    def selection_manifest_bytes(self) -> bytes: return self._selection
    def selection_mapping_bytes(self) -> bytes: return self._mapping
    def public_receipt_bytes(self) -> bytes: return self._receipt
    def public_manifest_bytes(self) -> bytes: return self._manifest

    def actual_extra_design_dates(self) -> int: return self._actual_extra_design_dates

    def open_count_summary(self) -> dict[str, int]:
        if self._opened != set(self._dates):
            raise InvalidSupervisor(PUBLIC_ERROR)
        return {
            "raw_source_opens": 1,
            "selected_shard_opens": len(self._dates),
            "unselected_shard_opens": 0,
        }


def materialize_child_capability(
    capability: NarrowDesignCapability,
    *,
    source_attempt_id: str,
) -> BoundChildCapability:
    try:
        if (
            type(capability) is not NarrowDesignCapability
            or capability._selection_preflight is None
            or capability._selection_mapping is None
        ):
            raise ValueError
        payload = build_child_payload(
            capability,
            selection_manifest=capability._selection_preflight.payload,
            contract={
                "collection_id": COLLECTION_ID,
                "hypothesis_id": HYPOTHESIS_ID,
                "source_attempt_id": source_attempt_id,
                "stage_role": "DESIGN",
                "output_capability": "trendstack_006_design_h1",
            },
        )
        if capability.attempted_open_count() != len(capability.design_dates()):
            raise ValueError
        counts = capability.open_count_summary()
        if (
            counts.get("selected_shard_opens") != len(capability.design_dates())
            or counts.get("unselected_shard_opens") != 0
            or capability.actual_extra_design_dates() != capability._selection_mapping.extra_date_count
        ):
            raise ValueError
        return BoundChildCapability(payload, capability._selection_mapping)
    except Exception as exc:
        if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def _validate_full_packet(packet: dict[str, object]) -> dict[str, object]:
    if type(packet) is not dict or set(packet) != FULL_PACKET_FIELDS:
        raise ValueError
    if (
        packet["schema_version"] != "trendstack_006_h1_splitvault_source_run_packet.v1"
        or packet["collection_id"] != COLLECTION_ID
        or packet["hypothesis_id"] != HYPOTHESIS_ID
        or packet["registry_row_index"] != REGISTRY_ROW_INDEX
        or packet["registry_row_sha256"] != REGISTRY_ROW_SHA256
        or not _valid_attempt_id(packet["source_attempt_id"])
    ):
        raise ValueError
    for key, expected in FROZEN_PACKET_VALUES.items():
        if packet.get(key) != expected:
            raise ValueError
    for key, value in packet.items():
        if key.endswith("_sha256") and not _valid_sha(value):
            raise ValueError
        if (key.endswith("_path") or key.endswith("_root")) and (
            type(value) is not str or not value or ".." in value.replace("\\", "/").split("/")
        ):
            raise ValueError
    if (
        packet["expected_design_dates"] != FROZEN_PACKET_VALUES["expected_design_dates"]
        or packet["expected_rows_per_day"] != FROZEN_PACKET_VALUES["expected_rows_per_day"]
        or packet["expected_total_rows"] != FROZEN_PACKET_VALUES["expected_total_rows"]
        or packet["expected_raw_opens"] != FROZEN_PACKET_VALUES["expected_raw_opens"]
        or packet["expected_selected_opens"] != FROZEN_PACKET_VALUES["expected_selected_opens"]
        or packet["expected_unselected_opens"] != FROZEN_PACKET_VALUES["expected_unselected_opens"]
        or packet["one_shot_custody_source_attempt_authorized"] is not True
        or packet["review_base_supervisor_sha256"] != packet["supervisor_review_base_sha256"]
    ):
        raise ValueError
    for key in (
        "network_allowed", "subprocess_allowed", "economics_authorized",
        "validation_authorized", "holdout_authorized", "performance_metrics_authorized",
        "mt5_authorized", "model0_authorized", "promotion_authorized",
        "paper_authorized", "live_authorized", "deploy_authorized", "trading_mutation",
    ):
        if packet[key] is not False:
            raise ValueError
    detached = compute_detached_packet_sha256(packet)
    if (
        packet["reviewed_run_packet_sha256"] != detached
        or type(packet["authority"]) is not dict
        or set(packet["authority"]) != _SOURCE_RUN_AUTHORITY_FIELDS
        or packet["authority"] != _expected_source_run_authority(packet, detached)
    ):
        raise ValueError
    return dict(packet)


def validate_full_packet_document(payload: bytes, expected_sha256: str) -> VerifiedRunPacket:
    try:
        if (
            type(payload) is not bytes
            or not payload.endswith(b"\n")
            or payload.count(b"\n") != 1
            or not _valid_sha(expected_sha256)
        ):
            raise ValueError
        packet = json.loads(payload)
        if canonical_json(packet) + b"\n" != payload:
            raise ValueError
        accepted = _validate_full_packet(packet)
        detached = compute_detached_packet_sha256(accepted)
        if detached != expected_sha256:
            raise ValueError
        return VerifiedRunPacket(accepted, detached, bytes(payload))
    except Exception as exc:
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def validate_run_packet(packet: dict[str, object]) -> dict[str, object]:
    try:
        # A mapping cannot prove canonical packet bytes or their detached digest.
        # Production therefore accepts only validate_full_packet_document output.
        raise ValueError
    except Exception as exc:
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


_SAFE_TERMINAL_FIELDS = frozenset(
    {
        "design_date_set_sha256",
        "source_receipt_sha256",
        "validated_dates",
        "validated_h1_rows",
        "validator_test_sha256",
        "validator_tool_sha256",
        "disarmed_supervisor_sha256",
        "supervisor_sentinel_status",
        "arm_manifest_sha256",
        "dependency_attestation_sha256",
        "actual_extra_design_dates",
    }
)
_READY = "SOURCE_READY_FOR_SEPARATE_DESIGN_ECONOMIC_RUN_PACKET"
_FAILED = "SOURCE_ATTEMPT_FAILED_ENGINEERING_NO_MARKET_VERDICT"


def _sanitized_terminal_evidence(value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise ValueError
    return {key: value[key] for key in sorted(_SAFE_TERMINAL_FIELDS) if key in value}


def _run_one_shot_lifecycle(packet: VerifiedRunPacket, operations) -> dict[str, object]:
    """Order-sensitive core used by the production wrapper and synthetic tests."""

    global REVIEWED_RUN_PACKET_SHA256
    marker: dict[str, object] | None = None
    marker_sha256: str | None = None
    context = None
    disarm_evidence: dict[str, object] | None = None
    disarm_attempted = False
    phase = "PRE_MARKER"
    try:
        if (
            type(packet) is not VerifiedRunPacket
            or REVIEWED_RUN_PACKET_SHA256 != packet.detached_sha256
            or not _valid_sha(REVIEWED_RUN_PACKET_SHA256)
        ):
            raise ValueError
        context = operations.preflight(packet)
        phase = "PREFLIGHT_COMPLETE"
        marker, marker_sha256 = operations.start(packet, context)
        phase = "MARKER_WRITTEN"
        if (
            type(marker) is not dict
            or marker.get("verdict") != "ATTEMPT_CONSUMED"
            or not _valid_sha(marker_sha256)
        ):
            raise ValueError
        result = operations.pipeline(packet, marker, context)
        phase = "PIPELINE_COMPLETE"
        if type(result) is not dict or result.get("verdict") != _READY:
            raise ValueError
        disarm_attempted = True
        disarm_evidence = operations.disarm(packet, context)
        if (
            type(disarm_evidence) is not dict
            or set(disarm_evidence) != {
                "disarmed_supervisor_sha256", "supervisor_sentinel_status", "arm_manifest_sha256"
            }
            or not _valid_sha(disarm_evidence["disarmed_supervisor_sha256"])
            or disarm_evidence["supervisor_sentinel_status"] != "DISARMED_NONE_VERIFIED"
            or not _valid_sha(disarm_evidence["arm_manifest_sha256"])
        ):
            raise ValueError
        phase = "DISARM_VERIFIED"
        evidence = _sanitized_terminal_evidence({**result, **disarm_evidence})
        phase = "READY_TERMINAL_WRITE"
        terminal_sha256 = operations.terminal(packet, marker_sha256, _READY, evidence, context)
        if not _valid_sha(terminal_sha256):
            raise ValueError
        return {
            **evidence,
            "attempt_started_sha256": marker_sha256,
            "attempt_terminal_sha256": terminal_sha256,
            "packet_sha256": packet.detached_sha256,
            "source_attempt_id": packet["source_attempt_id"],
            "verdict": _READY,
        }
    except Exception as exc:
        disarm_error: Exception | None = exc if disarm_attempted and disarm_evidence is None else None
        terminal_error: Exception | None = None
        if marker is not None and marker_sha256 is not None and context is not None:
            if not disarm_attempted:
                try:
                    disarm_attempted = True
                    disarm_evidence = operations.disarm(packet, context)
                except Exception as failure:
                    disarm_error = failure
            try:
                failure_evidence = _sanitized_terminal_evidence(disarm_evidence or {})
                terminal_sha256 = operations.terminal(packet, marker_sha256, _FAILED, failure_evidence, context)
                if not _valid_sha(terminal_sha256):
                    raise ValueError
            except Exception as failure:
                terminal_error = failure
        failures = []
        if disarm_error is not None:
            failures.append("DISARM_FAILED")
        if phase == "READY_TERMINAL_WRITE":
            failures.append("READY_TERMINAL_FAILED")
        if terminal_error is not None:
            failures.append("TERMINAL_FAILED")
        if failures:
            raise InvalidSupervisor(PUBLIC_ERROR + ":" + ";".join(failures)) from exc
        if isinstance(exc, InvalidSupervisor) and str(exc).startswith(PUBLIC_ERROR):
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc
    finally:
        REVIEWED_RUN_PACKET_SHA256 = None


def _resolve_path(value: object, workspace: Path) -> Path:
    if type(value) is not str or not value:
        raise ValueError
    path = Path(value)
    return path.absolute() if path.is_absolute() else (workspace / path).absolute()


def _assert_no_ads(path: Path) -> None:
    raw = str(path)
    tail = raw[2:] if len(raw) >= 2 and raw[1] == ":" else raw
    if ":" in tail:
        raise ValueError
    if os.name != "nt" or not path.exists() or path == Path(path.anchor):
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _StreamData(ctypes.Structure):
        _fields_ = [("size", ctypes.c_longlong), ("name", ctypes.c_wchar * 296)]

    data = _StreamData()
    first = kernel32.FindFirstStreamW
    first.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    first.restype = ctypes.c_void_p
    handle = first(str(path), 0, ctypes.byref(data), 0)
    if handle == ctypes.c_void_p(-1).value:
        if ctypes.get_last_error() not in (1, 38):
            raise OSError(ctypes.get_last_error(), "FindFirstStreamW")
        return
    names = []
    try:
        names.append(data.name)
        next_stream = kernel32.FindNextStreamW
        next_stream.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        next_stream.restype = ctypes.c_int
        while next_stream(handle, ctypes.byref(data)):
            names.append(data.name)
    finally:
        close = kernel32.FindClose
        close.argtypes = [ctypes.c_void_p]
        close.restype = ctypes.c_int
        close(handle)
    if names != ["::$DATA"]:
        raise ValueError


def _node_info(path: Path, *, directory: bool) -> os.stat_result:
    info = os.lstat(path)
    attributes = int(getattr(info, "st_file_attributes", 0))
    if attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)) or path.is_symlink():
        raise ValueError
    if directory:
        if not stat.S_ISDIR(info.st_mode) or (path != Path(path.anchor) and path.is_mount()):
            raise ValueError
    elif not stat.S_ISREG(info.st_mode) or int(info.st_nlink) != 1:
        raise ValueError
    _assert_no_ads(path)
    return info


def _directory_chain(path: Path) -> None:
    current = path.absolute().parent
    while True:
        _node_info(current, directory=True)
        if current.parent == current:
            return
        current = current.parent


def _file_anchor(path: Path) -> tuple[int, int, int, int, int, int, int]:
    info = _node_info(path, directory=False)
    return (
        int(info.st_dev), int(info.st_ino), int(info.st_size), int(info.st_mtime_ns),
        int(info.st_ctime_ns), int(info.st_nlink), int(getattr(info, "st_file_attributes", 0)),
    )


def _stable_file_read(path: Path, expected: tuple[int, ...] | None = None) -> bytes:
    if expected is not None and _file_anchor(path) != expected:
        raise ValueError
    _directory_chain(path)
    before = _file_anchor(path)
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (int(opened.st_dev), int(opened.st_ino)) != before[:2]:
            raise ValueError
        payload = handle.read()
        final = os.fstat(handle.fileno())
    after = _file_anchor(path)
    if before != after or int(final.st_size) != len(payload) or (expected is not None and after != expected):
        raise ValueError
    return payload


def _fsync_directory(path: Path) -> None:
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel32.CreateFileW
    create.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    create.restype = ctypes.c_void_p
    handle = create(str(path), 0x40000000, 0x7, None, 3, 0x02000000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "CreateFileW")
    try:
        flush = kernel32.FlushFileBuffers
        flush.argtypes = [ctypes.c_void_p]
        flush.restype = ctypes.c_int
        if not flush(handle):
            raise OSError(ctypes.get_last_error(), "FlushFileBuffers")
    finally:
        kernel32.CloseHandle(handle)


def _mkdirs(path: Path) -> None:
    missing: list[Path] = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    _directory_chain(current / "child")
    for directory in reversed(missing):
        directory.mkdir()
        _node_info(directory, directory=True)
        _fsync_directory(directory.parent)


def _exclusive_write(path: Path, payload: bytes) -> None:
    if type(payload) is not bytes or os.path.lexists(path):
        raise ValueError
    _mkdirs(path.parent)
    _directory_chain(path)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    _fsync_directory(path.parent)
    if _stable_file_read(path) != payload:
        raise ValueError


@dataclass(frozen=True)
class FrozenSymbol:
    name: str
    value: object
    value_type: type


_READ_ONLY_PROXY_STATE: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


class ReadOnlyDependencyProxy:
    __slots__ = ("__weakref__",)

    def __init__(self, name: str, symbols: dict[str, object]) -> None:
        _READ_ONLY_PROXY_STATE[self] = (name, types.MappingProxyType(dict(symbols)))

    def __getattr__(self, name: str) -> object:
        symbols = _READ_ONLY_PROXY_STATE[self][1]
        try:
            return symbols[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("read-only dependency proxy")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("read-only dependency proxy")

    def __repr__(self) -> str:
        return f"<verified dependency proxy {_READ_ONLY_PROXY_STATE[self][0]}>"


@dataclass(frozen=True)
class FrozenDependency:
    name: str
    module: types.ModuleType
    origin: str
    file_identity: tuple[int, ...] | None
    file_sha256: str | None
    loader: object
    loader_type: str
    symbols: tuple[FrozenSymbol, ...]
    proxy: ReadOnlyDependencyProxy


_TRUSTED_STANDARD_MODULES = {
    "__future__": _trusted_future,
    "_strptime": _trusted_strptime,
    "ctypes": ctypes,
    "dataclasses": _trusted_dataclasses,
    "datetime": _trusted_datetime,
    "hashlib": hashlib,
    "json": json,
    "math": math,
    "os": os,
    "pathlib": _trusted_pathlib,
    "stat": stat,
}
_EXACT_DEPENDENCY_SYMBOL_PATHS = {
    "__future__": ("annotations",),
    "_strptime": (),
    "ctypes": (
        "CDLL", "Structure", "WinDLL", "byref", "c_char_p", "c_int", "c_longlong",
        "c_uint", "c_uint32", "c_void_p", "c_wchar", "c_wchar_p", "get_errno",
        "get_last_error",
    ),
    "dataclasses": ("dataclass",),
    "datetime": ("datetime", "timedelta"),
    "hashlib": ("sha256",),
    "json": ("dumps", "loads"),
    "math": ("isfinite",),
    "os": (
        "O_RDONLY", "close", "fsencode", "fstat", "fsync", "lstat", "name", "open",
        "path.lexists", "rename", "scandir", "stat_result", "strerror",
    ),
    "pathlib": ("Path",),
    "pyarrow": (
        "BufferOutputStream", "BufferReader", "Table", "float64", "int32", "int8",
        "parquet.ParquetFile", "parquet.write_table", "schema", "timestamp", "uint64",
    ),
    "pyarrow.parquet": ("ParquetFile", "write_table"),
    "stat": ("FILE_ATTRIBUTE_REPARSE_POINT", "S_ISDIR", "S_ISREG"),
}
_MINIMAL_BUILTIN_NAMES = frozenset(
    {
        "__build_class__",
        "Exception", "OSError", "RuntimeError", "ValueError",
        "all", "any", "bool", "bytes", "callable", "dict", "enumerate",
        "float", "frozenset", "getattr", "globals", "int", "isinstance",
        "len", "list", "object", "range", "reversed", "set", "sorted",
        "str", "sum", "tuple", "type", "zip",
    }
)


def _loader_type(loader: object) -> str:
    kind = loader if isinstance(loader, type) else type(loader)
    module_name = getattr(kind, "__module__", None)
    qualname = getattr(kind, "__qualname__", None)
    if type(module_name) is not str or type(qualname) is not str:
        raise ValueError
    return module_name + "." + qualname


def _capture_symbol_proxy(
    name: str,
    value: object,
    paths: tuple[str, ...],
    *,
    prefix: str = "",
) -> tuple[ReadOnlyDependencyProxy, tuple[FrozenSymbol, ...]]:
    grouped: dict[str, list[str]] = {}
    for path in paths:
        if type(path) is not str or not path:
            raise ValueError
        head, separator, tail = path.partition(".")
        grouped.setdefault(head, []).append(tail if separator else "")
    proxy_values: dict[str, object] = {}
    captured: list[FrozenSymbol] = []
    for symbol_name in sorted(grouped):
        symbol = getattr(value, symbol_name)
        qualified = prefix + symbol_name
        captured.append(FrozenSymbol(qualified, symbol, type(symbol)))
        tails = grouped[symbol_name]
        nested = tuple(sorted(tail for tail in tails if tail))
        if "" in tails and nested:
            raise ValueError
        if nested:
            if not isinstance(symbol, types.ModuleType):
                raise ValueError
            nested_proxy, nested_symbols = _capture_symbol_proxy(
                name + "." + symbol_name,
                symbol,
                nested,
                prefix=qualified + ".",
            )
            proxy_values[symbol_name] = nested_proxy
            captured.extend(nested_symbols)
        else:
            proxy_values[symbol_name] = symbol
    return ReadOnlyDependencyProxy(name, proxy_values), tuple(captured)


def _dependency_file_metadata(module: types.ModuleType) -> tuple[str, tuple[int, ...] | None, str | None]:
    spec = getattr(module, "__spec__", None)
    origin = getattr(spec, "origin", None)
    if type(origin) is not str or not origin:
        raise ValueError
    if origin in {"built-in", "frozen"}:
        return origin, None, None
    module_file = getattr(module, "__file__", None)
    if type(module_file) is not str:
        raise ValueError
    path = Path(module_file).absolute()
    origin_path = Path(origin).absolute()
    if os.path.normcase(str(path)) != os.path.normcase(str(origin_path)):
        raise ValueError
    identity = _file_anchor(path)
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (int(opened.st_dev), int(opened.st_ino)) != identity[:2]:
            raise ValueError
        payload = handle.read()
        final = os.fstat(handle.fileno())
    if _file_anchor(path) != identity or int(final.st_size) != len(payload):
        raise ValueError
    return str(path), identity, _digest(payload)


def _canonical_third_party_module(
    name: str,
    search_path,
    trusted: types.ModuleType,
) -> types.ModuleType:
    spec = importlib.machinery.PathFinder.find_spec(name, search_path)
    if spec is None or type(spec.origin) is not str or not spec.origin:
        raise ValueError
    candidate = sys.modules.get(name)
    if candidate is not trusted or not isinstance(candidate, types.ModuleType):
        raise ValueError
    candidate_spec = getattr(candidate, "__spec__", None)
    candidate_origin = getattr(candidate_spec, "origin", None)
    if (
        type(candidate_origin) is not str
        or os.path.normcase(str(Path(candidate_origin).absolute()))
        != os.path.normcase(str(Path(spec.origin).absolute()))
    ):
        raise ValueError
    return candidate


def _freeze_dependency_map() -> dict[str, FrozenDependency]:
    dependencies: dict[str, types.ModuleType] = {}
    for name, module in _TRUSTED_STANDARD_MODULES.items():
        if sys.modules.get(name) is not module:
            raise ValueError
        dependencies[name] = module
    pyarrow = _canonical_third_party_module("pyarrow", sys.path, _trusted_pyarrow)
    package_path = getattr(pyarrow, "__path__", None)
    if package_path is None:
        raise ValueError
    parquet = _canonical_third_party_module(
        "pyarrow.parquet",
        package_path,
        _trusted_pyarrow_parquet,
    )
    if getattr(pyarrow, "parquet", None) is not parquet:
        raise ValueError
    dependencies["pyarrow"] = pyarrow
    dependencies["pyarrow.parquet"] = parquet
    if set(dependencies) != set(_EXACT_DEPENDENCY_SYMBOL_PATHS):
        raise ValueError
    if _PRODUCTION_BOOTSTRAP_ELIGIBLE:
        for name, canonical_spec in _BOOTSTRAP_CANONICAL_SPECS.items():
            module_spec = getattr(dependencies[name], "__spec__", None)
            if (
                sys.modules.get(name) is not dependencies[name]
                or module_spec is not canonical_spec
                or module_spec.loader is not canonical_spec.loader
                or module_spec.origin != canonical_spec.origin
            ):
                raise ValueError
    frozen: dict[str, FrozenDependency] = {}
    for name, module in dependencies.items():
        origin, identity, digest = _dependency_file_metadata(module)
        spec = getattr(module, "__spec__", None)
        loader = getattr(spec, "loader", None)
        if loader is None:
            raise ValueError
        proxy, symbols = _capture_symbol_proxy(
            name,
            module,
            _EXACT_DEPENDENCY_SYMBOL_PATHS[name],
        )
        frozen[name] = FrozenDependency(
            name,
            module,
            origin,
            identity,
            digest,
            loader,
            _loader_type(loader),
            symbols,
            proxy,
        )
    return frozen


def _recheck_dependency_map(dependencies: Mapping[str, FrozenDependency]) -> None:
    if type(dependencies) is not dict or set(dependencies) != set(_EXACT_DEPENDENCY_SYMBOL_PATHS):
        raise ValueError
    for name, frozen in dependencies.items():
        if type(frozen) is not FrozenDependency or frozen.name != name or sys.modules.get(name) is not frozen.module:
            raise ValueError
        origin, identity, digest = _dependency_file_metadata(frozen.module)
        if (origin, identity, digest) != (frozen.origin, frozen.file_identity, frozen.file_sha256):
            raise ValueError
        spec = getattr(frozen.module, "__spec__", None)
        if (
            getattr(spec, "loader", None) is not frozen.loader
            or _loader_type(frozen.loader) != frozen.loader_type
            or type(frozen.proxy) is not ReadOnlyDependencyProxy
        ):
            raise ValueError
        for symbol in frozen.symbols:
            if type(symbol) is not FrozenSymbol or not symbol.name:
                raise ValueError
            current: object = frozen.module
            proxied: object = frozen.proxy
            for component in symbol.name.split("."):
                current = getattr(current, component)
                proxied = getattr(proxied, component)
            if current is not symbol.value or type(current) is not symbol.value_type:
                raise ValueError
            if isinstance(symbol.value, types.ModuleType):
                if type(proxied) is not ReadOnlyDependencyProxy:
                    raise ValueError
            elif proxied is not symbol.value:
                raise ValueError
    if dependencies["pyarrow"].module.parquet is not dependencies["pyarrow.parquet"].module:
        raise ValueError


def _dependency_attestation(
    dependencies: Mapping[str, FrozenDependency],
) -> tuple[dict[str, object], str]:
    _recheck_dependency_map(dependencies)
    document = {
        "dependencies": [
            {
                "file_identity": list(frozen.file_identity) if frozen.file_identity is not None else None,
                "file_sha256": frozen.file_sha256,
                "loader_type": frozen.loader_type,
                "module": name,
                "origin": frozen.origin,
                "symbols": [
                    {
                        "name": symbol.name,
                        "type_module": getattr(symbol.value_type, "__module__", ""),
                        "type_qualname": getattr(symbol.value_type, "__qualname__", ""),
                    }
                    for symbol in frozen.symbols
                ],
            }
            for name, frozen in sorted(dependencies.items())
        ],
        "schema_version": "trendstack_006_dependency_attestation.v1",
    }
    payload = canonical_json(document)
    return document, _digest(payload)


def _recheck_dependency_attestation(context: Mapping[str, object]) -> None:
    document, digest = _dependency_attestation(context["dependencies"])
    if (
        context.get("dependency_attestation") != document
        or context.get("dependency_attestation_sha256") != digest
    ):
        raise ValueError


def _frozen_import(dependencies: Mapping[str, FrozenDependency]):
    def import_only_frozen(name, globals=None, locals=None, fromlist=(), level=0):
        if level != 0 or name not in dependencies:
            raise ImportError("verified module import denied")
        if fromlist or "." not in name:
            return dependencies[name].proxy
        root = name.split(".", 1)[0]
        return dependencies[root].proxy

    return import_only_frozen


def _execute_verified_module(
    payload: bytes,
    path: Path,
    expected_sha256: str,
    dependencies: Mapping[str, FrozenDependency],
):
    """Compile exact frozen bytes in a fresh, non-cached private namespace."""

    if type(payload) is not bytes or not _valid_sha(expected_sha256) or _digest(payload) != expected_sha256:
        raise InvalidSupervisor(PUBLIC_ERROR)
    _recheck_dependency_map(dependencies)
    safe_builtins = {name: getattr(builtins, name) for name in _MINIMAL_BUILTIN_NAMES}
    safe_builtins["__import__"] = _frozen_import(dependencies)
    private_name = "_verified_hyp006_" + expected_sha256
    if private_name in sys.modules:
        raise InvalidSupervisor(PUBLIC_ERROR)
    module = types.ModuleType(private_name)
    namespace = module.__dict__
    namespace.update({
        "__name__": private_name,
        "__file__": str(path),
        "__package__": None,
        "__verified_sha256__": expected_sha256,
        "__builtins__": safe_builtins,
    })
    try:
        # Dataclasses resolves postponed annotations through sys.modules while
        # classes are created.  The private hash-name exists only for that
        # execution window and is never a canonical/cached tool import.
        sys.modules[private_name] = module
        exec(compile(payload, str(path), "exec"), namespace)
        return module
    except Exception as exc:
        raise InvalidSupervisor(PUBLIC_ERROR) from exc
    finally:
        if sys.modules.get(private_name) is module:
            del sys.modules[private_name]


def _verify_registry_rows(payload: bytes, packet: VerifiedRunPacket) -> None:
    if type(payload) is not bytes or not payload.endswith(b"\n"):
        raise ValueError
    lines = payload.splitlines()
    if len(lines) < REGISTRY_ROW_INDEX:
        raise ValueError
    if _digest(lines[REGISTRY_ROW_INDEX - 1]) != REGISTRY_ROW_SHA256:
        raise ValueError
    raw = lines[REGISTRY_ROW_INDEX - 1]
    base = json.loads(raw)
    validation = base.get("validation") if type(base) is dict else None
    if (
        type(base) is not dict
        or base.get("hypothesis_id") != HYPOTHESIS_ID
        or base.get("state") != "probe"
        or type(validation) is not dict
        or validation.get("source_build_authorized") is not True
        or validation.get("source_run_authorized") is not False
        or packet["authority"].get("source_run_authorized") is not True
    ):
        raise ValueError


_ARM_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "collection_id",
        "hypothesis_id",
        "source_attempt_id",
        "registry_row_index",
        "registry_row_sha256",
        "detached_packet_sha256",
        "packet_document_sha256",
        "armed_supervisor_sha256",
        "disarmed_supervisor_sha256",
        "supervisor_review_base_sha256",
        "supervisor_path",
        "packet_path",
        "source_prep_task_packet_sha256",
        "verdict",
    }
)


def _arm_manifest_values(
    packet: VerifiedRunPacket,
    armed_supervisor_payload: bytes,
    supervisor_path: Path,
    packet_path: Path,
) -> dict[str, object]:
    armed_sha256 = _digest(armed_supervisor_payload)
    disarmed_payload = _disarmed_runtime_payload(armed_supervisor_payload, packet.detached_sha256)
    return {
        "schema_version": "trendstack_006_source_run_arm_manifest.v1",
        "collection_id": COLLECTION_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "source_attempt_id": packet["source_attempt_id"],
        "registry_row_index": REGISTRY_ROW_INDEX,
        "registry_row_sha256": REGISTRY_ROW_SHA256,
        "detached_packet_sha256": packet.detached_sha256,
        "packet_document_sha256": _digest(packet.canonical_bytes),
        "armed_supervisor_sha256": armed_sha256,
        "disarmed_supervisor_sha256": _digest(disarmed_payload),
        "supervisor_review_base_sha256": packet["supervisor_review_base_sha256"],
        "supervisor_path": str(supervisor_path.absolute()),
        "packet_path": str(packet_path.absolute()),
        "source_prep_task_packet_sha256": SOURCE_PREP_TASK_PACKET_V9_SHA256,
        "verdict": "ARM_AUTHORITY_VERIFIED",
    }


def build_arm_manifest_document(
    packet: VerifiedRunPacket,
    armed_supervisor_payload: bytes,
    supervisor_path: Path | str,
    packet_path: Path | str,
) -> bytes:
    """Create canonical arm-manifest bytes after the runtime is armed."""

    try:
        if type(packet) is not VerifiedRunPacket or type(armed_supervisor_payload) is not bytes:
            raise ValueError
        supervisor = Path(supervisor_path).absolute()
        packet_file = Path(packet_path).absolute()
        values = _arm_manifest_values(packet, armed_supervisor_payload, supervisor, packet_file)
        if (
            values["armed_supervisor_sha256"] != packet["runtime_supervisor_sha256"]
            or values["disarmed_supervisor_sha256"] != packet["supervisor_review_base_sha256"]
        ):
            raise ValueError
        return canonical_json(values) + b"\n"
    except Exception as exc:
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def create_arm_manifest(
    packet: VerifiedRunPacket,
    supervisor_path: Path | str,
    packet_path: Path | str,
    manifest_path: Path | str,
) -> str:
    """Durably create, never replace, the separate arm authority manifest."""

    try:
        supervisor = Path(supervisor_path).absolute()
        armed_payload = _stable_file_read(supervisor)
        payload = build_arm_manifest_document(packet, armed_payload, supervisor, packet_path)
        destination = Path(manifest_path).absolute()
        _exclusive_write(destination, payload)
        return _digest(payload)
    except Exception as exc:
        if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
            raise
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def validate_arm_manifest_document(
    manifest_payload: bytes,
    packet: VerifiedRunPacket,
    armed_supervisor_payload: bytes,
    supervisor_path: Path | str,
    packet_path: Path | str,
) -> dict[str, object]:
    try:
        if (
            type(manifest_payload) is not bytes
            or not manifest_payload.endswith(b"\n")
            or manifest_payload.count(b"\n") != 1
        ):
            raise ValueError
        values = json.loads(manifest_payload)
        if type(values) is not dict or set(values) != _ARM_MANIFEST_FIELDS:
            raise ValueError
        if canonical_json(values) + b"\n" != manifest_payload:
            raise ValueError
        expected = _arm_manifest_values(
            packet,
            armed_supervisor_payload,
            Path(supervisor_path).absolute(),
            Path(packet_path).absolute(),
        )
        if values != expected or values["armed_supervisor_sha256"] != packet["runtime_supervisor_sha256"]:
            raise ValueError
        return {**values, "arm_manifest_sha256": _digest(manifest_payload)}
    except Exception as exc:
        raise InvalidSupervisor(PUBLIC_ERROR) from exc


def _runtime_review_base(runtime_payload: bytes, packet_sha256: str, *, testing: bool) -> str:
    token = b"REVIEWED_RUN_PACKET_SHA256: str | None = "
    lines = runtime_payload.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line.startswith(token)]
    if len(matches) != 1:
        raise ValueError
    index = matches[0]
    line = lines[index]
    ending = b"\r\n" if line.endswith(b"\r\n") else b"\n" if line.endswith(b"\n") else b""
    armed = token + b'"' + packet_sha256.encode("ascii") + b'"' + ending
    disarmed = token + b"None" + ending
    if line == armed:
        normalized = b"".join(lines[:index] + [disarmed] + lines[index + 1 :])
        return _digest(normalized)
    if testing and line == disarmed:
        return _digest(runtime_payload)
    raise ValueError


def _disarmed_runtime_payload(runtime_payload: bytes, packet_sha256: str) -> bytes:
    if type(runtime_payload) is not bytes or not _valid_sha(packet_sha256):
        raise ValueError
    token = b"REVIEWED_RUN_PACKET_SHA256:" + b" str | None = "
    lines = runtime_payload.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line.startswith(token)]
    if len(matches) != 1:
        raise ValueError
    index = matches[0]
    line = lines[index]
    ending = b"\r\n" if line.endswith(b"\r\n") else b"\n" if line.endswith(b"\n") else b""
    armed = token + b'"' + packet_sha256.encode("ascii") + b'"' + ending
    disarmed = token + b"None" + ending
    if line == disarmed:
        return runtime_payload
    if line != armed:
        raise ValueError
    return b"".join(lines[:index] + [disarmed] + lines[index + 1 :])


def _self_disarm_runtime(packet_sha256: str, runtime_path: Path | str | None = None) -> dict[str, object]:
    path = Path(runtime_path if runtime_path is not None else __file__).absolute()
    original = _stable_file_read(path)
    disarmed = _disarmed_runtime_payload(original, packet_sha256)
    if disarmed != original:
        temporary = path.with_name("." + path.name + ".self-disarm-" + packet_sha256[:16])
        _exclusive_write(temporary, disarmed)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    readback = _stable_file_read(path)
    if readback != disarmed or _runtime_review_base(readback, packet_sha256, testing=True) != _digest(disarmed):
        raise ValueError
    return {
        "disarmed_supervisor_sha256": _digest(disarmed),
        "supervisor_sentinel_status": "DISARMED_NONE_VERIFIED",
    }


class _InProcessOperations:
    """Complete one-shot implementation; no subprocess or external capability."""

    def __init__(
        self,
        packet_path: Path,
        *,
        workspace: Path | None = None,
        arm_manifest_path: Path | None = None,
        testing_build_shape=None,
        testing_validation_shape=None,
        testing_clock_converter=None,
        _require_clean_bootstrap: bool = False,
    ) -> None:
        self.packet_path = packet_path.absolute()
        self.arm_manifest_path = (
            arm_manifest_path.absolute()
            if arm_manifest_path is not None
            else self.packet_path.with_name(ARM_MANIFEST_NAME)
        )
        self.workspace = (workspace or Path(__file__).resolve().parents[3]).absolute()
        self.testing_build_shape = testing_build_shape
        self.testing_validation_shape = testing_validation_shape
        self.testing_clock_converter = testing_clock_converter
        self._require_clean_bootstrap = _require_clean_bootstrap
        self.testing = testing_build_shape is not None or testing_validation_shape is not None
        if (
            (testing_build_shape is None) != (testing_validation_shape is None)
            or type(_require_clean_bootstrap) is not bool
        ):
            raise InvalidSupervisor(PUBLIC_ERROR)

    def _path(self, packet: VerifiedRunPacket, key: str) -> Path:
        return _resolve_path(packet[key], self.workspace)

    def _validate_production_paths(self, packet: VerifiedRunPacket) -> None:
        if self.testing:
            return
        source = self._path(packet, "source_path")
        research = Path(__file__).resolve().parent
        expected = {
            "custodian_tool_path": research / "h1_splitvault_002_custodian.py",
            "supervisor_tool_path": Path(__file__).resolve(),
            "design_builder_tool_path": research / "build_trendstack_006_design_source.py",
            "validator_tool_path": research / "validate_trendstack_006_design_source.py",
            "custodian_test_path": research / "tests" / "test_h1_splitvault_002_custodian.py",
            "supervisor_test_path": research / "tests" / "test_h1_splitvault_002_supervisor.py",
            "design_builder_test_path": research / "tests" / "test_build_trendstack_006_design_source.py",
            "validator_test_path": research / "tests" / "test_validate_trendstack_006_design_source.py",
            "parent_stage0_ledger_path": research / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_STAGE0" / "stage0_eligibility_ledger.jsonl",
            "parent_stage0_receipt_path": research / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_STAGE0" / "stage0_receipt.json",
            "splitvault_output_root": source.parent / "h1_splitvault_002",
            "design_source_output_root": source.parent / "trendstack_006_design_h1",
        }
        for key, path in expected.items():
            if self._path(packet, key) != path.absolute():
                raise ValueError
        attempt = str(packet["source_attempt_id"])
        if (
            self._path(packet, "custody_stage_path")
            != expected["splitvault_output_root"].parent / f".h1_splitvault_002.attempt-{attempt}"
            or self._path(packet, "design_stage_path")
            != expected["design_source_output_root"].parent / f".trendstack_006_design_h1.attempt-{attempt}"
            or self._path(packet, "attempt_evidence_root")
            != research / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-006_SOURCE_ATTEMPTS" / attempt
        ):
            raise ValueError

    def preflight(self, packet: VerifiedRunPacket) -> dict[str, object]:
        try:
            if self._require_clean_bootstrap and not _PRODUCTION_BOOTSTRAP_ELIGIBLE:
                raise ValueError
            self._validate_production_paths(packet)
            dependencies = _freeze_dependency_map()
            dependency_attestation, dependency_attestation_sha256 = _dependency_attestation(dependencies)
            verified_payloads: dict[str, bytes] = {}
            identities: dict[str, tuple[int, ...]] = {}
            for path_key, hash_key in _FILE_BINDINGS.items():
                path = self._path(packet, path_key)
                identity = _file_anchor(path)
                payload = _stable_file_read(path, identity)
                if _digest(payload) != packet[hash_key]:
                    raise ValueError
                identities[path_key] = identity
                verified_payloads[path_key] = payload
            runtime_payload = verified_payloads["supervisor_tool_path"]
            if _digest(runtime_payload) != packet["runtime_supervisor_sha256"]:
                raise ValueError
            review_base = _runtime_review_base(runtime_payload, packet.detached_sha256, testing=self.testing)
            if (
                review_base != packet["review_base_supervisor_sha256"]
                or review_base != packet["supervisor_review_base_sha256"]
            ):
                raise ValueError
            _verify_registry_rows(verified_payloads["registry_path"], packet)
            arm_manifest_identity = _file_anchor(self.arm_manifest_path)
            arm_manifest_payload = _stable_file_read(self.arm_manifest_path, arm_manifest_identity)
            arm_manifest = validate_arm_manifest_document(
                arm_manifest_payload,
                packet,
                runtime_payload,
                self._path(packet, "supervisor_tool_path"),
                self.packet_path,
            )
            selection = preflight_selection_manifest(
                verified_payloads["selection_manifest_path"],
                expected_count=int(packet["expected_design_dates"]),
                expected_date_set_sha256=FROZEN_DESIGN_DATE_SET_SHA256,
            )
            source = self._path(packet, "source_path")
            source_identity = _file_anchor(source)
            if source_identity[2] != packet["source_bytes"]:
                raise ValueError
            outputs = [
                self._path(packet, key)
                for key in (
                    "attempt_evidence_root", "custody_stage_path", "splitvault_output_root",
                    "design_stage_path", "design_source_output_root",
                )
            ]
            if len({os.path.normcase(str(path)) for path in outputs}) != len(outputs):
                raise ValueError
            custody_stage = self._path(packet, "custody_stage_path")
            custody_output = self._path(packet, "splitvault_output_root")
            design_stage = self._path(packet, "design_stage_path")
            design_output = self._path(packet, "design_source_output_root")
            attempt = str(packet["source_attempt_id"])
            if (
                custody_stage.parent != custody_output.parent
                or custody_stage.name != f".{custody_output.name}.attempt-{attempt}"
                or design_stage.parent != design_output.parent
                or design_stage.name != f".{design_output.name}.attempt-{attempt}"
            ):
                raise ValueError
            for path in outputs:
                if os.path.lexists(path):
                    raise ValueError
                _directory_chain(path)
            return {
                "verified_payloads": verified_payloads,
                "identities": identities,
                "source_identity": source_identity,
                "selection": selection,
                "source_reads": 0,
                "arm_manifest": arm_manifest,
                "arm_manifest_payload": arm_manifest_payload,
                "arm_manifest_identity": arm_manifest_identity,
                "dependencies": dependencies,
                "dependency_attestation": dependency_attestation,
                "dependency_attestation_sha256": dependency_attestation_sha256,
            }
        except Exception as exc:
            raise InvalidSupervisor(PUBLIC_ERROR) from exc

    def start(self, packet: VerifiedRunPacket, context: dict[str, object]) -> tuple[dict[str, object], str]:
        try:
            if context["source_reads"] != 0:
                raise ValueError
            for key, identity in context["identities"].items():
                if _file_anchor(self._path(packet, key)) != identity:
                    raise ValueError
            root = self._path(packet, "attempt_evidence_root")
            root.mkdir()
            _fsync_directory(root.parent)
            marker = {
                **packet.as_dict(),
                "arm_manifest_sha256": context["arm_manifest"]["arm_manifest_sha256"],
                "dependency_attestation_sha256": context["dependency_attestation_sha256"],
                "detached_packet_sha256": packet.detached_sha256,
                "verdict": "ATTEMPT_CONSUMED",
            }
            payload = canonical_json(marker) + b"\n"
            marker_path = root / "attempt_started.json"
            _exclusive_write(marker_path, payload)
            context["marker_path"] = marker_path
            context["marker_payload"] = payload
            return marker, _digest(payload)
        except Exception as exc:
            raise InvalidSupervisor(PUBLIC_ERROR) from exc

    def _clock_converter(self, payload: bytes):
        if self.testing_clock_converter is not None:
            return self.testing_clock_converter
        namespace: dict[str, object] = {"__name__": "_verified_hyp006_clock"}
        exec(compile(payload, str(self.packet_path), "exec"), namespace)
        converter = namespace.get("server_to_utc")
        if not callable(converter):
            raise ValueError
        return converter

    def _recheck_verified_tools(self, packet: VerifiedRunPacket, context: dict[str, object], *, armed: bool) -> None:
        keys = ("custodian_tool_path", "design_builder_tool_path", "validator_tool_path")
        if armed:
            keys = ("supervisor_tool_path",) + keys
        for key in keys:
            path = self._path(packet, key)
            if (
                _file_anchor(path) != context["identities"][key]
                or _digest(_stable_file_read(path, context["identities"][key]))
                != packet[_FILE_BINDINGS[key]]
            ):
                raise ValueError

    def _verified_private_tools(self, packet: VerifiedRunPacket, context: dict[str, object]):
        self._recheck_verified_tools(packet, context, armed=True)
        _recheck_dependency_attestation(context)
        payloads = context["verified_payloads"]
        return (
            _execute_verified_module(
                payloads["custodian_tool_path"],
                self._path(packet, "custodian_tool_path"),
                packet["custodian_tool_sha256"],
                context["dependencies"],
            ),
            _execute_verified_module(
                payloads["design_builder_tool_path"],
                self._path(packet, "design_builder_tool_path"),
                packet["design_builder_tool_sha256"],
                context["dependencies"],
            ),
            _execute_verified_module(
                payloads["validator_tool_path"],
                self._path(packet, "validator_tool_path"),
                packet["validator_tool_sha256"],
                context["dependencies"],
            ),
        )

    def pipeline(self, packet: VerifiedRunPacket, marker: dict[str, object], context: dict[str, object]) -> dict[str, object]:
        try:
            custodian, builder, validator = self._verified_private_tools(packet, context)

            source = self._path(packet, "source_path")

            def source_reader() -> bytes:
                context["source_reads"] += 1
                if context["source_reads"] != 1:
                    raise ValueError
                return _stable_file_read(source, context["source_identity"])

            base_marker_keys = {"verdict", "source_attempt_id", "registry_row_index", "registry_row_sha256", "source_sha256"}
            marker_bindings = tuple(sorted((key, value) for key, value in marker.items() if key not in base_marker_keys))
            authority = custodian.CustodyAuthority(
                source_sha256=packet["source_sha256"],
                source_bytes=packet["source_bytes"],
                source_footer_length=packet["source_footer_length"],
                source_footer_start=packet["source_footer_start"],
                source_footer_sha256=packet["source_footer_sha256"],
                source_manifest_sha256=packet["source_manifest_sha256"],
                clock_sha256=packet["clock_sha256"],
                collection_plan_v1_sha256=packet["collection_plan_v1_sha256"],
                collection_plan_v2_sha256=packet["collection_plan_v2_sha256"],
                registry_row_index=packet["registry_row_index"],
                registry_row_sha256=packet["registry_row_sha256"],
                source_attempt_id=packet["source_attempt_id"],
                expected_source_rows=packet["source_rows"],
                expected_source_row_groups=packet["source_row_groups"],
                marker_bindings=marker_bindings,
                clock_converter=self._clock_converter(context["verified_payloads"]["clock_path"]),
            )
            _custody_receipt, custody_capability = custodian.run_custody(
                source_reader,
                source_manifest_payload=context["verified_payloads"]["source_manifest_path"],
                clock_payload=context["verified_payloads"]["clock_path"],
                output_root=self._path(packet, "splitvault_output_root"),
                stage_root=self._path(packet, "custody_stage_path"),
                authority=authority,
                marker=marker,
            )
            if context["source_reads"] != packet["expected_raw_opens"]:
                raise ValueError
            narrowed = prepare_narrow_design_capability(
                custody_capability,
                context["selection"],
                expected_source_attempt_id=packet["source_attempt_id"],
            )
            child = materialize_child_capability(narrowed, source_attempt_id=packet["source_attempt_id"])
            actual_extra_design_dates = child.actual_extra_design_dates()
            context["actual_extra_design_dates"] = actual_extra_design_dates
            mapping_sha = _digest(child.selection_mapping_bytes())
            contract = builder.DesignSourceContract(
                builder_tool_sha256=packet["design_builder_tool_sha256"],
                custodian_tool_sha256=packet["custodian_tool_sha256"],
                validator_tool_sha256=packet["validator_tool_sha256"],
                custodian_test_sha256=packet["custodian_test_sha256"],
                supervisor_test_sha256=packet["supervisor_test_sha256"],
                builder_test_sha256=packet["design_builder_test_sha256"],
                validator_test_sha256=packet["validator_test_sha256"],
                collection_plan_v1_sha256=packet["collection_plan_v1_sha256"],
                collection_plan_v2_sha256=packet["collection_plan_v2_sha256"],
                probe_plan_v1_sha256=packet["probe_plan_v1_sha256"],
                probe_plan_v2_sha256=packet["probe_plan_v2_sha256"],
                registry_sha256=packet["registry_sha256"],
                registry_row_index=packet["registry_row_index"],
                registry_row_sha256=packet["registry_row_sha256"],
                packet_sha256=packet.detached_sha256,
                source_attempt_id=packet["source_attempt_id"],
                design_stage_path=str(self._path(packet, "design_stage_path")),
                stage_role="DESIGN",
                supervisor_review_base_sha256=packet["supervisor_review_base_sha256"],
                custodian_public_receipt_sha256=_digest(child.public_receipt_bytes()),
                custodian_public_manifest_sha256=_digest(child.public_manifest_bytes()),
                selection_manifest_sha256=packet["selection_manifest_sha256"],
                selection_mapping_sha256=mapping_sha,
            )
            if self.testing:
                builder_shape = builder.BuildShape(
                    self.testing_build_shape.design_date_set_sha256,
                    self.testing_build_shape.expected_design_dates,
                    self.testing_build_shape.expected_rows_per_day,
                    self.testing_build_shape.expected_total_rows,
                    self.testing_build_shape.first_design_date,
                    self.testing_build_shape.last_design_date,
                )
                build_result = builder.build_design_source_for_testing(
                    child, self._path(packet, "design_source_output_root"), contract,
                    shape=builder_shape,
                )
            else:
                build_result = builder.build_design_source(child, self._path(packet, "design_source_output_root"), contract)
            validation_authority = validator.ValidationAuthority(
                validator_tool_sha256=contract.validator_tool_sha256,
                validator_test_sha256=contract.validator_test_sha256,
                builder_tool_sha256=contract.builder_tool_sha256,
                builder_test_sha256=contract.builder_test_sha256,
                custodian_tool_sha256=contract.custodian_tool_sha256,
                custodian_test_sha256=contract.custodian_test_sha256,
                supervisor_test_sha256=contract.supervisor_test_sha256,
                collection_plan_v1_sha256=contract.collection_plan_v1_sha256,
                collection_plan_v2_sha256=contract.collection_plan_v2_sha256,
                probe_plan_v1_sha256=contract.probe_plan_v1_sha256,
                probe_plan_v2_sha256=contract.probe_plan_v2_sha256,
                registry_sha256=contract.registry_sha256,
                registry_row_index=contract.registry_row_index,
                registry_row_sha256=contract.registry_row_sha256,
                packet_sha256=contract.packet_sha256,
                source_attempt_id=contract.source_attempt_id,
                stage_path=contract.design_stage_path,
                stage_role=contract.stage_role,
                supervisor_review_base_sha256=contract.supervisor_review_base_sha256,
                custodian_public_receipt_sha256=contract.custodian_public_receipt_sha256,
                custodian_public_manifest_sha256=contract.custodian_public_manifest_sha256,
                selection_manifest_sha256=contract.selection_manifest_sha256,
                selection_mapping_sha256=contract.selection_mapping_sha256,
                expected_receipt_sha256=build_result["pending_receipt_sha256"],
                expected_tree_sha256=build_result["pending_tree_sha256"],
            )
            if self.testing:
                validation_shape = validator.ValidationShape(
                    self.testing_validation_shape.design_date_set_sha256,
                    self.testing_validation_shape.expected_design_dates,
                    self.testing_validation_shape.expected_rows_per_day,
                    self.testing_validation_shape.expected_total_rows,
                    self.testing_validation_shape.first_design_date,
                    self.testing_validation_shape.last_design_date,
                )
                validation_result = validator.validate_design_source_for_testing(
                    self._path(packet, "design_source_output_root"), validation_authority,
                    shape=validation_shape,
                )
            else:
                validation_result = validator.validate_design_source(
                    self._path(packet, "design_source_output_root"), validation_authority
                )
            if type(validation_result) is not dict:
                raise ValueError
            return {
                **validation_result,
                "actual_extra_design_dates": actual_extra_design_dates,
                "dependency_attestation_sha256": context["dependency_attestation_sha256"],
            }
        except Exception as exc:
            if isinstance(exc, InvalidSupervisor) and str(exc) == PUBLIC_ERROR:
                raise
            raise InvalidSupervisor(PUBLIC_ERROR) from exc

    def disarm(self, packet: VerifiedRunPacket, context: dict[str, object]) -> dict[str, object]:
        try:
            supervisor_path = self._path(packet, "supervisor_tool_path")
            if (
                _file_anchor(supervisor_path) != context["identities"]["supervisor_tool_path"]
                or _digest(_stable_file_read(supervisor_path, context["identities"]["supervisor_tool_path"]))
                != packet["runtime_supervisor_sha256"]
            ):
                raise ValueError
            result = _self_disarm_runtime(packet.detached_sha256, supervisor_path)
            if (
                result["disarmed_supervisor_sha256"]
                != context["arm_manifest"]["disarmed_supervisor_sha256"]
                or result["disarmed_supervisor_sha256"] != packet["supervisor_review_base_sha256"]
            ):
                raise ValueError
            return {
                **result,
                "arm_manifest_sha256": context["arm_manifest"]["arm_manifest_sha256"],
            }
        except Exception as exc:
            raise InvalidSupervisor(PUBLIC_ERROR) from exc

    def terminal(
        self,
        packet: VerifiedRunPacket,
        marker_sha256: str,
        verdict: str,
        evidence: dict[str, object],
        context: dict[str, object],
    ) -> str:
        try:
            if (
                _file_anchor(self.arm_manifest_path) != context["arm_manifest_identity"]
                or _stable_file_read(self.arm_manifest_path, context["arm_manifest_identity"])
                != context["arm_manifest_payload"]
            ):
                raise ValueError
            if verdict == _READY:
                _recheck_dependency_attestation(context)
                self._recheck_verified_tools(packet, context, armed=False)
                runtime = _stable_file_read(self._path(packet, "supervisor_tool_path"))
                if (
                    _digest(runtime) != evidence.get("disarmed_supervisor_sha256")
                    or evidence.get("supervisor_sentinel_status") != "DISARMED_NONE_VERIFIED"
                    or evidence.get("arm_manifest_sha256") != context["arm_manifest"]["arm_manifest_sha256"]
                    or evidence.get("dependency_attestation_sha256")
                    != context["dependency_attestation_sha256"]
                    or type(evidence.get("actual_extra_design_dates")) is not int
                    or evidence.get("actual_extra_design_dates") != context.get("actual_extra_design_dates")
                    or evidence["actual_extra_design_dates"] < 0
                ):
                    raise ValueError
            marker_path = context["marker_path"]
            marker_payload = context["marker_payload"]
            marker_document = json.loads(marker_payload)
            if (
                _stable_file_read(marker_path) != marker_payload
                or _digest(marker_payload) != marker_sha256
                or marker_document.get("dependency_attestation_sha256")
                != context["dependency_attestation_sha256"]
            ):
                raise ValueError
            terminal = {
                **evidence,
                "attempt_started_sha256": marker_sha256,
                "dependency_attestation_sha256": context["dependency_attestation_sha256"],
                "detached_packet_sha256": packet.detached_sha256,
                "schema_version": "trendstack_006_source_attempt_terminal.v1",
                "source_attempt_id": packet["source_attempt_id"],
                "verdict": verdict,
            }
            payload = canonical_json(terminal) + b"\n"
            path = self._path(packet, "attempt_evidence_root") / "attempt_terminal.json"
            _exclusive_write(path, payload)
            if _stable_file_read(marker_path) != marker_payload:
                raise ValueError
            return _digest(payload)
        except Exception as exc:
            raise InvalidSupervisor(PUBLIC_ERROR) from exc


def supervise(packet_path: Path | str) -> dict[str, object]:
    """Only production entrypoint; detached SHA authority comes from the sentinel."""

    global REVIEWED_RUN_PACKET_SHA256
    reviewed_authority = REVIEWED_RUN_PACKET_SHA256
    result: dict[str, object] | None = None
    primary_error: Exception | None = None
    try:
        if not _PRODUCTION_BOOTSTRAP_ELIGIBLE:
            raise ValueError
        if REVIEWED_RUN_PACKET_SHA256 is None or not _valid_sha(REVIEWED_RUN_PACKET_SHA256):
            raise ValueError
        path = Path(packet_path).absolute()
        if path.name != "HYP-TRENDSTACK-EURUSD-H1-006_SOURCE_RUN_PACKET.json":
            raise ValueError
        payload = _stable_file_read(path)
        verified = validate_full_packet_document(payload, REVIEWED_RUN_PACKET_SHA256)
        result = _run_one_shot_lifecycle(
            verified,
            _InProcessOperations(path, _require_clean_bootstrap=True),
        )
    except Exception as exc:
        primary_error = exc
    finally:
        REVIEWED_RUN_PACKET_SHA256 = None
    final_disarm_error: Exception | None = None
    if reviewed_authority is not None and _valid_sha(reviewed_authority):
        try:
            _self_disarm_runtime(reviewed_authority)
        except Exception as exc:
            final_disarm_error = exc
    if primary_error is not None:
        message = (
            str(primary_error)
            if isinstance(primary_error, InvalidSupervisor) and str(primary_error).startswith(PUBLIC_ERROR)
            else PUBLIC_ERROR
        )
        if final_disarm_error is not None:
            message += ";FINAL_DISARM_FAILED"
        raise InvalidSupervisor(message) from primary_error
    if final_disarm_error is not None:
        raise InvalidSupervisor(PUBLIC_ERROR + ":FINAL_DISARM_FAILED") from final_disarm_error
    if result is None:
        raise InvalidSupervisor(PUBLIC_ERROR)
    return result
