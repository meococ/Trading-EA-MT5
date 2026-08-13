import csv
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("analyze_qpf_002_source.py")
SPEC = importlib.util.spec_from_file_location("qpf_analyzer", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _write_report(path: Path) -> None:
    path.write_text(
        "History Quality:</td><td><b>99%</b>"
        "Ticks:</td><td><b>1000</b>"
        "Total Net Profit:</td><td><b>0.00</b>"
        "Total Trades:</td><td><b>0</b>",
        encoding="utf-8",
    )


def _rows():
    for year in MODULE.EXPECTED_YEARS:
        yield {
            "schema_version": MODULE.SCHEMA_VERSION,
            "hypothesis_id": MODULE.HYPOTHESIS_ID,
            "run_id": "RUN1",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "bucket_start_server": f"{year}.01.02 00:00:00",
            "bucket_end_server": f"{year}.01.02 00:05:00",
            "total_ticks": "100",
            "valid_quotes": "100",
            "invalid_quotes": "0",
            "invalid_time": "0",
            "reverse_time_msc": "0",
            "exact_duplicate_quotes": "2",
            "quote_changes": "98",
            "bid_only_changes": "5",
            "ask_only_changes": "5",
            "both_changes": "88",
            "spread_changes": "2",
            "bar_complete": "true",
            "orders_sent": "0",
            "promotion_eligible": "false",
        }


def _write_fixture(tmp_path: Path):
    csv_path = tmp_path / "EURUSD_QuotePathFidelity_RUN1.csv"
    rows = list(_rows())
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = tmp_path / "report.html"
    _write_report(report)
    manifest = tmp_path / "run_manifest.json"
    csv_hash = MODULE.sha256(csv_path)
    manifest.write_text(json.dumps({
        "hypothesis_id": MODULE.HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": "EA_QuotePathFidelityProbe",
        "symbol": "EURUSD",
        "period": "M1",
        "from": "2018.01.01",
        "to": "2026.08.01",
        "model": 0,
        "telemetry_tier": "off",
        "telemetry_profile": "none",
        "required_sidecars": ["*_QuotePathFidelity_*.csv"],
        "sidecars": [{"path": f"logs/{csv_path.name}", "sha256": csv_hash}],
    }), encoding="utf-8")
    return csv_path, report, manifest


def test_passes_source_only_fixture(tmp_path):
    csv_path, report, manifest = _write_fixture(tmp_path)
    result = MODULE.analyze(csv_path, report, manifest)
    assert result["verdict"].startswith("PASS_QUOTE_PATH_FIDELITY")
    assert result["economics_authorized"] is False
    assert result["promotion_authorized"] is False


def test_rejects_forbidden_economic_column(tmp_path):
    csv_path, report, manifest = _write_fixture(tmp_path)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    rows[0]["pnl"] = "1"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    try:
        MODULE.analyze(csv_path, report, manifest)
    except ValueError as exc:
        assert "forbidden economic columns" in str(exc)
    else:
        raise AssertionError("economic column was accepted")


def test_fails_year_gate_independently(tmp_path):
    csv_path, report, manifest = _write_fixture(tmp_path)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    rows[0]["bid_only_changes"] = "0"
    rows[0]["ask_only_changes"] = "0"
    rows[0]["both_changes"] = "98"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_data["sidecars"][0]["sha256"] = MODULE.sha256(csv_path)
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
    result = MODULE.analyze(csv_path, report, manifest)
    assert result["verdict"].startswith("KILL_QUOTE_PATH_FIDELITY")
    assert result["yearly_gates"]["2018"]["one_sided_update_share_ge_0_05"] is False


def test_rejects_second_matching_qpf_sidecar(tmp_path):
    csv_path, report, manifest = _write_fixture(tmp_path)
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_data["sidecars"].append({
        "path": "logs/EURUSD_QuotePathFidelity_SECOND.csv",
        "sha256": "A" * 64,
    })
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")
    result = MODULE.analyze(csv_path, report, manifest)
    assert result["verdict"] == "ENGINEERING_INVALID_NO_SOURCE_VERDICT"
    assert "manifest exact-one QPF sidecar" in result["identity_errors"]
