# VN action brief — Carry/swap-aware differential

- Intake de-dup: **CLEARED** (≠ V8 weekly/daily/5bp/vol; ≠ USBILL).
- Broker swap schedule: **GAP** → dùng G3 funding proxy.
- Offline 2 object → **OFFLINE_ALL_KILL / NO_MODEL0**:
  - `HYP-FX3-CARRY-FUNDPROXY-MONTHU-HARVEST-001`: N=278 PF=1.22 tpw=1.0663 x1.5=1.1528 → KILLED_AT_OFFLINE_PROBE
  - `HYP-FX3-CARRY-FLUSH-MR-MULTIDAY-001`: N=129 PF=0.8577 tpw=0.4948 x1.5=0.805 → KILLED_AT_OFFLINE_PROBE
- Receipt `5FD7597B31B8EEA3…`
- Không densify ngưỡng carry/funding/flush từ board này.
- Next: Microstructure **blocked** (cost chưa research-grade). CME 6J = **INTAKE_KILL densify** (z-gate đã kill). G10 daily acquire session này **BLOCKED**. Named next: **anti-carry × vol-spike** (≠ V8 calm-carry).
- Best shelf RR2 `194548`. Cost GAP. Login không phải headline. GOAL unmet.
