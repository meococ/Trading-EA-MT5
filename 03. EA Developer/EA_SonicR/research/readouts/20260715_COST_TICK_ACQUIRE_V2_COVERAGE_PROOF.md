# Cost/tick acquire V2 — coverage proof

## Question

Did this board clear research-grade multi-month bid/ask×commission×slip freeze?

## Answer

**NO — research-grade freeze still blocked.**

### Observed (honest max tonight)

- Union quote days: **2** / 90
- MT5 day-chunk max: **2** calendar day(s)
- Symbols probed: **11** (primary+majors+BTC)
- Sessions seen: `['ASIA', 'LONDON', 'LONDON_NY', 'NY', 'OFF']`
- Commission merged: `{'BTCUSD': 3, 'EURUSD': 2}`
- Slip: **0** (MISSING ≠ 0 if side-ref absent)

- Diagnostic table SHA: `5E92CC645139741288D12D4105DA6DFD6C819437CE8B24A710BD266D16BE32BB` grade=`SINGLE_DAY_OR_SHALLOW_HISTORY_DIAGNOSTIC_ONLY`

### Exact remaining GAP

- `quote_days=2/90`
- `EURUSD_comm=2/30`
- `USDJPY_comm=0/30`
- `slip≈0/100+_MISSING_NE_0`

### What unlocks freeze

- >=90 distinct UTC quote days (Real QFSI accumulate multi-week OR broker/vendor multi-month tick tape)
- >=30 unique commission observations per primary (EURUSD, USDJPY) from Real deal history
- >=100 side-referenced fill/slip samples per primary symbol (order→fill, not deal.profit alone)
- Do not use Strategy Tester 'current' spread as research cost surface
- Bulk copy_ticks_range multi-month hangs this terminal — need chunked offline dump or vendor tape

### Binding blocker

`COST_PROVENANCE_GAP` remains **NARROWED_NOT_CLEARED**. Track B monetization rebuild proceeds without inventing a surface.

Receipt: `80EF7C186468219D4DDB93BCB7956BD0E1F75B00877B6BE59C9E2493C91B4E70`
Sample: `03. EA Developer/EA_SonicR/research/preflight/20260715_COST_TICK_ACQUIRE_V2.json`

