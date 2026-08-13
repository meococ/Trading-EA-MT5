from pathlib import Path
s=(Path(__file__).resolve().parents[1]/"EA_VWAP_Disloc_EUR_M5_V4.mq5").read_text(encoding="utf-8")
must=["CopyRates(_Symbol,PERIOD_M5,1,required,rates)","CopyBuffer(g_atr_handle,0,1,1,values)","for(int i=0;i<InpVWAPWindow;i++)","rates[i].tick_volume<=0","g_state==STATE_DISLOCATION","bar.time>g_disloc_time","MathMin(volume_risk,MathMin(volume_notional,volume_margin))","PositionOpen(_Symbol,type,volume,entry,sl,0.0,InpVariantTag)","DATA_EPOCH_D0_SERIES_PROOF"]
for x in must:
    assert x in s,x
for x in ["CopyRates(_Symbol,PERIOD_M5,0,","CopyBuffer(g_atr_handle,0,0,","InpTargetR","vol = 1.0"]:
    assert x not in s,x
print("PASS 13/13 VDR MQL contract checks")
