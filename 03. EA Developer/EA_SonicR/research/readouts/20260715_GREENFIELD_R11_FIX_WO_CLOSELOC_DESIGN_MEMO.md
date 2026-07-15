# Design — Round 11 London fix / weekly-open dist / closeloc

Date: 2026-07-15

## 1 `HYP-FX3-H1-LONDON-FIX-REVERSION-001`
Closed 15 UTC H1 body≥0.8 ATR + close in extreme 0.3; **fade**; first FX3; SL=1.2 RR=1.5 hold≤4.
Mechanism: into-fix inventory / WM-proxy reversion — ≠ London open drive, ≠ NY reopen.

## 2 `HYP-FX3-H1-WEEKLY-OPEN-DIST-FADE-001`
|close − weekly_open| ≥ 2.5 ATR; fade toward WO; first FX3; ≤1/ISO-week; SL=1.5 RR=1.5 hold≤12.
Mechanism: weekly mean-reversion to open — ≠ W1 HL-break, ≠ VWAP, ≠ PDH.

## 3 `HYP-FX3-H1-CLOSELOC-PRESSURE-CONT-001`
close_loc≥0.75 (or ≤0.25) + body≥0.5 ATR → continue; skip hours {3,7,13,15}; ≤2/day; SL=1.2 RR=2.0 hold≤8.
Mechanism: held backup from USD-lag board — first offline probe (≠ bodyATR densify).
