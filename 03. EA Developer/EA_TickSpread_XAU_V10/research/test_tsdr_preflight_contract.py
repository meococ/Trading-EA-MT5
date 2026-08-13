from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "EA_TickSpread_XAU_V10.mq5").read_text(encoding="utf-8")

checks = {
    "strict": "#property strict" in SRC,
    "tick_api": "SymbolInfoTick(_Symbol,tick)" in SRC,
    "millisecond_clock": "tick.time_msc" in SRC,
    "xau_binding": '_Symbol!="XAUUSD"' in SRC,
    "m1_binding": "_Period!=PERIOD_M1" in SRC,
    "five_days": "InpRequiredBrokerDays==5" in SRC,
    "no_trade_include": "<Trade/Trade.mqh>" not in SRC,
    "no_position_open": "PositionOpen(" not in SRC,
    "no_order_send": "OrderSend(" not in SRC,
    "no_copy_ticks": "CopyTicks" not in SRC,
    "histogram": "HistogramQuantile" in SRC,
    "equal_time_excluded": "t==g_last_time_msc" in SRC,
    "long_run_gate": "long_run_pct<=InpLongZeroRunMaxPct" in SRC,
    "frozen_inputs": "InputsAreFrozen" in SRC,
    "blocked_verdict": '"DATA_FRONTIER_BLOCKED"' in SRC,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("FAIL " + ", ".join(failed))
print(f"PASS {len(checks)}/{len(checks)} TSDR P0 contract checks")
