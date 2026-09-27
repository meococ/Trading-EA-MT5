"""Smoke-tier quarantine (VMOPS-P1b B2).

`alpha.ps1 backtest -Smoke` writes runs with manifest tier='smoke' under
`runs/smoke/`. Those runs are mechanical checks, never governed evidence:
every consumer of run evidence must refuse them, and the governed path must
still refuse a missing ContractReceipt.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ALPHA_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ALPHA_ROOT.parent
TOOLS = ALPHA_ROOT / "tools"
ALPHA = ALPHA_ROOT / "alpha.ps1"
ENGINE = TOOLS / "research_loop_engine.ps1"
REGISTRY_VALIDATOR = (
    WORKSPACE / "04. Memory" / "research" / "validate_candidate_registry.py"
)
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def _load_module(name: str, path: Path):
    # runs_db rewraps sys.stdout/stderr at import; give it throwaway streams
    # so its TextIOWrapper never owns (or closes) pytest's capture buffers.
    import io

    out, err = sys.stdout, sys.stderr
    sys.stdout = io.TextIOWrapper(io.BytesIO())
    sys.stderr = io.TextIOWrapper(io.BytesIO())
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.stdout, sys.stderr = out, err
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


SMOKE_MANIFEST = {
    "schema_version": "alphafactory_run_manifest.v2",
    "run_id": "20260101_000000",
    "hypothesis_id": "SMOKE",
    "run_role": "challenger",
    "ea_name": "EA_Demo",
    "symbol": "XAUUSD",
    "tier": "smoke",
    "plane": "devin-vm-mqdemo",
    "terminal_build": "5.0.0.6230",
    "contract_receipt_sha256": None,
}


def _engine_extract_harness(body: str) -> str:
    """Dot-source every function definition from research_loop_engine.ps1
    (top-level script never runs) then evaluate `body`."""
    return (
        "$tokens=$null;$errs=$null;"
        f"$ast=[System.Management.Automation.Language.Parser]::ParseFile('{ENGINE}',[ref]$tokens,[ref]$errs);"
        "$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]},$true)"
        " | ForEach-Object { . ([ScriptBlock]::Create($_.Extent.Text)) };"
        f"$alphaRoot='{ALPHA_ROOT}';"
        + body
    )


def _run_powershell(command: str) -> subprocess.CompletedProcess:
    assert POWERSHELL, "PowerShell is required"
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=300,
    )


# ---------------------------------------------------------------------------
# runs_db.py
# ---------------------------------------------------------------------------

def test_runs_db_discover_skips_smoke_tree(tmp_path):
    runs_db = _load_module("runs_db", TOOLS / "runs_db.py")
    runs_dir = tmp_path / "runs"
    (runs_dir / "smoke" / "EA_Demo" / "20260101_000000").mkdir(parents=True)
    (runs_dir / "EA_Real" / "20260102_000000").mkdir(parents=True)
    found = runs_db.discover_runs(runs_dir)
    assert all(ea != "smoke" for ea, _, _ in found)
    assert all("smoke" not in path.parts for _, _, path in found)


def test_runs_db_parse_run_refuses_smoke_manifest(tmp_path):
    runs_db = _load_module("runs_db", TOOLS / "runs_db.py")
    run_dir = tmp_path / "EA_Demo" / "20260101_000000"
    _write_json(run_dir / "run_manifest.json", SMOKE_MANIFEST)
    _write_json(run_dir / "analysis" / "enhanced_summary.json", {})
    assert runs_db.parse_run("EA_Demo", "20260101_000000", run_dir) is None


def test_runs_db_parse_run_accepts_governed_manifest_tier(tmp_path):
    runs_db = _load_module("runs_db", TOOLS / "runs_db.py")
    run_dir = tmp_path / "EA_Demo" / "20260101_000000"
    _write_json(run_dir / "run_manifest.json", dict(SMOKE_MANIFEST, tier="governed"))
    _write_json(run_dir / "analysis" / "enhanced_summary.json", {})
    # The tier gate must not fire; parse_run proceeds into normal parsing.
    assert runs_db.parse_run("EA_Demo", "20260101_000000", run_dir) is not None


# ---------------------------------------------------------------------------
# validate_candidate_registry.py
# ---------------------------------------------------------------------------

def test_candidate_registry_refuses_smoke_run_path(tmp_path):
    vcr = _load_module("validate_candidate_registry", REGISTRY_VALIDATOR)
    errors: list[str] = []
    vcr.resolve_hash_bound_path(
        "02. AlphaFactory/runs/smoke/EA_Demo/20260101_000000/run_manifest.json",
        "A" * 64,
        "test-label",
        errors,
    )
    assert any("smoke" in e for e in errors)


def test_candidate_registry_refuses_moved_smoke_manifest():
    vcr = _load_module("validate_candidate_registry", REGISTRY_VALIDATOR)
    staging = WORKSPACE / "02. AlphaFactory" / "runtime" / "smoke_tier_test"
    manifest = _write_json(staging / "run_manifest.json", SMOKE_MANIFEST)
    try:
        rel = manifest.relative_to(WORKSPACE).as_posix()
        errors: list[str] = []
        vcr.resolve_hash_bound_path(rel, _sha256(manifest), "test-label", errors)
        assert any("smoke" in e for e in errors)

        governed = _write_json(staging / "governed_manifest" / "run_manifest.json",
                               dict(SMOKE_MANIFEST, tier="governed"))
        rel_g = governed.relative_to(WORKSPACE).as_posix()
        errors_g: list[str] = []
        vcr.resolve_hash_bound_path(rel_g, _sha256(governed), "test-label", errors_g)
        assert not any("smoke" in e for e in errors_g)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


# ---------------------------------------------------------------------------
# validate_ea_delivery_packet.py
# ---------------------------------------------------------------------------

def test_delivery_packet_refuses_smoke_run_manifest(tmp_path):
    vdp = _load_module("validate_ea_delivery_packet",
                       TOOLS / "validate_ea_delivery_packet.py")
    manifest = _write_json(tmp_path / "run" / "run_manifest.json", SMOKE_MANIFEST)
    payload = {
        "bindings": [
            {
                "role": "run_manifest",
                "path": manifest.relative_to(tmp_path).as_posix(),
                "bytes": manifest.stat().st_size,
                "sha256": _sha256(manifest),
            }
        ]
    }
    errors: list[str] = []
    vdp.validate_bindings(payload, tmp_path, "economic_run", errors)
    assert any("smoke" in e for e in errors)


# ---------------------------------------------------------------------------
# research_loop_engine.ps1 (Assert-RunManifestMatchesPacket + matched control)
# ---------------------------------------------------------------------------

def test_engine_assert_run_manifest_refuses_smoke(tmp_path):
    manifest = _write_json(tmp_path / "run_manifest.json", SMOKE_MANIFEST)
    body = (
        f"try {{ Assert-RunManifestMatchesPacket '{manifest}' $null $null $null ''; 'NO_THROW' }}"
        " catch { 'THROW:' + $_.Exception.Message }"
    )
    res = _run_powershell(_engine_extract_harness(body))
    assert "smoke" in res.stdout.lower(), res.stdout + res.stderr


def test_engine_matched_control_refuses_smoke(tmp_path):
    ea = "ZZ_SMOKE_T"
    run_id = "SMKTEST01"
    run_dir = ALPHA_ROOT / "runs" / ea / run_id
    manifest = _write_json(run_dir / "run_manifest.json", SMOKE_MANIFEST)
    report = run_dir / "report.html"
    report.write_text("<html>stub</html>", encoding="utf-8")
    manifest_sha = _sha256(manifest)
    report_sha = _sha256(report)
    body = f"""
$binding = [pscustomobject]@{{
    EaName='{ea}'; Symbol='XAUUSD'; Period='H1'; From='2024.01.01'; To='2024.01.31'
    Model=0; ExecutionMode=0; FixedDelayMs=0; Overrides=''; ControlOverrides=''
    Deposit=10000; Leverage=100; Spread='current'; RequiredSidecars=@()
    ControlSourceSha256=''; ControlConfigSha256=''; ControlEx5Sha256=''
    ControlIncludesSha256=''; ControlGitCommit=''; ControlGitStatusSha256=''
    BrokerFingerprint=''; ServerFingerprint=''; AccountFingerprint=''; DataFingerprint=''
}}
$contract = [pscustomobject]@{{
    HypothesisId='HYP-T-001'; LatestRow=[pscustomobject]@{{ parent_candidate='' }}
}}
$res = Resolve-MatchedControl '{run_id}' 'HYP-T-001' '{manifest_sha}' '{report_sha}' $contract $binding
$res.Blockers -join "`n"
"""
    try:
        res = _run_powershell(_engine_extract_harness(body))
        assert "smoke" in res.stdout.lower(), res.stdout + res.stderr
    finally:
        shutil.rmtree(ALPHA_ROOT / "runs" / ea, ignore_errors=True)


# ---------------------------------------------------------------------------
# build_control_packet.py — smoke-stamped evidence is refused
# ---------------------------------------------------------------------------

def test_control_packet_refuses_smoke_evidence():
    ea = "EA_LiquiditySweep"
    hyp = "HYP-LSWEEP-XAU-M5-001"
    sym = "ZZSMKT"
    evid = WORKSPACE / "03. EA Developer" / ea / "research" / "evidence"
    fabricated = [
        evid / f"{sym}_spread_evidence.json",
        evid / f"{sym}_slippage_evidence.json",
        evid / f"{sym}_commission_evidence.json",
    ]
    for p in fabricated:
        _write_json(p, {"tier": "smoke", "identity": {}})
    try:
        res = subprocess.run(
            [
                sys.executable,
                str(TOOLS / "build_control_packet.py"),
                "--ea", ea,
                "--hyp", hyp,
                "--symbol", sym,
                "--period", "M5",
                "--magic", "1",
                "--spread-points", "1",
                "--pip", "0.1",
                "--digits", "3",
                "--point", "0.001",
                "--history-quality", "99",
                "--bars", "1",
                "--ticks", "1",
            ],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=120,
        )
        assert res.returncode != 0
        assert "smoke tier" in (res.stdout + res.stderr).lower()
    finally:
        for p in fabricated:
            p.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# alpha.ps1 — governed path unchanged: missing receipt still refused;
# -Smoke refuses a receipt (lanes never mix).
# ---------------------------------------------------------------------------

ALPHA_LOCAL = ALPHA_ROOT / "alpha.local.ps1"


@pytest.mark.skipif(not ALPHA_LOCAL.is_file() or not POWERSHELL,
                    reason="requires alpha.local.ps1 machine config + powershell")
def test_backtest_without_receipt_still_refused():
    res = _run_powershell(
        f"& '{ALPHA}' backtest EA_SonicR_PVSRA -Symbol XAUUSD -Period H1 "
        "-From 2024.01.01 -To 2024.01.31 -HypothesisId HYP-SMKNEG-001"
    )
    combined = res.stdout + res.stderr
    assert "ContractReceipt is required for backtest evidence" in combined


@pytest.mark.skipif(not ALPHA_LOCAL.is_file() or not POWERSHELL,
                    reason="requires alpha.local.ps1 machine config + powershell")
def test_backtest_smoke_refuses_receipt_combo():
    res = _run_powershell(
        f"& '{ALPHA}' backtest EA_SonicR_PVSRA -Symbol XAUUSD -Period H1 "
        "-From 2024.01.01 -To 2024.01.31 -Smoke -ContractReceipt x.json"
    )
    combined = res.stdout + res.stderr
    assert res.returncode != 0
    assert "cannot be combined with ContractReceipt" in combined
