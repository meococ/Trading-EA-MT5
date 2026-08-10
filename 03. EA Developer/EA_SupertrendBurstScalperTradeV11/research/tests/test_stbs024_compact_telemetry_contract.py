from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[2]
V10 = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV10/EA_SupertrendBurstScalperTradeV10.mq5"
V11 = PACKAGE / "EA_SupertrendBurstScalperTradeV11.mq5"
FAILURE_ARCHIVE = (
    ROOT
    / "03. EA Developer/EA_SupertrendBurstScalperTradeV10/research/evidence"
    / "HYP-STBS-XAUUSD-M15-023/STBS023-FAILURE-CLOSE-001"
)
TESTER_PROJECTION = FAILURE_ARCHIVE / "tester_hyp023_no_spam_projection.utf16le.log"
AGENT_PROJECTION = FAILURE_ARCHIVE / "agent_hyp023_no_spam_projection.utf16le.log"
FROZEN_CAP = 4_194_304


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def normalize_v10_to_v11(text: str) -> str:
    replacements = {
        '#property version   "10.00"': '#property version   "11.00"',
        '#property description "H1 Supertrend flip baseline with stable lifecycle replay and SL-stressed margin admission."':
            '#property description "H1 Supertrend baseline with bounded telemetry and unchanged SL-stressed execution."',
        "HYP-STBS-XAUUSD-M15-023": "HYP-STBS-XAUUSD-M15-024",
        "STBS_H1_FLIP_M15_BURST_TRADE_V10_SL_STRESSED_MARGIN":
            "STBS_H1_FLIP_M15_BURST_TRADE_V11_COMPACT_MARGIN_TELEMETRY",
        "5604123": "5604124",
        "EA_SupertrendBurstScalperTradeV10": "EA_SupertrendBurstScalperTradeV11",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    spam = (
        "   if(!InpAuditOnly && !safe)\n"
        "      PrintFormat(\"STBS_MARGIN_STRESS_UNSAFE|volume=%.8f|loss=%.8f|free=%.8f|level=%.8f|threshold=%.8f\",\n"
        "                  volume,stressed_profit,stressed_check_free,stressed_margin_level,threshold);\n"
    )
    assert text.count(spam) == 1
    return text.replace(spam, "")


def summary_payload(path: Path) -> str:
    text = path.read_bytes().decode("utf-16le")
    rows = [line for line in text.splitlines() if "STBS_SUMMARY|hypothesis=HYP-STBS-XAUUSD-M15-023" in line]
    assert len(rows) == 1
    return rows[0][rows[0].index("STBS_SUMMARY|") :]


def test_v11_is_exact_v10_mapping_minus_identity_and_per_candidate_print():
    old = V10.read_text(encoding="utf-8")
    new = V11.read_text(encoding="utf-8")
    assert normalize_v10_to_v11(old) == new
    assert "STBS_MARGIN_STRESS_UNSAFE" not in new


def test_v11_identity_is_fail_closed():
    text = V11.read_text(encoding="utf-8")
    for needle in (
        '#property version   "11.00"',
        'InpHypothesisId        = "HYP-STBS-XAUUSD-M15-024"',
        'InpVariantTag          = "STBS_H1_FLIP_M15_BURST_TRADE_V11_COMPACT_MARGIN_TELEMETRY"',
        "InpMagic               = 5604124",
        'EA_NAME              = "EA_SupertrendBurstScalperTradeV11"',
        'InpHypothesisId!="HYP-STBS-XAUUSD-M15-024"',
        'InpVariantTag!="STBS_H1_FLIP_M15_BURST_TRADE_V11_COMPACT_MARGIN_TELEMETRY"',
        "InpAuditOnly || !InpEnableTelemetry || InpMagic!=5604124",
    ):
        assert needle in text


def test_archived_no_spam_replay_is_exact_and_requires_more_than_one_mib():
    assert sha256(TESTER_PROJECTION) == "DDE409FE80DE6687DD0A520D0B4EAD2F20817142C212CD40E9E7FAFB2CC4EC7B"
    assert sha256(AGENT_PROJECTION) == "2F08B3860EB6247BF168331914754650548155FFC93513FD51FA539369BCE7AF"
    assert TESTER_PROJECTION.stat().st_size == 871_692
    assert AGENT_PROJECTION.stat().st_size == 858_852
    combined = TESTER_PROJECTION.stat().st_size + AGENT_PROJECTION.stat().st_size
    assert combined == 1_730_544
    assert combined > 1_048_576
    assert combined < FROZEN_CAP
    assert summary_payload(TESTER_PROJECTION) == summary_payload(AGENT_PROJECTION)


def test_projection_has_exact_init_summary_and_no_removed_spam():
    for path in (TESTER_PROJECTION, AGENT_PROJECTION):
        text = path.read_bytes().decode("utf-16le")
        assert len(text.splitlines()) == 3_716
        assert text.count("STBS_INIT|hypothesis=HYP-STBS-XAUUSD-M15-023") == 1
        assert text.count("STBS_SUMMARY|hypothesis=HYP-STBS-XAUUSD-M15-023") == 1
        assert "STBS_MARGIN_STRESS_UNSAFE" not in text
        assert "|failed=false" in summary_payload(path)


def test_four_mib_is_the_frozen_minimal_headroom_choice():
    combined = 1_730_544
    assert 2_097_152 / combined < 1.25
    assert FROZEN_CAP / combined > 2.4
    assert FROZEN_CAP == 4_194_304
