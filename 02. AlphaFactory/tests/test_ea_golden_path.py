from __future__ import annotations

import hashlib
import json
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
    )


def test_alpha_discovers_only_two_canonical_active_packages() -> None:
    result = run_ps_file(ALPHA, "list")
    assert result.returncode == 0, result.stdout + result.stderr
    names = [line.strip() for line in result.stdout.splitlines() if line.strip().startswith("EA_")]
    assert names == ["EA_FVGConfluence", "EA_HybridICT_Sonic"]
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
    assert "CANDIDATE_REGISTRY_OK rows=2 hypotheses=2" in result.stdout


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
    assert "Latest registry state 'probe'" in combined
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
    engine = (ALPHA_ROOT / "tools" / "sonic_research_loop.ps1").read_text(encoding="utf-8-sig")
    alpha = ALPHA.read_text(encoding="utf-8-sig")
    assert "include_closure must contain the active EA include dependency set" not in engine
    assert "missing packet-bound include closure evidence" not in alpha
    assert "FileShare]::Read" in engine


def test_runner_freezes_acceptance_contract_and_telemetry_tier_before_mt5() -> None:
    engine = (ALPHA_ROOT / "tools" / "sonic_research_loop.ps1").read_text(encoding="utf-8-sig")
    assert "acceptance_contract must contain exactly the seven supported gate fields" in engine
    assert '"--min-pf"' in engine
    assert '"--max-mc-p95-dd-pct"' in engine
    assert "requires TelemetryTier=trade-only before MT5" in engine


def test_lifecycle_manifest_requires_exact_runmeta_identity() -> None:
    alpha = ALPHA.read_text(encoding="utf-8-sig")
    assert "requires exactly one *_LifecycleTrades_*.csv" in alpha
    assert "requires exactly one *_RunMeta_*.json" in alpha
    assert "alphafactory_run_meta.v1" in alpha
    assert "RunMeta identity does not match manifest EA/symbol/telemetry profile" in alpha


def test_generic_runbook_commands_bind_cost_source_manifest() -> None:
    golden = (WORKSPACE / "05. Playbook" / "ea_golden_path.md").read_text(encoding="utf-8")
    runbook = (WORKSPACE / "05. Playbook" / "sonic_tool_runbook.md").read_text(encoding="utf-8")
    assert "-CostSourceManifest <COST_SOURCE_MANIFEST.json>" in golden
    assert runbook.count("-CostSourceManifest") >= 2


def test_generic_templates_are_parseable_and_have_no_executable_claim() -> None:
    templates = ALPHA_ROOT / "templates" / "research"
    contract = json.loads((templates / "ALPHAFACTORY_EA_CONTRACT.template.json").read_text(encoding="utf-8"))
    packet = json.loads((templates / "TASK_PACKET.control.template.json").read_text(encoding="utf-8"))
    assert contract["schema_version"] == "alphafactory_ea_contract.v1"
    assert contract["telemetry_profile"] == "none"
    assert packet["schema_version"] == "alphafactory_research_task_packet.v1"
    assert packet["model"] == 0
    assert packet["acceptance_contract"]["min_profit_factor"] >= 1.30
    assert packet["acceptance_contract"]["max_drawdown_pct"] <= 8.0
    assert "REPLACE_WITH_64_HEX" in packet.values()
