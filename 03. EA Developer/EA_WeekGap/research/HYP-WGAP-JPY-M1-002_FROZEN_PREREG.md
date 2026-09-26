# HYP-WGAP-JPY-M1-002 — FROZEN (slot-variant measurement cell)

Parent: HYP-WGAP-JPY-M1-001 (frozen prereg same dir). This is a SENSITIVITY
CELL, not a new candidate claim: identical mechanism, identical contract,
one input change — signal slot moved from Mon 01:00 to Mon 00:05 server.

Why: lab M1 cannot measure the 00:00-00:10 week-open roll (100% of paths
suspect — fabricated bars). The tester reconstructs real ticks inside burst
regions, so only a governed run measures this slot truthfully. Lab's dirty-
path estimate (PF ~3.8 vs 2.30 at 01:00) is void as evidence but motivates
the measurement.

Frozen inputs (identical to parent unless listed):
- Symbol USDJPY, M1, window 2010.01.04-2026.09.18, Model 0, spread=4pts
- InpSignalHourServer=0, InpSignalMinuteServer=5  (CHANGED)
- InpGapThreshPips=2.0, InpSlPips=20.0, InpMaxHoldBars=61, all else = parent

Acceptance: this cell is a measurement. Its result informs the parent
mechanism's slot choice; it does not independently claim GOAL fitness
(cadence ceiling ~0.5/wk is structural and already declared).
