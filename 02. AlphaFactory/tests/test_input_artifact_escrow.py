from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
ALPHA = ALPHA_ROOT / "alpha.ps1"
ENGINE = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def run_harness(tmp_path: Path, action: str, spec: str = "") -> subprocess.CompletedProcess[str]:
    assert POWERSHELL, "PowerShell is required"
    common = tmp_path / "Common" / "Files"
    run_dir = tmp_path / "run"
    inputs = run_dir / "inputs"
    common.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = b"event_id,utc_time,event_class,currency,title\r\n1,2026.08.13 12:00:00,CPI,USD,fixture\r\n"
    source = common / "calendar.csv"
    source.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest().upper()
    harness = tmp_path / "input_escrow_harness.ps1"
    harness.write_text(
        r"""
param(
    [string]$Alpha,
    [string]$CommonRoot,
    [string]$RunDir,
    [string]$Action,
    [string]$Spec
)
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Alpha, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
foreach ($name in @(
    'Get-TextSha256',
    'Get-Sha256Required',
    'ConvertTo-RequiredInputArtifactList',
    'Get-RequiredInputArtifactBindingRecords',
    'Get-RequiredInputArtifactSetSha256',
    'New-RequiredInputArtifactSnapshots',
    'Assert-RequiredInputArtifactSnapshots'
)) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
try {
    $items = @(ConvertTo-RequiredInputArtifactList $Spec)
    if ($Action -ceq 'parse') {
        [pscustomobject]@{ ok = $true; items = @($items) } | ConvertTo-Json -Depth 8
        exit 0
    }
    $inputsDir = Join-Path $RunDir 'inputs'
    $snapshots = @(New-RequiredInputArtifactSnapshots $items $CommonRoot $inputsDir)
    $setHash = Get-RequiredInputArtifactSetSha256 $snapshots
    if ($Action -ceq 'mutate_source') {
        Set-Content -LiteralPath (Join-Path $CommonRoot 'calendar.csv') -Value 'changed' -Encoding UTF8
    }
    $verified = Assert-RequiredInputArtifactSnapshots $snapshots $RunDir $CommonRoot $setHash
    [pscustomobject]@{
        ok = $true
        items = @($items)
        snapshots = @($snapshots)
        set_sha256 = $setHash
        verified_sha256 = $verified
    } | ConvertTo-Json -Depth 8
} catch {
    [pscustomobject]@{ ok = $false; error = $_.Exception.Message } | ConvertTo-Json -Depth 8
}
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
            str(harness),
            "-Alpha",
            str(ALPHA),
            "-CommonRoot",
            str(common),
            "-RunDir",
            str(run_dir),
            "-Action",
            action,
            "-Spec",
            spec or f"calendar.csv@{expected}",
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )


def test_required_input_artifact_is_snapshotted_and_hash_verified(tmp_path: Path) -> None:
    result = run_harness(tmp_path, "snapshot")
    assert result.returncode == 0, result.stdout + result.stderr
    packet = json.loads(result.stdout)
    assert packet["ok"] is True
    assert packet["items"][0]["source"] == "FILE_COMMON"
    assert packet["items"][0]["name"] == "calendar.csv"
    assert packet["snapshots"][0]["path"] == "inputs/calendar.csv"
    assert packet["set_sha256"] == packet["verified_sha256"]
    assert (tmp_path / "run" / "inputs" / "calendar.csv").read_bytes() == (
        tmp_path / "Common" / "Files" / "calendar.csv"
    ).read_bytes()


def test_required_input_artifact_source_mutation_fails_closed(tmp_path: Path) -> None:
    result = run_harness(tmp_path, "mutate_source")
    assert result.returncode == 0, result.stdout + result.stderr
    packet = json.loads(result.stdout)
    assert packet["ok"] is False
    assert "source changed during the run" in packet["error"]


def test_required_input_artifact_missing_or_wrong_hash_fails_closed(tmp_path: Path) -> None:
    missing = run_harness(tmp_path / "missing", "snapshot", f"absent.csv@{'A' * 64}")
    assert missing.returncode == 0, missing.stdout + missing.stderr
    missing_packet = json.loads(missing.stdout)
    assert missing_packet["ok"] is False
    assert "is missing" in missing_packet["error"]

    wrong_hash = run_harness(tmp_path / "wrong-hash", "snapshot", f"calendar.csv@{'B' * 64}")
    assert wrong_hash.returncode == 0, wrong_hash.stdout + wrong_hash.stderr
    wrong_hash_packet = json.loads(wrong_hash.stdout)
    assert wrong_hash_packet["ok"] is False
    assert "hash mismatch" in wrong_hash_packet["error"]


def test_required_input_artifact_parser_rejects_unsafe_and_duplicate_names(tmp_path: Path) -> None:
    digest = "A" * 64
    unsafe = run_harness(tmp_path / "unsafe", "parse", f"..\\calendar.csv@{digest}")
    assert unsafe.returncode == 0, unsafe.stdout + unsafe.stderr
    unsafe_packet = json.loads(unsafe.stdout)
    assert unsafe_packet["ok"] is False
    assert "basename@sha256" in unsafe_packet["error"]

    duplicate = run_harness(
        tmp_path / "duplicate",
        "parse",
        f"calendar.csv@{digest};CALENDAR.csv@{digest}",
    )
    assert duplicate.returncode == 0, duplicate.stdout + duplicate.stderr
    duplicate_packet = json.loads(duplicate.stdout)
    assert duplicate_packet["ok"] is False
    assert "duplicate name" in duplicate_packet["error"]


def test_engine_routes_required_input_artifacts_into_receipt_and_alpha_invocation() -> None:
    text = ENGINE.read_text(encoding="utf-8")
    assert "required_input_artifacts = @($Binding.RequiredInputArtifacts)" in text
    assert "RequiredInputArtifacts = ConvertTo-AlphaRequiredInputArtifactSpecs" in text
    assert "Post-run manifest input_artifacts do not match task packet." in text


def test_price_data_fingerprint_remains_separate_from_input_artifact_identity() -> None:
    text = ALPHA.read_text(encoding="utf-8")
    assert "$manifest.data_fingerprint = $identity.DataFingerprint" in text
    assert "Get-TextSha256 ([string]::Join('|', @([string]$identity.DataFingerprint" not in text
    assert "-Name input_artifacts_sha256 -Value $inputArtifactSetSha256" in text
