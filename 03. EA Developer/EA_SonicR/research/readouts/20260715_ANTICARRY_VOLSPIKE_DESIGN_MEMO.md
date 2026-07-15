# Design memo — Anti-carry × vol-spike FX3

Parent: carry/swap-diff ALL_KILL; 6J densify INTAKE_KILL; G10 acquire BLOCKED.

## Design 1
`HYP-FX3-ANTICARRY-VOLSPIKE-H4-001`
When global FX vol AR(1) residual > 0: short highest-carry / long lowest-carry
(|carry|≥0.25); H4 entry next day; SL 1.5 ATR; hold≤8; ≤2 book.

## Design 2
`HYP-FX3-ANTICARRY-VOLSPIKE-D1CONFIRM-001`
Same + require prior 2 D1 closes moved WITH carry (crowding) before anti-carry.

## ≠ killed
≠ V8_CARRY_VOL_REGIME (WITH-carry when vol calm); ≠ V8 weekly/daily/5bp rank;
≠ USBILL; ≠ 6J z-gate; ≠ Mon→Thu harvest / flush-MR from prior board.
