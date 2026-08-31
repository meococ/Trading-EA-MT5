import hashlib
import importlib.util
import csv
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "tools" / "execution_data_foundation.py"
SPEC = importlib.util.spec_from_file_location("execution_data_foundation", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_partial_artifact_is_still_integrity_checked(tmp_path):
    artifact = tmp_path / "quotes.csv"
    artifact.write_text("header\n", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest().upper()
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")

    resolved = MODULE.resolve_artifact(
        {"status": "PARTIAL", "path": artifact.name, "sha256": digest},
        manifest,
        "EURUSD.quote_ticks",
    )

    assert resolved == artifact.resolve()


def test_missing_artifact_has_no_file_to_validate(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")

    assert MODULE.resolve_artifact(
        {"status": "MISSING", "path": "", "sha256": ""},
        manifest,
        "EURUSD.commission_lifecycles",
    ) is None


def test_quote_rows_must_be_unique_in_time(tmp_path):
    artifact = tmp_path / "quotes.csv"
    fields = sorted(MODULE.TICK_FIELDS)
    row = {
        "ask": "1.10002",
        "bid": "1.10000",
        "flags": "2",
        "last": "0",
        "symbol": "EURUSD",
        "time_msc": "1800000000000",
        "time_utc": "2027-01-15T08:00:00Z",
        "volume_real": "0",
    }
    with artifact.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(row)
        writer.writerow(row)

    with pytest.raises(ValueError, match="strictly monotonic"):
        MODULE.validate_ticks(
            artifact,
            {"row_count": 2},
            "EURUSD",
        )
