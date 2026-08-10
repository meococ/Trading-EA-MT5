from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "02. AlphaFactory/tools/run_stbs022_model0_baseline.ps1"
BASE = ROOT / "02. AlphaFactory/tools/research_loop_engine.ps1"
ALPHA = ROOT / "02. AlphaFactory/alpha.ps1"
AUDITOR = ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py"
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTradeV9.mq5"
STATIC_MANIFEST = PACKAGE / "HYP-STBS-XAUUSD-M15-022_NONREPAINT_MANIFEST.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_shared_alphafactory_remains_frozen():
    assert sha256(ALPHA) == "BC570A1EA7D8788AC9483A7133565893C8B679ADE9A0ED85E2B8AF8B3A0F02FC"
    assert sha256(BASE) == "6E205874477A79EB97EE56967B81FA3675FB25AD784D00D989BBD077DA837550"


def test_runner_is_hyp022_only_and_preserves_original_run_manifest():
    text = RUNNER.read_text(encoding="utf-8")
    assert "$EaName -cne 'EA_SupertrendBurstScalperTradeV9'" in text
    assert "$HypothesisId -cne 'HYP-STBS-XAUUSD-M15-022'" in text
    assert "$From -cne '2005.01.01' -or $To -cne '2023.01.01'" in text
    assert "$Model -ne 0" in text and "$TimeoutSec -ne 900" in text
    assert "$TelemetryTier -cne 'trade-only'" in text
    assert "nonrepaint_run_manifest.json" in text
    assert "New-Hyp022NonRepaintAuditManifest $runManifestPath $runManifestShaForAudit $analysisDir" in text
    assert "--manifest $nonRepaintRunManifestPath" in text
    assert "Write-JsonAtomically $run $RunManifestPath" not in text
    assert "& $alphaPs1 backtest" in text


def test_runner_binds_exact_static_provenance_authority():
    text = RUNNER.read_text(encoding="utf-8")
    assert "899E2C031DBC93FD99450990347C3FB1FB412E848964820AD4A0887FAAE3F6F1" in text
    assert "359E11DC5979E5D0B915A510F0148D3451D11994EDF46ADA1D18F3CF0C238509" in text
    assert "9B82946CF17A876B547E7227F7FA131183C2383D38BF639574001CAB03DF8D82" in text
    assert "366D70F0C6FAF02F85B4819E7305CD1BD271BA6A78B4789CF0DCDF2FB651E360" in text
    assert "$hyp022CopyTimeLine = 678" in text
    assert "single exact DATA_EPOCH_D0 CopyTime first-date proof; no decision or outcome access" in text
    assert "original_run_manifest_sha256 = $RunManifestSha256" in text
    assert text.count("changed while") >= 3
    manifest = json.loads(STATIC_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["nondecision_provenance_copytime_authorized"] is True
    assert manifest["source_sha256"] == sha256(SOURCE)


def test_derived_manifest_passes_only_the_exact_copytime_provenance(tmp_path: Path):
    snapshot_root = tmp_path / "snapshot"
    snapshot_root.mkdir()
    snapshot_source = snapshot_root / SOURCE.name
    shutil.copyfile(SOURCE, snapshot_source)
    base = {
        "hypothesis_id": "HYP-STBS-XAUUSD-M15-022",
        "run_id": "STBS022-ADAPTER-TEST",
        "snapshot_root": str(snapshot_root.resolve()),
        "source_snapshot": str(snapshot_source.resolve()),
        "source_sha256": sha256(snapshot_source),
        "include_snapshots": [],
    }
    manifest = tmp_path / "manifest.json"
    out = tmp_path / "audit.json"
    manifest.write_text(json.dumps(base), encoding="utf-8")
    rejected = subprocess.run(
        [sys.executable, str(AUDITOR), "--manifest", str(manifest), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert rejected.returncode == 1
    assert json.loads(out.read_text(encoding="utf-8"))["findings"] == [
        {
            "path": str(snapshot_source.resolve()),
                "line": 678,
            "rule": "unproven_closed_bar_shift",
            "function": "CopyTime",
            "shift_expression": "copytime_from",
        }
    ]

    base["nondecision_provenance_copytime_authorized"] = True
    manifest.write_text(json.dumps(base), encoding="utf-8")
    accepted = subprocess.run(
        [sys.executable, str(AUDITOR), "--manifest", str(manifest), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    audit = json.loads(out.read_text(encoding="utf-8"))
    assert audit["status"] == "PASS"
    assert audit["manifest"] == str(manifest.resolve())
    assert audit["manifest_sha256"] == sha256(manifest)
    assert audit["collection_authority_verified"] is False
    assert audit["audited_files"] == [
        {"path": str(snapshot_source.resolve()), "sha256": sha256(snapshot_source)}
    ]
    assert audit["findings"] == []
    assert audit["allowed_new_bar_gates"] == [
        {
            "path": str(snapshot_source.resolve()),
            "line": 678,
            "rule": "collection_first_date_copytime",
            "function": "CopyTime",
            "disposition": "allowed_collection_provenance_read",
        }
    ]


def test_runner_fail_closes_the_full_runtime_nonrepaint_semantics():
    text = RUNNER.read_text(encoding="utf-8")
    for needle in (
        "manifest_sha256 -cne $nonRepaintRunManifestShaForAudit",
        "collection_authority_verified -ne $false",
        "$auditedFiles.Count -ne 1",
        "$findings.Count -ne 0",
        "$allowedGates.Count -ne 1",
        "[int]$allowedGates[0].line -ne $hyp022CopyTimeLine",
        "[string]$allowedGates[0].rule -cne 'collection_first_date_copytime'",
        "[string]$allowedGates[0].function -cne 'CopyTime'",
        "[string]$allowedGates[0].disposition -cne 'allowed_collection_provenance_read'",
        "non-repaint auditor, derivative manifest or audit artifact drifted during validation",
        "reviewed_nonrepaint_auditor_sha256",
        "hyp022_nonrepaint_auditor",
    ):
        assert needle in text
