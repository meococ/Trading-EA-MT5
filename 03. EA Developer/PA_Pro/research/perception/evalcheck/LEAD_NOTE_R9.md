# LEAD NOTE R9 for EVAL-AUDIT (2026-09-21 16:32Z) - read before E3/E4

Full text: `research/perception/LEAD_RULINGS.md`, Ruling 9. Two items are for you.

**1. A ruler bug that E1 cannot see.** `eval.py` `eng_objects` sets `t1` for an ACTIVE engine object (`t_right is None`) to `len(m) - 1`, the last bar of the whole day. The engine was only fed bars up to `w1`, and golden open spans end at `w1`.
- The left side has the same asymmetry: engine `t0 < w0` is not clipped, but golden partial spans are.
- So any object still alive at the panel edge loses its time match.
- The self-test (golden in, golden out) cannot catch this, because golden objects never pass through `eng_objects`.

Your tasks:
- In `eval_v2`, clip engine spans to the panel window `[w0, w1]` on both sides.
- Add known-answer tests:
  - (a) engine box = golden box, ACTIVE at `w1` → must match;
  - (b) the same box closed at the golden `t1` → must match;
  - (c) the same box stretched to 23:55 → the old `eval.py` conversion fails it (show this).
- The build lane is applying the same one-line clip to `eval.py` now (DECISIONS: "ruler fix R9.1"). In E4, show `eval.py` both before and after R9.1.

**2. `iou()` in `eval.py` is intersection / max(length), not IoU.** It is always ≥ true IoU. Spec §6.1 says IoU.
- Use true IoU (intersection / union) in `eval_v2`.
- Report both definitions in E4.

**Data you can use for the D9 containment window:**
- Golden BOX has `build_end` on 108 of 116 objects and `build_start` on only 47 of 116. Fall back to `t0` when `build_start` is missing, and document the fallback.
- The engine's box candidates carry `build_start` / `build_end` in their `meta` (boxes.py:195 and :372–373), and a broken box sets `geometry["break_bar"]` (boxes.py:414). Check how these reach the finished object before relying on them.

Walls unchanged: write only under `evalcheck/`, TUNE v2 only, HOLD never read.
