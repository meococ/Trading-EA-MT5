# FRONTIER — the box trade-off, for the Owner (BOX-LAB, R63 §63.5)

One page. What we found, what it costs, and the choice only you can make.

## What the event routes are

v0 does not scan for "a box". It waits for a market *event* — a
confirmed swing pivot — and asks one of two questions:

- **`range_double_*`**: "did price just print a second pivot at the
  same level as an earlier one?" If yes, that repeated level is one
  edge; the extreme printed between the two pivots is the other. The
  box's left edge is the earlier pivot's bar — the box is born already
  spanning the whole congestion, like the author's.
- **`pullback_end`**: "did price just finish a pullback into the last
  opposite pivot?" If yes, the two pivots are the edges.

Both run on every confirmed pivot. We ported them verbatim onto v1's
SwingBook and they reach **12 of 15** event-route goldens — the same
boxes v0 catches, at v0's coverage (BOX recall .213), and they cured
the seven fixtures that were failing. The *generation* problem — right
box, right place, right time — is solved by these routes.

## Why the births cost ink

v1's pivot stream is much finer than v0's: it confirms every micro
swing, so the routes fire ~6.5 times per panel. The ruler charges
clutter for **every object whose span touches the evaluation window —
dead ones included**. Six or seven small overlapping boxes per panel =
clutter 5.67–6.00 against a 5.0 cap, while the budget only allows
about one extra object. The author draws one box per panel.

So the port wins on coverage and loses on ink. The fix had to be a
*throttle*: birth fewer event boxes but keep the right ones.

## The throttle matrix (all measured on the cache, nothing kept)

| throttle | births/panel | of the 15 reachable goldens kept |
|---|---|---|
| raw stream (no throttle) | 6.5 | 12 |
| one object, edges update in place (best) | 1 | 5 |
| defer birth, pick most-touched | 2 | 2 |
| one birth per episode, release X ABR | 5.5 → 1.8 | 1 |
| dedup new structures, D = 5/8/12 pips | 13 / 9 / 6 | 11 / 8 / 6 |
| coarse pivots only (v0-stream proxy) | 1–8 | 0–5 |

Dedup at 5 pips keeps 11 goldens but still births 13 per panel. Every
gate tight enough to satisfy the ink cap throws the right box out.

## Why no causal rule can pick the right box

We measured the candidates that *do* match the author's box against
the rest of the stream. They are statistically identical on every
feature available at the time of the decision:

- prior-leg size: median 8.8 pips — same as the stream's 8.8
- pivot prominence: 10.5 vs 10.5; pair spacing: 11 vs 8 bars
- edge re-touch count: 2 vs 2
- birth position: mid-stream — never first, rarely last
- no quiet gaps exist to segment "episodes"

v0 only ever looked right because its supersede chain kept *replacing*
the box all episode long — roughly six objects per panel, the last one
standing at evaluation happened to be right. That coverage is bought
with ink. There is no cheap version of it: at ~2 births per panel the
right candidate is indistinguishable from ~47 wrong ones.

## The choice (§63.2 — three options, priced by EVAL-AUDIT)

- **(A) Accept the gap.** Ship box 10/119 vs v0's 16. Level, line,
  clutter all pass. Cheapest, keeps today's economy.
- **(B) Raise the clutter cap.** Keep the full port unchanged: box
  16/119 (=v0), clutter 5.67 → passes only if the cap rises to ≥5.7.
  One flag carries v0's whole box family.
- **(C) Count clutter at τ.** Charge only objects live at evaluation —
  what is on the screen when the decision is made. No official number
  yet; EVAL-AUDIT is pricing it for parent, hybrid, and the port arms.
  BOX-LAB's cache estimate for T1: one event object per panel, always
  the live one → live-at-τ ≈ parent's ~1 + 1 ≈ **2 objects** (vs ~6.5
  under today's dead-included count for the raw port; under C the raw
  port's live-at-τ is expected near 1–2 if superseded objects die).

## Bottom line

Generation is solved. What is left is a policy question, not an
engineering one: the right box cannot be identified before hindsight,
so its coverage costs either ink on the ruler (B), a different
definition of clutter (C), or recall (A). All three numbers are now
measured and on the table.
