# Logic-to-code matrix — HYP-CBC-XAUUSD-M15-001

| Frozen rule | MQL5 authority |
|---|---|
| Completed M15 decision bars only | `CopyRates(..., PERIOD_M15, 1, ...)` and `CopyBuffer(..., 1, ...)` |
| Box excludes break bar | `DetectCompression`: indices 1..7 in the shift-1 array = terminal shifts 2..8; `EvaluateBreak`: index 0 = shift 1 |
| Frozen 9-bar state | `g_box_*`, `g_box_age`, `STATE_COMPRESSION`; no box recompute until break/expiry |
| Next-bar execution | decision time must be exactly one M15 behind `availability_time` |
| Structural clamped stop | `SubmitEntry`: box edge plus 0.20 ATR then 1.30..2.60 ATR clamp |
| No fixed TP; convex runner | `PositionOpen(..., sl, 0.0, ...)`, BE+ and closed-bar ATR trail |
| Three independent volume caps | risk, notional and margin candidates; normalized minimum plus post-normalization assertions |
| Loss/cooldown guards | equity day/week anchors plus `OnTradeTransaction` four-loss streak |
| Native data proof | `EmitSeriesProof` canonical D0 M5/M1 keys |
