from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "build_eurfxofi_010_source_quality.py"
SPEC = importlib.util.spec_from_file_location("eurfxofi010", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@dataclass
class WindowSpec:
    request_id: str
    local_date: str
    split: str
    start: str
    end: str
    filename: str | None
    source_empty: bool
    expected_bytes: int
    expected_sha256: str | None
    expected_records: int


def test_disarmed_sentinel_normalization_is_stable() -> None:
    assert MODULE.REVIEWED_REGISTRY_ROW_SHA256 is None
    payload = SCRIPT.read_bytes()
    base = MODULE.normalized_builder_base_sha256(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert MODULE.normalized_builder_base_sha256(armed) == base


def test_reconcile_preserves_paid_and_live_empty_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(MODULE, "EXPECTED_FILES", 2)
    monkeypatch.setattr(MODULE, "EXPECTED_POSITIVE_FILES", 1)
    monkeypatch.setattr(MODULE, "EXPECTED_PAID_EMPTY", 1)
    monkeypatch.setattr(MODULE, "EXPECTED_LIVE_EMPTY", 1)
    monkeypatch.setattr(MODULE, "EXPECTED_ROWS", 3)
    (tmp_path / "positive.dbn.zst").write_bytes(b"positive")
    (tmp_path / "empty.dbn.zst").write_bytes(b"empty")
    v1 = type("V1", (), {"FINAL_PARENT_STATUS": "DONE", "WindowSpec": WindowSpec})
    ledger = {
        "POS": {"local_date": "2020-01-02", "split": "TRAIN"},
        "PAID_EMPTY": {"local_date": "2020-01-03", "split": "TRAIN"},
        "LIVE_EMPTY": {"local_date": "2020-01-06", "split": "TRAIN"},
    }
    manifest = {
        "status": "DONE",
        "in_flight": None,
        "outcome_fields_used": False,
        "downloads": [
            {
                "request_id": "POS",
                "local_date": "2020-01-02",
                "split": "TRAIN",
                "start": "2020-01-02T00:00:00Z",
                "end": "2020-01-02T00:00:15Z",
                "filename": "positive.dbn.zst",
                "source_empty": False,
                "records": 2,
                "bytes": 8,
                "sha256": "A" * 64,
            },
            {
                "request_id": "PAID_EMPTY",
                "local_date": "2020-01-03",
                "split": "TRAIN",
                "start": "2020-01-03T00:00:00Z",
                "end": "2020-01-03T00:00:15Z",
                "filename": "empty.dbn.zst",
                "source_empty": True,
                "records": 0,
                "bytes": 5,
                "sha256": "B" * 64,
            },
        ],
        "source_empty_windows": [
            {
                "request_id": "LIVE_EMPTY",
                "start": "2020-01-06T00:00:00Z",
                "end": "2020-01-06T00:00:15Z",
            }
        ],
    }
    decoded: list[tuple[Path, str]] = []
    specs = MODULE.reconcile_manifest_010(
        v1,
        manifest,
        ledger,
        tmp_path,
        lambda path, spec: decoded.append((path, spec.request_id)),
    )
    assert len(specs) == 3
    assert decoded == [(tmp_path / "empty.dbn.zst", "PAID_EMPTY")]
    paid = next(spec for spec in specs if spec.request_id == "PAID_EMPTY")
    live = next(spec for spec in specs if spec.request_id == "LIVE_EMPTY")
    assert paid.source_empty is True and paid.filename == "empty.dbn.zst"
    assert live.source_empty is True and live.filename is None


def test_paid_empty_record_mismatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(MODULE, "EXPECTED_FILES", 1)
    monkeypatch.setattr(MODULE, "EXPECTED_POSITIVE_FILES", 0)
    monkeypatch.setattr(MODULE, "EXPECTED_PAID_EMPTY", 1)
    monkeypatch.setattr(MODULE, "EXPECTED_LIVE_EMPTY", 0)
    monkeypatch.setattr(MODULE, "EXPECTED_ROWS", 1)
    (tmp_path / "empty.dbn.zst").write_bytes(b"empty")
    v1 = type("V1", (), {"FINAL_PARENT_STATUS": "DONE", "WindowSpec": WindowSpec})
    manifest = {
        "status": "DONE",
        "in_flight": None,
        "outcome_fields_used": False,
        "downloads": [
            {
                "request_id": "X",
                "local_date": "2020-01-02",
                "split": "TRAIN",
                "start": "2020-01-02T00:00:00Z",
                "end": "2020-01-02T00:00:15Z",
                "filename": "empty.dbn.zst",
                "source_empty": True,
                "records": 1,
                "bytes": 5,
                "sha256": "A" * 64,
            }
        ],
        "source_empty_windows": [],
    }
    with pytest.raises(MODULE.SourceQualityError, match="empty/record mismatch"):
        MODULE.reconcile_manifest_010(
            v1,
            manifest,
            {"X": {"local_date": "2020-01-02", "split": "TRAIN"}},
            tmp_path,
            lambda path, spec: None,
        )


def test_authority_fails_while_disarmed(tmp_path: Path) -> None:
    with pytest.raises(MODULE.SourceQualityError, match="not armed"):
        MODULE.verify_authority(tmp_path)
