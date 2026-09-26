# ROUND L3 — session-extreme dedup

Config: L1 + session/Asia origins marked `sess`; when a running extreme
is superseded, drop it immediately if it has < min_defences. NMS band
2.5→3.0 p; revive window 48→96 bars.

| ruler | LC recall | LC prec | LC trusted | MINI recall |
|---|---|---|---|---|
| eval.py | 0.458 | 0.029 | 0.550 | 0.469 |
| eval_v2 | 0.479 | 0.031 | 0.575 | 0.548 |

Oracle LC 0.771, MINI 0.742. Snapshot LC 0.362, live med 4.0.
Ink: LC 4 + MINI 3 = ~7/panel (from ~9).

Lesson: immediate supersede-drop is too fast — a superseded extreme can
still be defended LATER (price comes back to the old high after the
session moved on). Dropping at supersede-time removes origins that
would qualify hours later → recall −0.125 for −2 ink. The fix is a
grace period, not instant removal.
