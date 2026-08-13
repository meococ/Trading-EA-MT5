from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "EA_TPR_EUR_M5_V3.mq5").read_text(encoding="utf-8")

required = {
    "closed rates": "CopyRates(_Symbol,PERIOD_M5,1,required,rates)",
    "closed buffers": "CopyBuffer(handle,0,1,1,values)",
    "trend expansion": "for(int i=0;i<InpExpansionBars;i++)",
    "pullback state": "g_state=STATE_PULLBACK",
    "resumption after pullback": "if(g_state==STATE_PULLBACK)",
    "next-bar assertion": "availability_time-bar.time",
    "closed-bar trail": "CopyRates(_Symbol,PERIOD_M5,1,1,closed)",
    "three-way cap": "MathMin(volume_risk,MathMin(volume_notional,volume_margin))",
    "margin assertion": "margin>free_margin*(InpMaxMarginUsagePct/100.0)+0.01",
    "notional assertion": "notional>equity*InpMaxNotionalMult+0.01",
    "no hard TP": "PositionOpen(_Symbol,order_type,volume,entry,sl,0.0,InpVariantTag)",
    "D0 proof": "DATA_EPOCH_D0_SERIES_PROOF",
}
for label, text in required.items():
    if text not in SOURCE:
        raise AssertionError(f"missing {label}: {text}")

for forbidden in ("CopyRates(_Symbol,PERIOD_M5,0,", "CopyBuffer(handle,0,0,", "InpTargetR"):
    if forbidden in SOURCE:
        raise AssertionError(f"forbidden contract fragment: {forbidden}")

print("PASS 15/15 TPR MQL contract checks")
