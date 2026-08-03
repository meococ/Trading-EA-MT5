import hashlib
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_LOMX_MultiAssetMomentum.mq5"
CONTRACT = ROOT / "ALPHAFACTORY_EA_CONTRACT.json"
README = ROOT / "README.md"
RESEARCH = ROOT / "research"
REGISTRY = ROOT.parents[1] / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized_overrides(text: str) -> dict[str, str]:
    values = dict(sorted(item.split("=", 1) for item in text.split(";") if item))
    if values.get("InpEngineMode") == "ENGINE_SWEEP":
        values["InpEngineMode"] = "0"
    return values


def test_build_is_default_off_and_does_not_bind_the_draft_hypothesis() -> None:
    text = source()
    assert 'input bool   InpResearchAutoMode=false;' in text
    assert 'input string InpHypothesisId="UNREGISTERED_BUILD_ONLY";' in text
    assert "HYP-LOMX-MULTI-M5-001" not in text
    assert "if(!InpResearchAutoMode)" in text
    assert 'InpHypothesisId=="UNREGISTERED_BUILD_ONLY"' in text
    assert "_Period!=PERIOD_M5" in text


def test_separable_engines_and_sweep_priority_router_are_present() -> None:
    text = source()
    for token in (
        "ENGINE_SWEEP",
        "ENGINE_BREAKOUT",
        "ENGINE_BOTH",
        "EvaluateSweep",
        "EvaluateBreakout",
        "g_both_collisions",
        "SWEEP_PRIORITY",
    ):
        assert token in text
    router = re.search(r"bool SelectSignal\(.+?\n  \}", text, re.S)
    assert router, "SelectSignal router is missing"
    assert router.group(0).find("sweep.fired") < router.group(0).find("breakout.fired")


def test_closed_bar_data_contract_has_no_bar_zero_signal_reads() -> None:
    text = source()
    assert "CopyRates(_Symbol,PERIOD_M5,1,CLOSED_BAR_COUNT" in text
    assert "CopyRates(_Symbol,PERIOD_M5,1,ASIAN_LOOKBACK_BAR_COUNT" in text
    assert "CopyBuffer(g_atr_handle,0,1,1" in text
    assert "SeriesInfoInteger(_Symbol,PERIOD_M5,SERIES_LASTBAR_DATE" in text
    assert "iTime(_Symbol,PERIOD_M5,0)" not in text
    forbidden = (
        r"i(?:Open|High|Low|Close|TickVolume)\s*\([^;]*,\s*0\s*\)",
        r"CopyRates\s*\([^;]*,\s*0\s*,",
        r"CopyBuffer\s*\([^;]*,\s*0\s*,\s*0\s*,",
    )
    for pattern in forbidden:
        assert not re.search(pattern, text), pattern


def test_fivepercent_hybrid_clock_and_frozen_utc_sessions() -> None:
    text = source()
    for token in (
        "IsEuropeDstUtc",
        "IsUnitedStatesDstUtc",
        "parts.year<=2023",
        "ServerToUtc",
        "UtcToServer",
        "ASIAN_START_MINUTE=0",
        "ASIAN_END_MINUTE=6*60",
        "TRADE_START_MINUTE=7*60",
        "TRADE_END_MINUTE=16*60",
        "ASIAN_BAR_COUNT=72",
        "ASIAN_LOOKBACK_BAR_COUNT=200",
    ):
        assert token in text
    assert "closed[j].time!=expected_server" in text
    assert "expected_utc=utc_day_start+(InpAsianStartMinutesUtc+i*5)*60" in text


def test_sweep_engine_geometry_and_volume_zscore_are_frozen() -> None:
    text = source()
    for token in (
        "SWEEP_ATR_MULT=0.30",
        "SWEEP_VOLUME_Z=1.50",
        "SWEEP_STOP_ATR_MULT=0.20",
        "SWEEP_MIN_TP2_R=1.50",
        "rates[0].low<asian_low-InpSweepEpsilonMult*atr",
        "rates[0].close>asian_low",
        "rates[0].high>asian_high+InpSweepEpsilonMult*atr",
        "rates[0].close<asian_high",
        "TickVolumeZScore(rates,0,InpVolumeLookback",
        "signal.tp1=(asian_high+asian_low)/2.0",
        "SubmitPartialClose",
        "SubmitBreakEven",
    ):
        assert token in text


def test_breakout_engine_geometry_is_frozen() -> None:
    text = source()
    for token in (
        "BREAKOUT_CONTRACTION_RATIO=0.70",
        "BREAKOUT_BUFFER_ATR_MULT=0.20",
        "BREAKOUT_STOP_ATR_MULT=0.10",
        "BREAKOUT_TARGET_R=2.0",
        "for(int i=2;i<=51;i++)",
        "for(int i=1;i<=15;i++)",
        "for(int i=1;i<=InpVolumeLookback;i++)",
        "rates[1].high-rates[1].low",
        "rates[0].close>box_high+BREAKOUT_BUFFER_ATR_MULT*atr",
        "rates[0].close<box_low-BREAKOUT_BUFFER_ATR_MULT*atr",
    ):
        assert token in text


def test_execution_is_symbol_scoped_synchronous_and_risk_safe() -> None:
    text = source()
    assert "OwnedPositionTicket" in text and "HasOwnedPendingOrder" in text
    assert "POSITION_SYMBOL)==_Symbol" in text
    assert "POSITION_MAGIC)==InpMagic" in text
    assert "ORDER_SYMBOL)==_Symbol" in text
    assert "ORDER_MAGIC)==InpMagic" in text
    assert not re.search(r"if\s*\(\s*PositionsTotal\s*\(\s*\)\s*>\s*0", text)
    assert "OrderCalcProfit" in text
    assert "OrderCalcMargin" in text
    assert "ACCOUNT_MARGIN_SO_MODE" in text
    assert "ACCOUNT_MARGIN_SO_SO" in text
    assert "ACCOUNT_STOPOUT_MODE_MONEY" in text
    assert "MARGIN_HEADROOM_RESERVE_FACTOR=0.20" in text
    assert "MARGIN_FREE_EQUITY_FLOOR=0.01" in text
    assert "ACCOUNT_MARGIN_SO_CALL" in text
    assert "MARGIN_DEPOSIT_BELOW_MONEY_THRESHOLD" in text
    assert "MarginSafeVolume" in text
    assert "FloorHalfSplittableVolume" in text
    assert "margin_stopout_clamps" in text
    assert "SYMBOL_TRADE_TICK_SIZE" in text
    assert "SYMBOL_TRADE_TICK_VALUE_LOSS" in text
    assert "MathFloor" in text and "SYMBOL_VOLUME_STEP" in text
    assert "SYMBOL_TRADE_STOPS_LEVEL" in text
    assert "SYMBOL_TRADE_FREEZE_LEVEL" in text
    assert "InpMaxSpreadToRisk" in text
    assert "OrderCheck" in text and "OrderSend" in text
    assert "SetAsyncMode(true)" not in text


def test_persistent_daily_lock_friday_flatten_and_lot_consistency() -> None:
    text = source()
    for token in (
        "DAILY_LOSS_LOCK_PCT=3.5",
        "DailyStatePrefix",
        "ACCOUNT_LOGIN",
        "InpHypothesisId",
        "_Symbol",
        "GlobalVariableSet",
        "InpMaxTradesPerDay",
        "InpMaxAccountDrawdownPct",
        "AccountRiskKey",
        "MQLInfoInteger(MQL_TESTER)",
        'AccountRiskKey("PEAK")',
        'AccountRiskKey("DDLOCK")',
        "InpDailyFlattenMinutesUtc",
        "parts.day_of_week==5",
        "minute_of_day>=InpFridayFlattenMinutesUtc",
        "InpMaxHoldBars",
        "LOMX_OVERNIGHT_GUARD",
        "LOMX_MAX_HOLD",
        "CloseOwnedPositions",
        "DeleteOwnedPendingOrders",
        "LotConsistencyReference",
        "InpLotConsistencyMinFills",
        "HistoryDealGetInteger(ticket,DEAL_MAGIC)!=InpMagic",
    ):
        assert token in text


def test_lifecycle_v3_uses_real_deals_and_one_final_close_guard() -> None:
    text = source()
    for token in (
        "void OnTradeTransaction",
        "TRADE_TRANSACTION_DEAL_ADD",
        "DEAL_TIME_MSC",
        "DEAL_VOLUME",
        "DEAL_PRICE",
        "DEAL_COMMISSION",
        "DEAL_SWAP",
        "DEAL_FEE",
        "RemainingVolumeThroughDeal",
        "FinalCloseAlreadyLogged",
        "MarkFinalCloseLogged",
        '"engine_name"',
        '"initial_risk_account"',
        '"is_final_close"',
        '"deal_profit"',
        '"deal_commission"',
        '"deal_swap"',
        '"deal_fee"',
        '"deal_net"',
    ):
        assert token in text
    assert re.search(r"deal_time_msc<=0\s*\|\|\s*deal_volume<=0\.0\s*\|\|\s*deal_price<=0\.0", text)
    assert not re.search(r"FileWrite\([^;]+position_id,\s*0\.0,\s*0\.0", text, re.S)


def test_runtime_metadata_and_pending_context_are_truthful_and_fail_closed() -> None:
    text = source()
    assert '(InpResearchAutoMode ? "true" : "false")' in text
    assert '(InpHypothesisId=="UNREGISTERED_BUILD_ONLY" ? "true" : "false")' in text
    assert "void ClearPendingEntryContext()" in text
    assert text.count("ClearPendingEntryContext();") >= 3
    assert "row_initial_risk_account=fill_loss_per_lot*deal_volume" in text


def test_contract_and_readme_are_build_only_and_accurate() -> None:
    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "alphafactory_ea_contract.v1"
    assert payload["telemetry_profile"] == "lifecycle-v3"
    assert payload["market_phase_adapter"] == "none"
    assert payload["variant_tag_input"] == "InpVariantTag"
    profile = payload["execution_profile"]
    assert profile["authority"] == "build-only-default"
    assert profile["timeframe"] == "M5"
    assert profile["research_auto_mode_default"] is False
    assert profile["hypothesis_id_default"] == "UNREGISTERED_BUILD_ONLY"
    assert profile["engine_modes"] == ["SWEEP", "BREAKOUT", "BOTH"]
    expected_inputs = {
        "InpResearchAutoMode": False,
        "InpEnableTelemetry": True,
        "InpHypothesisId": "UNREGISTERED_BUILD_ONLY",
        "InpVariantTag": "BUILD_SCAFFOLD_BOTH",
        "InpEngineMode": "ENGINE_BOTH",
        "InpMagic": 5603100,
        "InpRiskPercent": 0.25,
        "InpMaxDailyLossPct": 3.5,
        "InpMaxAccountDrawdownPct": 8.0,
        "InpMaxSpreadToRisk": 0.15,
        "InpMaxTradesPerDay": 3,
        "InpATRPeriod": 14,
        "InpSweepEpsilonMult": 0.3,
        "InpSweepStopAtrMult": 0.2,
        "InpSweepMinTp2R": 1.5,
        "InpVolumeLookback": 20,
        "InpVolumeThreshold": 1.5,
        "InpAsianStartMinutesUtc": 0,
        "InpAsianEndMinutesUtc": 360,
        "InpTradeStartMinutesUtc": 420,
        "InpTradeEndMinutesUtc": 960,
        "InpDailyFlattenMinutesUtc": 1200,
        "InpFridayFlattenMinutesUtc": 1200,
        "InpSweepScaleOutFraction": 0.5,
        "InpMaxHoldBars": 96,
        "InpLotConsistencyMinFills": 10,
        "InpLotConsistencyLookbackFills": 10,
        "InpLotConsistencyMinFactor": 0.5,
        "InpLotConsistencyMaxFactor": 1.5,
    }
    assert payload["inputs"] | expected_inputs == payload["inputs"]
    assert {key: payload["inputs"][key] for key in expected_inputs} == expected_inputs
    text = source()
    for name in expected_inputs:
        assert re.search(rf"^input\s+[^;\n]*\b{re.escape(name)}\b", text, re.M), name
        assert text.count(name) >= 2, f"{name} is declared but not bound to behavior"
    assert "reference=sum/fills" in text
    assert "AvgLot10" in text
    readme = README.read_text(encoding="utf-8")
    assert "engineering-valid" in readme.lower()
    assert "economic-invalid" in readme.lower()
    assert "no optimization, validation, holdout, paper or live authority" in readme.lower()


def test_model0_authority_artifacts_are_hash_and_override_consistent() -> None:
    prereg = RESEARCH / "HYP-LASR-XAUUSD-M5-001_FROZEN_PREREG.md"
    task_path = (
        RESEARCH
        / "preflight"
        / "HYP-LASR-XAUUSD-M5-001"
        / "task_packet.control.json"
    )
    prereg_text = prereg.read_text(encoding="utf-8")
    match = re.search(r"Exact overrides, sorted and immutable:\s*```text\s*(.+?)\s*```", prereg_text, re.S)
    assert match is not None
    frozen = normalized_overrides(match.group(1).strip())

    task_builder = load_module(RESEARCH / "build_lasr_task_packet.py", "lasr_task_builder")
    registrar = load_module(RESEARCH / "register_lasr_xauusd_m5_001.py", "lasr_registrar")
    task = json.loads(task_path.read_text(encoding="utf-8-sig"))
    latest = [
        json.loads(line)
        for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and json.loads(line).get("hypothesis_id") == "HYP-LASR-XAUUSD-M5-001"
    ][-1]

    assert task["deposit"] == 10000
    assert latest["prereg_sha256"] == hashlib.sha256(prereg.read_bytes()).hexdigest().upper()
    assert task["source_sha256"] == latest["source_hash"]
    assert normalized_overrides(task_builder.OVERRIDES) == frozen
    assert normalized_overrides(registrar.OVERRIDES) == frozen
    assert normalized_overrides(task["overrides"]) == frozen
    assert normalized_overrides(latest["exact_overrides"]) == frozen


def test_parked_eurusd_002_preflight_authority_is_coherent() -> None:
    hypothesis_id = "HYP-LASR-EURUSD-M5-002"
    prereg = RESEARCH / f"{hypothesis_id}_FROZEN_PREREG.md"
    task_path = RESEARCH / "preflight" / hypothesis_id / "task_packet.control.json"
    audit_path = RESEARCH / "evidence" / hypothesis_id / "STATIC_AUDIT" / "NONREPAINT_AUDIT.json"
    builder = load_module(
        RESEARCH / "build_lasr_eurusd_m5_002_task_packet.py",
        "lasr_eurusd_m5_002_task_builder",
    )
    task = json.loads(task_path.read_text(encoding="utf-8-sig"))
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    latest = [
        json.loads(line)
        for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and json.loads(line).get("hypothesis_id") == hypothesis_id
    ][-1]
    match = re.search(
        r"Exact overrides, sorted and immutable:\s*```text\s*(.+?)\s*```",
        prereg.read_text(encoding="utf-8"),
        re.S,
    )
    assert match is not None
    frozen = normalized_overrides(match.group(1).strip())

    assert latest["state"] == "parked"
    assert latest["validation"]["model0_authorized"] is False
    assert latest["metrics"]["performance_outcome_reads"] == 0
    assert latest["metrics"]["mt5_launches"] == 0
    assert latest["validation"]["signal_rules_changed"] is False
    assert latest["validation"]["margin_safety_repair_only"] is True
    assert task["source_sha256"] == latest["source_hash"]
    assert task["prereg_sha256"] == hashlib.sha256(prereg.read_bytes()).hexdigest().upper()
    assert task["prereg_sha256"] == latest["prereg_sha256"]
    assert audit["status"] == "PASS"
    assert audit["audited_files"][0]["sha256"] == task["source_sha256"]
    assert normalized_overrides(builder.OVERRIDES) == frozen
    assert normalized_overrides(task["overrides"]) == frozen
    assert normalized_overrides(latest["exact_overrides"]) == frozen
    assert task["deposit"] == 10000 and task["leverage"] == 100
    assert task["data_fingerprint"] == latest["validation"]["data_fingerprint"]


def test_parked_eurusd_003_invalid_identity_is_coherent() -> None:
    hypothesis_id = "HYP-LASR-EURUSD-M5-003"
    prereg = RESEARCH / f"{hypothesis_id}_FROZEN_PREREG.md"
    task_path = RESEARCH / "preflight" / hypothesis_id / "task_packet.control.json"
    audit_path = RESEARCH / "evidence" / hypothesis_id / "STATIC_AUDIT" / "NONREPAINT_AUDIT.json"
    builder = load_module(
        RESEARCH / "build_lasr_eurusd_m5_003_task_packet.py",
        "lasr_eurusd_m5_003_task_builder",
    )
    task = json.loads(task_path.read_text(encoding="utf-8-sig"))
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    latest = [
        json.loads(line)
        for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and json.loads(line).get("hypothesis_id") == hypothesis_id
    ][-1]
    match = re.search(
        r"Exact overrides, sorted and immutable:\s*```text\s*(.+?)\s*```",
        prereg.read_text(encoding="utf-8"),
        re.S,
    )
    assert match is not None
    frozen = normalized_overrides(match.group(1).strip())

    assert latest["state"] == "parked"
    assert latest["validation"]["model0_authorized"] is False
    assert latest["validation"]["economic_verdict_authorized"] is False
    assert latest["validation"]["strong_adverse_prior"] is True
    assert latest["metrics"]["performance_outcome_reads"] == 1
    assert task["source_sha256"] == latest["source_hash"]
    assert task["prereg_sha256"] == hashlib.sha256(prereg.read_bytes()).hexdigest().upper()
    assert task["prereg_sha256"] == latest["prereg_sha256"]
    assert audit["status"] == "PASS"
    assert audit["audited_files"][0]["sha256"] == task["source_sha256"]
    assert normalized_overrides(builder.OVERRIDES) == frozen
    assert normalized_overrides(task["overrides"]) == frozen
    assert normalized_overrides(latest["exact_overrides"]) == frozen
    assert task["deposit"] == 100000 and task["leverage"] == 100
    assert task["account_fingerprint"] == latest["validation"]["expected_account_fingerprint"]
    assert task["data_fingerprint"] == latest["validation"]["expected_data_fingerprint"]
    assert task["account_fingerprint"] != latest["validation"]["actual_account_fingerprint"]
    assert task["data_fingerprint"] != latest["validation"]["actual_data_fingerprint"]


def test_preordered_breakout_authority_is_coherent() -> None:
    hypothesis_id = "HYP-CBRK-EURUSD-M5-001"
    prereg = RESEARCH / f"{hypothesis_id}_FROZEN_PREREG.md"
    task_path = RESEARCH / "preflight" / hypothesis_id / "task_packet.control.json"
    audit_path = RESEARCH / "evidence" / hypothesis_id / "STATIC_AUDIT" / "NONREPAINT_AUDIT.json"
    failure_path = RESEARCH / f"{hypothesis_id}_FAILURE_PACKET.json"
    builder = load_module(
        RESEARCH / "build_cbrk_eurusd_m5_001_task_packet.py",
        "cbrk_eurusd_m5_001_task_builder",
    )
    task = json.loads(task_path.read_text(encoding="utf-8-sig"))
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    failure = json.loads(failure_path.read_text(encoding="utf-8-sig"))
    latest = [
        json.loads(line)
        for line in REGISTRY.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and json.loads(line).get("hypothesis_id") == hypothesis_id
    ][-1]
    match = re.search(
        r"Exact overrides, sorted and immutable:\s*```text\s*(.+?)\s*```",
        prereg.read_text(encoding="utf-8"),
        re.S,
    )
    assert match is not None
    frozen = normalized_overrides(match.group(1).strip())

    assert latest["state"] == "killed"
    assert latest["verdict"] == "KILL_BASE_PF_AND_CADENCE_FAIL_COST_NOT_REQUIRED"
    assert latest["validation"]["model0_authorized"] is False
    assert latest["validation"]["economic_verdict_authorized"] is True
    assert latest["validation"]["economic_valid"] is False
    assert latest["validation"]["edge_killed"] is True
    assert latest["validation"]["validation_access_authorized"] is False
    assert latest["validation"]["holdout_access_authorized"] is False
    assert latest["validation"]["paper_trading_authorized"] is False
    assert latest["validation"]["live_trading_authorized"] is False
    assert task["source_sha256"] == hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper()
    assert task["source_sha256"] == latest["source_hash"]
    assert task["prereg_sha256"] == hashlib.sha256(prereg.read_bytes()).hexdigest().upper()
    assert task["prereg_sha256"] == latest["prereg_sha256"]
    assert audit["status"] == "PASS"
    assert normalized_overrides(builder.OVERRIDES) == frozen
    assert normalized_overrides(task["overrides"]) == frozen
    assert normalized_overrides(latest["exact_overrides"]) == frozen
    assert task["deposit"] == 100000 and task["leverage"] == 100
    assert task["account_fingerprint"] == latest["validation"]["account_fingerprint"]
    assert task["data_fingerprint"] == latest["validation"]["data_fingerprint"]
    assert failure["decision"]["engineering_valid"] is True
    assert failure["decision"]["edge_killed"] is True
    assert failure["model0_result"]["n_trades"] == 402
    assert failure["model0_result"]["profit_factor"] < 1.3
    assert failure["model0_result"]["trades_per_elapsed_week"] < 2.0
    assert failure["model0_result"]["max_drawdown_pct"] < 8.0
    assert latest["validation"]["failure_packet_sha256"] == hashlib.sha256(
        failure_path.read_bytes()
    ).hexdigest().upper()
