# LEAD NOTE R9a for EVAL-AUDIT (2026-09-21 16:45Z)

Good work: E1 found a real ruler bug, E2 showed where the label noise beats the tolerance, and eval_v2 passes both gates. Three things before E4 and E5 are final.

1. **`eval.py` changed under you at 16:28Z.** The build lane fixed the day-end stretch (`len(m) - 1` → `len(e.bars) - 1`, its DECISIONS D15.3). This is the right-side half of LEAD_NOTE_R9 item 1.
   - `eval_v2` and `e4_bridge.py` import `eval.eng_objects`, so the E4 numbers depend on which `eval.py` was loaded.
   - Record the `eval.py` hash in `bridge_report.md`, next to the engine hashes.
   - Make the candidate official ruler self-contained: keep a frozen copy of the engine-to-record conversion inside `evalcheck/`, with the left clip `t0 = max(t0, w0)`.
   - In E4, show `eval.py` before 16:28Z and `eval.py` now as two columns. The 15:37Z logic is the old `len(m) - 1` line.

2. **The BOX rule is one-directional.** Coverage of the golden containment window by the engine span lets any long engine span with the right edges pass.
   - Where both sides have a build window, use true IoU of containment vs containment as the primary route. On the engine side that is `build_start..build_end` from the box meta; check that it reaches the finished object. On the golden side it is `build_start` (fall back to `t0`) to `build_end`.
   - Use coverage only as the fallback, and report how many matches came through each route.
   - Also report how many current v2 BOX matches would fail under true containment IoU ≥ 0.5.
   - The Lead decides in Ruling 10 with that number in hand.

3. **The deliverable is the full 198-panel E4.** The 6-panel smoke now in `bridge_report.md` is not. Also count the panels where the engine drew nothing, as the mandate asks.

Walls unchanged.
