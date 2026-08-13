from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / "EA_EffPersist_USDJPY_M15_V7.mq5").read_text(encoding="utf-8")
task = (root / "research" / "HYP-EPC-USDJPY-M15-001_BASELINE_TASK.json").read_text(encoding="utf-8")

checks = {
    "closed_bar_copy": "CopyRates(_Symbol,PERIOD_M15,1,need,r)" in src,
    "availability_proof": "availability-bar.time)!=PeriodSeconds(PERIOD_M15)" in src,
    "er_formula": "er=MathAbs(delta)/path" in src,
    "zero_range_fail_closed": "g_zero_range++;er=0.0;direction=0" in src,
    "trigger_threshold": "er<InpEREntryThreshold" in src,
    "later_persistence": "bar.time<=g_trigger_time" in src and "g_persist_age++" in src,
    "persistence_window": "g_persist_age>=InpMaxBarsToPersist" in src,
    "same_direction": "direction==g_eff_direction" in src,
    "reverse_cap": "reverse<=InpMaxReverseATR*atr" in src,
    "primary_control_lock": "PERSIST_PRIMARY" in src and "DIRECT_ER_CONTROL" in src,
    "one_owned_position": "AnySymbolExposure()" in src and "POSITION_MAGIC" in src,
    "trailing_closed_bar": "g_trail_armed&&new_bar" in src,
    "no_take_profit": "PositionOpen(_Symbol,type,volume,entry,sl,0.0" in src,
    "risk_caps": all(x in src for x in ("InpRiskPercent", "InpMaxNotionalMult", "InpMaxMarginUsagePct")),
    "frozen_task": all(x in task for x in ("2018.01.01", "2022.01.01", '"model":0', '"optimization_authorized":false')),
}

failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("FAIL: " + ", ".join(failed))
print(f"PASS {len(checks)}/{len(checks)} EPC contract checks")
