from pathlib import Path
s=(Path(__file__).resolve().parents[1]/"EA_LondonAuction_GBP_M15_V5.mq5").read_text(encoding="utf-8")
for x in ["CopyRates(_Symbol,PERIOD_M15,1,1,rates)","open_minute>=InpBalanceStartHour*60", "g_entries_today>0", "bar.time<=g_retest_time", "MathMin(vr,MathMin(vn,vm))", "PositionOpen(_Symbol,type,volume,entry,sl,0.0,InpVariantTag)", "DATA_EPOCH_D0_SERIES_PROOF"]: assert x in s,x
for x in ["CopyRates(_Symbol,PERIOD_M15,0,","InpTargetR"]: assert x not in s,x
print("PASS 9/9 LAR contract checks")
