from pathlib import Path

src = (Path(__file__).resolve().parents[1] / "EA_FixClock_EUR_M5_V11P.mq5").read_text(encoding="utf-8")
checks = {
    "identity": "HYP-FIXCLK-EURUSD-M5-001" in src,
    "binding": '_Symbol!="EURUSD"' in src and "_Period!=PERIOD_M5" in src,
    "closed_bar_clock": "SERIES_LASTBAR_DATE" in src and "CopyTime" in src,
    "canonical_d0": all(x in src for x in ("m5_synchronized=", "copytime_from_epoch=", "copytime_count=1")),
    "us_start": "FirstSunday(p.year,3)+7" in src,
    "uk_start": "LastSunday(p.year,3)" in src,
    "uk_end": "LastSunday(p.year,10)" in src,
    "us_end": "FirstSunday(p.year,11)" in src,
    "mismatch_gate": "g_mismatch_weeks>=InpRequiredMismatchWeeks" in src,
    "no_trade": "<Trade/Trade.mqh>" not in src and "OrderSend(" not in src and "PositionOpen(" not in src,
    "frozen": "InputsAreFrozen" in src,
    "blocked": "DATA_FRONTIER_BLOCKED_TIMEZONE" in src,
}
bad = [k for k, v in checks.items() if not v]
if bad:
    raise SystemExit("FAIL " + ", ".join(bad))
print(f"PASS {len(checks)}/{len(checks)} FIXCLK contract checks")
