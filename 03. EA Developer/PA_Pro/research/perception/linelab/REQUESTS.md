# REQUESTS — LINE-LAB to Lead / build lane

Requests for changes in files LINE-LAB does not own. Each item has the
measured basis; the Lead rules, the build lane implements.

## REQ-1 — line birth rate is the dominant right-proposal killer (L6, 2026-09-21)

Measured on labels_v1_694313a38abc2da6.jsonl (198 TUNE panels,
eval_v2 `50e11fd5`):

- PATTERN_LINE candidates proposed: 3,492
- Right proposals (R11 prefix-consistent `cand_right`, label != null): **125**
- Of those 125, outcomes at end of panel:

| outcome | n |
|---|---|
| rate_limited | **70** |
| expired (TTL while pooled) | 34 |
| born | 11 |
| outranked | 8 |
| nms_suppressed | 2 |

Salience refused or starved 112/125 right line proposals; only 11 were
born.  `rate_pattern_line = 2` per `rate_window_bars = 72` plus
`rate_total = 5` (all families share it) is the binding constraint —
junk bars earlier in the window spend the slots the line needs at the
moment it actually forms.

The lab showed the same line grammar at 0.13–0.16 v2 recall without
the cap; in the full engine born recall is 0.109.  The delta is almost
entirely this gate, not geometry.

**Request:** for the `line` family, either
- raise `rate_pattern_line` to 3 and/or exempt `revive`-class
  re-proposals from the rate counter (a revived line is the same
  structure, not new evidence — it should not spend a birth slot), or
- charge `rate_total` against *net new ink* (exclude candidates that
  revive a closed same-geometry object, since lines.py already handles
  the revive in-line).

LINE-LAB can implement whichever variant the Lead picks if it stays
inside `lines.py` + line params; if the change is in `salience.py`
(rate accounting) the build lane owns it.

## REQ-2 — candidate TTL vs slow-burn lines (observation, no change yet)

34/125 right proposals died of `expired` (cand_ttl_bars).  Lines often
need a third touch tens of bars after the second; if the ttl is short
the right proposal expires before it can win a slot.  No parameter
request yet — REQ-1 may absorb most of this; revisit after the Lead
rules on REQ-1.
