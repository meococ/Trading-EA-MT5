from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "research" / "splitvault_002_custodian.py"
SOURCE_ATTEMPT_ID = "HYP004-SOURCE-ATTEMPT-0123456789ABCDEF"


def load_tool():
    spec = importlib.util.spec_from_file_location("splitvault_002_custodian_test", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


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


def row(when: str, sentinel: float) -> dict[str, object]:
    stamp = datetime.fromisoformat(when)
    return {
        "time_server": stamp,
        "time_utc": stamp,
        "utc_offset_h": 0,
        "open": sentinel,
        "high": sentinel + 0.0002,
        "low": sentinel - 0.0002,
        "close": sentinel + 0.0001,
        "tick_volume": 10,
        "spread": 7,
        "real_volume": 0,
    }


def write_fixture(tmp_path: Path, rows: list[dict[str, object]] | None = None):
    tool = load_tool()
    source = tmp_path / "source.parquet"
    if rows is None:
        rows = [
            row("2015-12-31T23:59:00", 1.01),
            row("2016-01-04T12:01:00", 1.11),
            row("2016-01-04T12:02:00", 1.12),
            row("2021-01-04T12:01:00", 9.91),
            row("2023-01-03T12:01:00", 8.81),
        ]
    pq.write_table(pa.Table.from_pylist(rows, schema=source_schema()), source, row_group_size=2)
    source_payload = source.read_bytes()
    footer_length, footer_start, footer_sha256 = tool._footer_contract(source_payload)
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(b'{"schema_version":"synthetic.v1"}\n')
    clock = tmp_path / "clock.py"
    clock.write_text("def server_to_utc(value):\n    return value\n", encoding="utf-8")
    plan = tmp_path / "plan.md"
    plan.write_bytes(b"synthetic frozen collection plan\n")
    authority = tool.CustodyAuthority(
        collection_plan_sha256=sha256(plan.read_bytes()),
        source_sha256=sha256(source_payload),
        source_bytes=source.stat().st_size,
        source_manifest_sha256=sha256(manifest.read_bytes()),
        source_footer_length=footer_length,
        source_footer_start=footer_start,
        source_footer_sha256=footer_sha256,
        clock_sha256=sha256(clock.read_bytes()),
        custodian_tool_sha256=sha256(TOOL_PATH.read_bytes()),
        supervisor_review_base_sha256="A" * 64,
        source_attempt_id=SOURCE_ATTEMPT_ID,
        custody_stage_path=str((tmp_path / ".unused").resolve()),
        custody_stage_identity=(0, 0, 0, 0, 0, 0),
        stage_role="CUSTODY",
        source_identity=tool._identity(source),
    )
    return tool, source, manifest, clock, plan, authority


def run_custody(tool, source, manifest, plan, clock, output: Path, authority, lifecycle_hook=None):
    stage = output.parent / ("." + output.name + ".attempt-" + SOURCE_ATTEMPT_ID)
    stage.mkdir()
    bound = tool.CustodyAuthority(
        **{
            **authority.__dict__,
            "custody_stage_path": str(stage.resolve()),
            "custody_stage_identity": tool._directory_identity(stage),
        }
    )
    return tool.run_custody(
        source,
        manifest,
        plan,
        clock,
        output,
        bound,
        lifecycle_hook=lifecycle_hook,
    )


def test_calendar_only_split_is_exact_once_and_public_surface_is_design_only(tmp_path: Path) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
    output = tmp_path / "vault"
    receipt, capability = run_custody(tool, source, manifest, plan, clock, output, authority)
    assert receipt["verdict"] == "COLLECTION_ENGINEERING_VALID_DESIGN_CAPABILITY_ONLY"
    assert receipt["exact_once_status"] == "PASS"
    assert receipt["custodian_full_corpus_decoded"] is True
    assert receipt["research_validation_opened"] is False
    assert receipt["research_holdout_opened"] is False
    assert receipt["source_attempt_id"] == SOURCE_ATTEMPT_ID
    assert receipt["source_footer_length"] == authority.source_footer_length
    assert receipt["source_footer_start"] == authority.source_footer_start
    assert receipt["source_footer_sha256"] == authority.source_footer_sha256
    assert receipt["stage_role"] == "CUSTODY"
    assert receipt["supervisor_review_base_sha256"] == "A" * 64
    assert set(capability.design_dates()) == {"2016-01-04"}
    public_text = (output / "public" / "design_receipt.json").read_text(encoding="utf-8")
    assert "VALIDATION" not in public_text and "HOLDOUT" not in public_text
    assert "9.91" not in public_text and "8.81" not in public_text
    assert "sealed" not in public_text.lower() and "quarantine" not in public_text.lower()
    private_rows = [json.loads(line) for line in (output / "private" / "custody_manifest.jsonl").read_text().splitlines()]
    private_receipt = (output / "private" / "custody_receipt.json").read_bytes()
    assert sha256(private_receipt) == receipt["private_custody_receipt_sha256"]
    private_receipt_value = json.loads(private_receipt)
    assert private_receipt_value["source_attempt_id"] == SOURCE_ATTEMPT_ID
    assert private_receipt_value["source_footer_length"] == authority.source_footer_length
    assert private_receipt_value["source_footer_start"] == authority.source_footer_start
    assert private_receipt_value["source_footer_sha256"] == authority.source_footer_sha256
    assert private_receipt_value["stage_role"] == "CUSTODY"
    assert private_receipt_value["supervisor_review_base_sha256"] == "A" * 64
    assert {item["split"] for item in private_rows} == {"PRE_DESIGN", "DESIGN", "VALIDATION", "HOLDOUT"}
    assert sum(item["rows"] for item in private_rows) == 5
    assert all(pq.ParquetFile(output / item["relative_path"]).metadata.num_row_groups == 1 for item in private_rows)


def test_supervisor_and_custodian_directory_identity_shapes_are_explicitly_compatible(tmp_path: Path) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
    stage = tmp_path / (".vault.attempt-" + SOURCE_ATTEMPT_ID)
    stage.mkdir()
    identity = tool._directory_identity(stage)
    assert len(identity) == 6
    bound = tool.CustodyAuthority(
        **{
            **authority.__dict__,
            "custody_stage_path": str(stage.resolve()),
            "custody_stage_identity": identity,
        }
    )
    tool._validate_authority(bound)


def test_corrected_footer_contract_hashes_exact_suffix_without_file_open(tmp_path: Path) -> None:
    tool = load_tool()
    metadata = b"synthetic-footer-metadata"
    payload = b"PAR1body" + metadata + len(metadata).to_bytes(4, "little") + b"PAR1"
    tool._stable_read = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("no file open in footer QC"))
    length, start, digest = tool._footer_contract(payload)
    assert length == len(metadata)
    assert start == len(payload) - 8 - len(metadata)
    assert digest == sha256(payload[start:])
    assert payload[start:].endswith(len(metadata).to_bytes(4, "little") + b"PAR1")


@pytest.mark.parametrize(
    "payload",
    [
        b"NOPEbody" + b"x" + (1).to_bytes(4, "little") + b"PAR1",
        b"PAR1body" + b"x" + (1).to_bytes(4, "little") + b"NOPE",
        b"PAR1" + (99).to_bytes(4, "little") + b"PAR1",
        b"PAR1PAR1",
    ],
)
def test_corrected_footer_contract_rejects_magic_and_bounds(payload: bytes) -> None:
    tool = load_tool()
    with pytest.raises(ValueError):
        tool._footer_contract(payload)


def test_capability_denies_parent_private_future_and_path_escape(tmp_path: Path) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
    _, capability = run_custody(tool, source, manifest, plan, clock, tmp_path / "vault", authority)
    assert not hasattr(capability, "root")
    for value in ("../sealed/HOLDOUT/2023-01-03/m1.parquet", "2021-01-04", "2023-01-03", "C:/escape"):
        with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
            capability.read_design_day(value)
    assert capability.read_design_day("2016-01-04").startswith(b"PAR1")


def test_capability_introspection_contains_only_public_design_bytes(tmp_path: Path) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
    output = tmp_path / "vault"
    _, capability = run_custody(tool, source, manifest, plan, clock, output, authority)
    representation = repr(capability)
    state = getattr(capability, "__dict__", {})
    forbidden = (str(output), str(source), "private", "sealed", "validation", "holdout", "quarantine")
    exposed = (representation + repr(state)).lower()
    assert not any(token.lower() in exposed for token in forbidden)
    for slot in getattr(type(capability), "__slots__", ()):
        value = getattr(capability, slot)
        assert not isinstance(value, Path)
        if isinstance(value, str):
            assert not Path(value).is_absolute()


@pytest.mark.parametrize("attack", ["hardlink", "symlink"])
def test_source_aliases_are_rejected_with_constant_public_error(tmp_path: Path, attack: str) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
    alias = tmp_path / "alias.parquet"
    if attack == "hardlink":
        os.link(source, alias)
    else:
        try:
            alias.symlink_to(source)
        except OSError:
            pytest.skip("symlink creation unavailable")
    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, alias, manifest, plan, clock, tmp_path / "vault", authority)
    assert not (tmp_path / "vault" / "public" / "design_receipt.json").exists()


def test_source_identity_replacement_is_detected_before_decode(tmp_path: Path) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)

    def swap(event: str) -> None:
        if event == "after_source_lstat":
            payload = source.read_bytes()
            source.unlink()
            source.write_bytes(payload)

    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, source, manifest, plan, clock, tmp_path / "vault", authority, lifecycle_hook=swap)


def test_raw_source_is_opened_exactly_once_and_marker_precedes_open_contract(tmp_path: Path) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
    stable_read = tool._stable_read
    source_opens = {"count": 0}
    events: list[str] = []

    def tracked(path: Path) -> bytes:
        if Path(path).absolute() == source.absolute():
            source_opens["count"] += 1
        return stable_read(path)

    tool._stable_read = tracked
    receipt, _ = run_custody(
        tool,
        source,
        manifest,
        plan,
        clock,
        tmp_path / "vault",
        authority,
        lifecycle_hook=events.append,
    )
    assert source_opens["count"] == 1
    assert events.index("before_source_open") < events.index("after_source_open") < events.index("after_source_decode")
    assert receipt["source_attempt_id"] == SOURCE_ATTEMPT_ID


@pytest.mark.parametrize(
    "attack_event",
    ["after_source_lstat", "before_source_open", "after_source_open", "after_source_decode", "before_publish"],
)
def test_custody_stage_same_path_move_recreate_fails_at_every_source_boundary(
    tmp_path: Path, attack_event: str
) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
    output = tmp_path / "vault"
    source_reads = {"count": 0}
    stable_read = tool._stable_read

    def tracked(path: Path) -> bytes:
        if Path(path).absolute() == source.absolute():
            source_reads["count"] += 1
        return stable_read(path)

    tool._stable_read = tracked

    def replace_stage(event: str) -> None:
        if event != attack_event:
            return
        stage = output.parent / ("." + output.name + ".attempt-" + SOURCE_ATTEMPT_ID)
        old = stage.with_name(stage.name + ".old")
        stage.rename(old)
        stage.mkdir()

    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, source, manifest, plan, clock, output, authority, lifecycle_hook=replace_stage)
    if attack_event in {"after_source_lstat", "before_source_open"}:
        assert source_reads["count"] == 0
    else:
        assert source_reads["count"] == 1
    assert not (output / "public" / "design_receipt.json").exists()


def test_create_new_collision_and_partial_crash_never_publish_success(tmp_path: Path) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
    collision = tmp_path / "collision"
    collision.mkdir()
    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, source, manifest, plan, clock, collision, authority)

    def crash(event: str) -> None:
        if event == "before_publish":
            raise RuntimeError("future sentinel must not escape")

    failed = tmp_path / "failed"
    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$") as error:
        run_custody(tool, source, manifest, plan, clock, failed, authority, lifecycle_hook=crash)
    assert str(error.value) == "INVALID_CUSTODY"
    assert not (failed / "public" / "design_receipt.json").exists()
    assert len(list(tmp_path.glob(".failed.attempt-*"))) == 1


def test_late_output_collision_never_receives_sealed_attempt(tmp_path: Path) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
    output = tmp_path / "late"

    def collide(event: str) -> None:
        if event == "before_publish":
            output.mkdir()
            (output / "attacker.txt").write_text("collision", encoding="utf-8")

    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, source, manifest, plan, clock, output, authority, lifecycle_hook=collide)
    assert (output / "attacker.txt").read_text(encoding="utf-8") == "collision"
    assert not (output / "public" / "design_receipt.json").exists()
    attempts = list(tmp_path.glob(".late.attempt-*"))
    assert len(attempts) == 1 and (attempts[0] / "public" / "design_receipt.json").exists()


def test_late_output_reparse_never_receives_sealed_attempt(tmp_path: Path) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
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

    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, source, manifest, plan, clock, output, authority, lifecycle_hook=link)
    assert not (attacker / "public" / "design_receipt.json").exists()
    assert len(list(tmp_path.glob(".late_link.attempt-*"))) == 1


def test_duplicate_bad_geometry_and_clock_drift_fail_closed(tmp_path: Path) -> None:
    cases = [
        [row("2016-01-04T12:01:00", 1.1), row("2016-01-04T12:01:00", 1.2)],
        [{**row("2016-01-04T12:01:00", 1.1), "low": 2.0}],
        [{**row("2016-01-04T12:01:00", 1.1), "time_server": datetime(2016, 1, 4, 12, 2)}],
    ]
    for index, rows in enumerate(cases):
        case = tmp_path / str(index)
        case.mkdir()
        tool, source, manifest, clock, plan, authority = write_fixture(case, rows)
        with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
            run_custody(tool, source, manifest, plan, clock, case / "vault", authority)


def test_source_is_mechanism_free_and_forbids_network_subprocess_and_terminal_imports() -> None:
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
    for forbidden in ("hypothesis_id", "stage0", "atr20", "profit_factor", "economics", "entry_price", "stop_loss"):
        assert forbidden not in lowered


def test_runtime_type_confusion_and_wrong_footer_are_rejected(tmp_path: Path) -> None:
    tool, source, manifest, clock, plan, authority = write_fixture(tmp_path)
    bad = authority.__class__(**{**authority.__dict__, "source_bytes": True})
    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, source, manifest, plan, clock, tmp_path / "a", bad)
    bad = authority.__class__(**{**authority.__dict__, "source_footer_sha256": "F" * 64})
    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, source, manifest, plan, clock, tmp_path / "b", bad)
    bad = authority.__class__(
        **{
            **authority.__dict__,
            "source_footer_sha256": "92E8403266EF971ED2F4C05523ECB6C10AE5B5723F0F7504E09694663A779727",
        }
    )
    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, source, manifest, plan, clock, tmp_path / "c", bad)
    bad = authority.__class__(**{**authority.__dict__, "source_footer_length": authority.source_footer_length + 1})
    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, source, manifest, plan, clock, tmp_path / "d", bad)
    bad = authority.__class__(**{**authority.__dict__, "source_footer_start": authority.source_footer_start - 1})
    with pytest.raises(tool.InvalidCustody, match="^INVALID_CUSTODY$"):
        run_custody(tool, source, manifest, plan, clock, tmp_path / "e", bad)
