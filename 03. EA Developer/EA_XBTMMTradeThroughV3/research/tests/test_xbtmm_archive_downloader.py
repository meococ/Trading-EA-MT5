from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[2]
TOOL = PACKAGE / "research" / "tools" / "download_xbtmm_archives.py"
SPEC = importlib.util.spec_from_file_location("download_xbtmm_archives", TOOL)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sut
SPEC.loader.exec_module(sut)


def test_design_bounds_are_fail_closed() -> None:
    assert len(list(sut.iter_days(date(2018, 1, 1), date(2021, 12, 31)))) == 1461
    with pytest.raises(ValueError):
        list(sut.iter_days(date(2022, 1, 1), date(2022, 1, 1)))
    with pytest.raises(ValueError):
        list(sut.iter_days(date(2017, 12, 31), date(2018, 1, 1)))


def test_append_only_ledger_chain_detects_tampering(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    records: list[dict] = []
    first = sut.append_ledger(
        ledger,
        records,
        {
            "utc_day": "20180101",
            "kind": "quote",
            "status": "COMPLETE",
            "bytes": 3,
            "sha256": "A" * 64,
        },
    )
    second = sut.append_ledger(
        ledger,
        records,
        {
            "utc_day": "20180101",
            "kind": "trade",
            "status": "COMPLETE",
            "bytes": 4,
            "sha256": "B" * 64,
        },
    )

    loaded = sut.load_ledger(ledger)
    assert loaded == [first, second]
    assert second["previous_record_sha256"] == first["record_sha256"]

    lines = ledger.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["bytes"] = 9
    lines[0] = json.dumps(row, sort_keys=True, separators=(",", ":"))
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(sut.IntegrityError):
        sut.load_ledger(ledger)


def test_adopt_existing_requires_explicit_authority_and_hashes_file(tmp_path: Path) -> None:
    item = sut.WorkItem(date(2018, 1, 1), "quote")
    destination = sut.archive_path(tmp_path, item)
    destination.parent.mkdir(parents=True)
    with gzip.open(destination, "wb") as handle:
        handle.write(b"timestamp,symbol\n")

    with pytest.raises(sut.IntegrityError):
        sut.download_or_adopt(tmp_path, sut.DEFAULT_BASE_URL, item, None, False, 1)
    record = sut.download_or_adopt(tmp_path, sut.DEFAULT_BASE_URL, item, None, True, 1)
    assert record is not None
    assert record["origin"] == "ADOPTED_EXISTING"
    assert record["sha256"] == sut.sha256(destination)


def test_bound_existing_mismatch_is_not_silently_redownloaded(tmp_path: Path) -> None:
    item = sut.WorkItem(date(2018, 1, 1), "trade")
    destination = sut.archive_path(tmp_path, item)
    destination.parent.mkdir(parents=True)
    with gzip.open(destination, "wb") as handle:
        handle.write(b"one")
    record = {
        "bytes": destination.stat().st_size,
        "sha256": "0" * 64,
    }
    with pytest.raises(sut.IntegrityError):
        sut.download_or_adopt(tmp_path, sut.DEFAULT_BASE_URL, item, record, False, 1)
