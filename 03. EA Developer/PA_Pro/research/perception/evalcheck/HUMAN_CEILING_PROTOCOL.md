# HUMAN_CEILING_PROTOCOL — draft (R34 §34.6), EVAL-AUDIT C-round 1

One page. Purpose: measure how far two humans agree when they draw the
same chart — that agreement is the ceiling any engine fidelity number
can mean. Absolute end thresholds are proposed no higher than it.

## Panels (~10, stratified from TUNE 198)

Drawn by a seeded sampler (seed logged), stratified on:

- **Session**: 4 EU, 3 US, 3 Asia (mirrors the book's mix).
- **Golden density**: 5 panels with <= 2 goldens, 5 with >= 4 — so the
  ceiling covers sparse and busy panels alike.
- **Family mix**: every chosen panel carries goldens from >= 2 of
  box/level/line, so all three M1 families are scored.

Panel ids are drawn after the Owner agrees; the list and seed go in
VERIFY_LOG before the session.

## The drawing sheet

- One sheet per panel: real M5 candles, EMA25, faint 00/50 grid — the
  same base render as the judge pack (`plausibility.render_item`
  base + `_render_v2` — never `render.py`, F5).
- **Bars stop at the panel's tau.** Nothing after the decision bar is
  shown; a dashed divider marks tau. What you see is all the evidence
  anyone had.
- No titles, no labels, no hints of what the book drew.

## Instructions (non-expert, ~30 min for 10 panels)

> Draw what you would want on your own chart for the bars shown: boxes
> around ranges, horizontal levels, trendlines. One colour for
> everything. Aim for the author's budget: about one box, one level,
> up to two lines per panel. There is no right answer — draw what you
> see.

Two independent drawers (Owner + one more, or Owner twice > 24 h
apart). No conferring.

## Scoring — same ruler, same budgets

- Drawer A's set plays golden, drawer B's plays engine:
  `eval_v2.match` at the ruler's own tolerances, objects ranked by the
  draw order (humans draw important things first).
- Report per-family recall@k at the author's budget (box@1, level@1,
  line@2) and the pooled M1-style number, each with a day-bootstrap CI.
- Swap A/B and average: the ceiling is the mean of both directions.

## What becomes the ceiling

- The pooled per-family recall@k numbers are the ceilings for the
  matching M1 families. P-FREEZE absolute thresholds are proposed at
  or below them (R34 §34.6).

## Prior evidence (context, not a threshold)

Osler (2000): six expert firms' published FX support/resistance levels
agreed only ~30% of the time pairwise (13–38%, ±5-point tolerance) —
`design/WEB_RESEARCH_C1.md`. Expect the ceiling well under 1.0; if the
drawers agree near .3–.5 that is a *human* result, not an engine
failure, and the end thresholds must be set inside it.
