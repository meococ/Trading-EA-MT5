# PORT_PLAN — perception engine → MQL5

Gate: **no engine logic is ported before P-FREEZE** is announced in
`research/perception/LEAD_RULINGS.md`. This file is the plan only.

Status of dependencies at writing (2026-09-21 ~13:20 local):
`schema/perception_v1.json` EXISTS; `PERCEPTION_API.md` and
`PORT_NOTES_MQL5.md` do NOT exist yet — re-read them when they land.

## What is already in place (MQL5 side)

| Piece | File | State |
|---|---|---|
| Schema mirror (enums, struct, importer) | `PA_Perception.mqh` | done, aligned to schema v1 |
| Draw grammar (12 types, themes, budget) | `PA_Draw.mqh` | done |
| View-only indicator (zero trade code) | `../PA_Pro_View/PA_Pro_View.mq5` | done, compiles 0/0 |
| Mock snapshot (all 12 types, real week) | `tools/mock_snapshot.py` | done |
| JSONL→CSV projector (schema → wire) | `tools/jsonl_to_csv.py` | done, smoke-tested |
| Per-bar parity comparator | `parity/compare_perception.py` | done |
| Owner runbook | `VIEWER_RUNBOOK.md` | done |

## Wire contract (proposed to the perception lane)

Engine emits JSONL per `perception_v1.json` (one Snapshot per closed
bar, `t` = bar index, `t_cet` = CET wall). `tools/jsonl_to_csv.py`
projects it to `perception_csv_v1`:

```
[bar_t,]id,type,state,role,t_birth,t1,t2,p1,p2,letter,side,why
```

- `bar_t` present → per-bar parity stream; absent → flat viewer file.
- All times are SERVER EPOCHS (t_cet + 1h, D2). Bar indices never
  cross the wire; `t_right=null` → `t2=0` (open).
- `stand_aside[]` codes → one `STAND_ASIDE` pseudo-row per bar.
- `facts` (pressure, magnets, obstacles, domes, bar_facts) are NOT
  drawn; reserved for the setup lane. If wanted on chart, add a HUD
  line — no grammar objects.
- Geometry flattening is fixed per type (see PA_Perception.mqh header).

## State machines to port (per object family)

From spec §3 lifecycle (names are schema `state` values):

1. **BOX** — PROVISIONAL (≥2 touches on an edge, forming) → CONFIRMED
   (edges fixed). On close-through an edge ≥ tol → BROKEN; brief
   post-break window then DEAD. PIERCED when the opposite edge is
   poked intrabar but not closed through. Role can flip
   (resistance→support) on role reversal — `role`/`why` carry it.
2. **RANGE_OPEN** — ACTIVE while both lines hold; the bar a line is
   closed through → transition per schema events (BREAK); right edge
   stays open (t2=0) until the range resolves.
3. **CONTEXT_RANGE / CONTEXT_LINE** — passive, ACTIVE→DEAD only; they
   never trigger anything (context layer).
4. **PATTERN_LINE** — ACTIVE; PIERCED on intrabar violation, BROKEN on
   close-through; a pierce that fails spawns LABEL_TF "F" / FALSE_EXT.
5. **LEVEL_CARRIED** — ACTIVE until first clean touch → CONSUMED
   (drawn dimmed, no longer an obstacle).
6. **MINI_LEVEL** — ACTIVE; short-lived trigger, DEAD on break.
7. **SQUEEZE** — ACTIVE while walls narrow; resolved by a bar that
   escapes the ellipse → DEAD (or spawns PATTERN_LINE trigger).
8. **Annotations** (LABEL_TF, BRACKET, FALSE_EXT, STAND_ASIDE) — born
   and fixed; no lifecycle beyond ACTIVE→DEAD by age/irrelevance.

Exact transition conditions come from `research/perception/` at
P-FREEZE — this list is the skeleton, not the spec.

## Engine port shape (mirroring the zone-era lessons)

- Same two-track discipline as `PA_Zones.mqh` (D4): a pass track that
  steps objects on each closed bar, and a read view that reflects the
  snapshot at bar t. If the Python engine replays object state (like
  `views_at`), the port needs the same catch-up-at-birth.
- `CPaPerception2` (name TBD) next to `CPaCtx`: per-bar `StepBar`
  producing the object set + facts; `CPaSnapshot` already deserializes
  the same row shape for testing.
- ABR (avg high-low of last 50 closed bars), tol = max(1 pip,
  0.25·ABR), EMA25 — all already present (`PaEma25` in PA_Draw.mqh is
  the sf_ctx convention; keep ONE implementation).
- Visible window ≈ 84 bars; structure older than ~1 day of bars is
  culled — the port must reproduce the same pruning rule.

## Test vectors

1. `tools/mock_snapshot.py` output — every type, one DESIGN week:
   viewer smoke test (manual, Owner's chart) — DONE for grammar.
2. Golden weeks: the lane's `golden/` set (parsed book annotations) —
   replay through both engines; per-bar object sets must match.
3. Prefix-invariance: run the engine on bars [0..T] vs [0..T+k] and
   diff the object sets at bars ≤ T — must be identical (causality).
4. Incremental-vs-batch: same trick as `PaRunZoneSelfTest` — PushBar
   stream vs full Init must produce identical snapshots.
5. Edge cases: t_right=null open objects across weekend gaps; objects
   born before the export window (idx→epoch fallback path);
   stand_aside-only bars; >8 simultaneous structures (budget).

## Parity plan

- Python emits JSONL → `jsonl_to_csv.py` → `perception_csv_v1` (per-bar
  mode). MQL5 engine (post-freeze) emits the same CSV from
  `PA_Pro_Parity`-style script run by the Owner.
- `parity/compare_perception.py` joins on `bar_t`, compares id-keyed
  object records: type/state/role/side/letter exact, t1/t2 exact,
  p1/p2 within tol (default 1e-9 per spec §8). PASS = ≥99.5% of bars
  identical. `--report` writes per-bar diffs.
- DESIGN weeks only; the BOOK window (2012-02-13 → 2012-09-07 CET,
  EURUSD) is perception-lane-only — the EA side never touches it.
- Warmup: object state carries across window starts (like zones) —
  comparison needs a shared warmup margin (~1 day of bars; refine at
  freeze) or `--e0`-style bounds.

## Open questions for the perception lane (record, don't block)

1. Emit `t_cet` on every line (schema marks it optional-ish); the
   projector needs it or a `--bars` sidecar (idx,epoch).
2. `id` stability across bars (same object same id every bar — needed
   for the (bar_t,id) join and for stable object naming on chart).
3. `extends_to` semantics on lines (drawn segment vs influence span).
4. Whether `domes`/`obstacles` facts ever want a drawn form.
