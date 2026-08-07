from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]
TOOL = ALPHA_ROOT / "tools" / "large_log_reader.py"


def run_reader(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ALPHA_ROOT.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_small_inspect_keeps_full_sha256_by_default(tmp_path: Path) -> None:
    source = tmp_path / "small.log"
    source.write_text("alpha\nwarning one\nomega\n", encoding="utf-8")
    out = tmp_path / "index.json"

    result = run_reader("inspect", str(source), "--out", str(out))

    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["source"]["sha256_status"] == "computed_full"
    assert payload["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert payload["bounds"]["scan_truncated"] is False
    assert "sha256_status=computed_full" in result.stdout


def test_large_inspect_omits_full_sha_and_stops_at_byte_bound(tmp_path: Path) -> None:
    source = tmp_path / "huge.log"
    source.write_bytes(b"first line\nwarning early\n")
    with source.open("ab") as handle:
        handle.truncate(1024 * 1024 + 123)
    out = tmp_path / "huge-index.json"

    result = run_reader(
        "inspect",
        str(source),
        "--out",
        str(out),
        "--max-bytes",
        "32",
        "--max-full-sha-bytes",
        "64",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["source"]["sha256"] is None
    assert payload["source"]["sha256_status"] == "omitted_by_size"
    assert payload["source"]["bounded_fingerprint"]["value"]
    assert payload["bounds"]["scan_truncated"] is True
    assert payload["bounds"]["scan_end_byte"] == 32
    assert "sha256_status=omitted_by_size" in result.stdout


def test_window_can_read_from_byte_range_without_full_sha(tmp_path: Path) -> None:
    source = tmp_path / "range.log"
    source.write_bytes(b"skip me\nstart here\nerror in range\nend\n")
    out = tmp_path / "window.json"

    result = run_reader(
        "window",
        str(source),
        "--start",
        "1",
        "--count",
        "2",
        "--start-byte",
        "7",
        "--max-bytes",
        "24",
        "--max-full-sha-bytes",
        "8",
        "--out",
        str(out),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["source"]["sha256_status"] == "omitted_by_size"
    assert payload["request"]["scan_truncated"] is True
    assert payload["returned"] == 2
    assert payload["lines"][0]["text"] == "start here"


def test_utf16_window_recovers_from_odd_midline_byte_offset(tmp_path: Path) -> None:
    source = tmp_path / "mt5-journal.log"
    source.write_text(
        "header row\npartial row must be skipped\nerror in bounded tail\nomega\n",
        encoding="utf-16",
    )
    out = tmp_path / "utf16-window.json"
    raw = source.read_bytes()
    partial = "partial row".encode("utf-16-le")
    odd_offset = raw.index(partial) + 3

    result = run_reader(
        "window",
        str(source),
        "--start",
        "1",
        "--count",
        "2",
        "--start-byte",
        str(odd_offset),
        "--max-bytes",
        "128",
        "--max-full-sha-bytes",
        "8",
        "--out",
        str(out),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["source"]["encoding"] == "utf-16-le"
    assert payload["returned"] == 2
    assert payload["lines"][0]["text"] == "error in bounded tail"
    assert payload["lines"][1]["text"] == "omega"


def test_utf16_bounded_scan_never_reads_past_requested_window(tmp_path: Path) -> None:
    source = tmp_path / "bounded.log"
    source.write_text("discard me\ninside\noutside marker\n", encoding="utf-16")
    raw = source.read_bytes()
    start = raw.index("discard".encode("utf-16-le")) + 1
    end_before_outside = raw.index("outside".encode("utf-16-le"))
    out = tmp_path / "bounded-index.json"

    result = run_reader(
        "inspect",
        str(source),
        "--start-byte",
        str(start),
        "--max-bytes",
        str(end_before_outside - start),
        "--pattern",
        "outside=outside marker",
        "--max-full-sha-bytes",
        "8",
        "--out",
        str(out),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["patterns"][0]["count"] == 0
