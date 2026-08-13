from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / "EA_VolThrust_XAU_M5_V6.mq5").read_text(encoding="utf-8")
task = (root / "research" / "HYP-VTC-XAUUSD-M5-001_BASELINE_TASK.json").read_text(encoding="utf-8")

checks = {
    "closed_bar_copy": "CopyRates(_Symbol,PERIOD_M5,1,need,r)" in src,
    "availability_proof": "availability-bar.time)!=PeriodSeconds(PERIOD_M5)" in src,
    "volume_fail_closed": "if(r[i].tick_volume<=0){g_missing_volume++;return(false);}" in src,
    "thrust_body": "body_ratio<InpThrustBodyMin" in src,
    "thrust_range_atr": "range_atr<InpThrustRangeATRMin" in src,
    "thrust_volume": "vol_ratio<InpThrustVolMult" in src,
    "separate_pause_bar": "bar.time<=g_thrust_time" in src and "g_thrust_age++" in src,
    "pause_no_new_extreme": "no_new_extreme" in src,
    "primary_control_lock": "PAUSE_PRIMARY" in src and "DIRECT_THRUST_CONTROL" in src,
    "one_owned_position": "AnySymbolExposure()" in src and "POSITION_MAGIC" in src,
    "trailing_closed_bar": "g_trail_armed&&new_bar" in src,
    "no_take_profit": "PositionOpen(_Symbol,type,volume,entry,sl,0.0" in src,
    "risk_caps": all(x in src for x in ("InpRiskPercent", "InpMaxNotionalMult", "InpMaxMarginUsagePct")),
    "frozen_task": all(x in task for x in ("2018.01.01", "2022.01.01", '"model":0', '"optimization_authorized":false')),
}

failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("FAIL: " + ", ".join(failed))
print(f"PASS {len(checks)}/{len(checks)} VTC contract checks")
