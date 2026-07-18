from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "02. AlphaFactory" / "tools" / "cme_fx_options_inventory.py"


def load_module():
    spec = importlib.util.spec_from_file_location("cme_fx_options_inventory", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_empty_raw_directory_fails_closed(tmp_path: Path) -> None:
    module = load_module()
    raw = tmp_path / "raw"
    raw.mkdir()

    result = module.build_inventory(tmp_path)

    assert result["status"] == "MISSING_RAW_DATA"
    assert result["files"] == []
    assert result["contract"]["required_codes"] == [
        "EUVL",
        "EUUP",
        "EUDN",
        "EUSK",
        "EUAM",
        "EUCV",
    ]


def test_csv_inventory_hashes_profiles_and_passes_coverage(tmp_path: Path) -> None:
    module = load_module()
    raw = tmp_path / "raw"
    raw.mkdir()
    payload = (
        "trade_date,EUVL,EUUP,EUDN,EUSK,EUAM,EUCV\n"
        "2020-01-02,7.1,7.3,6.9,1.1,7.0,0.2\n"
        "2026-06-30,8.1,8.4,7.8,1.2,8.0,0.3\n"
    ).encode("utf-8")
    source = raw / "euvl_daily.csv"
    source.write_bytes(payload)
    (raw / "euro_fx_option_chain.csv").write_text(
        "trade_date,expiration,strike,option_type,settlement,volume,open_interest,implied_volatility\n"
        "2020-01-02,2020-03-13,1.1200,C,0.0041,120,540,0.071\n"
        "2026-06-30,2026-09-11,1.1800,P,0.0052,150,610,0.081\n",
        encoding="utf-8",
    )

    result = module.build_inventory(tmp_path)

    assert result["status"] == "CONTRACT_READY"
    cvol_file = next(item for item in result["files"] if item["path"].endswith("euvl_daily.csv"))
    assert cvol_file["sha256"] == hashlib.sha256(payload).hexdigest().upper()
    assert cvol_file["size_bytes"] == len(payload)
    cvol_profile = next(item for item in result["profiles"] if item["dataset_role"] == "cvol")
    assert cvol_profile["row_count"] == 2
    assert cvol_profile["coverage_from"] == "2020-01-02"
    assert cvol_profile["coverage_to"] == "2026-06-30"
    assert result["validation"]["required_codes_present"] is True
    assert result["validation"]["option_chain_schema_pass"] is True
    assert result["validation"]["cvol_coverage_pass"] is True
    assert result["validation"]["option_chain_coverage_pass"] is True


def test_missing_component_is_schema_incomplete(tmp_path: Path) -> None:
    module = load_module()
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "euvl_daily.csv").write_text(
        "trade_date,EUVL,EUSK\n2020-01-02,7.1,1.1\n2026-06-30,8.1,1.2\n",
        encoding="utf-8",
    )

    result = module.build_inventory(tmp_path)

    assert result["status"] == "SCHEMA_INCOMPLETE"
    assert result["validation"]["missing_codes"] == ["EUUP", "EUDN", "EUAM", "EUCV"]
    assert result["validation"]["missing_option_chain_fields"] == [
        "trade_date",
        "expiration",
        "strike",
        "option_type",
        "settlement",
        "volume",
        "open_interest",
        "implied_volatility",
    ]


def test_cli_writes_stable_json_manifest(tmp_path: Path) -> None:
    module = load_module()
    raw = tmp_path / "raw"
    raw.mkdir()
    out = tmp_path / "acquisition_manifest.json"

    exit_code = module.main(["--root", str(tmp_path), "--manifest", str(out)])

    assert exit_code == 2
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["schema_version"] == "cme_fx_options_inventory.v1"
    assert parsed["status"] == "MISSING_RAW_DATA"
