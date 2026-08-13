from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / "EA_VolRegime_EUR_M15_V9.mq5").read_text(encoding="utf-8")
task = (root / "research" / "HYP-VRE-EURUSD-M15-001_BASELINE_TASK.json").read_text(encoding="utf-8")

checks = {
    "single_symbol_shift1": "CopyRates(_Symbol,PERIOD_M15,1,need,r)" in src,
    "no_reference_copy": "InpJPYSymbol" not in src and "InpGBPSymbol" not in src,
    "atr_fast_slow": "atr_fast=fast/InpATRFastPeriod;atr_slow=slow/InpATRSlowPeriod" in src,
    "vol_ratio": "vol_ratio=atr_fast/atr_slow" in src,
    "expansion_threshold": "vr<InpVolRatioThreshold||br<InpBodyMinRatio" in src,
    "immediate_confirmation": "g_state==EXPANSION_DETECTED" in src and "bar.time<=g_expansion_time" in src,
    "same_direction": "bar.close>bar.open:bar.close<bar.open" in src,
    "reverse_cap": "reverse<=InpConfirmReverseMaxATR*af" in src,
    "failed_confirm_resets": "g_confirm_failures++;ResetExpansion();return(false)" in src,
    "primary_control_lock": "CONFIRM_PRIMARY" in src and "DIRECT_EXPANSION_CONTROL" in src,
    "one_owned_position": "AnySymbolExposure()" in src and "POSITION_MAGIC" in src,
    "compact_logging": "LogLevel(LOG_LEVEL_NO)" in src,
    "no_take_profit": "PositionOpen(_Symbol,type,volume,entry,sl,0.0" in src,
    "risk_caps": all(x in src for x in ("InpRiskPercent", "InpMaxNotionalMult", "InpMaxMarginUsagePct")),
    "frozen_task": all(x in task for x in ("2018.01.01", "2022.01.01", '"model":0', '"optimization_authorized":false')),
}

failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("FAIL: " + ", ".join(failed))
print(f"PASS {len(checks)}/{len(checks)} VRE contract checks")
