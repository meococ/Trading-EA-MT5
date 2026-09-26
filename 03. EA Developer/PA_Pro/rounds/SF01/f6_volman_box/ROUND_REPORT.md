# SF01 / F6 — VOLMAN BOX BREAK with buildup — ROUND REPORT

**Verdict: DEAD.**  2026-09-21.

- Ledger prereg: v1 `T000159` (sha `4aa823b7`) -> v2 `T000185`
  (sha `44aafe84`; SPEC.md sha `cccbe52c` v1 wording + v2 header).
  v2 re-scaled `box_atr` {0.7,0.9} -> {2.5,4.0} — v1's threshold was
  calibrated to per-bar width, not 12-bar window height, and produced
  zero candidates (D11, pre-outcome).
- Detector: `families/f6_volman_box.py` v2 — compressed 12-bar box
  pressed against an armed zone edge; close through box AND zone edge;
  stop order 1 pip beyond the box edge (the correct Volman entry);
  inv at the far box side.
- Tests: 11/11 pass (incl. prefix invariance, future mutation, warm-up).
- Census v2: thin — best cell 4.7/wk (S24/line1/box4.0, 1,474 sig);
  sd_base cells all <300.
- Snapshots: 12 PNGs, textbook box-break geometry verified.
- Screen: `SCREEN.json` — 20/20 configs.

## Headline screen stats (top 5 by PF_x1)

| cell | N | PF_x1 | PF_x2 | t | lift_pp | lift CI | yrs+ | syms+ |
|---|---|---|---|---|---|---|---|---|
| S14/sd_base/2.5 | 32 | 1.839 | 1.258 | 1.51 | +17.4 | [-0.5, 34.2] | 4/6 | 3/4 |
| S14/sd_base/4.0 | 77 | 1.368 | 1.065 | 1.22 | +14.6 | [+3.1, 26.1] | 4/6 | 3/4 |
| S32/line1/2.5 | 81 | 1.328 | 1.289 | 1.11 | +2.2 | [-8.9, 13.5] | 4/6 | 4/4 |
| S24/sd_base/2.5 | 37 | 1.102 | 1.062 | 0.25 | +2.8 | [-12.6, 19.3] | 2/6 | 2/4 |
| S18/line1/2.5 | 343 | 1.077 | 0.936 | 0.60 | +3.4 | [-2.0, 8.9] | 4/6 | 2/4 |

## Gate analysis

- `S14/sd_base/box4.0` is the only cell in the whole factory whose
  lift CI clears zero (+14.6pp, [+3.1, +26.1]) — but N=77 trades in 6
  years fails N>=300 by ~4x. Unscreenable as declared.
- Thick cells are flat or negative: S18/line1/4.0 N=1549 PF 0.95;
  S24/line1/4.0 N=1446 PF 0.91; S32/line1/4.0 N=814 PF 0.88.
- Positive cells sit exclusively in the thin regime (N<100) — exactly
  where noise lives; the one thick-ish positive cell (S18/line1/2.5,
  N=343) has PF_x2 0.94 < 1.0 and lift CI [-2.0, 8.9].

## Diagnosis

The Volman box break at armed zones is a genuinely rare event under
causal rules (~1-5/wk basket), and where it is dense enough to test
(line1_cluster, wider boxes) it has no edge. The sd_base pocket shows
the only positive lift signal of the round, but at ~1 trade per month
it cannot be confirmed on DESIGN without loosening the definition
beyond recognition — and a v3 loosening (prox_atr 0.5->1.0, shorter B)
would at best triple N to ~230, still under the gate, while widening
the CI further.

## Disposition

1/2 logic revisions used (D11). Family closes DEAD; the sd_base
box-break hint is recorded for a future lane with a denser box
definition or a lower-N protocol — not for this round.
