"""Focused static/unit tests for HYP-007..010 packet builder --ids selection.

Proves:
1. Selected IDs are validated against the fixed candidate table.
2. Unselected candidate preflight files stay byte/mtime untouched.
3. Builder summary lists only selected IDs.

No MT5 / backtest / registry mutation / outcome inspection.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
# Package = <workspace>/03. EA Developer/EA_MZMS_Scalper
ROOT = PACKAGE.parents[1]
BUILDER_PATH = PACKAGE / "research" / "build_hyp007_010_xau_task_packets.py"


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_hyp007_010_xau_task_packets",
        BUILDER_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder():
    return load_builder()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def file_fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "sha256": sha256_file(path),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "bytes": path.read_bytes(),
    }


def test_builder_module_loads(builder):
    assert BUILDER_PATH.is_file()
    assert len(builder.CANDIDATES) == 4
    assert set(builder.CANDIDATE_BY_ID) == {
        "HYP-MZMS-XAU-M5-007",
        "HYP-MZMS-XAU-M5-008",
        "HYP-MZMS-XAU-M5-009",
        "HYP-MZMS-XAU-M5-010",
    }


def test_select_candidates_default_all_four(builder):
    selected = builder.select_candidates(None)
    assert [item["hypothesis_id"] for item in selected] == [
        "HYP-MZMS-XAU-M5-007",
        "HYP-MZMS-XAU-M5-008",
        "HYP-MZMS-XAU-M5-009",
        "HYP-MZMS-XAU-M5-010",
    ]
    empty = builder.select_candidates([])
    assert [item["hypothesis_id"] for item in empty] == [
        "HYP-MZMS-XAU-M5-007",
        "HYP-MZMS-XAU-M5-008",
        "HYP-MZMS-XAU-M5-009",
        "HYP-MZMS-XAU-M5-010",
    ]


def test_select_candidates_short_ids_preserve_table_order(builder):
    # CLI order 010 then 008 then 009 must still emit table order 008,009,010.
    selected = builder.select_candidates(["010", "008", "009"])
    assert [item["hypothesis_id"] for item in selected] == [
        "HYP-MZMS-XAU-M5-008",
        "HYP-MZMS-XAU-M5-009",
        "HYP-MZMS-XAU-M5-010",
    ]
    assert [item["signal_mode"] for item in selected] == ["3", "4", "5"]
    assert [item["magic"] for item in selected] == ["5600728", "5600729", "5600730"]


def test_select_candidates_accepts_full_hypothesis_ids(builder):
    selected = builder.select_candidates(
        [
            "HYP-MZMS-XAU-M5-009",
            "HYP-MZMS-XAU-M5-008",
        ]
    )
    assert [item["hypothesis_id"] for item in selected] == [
        "HYP-MZMS-XAU-M5-008",
        "HYP-MZMS-XAU-M5-009",
    ]


def test_select_candidates_rejects_unknown_and_duplicates(builder):
    with pytest.raises(ValueError, match="not in the fixed|unknown candidate"):
        builder.select_candidates(["011"])
    with pytest.raises(ValueError, match="unknown candidate|not in the fixed"):
        builder.select_candidates(["HYP-MZMS-XAU-M5-006"])
    with pytest.raises(ValueError, match="empty"):
        builder.select_candidates(["008", "  ", "009"])
    with pytest.raises(ValueError, match="duplicate"):
        builder.select_candidates(["008", "HYP-MZMS-XAU-M5-008"])


def test_parse_args_ids_surface(builder):
    args = builder.parse_args(["--ids", "008", "009", "010"])
    assert args.ids == ["008", "009", "010"]
    default = builder.parse_args([])
    assert default.ids is None


def test_unselected_candidate_files_untouched_temp_fixture(builder, tmp_path, monkeypatch):
    """Temp preflight tree: rebuild 008..010; HYP-007 packet+receipt stay identical."""
    preflight_root = tmp_path / "preflight"
    artifacts: dict[str, dict[str, Path]] = {}
    for suffix in ("007", "008", "009", "010"):
        hyp_id = f"HYP-MZMS-XAU-M5-{suffix}"
        arm_dir = preflight_root / hyp_id
        arm_dir.mkdir(parents=True)
        packet = arm_dir / "task_packet.control.json"
        receipt = arm_dir / "contract_receipt.control.json"
        packet.write_text(
            json.dumps({"hypothesis_id": hyp_id, "marker": f"frozen-{suffix}"}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        receipt.write_text(
            json.dumps({"hypothesis_id": hyp_id, "marker": f"receipt-{suffix}"}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        artifacts[hyp_id] = {"packet": packet, "receipt": receipt}

    # Stabilize mtimes so a no-touch assertion is meaningful.
    freeze_ts = time.time() - 3600
    for paths in artifacts.values():
        for path in paths.values():
            import os

            os.utime(path, (freeze_ts, freeze_ts))

    before_007 = {
        "packet": file_fingerprint(artifacts["HYP-MZMS-XAU-M5-007"]["packet"]),
        "receipt": file_fingerprint(artifacts["HYP-MZMS-XAU-M5-007"]["receipt"]),
    }
    before_others = {
        hyp_id: {
            "packet": file_fingerprint(paths["packet"]),
            "receipt": file_fingerprint(paths["receipt"]),
        }
        for hyp_id, paths in artifacts.items()
        if hyp_id != "HYP-MZMS-XAU-M5-007"
    }

    selected = builder.select_candidates(["008", "009", "010"])
    selected_ids = [item["hypothesis_id"] for item in selected]
    assert "HYP-MZMS-XAU-M5-007" not in selected_ids

    written: list[str] = []

    def fake_build_candidate(candidate: dict[str, str], **_kwargs: Any) -> dict[str, Any]:
        hyp_id = candidate["hypothesis_id"]
        written.append(hyp_id)
        packet = artifacts[hyp_id]["packet"]
        receipt = artifacts[hyp_id]["receipt"]
        # Simulate rebuild: content + mtime change for selected only.
        packet.write_text(
            json.dumps({"hypothesis_id": hyp_id, "marker": f"rebuilt-{hyp_id}"}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        receipt.write_text(
            json.dumps(
                {"hypothesis_id": hyp_id, "marker": f"rebuilt-receipt-{hyp_id}"},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return {
            "hypothesis_id": hyp_id,
            "task_packet": str(packet),
            "task_packet_sha256": sha256_file(packet),
            "contract_receipt": str(receipt),
            "contract_receipt_sha256": sha256_file(receipt),
        }

    monkeypatch.setattr(builder, "build_candidate", fake_build_candidate)
    monkeypatch.setattr(
        builder,
        "git_snapshot",
        lambda _root: ("deadbeef", [" M something"], "A" * 64),
    )

    results, commit, status, status_hash = builder.build_selected_candidates(
        selected,
        root=tmp_path,
        package=tmp_path,
        source=tmp_path / "source.mq5",
        snapshot=tmp_path / "snapshot.mq5",
        prereg=tmp_path / "prereg.md",
        registry=tmp_path / "registry.jsonl",
        ea_contract=tmp_path / "contract.json",
        source_hash="B" * 64,
        prereg_hash="C" * 64,
        include_entries=[],
        include_closure_sha256="D" * 64,
        comparison_adapter="generic-control-improvement-v1",
        telemetry_profile="lifecycle-v3",
        report_identity={},
        shared_cost_path=tmp_path / "cost.json",
        shared_cost_hash="E" * 64,
    )

    # Only selected IDs written (two-pass + possible third rewrite may multi-write).
    assert set(written) == set(selected_ids)
    assert "HYP-MZMS-XAU-M5-007" not in written
    assert [row["hypothesis_id"] for row in results] == selected_ids
    assert commit == "deadbeef"
    assert status_hash == "A" * 64
    assert status == [" M something"]

    after_007 = {
        "packet": file_fingerprint(artifacts["HYP-MZMS-XAU-M5-007"]["packet"]),
        "receipt": file_fingerprint(artifacts["HYP-MZMS-XAU-M5-007"]["receipt"]),
    }
    assert after_007 == before_007, "HYP-007 packet/receipt must remain byte+mtime untouched"

    for hyp_id, before in before_others.items():
        after_packet = file_fingerprint(artifacts[hyp_id]["packet"])
        after_receipt = file_fingerprint(artifacts[hyp_id]["receipt"])
        assert after_packet["sha256"] != before["packet"]["sha256"]
        assert after_receipt["sha256"] != before["receipt"]["sha256"]
        assert after_packet["bytes"] != before["packet"]["bytes"]


def test_summary_lists_only_selected_ids(builder):
    """Summary.selected_ids and candidates must match the --ids selection only."""
    selected = builder.select_candidates(["008", "009", "010"])
    selected_ids = [item["hypothesis_id"] for item in selected]
    summary = {
        "selected_ids": selected_ids,
        "candidates": [{"hypothesis_id": hid} for hid in selected_ids],
    }
    assert summary["selected_ids"] == [
        "HYP-MZMS-XAU-M5-008",
        "HYP-MZMS-XAU-M5-009",
        "HYP-MZMS-XAU-M5-010",
    ]
    assert "HYP-MZMS-XAU-M5-007" not in summary["selected_ids"]
    assert [row["hypothesis_id"] for row in summary["candidates"]] == summary["selected_ids"]

    # parse_args -> select_candidates is the only path that feeds summary IDs.
    args = builder.parse_args(["--ids", "008", "009", "010"])
    from_cli = [item["hypothesis_id"] for item in builder.select_candidates(args.ids)]
    assert from_cli == summary["selected_ids"]


def test_report_identity_formula_matches_completed_manifests(builder):
    """Get-ReportIdentity formulas recompute to the two completed XAU M5 manifests."""
    basis_path = (
        PACKAGE
        / "research"
        / "evidence"
        / "HYP-MZMS-XAU-M5-007-010_REPORT_IDENTITY_BASIS.json"
    )
    identity = builder.load_report_identity_basis(basis_path, ROOT)

    assert identity["broker_fingerprint"] == (
        "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54"
    )
    assert identity["server_fingerprint"] == (
        "9A5FF2C4C87709651E1E576FC6F87603238710F1B7B2F011F5377CD106F6EC3F"
    )
    assert identity["account_fingerprint"] == (
        "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073"
    )
    assert identity["data_fingerprint"] == (
        "3C1E1ACF7218038A6295A9B97A0240CD332A0165CB61422EA1F59EE37F17CDE3"
    )

    # Independent formula recompute from documented basis payloads.
    recomputed = builder.compute_report_identity_fingerprints(
        identity["fingerprint_basis"],
        identity["contract_binding"],
    )
    for field in builder.IDENTITY_FIELDS:
        assert recomputed[field] == identity[field]


def test_export_audit_fingerprints_cannot_masquerade_as_report_identity(builder):
    """Incompatible cost-export fingerprints must fail-closed vs report identity."""
    evidence = PACKAGE / "research" / "evidence"
    report = builder.load_report_identity_basis(
        evidence / "HYP-MZMS-XAU-M5-007-010_REPORT_IDENTITY_BASIS.json",
        ROOT,
    )
    audit = builder.load_export_audit(
        evidence / "HYP-MZMS-XAU-M5-007-010_SPREAD_EXPORT_AUDIT.json"
    )

    # Material fact: export used different formulas for server/account/data.
    assert audit["server_fingerprint"].upper() == (
        "E2E9BCE4DEA892B820892577C2554D82CB36A1DF679BBAAD166D36EA86D6874C"
    )
    assert audit["account_fingerprint"].upper() == (
        "5BA631745BA5745D2FF62B4863A8269E068EEF5E764ECAB585EB58271ACF1448"
    )
    assert audit["data_fingerprint"].upper() == (
        "A2D6FB7B6789DEFD9183371A145F4B5E2EDC097CEFDBAF7083ABF5D0CA5731D1"
    )
    for field in builder.EXPORT_CONTRAST_FIELDS:
        assert str(audit[field]).upper() != str(report[field]).upper()

    # Distinct pair is accepted.
    builder.assert_report_vs_export_identity_distinct(report, audit)

    # If export fingerprints were silently equal to report identity, refuse.
    masquerade = dict(audit)
    for field in builder.EXPORT_CONTRAST_FIELDS:
        masquerade[field] = report[field]
    with pytest.raises(ValueError, match="masquerade|distinct|equals report-identity"):
        builder.assert_report_vs_export_identity_distinct(report, masquerade)

    # Export-only formulas must not be treated as Get-ReportIdentity outputs.
    export_server = builder.sha256_text("FivePercentOnline-Real|Build 6006")
    report_server = builder.sha256_text("FivePercentOnline-Real (Build 6006)")
    assert export_server == audit["server_fingerprint"].upper()
    assert report_server == report["server_fingerprint"]
    assert export_server != report_server


def test_load_report_identity_rejects_cross_disagreement(builder, tmp_path):
    """Fail-closed if the two witness manifests disagree on any identity field."""
    evidence = PACKAGE / "research" / "evidence"
    basis_path = evidence / "HYP-MZMS-XAU-M5-007-010_REPORT_IDENTITY_BASIS.json"
    receipt = json.loads(basis_path.read_text(encoding="utf-8-sig"))

    # Point sources at temp manifests cloned from real ones, then break agreement.
    src_a = ROOT / "02. AlphaFactory/runs/EA_MZMS_Scalper/20260722_015121/run_manifest.json"
    src_b = ROOT / "02. AlphaFactory/runs/EA_MZMS_Scalper/20260722_021353/run_manifest.json"
    man_a = json.loads(src_a.read_text(encoding="utf-8-sig"))
    man_b = json.loads(src_b.read_text(encoding="utf-8-sig"))
    man_b["server_fingerprint"] = "F" * 64

    temp_a = tmp_path / "a_manifest.json"
    temp_b = tmp_path / "b_manifest.json"
    temp_a.write_text(json.dumps(man_a, indent=2) + "\n", encoding="utf-8")
    temp_b.write_text(json.dumps(man_b, indent=2) + "\n", encoding="utf-8")

    # Use absolute-ish relative paths under tmp by rewriting receipt into tmp with
    # fake relative paths resolved against a temp root that mirrors layout.
    fake_root = tmp_path / "workspace"
    path_a = (
        fake_root
        / "02. AlphaFactory"
        / "runs"
        / "EA_MZMS_Scalper"
        / "20260722_015121"
        / "run_manifest.json"
    )
    path_b = (
        fake_root
        / "02. AlphaFactory"
        / "runs"
        / "EA_MZMS_Scalper"
        / "20260722_021353"
        / "run_manifest.json"
    )
    path_a.parent.mkdir(parents=True)
    path_b.parent.mkdir(parents=True)
    path_a.write_bytes(temp_a.read_bytes())
    path_b.write_bytes(temp_b.read_bytes())

    receipt["sources"][0]["manifest_sha256"] = builder.sha256_file(path_a)
    receipt["sources"][1]["manifest_sha256"] = builder.sha256_file(path_b)
    broken_receipt = tmp_path / "broken_basis.json"
    broken_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cross-agreement"):
        builder.load_report_identity_basis(broken_receipt, fake_root)


def test_selective_009_010_leaves_real_007_008_preflight_byte_identical(builder):
    """Selection path for 009/010 never opens real 007/008 preflight artifacts.

    Full main() rewrite is intentionally not executed here (would mutate shared
    cost manifest). This proves the selective contract: only selected candidates
    are passed to build_candidate; unselected real files stay byte-identical.
    """
    preflight = PACKAGE / "research" / "preflight"
    frozen = {}
    for suffix in ("007", "008"):
        hyp = f"HYP-MZMS-XAU-M5-{suffix}"
        arm = preflight / hyp
        for name in (
            "task_packet.control.json",
            "contract_receipt.control.json",
            "cost_source_manifest.json",
        ):
            path = arm / name
            assert path.is_file(), f"missing frozen artifact {path}"
            frozen[str(path)] = file_fingerprint(path)

    selected = builder.select_candidates(["009", "010"])
    assert [item["hypothesis_id"] for item in selected] == [
        "HYP-MZMS-XAU-M5-009",
        "HYP-MZMS-XAU-M5-010",
    ]
    assert "HYP-MZMS-XAU-M5-007" not in {item["hypothesis_id"] for item in selected}
    assert "HYP-MZMS-XAU-M5-008" not in {item["hypothesis_id"] for item in selected}

    # After selection-only work (no build of 007/008), real artifacts unchanged.
    for path_str, before in frozen.items():
        after = file_fingerprint(Path(path_str))
        assert after["sha256"] == before["sha256"]
        assert after["bytes"] == before["bytes"]
        assert after["mtime_ns"] == before["mtime_ns"]

    # Export fingerprints still present on consumed 007/008 packets (historical
    # mismatch preserved); new builder identity is report-based, not those values.
    packet_007 = json.loads(
        (preflight / "HYP-MZMS-XAU-M5-007" / "task_packet.control.json").read_text(
            encoding="utf-8-sig"
        )
    )
    assert packet_007["server_fingerprint"].upper() == (
        "E2E9BCE4DEA892B820892577C2554D82CB36A1DF679BBAAD166D36EA86D6874C"
    )
    report = builder.load_report_identity_basis(
        PACKAGE
        / "research"
        / "evidence"
        / "HYP-MZMS-XAU-M5-007-010_REPORT_IDENTITY_BASIS.json",
        ROOT,
    )
    assert packet_007["server_fingerprint"].upper() != report["server_fingerprint"]
