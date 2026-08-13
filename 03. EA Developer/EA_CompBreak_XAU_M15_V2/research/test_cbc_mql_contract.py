from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[1] / "EA_CompBreak_XAU_M15_V2.mq5").read_text(encoding="utf-8")


def require(fragment: str, label: str) -> None:
    if fragment not in SOURCE:
        raise AssertionError(f"missing {label}: {fragment}")


def forbid(fragment: str, label: str) -> None:
    if fragment in SOURCE:
        raise AssertionError(f"forbidden {label}: {fragment}")


checks = [
    ("CopyRates(_Symbol,PERIOD_M15,1,required,rates)", "closed-bar rates"),
    ("CopyBuffer(g_atr_handle,0,1,1,values)", "closed-bar ATR"),
    ("for(int i=1;i<=InpCompressionBars;i++)", "box uses array indices 1..7"),
    ("const MqlRates bar=rates[0]", "break uses shift-1 bar"),
    ("g_box_age>=InpExpiryBars", "frozen box expiry"),
    ("g_entry_price+InpBEOffsetR*g_initial_risk", "long BE offset"),
    ("closed[0].close-InpTrailATRMult*atr", "closed-bar long trail"),
    ("MathMin(volume_risk,MathMin(volume_notional,volume_margin))", "three-way volume cap"),
    ("margin>free_margin*(InpMaxMarginUsagePct/100.0)+0.01", "post-normalization margin assertion"),
    ("notional>equity*InpMaxNotionalMult+0.01", "post-normalization notional assertion"),
    ("PositionOpen(_Symbol,order_type,volume,entry,sl,0.0,InpVariantTag)", "no hard TP"),
    ("DATA_EPOCH_D0_SERIES_PROOF", "canonical D0 proof"),
]

for fragment, label in checks:
    require(fragment, label)

forbid("CopyRates(_Symbol,PERIOD_M15,0,", "forming-bar rate copy")
forbid("CopyBuffer(g_atr_handle,0,0,", "forming-bar ATR copy")
forbid("InpTargetR", "unreachable fixed target")

print(f"PASS {len(checks) + 3}/15 CBC MQL contract checks")
