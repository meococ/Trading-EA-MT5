from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / "EA_Residual_EUR_M15_V8.mq5").read_text(encoding="utf-8")
task = (root / "research" / "HYP-XRV-EURUSD-M15-001_BASELINE_TASK.json").read_text(encoding="utf-8")

checks = {
    "three_shift1_series": all(x in src for x in ('CopyRates(_Symbol,PERIOD_M15,1,2,e)', 'CopyRates(InpJPYSymbol,PERIOD_M15,1,2,j)', 'CopyRates(InpGBPSymbol,PERIOD_M15,1,2,g)')),
    "current_time_sync": "e[0].time!=j[0].time||e[0].time!=g[0].time" in src,
    "prior_time_sync": "e[1].time!=j[1].time||e[1].time!=g[1].time" in src,
    "zero_volume_fail_closed": all(x in src for x in ("e[0].tick_volume<=0", "j[1].tick_volume<=0", "g[1].tick_volume<=0")),
    "warmup_50": "g_sync_warmup<InpSyncWarmupBars" in src,
    "residual_formula": "basket=(-rj+rg)/2.0,residual=re-basket" in src,
    "separate_reversion_bar": "bar.time<=g_disloc_time" in src and "g_disloc_age++" in src,
    "forty_percent_retrace": "retrace>=InpRetracementPct" in src,
    "eur_reversion_close": "bar.close<bar.open:bar.close>bar.open" in src,
    "primary_control_lock": "RETRACE_PRIMARY" in src and "DIRECT_RESIDUAL_CONTROL" in src,
    "one_owned_position": "AnySymbolExposure()" in src and "POSITION_MAGIC" in src,
    "no_take_profit": "PositionOpen(_Symbol,type,volume,entry,sl,0.0" in src,
    "risk_caps": all(x in src for x in ("InpRiskPercent", "InpMaxNotionalMult", "InpMaxMarginUsagePct")),
    "frozen_task": all(x in task for x in ("2018.01.01", "2022.01.01", '"model":0', '"optimization_authorized":false')),
}

failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("FAIL: " + ", ".join(failed))
print(f"PASS {len(checks)}/{len(checks)} XRV contract checks")
