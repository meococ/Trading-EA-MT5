from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
ALPHA = ALPHA_ROOT / "alpha.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


HELPERS = [
    "Test-PathSafe",
    "Get-Mt5ReportHtml",
    "Get-Sha256Required",
    "Get-TextSha256",
    "Get-ObjectPropertyValue",
    "ConvertTo-ResearchDate",
    "ConvertTo-FiniteInvariantDouble",
    "Resolve-DataQualityContract",
    "Get-Mt5JournalLogFiles",
    "New-Mt5JournalLogSnapshot",
    "ConvertFrom-Mt5LogBytes",
    "Export-Mt5JournalLogDelta",
    "Get-DataQualityHistoryRange",
    "Get-DataQualitySeriesProof",
    "Get-ReportLabeledValue",
    "Assert-DataQualityRunEvidence",
]


def series_proof_line(actual_from: str, *, server_first: str | None = None) -> str:
    first = datetime.strptime(actual_from, "%Y.%m.%d").replace(tzinfo=timezone.utc)
    server = datetime.strptime(server_first or actual_from, "%Y.%m.%d").replace(tzinfo=timezone.utc)
    first_epoch = int(first.timestamp())
    server_epoch = int(server.timestamp())
    return (
        "DATA_EPOCH_D0_SERIES_PROOF symbol=EURUSD m5_synchronized=1 "
        f"m5_first_epoch={first_epoch} m5_terminal_first_epoch={first_epoch} "
        f"m1_server_first_epoch={server_epoch} m1_terminal_first_epoch={server_epoch} "
        "m5_bars=100001 terminal_maxbars=100000 "
        f"copytime_from_epoch={first_epoch} copytime_count=1 copytime_result=1 "
        f"copytime_first_epoch={first_epoch} copytime_last_error=0"
    )


def run_ps(tmp_path: Path, body: str, *args: str) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL, "PowerShell is required"
    script = tmp_path / "harness.ps1"
    helper_literal = "@(" + ",".join("'" + name + "'" for name in HELPERS) + ")"
    args_json = json.dumps(list(args))
    script.write_text(
        rf"""
$ErrorActionPreference = 'Stop'
$alpha = '{str(ALPHA)}'
$ArgsPassthrough = ConvertFrom-Json @'
{args_json}
'@
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($alpha, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) {{ throw ($parseErrors | ForEach-Object {{ $_.Message }} | Out-String) }}
$needed = {helper_literal}
foreach ($name in $needed) {{
    $fn = $ast.Find({{ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }}, $true)
    if ($null -eq $fn) {{ throw "Missing function $name" }}
    Invoke-Expression $fn.Extent.Text
}}
{body}
""",
        encoding="utf-8",
    )
    return subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_report(path: Path, history_quality: str) -> Path:
    path.write_text(
        f"""
<html><body>
<table>
<tr><td>History Quality:</td><td><b>{history_quality}</b></td></tr>
</table>
</body></html>
""",
        encoding="utf-8",
    )
    return path


def write_manifest(
    tmp_path: Path,
    *,
    history_quality: str = "100%",
    journal_text: str = "EURUSD: history synchronized from 2021.02.01 to 2024.12.31\n",
    requested_from: str = "1970.01.01",
    requested_to: str = "2024.12.31",
    threshold: float = 97.0,
) -> Path:
    run_dir = tmp_path / "run"
    logs = run_dir / "logs"
    logs.mkdir(parents=True)
    report = write_report(run_dir / "report.html", history_quality)
    journal = logs / "tester_journal_delta.log"
    if journal_text and "DATA_EPOCH_D0_SERIES_PROOF" not in journal_text:
        match = re.search(r"history synchronized from (\d{4}\.\d{2}\.\d{2})", journal_text)
        if match:
            try:
                journal_text = journal_text.rstrip() + "\n" + series_proof_line(match.group(1)) + "\n"
            except ValueError:
                pass
    journal.write_text(journal_text, encoding="utf-8")
    manifest = {
        "local_run_dir": str(run_dir),
        "report_path": str(report),
        "from": requested_from,
        "to": requested_to,
        "data_quality_contract": {
            "symbol": "EURUSD",
            "requested_from": requested_from,
            "requested_to": requested_to,
            "history_quality_threshold": threshold,
            "max_journal_delta_bytes": 4096,
        },
        "data_quality_journal_delta": {
            "path": "logs/tester_journal_delta.log",
            "sha256": sha(journal),
            "bytes_read": len(journal.read_bytes()),
            "files_read": 1,
            "truncated": False,
        },
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def validate_manifest(tmp_path: Path, manifest: Path) -> subprocess.CompletedProcess[str]:
    return run_ps(
        tmp_path,
        r"""
$manifest = Get-Content -LiteralPath $ArgsPassthrough[0] -Raw | ConvertFrom-Json
$result = Assert-DataQualityRunEvidence $manifest
$result | ConvertTo-Json -Depth 12
""",
        str(manifest),
    )


def test_history_quality_100_passes_and_binds_evidence(tmp_path: Path) -> None:
    result = validate_manifest(tmp_path, write_manifest(tmp_path, history_quality="100%"))
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["history_quality"] == 100.0
    assert payload["actual_from"] == "2021.02.01"
    assert payload["actual_to"] == "2024.12.31"
    assert payload["coverage_class"] == "BROKER_LIMITED_START"
    assert payload["exact_match_count"] == 1
    assert payload["distinct_range_count"] == 1


def test_history_quality_threshold_is_strict(tmp_path: Path) -> None:
    for value in ("97%", "96.9%"):
        case_dir = tmp_path / value.replace("%", "").replace(".", "_")
        result = validate_manifest(case_dir, write_manifest(case_dir, history_quality=value))
        assert result.returncode != 0
        assert "History Quality" in result.stderr


def test_malformed_history_quality_fails(tmp_path: Path) -> None:
    result = validate_manifest(tmp_path, write_manifest(tmp_path, history_quality="not-a-number"))
    assert result.returncode != 0
    assert "finite invariant-culture number" in result.stderr


def test_missing_ambiguous_and_wrong_symbol_journal_fail(tmp_path: Path) -> None:
    cases = {
        "missing": ("", "positive files_read and bytes_read"),
        "ambiguous": (
            "\n".join(
                [
                    "EURUSD: history synchronized from 2021.02.01 to 2024.12.31",
                    "EURUSD: history synchronized from 2021.03.01 to 2024.12.31",
                ]
            ),
            "history synchronization",
        ),
        "wrong": (
            "GBPUSD: history synchronized from 2021.02.01 to 2024.12.31",
            "history synchronization",
        ),
    }
    for name, (text, expected) in cases.items():
        case_dir = tmp_path / name
        result = validate_manifest(case_dir, write_manifest(case_dir, journal_text=text))
        assert result.returncode != 0
        assert expected in result.stderr


def test_end_short_fails_and_broker_declared_later_start_is_accepted(tmp_path: Path) -> None:
    short = validate_manifest(
        tmp_path / "short",
        write_manifest(
            tmp_path / "short",
            journal_text="EURUSD: history synchronized from 2023.01.01 to 2024.12.30\n",
        ),
    )
    assert short.returncode != 0
    assert "ends before requested_to" in short.stderr

    later_start = validate_manifest(
        tmp_path / "later_start",
        write_manifest(
            tmp_path / "later_start",
            journal_text="EURUSD: history synchronized from 2023.01.01 to 2024.12.31\n",
        ),
    )
    assert later_start.returncode == 0, later_start.stdout + later_start.stderr


def test_second_source_distinguishes_full_broker_limited_and_truncated_cache(tmp_path: Path) -> None:
    full = validate_manifest(
        tmp_path / "full",
        write_manifest(
            tmp_path / "full",
            journal_text="EURUSD: history synchronized from 2017.01.02 to 2024.12.31\n",
        ),
    )
    assert full.returncode == 0, full.stdout + full.stderr
    assert json.loads(full.stdout)["coverage_class"] == "FULL_2018_PLUS"

    truncated_text = (
        "EURUSD: history synchronized from 2023.01.01 to 2024.12.31\n"
        + series_proof_line("2023.01.01", server_first="2017.01.02")
        + "\n"
    )
    truncated = validate_manifest(
        tmp_path / "truncated_cache",
        write_manifest(tmp_path / "truncated_cache", journal_text=truncated_text),
    )
    assert truncated.returncode != 0
    assert "INVALID_TRUNCATED_TERMINAL_CACHE" in truncated.stderr


def test_copytime_request_must_start_at_the_reported_first_m5_bar(tmp_path: Path) -> None:
    valid = (
        "EURUSD: history synchronized from 2021.02.01 to 2024.12.31\n"
        + series_proof_line("2021.02.01")
        + "\n"
    )
    invalid = valid.replace("copytime_from_epoch=1612137600", "copytime_from_epoch=0")
    result = validate_manifest(
        tmp_path / "wrong_copytime_start",
        write_manifest(tmp_path / "wrong_copytime_start", journal_text=invalid),
    )
    assert result.returncode != 0
    assert "INVALID_TRUNCATED_TERMINAL_CACHE" in result.stderr


def test_identical_duplicate_range_is_accepted_deterministically(tmp_path: Path) -> None:
    manifest = write_manifest(
        tmp_path,
        journal_text="\n".join(
            [
                "EURUSD: history synchronized from 2021.02.01 to 2024.12.31",
                "EURUSD: history synchronized from 2021.02.01 to 2024.12.31",
            ]
        ),
    )
    result = validate_manifest(tmp_path, manifest)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["exact_match_count"] == 2
    assert payload["distinct_range_count"] == 1


def test_history_start_is_a_real_date_and_not_after_end(tmp_path: Path) -> None:
    for name, history_line, expected in (
        (
            "invalid_start",
            "EURUSD: history synchronized from 2024.99.99 to 2024.12.31\n",
            "journal actual_from must use a real yyyy.MM.dd date",
        ),
        (
            "reversed",
            "EURUSD: history synchronized from 2025.01.01 to 2024.12.31\n",
            "actual_from must not be later than actual_to",
        ),
    ):
        case_dir = tmp_path / name
        result = validate_manifest(case_dir, write_manifest(case_dir, journal_text=history_line))
        assert result.returncode != 0
        assert expected in result.stderr


def test_contract_range_mismatch_and_legacy_no_contract_path(tmp_path: Path) -> None:
    mismatch_path = write_manifest(tmp_path / "mismatch", requested_to="2024.12.31")
    payload = json.loads(mismatch_path.read_text(encoding="utf-8"))
    payload["to"] = "2024.12.30"
    mismatch_path.write_text(json.dumps(payload), encoding="utf-8")
    mismatch = validate_manifest(tmp_path / "mismatch", mismatch_path)
    assert mismatch.returncode != 0
    assert "must match run manifest" in mismatch.stderr

    legacy_path = write_manifest(tmp_path / "legacy")
    legacy_payload = json.loads(legacy_path.read_text(encoding="utf-8"))
    legacy_payload.pop("data_quality_contract")
    legacy_payload.pop("data_quality_journal_delta")
    legacy_path.write_text(json.dumps(legacy_payload), encoding="utf-8")
    legacy = validate_manifest(tmp_path / "legacy", legacy_path)
    assert legacy.returncode == 0, legacy.stdout + legacy.stderr
    assert legacy.stdout.strip() == ""


def test_journal_path_truncation_and_empty_capture_fail_closed(tmp_path: Path) -> None:
    escaped = write_manifest(tmp_path / "escaped")
    escaped_payload = json.loads(escaped.read_text(encoding="utf-8"))
    outside = escaped.parent / "outside.log"
    outside.write_text("EURUSD: history synchronized from 2021.02.01 to 2024.12.31\n", encoding="utf-8")
    escaped_payload["data_quality_journal_delta"].update(
        {"path": "../outside.log", "sha256": sha(outside), "bytes_read": outside.stat().st_size}
    )
    escaped.write_text(json.dumps(escaped_payload), encoding="utf-8")
    result = validate_manifest(tmp_path / "escaped", escaped)
    assert result.returncode != 0
    assert "fixed run-local path" in result.stderr

    for name, mutation, expected in (
        ("truncated", {"truncated": True}, "present and complete"),
        ("empty", {"bytes_read": 0, "files_read": 0}, "positive files_read and bytes_read"),
    ):
        manifest = write_manifest(tmp_path / name)
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["data_quality_journal_delta"].update(mutation)
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        result = validate_manifest(tmp_path / name, manifest)
        assert result.returncode != 0
        assert expected in result.stderr


def test_resolve_receipt_contract_defensive_validation(tmp_path: Path) -> None:
    receipt = {
        "binding": {
            "data_quality_contract": {
                "history_quality": {"operator": "gt", "value": 97.0},
                "coverage_mode": "all_available_asof",
                "availability_asof_utc": "2024-12-31T23:59:59Z",
                "requested_from": "1970.01.01",
                "requested_to": "2024.12.31",
                "require_tester_journal_bounds": True,
            }
        }
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    result = run_ps(
        tmp_path,
        r"""
$receipt = Get-Content -LiteralPath $ArgsPassthrough[0] -Raw | ConvertFrom-Json
$binding = [pscustomobject]@{ symbol = 'EURUSD'; from = '1970.01.01'; to = '2024.12.31' }
Resolve-DataQualityContract $receipt $binding | ConvertTo-Json -Depth 8
""",
        str(receipt_path),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["history_quality_threshold"] == 97.0
    assert json.loads(result.stdout)["symbol"] == "EURUSD"

    receipt["binding"]["data_quality_contract"]["requested_to"] = "2024.12.30"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    result = run_ps(
        tmp_path,
        r"""
$receipt = Get-Content -LiteralPath $ArgsPassthrough[0] -Raw | ConvertFrom-Json
$binding = [pscustomobject]@{ symbol = 'EURUSD'; from = '1970.01.01'; to = '2024.12.31' }
Resolve-DataQualityContract $receipt $binding | ConvertTo-Json -Depth 8
""",
        str(receipt_path),
    )
    assert result.returncode != 0
    assert "requested_from/requested_to" in result.stderr

    receipt["binding"]["data_quality_contract"]["requested_to"] = "2024.12.31"
    receipt["binding"]["data_quality_contract"]["symbol"] = "EURUSD"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    result = run_ps(
        tmp_path,
        r"""
$receipt = Get-Content -LiteralPath $ArgsPassthrough[0] -Raw | ConvertFrom-Json
$binding = [pscustomobject]@{ symbol = 'EURUSD'; from = '1970.01.01'; to = '2024.12.31' }
Resolve-DataQualityContract $receipt $binding | ConvertTo-Json -Depth 8
""",
        str(receipt_path),
    )
    assert result.returncode != 0
    assert "must contain exactly" in result.stderr


def test_resolve_receipt_contract_rejects_weaker_or_malformed_contracts(tmp_path: Path) -> None:
    base = {
        "binding": {
            "data_quality_contract": {
                "history_quality": {"operator": "gt", "value": 97.0},
                "coverage_mode": "all_available_asof",
                "availability_asof_utc": "2024-12-31T23:59:59Z",
                "requested_from": "1970.01.01",
                "requested_to": "2024.12.31",
                "require_tester_journal_bounds": True,
            }
        }
    }
    cases = {
        "low_threshold": (lambda value: value["binding"]["data_quality_contract"]["history_quality"].update({"value": 96.9}), ">= 97"),
        "bad_mode": (lambda value: value["binding"]["data_quality_contract"].update({"coverage_mode": "broker_history_sync"}), "must be 'all_available_asof'"),
        "non_z": (lambda value: value["binding"]["data_quality_contract"].update({"availability_asof_utc": "2024-12-31T23:59:59+00:00"}), "valid Z timestamp"),
        "asof_mismatch": (lambda value: value["binding"]["data_quality_contract"].update({"availability_asof_utc": "2024-12-30T23:59:59Z"}), "UTC calendar date"),
        "string_bool": (lambda value: value["binding"]["data_quality_contract"].update({"require_tester_journal_bounds": "true"}), "must be true"),
    }
    for name, (mutate, expected) in cases.items():
        receipt = json.loads(json.dumps(base))
        mutate(receipt)
        case_dir = tmp_path / name
        case_dir.mkdir(parents=True)
        receipt_path = case_dir / "receipt.json"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        result = run_ps(
            case_dir,
            r"""
$receipt = Get-Content -LiteralPath $ArgsPassthrough[0] -Raw | ConvertFrom-Json
$binding = [pscustomobject]@{ symbol = 'EURUSD'; from = '1970.01.01'; to = '2024.12.31' }
Resolve-DataQualityContract $receipt $binding | ConvertTo-Json -Depth 8
""",
            str(receipt_path),
        )
        assert result.returncode != 0
        assert expected in result.stderr

    wrong_case = {"binding": {"Data_Quality_Contract": base["binding"]["data_quality_contract"]}}
    wrong_case_path = tmp_path / "wrong_case.json"
    wrong_case_path.write_text(json.dumps(wrong_case), encoding="utf-8")
    (tmp_path / "wrong_case").mkdir()
    result = run_ps(
        tmp_path / "wrong_case",
        r"""
$receipt = Get-Content -LiteralPath $ArgsPassthrough[0] -Raw | ConvertFrom-Json
$binding = [pscustomobject]@{ symbol = 'EURUSD'; from = '1970.01.01'; to = '2024.12.31' }
Resolve-DataQualityContract $receipt $binding | ConvertTo-Json -Depth 8
""",
        str(wrong_case_path),
    )
    assert result.returncode != 0
    assert "exactly case-sensitive" in result.stderr


def test_journal_delta_reads_only_appended_utf16le_bytes(tmp_path: Path) -> None:
    root = tmp_path / "mt5" / "logs"
    root.mkdir(parents=True)
    log = root / "tester.log"
    before = "old line\n"
    appended = "EURUSD: history synchronized from 2021.02.01 to 2024.12.31\n"
    log.write_bytes(before.encode("utf-16le"))
    result = run_ps(
        tmp_path,
        r"""
$root = $ArgsPassthrough[0]
$log = $ArgsPassthrough[1]
$out = $ArgsPassthrough[2]
$snapshot = @(New-Mt5JournalLogSnapshot @($root))
Add-Content -LiteralPath $log -Value 'EURUSD: history synchronized from 2021.02.01 to 2024.12.31' -Encoding Unicode
$delta = Export-Mt5JournalLogDelta -Snapshot $snapshot -Roots @($root) -OutputPath $out -MaxBytes 4096
$text = Get-Content -LiteralPath $out -Raw
[pscustomobject]@{
    sha256 = [string]$delta.sha256
    bytes_read = [int64]$delta.bytes_read
    files_read = [int]$delta.files_read
    truncated = [bool]$delta.truncated
    text = [string]$text
} | ConvertTo-Json -Depth 4
""",
        str(root.parent),
        str(log),
        str(tmp_path / "delta.log"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert appended.strip() in payload["text"]
    assert before.strip() not in payload["text"]
    assert payload["sha256"] == sha(tmp_path / "delta.log")


def test_journal_delta_exact_limit_is_complete_and_over_limit_is_truncated(tmp_path: Path) -> None:
    for name, size, expected_truncated in (("exact", 32, False), ("over", 33, True)):
        case_dir = tmp_path / name
        root = case_dir / "mt5" / "logs"
        root.mkdir(parents=True)
        log = root / "tester.log"
        log.write_bytes(b"")
        result = run_ps(
            case_dir,
            r"""
$root = $ArgsPassthrough[0]
$log = $ArgsPassthrough[1]
$out = $ArgsPassthrough[2]
$payload = $ArgsPassthrough[3]
$snapshot = @(New-Mt5JournalLogSnapshot @($root))
[System.IO.File]::WriteAllBytes($log, [System.Text.Encoding]::ASCII.GetBytes($payload))
$delta = Export-Mt5JournalLogDelta -Snapshot $snapshot -Roots @($root) -OutputPath $out -MaxBytes 32
[pscustomobject]@{ bytes_read = [int64]$delta.bytes_read; truncated = [bool]$delta.truncated } | ConvertTo-Json
""",
            str(root.parent),
            str(log),
            str(case_dir / "delta.log"),
            "A" * size,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(result.stdout)
        assert payload["bytes_read"] == 32
        assert payload["truncated"] is expected_truncated


def test_journal_files_refuse_unscoped_tester_tree(tmp_path: Path) -> None:
    tester = tmp_path / "Tester"
    (tester / "bases").mkdir(parents=True)
    (tester / "logs").mkdir()
    (tester / "logs" / "x.log").write_text("x", encoding="utf-8")
    (tester / "cache").mkdir()
    (tester / "cache" / "nested.log").write_text("nope", encoding="utf-8")
    result = run_ps(
        tmp_path,
        r"""
$root = $ArgsPassthrough[0]
Get-Mt5JournalLogFiles @($root) | ConvertTo-Json
""",
        str(tester),
    )
    assert result.returncode != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "logs directory" in combined or "Tester/data tree" in combined
