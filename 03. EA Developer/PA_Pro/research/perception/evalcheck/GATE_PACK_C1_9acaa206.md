# GATE_PACK_C1 — C-round-1 freeze pack (EVAL-AUDIT)

Generated 2026-09-22 10:59Z by EVAL-AUDIT's own scorer (m1_row.py), TUNE 198 panels, ruler `50e11fd5a2ab7974`.

Candidate: `9acaa206c8d386dc` variant=`m1_v1` (C-ROUND-1 STABLE (frozen))

## M1 — per-family recall at the author's budget

| arm | box@1 | level@1 | line@2 | bracket@1 † |
|---|---|---|---|---|
| v0 `63c771d6` | 0.134 (16/119) | 0.066 (5/76) | 0.093 (18/193) | 0.388 (33/85) |
| candidate | 0.076 (9/119) -0.069 [-0.142..-0.003] | 0.079 (6/76) +0.039 [-0.033..+0.117] | 0.104 (20/193) +0.015 [-0.040..+0.070] | 0.341 (29/85) -0.015 [-0.172..+0.134] |

† bracket@1 reported, not part of M1 (no price check, R30 §30.3). CIs are paired day-bootstrap of (arm − v0), seed 20260921, 1000 resamples.

## Clutter + diagnostics (candidate)

- clutter ratio median (eng/gold per panel): **5.00** (v0 9.00); 90/179 scored panels ≤ 5.0
- BOX recall 0.111 | BOX precision 0.044 | PATTERN_LINE recall 0.114 | LEVEL_CARRIED recall 0.188 | LABEL_TF agreement 0/1 | clutter ratio med 5.00

## Keep verdicts (EVAL-AUDIT independent, own scorer)

- K1 line.lab_score @afba83c5: CONFIRMED (+2 line hits, OFF-id 1728/1728 vs STABLE parent)
- K2 defended_origin+def_mini_off @e62f2dc9: CONFIRMED (+2 level, −1/−1 allowed, OFF-id 1728/1728 cross-hash)
- K3 bxcombo @dd96c5fe: CONFIRMED (+1 box, +2 line, clutter 5.00, OFF-id 1728/1728 cross-hash)
- K4 box_score_pick arm A @cfb862d4: CONFIRMED (+4 box, OFF-id 1728/1728); arm B rejection CONFIRMED (−2 box)
- K5 line.slope_floor=0.25 @75a9650c: CONFIRMED (+1 line, clutter 5.00 thin margin 90/179, OFF-id 1728/1728)
- K6 box.cong_trigger k5.5/N6 @df79ade3: CONFIRMED (+2 box 9.4b+9.48b miss→hit, zero losses, clutter 5.00, OFF-id 1728/1728 post-§45.2 fix, suite 65/72 same-7). §46.1 noise note: +2/119 is within noise — the claim is that the mechanism is real (fresh congestion boxes outrank stale envelopes at τ), not that box fidelity improved significantly. Robustness: k 4.0–5.5 and N 6–8 hold the +2; k 3.0 loses it.
- box_prio (§42.4, 4 forms): all FAIL keep-rule on own scorer — v1 cd14f5fc lvl −3 cl 6.33; v2 cd00d0be box +1 lvl −4 cl 6.00 (+OFF-id broken: 3 obj + 1107 cand_log diffs); v3 afe99034 box +2 lvl −2 cl 6.33; v4 box_tau_prio c14060cb box −3 cl 5.00. Suite on v2-ON config 72/72 (fixes the 7 fixtures) but M1 cost stands — correctly rejected.
- fam_context (§44.2, 2 forms): FAIL — plain @88438120 lvl −2 cl 5.67 box flat; +ctxbirths-off @4dcc44d7 box +1 lvl −2 line −2 cl 5.67. Suite 72/72 both but M1 cost stands.
- joint_struct v2 (§43.4.2, structure-only): FAIL both caps @69cda24a — cap4 lvl −4/line −4 cl 5.33; cap3 lvl −3/line −4/brk −7 cl 5.33. famctx+jstruct (§45.3.2): FAIL both caps @df79ade3 — cap4 .076/.026/.083 brk −9 cl 5.67 (suite 72/72); cap3 .076/.066/.088 brk −15 cl 5.67 (suite 71/72).
- §42.5 choice rows (own scorer): kept (K1–K5 pre-K6) .059/.079/.104 cl 5.00; famoff_on .067/.053/.067 cl 5.67 (line below v0); famoff_nosup .042/.053/.073 cl 5.00 — kept config is M1-best; §45.4 froze the choice to K1–K6.
- Suite leg (R42 §42.3, unmodified fixtures, each keep's own config): K1 72/72, K2 72/72, K3 65/72, K4 65/72, K5 65/72, K6 65/72 — the same 7 theory fixtures fail once fam_budget+fam_caps hold (CONTEXT_RANGE occupies the box-family slot); box_prio ON or fam flags OFF each restore 72/72.

## Known spec violation carried into the freeze (R45 §45.4)

- Under `fam_budget`, a CONTEXT_RANGE can hold the box family's single live slot, so the book's BOX is not drawn in the textbook patterns of Fig 3.1, 3.8 and 3.9. The frozen suite runs unmodified: 65/72, with the seven named fixtures failing (pullback-end box birth, double-top box, false-break wick, break-close, tease-vs-proper, TF relabel, re-anchor double-top).
- Every suite-curing arm measured this round costs M1 (box_prio 4 forms, fam_context 2 forms, famoff 2 forms); none passes §34.5/§41.3. This defect is first on the next round's list (fam_context + structure-only cap).

## Tested and rejected this round (EVAL-AUDIT own scorer)

| arm | hash | box@1 | level@1 | line@2 | clutter | why |
|---|---|---|---|---|---|---|
| level_touch_rec | 22888182 | .025 | .013 | .088 | 5.00 | level −5 |
| line_dedup_merge | 22888182 | .025 | .079 | .098 | 5.00 | zero-delta |
| box_score_pick_prio (arm B) | cfb862d4 | .042 | .092 | .098 | 5.00 | box −2 vs arm A |
| fam_total_live=4/3/2 | 10c34e28/fbb3a173 | .050/.042/.042 | .026/.066/.026 | .057/.062/.057 | 3.00/2.33/1.50 | cap counts transient annots; M1 losses |
| famcap_bracket=2 | 10c34e28 | .059 | .079 | .098 | 5.00 | bracket −1, no gain |
| line.steep_pick | 75a9650c | .059 | .079 | .088 | 5.00 | line −2 |
| box_prio v1 birth-path | cd14f5fc | .059 | .039 | .098 | 6.33 | level −3, clutter |
| box_prio v2 +τ-rank | cd00d0be | .067 | .026 | .098 | 6.00 | level −4, clutter, OFF-id leak |
| box_prio v3 RO-excl | afe99034 | .076 | .053 | .098 | 6.33 | level −2, clutter |
| box_tau_prio | c14060cb | .034 | .079 | .104 | 5.00 | box −3 target down |
| famoff (§42.5 row) | a7f35026/e1edc511 | .067 | .053 | .067 | 5.67 | level+line below v0, clutter |
| famoff_nosup (§42.5 row) | e1edc511 | .042 | .053 | .073 | 5.00 | worse than kept on box+line |
| fam_context | 88438120 | .059 | .053 | .098 | 5.67 | level −2, clutter (suite 72/72) |
| famctx + CR births off | 4dcc44d7 | .067 | .053 | .093 | 5.67 | level −2, line −2, clutter |
| joint_struct cap4/cap3 | 69cda24a | .059/.059 | .026/.039 | .083/.083 | 5.33/5.33 | cap churn burns levels/lines |
| famctx+jstruct cap4/cap3 | df79ade3 | .076/.076 | .026/.066 | .083/.088 | 5.67/5.67 | churn; cap3 also breaks pierce fixture (71/72) |
| box.level_edges | 9d76b883/e1edc511 | .059/.050 | .079/.079 | .104/.104 | 5.00/5.00 | zero-delta / −1 |
| cong_density (peaks) | 0a100806 | .076 | .079 | .104 | 5.00 | inert — 0 dens births, same winners |
| cong_density q-mode | 13b3f53d | .059 | .092 | .104 | 5.00 | box −2 vs K6 (trims the edges that matched) |
| cong_subband | 5928a0e2 | .076 | .079 | .104 | 5.33 | flat box, clutter +0.33, 1123 cands 0 born |

## Leak ledger (R45 §45.2 / R46 §46.1, brief)

- The `_propose_window` narrowing + unconditional `congestion_scan` cand_log writes leaked into every hash between `cd00d0be` and `30486c39` inclusive. Object footprint: one `why` label flip (cluster_range→congestion_scan) on 2012-04-04 (panels 9.25a/b/c); cand_log diffs on ~1107 runs.
- Clean hashes: ≤ `cd14f5fc` and ≥ `df79ade3`. Every keep (K1–K6) was verified on clean code; every leaky-hash verdict is a FAIL or zero-delta whose margin (≥2 hits) exceeds the leak's footprint, and both arms shared it — rejections stand.

## Residual coverage — the no-edge class (R48 §48.1)

- 51 no-edge box goldens shrank to 38 under K6 (congestion proposals now carry matching edges for 13). BOX-LAB's causal census: a union of sources (10-pip rounds, pivots, buildup close extremes, 6h session hi/lo, prior-day hi/lo) reaches both edges of 27/38; 11 sit on no standard structure.
- **Null caveat (Lead's):** at 1.5–5 pip tolerance a 10-pip grid covers much of the price range by chance; R39 found the author's levels no rounder than chance (9% vs 8% null). Each source's share must be re-measured against a shuffled-edge null before building on it — next-round item (§48.3: old-structure edges inside qualified congestion runs, null-first).

## Status

**C-ROUND 1 FROZEN — STABLE `9acaa206c8d386dc`** (R48 §48.1; build logged STABLE 10:45Z).

- **Frozen config:** default engine = K1–K6 ON, exactly as verified. On-disk `code_hash` recomputes to `9acaa206c8d386dc`; 3-panel live spot check (9.1a/b/c) byte-identical to cached `m1_v1` runs. No K7 exists; `cong_density`/`cong_subband` probes rejected and are not in the freeze.
- **M1 vs v0:** box .076 (9/119) −.069 [−.142..−.003] — still below v0; level .079 (6/76) +.039 [−.033..+.117]; line .104 (20/193) +.015 [−.040..+.070]; bracket .341 (29/85) −.015 [−.172..+.134]. Level/line beat v0 on point estimate, CIs straddle 0.
- **Clutter:** median 5.00 vs v0 9.00; margin 90/179 panels ≤ 5.0 (one-panel margin).
- **Diagnostics:** BOX rec .111 prec .044 | PL .114 | LC .188 | LTF-agree 0/1 | clutter 5.00. (Build lane reports BOX prec .047 — the same object-set naming convention difference noted in VERIFY_LOG; recall and all other rows identical.)
- **Suite (frozen defaults, unmodified):** 65/72 — the seven named fam_budget fixtures fail (pullback-end box birth, range double-top, false-break wick, break-close, tease-vs-proper, TF relabel, re-anchor double-top); CONTEXT_RANGE holds the box-family live slot. Verified again on the restored snapshot this round-close.
- **Keeps:** K1–K6 all CONFIRMED on EVAL-AUDIT's own scorer with OFF≡parent identity; no keep rests on a leaky hash. K6's +2/119 box gain is within noise — mechanism real, magnitude not established.
- **Carried debt:** the seven-fixture spec violation, box 7 hits short of v0 (9 against 16 of 119; 38 no-edge, 27/38 reachable per census but null-unproven), one-panel clutter margin, F1 throughput collapse (991→32 bars/s — indexing/caching patch proposed for next round, identity-validated).
- **Next round (§48.3):** old-structure edges inside qualified congestion runs, measured against a shuffled-edge null first; fam_context + structure-only cap for the fixture debt; F1 performance patch.
