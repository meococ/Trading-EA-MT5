# SF01 — RECON (Stage 0 of the Setup Factory)

Lane: SF (setup families). Author: Devin (autonomous SF worker). Date: 2026-09-21.
Mandate: build PA-pro grade price-action setup FAMILIES F1-F6, screen them
economically on DESIGN only through `lib/` referee, verdict SURVIVOR/DEAD per
family. Budgets: <= 24 configs and <= 2 logic revisions per family.

## 1. What the referee gives me (verified by reading `lib/`)

- `pa_eval.evaluate(spec, split, symbols, tf, cost_tiers, round_name, family,
  data_provider, seed, K_random, warmup_days, notes)` — the ONLY economic path;
  every call appends a ledger trial line (errors included, status=ERROR).
- Entries come from `spec["entries_fn"](symbol, bars, spec)` or a literal
  `spec["entries"]` list. Entry dict keys consumed by `pa_fill.simulate`:
  `sig` (TF bar idx), `side` (+1/-1), `inv` (pre-fill cancel price | None),
  `atr` (for gap_atr reporting), `tag`, `order_px` (explicit order price).
- Order model: `stop` (default price = signal-bar extreme +/- `buf_pips`),
  `limit` (needs `order_px`), `market_next_open`. Gap-aware fills; pre-fill
  invalidation (`inv`); expiry `v_bars` TF bars; `session_cancel` via
  `next_end`; all-in cost applied ONCE as adverse fill shift per tier
  (`gross/x1/x1.5/x2` = 0/1/1.5/2 x c_rt_pips).
- Exits: SL at `S_pips` from fill, TP at `tp_mult * S_pips` from fill; SL
  checked first inside an M1 bar; flats: daily 22:00 server, Friday 20:00,
  weekend veto, **MIDNIGHT: positions never survive a server-day boundary**
  (exit at last bar close of the fill day), DATA_END. => Intraday-only
  semantics; targets must be reachable inside a day.
- **S_pips and tp_mult are FIXED per spec.** Per-entry structural stop prices
  are NOT supported by the engine => I express "stop at structure" by
  bucketing: an entry is emitted into the S-bucket config whose rung is >= the
  structural stop distance and within a declared tolerance (SL never sits
  inside the structure). See DECISIONS.md D1.
- Matched random baseline: `pa_random.match_random`, K=20, cells =
  (session eu/us, hour, dow, month), same order type/geometry, side drawn with
  P(long) = input long share. **Only in-session signal bars get matched
  controls** (eu 05:00-11:00, us 11:30-17:30 UTC of bar CLOSE).
- Warmup: signals with sig < first_live_idx or UTC before split start raise.
  `bars["warmup"]` flag exists on resampled bars; detectors must mask it.
- `pa_data.frame` is the default provider (m1 dict, resampled TF bars,
  starts, sess_mask, first_live_idx, c_rt_pips). Dropped incomplete TF bars
  leave time gaps in the index space — detectors must check `t` adjacency,
  not assume contiguous bar times.
- Costs x1 pips: EURUSD 1.0, GBPUSD 1.1, USDJPY 1.4, AUDUSD 1.4 (proxy,
  `docs/COSTS.md`). Geometry guard: stop >= 10 x c_rt => min stop
  EURUSD 10, GBPUSD 11, USDJPY/AUDUSD 14 pips.
- `pa_slots`: 2 heavy-process slots; both currently held by the R02 outcome
  run (pids 32776/37924, verified alive). All heavy work acquires a slot with
  a long timeout (queueing), BelowNormal + 4 threads set at import.

## 2. Zone infrastructure (`struct/zones/`, frozen — read-only to me)

- `ZoneContext(m5_bars, h1_bars)` supplies ATR14(H1) aligned to M5 closes,
  ATR14(M5), M5/H1 confirmed pivots, `refs` (PDH/PDL/PDC, Asia, week, 00/50).
- Generators (registry order): `line1_cluster` (+-3-bar M5 swing clusters,
  micro, densest), `fractal_h1`, `kde_swing`, `profile_va` (sparsest),
  `sd_base` (tight base + >= 1.2 ATR(H1) impulse, micro, 5-day life),
  `ref_levels` (PDH/PDL/PDC + Asia + week + 00/50 bands).
- Shared state machine (`common.py`): touches, respected tests
  (1.0 x ATR(H1) move within 48 bars), BREAK = close beyond far edge + 0.1 x
  ATR(H1), RECLAIM within 96 bars, FLIP_CONFIRMED after reclaim window,
  FRESH = no touch in 24 bars, RETIRE at max_age or break+192 bars.
  Strength v0 = weighted touches/respected/recency/age/scale/role/ref/qual.
- Arming (`arm_zones`): non-broken, centre within 2 x ATR(H1) of close,
  deduped by 0.25 x ATR centre distance, max 6, strongest first.
- **Reference semantics = `views_at(t)`**, which replays `_step_zone` over
  every bar in [born_idx, t]. The forward pass's `_step_all` is a cheaper
  approximation (it can miss late reclaims and gap-bars that never intersect
  the band). My snapshotter reproduces replay semantics exactly: step every
  live zone on every bar >= born_idx, with backfill from born_idx at creation
  (zones are born before they are created — pivot confirm lag). Verified
  against `views_at` in a unit test.
- `runner.py` already implements the candle + zone-band PNG pattern I reuse
  for family snapshots (code copied, source untouched).

## 3. What is already dead — do not repeat

- VPA DR3 micro-line pattern break: PF x1 0.795, lift +0.24pp — "looks like
  the book" is not edge (ECON-1). F6 must differ in mechanism: real zones for
  the box edges, structural stop >= 10 x cost, correct stop-order entry at the
  signal bar (not market at the break bar), structural room gate.
- Legacy kill list (~615 backtests): tight-geometry scalps (stops < ~10 x
  cost), raw PDH/PDL/Asia fades, bare range/session breakouts, round-number
  fade, compression->direction, VWAP, z-fade, exit overlays, AND-stacks that
  starve cadence.
- R01/R02 physics: zone-vs-empty is non-identifiable here; zone "strength" is
  mostly recency. => No family is gated on zone physics; the matched-random
  economic screen IS the test. Strength used only as a declared context
  bucket, never as a claim-bearing axis.
- Probe-vs-fill gap: only M1-path fill simulation numbers count.
- Never rescue a dead config with hour/day/year filters (charter + mandate).

## 4. Family plan (mandate order kept; generators chosen)

| fam | name | engine pattern | zones used | stop | target |
|---|---|---|---|---|---|
| F1 | ZONE REJECTION | probe into armed zone rejected; fade toward opposite structure | line1_cluster, sd_base | beyond probe extreme + buf (bucketed) | nearest opposing structure room gate, fixed R grid |
| F2 | BREAK-AND-RETEST | close through zone; first pullback into it rejected; continuation | line1_cluster, sd_base | beyond retest extreme + buf | break-side structure room, fixed R grid |
| F3 | FAILED BREAKOUT / TRAP | close beyond zone then reclaim within k bars; fade | line1_cluster, sd_base | beyond break extreme + buf | opposite zone edge room, fixed R grid |
| F4 | TREND PULLBACK TO ZONE | H1 trend; M5 pullback into trend-side zone; resume trigger | line1_cluster | pullback extreme / zone far edge + buf | prior trend extreme / room gate, fixed R grid |
| F5 | SECOND ENTRY | H1 trend; two-legged M5 pullback (H2/L2) trigger | none (pivots only) | 2nd-leg extreme + buf | prior extreme / room, fixed R grid |
| F6 | VOLMAN BOX BREAK w/ buildup | DR3 lineage: box from armed zones, compression, stop order through signal bar | line1_cluster (box edges) | signal-bar far extreme + buf (>= 10 x cost) | room gate, fixed R grid |

Rationale for generator choice (DECISIONS D2): `line1_cluster` = baseline
swing-cluster zones (densest, multi-touch semantics = "pro" S/R areas);
`sd_base` = supply/demand bases (the institutional "unfilled orders" story);
`ref_levels` kept out of F1-F4 grids (raw reference-level fades are on the
legacy kill list; their deltas are mechanism-free). F5 is deliberately
zone-free (pure structure). F6 uses line1_cluster zones as box edges.

## 5. Shared infra I will build (all under `families/`, tests under `tests/`)

- `sf_ctx.py` — cached per-(symbol,generator) DESIGN context: exact-semantics
  zone pass -> per-bar near-price zone table (armed + broken/live, <= 10
  slots), plus per-bar scalars (ATR14(H1) aligned, ATR14(M5), EMA25/50 on M5,
  H1/H4 trend sign, session flags). Written to `rounds/SF01/zcache/*.npz`;
  detectors assert `t` alignment with `bars`.
- `sf_detect.py` — detector helpers: session gate, warmup mask, contiguous-bar
  checks, structural stop bucketing, room-to-structure gate, cooldown.
- `sf_snap.py` — PNG renderer (candles + zone bands + signal/entry/SL/TP),
  pattern from `runner.py`.
- `sf_run.py` — census + screen driver: spec JSON -> ledger spec-hash line
  (kind="spec") -> census (no outcomes) -> `pa_eval.evaluate` per config ->
  gate evaluation + JSON report per config.
- `f<k>_<name>.py` — one detector module per family (`entries_fn` +
  PARAMS + spec emitter).
- `tests/test_sf_*.py` — synthetic-market tests: prefix invariance of every
  detector, warmup ban, determinism, adversarial planted cases, bucket
  arithmetic, loader sealed-split assertion test.

## 6. Risks / open issues

- Referee MIDNIGHT exit caps holding at one server day — all targets are
  intraday-reachable by construction (room gate + modest R multiples).
- Full zone pass cost unknown: measured on a slice first; cache built once
  per (symbol, generator) under a pa_slots slot.
- `evaluate` computes spec_sha itself; I also append a `kind="spec"` ledger
  line per family spec before ANY outcome — ordering evidence in the chain.
- Screens queue behind R02's two running slot holders; the factory proceeds
  with non-compute work (specs, detectors, tests, snapshot renderer) meanwhile.
