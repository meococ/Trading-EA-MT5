# GOLDEN_AUDIT — BOOK2012 → BOOK2012_v2

Ruling 2 Q1 output. The catalogue text is the spec; the validator checks
each drawn object against BOTH the text features and the real M1 bars
(`book_loader`, Berlin-wall clock, D3). Repair never overwrites catalogue
truth — `draft/BOOK2012_draft.jsonl` remains the record; v2 stores text
fields (`text_*`, `clause`) separately from derived geometry
(`price0/1`, `price_lo/hi`, `build_start`, `build_end`).

## Before: refined geometry vs text + bars (TUNE, 574 objects+marks)

| check | hard fails |
|---|---|
| HAS_GEOM | 154 |
| CONTAIN | 66 |
| EDGE_TOUCH_TOP | 46 |
| EDGE_TOUCH_BOT | 44 |
| SLOPE_TEXT | 43 |
| ANCHOR | 26 |
| PRICE_TEXT | 11 |
| SIDE_TOUCH | 10 |
| LEVEL_ANCHOR | 7 |
| BRACKET_SIDE | 2 |

**Pass: 261/574 = 45%.**

### The two structural findings (D8)

1. **Slope sign**: 37/77 slope-worded refined lines slope the wrong way
   (48%); 28 of them still had rms ≤ 2 px. Root cause: `drawn_ink`
   removes only the longest run per column, leaving wick/border residue,
   and `corridor_fit` least-squares all ink in a wide corridor — it fits
   the price path, not the drawn line. Low pixel residual proves nothing.
2. **Catalogue overwrite**: refinement replaced text prices in place;
   the draft is the only surviving truth.

### The box-semantics finding (D9)

Drawn right edge ≠ containment end. Stated height matches the PRE-BREAK
range in every measured case. A box is born when two barriers have
company (≥2 touches within tol); it lives while closes stay inside; it
dies at the first decisive close beyond an edge. Lone spikes are pokes,
not barriers — unless the text names the edge ("bottom = the 10:25
spike low"). CONTAIN is judged on the buildup window
[build_start, build_end], closes only; wick pokes that close back inside
are teases.

## After: BOOK2012_v2 (frozen, Ruling 4)

Frozen yardstick code (sha256, first 16):

| file | sha256 |
|---|---|
| `golden/textfeat.py` | `ada60dd1d1673ee1` |
| `golden/validate.py`  | `2224ea3b15750388` |
| `golden/repair.py`    | `df56cecd5ccc4a3d` |

**Independence (Ruling 4d):** none of the three imports `engine.py` or
shares its swing/pivot code; the yardstick is independent of what it
measures. Repair consumes the catalogue draft, the refined overlay and
`book_loader` bars only.

### TUNE object status (527 objects)

| type | ok | repaired | time_only | unusable |
|---|---|---|---|---|
| BAR_MARKER | 4 | 0 | 0 | 0 |
| BOX | 63 | 48 | 0 | 5 |
| BRACKET | 78 | 7 | 0 | 2 |
| CONTEXT_LINE | 0 | 8 | 1 | 0 |
| CONTEXT_RANGE | 4 | 2 | 0 | 0 |
| LEVEL_CARRIED | 20 | 27 | 1 | 0 |
| MINI_LEVEL | 4 | 27 | 1 | 0 |
| PATTERN_LINE | 0 | 184 | 2 | 12 |
| RANGE_OPEN | 4 | 4 | 0 | 0 |
| SQUEEZE | 2 | 0 | 0 | 0 |
| (fragment, no spec_type) | — | — | — | 17 |

**Usable = ok + repaired = 486/527 = 92.2%** (486/510 = 95.3% excluding
fragments; +5 time_only = scored on time/type only).
Strict re-validation of v2 (objects + marks, 590 results): **87.8% pass**.
Residual hard fails on kept objects: EDGE_TOUCH_TOP 25,
EDGE_TOUCH_BOT 20 (author eyeball prices sit 1–3 pips off exact extremes
— kept deliberately, text is authoritative), LEVEL_ANCHOR 7,
HAS_GEOM 28 (mostly unusable/fragment objects by construction),
CONTAIN 2, SLOPE_TEXT 1.

### HOLD (blind — counts only, never tuned)

Same frozen code, same parameters. 614 objects: ok 192, repaired 318,
time_only 10, unusable 47, fragment 47 → **usable 510/614 = 83.1%**
(89.9% excluding fragments). Strict validation: 85.5% pass.
Ledger: T000366 (frozen yardstick; supersedes T000363/T000365, split ref
T000361/T000362). **HOLD v2 is now frozen — no code runs on it again
until the Lead's scoring go.**

The 9-point TUNE/HOLD usable gap is composition, not tuning: HOLD has
47 catalogue fragments vs 17 in TUNE (the later catalogue pages carry
more partial notes), and more out-of-window/underspecified objects land
as `unusable` there. Type-level strict pass is actually higher on HOLD
for LEVEL_CARRIED (94% vs 85%) and comparable for BRACKET.

### Repair provenance (TUNE)

| method | n | meaning |
|---|---|---|
| none | 106 | kept refined geometry (validated clean) |
| text_price | 90 | author prices authoritative as-is |
| constrained_fit | 124+1f | bar-extreme pair fit under text slope bounds |
| text_anchor_bars | 98+1f | line through the bar the text names |
| edge_from_bars | 76+3f | box edges = clustered extremes, pokes excluded |
| edge_from_bars+subwindow | 3+1f | bounds only the contained run inside a loose span |
| sibling_span | 6 | object inherits a named sibling formation |
| time_only | 5 | times known, no responsible price recoverable |
| unusable | 14 | genuinely under-specified catalogue fragments |

`+fail` suffix = method ran but a hard check still fails → status
`unusable`. Ink was used only to confirm or break ties; it never sets a
slope sign against the text.

### What remains unusable (TUNE, 19 + 17 fragments)

Honest catalogue gaps, not hidden failures: compound notes split across
objects ("its bottom edge is broken where a bar dips"), callouts
("[stay out]"), objects drawn past the axis edge ("small box after
~11:05" on a panel ending 11:00), and notes with no drawable spec at all
("only a tiny carried line"). Each carries `status=unusable` and its
fail codes.

## Semantic rules discovered (feed the design notes)

- **SLOPE_TEXT**: sign + magnitude bounds per vocabulary word
  ("nearly flat" ±10p over span; "steep" ≥8p; arrows `tl↗/tl↘` count).
- **Side**: "under the lows"/"over the highs" → ≥2 touches within 1.5p
  on that extreme + bounded closes beyond.
- **Anchors**: "from the ~15:45 high" → line within ~2p of that bar's
  extreme, ±2 bars.
- **Compound notes**: clauses are split and attributed per object
  (time/price/dir match, then ordinal).
- **Round refs**: "under the 1.30" pins the lid at 1.3000; "straddling
  1.26" constrains the figure to lie INSIDE the box (not centred) —
  a fixed-height window is slid over candidate edges subject to
  lo < 1.2600 < hi.
- **Shared ends**: "both to ~11:55" / "to ~17:35" — a trailing clause
  time is the drawn end of the object even past its source span.
- **Sibling references**: "projected from that congestion top" resolves
  to the sibling object's stated price.
- **Endpoint-bound anchors**: in a compound note, an anchor only binds
  the object whose own t0/t1 it sits on (each triangle leg owns its
  start bar).
- **Broken/pierced/teased lines**: required to hold only to the break —
  fitted on the pre-break prefix, drawn span unchanged.
- **Levels**: text price wins; else named-bar extreme; else own-span
  extreme — the most extreme print WITH company (≥2 bars within tol);
  a lone spike is a poke, not the ceiling ("small ceiling" → the
  cluster top, not the breakout high).

## Limitations

- `flat` tolerance (±10p) and touch tolerance (1.5p) are validator
  conventions; spot-check judges whether they are fair.
- `text_price` boxes keep eyeball prices — EDGE_TOUCH fails there are
  known author-rounding artifacts, not hidden.
- Marks (LABEL_TF) are validated structurally only (right side, right
  span); a T/F's pip depth is not yet semantically checked.
- HOLD was run once, blind, after the code froze on TUNE. No HOLD
  object was individually inspected.

## Independent spot check

`qa/SPOTCHECK.md` (round 1): 45 TUNE objects, judged by an agent that
did not write `validate.py`, against text + bars only — **39/44
determinable = 88.6%**, below the ≥90% gate. Its five mismatches were
real and each traced to a repair defect, now fixed:

| object | defect | fix |
|---|---|---|
| 9.63a BOX | "straddling 1.26" read as centred → 7.5p box below the figure | figure-inside fixed-height edge search → [1.25874, 1.26004] = 13.0p straddling 1.26 |
| 9.33b#1 PATTERN_LINE | clause anchor filter absent → sibling leg's anchor hijacked the end; drawn 08:35→09:30 vs "both to ~11:55" | endpoint-bound anchors + shared-end time → drawn 08:35→11:55, rising off the 08:35 spike low |
| 9.5c#1 LEVEL_CARRIED | "projected from that congestion top" fit a rally high 30p away | sibling-price resolution → 1.3137 = the stated congestion top |
| 9.23c#0 LEVEL_CARRIED | carry end "to ~17:35" dropped by clause split | trailing `to ~HH:MM` re-attached → span 14:01–17:35 |
| 9.15b#2 MINI_LEVEL | "small ceiling" priced at the span low | company-rule edge (lone spike = poke) → 1.32277 ceiling cluster |

Round 2 (`qa/SPOTCHECK_R2.md`): an independent re-verification of the
same 45 objects against the rebuilt v2 — **43/44 determinable =
97.7%, gate ≥90% PASSED**. (Two independent checker agents converged
on the identical score and the identical residual; the on-disk report
is the second agent's, with fresh per-bar probe evidence in
`qa/_r2_spotcheck_out.txt` and `qa/_r2_probe.py`.) Four of the five
R1 defects verified fixed (9.63a, 9.33b, 9.15b, 9.23c). Residual:
9.5c LEVEL_CARRIED has the correct price (1.3137) but its span still
starts at the stated carry end (drawn 17:00–18:00 vs "to ~17:00";
the level genuinely capped 15:10–17:00) — recorded in the R2 report;
not fixed because the yardstick froze before the verdict landed. One
further cross-check: 9.63a's edge touches/containment were recomputed
independently on the M5 bars — drawn-span touches top=2/bot=22,
buildup containment 100% (46 bars), straddle of 1.2600 confirmed.
