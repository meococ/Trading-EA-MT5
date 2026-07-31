from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from types import SimpleNamespace
from datetime import date, timedelta
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "research" / "build_trendstack_002_design_request_plan.py"
CLOCK_PATH = ROOT.parents[1] / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
STAGE0_LEDGER_PATH = ROOT / "research" / "evidence" / "HYP-TRENDSTACK-EURUSD-H1-002_STAGE0" / "stage0_eligibility_ledger.jsonl"


def load_tool():
    spec = importlib.util.spec_from_file_location("build_trendstack_002_design_request_plan", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def frozen_dates() -> list[str]:
    result = [
        row["opportunity_id"]
        for row in (json.loads(line) for line in STAGE0_LEDGER_PATH.read_text(encoding="utf-8").splitlines())
        if row["split"] == "DESIGN"
    ]
    assert len(result) == 1297
    assert result[0] == "2016-01-04" and result[-1] == "2020-12-31"
    return result


def wrong_interior_dates() -> list[str]:
    accepted = frozen_dates()
    accepted_set = set(accepted)
    cursor = date(2016, 1, 4)
    end = date(2020, 12, 31)
    absent = []
    while cursor <= end:
        value = cursor.isoformat()
        if value not in accepted_set and value not in {accepted[0], accepted[-1]}:
            absent.append(value)
        cursor += timedelta(days=1)
    wrong = sorted((accepted_set - set(accepted[1:375])) | set(absent[:374]))
    assert len(wrong) == 1297 and wrong[0] == accepted[0] and wrong[-1] == accepted[-1]
    assert len(set(accepted) - set(wrong)) == len(set(wrong) - set(accepted)) == 374
    return wrong


def test_request_builder_pins_all_upstream_authority_hashes() -> None:
    tool = load_tool()
    assert tool.DESIGN_PLAN_SHA256 == "06AB038A59A9CEEF3E47734E892CCC04A98F43D6E82B9373A2C8680EBB6DA0A9"
    assert tool.SOURCE_PLAN_SHA256 == "3A6137ACEA37D1CC6BEE1700A561873AF8278AC524973054A82F92C70ED95EAF"
    assert tool.DESIGN_PLAN_V2_SHA256 == "3E31F1229C1BD4DBAB05D977E9F9FB5BB553EE65F097BB0B43B787AC9A1EC4C6"
    assert tool.DESIGN_DATE_SET_SHA256 == "4F30B5E09C8C21C3FCB63F4D5A016EB514D689710589077427464B92CD99A06A"
    assert tool.STAGE0_LEDGER_SHA256 == "3092A6FCFADE0DA23E4470C4BF3B1D7750190358CF6ED09A2BB942937A7CD3C7"
    assert tool.STAGE0_RECEIPT_SHA256 == "5AEA570736361EF22BF2F090A5C05EF2974F482B5CB34A1186F27D9B43AAF5CE"
    assert tool.PACKET_MANIFEST_SHA256 == "D199E105CF6B51E0516D4FB57FFCB0D9AF63A72D8084B04BE6D73892ED7EA9DA"
    assert tool.PACKET_RECEIPT_SHA256 == "DA113E80157FFF69DBD11BB478637DC2DA3B9FD829102763250DA55D07773320"
    assert tool.PACKET_SET_SHA256 == "22B0F111DCA293C0234C4C1D88F5A6E4CEABC7E7EE071466E310C9D0079F6E3E"


def test_exact_request_count_ids_windows_total_rows_and_separate_clock_roundtrips() -> None:
    tool = load_tool()
    clock = tool.load_clock(CLOCK_PATH)
    rows = tool.build_request_rows(frozen_dates(), clock)
    assert len(rows) == 1297
    assert rows[0]["request_id"] == "M1-DESIGN-0001-20160104"
    assert rows[-1]["request_id"] == "M1-DESIGN-1297-20201231"
    assert rows[0]["canonical_from_utc"] == "2016-01-04T12:01:00Z"
    assert rows[0]["canonical_to_inclusive_utc"] == "2016-01-04T18:00:00Z"
    assert all(row["expected_rows"] == 360 for row in rows)
    assert sum(row["expected_rows"] for row in rows) == 466_920
    assert all(row["from_clock_roundtrip_status"] == "PASS" for row in rows)
    assert all(row["to_clock_roundtrip_status"] == "PASS" for row in rows)
    assert tool.validate_request_rows(rows) is None
    payload = tool.canonical_design_date_set_bytes(frozen_dates())
    assert len(payload) == 14_301
    assert sha256(payload) == tool.DESIGN_DATE_SET_SHA256


def test_same_count_endpoints_but_374_added_and_missing_interior_dates_is_rejected() -> None:
    tool = load_tool()
    wrong_rows = tool.build_request_rows(wrong_interior_dates(), tool.load_clock(CLOCK_PATH))
    assert len(wrong_rows) == 1297
    assert wrong_rows[0]["opportunity_id"] == "2016-01-04"
    assert wrong_rows[-1]["opportunity_id"] == "2020-12-31"
    with pytest.raises(tool.InvalidEngineering, match="date-set"):
        tool.validate_request_rows(wrong_rows)


def test_request_schema_contains_no_decision_or_outcome_fields() -> None:
    tool = load_tool()
    clock = tool.load_clock(CLOCK_PATH)
    row = tool.build_request_rows(["2016-01-04"], clock)[0]
    assert set(row) == tool.REQUEST_FIELDS
    forbidden = ("price", "open", "high", "low", "close", "direction", "atr", "arm", "return", "outcome", "pnl", "metric")
    assert not any(any(token in key.lower() for token in forbidden) for key in row)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rows: rows + [{**rows[0], "request_id": "M1-DESIGN-0002-20160104"}],
        lambda rows: list(reversed(rows)),
        lambda rows: [{**rows[0], "opportunity_id": "2021-01-01"}],
        lambda rows: [{**rows[0], "request_id": "M1-DESIGN-0001-20230101", "opportunity_id": "2023-01-01"}],
    ],
    ids=["duplicate-date", "non-monotonic", "validation", "holdout"],
)
def test_request_validation_rejects_duplicate_nonmonotonic_validation_and_holdout(mutation) -> None:
    tool = load_tool()
    clock = tool.load_clock(CLOCK_PATH)
    rows = tool.build_request_rows(["2016-01-04", "2016-01-05"], clock)
    with pytest.raises(tool.InvalidEngineering):
        tool.validate_request_rows(mutation(rows), expected_count=len(mutation(rows)))


def test_canonical_create_new_outputs_are_deterministic_and_receipt_is_false_outcome(tmp_path: Path) -> None:
    tool = load_tool()
    clock = tool.load_clock(CLOCK_PATH)
    rows = tool.build_request_rows(frozen_dates(), clock)
    upstream = tool.expected_upstream_hashes()
    builder_sha = sha256(TOOL_PATH.read_bytes())
    clock_sha = sha256(CLOCK_PATH.read_bytes())
    receipt_a = tool.persist_request_plan(rows, tmp_path / "a", upstream, clock_sha, builder_sha)
    receipt_b = tool.persist_request_plan(rows, tmp_path / "b", upstream, clock_sha, builder_sha)
    for name in ("design_request_plan.jsonl", "design_request_plan_receipt.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    assert receipt_a == receipt_b
    assert receipt_a["request_count"] == 1297
    assert receipt_a["expected_m1_rows"] == 466_920
    assert receipt_a["design_plan_v2_sha256"] == tool.DESIGN_PLAN_V2_SHA256
    assert receipt_a["design_date_set_sha256"] == tool.DESIGN_DATE_SET_SHA256
    assert receipt_a["design_date_set_canonical_bytes"] == 14_301
    assert receipt_a["validation_m1_opened"] is False
    assert receipt_a["holdout_opened"] is False
    assert receipt_a["economics_computed"] is False
    with pytest.raises((tool.InvalidEngineering, FileExistsError)):
        tool.persist_request_plan(rows, tmp_path / "a", upstream, clock_sha, builder_sha)


def test_regular_input_rejects_hardlinks_and_symlinks(tmp_path: Path) -> None:
    tool = load_tool()
    source = tmp_path / "source.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    hardlink = tmp_path / "hardlink.jsonl"
    os.link(source, hardlink)
    with pytest.raises(tool.InvalidEngineering):
        tool.read_stable_file(source)

    target = tmp_path / "target.jsonl"
    target.write_text("{}\n", encoding="utf-8")
    symlink = tmp_path / "symlink.jsonl"
    try:
        symlink.symlink_to(target)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege is unavailable (WinError 1314)")
        raise
    with pytest.raises(tool.InvalidEngineering):
        tool.read_stable_file(symlink)


def test_output_root_rejects_input_overlap_and_real_junction_parent(tmp_path: Path) -> None:
    tool = load_tool()
    rows = tool.build_request_rows(frozen_dates(), tool.load_clock(CLOCK_PATH))
    upstream = tool.expected_upstream_hashes()
    builder_sha = sha256(TOOL_PATH.read_bytes())
    clock_sha = sha256(CLOCK_PATH.read_bytes())
    input_root = tmp_path / "accepted-input"
    input_root.mkdir()
    input_file = input_root / "ledger.jsonl"
    input_file.write_bytes(b"{}\n")
    with pytest.raises(tool.InvalidEngineering, match="overlap"):
        tool.persist_request_plan(
            rows,
            input_root / "output",
            upstream,
            clock_sha,
            builder_sha,
            input_paths=[input_root, input_file],
        )

    if os.name != "nt":
        pytest.skip("Windows junction test")
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    junction = tmp_path / "junction-parent"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(real_parent)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"junction creation unavailable: {result.stderr.strip()}")
    with pytest.raises(tool.InvalidEngineering, match="reparse"):
        tool.persist_request_plan(rows, junction / "output", upstream, clock_sha, builder_sha)


def test_output_parent_identity_swap_is_rejected_before_any_file_is_published(tmp_path: Path, monkeypatch) -> None:
    tool = load_tool()
    rows = tool.build_request_rows(frozen_dates(), tool.load_clock(CLOCK_PATH))
    upstream = tool.expected_upstream_hashes()
    builder_sha = sha256(TOOL_PATH.read_bytes())
    clock_sha = sha256(CLOCK_PATH.read_bytes())
    output = tmp_path / "identity-swap"
    real_lstat = tool.os.lstat

    def swapped_lstat(path):
        metadata = real_lstat(path)
        if Path(path) == tmp_path and output.exists():
            return SimpleNamespace(
                st_mode=metadata.st_mode,
                st_dev=metadata.st_dev,
                st_ino=metadata.st_ino + 1,
                st_size=metadata.st_size,
                st_mtime_ns=metadata.st_mtime_ns,
                st_ctime_ns=metadata.st_ctime_ns,
                st_nlink=metadata.st_nlink,
                st_file_attributes=getattr(metadata, "st_file_attributes", 0),
            )
        return metadata

    monkeypatch.setattr(tool.os, "lstat", swapped_lstat)
    with pytest.raises(tool.InvalidEngineering, match="identity"):
        tool.persist_request_plan(rows, output, upstream, clock_sha, builder_sha)
    assert not (output / "design_request_plan.jsonl").exists()
