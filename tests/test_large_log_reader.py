from __future__ import annotations

import importlib.util
import json
import tracemalloc
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "02. AlphaFactory" / "tools" / "large_log_reader.py"
SPEC = importlib.util.spec_from_file_location("large_log_reader", MODULE_PATH)
assert SPEC and SPEC.loader
large_log_reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(large_log_reader)


def test_inspect_is_hash_bound_and_bounded(tmp_path: Path) -> None:
    source = tmp_path / "tester.log"
    source.write_text(
        "header\n"
        "ok 1\n"
        "warning spread widened\n"
        "ok 2\n"
        "fatal order rejected\n"
        "tail\n",
        encoding="utf-8",
    )
    result = large_log_reader.inspect_log(
        source,
        head_count=2,
        tail_count=2,
        patterns=large_log_reader.parse_patterns(None),
        max_samples_per_pattern=1,
        max_chars=80,
    )
    assert result["source"]["line_count"] == 6
    assert result["source"]["sha256"] == large_log_reader.sha256_file(source)
    assert [item["line"] for item in result["head"]] == [1, 2]
    assert [item["line"] for item in result["tail"]] == [5, 6]
    counts = {item["name"]: item["count"] for item in result["patterns"]}
    assert counts["warning"] == 1
    assert counts["fatal"] == 1
    assert counts["rejected"] == 1
    assert all(len(item["samples"]) <= 1 for item in result["patterns"])


def test_search_context_and_match_output_are_capped(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    source.write_text("\n".join(f"row {i} {'ERROR' if i in (3, 7, 9) else 'ok'}" for i in range(1, 12)) + "\n")
    result = large_log_reader.search_log(source, r"ERROR", context=1, max_matches=2, max_chars=80)
    assert result["total_matches"] == 3
    assert result["stored_matches"] == 2
    assert result["truncated"] is True
    assert [block["match_line"] for block in result["matches"]] == [3, 7]
    assert [line["line"] for line in result["matches"][0]["lines"]] == [2, 3, 4]


def test_window_enforces_hard_output_limit(tmp_path: Path) -> None:
    source = tmp_path / "rows.log"
    source.write_text("\n".join(f"line {i}" for i in range(1, 1001)) + "\n")
    result = large_log_reader.read_window(source, start=500, count=5)
    assert [item["line"] for item in result["lines"]] == [500, 501, 502, 503, 504]
    with pytest.raises(ValueError, match="between 1 and 500"):
        large_log_reader.read_window(source, start=1, count=501)


def test_cli_writes_artifact_without_dumping_log(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "cli.log"
    source.write_text("ok\nERROR bounded\ntail\n", encoding="utf-8")
    output = tmp_path / "index.json"
    assert large_log_reader.main(["inspect", str(source), "--out", str(output), "--head", "1", "--tail", "1"]) == 0
    stdout = capsys.readouterr().out
    assert stdout.startswith("LARGE_LOG_ARTIFACT_CREATED")
    assert "ERROR bounded" not in stdout
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source"]["line_count"] == 3

    window_output = tmp_path / "window.json"
    assert large_log_reader.main(["window", str(source), "--start", "2", "--count", "1", "--out", str(window_output)]) == 0
    window_payload = json.loads(window_output.read_text(encoding="utf-8"))
    assert window_payload["source"]["sha256"] == large_log_reader.sha256_file(source)


def test_one_million_lines_use_bounded_memory(tmp_path: Path) -> None:
    source = tmp_path / "million.log"
    with source.open("w", encoding="utf-8", newline="\n") as handle:
        for index in range(1_000_000):
            marker = " ERROR" if index in (123, 999_999) else ""
            handle.write(f"{index:07d},EURUSD,M15,ok{marker}\n")

    tracemalloc.start()
    result = large_log_reader.inspect_log(
        source,
        head_count=3,
        tail_count=3,
        patterns=[("error", r"ERROR")],
        max_samples_per_pattern=2,
        max_chars=100,
    )
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert result["source"]["line_count"] == 1_000_000
    assert result["patterns"][0]["count"] == 2
    assert len(result["head"]) == 3
    assert len(result["tail"]) == 3
    assert peak < 16 * 1024 * 1024
