from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
SOURCE = PACKAGE / "EA_KLR_Scalper.mq5"
INCLUDE = PACKAGE / "research" / "generated" / "KLR_DTWEXBGS_Data.mqh"
PREREG = (
    PACKAGE
    / "research"
    / "HYP-KLR-MT5-REPLICATION-M5-XAU-001_FROZEN_PREREG.md"
)
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
AUDITOR = ROOT / "02. AlphaFactory" / "tools" / "audit_mql5_nonrepaint.py"


def load_auditor():
    spec = importlib.util.spec_from_file_location("klr_nonrepaint_auditor", AUDITOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_alpha_contract_and_frozen_identity() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    source = SOURCE.read_text(encoding="utf-8")
    prereg = PREREG.read_text(encoding="utf-8")

    assert contract["telemetry_profile"] == "lifecycle-v3"
    assert contract["variant_tag_input"] == "InpRequireUsdGate"
    assert 'HYPOTHESIS_ID="HYP-KLR-MT5-REPLICATION-M5-XAU-001"' in source
    assert "Status: **FROZEN BEFORE SOURCE AND MODEL 0**" in prereg


def test_source_matches_frozen_parameters_and_has_no_external_io() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    expected_inputs = {
        "InpRiskPercent": "0.25",
        "InpMagic": "5600718",
        "InpAtrPeriod": "14",
        "InpPivotStrength": "2",
        "InpDisplacementAtr": "1.00",
        "InpDisplacementBars": "4",
        "InpRetestBars": "6",
        "InpStopAtrBuffer": "0.10",
        "InpTargetRR": "2.00",
        "InpMaxHoldBars": "12",
        "InpMaxTradesPerDay": "1",
        "InpLondonStartMinuteET": "120",
        "InpLondonEndMinuteET": "300",
        "InpNyStartMinuteET": "510",
        "InpNyEndMinuteET": "660",
        "InpMaxSpreadPoints": "35",
        "InpServerUtcOffsetWinterHours": "2",
    }
    for name, value in expected_inputs.items():
        assert re.search(rf"input\s+\w+\s+{name}\s*=\s*{re.escape(value)}\s*;", source)

    assert "input bool   InpRequireUsdGate=true;" in source
    assert "input bool   InpServerUsesEuropeDst=true;" in source
    assert "input bool   InpUseFileCommon=false;" in source
    assert "FILE_COMMON" not in source
    assert "WebRequest" not in source


def test_usd_snapshot_is_embedded_and_hash_bound() -> None:
    include = INCLUDE.read_text(encoding="utf-8")
    assert (
        'KLR_DTWEXBGS_SOURCE_SHA256="'
        "15B46514271F0E8D5D721CFEE2FA5A994DB56982E042B55F66F23750B70E8951"
        '"'
    ) in include
    assert "KLR_USD_OBSERVATION_COUNT=758" in include
    assert "D'2021.12.20 00:00'" in include
    assert "D'2024.12.31 00:00'" in include
    assert hashlib.sha256(INCLUDE.read_bytes()).hexdigest()


def test_official_static_auditor_proves_closed_bar_access() -> None:
    auditor = load_auditor()
    source_findings, allowed = auditor.audit_file(SOURCE)
    include_findings, _ = auditor.audit_file(INCLUDE)
    assert source_findings == []
    assert include_findings == []
    assert any(item["rule"] == "iTime_zero" for item in allowed)
