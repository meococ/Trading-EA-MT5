# M2_PACK_PLAN — blind human-judged pack for any candidate hash
(R34 §34.4 M2; validity under R28–R31; EVAL-AUDIT draft, C-round 1)

## What the pack measures

- **Precision** = yes / all answers on engine items ("can't tell"
  counts as not yes; report yes/(yes+no) beside it).
- **Sensitivity** on golden controls, **specificity** on valid
  negatives — each with a CI (R33 §33.4).

## Item construction (from any candidate hash)

1. Run the candidate (cache or live) on TUNE; at each panel's tau take
   the per-family top-k under the author's budget — exactly the
   objects M1 counts (box@1, level@1, line@2 per tau).
2. Dedupe the same object drawn at several taus (object id); one PNG
   per surviving object, rendered at its own tau.
3. Golden controls: real golden items sampled as in `owner_pack.py`.
4. Negatives: audited decoys from `_plaus_neg.jsonl` (the same pool the
   20-item pack used).

## Validity rules (identical to the 20-item pack)

- One tau rule per class — `plausibility.tau_item` on the drawn
  object's own times for every source (kills the "tau inside box =
  golden" tell).
- One colour for all classes; no titles or metadata bands
  (`blind=True` strips the band).
- Audited negatives drawn from the negative manifest, same verdict mix
  as the judge measured.
- No answer key in the rendered pages; truth stays in
  `_owner_judge_key/_key.json`, outside the pack.
- Degenerate items (invisible render, R25 §25.3.2) swapped for a
  same-class replacement before packing.
- Render path: `plausibility.render_item` → `_render_v2` — the proven
  price-space path. Never `render.py` (F5).

## Sample size (precision CI half-width <= .15)

Binomial worst case p = .5: half-width ≈ 1.96·sqrt(.25/n).

- n = 43 engine items → .149; **n = 48 → .141** (recommended floor).
- n = 67 → .120 if the Owner tolerates a second sitting.

Pack composition at n = 48 engine items (mirroring the 20-item mix):
48 engine + 30 golden controls + 24 negatives = **102 items**
(~35–45 min). Controls/negatives stay large enough for usable
sensitivity/specificity CIs (~.15–.18 half-widths).

Shuffle with a fixed seed; log the seed, the hash, the per-panel tau
list and the mix in VERIFY_LOG when a pack is built.
