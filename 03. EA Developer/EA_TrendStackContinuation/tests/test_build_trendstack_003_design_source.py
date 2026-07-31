from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "research" / "build_trendstack_003_design_source.py"
CUSTODIAN_PATH = ROOT / "research" / "splitvault_001_custodian.py"
SOURCE_ATTEMPT_ID = "HYP003-SOURCE-ATTEMPT-0123456789ABCDEF"
SUPERVISOR_REVIEW_BASE_SHA256 = "A" * 64


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def parent_row(tool, day: str, split: str, index: int) -> dict[str, object]:
    direction = 1 if index % 2 == 0 else -1
    return {
        "challenger_stack_direction": direction,
        "challenger_stack_eligible": True,
        "control_m252_only_direction": direction,
        "control_m252_only_eligible": True,
        "control_m6_only_direction": direction,
        "control_m6_only_eligible": True,
        "exclusion_reason": None,
        "feature_complete": True,
        "hypothesis_id": tool.PARENT_HYPOTHESIS_ID,
        "max_source_time_utc": f"{day}T11:00:00",
        "negative_disagree_direction": None,
        "negative_disagree_eligible": False,
        "next_prefix_sha256": f"{index + 10:064X}",
        "opportunity_id": day,
        "packet_file_sha256": f"{index + 20:064X}",
        "packet_path": f"{'DESIGN' if split == 'DESIGN' else 'VALIDATION_FEATURE_ONLY'}/{day}.json",
        "packet_payload_sha256": f"{index + 30:064X}",
        "prior_prefix_sha256": f"{index + 40:064X}",
        "row_index": index,
        "row_payload_sha256": f"{index + 50:064X}",
        "schema_version": tool.PARENT_LEDGER_SCHEMA,
        "source_chain_sha256": f"{index + 60:064X}",
        "split": split,
    }


def write_mixed_projection_fixture(tmp_path: Path, design_dates: list[str]):
    tool = load(TOOL_PATH, "trendstack_003_builder_test")
    rows = [parent_row(tool, day, "DESIGN", index) for index, day in enumerate(design_dates)]
    rows.append(parent_row(tool, "2021-01-04", "VALIDATION_FEATURE_ONLY", len(rows)))
    ledger = tmp_path / "mixed.jsonl"
    ledger.write_bytes(b"".join(canonical(item) + b"\n" for item in rows))
    receipt = tmp_path / "parent_receipt.json"
    receipt.write_bytes(b'{"stage0_verdict":"PASS"}\n')
    date_hash = tool.sha256_bytes(tool.canonical_design_date_set_bytes(design_dates))
    authority = tool.ProjectionAuthority(
        parent_ledger_sha256=sha256(ledger.read_bytes()),
        parent_receipt_sha256=sha256(receipt.read_bytes()),
        design_date_set_sha256=date_hash,
        expected_design_dates=len(design_dates),
        projector_tool_sha256=sha256(TOOL_PATH.read_bytes()),
    )
    capability = tool.project_design_stage0(ledger, receipt, authority)
    return tool, rows, capability, date_hash


def source_schema() -> pa.Schema:
    return pa.schema(
        [
            ("time_server", pa.timestamp("ns")),
            ("time_utc", pa.timestamp("ns")),
            ("utc_offset_h", pa.int8()),
            ("open", pa.float64()),
            ("high", pa.float64()),
            ("low", pa.float64()),
            ("close", pa.float64()),
            ("tick_volume", pa.uint64()),
            ("spread", pa.int32()),
            ("real_volume", pa.uint64()),
        ]
    )


def minute_rows(day: str, *, missing: set[int] = frozenset(), duplicate: int | None = None, bad_last: bool = False):
    start = datetime.fromisoformat(day + "T12:01:00")
    rows = []
    for index in range(360):
        if index in missing:
            continue
        stamp = start + timedelta(minutes=index)
        if bad_last and index == 359:
            stamp += timedelta(minutes=1)
        price = 1.1 + index * 0.000001
        rows.append(
            {
                "time_server": stamp,
                "time_utc": stamp,
                "utc_offset_h": 0,
                "open": price,
                "high": price + 0.0001,
                "low": price - 0.0001,
                "close": price,
                "tick_volume": 1,
                "spread": 7,
                "real_volume": 0,
            }
        )
    if duplicate is not None:
        rows.append(dict(rows[duplicate]))
        rows.sort(key=lambda item: item["time_utc"])
    return rows


class SyntheticDesignCapability:
    def __init__(self, day_payloads: dict[str, bytes]):
        self._payloads = day_payloads

    def design_dates(self):
        return tuple(sorted(self._payloads))

    def read_design_day(self, day: str):
        if day not in self._payloads:
            raise RuntimeError("denied")
        return self._payloads[day]

    def public_receipt_bytes(self):
        return canonical(
            {
                "source_attempt_id": SOURCE_ATTEMPT_ID,
                "stage_role": "CUSTODY",
                "supervisor_review_base_sha256": SUPERVISOR_REVIEW_BASE_SHA256,
                "verdict": "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY",
            }
        ) + b"\n"

    def public_manifest_bytes(self):
        return b"".join(canonical({"date": day, "sha256": sha256(payload)}) + b"\n" for day, payload in sorted(self._payloads.items()))


def payload_for(rows: list[dict[str, object]], tmp_path: Path, name: str) -> bytes:
    path = tmp_path / name
    pq.write_table(pa.Table.from_pylist(rows, schema=source_schema()), path, row_group_size=max(1, len(rows)))
    return path.read_bytes()


def contract(tool, dates: list[str], date_hash: str, stage: Path):
    return tool.DesignSourceContract(
        design_date_set_sha256=date_hash,
        expected_design_dates=len(dates),
        expected_rows_per_day=360,
        expected_total_rows=len(dates) * 360,
        first_design_date=dates[0],
        last_design_date=dates[-1],
        builder_tool_sha256=sha256(TOOL_PATH.read_bytes()),
        source_attempt_id=SOURCE_ATTEMPT_ID,
        design_stage_path=str(stage.resolve()),
        stage_role="DESIGN",
        supervisor_review_base_sha256=SUPERVISOR_REVIEW_BASE_SHA256,
    )


def run_bound_build(tool, capability, projection, output: Path, dates: list[str], date_hash: str, lifecycle_hook=None):
    stage = output.parent / ("." + output.name + ".attempt-" + SOURCE_ATTEMPT_ID)
    stage.mkdir()
    identity = tool._directory_identity(stage)
    return tool.build_design_source(
        capability,
        projection,
        output,
        contract(tool, dates, date_hash, stage),
        lifecycle_hook=lifecycle_hook,
        attempt_root=stage,
        expected_attempt_identity=identity,
    )


def test_projection_is_byte_preserving_design_only_and_leaks_no_validation_identity(tmp_path: Path) -> None:
    tool, rows, capability, _ = write_mixed_projection_fixture(tmp_path, ["2016-01-04", "2016-01-05"])
    wrappers = [json.loads(line) for line in capability.projection_bytes().splitlines()]
    assert len(wrappers) == 2
    decoded = [tool.decode_projected_parent_row(item) for item in wrappers]
    assert decoded == rows[:2]
    public = capability.projection_bytes() + capability.receipt_bytes()
    assert b"2021-01-04" not in public and b"VALIDATION" not in public


def test_exact_design_source_build_writes_360_row_daily_shards_and_false_outcomes(tmp_path: Path) -> None:
    dates = ["2016-01-04", "2016-01-05"]
    tool, _, projection, date_hash = write_mixed_projection_fixture(tmp_path, dates)
    payloads = {day: payload_for(minute_rows(day), tmp_path, day + ".parquet") for day in dates}
    receipt = run_bound_build(tool, SyntheticDesignCapability(payloads), projection, tmp_path / "output", dates, date_hash)
    assert receipt["verdict"] == "PENDING_INDEPENDENT_VALIDATION"
    assert receipt["request_count"] == 2 and receipt["m1_rows"] == 720
    assert receipt["economics_opened"] is False and receipt["performance_trials_executed"] == 0
    assert receipt["research_validation_opened"] is False and receipt["research_holdout_opened"] is False
    assert receipt["source_attempt_id"] == SOURCE_ATTEMPT_ID
    assert receipt["stage_path"].endswith(".output.attempt-" + SOURCE_ATTEMPT_ID)
    assert receipt["stage_role"] == "DESIGN"
    assert receipt["supervisor_review_base_sha256"] == SUPERVISOR_REVIEW_BASE_SHA256
    for key in (
        "request_receipt_sha256",
        "projection_receipt_sha256",
        "reconciliation_sha256",
        "m1_manifest_sha256",
        "trace_sha256",
    ):
        assert len(receipt[key]) == 64
    for day in dates:
        shard = tmp_path / "output" / "raw_m1" / "DESIGN" / day / "1201_1800.parquet"
        assert pq.ParquetFile(shard).metadata.num_rows == 360
        assert pq.ParquetFile(shard).metadata.num_row_groups == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_attempt_id", "HYP003-SOURCE-ATTEMPT-FEDCBA9876543210"),
        ("design_stage_path", "relative-stage"),
        ("stage_role", "CUSTODY"),
        ("supervisor_review_base_sha256", "F" * 64),
    ],
)
def test_design_contract_rejects_mismatched_attempt_provenance(tmp_path: Path, field: str, value: object) -> None:
    day = "2016-01-04"
    tool, _, projection, date_hash = write_mixed_projection_fixture(tmp_path, [day])
    output = tmp_path / "output"
    stage = output.parent / ("." + output.name + ".attempt-" + SOURCE_ATTEMPT_ID)
    stage.mkdir()
    authority = contract(tool, [day], date_hash, stage)
    setattr(authority, field, value)
    payload = payload_for(minute_rows(day), tmp_path, "day.parquet")
    with pytest.raises(tool.InvalidDesignSource, match="^INVALID_DESIGN_SOURCE$"):
        tool.build_design_source(
            SyntheticDesignCapability({day: payload}),
            projection,
            output,
            authority,
            attempt_root=stage,
            expected_attempt_identity=tool._directory_identity(stage),
        )


def test_precreated_design_stage_same_path_recreation_fails_before_build(tmp_path: Path) -> None:
    day = "2016-01-04"
    tool, _, projection, date_hash = write_mixed_projection_fixture(tmp_path, [day])
    output = tmp_path / "output"
    stage = output.parent / ("." + output.name + ".attempt-" + SOURCE_ATTEMPT_ID)
    stage.mkdir()
    identity = tool._directory_identity(stage)
    stage.rename(stage.with_name(stage.name + ".old"))
    stage.mkdir()
    payload = payload_for(minute_rows(day), tmp_path, "day.parquet")
    with pytest.raises(tool.InvalidDesignSource, match="^INVALID_DESIGN_SOURCE$"):
        tool.build_design_source(
            SyntheticDesignCapability({day: payload}),
            projection,
            output,
            contract(tool, [day], date_hash, stage),
            attempt_root=stage,
            expected_attempt_identity=identity,
        )
    assert not output.exists()


def test_design_stage_move_recreate_before_publish_never_publishes_replacement(tmp_path: Path) -> None:
    day = "2016-01-04"
    tool, _, projection, date_hash = write_mixed_projection_fixture(tmp_path, [day])
    output = tmp_path / "output"
    payload = payload_for(minute_rows(day), tmp_path, "day.parquet")

    def replace_stage(event: str) -> None:
        if event != "before_publish":
            return
        stage = output.parent / ("." + output.name + ".attempt-" + SOURCE_ATTEMPT_ID)
        stage.rename(stage.with_name(stage.name + ".old"))
        stage.mkdir()

    with pytest.raises(tool.InvalidDesignSource, match="^INVALID_DESIGN_SOURCE$"):
        run_bound_build(
            tool,
            SyntheticDesignCapability({day: payload}),
            projection,
            output,
            [day],
            date_hash,
            replace_stage,
        )
    assert not output.exists()


@pytest.mark.parametrize("attack", ["gap", "duplicate", "outside"])
def test_gap_duplicate_and_outside_window_fail_before_receipt(tmp_path: Path, attack: str) -> None:
    day = "2016-03-11"
    tool, _, projection, date_hash = write_mixed_projection_fixture(tmp_path, [day])
    rows = minute_rows(
        day,
        missing={279, 280, 281, 282} if attack == "gap" else frozenset(),
        duplicate=10 if attack == "duplicate" else None,
        bad_last=attack == "outside",
    )
    payload = payload_for(rows, tmp_path, "day.parquet")
    output = tmp_path / "output"
    with pytest.raises(tool.InvalidDesignSource, match="^INVALID_DESIGN_SOURCE$"):
        run_bound_build(tool, SyntheticDesignCapability({day: payload}), projection, output, [day], date_hash)
    assert not (output / "design_m1_source_receipt.json").exists()


def test_mixed_or_tampered_projection_never_opens_vault(tmp_path: Path) -> None:
    dates = ["2016-01-04"]
    tool, _, projection, date_hash = write_mixed_projection_fixture(tmp_path, dates)
    raw = projection.projection_bytes().replace(b'"split":"DESIGN"', b'"split":"VALIDATION_FEATURE_ONLY"')
    tampered = tool.ProjectionCapability.from_bytes_for_testing(raw, projection.receipt_bytes())
    touched = {"days": 0}

    class ForbiddenCapability(SyntheticDesignCapability):
        def read_design_day(self, day):
            touched["days"] += 1
            raise AssertionError("vault must remain unopened")

    with pytest.raises(tool.InvalidDesignSource, match="^INVALID_DESIGN_SOURCE$"):
        run_bound_build(tool, ForbiddenCapability({}), tampered, tmp_path / "output", dates, date_hash)
    assert touched["days"] == 0


def test_wrong_interior_date_set_is_rejected_before_vault_access(tmp_path: Path) -> None:
    tool, _, projection, _ = write_mixed_projection_fixture(tmp_path, ["2016-01-04", "2016-01-06"])
    correct_hash = tool.sha256_bytes(tool.canonical_design_date_set_bytes(["2016-01-04", "2016-01-05"]))
    touched = {"days": 0}

    class ForbiddenCapability(SyntheticDesignCapability):
        def read_design_day(self, day):
            touched["days"] += 1
            raise AssertionError("vault must remain unopened")

    with pytest.raises(tool.InvalidDesignSource, match="^INVALID_DESIGN_SOURCE$"):
        run_bound_build(tool, ForbiddenCapability({}), projection, tmp_path / "output", ["2016-01-04", "2016-01-05"], correct_hash)
    assert touched["days"] == 0


def test_output_collision_and_crash_are_quarantined_without_success(tmp_path: Path) -> None:
    day = "2016-01-04"
    tool, _, projection, date_hash = write_mixed_projection_fixture(tmp_path, [day])
    payload = payload_for(minute_rows(day), tmp_path, "day.parquet")
    cap = SyntheticDesignCapability({day: payload})
    collision = tmp_path / "collision"
    collision.mkdir()
    with pytest.raises(tool.InvalidDesignSource, match="^INVALID_DESIGN_SOURCE$"):
        run_bound_build(tool, cap, projection, collision, [day], date_hash)

    def crash(event: str) -> None:
        if event == "before_publish":
            raise RuntimeError("crash")

    failed = tmp_path / "failed"
    with pytest.raises(tool.InvalidDesignSource, match="^INVALID_DESIGN_SOURCE$"):
        run_bound_build(tool, cap, projection, failed, [day], date_hash, lifecycle_hook=crash)
    assert len(list(tmp_path.glob(".failed.attempt-*"))) == 1
    assert not (failed / "design_m1_source_receipt.json").exists()


def test_late_output_collision_preserves_attempt_outside_attacker_root(tmp_path: Path) -> None:
    day = "2016-01-04"
    tool, _, projection, date_hash = write_mixed_projection_fixture(tmp_path, [day])
    payload = payload_for(minute_rows(day), tmp_path, "day.parquet")
    output = tmp_path / "late"

    def collide(event: str) -> None:
        if event == "before_publish":
            output.mkdir()
            (output / "attacker.txt").write_text("collision", encoding="utf-8")

    with pytest.raises(tool.InvalidDesignSource, match="^INVALID_DESIGN_SOURCE$"):
        run_bound_build(tool, SyntheticDesignCapability({day: payload}), projection, output, [day], date_hash, collide)
    assert not (output / "design_m1_source_receipt.json").exists()
    attempts = list(tmp_path.glob(".late.attempt-*"))
    assert len(attempts) == 1 and (attempts[0] / "design_m1_source_receipt.json").exists()


def test_late_output_reparse_preserves_attempt_outside_target(tmp_path: Path) -> None:
    day = "2016-01-04"
    tool, _, projection, date_hash = write_mixed_projection_fixture(tmp_path, [day])
    payload = payload_for(minute_rows(day), tmp_path, "day.parquet")
    output = tmp_path / "late_link"
    attacker = tmp_path / "attacker_target"
    attacker.mkdir()
    probe = tmp_path / "link_probe"
    try:
        probe.symlink_to(attacker, target_is_directory=True)
        probe.unlink()
    except OSError:
        pytest.skip("directory symlink creation unavailable")

    def link(event: str) -> None:
        if event == "before_publish":
            output.symlink_to(attacker, target_is_directory=True)

    with pytest.raises(tool.InvalidDesignSource, match="^INVALID_DESIGN_SOURCE$"):
        run_bound_build(tool, SyntheticDesignCapability({day: payload}), projection, output, [day], date_hash, link)
    assert not (attacker / "design_m1_source_receipt.json").exists()
    assert len(list(tmp_path.glob(".late_link.attempt-*"))) == 1


def test_builder_source_has_no_raw_monolith_parent_quarantine_network_or_economics_surface() -> None:
    source = TOOL_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imports.intersection({"socket", "requests", "urllib", "subprocess", "MetaTrader5"})
    lowered = source.lower()
    for forbidden in ("eurusd_m1_2015_now", "trendstack_002_design_m1", "failure_manifest", "profit_factor", "net_r", "mfe", "mae"):
        assert forbidden not in lowered
