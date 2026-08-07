from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALPHA = ROOT / "02. AlphaFactory" / "alpha.ps1"
RESEARCH_LOOP = ROOT / "02. AlphaFactory" / "tools" / "research_loop_engine.ps1"
ABI_PACKET_BUILDER = (
    ROOT
    / "03. EA Developer"
    / "EA_RegimeStructureFusion"
    / "research"
    / "abi_corrected"
    / "build_task_packet.ps1"
)
FORENSIC = (
    ROOT
    / "03. EA Developer"
    / "EA_RegimeStructureFusionForensics"
    / "EA_RegimeStructureFusionForensics.mq5"
)
PARENT = (
    ROOT
    / "03. EA Developer"
    / "EA_RegimeStructureFusion"
    / "EA_RegimeStructureFusion.mq5"
)
CONTRACTS = [
    ROOT / "03. EA Developer" / "EA_RegimeStructureFusion" / "ALPHAFACTORY_EA_CONTRACT.json",
    ROOT
    / "03. EA Developer"
    / "EA_RegimeStructureFusionForensics"
    / "ALPHAFACTORY_EA_CONTRACT.json",
]


def test_alpha_visual_mode_is_explicit_and_receipt_bound() -> None:
    source = ALPHA.read_text(encoding="utf-8-sig")
    assert "[switch]$Visual" in source
    assert "Visual=$testerVisual" in source
    assert "visual_mode = [bool]$VisualMode" in source
    assert "must be true for a visual replay" in source
    assert "Visual replay produced no native MT5 chart evidence" in source
    assert 'chartSidecarPatterns = @("RSFV_*.png")' in source


def test_indicator_bundle_is_declared_for_strategy_and_forensics() -> None:
    expected = {
        "AI_Regime_Detection",
        "Volatility_Regime_Classifier_QuantRegime",
        "Modern_Bollinger_Bands_GBB",
        "TB_Smart_Money_Concept_2026",
        "QQE_MOD",
    }
    for path in CONTRACTS:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        dependencies = payload["indicator_dependencies"]
        assert {item["name"] for item in dependencies} == expected
        assert all(item["source"].endswith(".mq5") for item in dependencies)
        assert all(item["terminal_ex5"].endswith(".ex5") for item in dependencies)


def test_research_receipt_hash_binds_and_locks_indicator_sources() -> None:
    source = RESEARCH_LOOP.read_text(encoding="utf-8-sig")
    builder = ABI_PACKET_BUILDER.read_text(encoding="utf-8-sig")
    assert "Get-LiveIndicatorDependencyBinding" in source
    assert "Task packet field 'indicator_dependencies' is required" in source
    assert "Task packet indicator_dependencies do not match" in source
    assert "indicator_dependencies = @(\n                $Binding.IndicatorDependencies" in source
    assert "$item.source_absolute_path" in source
    assert "indicator_dependencies = @($indicatorDependencies)" in builder
    assert "source_sha256 = (Get-FileHash" in builder


def test_forensic_images_are_preselected_and_queued() -> None:
    source = FORENSIC.read_text(encoding="utf-8-sig")
    ids_match = re.search(r"ulong ids\[\]=\{([^}]+)\};", source)
    assert ids_match is not None
    position_ids = {int(value) for value in ids_match.group(1).split(",")}
    assert position_ids == {
        342,
        424,
        782,
        808,
        500,
        1052,
        832,
        774,
        456,
        422,
        604,
        780,
        1222,
        246,
    }
    assert "LookupFrozenVisualCase(position_id,case_id)" in source
    assert "g_ticks_seen<=item.queued_tick" in source
    assert "CaptureQueuedVisualShots(false)" in source
    assert "CaptureQueuedVisualShots(true)" in source
    assert "MQLInfoInteger(MQL_VISUAL_MODE)" in source


def test_visual_csv_carries_native_join_keys() -> None:
    source = FORENSIC.read_text(encoding="utf-8-sig")
    for field in (
        '"case_id"',
        '"deal"',
        '"order"',
        '"position_id"',
        '"filename"',
        '"screenshot_ok"',
        '"qqe_probe_mask"',
        '"qqe_hist"',
        '"qqe_secondary"',
        '"qqe_neutral_mirror"',
        '"run_id"',
    ):
        assert field in source


def test_grouped_indicator_abi_is_explicit_in_icustom_calls() -> None:
    parent = PARENT.read_text(encoding="utf-8-sig")
    qqe_call = re.search(
        r"int CreateQqeHandle\(\).*?return\(iCustom\((.*?)\)\);",
        parent,
        flags=re.S,
    )
    assert qqe_call is not None
    qqe_args = qqe_call.group(1)
    required_qqe_groups = (
        '"Primary QQE Settings"',
        '"Secondary QQE Settings"',
        '"Bollinger Bands Settings"',
    )
    assert all(group in qqe_args for group in required_qqe_groups)
    assert [qqe_args.index(group) for group in required_qqe_groups] == sorted(
        qqe_args.index(group) for group in required_qqe_groups
    )

    forensic = FORENSIC.read_text(encoding="utf-8-sig")
    for group in (
        '"Adaptive length"',
        '"Basis / bands"',
        '"Regime / squeeze"',
        '"Signals"',
        '"Display"',
        '"Closed-bar alerts"',
        '"Parity"',
        '"EA Engine Contract - iCustom inputs first"',
        '"TB SMC 2026 - Look"',
        '"TB SMC 2026 - Map"',
        '"Closed-Bar Alerts"',
    ):
        assert group in forensic


def test_external_native_chart_lane_is_bounded_and_png_verified() -> None:
    source = ALPHA.read_text(encoding="utf-8-sig")
    assert "Import-NativeMt5ChartEvidence" in source
    assert "NativeChartEvidence must stay inside the workspace" in source
    assert "^NATIVE_MT5_[A-Za-z0-9_.-]+\\.png$" in source
    assert "89-50-4E-47-0D-0A-1A-0A" in source
    assert "NativeChartEvidence is stale for this run" in source
    assert "NativeChartEvidence is accepted only for a Visual Mode run" in source
    assert "AddSeconds(120)" in source
    assert "Start-Sleep -Milliseconds 250" in source
    assert "Import-NativeMt5ChartEvidenceSet" in source
    assert "between 1 and 32 explicit PNG paths" in source
    assert "NativeChartEvidence batch is incomplete" in source
    assert "NativeChartEvidence contains duplicate paths" in source
    batch_fn = re.search(
        r"function Import-NativeMt5ChartEvidenceSet(.*?)function Write-RunManifest",
        source,
        flags=re.S,
    )
    assert batch_fn is not None
    assert "$imports = @()" in batch_fn.group(1)
    assert "New-Object System.Collections.Generic.List[object]" not in batch_fn.group(1)


def test_native_loss_capture_uses_wall_clock_hold_not_tester_sleep() -> None:
    source = FORENSIC.read_text(encoding="utf-8-sig")
    schedule = re.search(
        r"void ProcessNativeLossSchedule\(\)(.*?)void QueueVisualSmokeIfDue",
        source,
        flags=re.S,
    )
    assert schedule is not None
    body = schedule.group(1)
    assert 'FROZEN_7_LOSER_OUTCOMES_V1' in body
    assert 'WriteNativeCaptureFlag(ids[i],capture_time)' in body
    assert 'DrawReferenceExitAt(ids[i],directions[i],exits[i],net_rs[i],exit_times[i])' in body
    assert 'InpForensicNativeCaseIndex>0' in body
    assert 'CaptureQueuedVisualShots(true)' not in body
    assert 'ChartSetInteger(0,CHART_AUTOSCROLL,true)' in body
    assert 'ChartSetInteger(0,CHART_SHIFT,false)' in body
    assert 'ChartNavigate(0,CHART_END,0)' in body
    assert '"REFERENCE_OUTCOME"' in body
    assert "GetMicrosecondCount()" in body
    assert "InpForensicExternalCapturePauseMs*1000ULL" in body
    assert "Sleep(InpForensicExternalCapturePauseMs)" not in body


def test_native_outcome_png_is_unique_and_objects_survive_async_request() -> None:
    source = FORENSIC.read_text(encoding="utf-8-sig")
    assert 'RSFV_%s_%s_%I64u_%I64u_%s_M5.png' in source
    assert 'SafeToken(item.case_id)' in source
    schedule = re.search(
        r"void ProcessNativeLossSchedule\(\)(.*?)void QueueVisualSmokeIfDue",
        source,
        flags=re.S,
    )
    assert schedule is not None
    assert 'DeleteReferenceTrade(ids[i]);' not in schedule.group(1)
