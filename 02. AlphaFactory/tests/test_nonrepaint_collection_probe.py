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
    data_quality_contract: bool = True,
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
        "data_quality_contract": (
            {
                "schema_version": "alphafactory_data_quality_contract.v1",
                "symbol": "XAUUSD",
                "requested_from": "1970.01.01",
                "requested_to": "2026.07.30",
                "history_quality_threshold": 97,
                "coverage_mode": "all_available_asof",
                "availability_asof_utc": "2026-07-30T23:59:59.0000000Z",
                "require_tester_journal_bounds": True,
                "max_journal_delta_bytes": 1048576,
            }
            if data_quality_contract
            else None
        ),
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

    # Without a receipt the collection authority is unverified, but the probe
    # is still allowed because the manifest's data-quality contract mandates
    # the emitted DATA_EPOCH_D0_SERIES_PROOF line in every governed run.
    assert AUDITOR.run(manifest, output, None) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["collection_authority_verified"] is False
    assert [item["rule"] for item in result["allowed_new_bar_gates"]] == [
        "collection_first_date_copytime"
    ]


def test_probe_rejected_when_no_receipt_and_no_data_quality_contract(
    tmp_path: Path,
) -> None:
    manifest, receipt, output = _fixture(tmp_path, data_quality_contract=False)

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


def test_probe_allowed_when_trade_calls_live_in_other_functions(tmp_path: Path) -> None:
    # Governed trading EAs necessarily call CTrade/PositionClose elsewhere in
    # the file; the no-trade guarantee is scoped to the probe's own function.
    source = """
CTrade g_trade;
""" + COLLECTION_SOURCE + """
void CloseAll()
  {
   g_trade.PositionClose(123);
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert [item["rule"] for item in result["allowed_new_bar_gates"]] == [
        "collection_first_date_copytime"
    ]


def test_probe_rejected_when_trade_calls_share_the_probe_function(
    tmp_path: Path,
) -> None:
    source = """
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
   OrderSend(request,result);
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 1
    result = json.loads(output.read_text(encoding="utf-8"))
    assert "unproven_closed_bar_shift" in {item["rule"] for item in result["findings"]}


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


def test_itime_zero_is_timestamp_only_read(tmp_path: Path) -> None:
    source = COLLECTION_SOURCE + """
void Edge()
  {
   const datetime bar0=iTime(_Symbol,PERIOD_M5,0);
   if(bar0!=g_last){ g_last=bar0; }
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert any(
        item["rule"] == "iTime_zero"
        and item["disposition"] == "allowed_timestamp_only_read"
        for item in result["allowed_new_bar_gates"]
    )


def test_guarded_shift_param_is_allowed(tmp_path: Path) -> None:
    source = COLLECTION_SOURCE + """
bool BarAt(const int shift)
  {
   if(shift<1)
      return(false);
   MqlRates r[];
   if(CopyRates(_Symbol,PERIOD_M5,shift,1,r)!=1)
      return(false);
   return(true);
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert any(
        item["rule"] == "unproven_closed_bar_shift"
        and item["disposition"] == "allowed_guarded_shift_param"
        for item in result["allowed_new_bar_gates"]
    )


def test_unguarded_shift_param_is_still_a_finding(tmp_path: Path) -> None:
    source = COLLECTION_SOURCE + """
bool BarAt(const int shift)
  {
   if(shift<0)
      return(false);
   MqlRates r[];
   if(CopyRates(_Symbol,PERIOD_M5,shift,1,r)!=1)
      return(false);
   return(true);
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 1
    result = json.loads(output.read_text(encoding="utf-8"))
    assert any(
        item["rule"] == "unproven_closed_bar_shift"
        and item["shift_expression"] == "shift"
        for item in result["findings"]
    )


def test_bounded_datetime_range_is_allowed(tmp_path: Path) -> None:
    source = COLLECTION_SOURCE + """
int RangeHL(const datetime from,const datetime to)
  {
   if(from<=0 || to<from)
      return(0);
   const datetime last_closed_open=iTime(_Symbol,PERIOD_M5,1);
   datetime to_eff=to;
   if(to_eff>last_closed_open)
      to_eff=last_closed_open;
   MqlRates rates[];
   const int copied=CopyRates(_Symbol,PERIOD_M5,from,to_eff,rates);
   return(copied);
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert any(
        item["rule"] == "unproven_closed_bar_shift"
        and item["disposition"] == "allowed_bounded_datetime_range"
        for item in result["allowed_new_bar_gates"]
    )


def test_unbounded_datetime_range_is_still_a_finding(tmp_path: Path) -> None:
    source = COLLECTION_SOURCE + """
int RangeHL(const datetime from,const datetime to)
  {
   MqlRates rates[];
   const int copied=CopyRates(_Symbol,PERIOD_M5,from,to,rates);
   return(copied);
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 1
    result = json.loads(output.read_text(encoding="utf-8"))
    assert any(
        item["rule"] == "unproven_closed_bar_shift"
        and item["shift_expression"] == "from"
        for item in result["findings"]
    )

def test_for_loop_shift_is_allowed(tmp_path: Path) -> None:
    source = COLLECTION_SOURCE + """
int Nr4Check()
  {
   const double r2=iHigh(_Symbol,_Period,2)-iLow(_Symbol,_Period,2);
   if(r2<=0.0)
      return(0);
   for(int k=3;k<=1+4;k++)
     {
      const double rk=iHigh(_Symbol,_Period,k)-iLow(_Symbol,_Period,k);
      if(rk<=0.0 || rk<r2)
         return(0);
     }
   return(1);
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert any(
        item["rule"] == "unproven_closed_bar_shift"
        and item["disposition"] == "allowed_for_loop_shift"
        for item in result["allowed_new_bar_gates"]
    )


def test_for_loop_shift_reassigned_in_body_is_a_finding(tmp_path: Path) -> None:
    source = COLLECTION_SOURCE + """
int Bad()
  {
   for(int k=3;k<=5;k++)
     {
      k=0;
      const double rk=iHigh(_Symbol,_Period,k);
      if(rk<=0.0)
         return(0);
     }
   return(1);
  }
"""
    manifest, receipt, output = _fixture(tmp_path, source)

    assert AUDITOR.run(manifest, output, receipt) == 1
    result = json.loads(output.read_text(encoding="utf-8"))
    assert any(
        item["rule"] == "unproven_closed_bar_shift"
        and item["shift_expression"] == "k"
        for item in result["findings"]
    )
