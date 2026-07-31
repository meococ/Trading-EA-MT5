from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "build_eurfxofi_009_source_quality.py"
SPEC = importlib.util.spec_from_file_location("eurfxofi009", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_disarmed_sentinel_normalizes_without_logic_drift() -> None:
    assert MODULE.REVIEWED_REGISTRY_ROW_SHA256 is None
    payload = SCRIPT.read_bytes()
    base = MODULE.normalized_builder_base_sha256(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert MODULE.normalized_builder_base_sha256(armed) == base


def test_raw_payload_contract_is_explicit_child() -> None:
    root = Path("source_root")
    assert MODULE.raw_payload_root(root) == root / "raw"
    assert MODULE.FEATURE_REL_PATH().endswith("/source_features.parquet")
    assert MODULE.SUMMARY_REL_PATH().endswith("/source_quality_summary.json")
    assert MODULE.ARTIFACT_MANIFEST_REL_PATH().endswith("/artifact_manifest.json")


def test_extract_reconciles_and_decodes_from_raw_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source_root = tmp_path / "source"
    raw_root = source_root / "raw"
    raw_root.mkdir(parents=True)
    (source_root / "download_manifest.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "ledger.jsonl").write_text("{}\n", encoding="utf-8")
    captured: dict[str, Path] = {}
    spec = SimpleNamespace(
        source_empty=True,
        filename=None,
        request_id="ECBFX-2020-01-02",
    )

    def reconcile(manifest, ledger, payload_root):
        captured["payload_root"] = payload_root
        return [spec]

    def write_json(path: Path, payload: dict) -> None:
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    fake_v1 = SimpleNamespace(
        load_json=lambda path: {"downloads": []},
        load_ledger=lambda path: {"ECBFX-2020-01-02": {}},
        reconcile_manifest=reconcile,
        empty_feature_row=lambda item: {
            "local_date": "2020-01-02",
            "source_empty": True,
            "records": 0,
        },
        validate_and_decode_file=lambda path, item: pytest.fail("empty row must not decode"),
        source_summary=lambda frame, manifest, manifest_hash: {
            "verdict": "PASS_SOURCE_QUALITY",
            "decoded_records": 0,
        },
        write_json_atomic=write_json,
    )
    monkeypatch.setattr(MODULE, "workspace", lambda: tmp_path)
    monkeypatch.setattr(MODULE, "require_d", lambda path, label: path)
    monkeypatch.setattr(MODULE, "verify_authority", lambda root: {
        "registry_row_sha256": "A" * 64,
        "builder_base_sha256": "B" * 64,
        "builder_file_sha256": "C" * 64,
        "test_sha256": "D" * 64,
    })
    monkeypatch.setattr(MODULE, "load_v1", lambda root: fake_v1)
    monkeypatch.setattr(MODULE, "SOURCE_REL", "source")
    monkeypatch.setattr(MODULE, "OUTPUT_REL", "output")
    monkeypatch.setattr(MODULE, "EVIDENCE_REL", "evidence")
    monkeypatch.setattr(MODULE, "LEDGER_REL", "ledger.jsonl")
    output = MODULE.extract()
    assert output == tmp_path / "output"
    assert captured["payload_root"] == raw_root
    assert (output / MODULE.FEATURE_NAME).is_file()
    assert (output / MODULE.SUMMARY_NAME).is_file()
    assert (tmp_path / "evidence" / "attempt_started.json").is_file()
    assert (tmp_path / "evidence" / "extract_completed.json").is_file()


def test_authority_is_fail_closed_while_disarmed(tmp_path: Path) -> None:
    with pytest.raises(MODULE.SourceQualityError, match="not armed"):
        MODULE.verify_authority(tmp_path)
