from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "audit_mql5_nonrepaint.py"
SPEC = importlib.util.spec_from_file_location("audit_mql5_nonrepaint", TOOL_PATH)
assert SPEC and SPEC.loader
AUDITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDITOR)


COLLECTION_SOURCE = """
void EmitSeriesProof()
  {
   long m5_first_epoch=0;
   ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE,"m5_first_epoch",m5_first_epoch);
   datetime copytime_values[];
   const datetime copytime_from=(datetime)m5_first_epoch;
   int copytime_result=CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values);
   int copytime_error=GetLastError();
   long copytime_first_epoch=(long)copytime_values[0];
   Print("DATA_EPOCH_D0_SERIES_PROOF");
   if(copytime_result!=1||copytime_first_epoch!=m5_first_epoch||copytime_error!=0)
      return;
  }
"""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fixture(
    tmp_path: Path,
    source_text: str = COLLECTION_SOURCE,
    *,
    authority: str = AUDITOR.COLLECTION_AUTHORITY,
    model: int = 0,
) -> tuple[Path, Path, Path]:
    run_dir = tmp_path / "run"
    snapshot_root = run_dir / "snapshot"
    snapshot_root.mkdir(parents=True)
    source = snapshot_root / "probe.mq5"
    source.write_text(source_text, encoding="utf-8")

    receipt_contract = {
        "history_quality": {"operator": "gt", "value": 97},
        "coverage_mode": "all_available_asof",
        "availability_asof_utc": "2026-07-30T23:59:59Z",
        "requested_from": "1970.01.01",
        "requested_to": "2026.07.30",
        "require_tester_journal_bounds": True,
    }
    binding = {
        "hypothesis_id": "HYP-COLLECTION-TEST",
        "ea_name": "EA_COLLECTION_TEST",
        "symbol": "XAUUSD",
        "period": "M5",
        "from": "1970.01.01",
        "to": "2026.07.30",
        "model": model,
        "run_role": "control",
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "telemetry_profile": "none",
        "telemetry_tier": "off",
        "broker_fingerprint": "A" * 64,
        "server_fingerprint": "B" * 64,
        "account_fingerprint": "C" * 64,
        "data_fingerprint": "D" * 64,
        "overrides": "InpCollectionOnly=true",
        "required_sidecars": [],
        "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
        "include_closure_sha256": hashlib.sha256(b"").hexdigest().upper(),
        "data_quality_contract": receipt_contract,
    }
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "authority": authority,
        "binding": binding,
        "evidence": [{"label": "source", "sha256": _sha(source)}],
    }
    receipt_path = run_dir / "receipt.json"
    _write_json(receipt_path, receipt)

    manifest = {
        **{key: value for key, value in binding.items() if key != "data_quality_contract"},
        "run_id": "RUN-COLLECTION-TEST",
        "snapshot_root": str(snapshot_root),
        "source_snapshot": str(source),
        "source_sha256": _sha(source),
        "include_snapshots": [],
        "contract_receipt_sha256": _sha(receipt_path),
        "contract_symbol_geometry": binding["symbol_geometry"],
        "includes_sha256": binding["include_closure_sha256"],
        "data_quality_contract": {
            "schema_version": "alphafactory_data_quality_contract.v1",
            "symbol": "XAUUSD",
            "requested_from": "1970.01.01",
            "requested_to": "2026.07.30",
            "history_quality_threshold": 97,
            "coverage_mode": "all_available_asof",
            "availability_asof_utc": "2026-07-30T23:59:59.0000000Z",
            "require_tester_journal_bounds": True,
            "max_journal_delta_bytes": 1048576,
        },
    }
    manifest_path = run_dir / "run_manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path, receipt_path, run_dir / "audit.json"


def test_collection_probe_requires_hash_bound_receipt(tmp_path: Path) -> None:
    manifest, receipt, output = _fixture(tmp_path)

    assert AUDITOR.run(manifest, output, receipt) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert result["collection_authority_verified"] is True
    assert [item["rule"] for item in result["allowed_new_bar_gates"]] == [
        "collection_first_date_copytime"
    ]

    assert AUDITOR.run(manifest, output, None) == 1
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["collection_authority_verified"] is False
    assert "unproven_closed_bar_shift" in {item["rule"] for item in result["findings"]}


def test_model4_collection_authority_requires_model4_binding(tmp_path: Path) -> None:
    manifest, receipt, output = _fixture(
        tmp_path,
        authority=AUDITOR.MODEL4_COLLECTION_AUTHORITY,
        model=4,
    )

    assert AUDITOR.run(manifest, output, receipt) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert result["collection_authority_verified"] is True

    manifest, receipt, output = _fixture(
        tmp_path / "old_on_model4",
        authority=AUDITOR.COLLECTION_AUTHORITY,
        model=4,
    )
    with pytest.raises(ValueError, match="collection-only"):
        AUDITOR.run(manifest, output, receipt)

    manifest, receipt, output = _fixture(
        tmp_path / "new_on_model0",
        authority=AUDITOR.MODEL4_COLLECTION_AUTHORITY,
        model=0,
    )
    with pytest.raises(ValueError, match="collection-only"):
        AUDITOR.run(manifest, output, receipt)


def test_collection_probe_rejects_tampered_or_wrong_source_receipt(tmp_path: Path) -> None:
    manifest, receipt, output = _fixture(tmp_path)
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    receipt_payload["binding"]["data_fingerprint"] = "E" * 64
    _write_json(receipt, receipt_payload)
    with pytest.raises(ValueError, match="receipt SHA256"):
        AUDITOR.run(manifest, output, receipt)

    manifest, receipt, output = _fixture(tmp_path / "other")
    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    receipt_payload["evidence"][0]["sha256"] = "F" * 64
    _write_json(receipt, receipt_payload)
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_payload["contract_receipt_sha256"] = _sha(receipt)
    _write_json(manifest, manifest_payload)
    with pytest.raises(ValueError, match="source SHA256"):
        AUDITOR.run(manifest, output, receipt)


def test_collection_authority_does_not_exempt_other_dynamic_series_reads(tmp_path: Path) -> None:
    source = COLLECTION_SOURCE + """
void OnTick()
  {
   int start_shift=2;
   MqlRates rates[];
   CopyRates(_Symbol,PERIOD_M5,start_shift,1,rates);
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 1
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["collection_authority_verified"] is True
    assert any(
        item["function"] == "CopyRates" and item["rule"] == "unproven_closed_bar_shift"
        for item in result["findings"]
    )


def test_collection_authority_does_not_exempt_a_second_copytime_call(tmp_path: Path) -> None:
    source = COLLECTION_SOURCE + """
void OtherRead()
  {
   datetime signal_values[];
   CopyTime(_Symbol,PERIOD_M5,copytime_from,999,signal_values);
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 1
    result = json.loads(output.read_text(encoding="utf-8"))
    assert any(
        item["function"] == "CopyTime" and item["rule"] == "unproven_closed_bar_shift"
        for item in result["findings"]
    )
