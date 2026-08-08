from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
ALPHA = ALPHA_ROOT / "alpha.ps1"
RUNNER = ALPHA_ROOT / "tools" / "ea_research_loop.ps1"
REGISTRY = WORKSPACE / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
REGISTRY_VALIDATOR = WORKSPACE / "04. Memory" / "research" / "validate_candidate_registry.py"


def run_ps_file(script: Path, *args: str, cwd: Path = WORKSPACE) -> subprocess.CompletedProcess[str]:
    assert POWERSHELL, "PowerShell is required"
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )


def run_data_quality_contract_validator(
    tmp_path: Path,
    packet: dict,
    *,
    from_date: str = "1970.01.01",
    to_date: str = "2025.12.31",
) -> dict:
    assert POWERSHELL, "PowerShell is required"
    tmp_path.mkdir(parents=True, exist_ok=True)
    packet_path = tmp_path / "packet.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    engine = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
    harness_path = tmp_path / "validate_data_quality.ps1"
    harness_path.write_text(r"""
param(
    [string]$Engine,
    [string]$PacketPath,
    [string]$FromDate,
    [string]$ToDate
)
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
$needed = @(
    'Test-ProvenanceObject',
    'Get-ObjectProperty',
    'Test-FiniteNumber',
    'Test-ExactObjectKeys',
    'Test-ResearchDate',
    'Test-ZuluTimestamp',
    'Resolve-DataQualityContract'
)
foreach ($name in $needed) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
$packet = Get-Content -LiteralPath $PacketPath -Raw | ConvertFrom-Json
$binding = [pscustomobject]@{ From = $FromDate; To = $ToDate }
$blockers = New-Object System.Collections.Generic.List[string]
$contract = Resolve-DataQualityContract $packet $binding $blockers
[pscustomobject]@{
    blockers = @($blockers | ForEach-Object { [string]$_ })
    contract = $contract
} | ConvertTo-Json -Depth 12
""", encoding="utf-8")
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(harness_path),
            "-Engine",
            str(engine),
            "-PacketPath",
            str(packet_path),
            "-FromDate",
            from_date,
            "-ToDate",
            to_date,
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def run_execution_authority_validator(tmp_path: Path, packet: dict, binding: dict) -> dict:
    assert POWERSHELL, "PowerShell is required"
    tmp_path.mkdir(parents=True, exist_ok=True)
    packet_path = tmp_path / "authority_packet.json"
    binding_path = tmp_path / "authority_binding.json"
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    engine = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
    harness = tmp_path / "validate_authority.ps1"
    harness.write_text(r'''
param([string]$Engine, [string]$PacketPath, [string]$BindingPath)
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
$fn = $ast.Find({ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -ceq 'Resolve-ExecutionAuthority'
}, $true)
if ($null -eq $fn) { throw 'Missing Resolve-ExecutionAuthority' }
Invoke-Expression $fn.Extent.Text
$packet = Get-Content -LiteralPath $PacketPath -Raw | ConvertFrom-Json
$binding = Get-Content -LiteralPath $BindingPath -Raw | ConvertFrom-Json
$blockers = New-Object System.Collections.Generic.List[string]
$authority = Resolve-ExecutionAuthority $packet $binding $blockers
[pscustomobject]@{
    authority = $authority
    blockers = @($blockers | ForEach-Object { [string]$_ })
} | ConvertTo-Json -Depth 6
''', encoding="utf-8")
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(harness),
            "-Engine",
            str(engine),
            "-PacketPath",
            str(packet_path),
            "-BindingPath",
            str(binding_path),
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def run_model4_launch_authority_validator(
    tmp_path: Path,
    *,
    validation_overrides: dict | None = None,
    preexisting_claim: bool = False,
    create_claim: bool = False,
) -> dict:
    assert POWERSHELL, "PowerShell is required"
    tmp_path.mkdir(parents=True, exist_ok=True)
    fake_root = tmp_path / "repo"
    fake_alpha = fake_root / "02. AlphaFactory"
    fake_tools = fake_alpha / "tools"
    fake_research = fake_root / "04. Memory" / "research"
    fake_tools.mkdir(parents=True, exist_ok=True)
    fake_research.mkdir(parents=True, exist_ok=True)
    engine = fake_tools / "research_loop_engine.ps1"
    engine.write_text(
        (ALPHA_ROOT / "tools" / "research_loop_engine.ps1").read_text(encoding="utf-8-sig"),
        encoding="utf-8",
    )
    control_files = {
        fake_alpha / "alpha.ps1": ALPHA.read_text(encoding="utf-8-sig"),
        fake_alpha / "alpha.local.ps1": "$MT5InstallRoot='D:/MT5'\n",
        fake_tools / "mt5_storage_contract.ps1": "# mt5 storage\n",
        fake_tools / "ea_contract.ps1": "# ea contract\n",
        fake_tools / "log_storage.ps1": "# log storage\n",
        fake_tools / "audit_mql5_nonrepaint.py": "# nonrepaint\n",
        fake_research / "validate_candidate_registry.py": REGISTRY_VALIDATOR.read_text(
            encoding="utf-8"
        ),
    }
    for path, text in control_files.items():
        path.write_text(text, encoding="utf-8")
    bound_test_relative_paths = [
        "02. AlphaFactory/tests/test_ea_golden_path.py",
        "02. AlphaFactory/tests/test_nonrepaint_collection_probe.py",
        "03. EA Developer/EA_PTR_T2_DataEpochD0V3/tests/test_mql5_contract.py",
        (
            "03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/tests/"
            "test_append_t2_data_epoch_evidence.py"
        ),
        (
            "03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/tests/"
            "test_append_t2_data_epoch_model4_evidence.py"
        ),
        (
            "03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/tests/"
            "test_t2_d0_model4_wrappers.py"
        ),
        (
            "03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/tests/"
            "test_t2_d0_hyp005_wrappers.py"
        ),
        "04. Memory/research/tests/test_validate_data_epoch.py",
        "04. Memory/research/tests/test_validate_campaign_exposure.py",
        (
            "04. Memory/research/tests/"
            "test_validate_candidate_registry_model4_collection.py"
        ),
    ]
    bound_tests = []
    for index, relative_path in enumerate(bound_test_relative_paths):
        path = fake_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# bound test {index}\n", encoding="utf-8")
        bound_tests.append(
            {
                "path": relative_path,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
            }
        )
    packet_path = fake_root / "packet.json"
    packet = {
        "authority": "DATA_ACQUISITION_ONLY_NO_PERFORMANCE",
        "registry_sha256": "A" * 64,
        "registry_row_sha256": "B" * 64,
        "git_status_sha256": "C" * 64,
    }
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    packet_sha = hashlib.sha256(packet_path.read_bytes()).hexdigest().upper()
    dependency_bindings = [
        {
            "path": "02. AlphaFactory/alpha.ps1",
            "sha256": hashlib.sha256((fake_alpha / "alpha.ps1").read_bytes()).hexdigest().upper(),
        },
        {
            "path": "02. AlphaFactory/tools/mt5_storage_contract.ps1",
            "sha256": hashlib.sha256((fake_tools / "mt5_storage_contract.ps1").read_bytes()).hexdigest().upper(),
        },
        {
            "path": "02. AlphaFactory/tools/ea_contract.ps1",
            "sha256": hashlib.sha256((fake_tools / "ea_contract.ps1").read_bytes()).hexdigest().upper(),
        },
        {
            "path": "02. AlphaFactory/tools/log_storage.ps1",
            "sha256": hashlib.sha256((fake_tools / "log_storage.ps1").read_bytes()).hexdigest().upper(),
        },
        {
            "path": "02. AlphaFactory/tools/audit_mql5_nonrepaint.py",
            "sha256": hashlib.sha256((fake_tools / "audit_mql5_nonrepaint.py").read_bytes()).hexdigest().upper(),
        },
    ]
    prior_receipt = tmp_path / "packet_set_dry_run_receipt.json"
    prior_receipt.write_text('{"ok":true}', encoding="utf-8")
    prior_receipt_sha = hashlib.sha256(prior_receipt.read_bytes()).hexdigest().upper()
    prior_receipt_path = str(prior_receipt)
    bridge_receipt_path = (
        "03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/evidence/"
        "HYP-PTR-T2-DATA-EPOCH-D0-M5-005/"
        "HYP005_XAU_MODEL4_EXECUTE_GATE_HARDENING_RECEIPT_V4.json"
    )
    bridge_receipt_normal = (fake_root / bridge_receipt_path).resolve()
    bridge_receipt = (
        Path("\\\\?\\" + str(bridge_receipt_normal))
        if os.name == "nt"
        else bridge_receipt_normal
    )
    bridge_receipt.parent.mkdir(parents=True, exist_ok=True)
    bridge_receipt.write_text('{"bridge":true}', encoding="utf-8")
    bridge_receipt_sha = hashlib.sha256(bridge_receipt.read_bytes()).hexdigest().upper()
    hardening_receipt = tmp_path / "execute_gate_hardening_receipt.json"
    hardening_payload = {
        "schema_version": "alphafactory_prelaunch_xau_model4_execute_gate_hardening.v5",
        "hypothesis_id": "HYP-PTR-T2-DATA-EPOCH-D0-M5-005",
        "classification": "PRELAUNCH_XAU_MODEL4_REGISTRY_LOCK_FULL_SUITE_EXECUTE_AUTHORIZATION",
        "authority": "DATA_ACQUISITION_ONLY_NO_PERFORMANCE",
        "verdict": "PASS_ONE_SHOT_XAU_REGISTRY_LOCK_FULL_SUITE_EXECUTE_GATE",
        "execution_authorized": True,
        "full_suite_attested": True,
        "prior_registry": {
            "path": "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
            "line": 459,
            "sha256": "E" * 64,
            "row_sha256": "F" * 64,
        },
        "prior_bridge_receipt": {
            "path": bridge_receipt_path,
            "sha256": bridge_receipt_sha,
        },
        "prior_authority_receipt": {
            "path": prior_receipt_path,
            "sha256": prior_receipt_sha,
        },
        "authorized_git_status": {"current_sha256": "D" * 64},
        "control_plane": {
            "runner": {
                "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                "sha256": hashlib.sha256(engine.read_bytes()).hexdigest().upper(),
            },
            "candidate_registry_validator": {
                "path": "04. Memory/research/validate_candidate_registry.py",
                "sha256": hashlib.sha256(
                    (fake_research / "validate_candidate_registry.py").read_bytes()
                )
                .hexdigest()
                .upper(),
            },
            "alpha_entrypoint": {
                "path": "02. AlphaFactory/alpha.ps1",
                "sha256": dependency_bindings[0]["sha256"],
            },
            "execution_dependency_bindings": dependency_bindings,
        },
        "bound_tests": bound_tests,
        "launch_claim_path": (
            "03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/evidence/"
            "HYP-PTR-T2-DATA-EPOCH-D0-M5-005/HYP005_XAU_MODEL4_LAUNCH_CLAIM.json"
        ),
        "exact_test_run": {
            "framework": "pytest",
            "result": "PASS",
            "passed": 124,
            "failed": 0,
            "declared_test_file_count": 10,
            "symbol": "XAUUSD",
            "model": 4,
            "run_role": "control",
            "authority": "DATA_ACQUISITION_ONLY_NO_PERFORMANCE",
        },
        "exposure_readback": {
            "hyp005_execution_receipts": 0,
            "hyp005_run_manifests": 0,
            "launch_claims": 0,
            "trades_executed": 0,
            "economic_trials_consumed": 0,
        },
    }
    receipt_overrides = (validation_overrides or {}).pop("hardening_receipt_overrides", None)
    if receipt_overrides:
        for key, value in receipt_overrides.items():
            hardening_payload[key] = value
    hardening_receipt.write_text(json.dumps(hardening_payload), encoding="utf-8")
    validation = {
        "probe_status": "SCREENED_PRELAUNCH_XAU_MODEL4_COLLECTION_REGISTRY_LOCK_FULL_SUITE_AUTHORIZED",
        "task_packets_created": True,
        "task_packet_authorized_next": False,
        "xau_model4_collection_launch_authorized": True,
        "mt5_data_collection_authorized": True,
        "model4_data_collection_authorized": True,
        "mt5_authorized": False,
        "model4_authorized": False,
        "trading_backtest_authorized": False,
        "trades_authorized": False,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "optimization_authorized": False,
        "validation_access_authorized": False,
        "holdout_access_authorized": False,
        "promotion_eligible": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
        "market_edge_claim_authorized": False,
        "authorized_symbol": "XAUUSD",
        "authorized_symbol_order_index": 0,
        "authorized_launch_limit": 1,
        "authorized_launches_consumed": 0,
        "xau_task_packet_path": "packet.json",
        "xau_task_packet_sha256": packet_sha,
        "authorized_packet_registry_sha256": packet["registry_sha256"],
        "authorized_packet_registry_row_sha256": packet["registry_row_sha256"],
        "authorized_packet_git_status_sha256": packet["git_status_sha256"],
        "execute_gate_prior_registry_line": 459,
        "execute_gate_prior_registry_sha256": "E" * 64,
        "execute_gate_prior_registry_row_sha256": "F" * 64,
        "authorized_current_git_status_sha256": "D" * 64,
        "runner_engine_sha256": hashlib.sha256(engine.read_bytes()).hexdigest().upper(),
        "candidate_registry_validator_sha256": hashlib.sha256(
            (fake_research / "validate_candidate_registry.py").read_bytes()
        )
        .hexdigest()
        .upper(),
        "alpha_entrypoint_sha256": dependency_bindings[0]["sha256"],
        "execution_dependency_bindings": dependency_bindings,
        "bound_tests": bound_tests,
        "packet_set_dry_run_receipt_path": prior_receipt_path,
        "packet_set_dry_run_receipt_sha256": prior_receipt_sha,
        "execute_gate_hardening_receipt_path": str(hardening_receipt),
        "execute_gate_hardening_receipt_sha256": hashlib.sha256(
            hardening_receipt.read_bytes()
        )
        .hexdigest()
        .upper(),
        "launch_claim_path": (
            "03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/evidence/"
            "HYP-PTR-T2-DATA-EPOCH-D0-M5-005/HYP005_XAU_MODEL4_LAUNCH_CLAIM.json"
        ),
    }
    if preexisting_claim:
        claim = fake_root / validation["launch_claim_path"]
        claim.parent.mkdir(parents=True, exist_ok=True)
        claim.write_text('{"claimed":true}', encoding="utf-8")
    validation.update(validation_overrides or {})
    validation_path = tmp_path / "validation.json"
    validation_path.write_text(json.dumps(validation), encoding="utf-8")
    harness = tmp_path / "validate_model4_launch.ps1"
    harness.write_text(
        r'''
param(
    [string]$Engine,
    [string]$Root,
    [string]$PacketPath,
    [string]$ValidationPath
)
$ErrorActionPreference = 'Stop'
$repoRoot = $Root
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Engine, [ref]$tokens, [ref]$parseErrors
)
if ($parseErrors.Count -gt 0) {
    throw ($parseErrors | ForEach-Object { $_.Message } | Out-String)
}
$needed = @(
    'Get-Sha256IfExists',
    'Test-Sha256Text',
    'Test-IntegerValue',
    'Test-ProvenanceObject',
    'Test-ExactObjectKeys',
    'Get-ObjectProperty',
    'Resolve-EvidencePath',
    'Get-RepoRelativePath',
    'Get-Model4ControlPlaneBinding',
    'Get-Model4ExecutionDependencyBindings',
    'Test-Model4ExecutionDependencyBindings',
    'Get-ExpectedModel4BoundTestRelativePaths',
    'Test-Model4BoundTestBindings',
    'Test-ScopedModel4PriorRegistryPacket',
    'Get-ExpectedModel4LaunchClaimRelativePath',
    'Add-Model4ReceiptObjectBlockers',
    'Add-Model4CollectionLaunchAuthorityBlockers',
    'New-Model4CollectionLaunchClaim'
)
foreach ($name in $needed) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
$packet = Get-Content -LiteralPath $PacketPath -Raw | ConvertFrom-Json
$validation = Get-Content -LiteralPath $ValidationPath -Raw | ConvertFrom-Json
$contract = [pscustomobject]@{
    HypothesisId = 'HYP-PTR-T2-DATA-EPOCH-D0-M5-005'
    RegistryState = 'screened'
    RegistryPath = Join-Path $Root '04. Memory\research\CANDIDATE_REGISTRY.jsonl'
    RegistrySha256 = '7' * 64
    RegistryLine = 460
    RegistryRowSha256 = '8' * 64
    LatestRow = [pscustomobject]@{ validation = $validation }
}
$binding = [pscustomobject]@{
    Model = 4
    RunRole = 'control'
    Symbol = 'XAUUSD'
    GitStatusSha256 = 'D' * 64
}
$packetResult = [pscustomobject]@{
    Packet = $packet
    PacketPath = $PacketPath
    PacketSha256 = Get-Sha256IfExists $PacketPath
    Authority = 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
}
$blockers = New-Object System.Collections.Generic.List[string]
Add-Model4CollectionLaunchAuthorityBlockers `
    $contract $binding $packetResult $Engine $blockers
$claimCreated = $false
$duplicateRejected = $false
if ($env:MODEL4_CREATE_CLAIM -ceq '1') {
    $claim = New-Model4CollectionLaunchClaim $contract $binding $packetResult $Engine
    $claimCreated = (Test-Path -LiteralPath $claim.Path -PathType Leaf) -and
        ((Get-Sha256IfExists $claim.Path) -ceq $claim.Sha256)
    try {
        [void](New-Model4CollectionLaunchClaim $contract $binding $packetResult $Engine)
    } catch {
        $duplicateRejected = $true
    }
}
[pscustomobject]@{
    scoped = Test-ScopedModel4PriorRegistryPacket `
        $packet $contract $binding $PacketPath
    blockers = @($blockers | ForEach-Object { [string]$_ })
    claim_created = $claimCreated
    duplicate_rejected = $duplicateRejected
} | ConvertTo-Json -Depth 6
''',
        encoding="utf-8",
    )
    env = None
    if create_claim:
        env = {**dict(os.environ), "MODEL4_CREATE_CLAIM": "1"}
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(harness),
            "-Engine",
            str(engine),
            "-Root",
            str(fake_root),
            "-PacketPath",
            str(packet_path),
            "-ValidationPath",
            str(validation_path),
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def run_model4_execution_receipt_builder(tmp_path: Path) -> dict:
    assert POWERSHELL, "PowerShell is required"
    tmp_path.mkdir(parents=True, exist_ok=True)
    packet = tmp_path / "packet.json"
    registry = tmp_path / "registry.jsonl"
    source = tmp_path / "source.mq5"
    prereg = tmp_path / "PROBE_PLAN.json"
    cost = tmp_path / "cost.json"
    claim = tmp_path / "launch_claim.json"
    for path, text in {
        packet: '{"authority":"DATA_ACQUISITION_ONLY_NO_PERFORMANCE"}',
        registry: "{}\n",
        source: "void OnTick(){}\n",
        prereg: "{}\n",
        cost: "{}\n",
        claim: "{}\n",
    }.items():
        path.write_text(text, encoding="utf-8")
    receipt = tmp_path / "execution_receipt.json"
    engine = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
    harness = tmp_path / "build_execution_receipt.ps1"
    harness.write_text(
        r'''
param(
    [string]$Engine,
    [string]$Workspace,
    [string]$TmpRoot,
    [string]$PacketPath,
    [string]$RegistryPath,
    [string]$SourcePath,
    [string]$PreregPath,
    [string]$CostPath,
    [string]$ClaimPath,
    [string]$ReceiptPath
)
$ErrorActionPreference = 'Stop'
$repoRoot = $Workspace
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
foreach ($name in @(
    'Write-JsonAtomically',
    'Get-Sha256IfExists',
    'Test-Sha256Text',
    'Get-ObjectProperty',
    'Resolve-EvidencePath',
    'Get-Model4ControlPlaneBinding',
    'Get-Model4ExecutionDependencyBindings',
    'Add-DataQualityContractToReceiptBinding',
    'New-ExecutionReceipt'
)) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
$packet = Get-Content -LiteralPath $PacketPath -Raw | ConvertFrom-Json
$contract = [pscustomobject]@{
    HypothesisId = 'HYP-PTR-T2-DATA-EPOCH-D0-M5-005'
    RegistryRowSha256 = 'B' * 64
    RegistryPath = $RegistryPath
    RegistrySha256 = Get-Sha256IfExists $RegistryPath
    CanonicalSourceAbsolute = $SourcePath
    CurrentSourceSha256 = Get-Sha256IfExists $SourcePath
    EaContractSha256 = ''
    EaContractAbsolutePath = ''
    PreregPath = $PreregPath
    PreregSha256 = Get-Sha256IfExists $PreregPath
    LatestRow = [pscustomobject]@{
        validation = [pscustomobject]@{
            execute_gate_hardening_receipt_path = $CostPath
            execute_gate_hardening_receipt_sha256 = Get-Sha256IfExists $CostPath
            packet_set_dry_run_receipt_path = $PreregPath
            packet_set_dry_run_receipt_sha256 = Get-Sha256IfExists $PreregPath
        }
    }
}
$packetResult = [pscustomobject]@{
    Packet = $packet
    PacketPath = $PacketPath
    PacketSha256 = Get-Sha256IfExists $PacketPath
    CostSourceManifestPath = $CostPath
    CostEvidence = @()
    IncludeClosure = @()
    WfaArtifactPath = ''
    VariantsDir = ''
    Authority = 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
}
$binding = [pscustomobject]@{
    HypothesisId = 'HYP-PTR-T2-DATA-EPOCH-D0-M5-005'
    RunRole = 'control'
    EaName = 'EA_PTR_T2_DataEpochD0V3'
    Symbol = 'XAUUSD'
    Period = 'M5'
    From = '1970.01.01'
    To = '2026.07.30'
    Model = 4
    ExecutionMode = 0
    FixedDelayMs = 0
    Overrides = ''
    TelemetryTier = 'off'
    TelemetryProfile = 'none'
    Deposit = 10000
    Leverage = 100
    Spread = '0'
    RequiredSidecars = @()
    BrokerFingerprint = '1' * 64
    ServerFingerprint = '2' * 64
    AccountFingerprint = '3' * 64
    DataFingerprint = '4' * 64
    SymbolDigits = 2
    SymbolPoint = 0.01
    PipSize = 0.01
    IncludeClosureSha256 = 'E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855'
    GitCommit = 'test'
    GitStatusSha256 = '5' * 64
    DataQualityContract = [pscustomobject][ordered]@{
        history_quality = [pscustomobject][ordered]@{ operator = 'gt'; value = 97.0 }
        coverage_mode = 'all_available_asof'
        availability_asof_utc = '2026-07-30T00:00:00Z'
        requested_from = '1970.01.01'
        requested_to = '2026.07.30'
        require_tester_journal_bounds = $true
    }
}
$claimRecord = [pscustomobject]@{ Path = $ClaimPath; Sha256 = Get-Sha256IfExists $ClaimPath }
$record = New-ExecutionReceipt $ReceiptPath $contract $packetResult $binding $claimRecord $Engine
$receipt = Get-Content -LiteralPath $record.Path -Raw | ConvertFrom-Json
[pscustomobject]@{
    schema_version = [string]$receipt.schema_version
    authority = [string]$receipt.authority
    has_binding = ($null -ne $receipt.binding)
    has_launch_claim = ($null -ne $receipt.launch_claim)
    labels = @($receipt.evidence | ForEach-Object { [string]$_.label })
} | ConvertTo-Json -Depth 8
''',
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(harness),
            "-Engine",
            str(engine),
            "-Workspace",
            str(WORKSPACE),
            "-TmpRoot",
            str(tmp_path),
            "-PacketPath",
            str(packet),
            "-RegistryPath",
            str(registry),
            "-SourcePath",
            str(source),
            "-PreregPath",
            str(prereg),
            "-CostPath",
            str(cost),
            "-ClaimPath",
            str(claim),
            "-ReceiptPath",
            str(receipt),
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_alpha_discovers_canonical_active_packages() -> None:
    result = run_ps_file(ALPHA, "list")
    assert result.returncode == 0, result.stdout + result.stderr
    names = [
        line.strip()
        for line in result.stdout.splitlines()
        if re.fullmatch(r"EA_[A-Za-z0-9_.-]+", line.strip())
    ]
    developer_root = WORKSPACE / "03. EA Developer"
    expected = sorted(
        (
            package.name
            for package in developer_root.iterdir()
            if package.is_dir() and (package / f"{package.name}.mq5").is_file()
        ),
        key=str.casefold,
    )
    assert names == expected
    assert "EA_SonicR" not in names


def test_backup_action_is_removed_and_cannot_mutate_git() -> None:
    before = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    result = run_ps_file(ALPHA, "backup")
    after = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert result.returncode != 0
    assert before == after
    alpha_text = ALPHA.read_text(encoding="utf-8-sig")
    assert '"backup"' not in alpha_text
    assert "git push" not in alpha_text


def test_canonical_registry_validates() -> None:
    result = subprocess.run(
        [sys.executable, str(REGISTRY_VALIDATOR)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    match = re.search(r"CANDIDATE_REGISTRY_OK rows=(\d+) hypotheses=(\d+)", result.stdout)
    assert match, result.stdout
    assert int(match.group(1)) >= 3
    assert int(match.group(2)) >= 3


def test_registry_rejects_tampered_hash_and_illegal_terminal_transition(tmp_path: Path) -> None:
    rows = [json.loads(line) for line in REGISTRY.read_text(encoding="utf-8").splitlines()]
    rows[0]["source_hash"] = "0" * 64
    tampered = tmp_path / "tampered.jsonl"
    tampered.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(REGISTRY_VALIDATOR), "--registry", str(tampered)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "SHA256 mismatch" in result.stderr

    illegal_row = dict(rows[1])
    illegal_row["state"] = "screened"
    illegal_row["updated_at_utc"] = "2026-07-16T11:00:00Z"
    illegal = tmp_path / "illegal.jsonl"
    pristine = REGISTRY.read_text(encoding="utf-8").rstrip("\n")
    illegal.write_text(pristine + "\n" + json.dumps(illegal_row) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(REGISTRY_VALIDATOR), "--registry", str(illegal)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "illegal transition killed->screened" in result.stderr


def test_registry_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    first = REGISTRY.read_text(encoding="utf-8").splitlines()[0]
    duplicate = first[:-1] + ',"state":"screened"}'
    path = tmp_path / "duplicate.jsonl"
    path.write_text(duplicate + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(REGISTRY_VALIDATOR), "--registry", str(path)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "duplicate JSON key" in result.stderr


def test_registry_rejects_tampered_terminal_source_snapshot(tmp_path: Path) -> None:
    rows = [json.loads(line) for line in REGISTRY.read_text(encoding="utf-8").splitlines()]
    target = next(
        row
        for row in reversed(rows)
        if row["hypothesis_id"] == "HYP-UPS-XAU-M5-003" and row["state"] == "killed"
    )
    target["source_path"] = (
        "03. EA Developer/EA_UnicornPrecisionScalper/research/source_snapshots/"
        "missing.mq5"
    )
    path = tmp_path / "tampered-terminal-snapshot.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(REGISTRY_VALIDATOR), "--registry", str(path)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "file is missing" in result.stderr


def test_registry_rejects_weakened_acceptance_contract(tmp_path: Path) -> None:
    rows = [json.loads(line) for line in REGISTRY.read_text(encoding="utf-8").splitlines()]
    rows[0]["acceptance_contract"]["min_profit_factor"] = 1.0
    path = tmp_path / "weak-gates.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(REGISTRY_VALIDATOR), "--registry", str(path)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "acceptance_contract" in result.stderr

    transition = json.loads(REGISTRY.read_text(encoding="utf-8").splitlines()[0])
    transition["state"] = "screened"
    transition["acceptance_contract"]["min_profit_factor"] = 1.30
    transition["updated_at_utc"] = "2026-07-16T11:00:00Z"
    path = tmp_path / "post-readout-weaken.jsonl"
    path.write_text(
        REGISTRY.read_text(encoding="utf-8").rstrip("\n") + "\n" + json.dumps(transition) + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(REGISTRY_VALIDATOR), "--registry", str(path)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "frozen 'acceptance_contract' changed" in result.stderr


def test_fvg_research_dry_run_is_generic_and_blocks_before_mt5() -> None:
    result = run_ps_file(
        RUNNER,
        "-EaName", "EA_FVGConfluence",
        "-HypothesisId", "HYP-FVG-SCALP-CONFL-M5-EUR-001",
        "-RunRole", "control",
        "-Symbol", "EURUSD",
        "-Period", "M5",
        "-From", "2020.01.01",
        "-To", "2026.07.15",
        "-Model", "0",
        "-TelemetryTier", "off",
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert '"ea":  "EA_FVGConfluence"' in combined
    assert "Latest registry state 'killed'" in combined
    assert "no AlphaFactory lifecycle telemetry contract" in combined
    assert "missing Sonic" not in combined
    assert '"execution_allowed":  false' in combined


def test_variant_tag_requires_declared_package_capability() -> None:
    result = run_ps_file(
        RUNNER,
        "-EaName", "EA_FVGConfluence",
        "-HypothesisId", "HYP-FVG-SCALP-CONFL-M5-EUR-001",
        "-Symbol", "EURUSD",
        "-Period", "M5",
        "-From", "2020.01.01",
        "-To", "2026.07.15",
        "-VariantTag", "TEST",
    )
    assert result.returncode != 0
    assert "VariantTag is not supported" in (result.stdout + result.stderr)


def test_package_capability_contract_is_data_driven(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    package = repo / "03. EA Developer" / "EA_Demo"
    package.mkdir(parents=True)
    (package / "EA_Demo.mq5").write_text("input bool InpEnableTelemetry=false;\n", encoding="utf-8")
    contract = {
        "schema_version": "alphafactory_ea_contract.v1",
        "telemetry_profile": "lifecycle-v3",
        "market_phase_adapter": "none",
        "comparison_adapter": "generic-control-improvement-v1",
        "variant_tag_input": None,
    }
    contract_path = package / "ALPHAFACTORY_EA_CONTRACT.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    command = (
        f". '{ALPHA_ROOT / 'tools' / 'ea_contract.ps1'}'; "
        f"Resolve-EaSourceContract -RepoRoot '{repo}' -EaName 'EA_Demo' | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip())
    assert payload["TelemetryProfile"] == "lifecycle-v3"
    assert payload["ComparisonAdapter"] == "generic-control-improvement-v1"
    assert payload["ContractSha256"] == hashlib.sha256(contract_path.read_bytes()).hexdigest().upper()


def write_run(path: Path, *, net: float, pf: float, dd: float, trades: int = 100) -> None:
    analysis = path / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    (path / "run_manifest.json").write_text(
        json.dumps({
            "run_id": path.name,
            "ea_name": "EA_Demo",
            "symbol": "EURUSD",
            "period": "M15",
            "from": "2020.01.01",
            "to": "2025.12.31",
            "model": 0,
        }),
        encoding="utf-8",
    )
    (analysis / "enhanced_summary.json").write_text(
        json.dumps({
            "n_trades": trades,
            "net_profit": net,
            "profit_factor": pf,
            "max_drawdown_abs": dd,
            "max_drawdown_pct": dd / 100,
            "expectancy_per_trade": net / trades,
        }),
        encoding="utf-8",
    )
    (analysis / "validation_summary.json").write_text(json.dumps({"verdict": "PASS"}), encoding="utf-8")


def test_generic_comparator_has_no_sonic_absolute_thresholds(tmp_path: Path) -> None:
    baseline = tmp_path / "control"
    candidate = tmp_path / "challenger"
    write_run(baseline, net=100, pf=1.10, dd=50)
    write_run(candidate, net=120, pf=1.20, dd=55)
    output = tmp_path / "compare.json"
    tool = ALPHA_ROOT / "tools" / "alpha_candidate_compare.py"
    result = subprocess.run(
        [sys.executable, str(tool), str(candidate), "--baseline", str(baseline), "--ea", "EA_Demo", "--out", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["verdict"] == "RESEARCH_PASS"
    assert payload["schema_version"] == "alphafactory_candidate_compare.v1"
    assert "pf_below_1_30" not in payload["findings"]

    write_run(candidate, net=120, pf=1.20, dd=100)
    result = subprocess.run(
        [sys.executable, str(tool), str(candidate), "--baseline", str(baseline), "--ea", "EA_Demo", "--out", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "net_to_drawdown_below_control" in json.loads(output.read_text(encoding="utf-8"))["findings"]


def test_standalone_ea_include_closure_is_not_rejected_by_policy_text() -> None:
    engine = (ALPHA_ROOT / "tools" / "research_loop_engine.ps1").read_text(encoding="utf-8-sig")
    alpha = ALPHA.read_text(encoding="utf-8-sig")
    assert "include_closure must contain the active EA include dependency set" not in engine
    assert "missing packet-bound include closure evidence" not in alpha
    assert "FileShare]::Read" in engine


def test_runner_freezes_acceptance_contract_and_telemetry_tier_before_mt5() -> None:
    engine = (ALPHA_ROOT / "tools" / "research_loop_engine.ps1").read_text(encoding="utf-8-sig")
    assert "acceptance_contract must contain exactly the seven supported gate fields" in engine
    assert '"--min-pf"' in engine
    assert '"--max-mc-p95-dd-pct"' in engine
    assert "requires TelemetryTier=trade-only before MT5" in engine


def valid_data_quality_packet() -> dict:
    return {
        "data_quality_contract": {
            "history_quality": {"operator": "gt", "value": 97.0},
            "coverage_mode": "all_available_asof",
            "availability_asof_utc": "2025-12-31T23:59:59Z",
            "requested_from": "1970.01.01",
            "requested_to": "2025.12.31",
            "require_tester_journal_bounds": True,
        }
    }


def valid_collection_binding(model: int = 0) -> dict:
    return {
        "RunRole": "control",
        "Model": model,
        "TelemetryProfile": "none",
        "TelemetryTier": "off",
        "AllowResearchCostProxy": False,
        "DataQualityContract": valid_data_quality_packet()["data_quality_contract"],
    }


def test_data_acquisition_authority_is_exact_and_fail_closed(tmp_path: Path) -> None:
    model0_authority = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
    model4_authority = "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
    valid_model0 = run_execution_authority_validator(
        tmp_path / "valid_model0", {"authority": model0_authority}, valid_collection_binding()
    )
    assert valid_model0 == {"authority": model0_authority, "blockers": []}
    valid_model4 = run_execution_authority_validator(
        tmp_path / "valid_model4", {"authority": model4_authority}, valid_collection_binding(4)
    )
    assert valid_model4 == {"authority": model4_authority, "blockers": []}

    cases = [
        ("wrong_case_field", {"Authority": model0_authority}, valid_collection_binding(), "case-sensitive"),
        ("unsupported", {"authority": "DATA_ACQUISITION_ONLY"}, valid_collection_binding(), "unsupported"),
        ("challenger", {"authority": model0_authority}, {**valid_collection_binding(), "RunRole": "challenger"}, "RunRole=control"),
        ("old_wrong_model", {"authority": model0_authority}, valid_collection_binding(4), "Model=0"),
        ("new_wrong_model", {"authority": model4_authority}, valid_collection_binding(0), "Model=4"),
        ("telemetry", {"authority": model4_authority}, {**valid_collection_binding(4), "TelemetryProfile": "lifecycle-v3"}, "telemetry_profile='none'"),
        ("cost_proxy", {"authority": model4_authority}, {**valid_collection_binding(4), "AllowResearchCostProxy": True}, "forbids research cost proxy"),
        ("sidecar_permission", {"authority": model4_authority}, {**valid_collection_binding(4), "TelemetryTier": "trade-only"}, "telemetry_profile='none'"),
        ("no_dq", {"authority": model4_authority}, {**valid_collection_binding(4), "DataQualityContract": None}, "data_quality_contract"),
    ]
    for name, packet, binding, expected in cases:
        result = run_execution_authority_validator(tmp_path / name, packet, binding)
        assert any(expected in blocker for blocker in result["blockers"]), result

    launch = run_model4_launch_authority_validator(tmp_path / "launch")
    assert launch["scoped"] is True
    assert launch["blockers"] == []
    assert launch["claim_created"] is False
    # Keep the synthetic root short enough for Windows PowerShell 5.1 path APIs.
    claim = run_model4_launch_authority_validator(tmp_path / "lc", create_claim=True)
    assert claim["scoped"] is True
    assert claim["blockers"] == []
    assert claim["claim_created"] is True
    assert claim["duplicate_rejected"] is True
    unsafe_cases = [
        ("trades", {"trades_authorized": True}),
        ("broad_mt5", {"mt5_authorized": True}),
        ("wrong_symbol", {"authorized_symbol": "EURUSD"}),
        ("limit", {"authorized_launch_limit": 2}),
        ("consumed", {"authorized_launches_consumed": 1}),
    ]
    for name, overrides in unsafe_cases:
        rejected = run_model4_launch_authority_validator(
            tmp_path / f"launch_{name}",
            validation_overrides=overrides,
        )
        assert rejected["scoped"] is False
        assert any("exact one-shot XAUUSD" in item for item in rejected["blockers"])
    stale_runner = run_model4_launch_authority_validator(
        tmp_path / "launch_stale_runner",
        validation_overrides={"runner_engine_sha256": "F" * 64},
    )
    assert stale_runner["scoped"] is True
    assert any("runner_engine_sha256" in item for item in stale_runner["blockers"])
    stale_validator = run_model4_launch_authority_validator(
        tmp_path / "launch_stale_validator",
        validation_overrides={"candidate_registry_validator_sha256": "E" * 64},
    )
    assert stale_validator["scoped"] is True
    assert any("candidate_registry_validator_sha256" in item for item in stale_validator["blockers"])
    stale_alpha = run_model4_launch_authority_validator(
        tmp_path / "launch_stale_alpha",
        validation_overrides={"alpha_entrypoint_sha256": "D" * 64},
    )
    assert stale_alpha["scoped"] is True
    assert any("alpha_entrypoint_sha256" in item for item in stale_alpha["blockers"])
    stale_dependency = run_model4_launch_authority_validator(
        tmp_path / "launch_stale_dependency",
        validation_overrides={
            "execution_dependency_bindings": [
                {"path": "02. AlphaFactory/alpha.ps1", "sha256": "1" * 64}
            ]
        },
    )
    assert stale_dependency["scoped"] is True
    assert any("execution_dependency_bindings" in item for item in stale_dependency["blockers"])
    stale_receipt = run_model4_launch_authority_validator(
        tmp_path / "launch_stale_receipt",
        validation_overrides={"execute_gate_hardening_receipt_sha256": "2" * 64},
    )
    assert stale_receipt["scoped"] is True
    assert any("hardening receipt" in item for item in stale_receipt["blockers"])
    stale_bound_test = run_model4_launch_authority_validator(
        tmp_path / "launch_stale_bound_test",
        validation_overrides={
            "bound_tests": [
                {
                    "path": "02. AlphaFactory/tests/test_ea_golden_path.py",
                    "sha256": "6" * 64,
                }
            ]
        },
    )
    assert stale_bound_test["scoped"] is True
    assert any("bound_tests" in item for item in stale_bound_test["blockers"])
    stale_receipt_dependency = run_model4_launch_authority_validator(
        tmp_path / "launch_stale_receipt_dependency",
        validation_overrides={
            "hardening_receipt_overrides": {
                "control_plane": {
                    "runner": {
                        "path": "02. AlphaFactory/tools/research_loop_engine.ps1",
                        "sha256": hashlib.sha256(
                            (ALPHA_ROOT / "tools" / "research_loop_engine.ps1").read_bytes()
                        )
                        .hexdigest()
                        .upper(),
                    },
                    "candidate_registry_validator": {
                        "path": "04. Memory/research/validate_candidate_registry.py",
                        "sha256": "3" * 64,
                    },
                    "alpha_entrypoint": {"path": "02. AlphaFactory/alpha.ps1", "sha256": "4" * 64},
                    "execution_dependency_bindings": [
                        {"path": "02. AlphaFactory/alpha.ps1", "sha256": "5" * 64}
                    ],
                }
            }
        },
    )
    assert stale_receipt_dependency["scoped"] is True
    assert any("execute-gate receipt" in item for item in stale_receipt_dependency["blockers"])
    preexisting_claim = run_model4_launch_authority_validator(
        tmp_path / "launch_preexisting_claim",
        preexisting_claim=True,
    )
    assert preexisting_claim["scoped"] is True
    assert any("launch claim already exists" in item for item in preexisting_claim["blockers"])


def test_model4_execution_receipt_remains_alpha_contract_compatible(tmp_path: Path) -> None:
    receipt = run_model4_execution_receipt_builder(tmp_path)
    labels = set(receipt["labels"])
    assert receipt["schema_version"] == "alphafactory_execution_receipt.v1"
    assert receipt["authority"] == "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
    assert receipt["has_binding"] is True
    assert receipt["has_launch_claim"] is True
    assert {"task_packet", "candidate_registry", "source", "prereg", "cost_source_manifest", "launch_claim"} <= labels
    assert {
        "execution_control:runner",
        "execution_control:candidate_registry_validator",
        "execute_gate_hardening_receipt",
        "packet_set_authority_receipt",
        "execution_dependency:02. AlphaFactory/alpha.ps1",
        "execution_dependency:02. AlphaFactory/tools/mt5_storage_contract.ps1",
        "execution_dependency:02. AlphaFactory/tools/ea_contract.ps1",
        "execution_dependency:02. AlphaFactory/tools/log_storage.ps1",
        "execution_dependency:02. AlphaFactory/tools/audit_mql5_nonrepaint.py",
    } <= labels
    engine = (ALPHA_ROOT / "tools" / "research_loop_engine.ps1").read_text(encoding="utf-8-sig")
    assert "New-Model4CollectionLaunchClaim $contract $binding $packetResult $PSCommandPath" in engine
    assert "$postClaimGitSnapshot = Get-GitSnapshot $contract.CanonicalSourceAbsolute" in engine
    assert "$binding.GitStatusSha256 = $postClaimGitSnapshot.StatusSha256" in engine
    assert "New-ExecutionReceipt $receiptPath $contract $packetResult $binding $launchClaimRecord $PSCommandPath" in engine
    assert "[void]$immutableEvidencePaths.Add([string]$model4ControlPlane.RunnerPath)" in engine
    assert "[void]$immutableEvidencePaths.Add([string]$model4ControlPlane.ValidatorPath)" in engine
    assert "execute_gate_hardening_receipt_path" in engine
    assert "packet_set_dry_run_receipt_path" in engine
    assert "Add-Model4PostLockRevalidationBlockers" in engine
    assert engine.rindex("Enter-ImmutableEvidenceReadLocks") < engine.rindex(
        "Add-Model4PostLockRevalidationBlockers"
    )
    assert engine.rindex("Add-Model4PostLockRevalidationBlockers") < engine.index(
        "$launchClaimRecord = New-Model4CollectionLaunchClaim"
    )
    assert "$stream.Flush($true)" in engine
    assert "Get-ObjectProperty $model4Validation 'bound_tests'" in engine
    assert "Assert-CandidateRegistryValid" in engine
    assert "Get-LatestCandidateRegistryIdentity $Contract.RegistryPath $Contract.HypothesisId" in engine
    assert engine.rindex("Assert-CandidateRegistryValid") < engine.rindex(
        "Get-LatestCandidateRegistryIdentity $Contract.RegistryPath $Contract.HypothesisId"
    )


def test_model4_postlock_revalidation_reruns_canonical_registry_validator(tmp_path: Path) -> None:
    engine = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
    registry = tmp_path / "registry.jsonl"
    validator = tmp_path / "validate_candidate_registry.py"
    registry.write_text('{"hypothesis_id":"HYP-PTR-T2-DATA-EPOCH-D0-M5-005"}\n', encoding="utf-8")
    validator.write_text(
        "import sys\nprint('MUTATED_REGISTRY_REJECTED')\nsys.exit(7)\n",
        encoding="utf-8",
    )
    harness = tmp_path / "postlock_registry_validator.ps1"
    harness.write_text(r'''
param([string]$Engine, [string]$Registry, [string]$Validator)
$ErrorActionPreference = 'Stop'
$script:registryPath = $Registry
$script:registryValidatorPath = $Validator
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
foreach ($name in @(
    'Get-ObjectProperty',
    'Get-TextSha256',
    'Assert-CandidateRegistryValid',
    'Get-LatestCandidateRegistryIdentity',
    'Add-Model4PostLockRevalidationBlockers'
)) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
$contract = [pscustomobject]@{
    HypothesisId = 'HYP-PTR-T2-DATA-EPOCH-D0-M5-005'
    RegistryPath = $Registry
    RegistryLine = 1
    RegistryRowSha256 = 'A' * 64
}
$blockers = New-Object System.Collections.Generic.List[string]
Add-Model4PostLockRevalidationBlockers $contract $null $null $Engine $blockers
$blockers | ConvertTo-Json -Depth 4
''', encoding="utf-8")
    result = run_ps_file(
        harness,
        "-Engine",
        str(engine),
        "-Registry",
        str(registry),
        "-Validator",
        str(validator),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    blockers = json.loads(result.stdout.strip().splitlines()[-1])
    if isinstance(blockers, str):
        blockers = [blockers]
    assert any("canonical candidate registry validation failed" in item for item in blockers)
    assert any("MUTATED_REGISTRY_REJECTED" in item for item in blockers)


def test_model4_postlock_revalidation_rejects_latest_registry_row_identity_change(tmp_path: Path) -> None:
    engine = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
    registry = tmp_path / "registry.jsonl"
    validator = tmp_path / "validate_candidate_registry.py"
    first = '{"hypothesis_id":"HYP-PTR-T2-DATA-EPOCH-D0-M5-005","state":"screened"}'
    second = '{"hypothesis_id":"HYP-PTR-T2-DATA-EPOCH-D0-M5-005","state":"screened","mutated":true}'
    registry.write_text(first + "\n" + second + "\n", encoding="utf-8")
    validator.write_text("print('CANDIDATE_REGISTRY_OK rows=2 hypotheses=1')\n", encoding="utf-8")
    first_sha = hashlib.sha256(first.encode("utf-8")).hexdigest().upper()
    harness = tmp_path / "postlock_registry_identity.ps1"
    harness.write_text(r'''
param([string]$Engine, [string]$Registry, [string]$Validator, [string]$FirstSha)
$ErrorActionPreference = 'Stop'
$script:registryPath = $Registry
$script:registryValidatorPath = $Validator
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
foreach ($name in @(
    'Get-ObjectProperty',
    'Get-TextSha256',
    'Assert-CandidateRegistryValid',
    'Get-LatestCandidateRegistryIdentity',
    'Add-Model4PostLockRevalidationBlockers'
)) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
$contract = [pscustomobject]@{
    HypothesisId = 'HYP-PTR-T2-DATA-EPOCH-D0-M5-005'
    RegistryPath = $Registry
    RegistryLine = 1
    RegistryRowSha256 = $FirstSha
}
$blockers = New-Object System.Collections.Generic.List[string]
Add-Model4PostLockRevalidationBlockers $contract $null $null $Engine $blockers
$blockers | ConvertTo-Json -Depth 4
''', encoding="utf-8")
    result = run_ps_file(
        harness,
        "-Engine",
        str(engine),
        "-Registry",
        str(registry),
        "-Validator",
        str(validator),
        "-FirstSha",
        first_sha,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    blockers = json.loads(result.stdout.strip().splitlines()[-1])
    if isinstance(blockers, str):
        blockers = [blockers]
    assert any("latest registry row identity changed" in item for item in blockers)


def test_model4_collection_authority_passes_full_task_packet_gate(tmp_path: Path) -> None:
    engine = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
    harness = tmp_path / "resolve_hyp004_packet.ps1"
    harness.write_text(r'''
param([string]$Engine, [string]$Workspace, [string]$TmpRoot)
$ErrorActionPreference = 'Stop'
$repoRoot = $Workspace
$alphaRoot = Join-Path $repoRoot '02. AlphaFactory'
$researchRoot = Join-Path $repoRoot '04. Memory\research'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
$functions = @($ast.FindAll({ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst]
}, $true))
foreach ($fn in $functions) { Invoke-Expression $fn.Extent.Text }

function Test-ToRepoRelative([string]$Path) {
    $root = [System.IO.Path]::GetFullPath($Workspace).TrimEnd('\', '/')
    $full = [System.IO.Path]::GetFullPath($Path)
    if ($full.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $full.Substring($root.Length).TrimStart('\', '/').Replace('\','/')
    }
    return $full.Replace('\','/')
}

New-Item -ItemType Directory -Path $TmpRoot -Force | Out-Null
$epoch = Join-Path $TmpRoot 'epoch.json'
$registry = Join-Path $TmpRoot 'registry.jsonl'
$prereg = Join-Path $TmpRoot 'PROBE_PLAN.json'
$source = Join-Path $TmpRoot 'EA_PTR_T2_DataEpochD0V3.mq5'
Set-Content -LiteralPath $epoch -Value (
    '{"server":"FivePercentOnline-Real","timeframe":"M5","tester_model":4}'
) -NoNewline -Encoding UTF8
Set-Content -LiteralPath $registry -Value "{}" -NoNewline -Encoding UTF8
Set-Content -LiteralPath $prereg -Value "{}" -NoNewline -Encoding UTF8
$epochSha = Get-Sha256IfExists $epoch
Set-Content -LiteralPath $source -Value (
    "input string InpEpochManifestSha256=`"$epochSha`";`n" +
    "bool BindEpoch(string value){ return value==`"$epochSha`"; }"
) -NoNewline -Encoding UTF8
$epochRel = Test-ToRepoRelative $epoch
$cost = Join-Path $TmpRoot 'collection_cost.json'
$costPayload = [ordered]@{
    schema_version = 'alphafactory_cost_source_manifest.v1'
    evidence_tier = 'DATA_ACQUISITION_ONLY'
    provenance_status = 'UNVERIFIED'
    audit_status = 'NOT_APPLICABLE'
    verdict = 'NO_ECONOMIC_AUTHORITY'
    promotion_eligible = $false
    performance_metrics_authorized = $false
    economics_authorized = $false
    authority = 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    epoch_manifest_path = $epochRel
    epoch_manifest_sha256 = $epochSha
    note = 'Costs are UNVERIFIED and no economic metric is authorized.'
}
Write-JsonAtomically $costPayload $cost 8
$costRel = Test-ToRepoRelative $cost
$acceptance = [pscustomobject][ordered]@{
    min_profit_factor = 1.3
    min_trades_per_week = 2.0
    max_trades_per_week = 5.0
    max_drawdown_pct = 8.0
    min_cost_pf_x1_5 = 1.25
    min_cost_pf_x2 = 1.0
    max_monte_carlo_p95_dd_pct = 8.0
}
$contract = [pscustomobject]@{
    HypothesisId = 'HYP-PTR-T2-DATA-EPOCH-D0-M5-004'
    CanonicalSourcePath = Test-ToRepoRelative $source
    CanonicalSourceAbsolute = $source
    CurrentSourceSha256 = Get-Sha256IfExists $source
    RegistryPath = $registry
    RegistrySha256 = Get-Sha256IfExists $registry
    RegistryRowSha256 = 'A' * 64
    RegisteredPreregPath = Test-ToRepoRelative $prereg
    PreregSha256 = Get-Sha256IfExists $prereg
    TelemetryProfile = 'none'
    ComparisonAdapter = 'none'
    AcceptanceContract = $acceptance
    EaContractSha256 = ''
    EaContractPath = ''
}
$binding = [pscustomobject]@{
    RunRole = 'control'
    EaName = 'EA_PTR_T2_DataEpochD0V3'
    Symbol = 'XAUUSD'
    Period = 'M5'
    From = '1970.01.01'
    To = '2026.07.30'
    Model = 4
    ExecutionMode = 0
    FixedDelayMs = 0
    Overrides = "InpCollectionOnly=true;InpEpochManifestSha256=$epochSha"
    TelemetryProfile = 'none'
    TelemetryTier = 'off'
    Deposit = 10000
    Leverage = 100
    Spread = '0'
    ValidationStage = 'challenger'
    HoldingContract = 'scalp'
    GitCommit = '0123456789abcdef0123456789abcdef01234567'
    GitStatusSha256 = 'B' * 64
    GitStatus = @(' M harness')
    CostSourceManifest = $costRel
    AllowResearchCostProxy = $false
    WfaArtifact = ''
    VariantsDir = ''
    MatchedControlRunId = ''
}
$packet = [ordered]@{
    schema_version = 'alphafactory_research_task_packet.v1'
    hypothesis_id = $contract.HypothesisId
    run_role = $binding.RunRole
    ea_name = $binding.EaName
    source_path = $contract.CanonicalSourcePath
    source_sha256 = $contract.CurrentSourceSha256
    registry_path = Test-ToRepoRelative $registry
    registry_sha256 = $contract.RegistrySha256
    registry_row_sha256 = $contract.RegistryRowSha256
    prereg_path = $contract.RegisteredPreregPath
    prereg_sha256 = $contract.PreregSha256
    telemetry_profile = $contract.TelemetryProfile
    comparison_adapter = $contract.ComparisonAdapter
    indicator_dependencies = @()
    acceptance_contract = $acceptance
    symbol = $binding.Symbol
    period = $binding.Period
    from = $binding.From
    to = $binding.To
    model = $binding.Model
    execution_mode = $binding.ExecutionMode
    fixed_delay_ms = $binding.FixedDelayMs
    overrides = $binding.Overrides
    telemetry_tier = $binding.TelemetryTier
    deposit = $binding.Deposit
    leverage = $binding.Leverage
    spread = $binding.Spread
    validation_stage = $binding.ValidationStage
    holding_contract = $binding.HoldingContract
    git_commit = $binding.GitCommit
    git_status_sha256 = $binding.GitStatusSha256
    git_status = @($binding.GitStatus)
    data_quality_contract = [ordered]@{
        history_quality = [ordered]@{ operator = 'gt'; value = 97.0 }
        coverage_mode = 'all_available_asof'
        availability_asof_utc = '2026-07-30T00:00:00Z'
        requested_from = $binding.From
        requested_to = $binding.To
        require_tester_journal_bounds = $true
    }
    authority = 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    include_closure = @()
    include_closure_sha256 = Get-PathHashSetSha256 @()
    broker_fingerprint = 'C' * 64
    server_fingerprint = 'D' * 64
    account_fingerprint = 'E' * 64
    data_fingerprint = 'F' * 64
    symbol_geometry = [ordered]@{ digits = 2; point = 0.01; pip_size = 0.01 }
    required_sidecars = @()
    required_manifest_hashes = @('source_sha256', 'config_sha256', 'report_sha256', 'ex5_sha256', 'includes_sha256')
    cost_evidence_tier = 'data_acquisition_only'
    cost_source_manifest_path = $costRel
    cost_source_manifest_sha256 = Get-Sha256IfExists $cost
    wfa_artifact_path = ''
    variants_dir = ''
}

function Copy-JsonObject($Object) {
    return ($Object | ConvertTo-Json -Depth 20 | ConvertFrom-Json)
}

function Invoke-Case($Name, $Patch) {
    $casePacket = Copy-JsonObject $packet
    $caseBinding = Copy-JsonObject $binding
    & $Patch $casePacket $caseBinding
    $packetPath = Join-Path $TmpRoot "$Name.packet.json"
    Write-JsonAtomically $casePacket $packetPath 12
    $result = Resolve-TaskPacket $packetPath $contract $caseBinding
    [pscustomobject]@{
        name = $Name
        authority = $result.Authority
        blockers = @($result.Blockers | ForEach-Object { [string]$_ })
    }
}

$results = @(
    Invoke-Case 'valid_model4_collection' { param($p, $b) }
    Invoke-Case 'missing_authority_model4' { param($p, $b) $p.PSObject.Properties.Remove('authority') }
    Invoke-Case 'old_authority_model4' { param($p, $b) $p.authority = 'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE' }
    Invoke-Case 'new_authority_challenger_role' { param($p, $b) $p.run_role = 'challenger'; $b.RunRole = 'challenger' }
)
$results | ConvertTo-Json -Depth 8
''', encoding="utf-8")
    work_tmp = ALPHA_ROOT / "tmp" / f"pytest_model4_packet_{tmp_path.name}"
    if work_tmp.exists():
        shutil.rmtree(work_tmp)
    result = run_ps_file(
        harness,
        "-Engine",
        str(engine),
        "-Workspace",
        str(WORKSPACE),
        "-TmpRoot",
        str(work_tmp),
    )
    if work_tmp.exists():
        shutil.rmtree(work_tmp)
    assert result.returncode == 0, result.stdout + result.stderr
    rows = {row["name"]: row for row in json.loads(result.stdout)}
    assert rows["valid_model4_collection"]["authority"] == "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
    assert rows["valid_model4_collection"]["blockers"] == [], rows["valid_model4_collection"]["blockers"]
    assert any("Model=0" in item for item in rows["missing_authority_model4"]["blockers"])
    assert any("Model=0" in item for item in rows["old_authority_model4"]["blockers"])
    assert any("RunRole=control" in item for item in rows["new_authority_challenger_role"]["blockers"])


def test_collection_authority_is_receipt_bound_and_stops_before_economics() -> None:
    engine = (ALPHA_ROOT / "tools" / "research_loop_engine.ps1").read_text(encoding="utf-8-sig")
    alpha = ALPHA.read_text(encoding="utf-8-sig")
    authority = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
    assert "$receipt['authority'] = [string]$PacketResult.Authority" in engine
    assert 'Assert-ZeroTradeCollectionSummary' in engine
    assert 'data_acquisition_verified' in engine
    assert 'economic validation was forbidden' in engine
    assert "Unsupported contract receipt authority" in alpha
    assert "authority does not match its hash-bound task packet" in alpha
    assert "required frozen History Quality >97 contract" in alpha
    assert "DATA_ACQUISITION_ONLY_NO_PERFORMANCE" in engine
    assert "DATA_ACQUISITION_ONLY_NO_PERFORMANCE" in alpha

    generic_template = json.loads(
        (ALPHA_ROOT / "templates" / "research" / "TASK_PACKET.control.template.json").read_text(encoding="utf-8")
    )
    collection_template = json.loads(
        (ALPHA_ROOT / "templates" / "research" / "TASK_PACKET.data_acquisition.template.json").read_text(encoding="utf-8")
    )
    assert "authority" not in generic_template
    assert collection_template["authority"] == authority
    assert collection_template["telemetry_profile"] == "none"
    assert collection_template["telemetry_tier"] == "off"
    assert collection_template["required_sidecars"] == []


def test_zero_trade_collection_summary_rejects_metric_leakage(tmp_path: Path) -> None:
    engine = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
    valid_path = tmp_path / "valid.json"
    forged_path = tmp_path / "forged.json"
    base = {
        "schema_version": "alphafactory_zero_trade_collection_summary.v1",
        "analysis_mode": "data_acquisition_only",
        "authority": "DATA_ACQUISITION_ONLY_NO_PERFORMANCE",
        "n_trades": 0,
        "performance_metrics_authorized": False,
        "generated_at_utc": "2026-07-31T00:00:00Z",
    }
    valid_path.write_text(json.dumps(base), encoding="utf-8")
    forged_path.write_text(json.dumps({**base, "profit_factor": 9.99}), encoding="utf-8")
    harness = tmp_path / "validate_zero_trade_summary.ps1"
    harness.write_text(r'''
param([string]$Engine, [string]$ValidPath, [string]$ForgedPath)
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
foreach ($name in @('Test-IntegerValue', 'Assert-ZeroTradeCollectionSummary')) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
$authority = 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
[void](Assert-ZeroTradeCollectionSummary $ValidPath $authority)
$forgedRejected = $false
try { [void](Assert-ZeroTradeCollectionSummary $ForgedPath $authority) } catch { $forgedRejected = $true }
if (-not $forgedRejected) { throw 'Forged performance field was accepted.' }
Write-Output 'PASS'
''', encoding="utf-8")
    result = run_ps_file(
        harness,
        "-Engine",
        str(engine),
        "-ValidPath",
        str(valid_path),
        "-ForgedPath",
        str(forged_path),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout


def test_collection_cost_manifest_preserves_unverified_no_economics_contract(tmp_path: Path) -> None:
    model0_epoch = WORKSPACE / "04. Memory" / "research" / "PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH.json"
    model4_epoch = WORKSPACE / "04. Memory" / "research" / "PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH_V3.json"
    model0_authority = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
    model4_authority = "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
    manifest = {
        "schema_version": "alphafactory_cost_source_manifest.v1",
        "evidence_tier": "DATA_ACQUISITION_ONLY",
        "provenance_status": "UNVERIFIED",
        "audit_status": "NOT_APPLICABLE",
        "verdict": "NO_ECONOMIC_AUTHORITY",
        "promotion_eligible": False,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "authority": model4_authority,
        "epoch_manifest_path": str(model4_epoch.relative_to(WORKSPACE)).replace("\\", "/"),
        "epoch_manifest_sha256": hashlib.sha256(model4_epoch.read_bytes()).hexdigest().upper(),
        "note": "Costs are UNVERIFIED and no economic metric is authorized.",
    }
    valid = tmp_path / "collection_cost.json"
    forged = tmp_path / "forged_cost.json"
    valid.write_text(json.dumps(manifest), encoding="utf-8")
    forged.write_text(json.dumps({**manifest, "economics_authorized": True}), encoding="utf-8")
    harness = tmp_path / "validate_collection_cost.ps1"
    harness.write_text(r'''
param([string]$Engine, [string]$Workspace, [string]$Valid, [string]$Forged)
$script:repoRoot = $Workspace
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
foreach ($name in @(
    'Test-Sha256Text', 'Get-Sha256IfExists', 'Test-ProvenanceObject', 'Get-ObjectProperty',
    'Test-IntegerValue',
    'Test-ExactObjectKeys', 'Resolve-EvidencePath', 'Resolve-CostEvidenceFile',
    'Resolve-CollectionCostManifest'
)) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
$authority = 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
$binding = [pscustomobject]@{ Period = 'M5'; Model = 4 }
$validBlockers = New-Object System.Collections.Generic.List[string]
$validContract = Resolve-CollectionCostManifest (Get-Content -LiteralPath $Valid -Raw | ConvertFrom-Json) $authority $binding $validBlockers
if ($validBlockers.Count -ne 0 -or $null -eq $validContract) { throw "Valid collection manifest rejected: $($validBlockers -join '; ')" }
if ($validContract.Server -cne 'FivePercentOnline-Real' -or $validContract.Period -cne 'M5') { throw 'Collection identity was not bound from the epoch manifest.' }
$forgedBlockers = New-Object System.Collections.Generic.List[string]
[void](Resolve-CollectionCostManifest (Get-Content -LiteralPath $Forged -Raw | ConvertFrom-Json) $authority $binding $forgedBlockers)
if (-not @($forgedBlockers | Where-Object { $_ -like '*forbid*economics*' })) { throw 'Forged economics authority was accepted.' }
Write-Output 'PASS'
''', encoding="utf-8")
    result = run_ps_file(
        harness,
        "-Engine",
        str(ALPHA_ROOT / "tools" / "research_loop_engine.ps1"),
        "-Workspace",
        str(WORKSPACE),
        "-Valid",
        str(valid),
        "-Forged",
        str(forged),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout

    legacy_path = tmp_path / "legacy_collection_cost.json"
    legacy_path.write_text(
        json.dumps(
            {
                **manifest,
                "authority": model0_authority,
                "epoch_manifest_path": str(model0_epoch.relative_to(WORKSPACE)).replace("\\", "/"),
                "epoch_manifest_sha256": hashlib.sha256(model0_epoch.read_bytes()).hexdigest().upper(),
            }
        ),
        encoding="utf-8",
    )
    legacy_harness = tmp_path / "validate_legacy_collection_cost.ps1"
    legacy_harness.write_text(r'''
param([string]$Engine, [string]$Workspace, [string]$Valid)
$script:repoRoot = $Workspace
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
foreach ($name in @(
    'Test-Sha256Text', 'Get-Sha256IfExists', 'Test-ProvenanceObject', 'Get-ObjectProperty',
    'Test-IntegerValue',
    'Test-ExactObjectKeys', 'Resolve-EvidencePath', 'Resolve-CostEvidenceFile',
    'Resolve-CollectionCostManifest'
)) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
$authority = 'DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE'
$binding = [pscustomobject]@{ Period = 'M5'; Model = 0 }
$blockers = New-Object System.Collections.Generic.List[string]
$contract = Resolve-CollectionCostManifest (Get-Content -LiteralPath $Valid -Raw | ConvertFrom-Json) $authority $binding $blockers
if ($blockers.Count -ne 0 -or $null -eq $contract) { throw "Legacy collection manifest rejected: $($blockers -join '; ')" }
Write-Output 'PASS'
''', encoding="utf-8")
    legacy_result = run_ps_file(
        legacy_harness,
        "-Engine",
        str(ALPHA_ROOT / "tools" / "research_loop_engine.ps1"),
        "-Workspace",
        str(WORKSPACE),
        "-Valid",
        str(legacy_path),
    )
    assert legacy_result.returncode == 0, legacy_result.stdout + legacy_result.stderr
    assert "PASS" in legacy_result.stdout


def test_data_quality_contract_validates_and_normalizes(tmp_path: Path) -> None:
    result = run_data_quality_contract_validator(tmp_path, valid_data_quality_packet())
    assert result["blockers"] == []
    assert result["contract"]["history_quality"] == {"operator": "gt", "value": 97.0}
    assert result["contract"]["coverage_mode"] == "all_available_asof"
    assert result["contract"]["availability_asof_utc"] == "2025-12-31T23:59:59Z"
    assert result["contract"]["requested_from"] == "1970.01.01"
    assert result["contract"]["requested_to"] == "2025.12.31"
    assert result["contract"]["require_tester_journal_bounds"] is True


def test_fixed_window_data_quality_contract_validates_and_normalizes(tmp_path: Path) -> None:
    packet = valid_data_quality_packet()
    packet["data_quality_contract"].update({
        "coverage_mode": "fixed_window",
        "requested_from": "2016.01.04",
        "requested_to": "2020.12.31",
    })
    result = run_data_quality_contract_validator(
        tmp_path,
        packet,
        from_date="2016.01.04",
        to_date="2020.12.31",
    )
    assert result["blockers"] == []
    assert result["contract"]["coverage_mode"] == "fixed_window"
    assert result["contract"]["requested_from"] == "2016.01.04"
    assert result["contract"]["requested_to"] == "2020.12.31"


def test_data_quality_contract_absence_is_legacy_compatible(tmp_path: Path) -> None:
    result = run_data_quality_contract_validator(tmp_path, {})
    assert result["blockers"] == []
    assert result["contract"] is None


def test_registered_data_acceptance_is_symbol_and_quality_bound(tmp_path: Path) -> None:
    assert POWERSHELL, "PowerShell is required"
    engine = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
    registered = tmp_path / "registered.json"
    quality = tmp_path / "quality.json"
    registered.write_text(
        json.dumps({
            "history_quality_operator": "gt",
            "history_quality_threshold_pct": 97.0,
            "coverage_mode": "all_available_asof",
            "mandatory_symbols": ["XAUUSD", "EURUSD"],
            "no_skip": True,
            "require_tester_journal_bounds": True,
            "require_series_proof": True,
        }),
        encoding="utf-8",
    )
    quality.write_text(
        json.dumps(valid_data_quality_packet()["data_quality_contract"]),
        encoding="utf-8",
    )
    harness = tmp_path / "data_acceptance.ps1"
    harness.write_text(
        r'''
param([string]$Engine,[string]$Registered,[string]$Quality,[string]$Symbol)
$ErrorActionPreference='Stop'
$tokens=$null;$parseErrors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($Engine,[ref]$tokens,[ref]$parseErrors)
foreach($name in @('Get-ObjectProperty','Test-ProvenanceObject','Add-RegisteredDataAcceptanceBlockers')){
    $fn=$ast.Find({param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    },$true)
    if($null -eq $fn){throw "Missing function $name"}
    Invoke-Expression $fn.Extent.Text
}
$registeredObject=Get-Content -LiteralPath $Registered -Raw|ConvertFrom-Json
$qualityObject=Get-Content -LiteralPath $Quality -Raw|ConvertFrom-Json
$blockers=New-Object System.Collections.Generic.List[string]
Add-RegisteredDataAcceptanceBlockers $registeredObject $qualityObject ([pscustomobject]@{Symbol=$Symbol}) $blockers
[pscustomobject]@{blockers=@($blockers|ForEach-Object{[string]$_})}|ConvertTo-Json
''',
        encoding="utf-8",
    )
    valid = run_ps_file(
        harness,
        "-Engine", str(engine), "-Registered", str(registered),
        "-Quality", str(quality), "-Symbol", "XAUUSD",
    )
    assert valid.returncode == 0, valid.stdout + valid.stderr
    assert json.loads(valid.stdout)["blockers"] == []

    invalid = run_ps_file(
        harness,
        "-Engine", str(engine), "-Registered", str(registered),
        "-Quality", str(quality), "-Symbol", "BTCUSD",
    )
    assert invalid.returncode == 0, invalid.stdout + invalid.stderr
    assert "outside the frozen mandatory_symbols" in " ".join(json.loads(invalid.stdout)["blockers"])


def test_data_quality_contract_rejects_malformed_cases(tmp_path: Path) -> None:
    cases = [
        ("extra_key", lambda pkt: pkt["data_quality_contract"].update({"unexpected": True}), "must contain exactly"),
        ("missing_key", lambda pkt: pkt["data_quality_contract"].pop("coverage_mode"), "must contain exactly"),
        ("bad_history_operator", lambda pkt: pkt["data_quality_contract"]["history_quality"].update({"operator": "gte"}), "operator must equal 'gt'"),
        ("bad_history_value", lambda pkt: pkt["data_quality_contract"]["history_quality"].update({"value": "97"}), "value must be a finite number"),
        ("negative_history_value", lambda pkt: pkt["data_quality_contract"]["history_quality"].update({"value": -1}), "in [97,100)"),
        ("below_required_history_value", lambda pkt: pkt["data_quality_contract"]["history_quality"].update({"value": 96.999}), "in [97,100)"),
        ("impossible_history_value", lambda pkt: pkt["data_quality_contract"]["history_quality"].update({"value": 100}), "in [97,100)"),
        ("oversized_history_value", lambda pkt: pkt["data_quality_contract"]["history_quality"].update({"value": 101}), "in [97,100)"),
        ("bad_coverage_mode", lambda pkt: pkt["data_quality_contract"].update({"coverage_mode": "broker_history_sync"}), "coverage_mode must equal 'all_available_asof' or 'fixed_window'"),
        ("bad_timestamp", lambda pkt: pkt["data_quality_contract"].update({"availability_asof_utc": "2026-07-31T00:00:00+00:00"}), "must be a Z timestamp"),
        ("future_timestamp", lambda pkt: pkt["data_quality_contract"].update({"availability_asof_utc": "2999-12-31T23:59:59Z", "requested_to": "2999.12.31"}), "must not be in the future"),
        ("bad_date_format", lambda pkt: pkt["data_quality_contract"].update({"requested_from": "2020-01-01"}), "requested_from must use YYYY.MM.DD"),
        ("impossible_date", lambda pkt: pkt["data_quality_contract"].update({"requested_from": "2020.13.40"}), "requested_from must use YYYY.MM.DD"),
        ("asof_date_mismatch", lambda pkt: pkt["data_quality_contract"].update({"availability_asof_utc": "2025-12-30T23:59:59Z"}), "must equal the UTC calendar date"),
        ("bad_journal_flag", lambda pkt: pkt["data_quality_contract"].update({"require_tester_journal_bounds": False}), "require_tester_journal_bounds must be true"),
    ]
    for name, mutate, expected in cases:
        packet = valid_data_quality_packet()
        mutate(packet)
        result = run_data_quality_contract_validator(tmp_path / name, packet)
        assert any(expected in blocker for blocker in result["blockers"]), result
        assert result["contract"] is None


def test_data_quality_contract_requested_range_must_match_binding(tmp_path: Path) -> None:
    packet = valid_data_quality_packet()
    packet["data_quality_contract"]["requested_to"] = "2026.01.01"
    result = run_data_quality_contract_validator(tmp_path, packet)
    assert any("requested_to must match task packet/to binding '2025.12.31'" in blocker for blocker in result["blockers"])
    assert result["contract"] is None


def test_data_quality_contract_requires_all_available_sentinel(tmp_path: Path) -> None:
    packet = valid_data_quality_packet()
    packet["data_quality_contract"]["requested_from"] = "2020.01.01"
    result = run_data_quality_contract_validator(tmp_path, packet, from_date="2020.01.01")
    assert any("frozen sentinel '1970.01.01'" in blocker for blocker in result["blockers"])
    assert result["contract"] is None


def test_data_quality_contract_field_name_is_case_sensitive(tmp_path: Path) -> None:
    packet = valid_data_quality_packet()
    packet["Data_Quality_Contract"] = packet.pop("data_quality_contract")
    result = run_data_quality_contract_validator(tmp_path, packet)
    assert any("exactly case-sensitive 'data_quality_contract'" in blocker for blocker in result["blockers"])
    assert result["contract"] is None


def test_data_quality_contract_is_propagated_into_execution_receipt_binding(tmp_path: Path) -> None:
    engine = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
    harness = tmp_path / "receipt_binding.ps1"
    harness.write_text(r'''
param([string]$Engine)
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
$fn = $ast.Find({ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -ceq 'Add-DataQualityContractToReceiptBinding'
}, $true)
if ($null -eq $fn) { throw 'Missing Add-DataQualityContractToReceiptBinding' }
Invoke-Expression $fn.Extent.Text
$present = [ordered]@{ hypothesis_id = 'HYP-TEST' }
$contract = [ordered]@{ coverage_mode = 'all_available_asof' }
Add-DataQualityContractToReceiptBinding $present $contract
$legacy = [ordered]@{ hypothesis_id = 'HYP-LEGACY' }
Add-DataQualityContractToReceiptBinding $legacy $null
[pscustomobject]@{ present = $present; legacy = $legacy } | ConvertTo-Json -Depth 6
''', encoding="utf-8")
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness), "-Engine", str(engine)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["present"]["data_quality_contract"] == {"coverage_mode": "all_available_asof"}
    assert "data_quality_contract" not in payload["legacy"]


def test_post_run_data_quality_gate_is_recomputed_and_packet_bound(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True)
    journal = logs_dir / "tester_journal_delta.log"
    journal.write_text(
        "EURUSD: history synchronized from 2021.02.01 to 2024.12.31\n"
        "DATA_EPOCH_D0_SERIES_PROOF symbol=EURUSD m5_synchronized=1 m5_first_epoch=1612137600 "
        "m5_terminal_first_epoch=1612137600 m1_server_first_epoch=1612137600 "
        "m1_terminal_first_epoch=1612137600 m5_bars=100001 terminal_maxbars=100000 "
        "copytime_from_epoch=1612137600 copytime_count=1 copytime_result=1 "
        "copytime_first_epoch=1612137600 copytime_last_error=0\n",
        encoding="utf-8",
    )
    report = run_dir / "report.html"
    report.write_text(
        "<html><table><tr><td>History Quality:</td><td><b>99%</b></td></tr></table></html>",
        encoding="utf-8",
    )
    engine = ALPHA_ROOT / "tools" / "research_loop_engine.ps1"
    harness = tmp_path / "post_run_data_quality.ps1"
    harness.write_text(r'''
param([string]$Engine, [string]$RunDir)
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Engine, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | ForEach-Object { $_.Message } | Out-String) }
$needed = @(
    'Get-Sha256IfExists', 'Get-TextSha256', 'Test-Sha256Text',
    'Test-ProvenanceObject', 'Get-ObjectProperty', 'Test-FiniteNumber',
    'Test-ExactObjectKeys', 'Test-ResearchDate', 'Test-ZuluTimestamp', 'Test-IntegerValue',
    'Resolve-DataQualityContract',
    'Get-DataQualityReportHistoryQuality',
    'Get-DataQualityHistoryRangeFromJournal',
    'Get-DataQualitySeriesProofFromJournal',
    'Assert-DataQualityModel4JournalMode',
    'Assert-DataQualityManifestMatchesPacket'
)
foreach ($name in $needed) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
$rawPacket = [pscustomobject]@{
    data_quality_contract = [pscustomobject][ordered]@{
        history_quality = [pscustomobject][ordered]@{ operator = 'gt'; value = 97.0 }
        coverage_mode = 'all_available_asof'
        availability_asof_utc = '2024-12-31T23:59:59Z'
        requested_from = '1970.01.01'
        requested_to = '2024.12.31'
        require_tester_journal_bounds = $true
    }
}
$resolveBlockers = New-Object System.Collections.Generic.List[string]
$packetContract = Resolve-DataQualityContract $rawPacket ([pscustomobject]@{ From = '1970.01.01'; To = '2024.12.31' }) $resolveBlockers
if ($resolveBlockers.Count -ne 0 -or $null -eq $packetContract) { throw "Production contract resolution failed: $($resolveBlockers -join '; ')" }
$contract = [pscustomobject][ordered]@{
    schema_version = 'alphafactory_data_quality_contract.v1'
    symbol = 'EURUSD'
    requested_from = '1970.01.01'
    requested_to = '2024.12.31'
    history_quality_threshold = 97.0
    coverage_mode = 'all_available_asof'
    availability_asof_utc = '2024-12-31T23:59:59.0000000Z'
    require_tester_journal_bounds = $true
    max_journal_delta_bytes = 1048576
}
$journalPath = Join-Path $RunDir 'logs\tester_journal_delta.log'
$journalSha = Get-Sha256IfExists $journalPath
$journalBytes = (Get-Item -LiteralPath $journalPath).Length
$reportPath = Join-Path $RunDir 'report.html'
$reportSha = Get-Sha256IfExists $reportPath
$gate = [pscustomobject][ordered]@{
    contract = $contract
    history_quality = 99.0
    actual_from = '2021.02.01'
    actual_to = '2024.12.31'
    coverage_class = 'BROKER_LIMITED_START'
    series_proof = [pscustomobject][ordered]@{
        symbol = 'EURUSD'
        m5_synchronized = 1; m5_first_epoch = 1612137600; m5_terminal_first_epoch = 1612137600
        m1_server_first_epoch = 1612137600; m1_terminal_first_epoch = 1612137600
        m5_bars = 100001; terminal_maxbars = 100000; copytime_from_epoch = 1612137600
        copytime_count = 1; copytime_result = 1; copytime_first_epoch = 1612137600; copytime_last_error = 0
    }
    journal_path = 'logs/tester_journal_delta.log'
    journal_sha256 = $journalSha
    journal_bytes_read = $journalBytes
    journal_files_read = 1
    journal_truncated = $false
    exact_match_count = 1
    distinct_range_count = 1
}
$fingerprintBasis = [pscustomobject][ordered]@{
    schema_version = 'alphafactory_data_quality_fingerprint.v1'
    base_data_fingerprint = ('A' * 64)
    contract = $contract
    history_quality = 99.0
    actual_from = '2021.02.01'
    actual_to = '2024.12.31'
    coverage_class = 'BROKER_LIMITED_START'
    series_proof = $gate.series_proof
    journal_sha256 = $journalSha
    journal_bytes_read = $journalBytes
    journal_files_read = 1
    journal_truncated = $false
    exact_match_count = 1
    distinct_range_count = 1
}
$manifest = [pscustomobject]@{
    symbol = 'EURUSD'
    period = 'M5'
    local_run_dir = $RunDir
    report_path = $reportPath
    report_sha256 = $reportSha
    data_fingerprint = ('A' * 64)
    data_quality_contract = $contract
    data_quality_journal_delta = [pscustomobject][ordered]@{
        path = 'logs/tester_journal_delta.log'; sha256 = $journalSha
        bytes_read = $journalBytes; files_read = 1; truncated = $false
    }
    data_quality_gate = $gate
    data_quality_fingerprint_basis = $fingerprintBasis
    data_quality_fingerprint = Get-TextSha256 ($fingerprintBasis | ConvertTo-Json -Depth 12 -Compress)
}
$packetResult = [pscustomobject]@{ DataQualityContract = $packetContract }
Assert-DataQualityManifestMatchesPacket $manifest $packetResult $RunDir
$manifest.data_quality_fingerprint = ('B' * 64)
$tamperRejected = $false
try { Assert-DataQualityManifestMatchesPacket $manifest $packetResult $RunDir } catch { $tamperRejected = $true }
if (-not $tamperRejected) { throw 'Tampered data-quality fingerprint was accepted.' }
$manifest.data_quality_gate.history_quality = 98.0
$manifest.data_quality_fingerprint_basis.history_quality = 98.0
$manifest.data_quality_fingerprint = Get-TextSha256 ($manifest.data_quality_fingerprint_basis | ConvertTo-Json -Depth 12 -Compress)
$reportClaimRejected = $false
try { Assert-DataQualityManifestMatchesPacket $manifest $packetResult $RunDir } catch { $reportClaimRejected = $true }
if (-not $reportClaimRejected) { throw 'Report-contradicting History Quality was accepted.' }
$manifest.data_quality_gate.history_quality = 99.0
$manifest.data_quality_fingerprint_basis.history_quality = 99.0
$manifest.data_quality_gate.actual_from = '2025.01.01'
$manifest.data_quality_fingerprint_basis.actual_from = '2025.01.01'
$manifest.data_quality_fingerprint = Get-TextSha256 ($manifest.data_quality_fingerprint_basis | ConvertTo-Json -Depth 12 -Compress)
$reversedRejected = $false
try { Assert-DataQualityManifestMatchesPacket $manifest $packetResult $RunDir } catch { $reversedRejected = $true }
if (-not $reversedRejected) { throw 'Reversed actual history bounds were accepted.' }
$manifest.data_quality_gate.actual_from = '2021.03.01'
$manifest.data_quality_fingerprint_basis.actual_from = '2021.03.01'
$manifest.data_quality_fingerprint = Get-TextSha256 ($manifest.data_quality_fingerprint_basis | ConvertTo-Json -Depth 12 -Compress)
$journalClaimRejected = $false
try { Assert-DataQualityManifestMatchesPacket $manifest $packetResult $RunDir } catch { $journalClaimRejected = $true }
if (-not $journalClaimRejected) { throw 'Journal-contradicting history claim was accepted.' }
$manifest.local_run_dir = Split-Path -Parent $RunDir
$externalRootRejected = $false
try { Assert-DataQualityManifestMatchesPacket $manifest $packetResult $RunDir } catch { $externalRootRejected = $true }
if (-not $externalRootRejected) { throw 'External manifest local_run_dir was accepted.' }
$legacyManifest = [pscustomobject]@{
    data_quality_contract = $null
    data_quality_journal_delta = $null
}
Assert-DataQualityManifestMatchesPacket $legacyManifest ([pscustomobject]@{ DataQualityContract = $null }) $RunDir

function Update-JournalEvidence([string]$Text) {
    [System.IO.File]::WriteAllText($journalPath, $Text, [System.Text.UTF8Encoding]::new($false))
    $script:journalSha = Get-Sha256IfExists $journalPath
    $script:journalBytes = (Get-Item -LiteralPath $journalPath).Length
    $manifest.data_quality_journal_delta.sha256 = $script:journalSha
    $manifest.data_quality_journal_delta.bytes_read = $script:journalBytes
    $manifest.data_quality_gate.journal_sha256 = $script:journalSha
    $manifest.data_quality_gate.journal_bytes_read = $script:journalBytes
    $manifest.data_quality_fingerprint_basis.journal_sha256 = $script:journalSha
    $manifest.data_quality_fingerprint_basis.journal_bytes_read = $script:journalBytes
    $manifest.data_quality_fingerprint = Get-TextSha256 ($manifest.data_quality_fingerprint_basis | ConvertTo-Json -Depth 12 -Compress)
}

$baseJournal = "EURUSD: history synchronized from 2021.02.01 to 2024.12.31`n" +
    "DATA_EPOCH_D0_SERIES_PROOF symbol=EURUSD m5_synchronized=1 m5_first_epoch=1612137600 m5_terminal_first_epoch=1612137600 m1_server_first_epoch=1612137600 m1_terminal_first_epoch=1612137600 m5_bars=100001 terminal_maxbars=100000 copytime_from_epoch=1612137600 copytime_count=1 copytime_result=1 copytime_first_epoch=1612137600 copytime_last_error=0`n"
$manifest.local_run_dir = $RunDir
$manifest.data_quality_gate.actual_from = '2021.02.01'
$manifest.data_quality_fingerprint_basis.actual_from = '2021.02.01'
$manifest | Add-Member -MemberType NoteProperty -Name model -Value 4 -Force
$model4PacketResult = [pscustomobject]@{
    DataQualityContract = $packetContract
    Authority = 'DATA_ACQUISITION_ONLY_NO_PERFORMANCE'
    CollectionSymbol = 'EURUSD'
    CollectionPeriod = 'M5'
    CollectionServer = 'FivePercentOnline-Real'
}
Update-JournalEvidence $baseJournal
$missingModel4ModeRejected = $false
try { Assert-DataQualityManifestMatchesPacket $manifest $model4PacketResult $RunDir } catch { $missingModel4ModeRejected = $true }
if (-not $missingModel4ModeRejected) { throw 'Model4 data acquisition accepted a journal without exact real-tick execution mode.' }
Update-JournalEvidence ("Tester: real ticks unavailable fallback maybe`n" + $baseJournal)
$looseModel4ModeRejected = $false
try { Assert-DataQualityManifestMatchesPacket $manifest $model4PacketResult $RunDir } catch { $looseModel4ModeRejected = $true }
if (-not $looseModel4ModeRejected) { throw 'Model4 data acquisition accepted a loose real ticks substring.' }
Update-JournalEvidence ("Tester: generating based on real ticks unavailable/fallback`n" + $baseJournal)
$suffixModel4ModeRejected = $false
try { Assert-DataQualityManifestMatchesPacket $manifest $model4PacketResult $RunDir } catch { $suffixModel4ModeRejected = $true }
if (-not $suffixModel4ModeRejected) { throw 'Model4 data acquisition accepted a suffixed/fallback mode claim.' }
$wrongIdentityCases = [ordered]@{
    bare = "Tester: EURUSD,M5 (FivePercentOnline-Real): generating based on real ticks"
    wrong_symbol = "CS`t0`t07:55:31.561`tTester`tXAUUSD,M5 (FivePercentOnline-Real): generating based on real ticks"
    wrong_period = "CS`t0`t07:55:31.561`tTester`tEURUSD,M15 (FivePercentOnline-Real): generating based on real ticks"
    wrong_server = "CS`t0`t07:55:31.561`tTester`tEURUSD,M5 (WrongServer): generating based on real ticks"
}
$wrongIdentityRejected = [ordered]@{}
foreach ($caseName in $wrongIdentityCases.Keys) {
    Update-JournalEvidence ($wrongIdentityCases[$caseName] + "`n" + $baseJournal)
    $rejected = $false
    try { Assert-DataQualityManifestMatchesPacket $manifest $model4PacketResult $RunDir } catch { $rejected = $true }
    if (-not $rejected) { throw "Model4 data acquisition accepted $caseName journal identity." }
    $wrongIdentityRejected[$caseName] = $true
}
$realModeLine = "CS`t0`t07:55:31.561`tTester`tEURUSD,M5 (FivePercentOnline-Real): generating based on real ticks"
$generatedModeLine = "CS`t0`t07:55:31.562`tTester`tEURUSD,M5 (FivePercentOnline-Real): every tick generated from M1 bars"
Update-JournalEvidence ($realModeLine + "`n" + $generatedModeLine + "`n" + $baseJournal)
$contradictoryModel4ModeRejected = $false
try { Assert-DataQualityManifestMatchesPacket $manifest $model4PacketResult $RunDir } catch { $contradictoryModel4ModeRejected = $true }
if (-not $contradictoryModel4ModeRejected) { throw 'Model4 data acquisition accepted contradictory generated-tick execution mode.' }
Update-JournalEvidence ($realModeLine + "`n" + $baseJournal)
Assert-DataQualityManifestMatchesPacket $manifest $model4PacketResult $RunDir
[pscustomobject]@{ valid = $true; tamper_rejected = $tamperRejected; report_claim_rejected = $reportClaimRejected; reversed_rejected = $reversedRejected; journal_claim_rejected = $journalClaimRejected; external_root_rejected = $externalRootRejected; legacy = $true; missing_model4_mode_rejected = $missingModel4ModeRejected; loose_model4_mode_rejected = $looseModel4ModeRejected; suffix_model4_mode_rejected = $suffixModel4ModeRejected; bare_model4_mode_rejected = $wrongIdentityRejected.bare; wrong_symbol_model4_mode_rejected = $wrongIdentityRejected.wrong_symbol; wrong_period_model4_mode_rejected = $wrongIdentityRejected.wrong_period; wrong_server_model4_mode_rejected = $wrongIdentityRejected.wrong_server; contradictory_model4_mode_rejected = $contradictoryModel4ModeRejected; exact_model4_mode_accepted = $true } | ConvertTo-Json
''', encoding="utf-8")
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(harness),
            "-Engine",
            str(engine),
            "-RunDir",
            str(run_dir),
        ],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {
        "valid": True,
        "tamper_rejected": True,
        "report_claim_rejected": True,
        "reversed_rejected": True,
        "journal_claim_rejected": True,
        "external_root_rejected": True,
        "legacy": True,
        "missing_model4_mode_rejected": True,
        "loose_model4_mode_rejected": True,
        "suffix_model4_mode_rejected": True,
        "bare_model4_mode_rejected": True,
        "wrong_symbol_model4_mode_rejected": True,
        "wrong_period_model4_mode_rejected": True,
        "wrong_server_model4_mode_rejected": True,
        "contradictory_model4_mode_rejected": True,
        "exact_model4_mode_accepted": True,
    }


def test_model_zero_is_not_mislabeled_as_broker_real_ticks() -> None:
    engine = (ALPHA_ROOT / "tools" / "research_loop_engine.ps1").read_text(encoding="utf-8-sig")
    validation = (ALPHA_ROOT / "analysis" / "unified_validation.py").read_text(encoding="utf-8-sig")
    assert "Model=0 (real ticks)" not in engine
    assert "run_manifest.model == 0 (MT5 real ticks)" not in validation
    assert "every tick generated from M1 bars; not broker real ticks" in engine
    assert "every tick generated from M1 bars; not broker real ticks" in validation


def test_lifecycle_manifest_requires_exact_runmeta_identity() -> None:
    alpha = ALPHA.read_text(encoding="utf-8-sig")
    assert "requires exactly one *_LifecycleTrades_*.csv" in alpha
    assert "requires exactly one *_RunMeta_*.json" in alpha
    assert "alphafactory_run_meta.v1" in alpha
    assert "RunMeta identity does not match manifest EA/symbol/telemetry profile" in alpha


def test_default_sidecar_collection_includes_outcome_blind_stage_telemetry() -> None:
    alpha = ALPHA.read_text(encoding="utf-8-sig")
    assert '"${Sym}_*StageTelemetry_*.csv"' in alpha


def test_tester_input_serializer_is_typed_include_aware_and_fail_closed(tmp_path: Path) -> None:
    assert POWERSHELL, "PowerShell is required"
    source = tmp_path / "EA_Test.mq5"
    include = tmp_path / "inputs.mqh"
    source.write_text(
        '#include "inputs.mqh"\ninput int InpCount=1;\n',
        encoding="utf-8",
    )
    include.write_text(
        'sinput string InpLabel="x";\ninput bool InpEnabled=true;\n',
        encoding="utf-8",
    )
    harness = tmp_path / "typed_inputs.ps1"
    harness.write_text(
        r'''
param([string]$Alpha,[string]$Source,[string]$Root)
$ErrorActionPreference='Stop'
$tokens=$null
$parseErrors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile($Alpha,[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count -gt 0){throw ($parseErrors|ForEach-Object{$_.Message}|Out-String)}
foreach($name in @(
    'ConvertTo-NormalizedOverrideMap','Get-RelativePathUnderRoot',
    'Assert-NonArchiveInclude','Resolve-IncludeDependency',
    'Get-IncludeDependencyClosure','Get-MqlInputTypeMap',
    'ConvertTo-TesterInputLines'
)){
    $fn=$ast.Find({param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -ceq $name
    },$true)
    if($null -eq $fn){throw "Missing function $name"}
    Invoke-Expression $fn.Extent.Text
}
$script:AdvisorsRoot=$Root
$script:AlphaRoot=Join-Path $Root '02. AlphaFactory'
$script:MT5Mql5Root=Join-Path $Root 'MQL5'
$lines=@(ConvertTo-TesterInputLines $Source 'InpLabel=alpha;InpCount=3;InpEnabled=false')
if('InpLabel=alpha' -cnotin $lines){throw 'string input was not emitted as plain key=value'}
if('InpCount=3||3||0||3||N' -cnotin $lines){throw 'numeric input tuple missing'}
if('InpEnabled=false||false||0||false||N' -cnotin $lines){throw 'bool input tuple missing'}
$unknownRejected=$false
try{[void](ConvertTo-TesterInputLines $Source 'InpUnknown=1')}catch{
    $unknownRejected=$_.Exception.Message -like "*does not match a declared input/sinput*"
}
if(-not $unknownRejected){throw 'unknown tester override was not rejected'}
''',
        encoding="utf-8",
    )
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(harness),
         "-Alpha", str(ALPHA), "-Source", str(source), "-Root", str(tmp_path)],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_single_workflow_keeps_cost_and_mt5_bindings() -> None:
    workflow = (WORKSPACE / "05. Playbook" / "WORKFLOW.md").read_text(encoding="utf-8")
    assert "spread/commission/slippage" in workflow
    assert "dynamic cost stress" in workflow
    assert "02. AlphaFactory/alpha.ps1" in workflow
    assert "Không dùng TradingView" in workflow


def test_generic_templates_are_parseable_and_have_no_executable_claim() -> None:
    templates = ALPHA_ROOT / "templates" / "research"
    contract = json.loads((templates / "ALPHAFACTORY_EA_CONTRACT.template.json").read_text(encoding="utf-8"))
    packet = json.loads((templates / "TASK_PACKET.control.template.json").read_text(encoding="utf-8"))
    data_packet = json.loads((templates / "TASK_PACKET.data_acquisition.template.json").read_text(encoding="utf-8"))
    assert contract["schema_version"] == "alphafactory_ea_contract.v1"
    assert contract["telemetry_profile"] == "none"
    assert packet["schema_version"] == "alphafactory_research_task_packet.v1"
    assert packet["model"] == 0
    assert packet["acceptance_contract"]["min_profit_factor"] >= 1.30
    assert packet["acceptance_contract"]["max_drawdown_pct"] <= 8.0
    assert "data_quality_contract" in data_packet
    assert "acceptance_contract" not in data_packet
    assert "REPLACE_WITH_64_HEX" in packet.values()


def test_model4_collection_preflight_binds_source_override_to_epoch(
    tmp_path: Path,
) -> None:
    assert POWERSHELL, "PowerShell is required"
    epoch_sha = "A" * 64
    good_source = tmp_path / "good.mq5"
    good_source.write_text(
        f'input string InpEpochManifestSha256="{epoch_sha}";\n'
        f'if(value!="{epoch_sha}") return false;\n',
        encoding="utf-8",
    )
    bad_source = tmp_path / "bad.mq5"
    bad_source.write_text(
        f'input string InpEpochManifestSha256="{epoch_sha}";\n',
        encoding="utf-8",
    )
    harness = tmp_path / "model4_epoch_binding.ps1"
    harness.write_text(
        r'''
param(
    [string]$Engine,
    [string]$GoodSource,
    [string]$BadSource,
    [string]$EpochSha
)
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $Engine, [ref]$tokens, [ref]$parseErrors
)
if ($parseErrors.Count -gt 0) {
    throw ($parseErrors | ForEach-Object { $_.Message } | Out-String)
}
foreach ($name in @(
    'Get-ObjectProperty',
    'ConvertTo-NormalizedOverrideMap',
    'Add-Model4CollectionSourceEpochBlockers'
)) {
    $fn = $ast.Find({ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -ceq $name
    }, $true)
    if ($null -eq $fn) { throw "Missing function $name" }
    Invoke-Expression $fn.Extent.Text
}
$manifest = [pscustomobject]@{ epoch_manifest_sha256 = $EpochSha }
$binding = [pscustomobject]@{
    Overrides = "InpEpochManifestSha256=$EpochSha;InpCollectionOnly=true"
}
$good = New-Object System.Collections.Generic.List[string]
Add-Model4CollectionSourceEpochBlockers `
    ([pscustomobject]@{ CanonicalSourceAbsolute = $GoodSource }) `
    $binding $manifest $good
if ($good.Count -ne 0) { throw "Good source rejected: $($good -join '; ')" }
$badSourceErrors = New-Object System.Collections.Generic.List[string]
Add-Model4CollectionSourceEpochBlockers `
    ([pscustomobject]@{ CanonicalSourceAbsolute = $BadSource }) `
    $binding $manifest $badSourceErrors
$wrongOverrideErrors = New-Object System.Collections.Generic.List[string]
Add-Model4CollectionSourceEpochBlockers `
    ([pscustomobject]@{ CanonicalSourceAbsolute = $GoodSource }) `
    ([pscustomobject]@{ Overrides = "InpEpochManifestSha256=$('B' * 64)" }) `
    $manifest $wrongOverrideErrors
if ($badSourceErrors.Count -eq 0) { throw 'Single source binding was accepted.' }
if ($wrongOverrideErrors.Count -eq 0) { throw 'Wrong epoch override was accepted.' }
[pscustomobject]@{
    valid = $true
    bad_source_rejected = $true
    wrong_override_rejected = $true
} | ConvertTo-Json -Compress
''',
        encoding="utf-8",
    )
    result = run_ps_file(
        harness,
        "-Engine",
        str(ALPHA_ROOT / "tools" / "research_loop_engine.ps1"),
        "-GoodSource",
        str(good_source),
        "-BadSource",
        str(bad_source),
        "-EpochSha",
        epoch_sha,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {
        "valid": True,
        "bad_source_rejected": True,
        "wrong_override_rejected": True,
    }
