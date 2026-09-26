VERDICT: FAIL

Adversarial audit of the FROZEN+EXECUTED R01 physics bake-off (retrospective; the
run was frozen 2026-09-20T15:35:55Z and resolved ~15:37Z). Two MAJOR findings
stand: (F1) the preregistered control is confounded by approach distance —
measured, not hypothetical — so the printed "no edge over arbitrary levels"
answer is not clean evidence either way; (F2) the eval-token gate has two working
bypasses (off the R01 outcome path, but a live hole in the referee). The frozen
artifacts themselves are internally consistent: code == frozen prereg, freeze
ordering holds, hashes and ledger verify, prefix-invariance holds for 3
generators + the event table. The result should NOT be re-run under this spec;
it stands with a changed interpretation, and the decisive retest needs a
distance-matched-control preregistration (R02). Full reasoning in §4.

## 1. Scope — every file judged (sha256 + mtime at time read)

| mtime (local, UTC+7) | sha256 | file |
|---|---|---|
| 2026-09-20 18:32:36 | 3c57536848a4aa6113950d06d50331b8c664e18b79d34e08def2f1019bc5dc2c | PA_PRO_CHARTER.md |
| 2026-09-20 19:16:24 | 37756d6922c7134901e94940a10e03ef4e11f7b72418f754d2ceffe525d38592 | docs/CHARTER_ADDENDUM_1.md |
| 2026-09-20 22:14:12 | dcb85c81e4d1755d7fa2dd8ef5fd934e4f2b65c62556308aa6be4f5b964088ce | docs/CHARTER_ADDENDUM_2.md |
| 2026-09-20 21:55:07 | ce35ed66a6513436d9e1d80f3d7d1a7fc2a67fa5576fe109ad2759d8d8929365 | rounds/R01/00_LEAD_RULINGS_READ_FIRST.md |
| 2026-09-20 22:35:48 | 91b21dc7dc5d3701ba5d68904c8621eb7e10df9e1324bf4aae59d26335252184 | rounds/R01/PHYSICS_PREREG.md |
| 2026-09-20 22:35:55 | 10a9830eb1f34cadc93fd8876f2d311f35fd175af36d974b434ee7330258be44 | rounds/R01/FREEZE.json |
| 2026-09-20 22:27:22 | a3dece3575afafa25afdd5e0903fe05db05451b406a1da6e58b5981cc0a9d074 | rounds/R01/PARITY.md |
| 2026-09-20 23:02:14 | b31e768e73730d799c66ec9493dbc5a1f15defd8bd4e93509ba26e36f036de79 | rounds/R01/PHYSICS_RESULTS.md |
| 2026-09-20 22:51:19 | d0063567fa25c9574616d0d57712407e38bbf0d766c42714ce4637f67d6c62c4 | rounds/R01/REVIEW_R01_PHYSICS.md |
| 2026-09-20 21:41:58 | d669410078bc0410ba6addec52386cfd4abbcb0680767c973f1e2741fc3abe2d | research/zones/SHORTLIST.md |
| 2026-09-20 21:49:05 | 870f8ae66de532cb18d72c64f27206301a7578d9db8f93800cddabcb29b48b16 | research/zones/REVIEW_ZONE1.md |
| 2026-09-20 21:22:50 | 08ac789756fdc3308b122508a47caaa164097cc3a0a763deaaa3f0a52b16c6e2 | research/physics/phys_common.py |
| 2026-09-20 22:16:00 | 74eabf69acab294eb65ae3ba61ccf91ab005f25e2f730e6348069f9112a9f3f5 | research/physics/phys_extract.py |
| 2026-09-20 22:17:59 | c18b643ec78d6c4c062aae54c42dcced5ea001dc1c0ab7b104cd384eb396b5c6 | research/physics/phys_controls.py |
| 2026-09-20 21:25:13 | b4f05d05431c2435a56e6df5246b46685867fd94c4ce8f569ad9e335b2f27a86 | research/physics/phys_resolve.py |
| 2026-09-20 22:22:24 | 0d7fe751c815e88e95919b08715e6816a565835ca997a69e134859dc975df2db | research/physics/phys_source.py |
| 2026-09-20 21:25:59 | 4a66fc84f13097dd01c9cd73f3d8e6cef09ff63149e7585c3a2092957f4cf2f1 | research/physics/phys_stats.py |
| 2026-09-20 22:28:29 | d1f5232f10628610c9c79e50b42ef3546ee6945b3a1123b19ecd0f8f74002790 | research/physics/phys_analysis.py |
| 2026-09-20 22:28:40 | 52f7b7d6b6838e278c8edfb32aaf22d71d62822bf1e8368db9ced73acf38fdf4 | research/physics/phys_freeze.py |
| 2026-09-20 22:27:36 | 256d38bbbb677410da2bc9bf2a62b07625ed03ad305e09a73a05177417416a71 | research/physics/run_bakeoff.py |
| 2026-09-20 21:30:57 | cde9aa33d10f24b704c3e2d2cf9a2acfd87f2ce7363e836bdf29d629967bcec8 | research/physics/run_counts.py |
| 2026-09-20 22:18:53 | 2cdf27e5dcaaa2aef9725a0184ddf780f184c3a581267c899904255e2be6beff | research/physics/phys_parity.py |
| 2026-09-20 21:38:59 | 3bcad6f576d1c84c19135aaccc62c9988fcaa8ba0f45ff4078ad346874556574 | struct/zones/common.py |
| 2026-09-20 20:56:02 | 2e3387a5475cf19489c00943c3199793150090840e91a8733da4e79083be245d | struct/zones/refs.py |
| 2026-09-20 21:16:24 | db845417b1f9873297023ff519bec4db3194e4dea07d54ec2babb2382bf04596 | struct/zones/ref_zones.py |
| 2026-09-20 20:58:25 | 13744db86c3550b12601fb847eb21357966d63eb23c893270ec574624e0362f6 | struct/zones/data_helpers.py |
| 2026-09-20 21:25:35 | a022eba86e71cd825769c603578ca816927c76caf65941c8e963201d430d3592 | struct/zones/registry.py |
| 2026-09-20 21:39:50 | 9703b5e8b5478e7dce20d0320697944c2ebabb5d7359f53bad66862a7ebae5be | struct/zones/line1_cluster_zones.py |
| 2026-09-20 21:39:50 | b730e1261eb9cac6b74201536b48a35d08f359f55e63e8a964b3927474943ca8 | struct/zones/fractal_zones.py |
| 2026-09-20 21:09:20 | ac6bbac63f73ff8436c133315ebac22382f9c741167c5f1b93a1dcc0b8223aa5 | struct/zones/kde_swing_zones.py |
| 2026-09-20 21:08:28 | 7fbbc73aef07118cc4ccf1a47b31b9fb40d5f0932e4e0be27852ac6a9dc7842e | struct/zones/profile_zones.py |
| 2026-09-20 21:13:10 | bd2315889c6db0732de912f836e9e65d46ccbf4ccba39ec3b90159dbe569f6c2 | struct/zones/sd_base_zones.py |
| 2026-09-20 18:40:43 | c9ff59a3325ef78b6c3d25cd572a022034b828d5083c489f55e1115c25c11832 | lib/pa_sealed.py |
| 2026-09-20 18:46:49 | 51b4fdfa7b8e886a24fc55a491fdf544d9836e300fe8bfa2c4409b2573bd6c22 | lib/pa_data.py |
| 2026-09-20 18:48:56 | f5cc1c4aa09c4de73d04684406705981dec2bbf312114cde0037ef9f90f2f5a4 | lib/pa_ledger.py |
| 2026-09-20 18:54:26 | 82a96e6bf7513c6ddde655e2d6d93018496b31e16becf9340b2adc025b62c542 | lib/pa_eval.py |
| 2026-09-20 19:23:38 | 74f027095a1cc5d34c460c7c916e170233d67d41117568cb2119abe22120e7ce | lib/pa_metrics.py |
| 2026-09-20 22:52:27 | 8e65a15e366c03a092d9f0b84e5b7b6a857e1c5f04faa676c610f421f8af85b6 | lib/pa_fill.py |
| 2026-09-20 18:40:02 | 8c05f19a793a155c1b47b6db85bed30343a53b7548b178a91816f60c668202ee | lib/pa_clock.py |
| 2026-09-20 18:57:36 | a2402d0566c50474ca640cc62e4e8b409a8e1cc3c66a261620100491a0e70b66 | lib/pa_costs.py |
| 2026-09-20 18:42:07 | 350146d430b1fe205aff65ecbcf9ad30b1470614d8b853e1c6c0b9f242ffa750 | lib/pa_random.py |

Frozen-bundle hash notes: `physics_code_sha256` frozen `d118b72f…` — verified by
REVIEW_R01_PHYSICS (MATCH excl. post-freeze `_diag_dist.py`). `lib_code_sha256`
frozen `afa4ac30…`; recomputed now `9427a816…` — STALE because `pa_fill.py` was
modified at 22:52:27 local (15:52:27Z), i.e. AFTER freeze and after the physics
review's hash check (see F8). `zones_code_sha256` frozen `3676262d…` matches
this table's zone files (they are unchanged since the freeze — all zone mtimes
precede 22:35:55 except none; verified by spot check above).

## 2. Findings

| ID | sev | file:line | defect | concrete failing scenario (inputs → wrong output) | minimal repro |
|---|---|---|---|---|---|
| F1 | **MAJOR** | `docs/CHARTER_ADDENDUM_2.md` item 2 → `PHYSICS_PREREG.md:148-154` → `phys_controls.py:249-276` | The preregistered control is confounded by approach distance: real ARMED events require the zone already near price (armed rule ≤2×ATR center; measured median near-edge distance **0.28–0.34 ATR** at anchor), while control bands must sit ≥1 ATR away and actually draw at a median **2.11–2.37 ATR** (~18–30 pips). A control event can therefore only fire after a ≥1 ATR directional move toward the band — a different episode type (impulse-arrival) than a real event (hover/retest of adjacent structure). | EURUSD `line1_cluster`, frozen tables: real P(bounce\|res)=0.651 vs control 0.693 → D≈−4.2pp pooled (−5.55pp top tercile). The gap could come entirely from episode-type selection, not "zone vs level". Same asymmetry predicts D_cont>0 (post-impulse continuation): observed +21…+29pp. | Measured from frozen CSVs, no regeneration: script "B4/B6" in §3 (distR/distC, per-gen P(bounce\|res)); RESULTS.md:67-80 post-run diagnostic reports the same in pips (3.78 vs 29.76). |
| F2 | **MAJOR** | `lib/pa_eval.py:86` + `lib/pa_metrics.py:49-51` | The "no-bypass" eval-token mechanism is bypassable twice: `_enter_eval`/`_mint_token` are module-level names, and `register_token_checker` is public — either route yields `pa_metrics.compute` metrics with NO ledger append. | `pa_eval._enter_eval(); t=pa_eval._mint_token("DESIGN"); pa_eval._leave_eval(); pa_metrics.compute([], t)` → returns a metrics block (verified). `pa_metrics.register_token_checker(lambda o: True); pa_metrics.compute([], object())` → metrics (verified). | Both run in battery A2, §3 — fresh process, no files written. (Not on the R01 outcome path: physics never imports pa_eval/pa_metrics.) |
| F3 | MINOR | `struct/zones/refs.py:59-67` | `pdh/pdl/pdc` are written only at the day-rollover bar — no carry-forward (unlike `wk_*` L93-95 and `asia_*` L109-116 which carry). `levels_at`/`confluence`/`ref_inside` see daily refs on **141/40000 bars (0.35%)** instead of ~39,737. | Any non-rollover bar: `levels_at(t)` omits the previous day's H/L/C → `T_ref` understated; **33.9%** of EURUSD in-slice events would gain ≥1 ref hit under correct carry-forward (mean Δn_ref=0.348 → strength shift ≈ +0.009 concentrated on a third of events → tercile-boundary shuffling, unsystematic sign). `contam_ref` understated → S-CLEAN keeps some truly contaminated controls. `ref_levels` zones unaffected (publish happens at the same rollover bar). | Battery B1 + T_ref recount (§3). |
| F4 | MINOR | `research/physics/phys_stats.py:184-187` | `years_4of6` and `symbols_3of4` contain lenient "all-of-3" fallbacks: `years_4of6 = (n_yr_pos>=4 and n_yr>=6) or (n_yr==3 and n_yr_pos>=3)` — weaker than the charter's ≥4/6 rule. | Synthetic: 3 observed years, all positive → `years_4of6=True`, gate PASS — a 3-of-3 pass the spec forbids. In the frozen run n_yr=6 and all year signs ≤0 (worst +1/6): the clause never fired and could not have flipped any verdict. | Battery A4 (§3). |
| F5 | MINOR | `research/physics/phys_analysis.py:56-59` | `_freeze_ok` checks existence only; the docstring claims it "refuses to run unless FREEZE.json exists and is older than the CSV tables" — the ordering guard is absent. | A future resolve-after-table-regeneration with a stale FREEZE would not be stopped. No actual violation this run: FREEZE 15:35:55Z < first OUTCOME 15:36:03Z < STATS 15:37:09Z (mtimes verified). | Code read + mtimes (§3). |
| F6 | MINOR | `PHYSICS_PREREG.md:105-107` vs `PHYSICS_PREREG_DRAFT.md` §3.2 | Frozen §3.2 silently rewrote freshness to the strict-window rule the code already had (`ins[w0:k].any()` → reject, `phys_extract.py:92`); the draft's ordered scan (accept at first away bar) would accept materially more events. | Inside-touch at t−20, ≥1 ATR-away bar at t−15, re-touch at t: ordered→ACCEPT, frozen→REJECT. Measured on EURUSD `line1_cluster` 40k-bar slice: ordered 1914 vs strict 1343 candidates — **+42.5%** population the draft would have yielded. Frozen spec is binding and code is faithful to it, but the tightening is undeclared in §0 and shrank the event population ~30%. | Battery B3 (§3). |
| F7 | MINOR | `PHYSICS_PREREG.md:131-133` → `PHYSICS_RESULTS.md` | Prereg requires "raw shares with NONE in the denominator … reported side by side"; RESULTS prints only conditional proportions (raw shares not shown anywhere). | Raw shares computed from frozen tables (B4): e.g. `line1_cluster` P(bounce\|all)=0.470 vs 0.539 — the raw gap (−6.9pp) is *larger* than the conditional one (−4.2pp): conditioning on resolution slightly MASKS the negative D (real NONE 22–28% vs control 18–25%). The bias direction is favorable-to-zones, not adverse. | Battery B4 (§3). |
| F8 | INFO | `lib/` bundle | `pa_fill.py` modified 22:52:27 local (15:52:27Z) — after the freeze and after REVIEW_R01_PHYSICS's hash check: current `pa_ledger.code_sha256()` = `9427a816…` ≠ frozen `afa4ac30…`. | Recompute lib hash now → mismatch vs FREEZE.json/ledger `code_sha256`. Harmless to the frozen numbers (physics never calls pa_fill; tables/results precede the edit) but future integrity audits will flag it; post-freeze edits to bundle-covered files should bump or quarantine the bundle hash. | `pa_ledger.code_sha256()` vs FREEZE.json (§3). |
| F9 | INFO | `lib/pa_ledger.py:170-197` | `verify()` detects any mid-file edit (flags the NEXT line) but cannot detect an edit to the LAST line (nothing references its hash). | In-memory replica of verify()'s algorithm: tamper line 5 → flagged at 6; tamper last line → (True, None). | Battery A3 (§3). |
| F10 | INFO | `research/physics/run_counts.py:126-128` | Calls `extract_controls` with the pre-Addendum-2 signature → TypeError if run. Not on the outcome path (outcomes came from `run_bakeoff.py`). | `python run_counts.py --controls-for …` → TypeError. | Signature comparison (not run). |
| F11 | INFO | `research/physics/phys_analysis.py:227` + RESULTS col "K̄ (ctrl/ev)" | `mean_k = n_ctrl / n_resolved` (all drawn controls ÷ *resolved real* events) — can exceed K=5 (`sd_base` 45284/7450 = **6.08**); column header misleads. | sd_base row shows K̄=6.08 though the sampler emits ≤5 controls per event. | Battery A5 (§3). |

## 3. What was checked and found CLEAN — with the measurements

All in one python process per battery, `OMP_NUM_THREADS=4`, `python -B -` (stdin,
no files created), DESIGN split only, EURUSD first 40,000 M5 bars (~142 days
2016) for data checks; frozen CSVs read, never regenerated.

**A. Seal / token / ledger / gate (no data)**
- `pa_sealed.assert_allowed` for CONFIRM / PROBE / OOS / "2010-2015" →
  `SealedSplitError` each; DESIGN allowed. `pa_data.load_m1("EURUSD", split="CONFIRM")`
  → `SealedSplitError` (assert fires before any parquet read). CLEAN.
- `pa_metrics.compute([], None)` → `EvalTokenError` (gate works for the honest
  caller). Two bypasses DO work — finding F2.
- `pa_ledger.verify()` → `(True, None)`; 27 lines; exactly 6 `R01 PHYSICS`
  trials `T000022…T000027`. Tamper replica: mid-file edit flagged at next line;
  last-line edit undetectable (F9). CLEAN-with-caveat.
- `gate_verdict` arithmetic: n_yr==3 fallback demonstrated (F4); could not have
  fired in this run (all year-signs ≤0, n_yr=6). CLEAN for this result.

**B. Causality / look-ahead**
- Prefix-invariance on real EURUSD (40,000 vs 30,000 M5): event tables
  identical for `line1_cluster` (528/528), `fractal_h1` (348/348),
  `ref_levels` (330/330) on bar_idx<29,000; live-zone band sets at bar 29,999
  identical. Command shape: `load_ctx("EURUSD", max_bars=N)` →
  `GenSource(name, registry.get(name), ctx).run()` → `extract_events(src)` →
  compare keys `(bar_idx,zid,side,near,far,strength)`. CLEAN (extends the
  existing `tests/test_real_prefix.py` which covered only line1_cluster).
- Extractor reads only idx≤t features (`phys_extract.py:77-110`); freshness
  window `[t-24,t-1]`; side rule from `c[t-1]` vs band at t; outcomes start
  `j0=t+1` (`phys_resolve.py:57`); adverse-first tie order verified
  (break>bounce, return>cont). Control forward-scan `[t,t+1440]` is the
  declared fake-event construction; CONTROLS carry no real outcome fields.
  CLEAN.
- Strength terciles are pre-registered constants in FREEZE.json
  (`generators.*.tercile_bounds`), computed before outcome joins per prereg.
  CLEAN.

**C. Prereg consistency (frozen doc is binding)**
- Event rule, barriers `m=1.0×ATR(t)` frozen at event bar, 48-bar window,
  adverse-first ties, K=5 with only-Z exclusion, per-event seeded RNG
  `default_rng([20260920, sym_ord, t])`, armed population via
  `armed_ids_from(active_at_fast(t))` — all match frozen `PHYSICS_PREREG.md`.
  Divergences found are draft→frozen spec changes (F6), not code deviations.
  CLEAN (vs frozen spec).
- Freeze ordering: FREEZE.json mtime 15:35:55Z < first OUTCOME csv 15:36:03Z <
  STATS.json 15:37:09Z < PHYSICS_RESULTS.md 16:02:14Z. Spot-checked 3 table
  hashes vs FREEZE.json `tables` → MATCH (all 48 verified by the other review).
  CLEAN.

**D. The attack on the negative D (frozen tables only)**

| candidate | present? | expected sign | measured size | verdict |
|---|---|---|---|---|
| position-in-range (real zones at 5-day-range edges vs controls mid-range) | NO — both sit mid-range | would be −D if true | band-mid position in R5: real mean 0.46–0.51 vs control 0.48–0.53 (in-slice) | **rejected** by B5 |
| approach-distance / episode-type (real ~at price vs control reached after ≥1 ATR impulse) | YES | −D on bounce, +D on continuation — matches BOTH endpoints | distR median 0.28–0.34 ATR vs distC 2.11–2.37 ATR; P(bounce\|res) gap −2.6…−4.8pp per gen; flat across control-distance deciles (0.68±0.005) → contrast is real-vs-any-control, not distance within controls | **dominant explanation (F1)** |
| barrier asymmetry (touch vs close-through; m=A(t) vs A(t_k)) | present, symmetric | cancels in D | same construction both sides; w copied in price units | minor |
| t_k drift (median 129–169 bars ≈ 11–14h) | present | adds episode noise; S-NEAR (tk≤288) more negative (−14…−18pp) is consistent with stronger-impulse episodes | measured tk_med per gen | symptom of F1 |
| selection on resolution | present, benign direction | could bias either way | real NONE 22–28% vs control 18–25%; raw gap ≥ conditional gap → conditioning slightly masks the negative D | measured, not the driver |
| pdh carry-forward (F3) | present | unsystematic | 0.35% of bars see daily refs; 33.9% of events would gain ref hits; ΔS ≈ +0.009 mean | cannot explain −6pp |
| n_yr==3 clause (F4) | present | — | inert this run | inert |
| control contamination (fake band = real structure) | present | biases D toward 0 only (declared) | contam_zone 11–63%, contam_ref 19–36% (understated per F3) | attenuates, cannot create −D |

**Mechanism (ranked):** the real-vs-control gap is almost entirely an
episode-type contrast built into Addendum 2's control: a control event requires
price to travel ≥1 ATR to a band price had not recently touched (arrival after
an impulse → post-arrival pullback touches the "bounce" barrier more often; and
post-break continuation rides the impulse → the huge +21…29pp D_cont). A real
event fires while price hovers at/retests an adjacent zone (congestion → more
NONE, more drift-through "break" closes, more post-break returns). Position in
the 5-day range is NOT the driver (B5); conditioning on resolution is NOT the
driver (raw gap ≥ conditional gap, B4/F7); distance among controls is NOT the
driver (B6 flat). The confound is the real-vs-control approach-distance
asymmetry itself.

## 4. Recommendation to the Lead (one line)

**Stand, but change the interpretation — do NOT re-run R01 under this spec:**
the frozen FAIL is a faithful answer to the preregistered estimand, but the
estimand's control is confounded by approach distance (F1), so "no measurable
edge over arbitrary levels" cannot be read as evidence against zone physics;
settle it with a distance-matched control (fake band placed at the same
distance/offset as the real zone) under a new preregistration (R02), and fix
F2/F3/F4/F5 before that freeze.

## 5. Open questions for the Lead

1. R02 control design: distance-matched band (same distance from c[t−1] as the
   real zone's near edge, arbitrary price level, same side) — agree this is the
   decisive variant? A cheaper complementary read: re-bin existing controls by
   episode type (post-impulse vs hover) — but the frozen tables cannot separate
   real events that way without a new event feature; a new draw is cleaner.
2. Was the draft→frozen §3.2 freshness rewrite deliberate? If yes, the §0
   deviations list should have carried it (it halved-to-thirded the event
   population vs the draft semantics, F6).
3. What changed in `pa_fill.py` at 15:52:27Z (F8)? Post-freeze edits inside a
   frozen bundle make later hash recomputation diverge — quarantine policy?
4. R02 fix list — confirm scope: `refs.py` carry-forward (F3), `gate_verdict`
   3-of-3 fallbacks (F4), `_freeze_ok` ordering guard (F5), token-gate bypasses
   (F2 — e.g. drop public `register_token_checker`, hide mint/enter behind a
   package-private closure or a context manager).
5. S-NEAR (−14…−18pp) is the better time-matched view and is MORE negative —
   consistent with F1 (stronger-impulse episodes). Does the Lead want it cited
   as supporting evidence in the R02 prereg?
