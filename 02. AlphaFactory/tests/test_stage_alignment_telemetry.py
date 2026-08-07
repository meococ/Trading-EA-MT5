from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "analyze_stage_alignment_telemetry.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("stage_alignment", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_analyzer_is_outcome_blind_and_streaming() -> None:
    text = TOOL_PATH.read_text(encoding="utf-8")
    assert "csv.DictReader" in text
    assert "Raw\nrows are never retained" in text
    assert '"outcomes_observed": False' in text
    assert '"claim_edge": False' in text
    assert '"optimize": False' in text
    assert "availability_price" in text
    assert "selected_route" in text


def test_age_buckets_are_frozen() -> None:
    tool = load_tool()
    assert tool.age_bucket(-1) == "missing"
    assert tool.age_bucket(0) == "0"
    assert tool.age_bucket(2) == "1-2"
    assert tool.age_bucket(5) == "3-5"
    assert tool.age_bucket(10) == "6-10"
    assert tool.age_bucket(20) == "11-20"


def test_forbidden_header_is_rejected(tmp_path: Path) -> None:
    tool = load_tool()
    headers = [f"field_{i}" for i in range(tool.EXPECTED_FIELDS - 1)] + ["outcome"]
    csv_path = tmp_path / "bad.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
    run_meta = tmp_path / "meta.json"
    manifest = tmp_path / "manifest.json"
    run_meta.write_text(json.dumps({}), encoding="utf-8")
    manifest.write_text(json.dumps({}), encoding="utf-8")
    try:
        tool.analyze(csv_path, run_meta, manifest, 1024 * 1024, 10)
    except ValueError as exc:
        assert "forbidden outcome/route headers" in str(exc)
    else:
        raise AssertionError("forbidden header was accepted")
