# M2-TV plan — the Owner's blind precision on a trade-view pack

Ruling 79 §79.2, amended by Ruling 82 §82.5.  Drafted by EVAL-AUDIT;
Lead approves before any rendering.  Engine under test: **named in
R83** (only verified candidates eligible).  Dry-run placeholder per
§82.5(4): **C-3 @fa2e52e5 + `trade_tags=1`**.

## 1. What "tradeable" means (R82 §82.5.1)

An object is **tradeable** iff it carries **no tag in
`trade_tags.TRADE_VIEW_HIDE`** at the item's decision τ.  The constant
is **imported, never copied** as a list.

- `lone_edge` does **not** disqualify (fact only, R81 §81.5(1)).
- `line_broken`, `line_cuts_bodies`, `stale_far` **do** disqualify,
  together with `daylight`, `steep`, `shock_inside`,
  `impulse_inside`, `zombie`, `superseded`.
- The rule is **identical for engine, golden and negative** items;
  negatives are re-tagged after mutation (the mutation itself is the
  negativity; a mutation that leaves no hide-tag is still a negative).
- §82.4 consequence: golden lines tagged `line_broken` are
  ineligible for the golden pool (eligible lines = 73/193;
  reported to the Lead 13:05Z via PERCEPTION_LOG).

Tags are computed from bars ≤ τ only (TT predicates in
`trade_tags.py`, single-sourced with DR_RULES_measure).  For golden
items the same tag functions are applied to the golden object's
geometry at its τ — identical semantics for every class (the pack
stays blind).

## 2. Composition — 50 items

| class | n | source |
|---|---|---|
| engine | 30 | tradeable engine objects at golden-decision τ |
| golden | 10 | author objects the same rule marks tradeable |
| negative | 10 | built from *tradeable* engine objects by the audited M2_PACK_PLAN methods (shift / stretch / spike anchor), re-tagged after mutation |

Constraints (§82.5.2 approvals):

- engine: ≥ 6 items per family (box, level, line); the rest
  proportional to the engine's tradeable output per family;
- ≤ 1 item per panel per family;
- golden: stratified by family; **may share panels with engine
  items** (the ≤1/panel/family rule still applies);
- **excluded panels:** those of p099, p100, p101, p102;
- TUNE panels only; HOLD sealed; **seed 20260923** (approved);
- one object per image;
- **τ = the golden-decision τ at which the object entered the pool**
  (approved), with the object clipped there.

## 3. Pool construction (engine)

For every golden-decision τ on each TUNE panel:

1. load the τ-run (canonical cache) under the R83 engine;
2. take the live set at τ, rank per `recall_at_k`, apply the author's
   per-family budget (box@1, line@2, level@1) — same accounting as
   M1;
3. keep only objects whose tag set at τ has no TRADE_VIEW_HIDE tag;
4. dedupe by (panel, object id);
5. sample 30 under the family floor/cap rules with seed 20260923.

Golden pool: golden objects scorable at their τ with no hide-tag,
sampled 10, stratified by family, excluding the four panels.

Negative pool: sample 10 tradeable engine objects, apply the
audited mutation (shift / stretch / spike anchor), then re-tag —
the mutation itself is the negativity; the underlying object was
tradeable before mutation.

## 4. Rendering

- `plausibility.render_item` / `_render_v2` path (never legacy
  render.py);
- R77 bracket placement (formation extreme ± offset);
- **EMA25 visible** on the panel;
- **no bars after τ**: the chart ends at the τ bar;
- the object is clipped at τ;
- one blue object, dashed "now" (τ) divider at the right edge;
- no title band, no metadata, single colour for all classes;
- **trade-view styling**: objects other than the item are drawn
  under the trade-view rule — hide-set-tagged objects are not
  drawn (`--drop-tagged` semantics), per §80.3 render doctrine.

## 5. Files

- `owner_pack/items/p001..p050.png`
- `owner_pack/manifest.jsonl` — `{seq, png}` only (blind)
- `owner_pack/ANSWERS.md` — p001..p050 blank, `yes/no/cant_tell`
- sealed key `evalcheck/_owner_judge_key/m2_tv_key.json` —
  truth/family/panel/τ/tags/object id per seq; outside the pack
- geometry-only sidecar (seq → geometry, no class) kept evalcheck-side
  for later rule analysis — never in owner_pack with class fields

## 6. Gemini render check (§82.5.5, §80.3b)

Before the Owner sees the pack, Gemini render-checks the page and the
pack renders: readable instructions, visible object, no bars after τ,
correct bracket placement, EMA25 visible where required, dashed "now"
divider, objects clipped at τ.  Gemini does **not** judge whether the
items are true.

## 7. Scoring (after the Owner answers)

- **M2-TV** = yes / (yes + no) over the 30 engine items, Wilson 95 CI;
- sensitivity counting `cant_tell` as no (yes/(yes+no+cant_tell));
- golden yes-rate and negative no-rate reported descriptively (not
  validity gates on the Owner);
- per-family precision (box / level / line);
- report → `evalcheck/M2_TV_REPORT.md`; the threshold .60 (R34)
  applies to M2-TV.

## 8. Independence

- Builder = EVAL-AUDIT only; the Lead sees aggregates only;
- key sealed in `evalcheck/_owner_judge_key/` before the pack is
  published;
- no truth/engine-status fields in any public artifact;
- blind until the Owner's answers are scored.

## 9. Dry run (§82.5(4), authorized before R83)

EVAL-AUDIT may build and dry-run the pack builder with the
placeholder engine (C-3 @fa2e52e5 + trade_tags=1):

- output is **pool counts per family and class only**;
- **no PNG in owner_pack, no sealed key** — nothing the Owner sees;
- once R83 names the engine, the pack is one run.

## 10. Resolved open points (§82.5.2 — all approved)

1. Seed **20260923**.
2. Negatives: audited M2_PACK_PLAN methods (shift/stretch/spike
   anchor), re-tagged after mutation.
3. Goldens may share panels with engine items (≤1/panel/family
   applies).
4. Engine item τ = the golden-decision τ at which it entered the
   pool, clipped there.
