from pathlib import Path

root = Path(__file__).resolve().parents[1]
src = (root / "EA_EffPersist_USDJPY_M15_V7R1.mq5").read_text(encoding="utf-8")
task = (root / "research" / "HYP-EPC-USDJPY-M15-002_BASELINE_TASK.json").read_text(encoding="utf-8")

checks = {
    "new_identity": all(x in src for x in ("EA_EffPersist_USDJPY_M15_V7R1", "HYP-EPC-USDJPY-M15-002", "5605302")),
    "closed_bar_copy": "CopyRates(_Symbol,PERIOD_M15,1,need,r)" in src,
    "er_formula": "er=MathAbs(delta)/path" in src,
    "same_persistence": all(x in src for x in ("er<InpERPersistThreshold", "direction==g_eff_direction", "reverse<=InpMaxReverseATR*atr")),
    "same_stop_exit": all(x in src for x in ("InpSLBufferATR", "InpBETriggerR", "InpTrailStartR", "InpTimeStopBars")),
    "compact_trade_library": "LogLevel(LOG_LEVEL_NO)" in src,
    "compact_custom_logs": all(x in src for x in ("EPC002_INIT", "EPC002_ENTRY", "EPC002_EXIT", "EPC002_SUMMARY")),
    "verbose_state_removed": not any(x in src for x in ("EPC002_HIGH_EFF", "EPC002_PERSIST", "EPC002_SIGNAL", "EPC002_STOP_MOVE", "EPC002_CLOSE_REQUEST")),
    "no_take_profit": "PositionOpen(_Symbol,type,volume,entry,sl,0.0" in src,
    "frozen_task": all(x in task for x in ("2018.01.01", "2022.01.01", '"model":0', '"optimization_authorized":false')),
}

failed = [name for name, passed in checks.items() if not passed]
if failed:
    raise SystemExit("FAIL: " + ", ".join(failed))
print(f"PASS {len(checks)}/{len(checks)} EPC runtime-reissue checks")
