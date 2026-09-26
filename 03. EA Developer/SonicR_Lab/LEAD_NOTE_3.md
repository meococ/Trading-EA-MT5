# LEAD NOTE 3 - zone "birth" has two meanings; keep them separate (Lead, 23/09 16:36Z)

Your log: "keep birth = earliest member idx". That is fine ONLY for the death check. Split the two fields:

- `avail_idx` (when the zone may be USED by any decision) = the confirmation bar of the swing that completes the
  cluster (the 2nd member's confirmation bar, i.e. its pivot bar + the detector's confirmation lag). A zone must
  never gate, target or stop anything on a decision bar t < avail_idx. This is the causal rule.
- `origin_idx` (earliest member pivot bar) may be used as the START of the death-check window: if price closed
  through the zone by > 0.5 x ATR14 between the members, the zone is already dead when it becomes available.
  That is stricter and still causal, because the check only looks at bars <= avail_idx at availability time.
- Add a unit test: a zone whose 2nd member is confirmed at bar k is invisible to `zones_at(t)` for every t < k and
  visible at t >= k (unless dead). Put the test name in LAB_LOG.md. The neutral reviewer must check this one.
- Same rule for WHQ zones (always available) and for any swing-based SL/TP anchor (available only after
  confirmation).

Also, from LEAD NOTE 2 (please confirm you read it): parity = PF +/-0.15 plus 10 hand-checked F0_J trades, and the
trade-list export must carry ticket-level fields for the round-3 MT5 parity. And from PREREG section 3: report
clean-only PF next to all-trades PF - F0_J had 401/1441 exits on suspect M1 bars, which may be fake spikes.

## ADDENDUM (Lead, 23/09 16:52Z) - Lead read src/components/zones.py; behaviour is already causal
`SwingZones.zones_at(t)` clusters only swings with conf <= t, so a zone first appears at the 2nd member's
confirmation bar, and `birth = min(member idx)` is used only as the start of the death window (bars <= t).
That is exactly the rule above. So: do NOT change zone behaviour and do NOT rerun the census for this note.
Only these no-behaviour-change items, before the final report:
1. Fix the stale module docstring ("birth = the confirmation bar of the LAST member") to describe the code.
2. Add fields to each zone dict: `avail_idx = max(member conf)`, `origin_idx = min(member idx)` (for audit and
   the round-3 trade list), and the unit test from point 3 above (name it in LAB_LOG.md).
3. Tie case: a 2-member cluster of one high + one low (sum(dir) == 0) is labelled support (-1). Keep it in
   this round, but count such zones in the census and state the count in RESULTS.md (a flip zone is a
   round-3 design question, not a mid-round change).
