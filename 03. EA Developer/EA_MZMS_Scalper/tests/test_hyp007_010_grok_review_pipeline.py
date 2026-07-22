"""Focused tests for HYP-007..010 Grok vision review request/collect pipeline."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "03. EA Developer" / "EA_MZMS_Scalper" / "research"
BUILDER = RESEARCH / "build_hyp007_010_grok_review_requests.py"
COLLECTOR = RESEARCH / "collect_hyp007_010_grok_review.py"
BATCH = RESEARCH / "run_hyp007_010_grok_review_batch.py"
EVIDENCE = RESEARCH / "evidence" / "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400"
CONTEXT = ROOT / ".context"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def builder():
    return load_module(BUILDER, "build_hyp007_010_grok_review_requests")


@pytest.fixture(scope="module")
def collector():
    return load_module(COLLECTOR, "collect_hyp007_010_grok_review")


@pytest.fixture(scope="module")
def batch():
    return load_module(BATCH, "run_hyp007_010_grok_review_batch")


def test_builder_constants(builder):
    assert builder.CHUNK_SIZE == 10
    assert builder.CHUNK_COUNT == 10
    assert len(builder.HYPOTHESES) == 4
    assert [h["short"] for h in builder.HYPOTHESES] == ["007", "008", "009", "010"]
    assert builder.EVIDENCE.exists()
    assert builder.CASEBOOK.exists()


def test_response_schema_requires_core_fields(builder):
    schema = builder.response_schema("HYP-MZMS-XAU-M5-007", "chunk_01", 10)
    required = set(schema["required"])
    assert {
        "hypothesis_id",
        "chunk_id",
        "image_inspection_supported",
        "coverage",
        "cases",
        "ranked_mechanisms",
        "classification_summary",
        "fresh_hypothesis_candidates",
    } <= required
    case_props = schema["properties"]["cases"]["items"]["properties"]
    assert "case_kind" in case_props
    assert case_props["position_id"]["type"] == ["integer", "null"]
    assert set(case_props["evidence_label"]["enum"]) == {
        "OBSERVED",
        "STRONG_INFERENCE",
        "HYPOTHESIS",
        "UNKNOWN",
    }
    class_keys = set(
        schema["properties"]["classification_summary"]["required"]
    )
    assert class_keys == {
        "bad_entry_or_adverse_selection",
        "normal_stochastic_loss",
        "good_rejected_near_miss",
        "cadence_bottleneck",
    }


def test_synthesis_schema_blocks_promotion_and_rescue(builder):
    schema = builder.synthesis_response_schema()
    assert schema["properties"]["promotion_blocked"]["const"] is True
    assert schema["properties"]["post_hoc_rescue_blocked"]["const"] is True
    assert "owner_facing_markdown_vi" in schema["required"]
    assert schema["properties"]["fresh_prereg_candidates"]["maxItems"] == 4


def test_build_all_creates_exactly_40_requests_and_synthesis(builder):
    summary = builder.build_all()
    assert summary["chunk_requests"] == 40
    assert Path(summary["synthesis_request"]).exists()
    for short in ("007", "008", "009", "010"):
        for number in range(1, 11):
            path = CONTEXT / f"mzms-xau-007-010-vision-{short}-c{number:02d}" / "grok-request.json"
            assert path.exists(), path
            req = json.loads(path.read_text(encoding="utf-8"))
            assert req["task"] == f"mzms-xau-007-010-vision-{short}-chunk_{number:02d}"
            assert req["request"]["response_format"]["type"] == "json_schema"
            meta = req["meta"]
            assert len(meta["case_ids"]) == 10
            assert len(meta["image_paths"]) == 10
            assert all(Path(p).exists() for p in meta["image_paths"])
            prompt = req["request"]["input"][1]["content"]
            assert "98%" in prompt
            assert "CopyBuffer" in prompt
            assert "telemetry" in prompt.lower() or "StateTelemetry" in prompt
            assert "hypothetical PnL" in prompt or "hypothetical" in prompt.lower()
            assert "cannot promote" in prompt.lower() or "cannot authorize" in prompt.lower()
            assert "post-hoc" in prompt.lower() or "rescue" in prompt.lower()
    synth = json.loads(Path(summary["synthesis_request"]).read_text(encoding="utf-8"))
    assert synth["meta"]["promotion_blocked"] is True
    assert synth["meta"]["post_hoc_rescue_blocked"] is True
    synth_prompt = synth["request"]["input"][1]["content"]
    assert "Vietnamese" in synth_prompt or "owner_facing_markdown_vi" in synth_prompt
    assert "007" in synth_prompt and "010" in synth_prompt


def test_chunk_order_matches_casebook(builder):
    casebook = json.loads(builder.CASEBOOK.read_text(encoding="utf-8"))
    by_hyp = {}
    for row in casebook["results"]:
        by_hyp.setdefault(row["hypothesis_id"], []).append(row["case_id"])
    for short, hyp_id in (
        ("007", "HYP-MZMS-XAU-M5-007"),
        ("008", "HYP-MZMS-XAU-M5-008"),
        ("009", "HYP-MZMS-XAU-M5-009"),
        ("010", "HYP-MZMS-XAU-M5-010"),
    ):
        ordered = by_hyp[hyp_id]
        assert len(ordered) == 100
        rebuilt = []
        for number in range(1, 11):
            req = json.loads(
                (
                    CONTEXT
                    / f"mzms-xau-007-010-vision-{short}-c{number:02d}"
                    / "grok-request.json"
                ).read_text(encoding="utf-8")
            )
            rebuilt.extend(req["meta"]["case_ids"])
        assert rebuilt == ordered


def test_near_miss_position_null_in_manifests(builder):
    # HYP-008 has 20 near-misses; HYP-010 has 98.
    for short in ("008", "010"):
        found_near_miss = False
        for number in range(1, 11):
            manifest = json.loads(
                (
                    EVIDENCE
                    / "grok_review_chunks10"
                    / short
                    / f"chunk_{number:02d}"
                    / "chunk_manifest.json"
                ).read_text(encoding="utf-8")
            )
            for image in manifest["images"]:
                if image["case_kind"] == "OFFLINE_NEAR_MISS_DIAGNOSTIC":
                    found_near_miss = True
                    assert image["position_id"] is None
                else:
                    assert isinstance(image["position_id"], int)
        assert found_near_miss


def test_collector_valid_candidate_accepts_good_payload(builder, collector, tmp_path):
    # Use a real chunk request for expected IDs/hashes.
    short = "007"
    chunk_id = "chunk_01"
    request_src = CONTEXT / f"mzms-xau-007-010-vision-{short}-c01" / "grok-request.json"
    request = json.loads(request_src.read_text(encoding="utf-8"))
    case_ids = request["meta"]["case_ids"]
    position_ids = request["meta"]["position_ids"]
    case_kinds = request["meta"]["case_kinds"]
    cases = []
    for case_id, pos, kind in zip(case_ids, position_ids, case_kinds):
        cases.append(
            {
                "case_id": case_id,
                "case_kind": kind,
                "position_id": pos,
                "image_opened": True,
                "price_structure_observed": "observed structure",
                "indicator_gate_observed": "observed gates",
                "path_observed": "observed path",
                "primary_mechanism": "test mechanism",
                "evidence_label": "OBSERVED",
                "confidence": "HIGH",
                "fidelity_note": "ok",
            }
        )
    instance = {
        "hypothesis_id": "HYP-MZMS-XAU-M5-007",
        "chunk_id": chunk_id,
        "validity_boundary": builder.VALIDITY_BOUNDARY,
        "image_inspection_supported": True,
        "coverage": {
            "expected_images": 10,
            "images_opened": 10,
            "all_cases_reported": True,
        },
        "cases": cases,
        "ranked_mechanisms": [
            {
                "rank": 1,
                "label": "test",
                "case_ids": case_ids[:2],
                "count_in_chunk": 2,
                "finding": "f",
                "confidence": "MEDIUM",
            }
        ],
        "classification_summary": {
            "bad_entry_or_adverse_selection": case_ids[:1],
            "normal_stochastic_loss": case_ids[1:3],
            "good_rejected_near_miss": [],
            "cadence_bottleneck": [],
        },
        "fresh_hypothesis_candidates": [],
        "chunk_verdict": "diagnostic only",
        "limitations": ["synthetic test payload"],
    }
    task_dir = tmp_path / "good"
    task_dir.mkdir()
    (task_dir / "grok-request.json").write_text(
        json.dumps(request), encoding="utf-8"
    )
    summary = {
        "success": True,
        "structured_output_validation": {
            "passed": True,
            "instance": instance,
        },
    }
    summary_path = task_dir / "summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    ok, reason, payload = collector.valid_candidate(summary_path)
    assert ok is True
    assert reason == "ok"
    assert payload is not None
    assert payload["chunk_id"] == chunk_id


def test_collector_rejects_order_mismatch(builder, collector, tmp_path):
    short = "007"
    request_src = CONTEXT / f"mzms-xau-007-010-vision-{short}-c01" / "grok-request.json"
    request = json.loads(request_src.read_text(encoding="utf-8"))
    case_ids = list(request["meta"]["case_ids"])
    case_ids[0], case_ids[1] = case_ids[1], case_ids[0]
    position_ids = list(request["meta"]["position_ids"])
    position_ids[0], position_ids[1] = position_ids[1], position_ids[0]
    case_kinds = list(request["meta"]["case_kinds"])
    case_kinds[0], case_kinds[1] = case_kinds[1], case_kinds[0]
    cases = []
    for case_id, pos, kind in zip(case_ids, position_ids, case_kinds):
        cases.append(
            {
                "case_id": case_id,
                "case_kind": kind,
                "position_id": pos,
                "image_opened": True,
                "price_structure_observed": "x",
                "indicator_gate_observed": "x",
                "path_observed": "x",
                "primary_mechanism": "x",
                "evidence_label": "OBSERVED",
                "confidence": "LOW",
                "fidelity_note": "x",
            }
        )
    instance = {
        "hypothesis_id": "HYP-MZMS-XAU-M5-007",
        "chunk_id": "chunk_01",
        "validity_boundary": builder.VALIDITY_BOUNDARY,
        "image_inspection_supported": True,
        "coverage": {
            "expected_images": 10,
            "images_opened": 10,
            "all_cases_reported": True,
        },
        "cases": cases,
        "ranked_mechanisms": [
            {
                "rank": 1,
                "label": "t",
                "case_ids": [case_ids[0]],
                "count_in_chunk": 1,
                "finding": "f",
                "confidence": "LOW",
            }
        ],
        "classification_summary": {
            "bad_entry_or_adverse_selection": [],
            "normal_stochastic_loss": [],
            "good_rejected_near_miss": [],
            "cadence_bottleneck": [],
        },
        "fresh_hypothesis_candidates": [],
        "chunk_verdict": "x",
        "limitations": [],
    }
    task_dir = tmp_path / "bad_order"
    task_dir.mkdir()
    (task_dir / "grok-request.json").write_text(json.dumps(request), encoding="utf-8")
    summary_path = task_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "success": True,
                "structured_output_validation": {
                    "passed": True,
                    "instance": instance,
                },
            }
        ),
        encoding="utf-8",
    )
    ok, reason, _ = collector.valid_candidate(summary_path)
    assert ok is False
    assert reason == "case_order_or_id_mismatch"


def test_collector_fail_closed_without_chunks(collector):
    accepted = {short: {} for short in collector.SHORT_IDS}
    with pytest.raises(RuntimeError, match="incomplete validated Grok coverage"):
        collector.consolidate(accepted, audit=[])


def test_collector_status_shape(collector):
    accepted, audit = collector.discover()
    report = collector.status_report(accepted)
    assert set(report) == {"007", "008", "009", "010"}
    for short in collector.SHORT_IDS:
        assert "validated_chunks" in report[short]
        assert "missing_chunks" in report[short]
    assert isinstance(audit, list)


def test_batch_enumerates_40(batch):
    rows = batch.enumerate_chunks()
    assert len(rows) == 40
    assert rows[0][0] == "007" and rows[0][1] == 1
    assert rows[-1][0] == "010" and rows[-1][1] == 10
    subset = batch.enumerate_chunks("008", [2, 3])
    assert [(s, n) for s, n, _ in subset] == [("008", 2), ("008", 3)]


def test_batch_permission_mode_defaults_and_cli_choices(batch):
    assert batch.DEFAULT_PERMISSION_MODE == "bypassPermissions"
    assert batch.PERMISSION_MODES == ("auto", "bypassPermissions")


def test_batch_build_runner_cmd_bypass_adds_always_approve(batch, tmp_path):
    path = tmp_path / "chunk"
    path.mkdir()
    (path / "grok-request.json").write_text("{}", encoding="utf-8")
    cmd = batch.build_runner_cmd(
        path,
        permission_mode="bypassPermissions",
        dry_run=False,
        timeout_seconds=1800,
        max_turns=40,
    )
    assert "--permission-mode" in cmd
    mode_idx = cmd.index("--permission-mode")
    assert cmd[mode_idx + 1] == "bypassPermissions"
    assert "--always-approve" in cmd
    assert "--no-plan" in cmd
    assert "--no-subagents" in cmd
    assert "--disable-web-search" in cmd
    assert "--dry-run" not in cmd


def test_batch_build_runner_cmd_auto_omits_always_approve(batch, tmp_path):
    path = tmp_path / "chunk"
    path.mkdir()
    (path / "grok-request.json").write_text("{}", encoding="utf-8")
    cmd = batch.build_runner_cmd(
        path,
        permission_mode="auto",
        dry_run=True,
        timeout_seconds=900,
        max_turns=20,
    )
    mode_idx = cmd.index("--permission-mode")
    assert cmd[mode_idx + 1] == "auto"
    assert "--always-approve" not in cmd
    assert "--dry-run" in cmd
    assert cmd[cmd.index("--max-turns") + 1] == "20"
    assert cmd[cmd.index("--timeout-seconds") + 1] == "900"


def test_batch_build_runner_cmd_rejects_unknown_mode(batch, tmp_path):
    path = tmp_path / "chunk"
    path.mkdir()
    with pytest.raises(ValueError, match="permission_mode"):
        batch.build_runner_cmd(
            path,
            permission_mode="dangerous",
            dry_run=False,
            timeout_seconds=1,
            max_turns=1,
        )


def test_batch_skip_logic_uses_collector(batch, collector, tmp_path):
    # Synthetic failed/cancelled chunk: stop_reason Cancelled, success=false.
    # Isolated under tmp_path so live recovered tasks cannot make this env-dependent.
    task_dir = tmp_path / "failed_cancelled_skip"
    task_dir.mkdir()
    summary = {
        "success": False,
        "stop_reason": "Cancelled",
        "structured_output_validation": {
            "passed": False,
            "instance": None,
        },
        "coverage": {
            "expected_images": 10,
            "images_opened": 0,
            "all_cases_reported": False,
        },
    }
    (task_dir / "summary.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    ok, reason = batch.chunk_already_valid(collector, task_dir)
    # Honest smoke failure must never be treated as valid resume skip.
    assert ok is False
    assert reason == "runner_not_success"


def test_batch_skips_only_when_collector_marks_valid(
    batch, collector, builder, tmp_path
):
    # Synthetic valid summary in an isolated dir must be skip-eligible.
    short = "007"
    chunk_id = "chunk_01"
    request_src = CONTEXT / f"mzms-xau-007-010-vision-{short}-c01" / "grok-request.json"
    request = json.loads(request_src.read_text(encoding="utf-8"))
    case_ids = request["meta"]["case_ids"]
    position_ids = request["meta"]["position_ids"]
    case_kinds = request["meta"]["case_kinds"]
    cases = []
    for case_id, pos, kind in zip(case_ids, position_ids, case_kinds):
        cases.append(
            {
                "case_id": case_id,
                "case_kind": kind,
                "position_id": pos,
                "image_opened": True,
                "price_structure_observed": "observed structure",
                "indicator_gate_observed": "observed gates",
                "path_observed": "observed path",
                "primary_mechanism": "test mechanism",
                "evidence_label": "OBSERVED",
                "confidence": "HIGH",
                "fidelity_note": "ok",
            }
        )
    instance = {
        "hypothesis_id": "HYP-MZMS-XAU-M5-007",
        "chunk_id": chunk_id,
        "validity_boundary": builder.VALIDITY_BOUNDARY,
        "image_inspection_supported": True,
        "coverage": {
            "expected_images": 10,
            "images_opened": 10,
            "all_cases_reported": True,
        },
        "cases": cases,
        "ranked_mechanisms": [
            {
                "rank": 1,
                "label": "test",
                "case_ids": case_ids[:2],
                "count_in_chunk": 2,
                "finding": "f",
                "confidence": "MEDIUM",
            }
        ],
        "classification_summary": {
            "bad_entry_or_adverse_selection": case_ids[:1],
            "normal_stochastic_loss": case_ids[1:3],
            "good_rejected_near_miss": [],
            "cadence_bottleneck": [],
        },
        "fresh_hypothesis_candidates": [],
        "chunk_verdict": "diagnostic only",
        "limitations": ["synthetic test payload"],
    }
    task_dir = tmp_path / "valid_skip"
    task_dir.mkdir()
    (task_dir / "grok-request.json").write_text(
        json.dumps(request), encoding="utf-8"
    )
    (task_dir / "summary.json").write_text(
        json.dumps(
            {
                "success": True,
                "structured_output_validation": {
                    "passed": True,
                    "instance": instance,
                },
            }
        ),
        encoding="utf-8",
    )
    ok, reason = batch.chunk_already_valid(collector, task_dir)
    assert ok is True
    assert reason == "ok"
