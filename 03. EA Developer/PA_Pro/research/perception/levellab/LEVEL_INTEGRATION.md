# LEVEL INTEGRATION (V5, v2 — live-budget edition) — proposal only, Lead rules first

Supersedes the v1 draft on the same filename. The v1 design was a
proposer without an ink budget; R17 §17.2 required re-testing at the
author's budget before any integration claim.

## Evidence base (paired A/B, one code state, `budget_r1.json`)

Matched-ink test on 198 TUNE panels — three proposers, top-k live at τ:

| metric | lab | prod stream (caps off) | naive pivots |
|---|---|---|---|
| LC recall@2 (best ranker) | **.333** (ret24) | .208 (birth_score) | .292 (ret24) |
| LC@2, day-5-fold **CV** | **.267** | .208 | .203 |
| MINI@2 CV | **.264** | .082 | .137 |
| LC@1 CV | 0.107 | **0.171** | 0.127 |

**Integration condition from RESUME-4 §4 is met at k = 2: the lab
proposer beats both the production stream and the naive baseline under
day-level 5-fold CV**, and wins MINI@2 outright. **Caveat: at k = 1 lab
loses to prod** — the proposal requires `level_max_live ≥ 2`; a 1-slot
budget would favour the production stream. Full tables: `ROUND_L7.md`.

Raw-stream cost that the budget must hide: lab births 14/panel (live@τ 6)
vs author's ~2 objects/panel. The proposer's value is coverage + ranking;
a **live budget is mandatory**, not optional.

## Exact change list for `levels.py`

1. **Origin registry** (new, in `LevelBook`):
   `self.origins = [{bar, price, dir, cls, n_def, last_t, sess, expire}]`
   - `on_pivot`: every confirmed θ pivot registers
     `{bar=piv.t_ext, price=piv.price, dir=piv.dir,
     cls='theta2'|'theta1'}`; merge into an existing same-side origin
     within `level.touch_tol`.
   - Session/Asia origins: running session hi/lo + finalized Asia
     (m < `asia_end_min=420`) extremes; a superseded extreme gets
     `expire = i + sess_grace_bars(48)` and is dropped at grace end with
     n_def < min_defences.
   - Merge rule: same-side origins within `touch_tol` keep the
     **defended-edge price** (min for lows, max for highs) — never the
     mean (L4: mean drifted born prices 1.5–3p).
2. **Defence sweep** (per bar): bar extreme within `touch_tol` of an
   origin price (dedupe consecutive bars) → `n_def += 1`, `last_t = i`.
3. **Approach trigger** (route `defended_origin`): `n_def >= 2` and
   `|close − price| <= approach_abr(1.75)·ABR` → candidate
   (`MINI_LEVEL` if `age ≤ mini_max_age(90)`). Score
   `= n_def − dist_abr`; birth floor `min_score(1.0)`. Feats:
   `touches=n_def, prom_abr, age_min, dist_abr, cls, ret24`.
3b. **NMS reprice**: challenger inside `nms_band` with
    `n_def ≥ incumbent.n_def0` reprices incumbent to the challenger edge
    price, keeps early `t_birth`, logs `reprice`. Side-free (a defended
    zone flips roles).
4. **Live budget** (new — the v2 core):
   - `level_max_live = 2` live LEVEL_CARRIED + `mini_max_live = 1` live
     MINI_LEVEL at any time (author's ink ≈ 2 objects/panel; V8 test was
     k ≤ 2). **Not 1** — under CV the lab loses to the prod stream at
     k = 1 (0.107 vs 0.171); the edge only exists with ≥ 2 live slots.
   - When a candidate wants to birth and the budget is full: compute the
     **live score** of candidate and of each live member,
     `live_score = n_def − dist_abr + 1.0·ret24`
     (ret24 = `last_t` within 24 bars — "the level was defended on the
     return leg"; CV-chosen ranker, ROUND_L7; standalone AUC 0.606
     borderline — REQ-L2).
   - Candidate births only if its live_score exceeds the weakest live
     member's; the displaced member closes as `superseded` (recoverable
     by revive, below). Otherwise the proposal is suppressed — no object,
     no salience slot spent.
   - This makes the family self-throttling: it stops depending on global
     rate caps for its ink discipline, and REQ-L1's family-floor ask
     shrinks to "let the budget winner compete".
5. **Lifecycle in `maintain`:**
   - traverse-death: `traverse_bars(2)` consecutive closes through zone;
   - `price_left`: close when `|close − price| > live_abr(3.0)·ABR`;
   - `stale`: close after `stale_retire_bars(60)` without a zone touch;
   - revive: CLOSED object re-approached within `revive_bars(96)`
     re-activates (subject to the same live budget — it must win a slot);
   - a `superseded` level re-births freely if its origin is touched again
     (defence refresh) — budget churn is cheap ink, not lost structure.
6. **Dedup band**: `dedupe_within_pips` 1.5 → `nms_band_pips 3.0`.

## Param changes (str_replace-style on the level block)

```jsonc
"level": {
  ...keep all existing...
  "min_defences": 2,        // meas: V2 85% trusted LC have >=3 touches
  "approach_abr": 1.75,     // meas: V2 dist_tau p50=1.64
  "live_abr": 3.0,          // lab
  "traverse_bars": 2,       // lab: golden tolerates teases
  "stale_retire_bars": 60,  // meas: DR-MARKET v2 via R11 (~5h)
  "sess_grace_bars": 48,    // lab: L4 sweep 24<48=72
  "min_score": 1.0,         // lab: L5 sweep 2.0<1.5<1.0=1.2<0
  "revive_bars": 96,        // lab: anti-churn
  "mini_max_age": 90,       // lab: MINI when origin <90min old
  "level_max_live": 2,      // NEW: R17 author's-budget test used k<=2
  "mini_max_live": 1,       // NEW
  "ret24_bars": 24,         // NEW: ranker window, CV-chosen (ROUND_L7)
  "dedupe_within_pips": 3.0 // meas: V2 zone width p50 5-8p
}
```

## Provenance requirements

- Origin registry records `cls` and `n_def` on every candidate (funnel
  labels need them).
- `price` frozen at birth EXCEPT the 3b reprice — log `reprice` events.
- Budget evictions log `superseded` with the winning candidate's id, so
  the funnel can distinguish "rejected by salience" from "outranked in
  family".

## Expected deltas (honest, post-V8 — budget mechanism simulated, ROUND_L8)

- The budget was then **simulated inside the lab engine** (same code,
  three param sets): uncapped LC 0.729 / MINI 0.677 / live@τ 6 /
  ~14 born per panel → **budget 3+2: LC 0.729, MINI 0.645, live@τ ~5,
  ~11 born** → **budget 2+1: LC 0.667, MINI 0.548, live@τ ~4, ~9 born**.
  Born recall survives eviction because superseded levels revive on
  re-approach; what the budget removes is simultaneous live ink.
- Under the live budget the ruler-visible metric moves toward
  **recall@τ**: measured lab LC .333@2 in-sample / **.267 CV**;
  prod stream .208 CV; naive .203 CV.
- **Flag for the Lead:** the charter gate (born recall ≥ .60) survives
  the budget better than feared — 2+1 still reads 0.667 born — but the
  honest author's-ink number is the recall@τ pair (.33@2 in-sample,
  .27 CV) since eviction churn inflates the birth count. If the gate
  stays defined on born recall the proposal clears it in the lab; the
  Lead decides which reading is authoritative.
- Other types: no change outside levels.py; expect no recall delta
  elsewhere. Salience pressure on the family drops sharply (suppression
  happens pre-slot).
- MINI_LEVEL: +recall from young defended origins under a 1-live budget
  (lab .387@2 vs prod .194); `formation_extreme` route stays.

## Salience request

REQ-L1 stands but shrinks: with the budget, the family asks for at most
~3 slots/panel; the ask is a family floor of 1 slot per window when a
budget-winning candidate exists — not a cap raise.

## 5-line summary

Golden levels are old defended pivots; the lab proposer covers them
(.75 uncapped) but only earns its keep under a budget: at ≤2 live levels
it beats prod and naive under CV (.267 vs .208/.203).
Integration = origin registry + causal defences + defended-edge merge +
approach trigger + a self-throttling live budget ranked by
`n_def − dist_abr + ret24`, with reprice/revise lifecycle.
ret24 is the CV-chosen ranker but only a borderline standalone feature
(REQ-L2). Charter-gate metric mismatch flagged for the Lead.

---

## Post-integration A/B (R19 §19.3 item 2, engine `1c24be53`, 2026-09-21)

Shipped behind `level.defended_origin=false`.  Flag ON **replaces**
`session_extreme` and `formation_extreme` inside `levels.py` (running
extremes + confirmed pivots feed the origin registry instead); external
level emitters (`broken_line_edge` in patterns.py) are unchanged —
chosen because the author's ink is small and the routes overlap.

Paired A/B on 198 TUNE, ruler `50e11fd5` (full table in ROUND_L9.md):

- LC born recall .146 -> .229 (+4 objects), MINI flat; clutter ratio
  2.50 = 2.50, live levels at tau 0 = 0; flicker .33 -> .43 ch/h.
- **Keep-rule (R18 §18.1) FAILS**: BOX family loses 2 matched objects
  net (4 lost, 2 won) — the flag therefore stays default OFF.  Logged
  as a lever for the Owner's pack.
- Starvation (the pre-flagged concern): 293,698 defended proposals ->
  262 born.  `suppressed_budget` 122,913 — the local 2+1 gate mostly
  suppresses its own pending queue; `rate_limited` 3,123.  The 2-LC
  live budget cannot materialize while `rate_level_carried=1/72` and
  `rate_total=5/72` govern births — see REQ-L3 in REQUESTS.md.
- Bootstrap: lab−prod LC@2 +.056 [−.086,.202] weak; lab−naive +.067
  [−.039,.179] weak (ci_bootstrap.py on sb_r2.json fold rows).

KATs added to tests/test_engine_v1.py (suite 34 -> 38, all green;
pytest 46/46): births_on_approach, lone_extreme_never_births,
budget_evicts_weakest, budget_suppresses_weaker.  One production bug
found by them: `_budget_ok` originally counted foreign-route objects of
the same kind and could evict them — now filters `why==defended_origin`.
Known artifact: pool birth-lag lets a suppressed loser transiently
birth then close 'superseded' — contributes to the flicker delta.

## Post-integration rounds (R24 §24.2) — see LEVER_TABLE.md

- **v2** (`def_mini_off`, ROUND_L10): defended LC only.  BOX loss
  healed (+1) and flicker back to .33, but PATTERN_LINE −2 (same
  rate_total ledger mechanism, different victim) and LC gain shrinks
  to .167 — flag_on's extra hits were MINI-carried via the family
  match.  Keep-rule FAILS.
- **v2b** (`def_all_lc`, ROUND_L11): all defended births typed LC.
  First variant with every family within −1 (BOX −1, PL −1, RANGE −1,
  MINI +1).  LC born flat; MINI .097; snapshot/LC@2 .085.  Keep-rule
  losses+ink legs met; recall leg is a judgment call.  Underneath the
  flat headline: budget thrash trades stable hits for different ones.
- **v2c negative control** (3-LC budget): worse — BRACKET −3, PL −2.
  Ordering-driven thrash, not capacity.  Not adopted, no param added.
- flag_on LC born diff +.071 [.010,.152] is the only positive-CI
  result in the family; all other CIs weak.
- Identity: flag OFF @a62edc19 bit-identical to STABLE 584c7743
  (198/198 panels, objects+cand_log+bars, identity_check.py).
- Scoreboard: flag_off / flag_on / v2 / v2b all appended @a62edc19.

## The recommended configuration (R25 §25.5 measured, ROUND_L12)

The integration proposal is no longer the flag alone — it is the
**pair**:

```jsonc
"salience": { "fam_ledger": true },                 // build lane's flag
"level": { "defended_origin": true, "def_mini_off": true }
```

Measured at `2795e5e0` (re-verified identically at `9283b389`),
198 TUNE, ruler `50e11fd5`:

- LC born recall .146 -> **.229** (+4), trusted .275; snapshot .128;
  LC@1 **.064** (author's median live count is 1 — R28 §28.5),
  LC@2/.128, LC@3 .128; trusted LC@2 .154.
- **Keep-rule PASSES every leg** — BOX 0, PATTERN_LINE 0, MINI 0,
  worst CONTEXT_RANGE −1; BRACKET +5, CONTEXT_LINE +1.
- Ink unchanged: births/panel 6.0, clutter ratio 2.50, live@τ 0.0,
  flicker .33 ch/h — all equal to default.
- Day-bootstrap CIs positive: LC born **+.120 [.009,.242]**, LC@2
  **+.119 [.021,.233]**.
- Mechanism: defended births draw on LEVEL_CARRIED's own ledger
  share — they can no longer displace BOX/PL births (cross-family
  zero-sum removed).  Ledger alone (arm b) FAILS the keep-rule
  (BOX −2) — the pair is the lever, not the ledger by itself.

Residual bottleneck, documented not run (R28 §28.5): intra-family
competition inside the LC share — `rate_level_carried=1/72` (the
binding cap; `fam_rate_level_carried` alone is a no-op) blocks 19
covered-but-unhit goldens, and the local 2-LC defended budget blocks
6 more.  A priced ceiling probe (`rate_level_carried=2` +
`fam_rate_level_carried=2`) buys +3 goldens for +1 object/panel and
2x flicker — an Owner-level trade, not a keep.

Both flags remain **default OFF**; the freeze default is unchanged
(R27 §27.3).  R29 §29.2 narrows the claim to the pack's exact
wording — "keep-rule pass on born recall (verified); four kinds
silenced (defect); no gain at the author's budget": under the
engine's own top-k ranker (c) is flat at k≤5, so the lab-ranker
@k/snapshot gains above are a direction for the next build round
(floor shares, per-family live budget, within-family NMS), not a
shipped result.
