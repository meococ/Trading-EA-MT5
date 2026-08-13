from pathlib import Path

src = (Path(__file__).resolve().parents[1] / "EA_FixReversal_EUR_M5_V11.mq5").read_text(encoding="utf-8")
checks = {
    "identity": "HYP-WMRR-EURUSD-M5-001" in src,
    "binding": '_Symbol!="EURUSD"' in src and "_Period!=PERIOD_M5" in src,
    "closed_rates": "CopyRates(_Symbol,PERIOD_M5,1,count,rates)" in src,
    "clock_convention": 'InpClockConvention=="US_DST_NY_CLOSE"' in src,
    "fix_18_19": "InpNormalFixHour==18" in src and "InpMismatchFixHour==19" in src,
    "us_uk_rules": all(x in src for x in ("FirstSunday(p.year,3)+7", "LastSunday(p.year,3)", "LastSunday(p.year,10)", "FirstSunday(p.year,11)")),
    "thirteen_bars": "InpMeasurementBars+1" in src and "r[InpMeasurementBars].close" in src,
    "contiguity": "BarsContiguous" in src,
    "fix_not_confirmation": "if(g_state==FIX_OBSERVED){EvaluateConfirmation(bar);return;}DetectFixWindow(bar);" in src,
    "three_confirmations": "InpMaxConfirmationBars==3" in src,
    "reversal_algebra": "g_fix_dir>0?r[0].close<=g_fix_close-threshold:r[0].close>=g_fix_close+threshold" in src,
    "atr_closed": "LoadClosedRates(InpATRPeriod+1,r)" in src,
    "one_day_latch": "g_day_latched" in src,
    "risk_caps": all(x in src for x in ("InpRiskPercent", "InpMaxNotionalMult", "InpMaxMarginUsagePct")),
    "stops_freeze": "SYMBOL_TRADE_FREEZE_LEVEL" in src and "g_stops_cancels" in src,
    "no_trailing": "PositionModify(" not in src,
    "canonical_d0": "copytime_from_epoch=" in src and "copytime_count=1" in src,
    "frozen": "InputsAreFrozen" in src,
}
bad = [k for k, v in checks.items() if not v]
if bad:
    raise SystemExit("FAIL " + ", ".join(bad))
print(f"PASS {len(checks)}/{len(checks)} WMRR contract checks")
