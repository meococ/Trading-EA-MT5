# PA-PRO — ROUND 00 REPORT (foundation)

Round: R00 (foundation) · 2026-09-20 · Orchestrator: OpenCode worker (DeepSeek) · Owner: Mèo Cọc · Lead: Claude.
Charter: `PA_PRO_CHARTER.md` SHA256 `3C57536848A4AA6113950D06D50331B8C664E18B79D34E08DEF2F1019BC5DC2C` (verified).
Addendum 1: `docs/CHARTER_ADDENDUM_1.md` SHA256 `37756D6922C7134901E94940A10E03EF4E11F7B72418F754D2CEFFE525D38592`.

**Scope executed: foundation only. No strategy was screened; the only economic run is the mandatory
DR3 regression, which reproduces a known kill. Round 01 has NOT been started.**

---

## 1. What exists after R00

| deliverable | path | state |
|---|---|---|
| Referee (11 modules) | `lib/pa_clock.py`, `pa_data.py`, `pa_sealed.py`, `pa_costs.py`, `pa_fill.py`, `pa_random.py`, `pa_metrics.py`, `pa_stats.py`, `pa_ledger.py`, `pa_slots.py`, `pa_eval.py` | DONE, frozen hash below |
| Referee tests | `tests/` (11 files) | 42 passed (verbatim §3) |
| Trial ledger | `ledger/TRIALS.jsonl` (21 lines, hash-chained) | chain `verify() == (True, None)` |
| Mandatory regression | `rounds/R00/regression_dr3.py`, `rounds/R00/REGRESSION_DR3.md` | reproduces ECON-1 exactly |
| Data inventory | `docs/DATA_INVENTORY.md` (+ `docs/_data_inventory/*.json`, scanner/renderer) | 7 symbols 2010-2026 |
| Cost inventory | `docs/COSTS.md` | c_rt + feasibility, file:line provenance |
| Hypothesis bank | `bank/HYPOTHESIS_BANK.md` | 14 families PAF-01..PAF-14, 18 refused, R01 shortlist |
| Perception spec | `struct/PERCEPTION_SPEC.md` (+ `struct/LEAD_REVIEW_LINE1_V0.md`) | v0 draft, object/event map + lags + score v0 |
| Physics prereg | `rounds/R01/PHYSICS_PREREG_DRAFT.md` | DRAFT (frozen in R01) |
| Zone-first build (ZONE-1 job) | `struct/zones/` (common, refs, registry, line1_cluster_zones, tests), `research/zones/_survey_*.md`, `_legacy_kills.md` | in progress by the ZONE-1 job; `SHORTLIST.md` not yet on disk |
| Review | `rounds/R00/REVIEW_R00.md` | round 1 FAIL (E1 MAJOR); fixes applied; round 2 appended |
| Provenance | `docs/PROVENANCE.md` | frozen sources + R00 freeze + no-copy note |

Referee freeze hash (`pa_ledger.code_sha256()` over `lib/*.py`):
`afa4ac305f19cc7aa4daf2acdc70b5e64686e91a6bf3bcc0fc530141120ef87f`

---

## 2. Referee — what it enforces (charter §6)

- ONE entry point `pa_eval.evaluate(spec, split, symbols, tf, cost_tiers)`; it appends to the ledger
  on normal return, empty result and exception (status `ERROR` then re-raise). No other path produces
  economic numbers: `pa_metrics.compute`, `_metrics_of` and `_agg` all require a token minted only
  inside `evaluate`; `_metrics_of`/`_agg` are out of `__all__`.
- Orders/fills: stop / limit / market-next-open, expiry in bars, session-end cancel, gap-aware fill,
  pre-fill invalidation cancel, cost applied once as an adverse fill shift, SL-first on ambiguous M1,
  daily 22:00 / weekend / server-midnight flats, no weekend hold. `legacy_flats` reproduces the frozen
  ECON-1 Thursday quirk for the regression; the default is the corrected calendar.
- Matched random: cells (session, hour, weekday, month), K=20, direction mix, seeded; bit-identical to
  the frozen matcher (tested on real DESIGN bars).
- Sealed guard: any split outside DESIGN refuses without `UNSEAL/<cand_id>__<split>.json`; 30-day
  warm-up rule for indicators; sealed reads are ledger-logged.
- Ledger: append-only JSONL, `prev_line_sha256` chain over raw line bytes, lock + fsync; tampering a
  middle line is detected at the following line.
- CPU slots: 2 file-locked slots with PID + 6h stale reclaim, threads 4, BelowNormal; other agents'
  processes (`dukascopy_bi5.py`, `lines1_run.py`, `ops.live.run_paper`) are not counted.
- Stats: seeded percentile bootstrap, BH-FDR, Deflated Sharpe (Bailey & López de Prado 2014) with the
  program trial count read from the ledger.

---

## 3. Test results (verbatim)

Command (final, after the review fixes):

```
python -m pytest tests -q
..........................................                               [100%]
42 passed in 4.61s
```

Round-1 reviewer mutation matrix (independent): 11/11 previously caught mutations still caught;
the 5 previously **uncaught** behaviours are now locked by new tests and each new test FAILS under the
reviewer's mutation (`rounds/R00/_review/fixcheck/fixcheck_mutations.py`, verbatim):

```
CAUGHT      resample_incomplete_ok
CAUGHT      design_split_extended
CAUGHT      warmup_flag_min
CAUGHT      fill_warmup_guard_off
CAUGHT      metrics_dd_linear
```

E1 bypass attempt after the fix (verbatim):

```
_metrics_of -> EvalTokenError: pa_metrics economic aggregation requires an evaluation token minted by
_agg -> EvalTokenError: pa_metrics economic aggregation requires an evaluation token minted by
__all__: ['EvalTokenError', 'register_token_checker', 'compute', 'newcombe_diff']
```

---

## 4. Mandatory regression — frozen DR3 through the referee (DESIGN, EURUSD M5)

Run on the frozen `lib/` hash `afa4ac30…` (trials T000012..T000021; 56.8 s):

```
tier        N      WR     PF      b     expR      Rtot  maxDD% |     rN     rWR    rPF  lift pp               CI
gross    2436 0.3498  0.992  1.842  -0.0051    -12.37   38.96 |  42257 0.3456  0.971    +0.44 [-1.49,+2.41]
x1       2436 0.3017  0.795  1.839  -0.1385   -337.49   84.19 |  42257 0.2994  0.783    +0.24 [-1.61,+2.14]
x1.5     2436 0.2837  0.720  1.819  -0.1950   -474.90   91.81 |  42257 0.2758  0.695    +0.83 [-0.98,+2.70]
x2       2436 0.2697  0.667  1.807  -0.2373   -578.05   95.03 |  42257 0.2552  0.625    +1.49 [-0.29,+3.34]
```

| metric (x1) | ECON-1 | ours | match |
|---|---|---|---|
| N fills | 2436 | 2436 | YES |
| WR | 30.17% | 30.1724% | YES |
| PF | 0.795 | 0.795195 | YES |
| b | 1.839 | 1.83923 | YES |
| exp R | -0.1385 | -0.138542 | YES |
| total R | -337.5 | -337.487 | YES |
| max DD | 84.19% | 84.1919% | YES |
| exit mix TP/SL/DAILY/FRIDAY/MIDNIGHT/DATA_END | 617/1618/139/61/1/0 | identical | YES |
| status counts | {CANCELLED 165, EXPIRED 1708, FILLED 2436, VETO_FRIDAY 22} | identical | YES |

Random x1: N 42257, WR 29.94%, PF 0.783, lift +0.24pp CI [-1.61,+2.14] — exact.
Corrected Friday policy (new semantics, informational): 2440 fills, WR 30.82%, PF 0.815, lift +0.76pp
CI [-1.10,+2.67]. Differences are itemised in `REGRESSION_DR3.md` §4.

---

## 5. Data & cost inventory highlights (7 symbols, 2010-2026, cache READ-ONLY)

| symbol | M1 bars | suspect % | ATR14(H1) med | ATR14(M15) med | c_rt x1 (pips) | source | 10xc_rt vs ATR14(H1): share of H1 bars covering the guard |
|---|---|---|---|---|---|---|---|
| EURUSD | 6,200,976 | 1.11% | 15.40 p | 7.23 p | 1.0 | measured | 87.9% |
| GBPUSD | 6,201,227 | 1.11% | 19.40 p | 9.18 p | 1.1 | measured | 97.2% |
| USDJPY | 6,200,596 | 1.11% | 15.81 p | 7.35 p | 1.4 | measured | 59.8% |
| AUDUSD | 6,199,005 | 1.11% | 13.72 p | 6.56 p | 1.4 | **proxy** | 47.9% |
| USDCAD | 6,195,950 | 1.10% | 15.25 p | 7.05 p | 1.4 | **proxy** | 59.6% |
| USDCHF | 6,193,336 | 1.10% | 12.80 p | 6.11 p | 1.1 | measured | 67.1% |
| NZDUSD | 6,192,049 | 1.11% | 13.13 p | 6.29 p | 1.4 | **proxy** | 43.6% |

- Measured c_rt provenance: `EA_VolmanPA/PLAN/COST_FEASIBILITY.md:75-78` +
  `vpa_random_baseline.py:41`. AUDUSD/USDCAD/NZDUSD: repo-wide evidence search documented in
  `docs/COSTS.md:254-308` — no measured all-in c_rt exists, all three marked **1.4 proxy** (charter
  §3 fallback). Per-year tables: `docs/COSTS.md:94-253`; per-symbol detail: `DATA_INVENTORY.md`.
- Gaps > 1 day: 884-885 per symbol, dominated by weekend breaks; largest are Christmas/New Year.
- Measured fact affecting D1: the server day's M1 grid is 00:16..23:59 (minutes 00:00-00:15 are a
  daily gap), so strict D1 completeness (1440 M1) yields 0 bars; `pa_data.resample` needs an explicit
  `min_src` override for D1 context (open issue §8).

---

## 6. Hypothesis bank — R01 shortlist (ranked; full grids in the bank)

| rank | family | one-line why | physics dep. | key risk |
|---|---|---|---|---|
| 1 | PAF-02 break-close + role-flip retest | retest entry avoids breakout adverse fill; Osler 2000 grounding; natural >= 2R room | MED | zone supply per symbol |
| 2 | PAF-01 pattern break at strong zones + buildup | strongest book+order-flow mechanism; DR3 referee calibration exists | HIGH | DR3 shadow if zone score weak |
| 3 | PAF-07 HTF zone + LTF trigger | best cost geometry (b >= 3); uses the highest-quality L1 object | HIGH | HTF zone supply / cadence |
| 4 | PAF-10 TFF at EMA25 (first failed counter-break) | novel trapped-cohort trigger, cheap, no legacy shadow | LOW | overlap with PAF-03/05 |
| 5 | PAF-03 failed break / reclaim at strong zones | direct Osler cascade test; tercile discriminator | HIGH | fade class worst prior |
| 6 | PAF-11 trendline break + first pullback hold | new L1 object, no legacy shadow | MED | confirmation lag |
| 7 | PAF-08 double top/bottom neckline break/retest | classical, measured-move geometry | HIGH | literature anchor thin |
| 8 | PAF-05 trend pullback to structure + Volman trigger | seed; must beat dead bare-pullback class | MED | anchor discipline |

Deferred: PAF-04 (box fade), PAF-06 (compression - NR4 shadow, delta tightened by review), PAF-09
(Asia retest), PAF-12 (round continuation - explicit refusal shadow), PAF-13 (raw PDH/PDL shadow),
PAF-14 (stop guard may starve cadence). 18 refused rows in `bank/HYPOTHESIS_BANK.md:1035-1057`.

---

## 7. Perception / physics prereg status

- `struct/PERCEPTION_SPEC.md`: 15 charter L1 objects -> 3 EXISTS / 7 PARTIAL / 5 MISSING; 12 events ->
  0 EXISTS / 5 PARTIAL / 7 MISSING, with per-object confirmation-lag table and a frozen strength v0:
  `S = 100*[0.30*min(1,T/4) + 0.20*min(1,Resp/3) + 0.15*exp(-dt/288) + 0.10*min(1,age/288) +
  0.10*scale + 0.05*role + 0.05*min(1,(n_ref+n_round)/2) + 0.05*min(1,tv6/tv288)]`.
- Binding supersession by Addendum 1 (zone-first, widths 0.2-0.6 x ATR14(H1), trendline bands
  secondary, 4-6 armed zones, bake-off) is recorded at the top of the spec.
- Known LINE-1 defect: `LineEngine._htf_align` look-ahead — being fixed in LINE-1's own session;
  PA-PRO must copy the FIXED revision, re-pin SHAs at freeze and add a score prefix-invariance test
  (note in `PERCEPTION_SPEC.md` §1). The file changed again after the re-pin
  (SHA256 `519A8C5A…` observed 2026-09-20 21:05 local).
- `rounds/R01/PHYSICS_PREREG_DRAFT.md`: exact FRESH-approach event, BOUNCE/BREAK/NONE + continuation
  analogue, K=5 fake-zone controls with sampler + seed policy, strata, Wilson/bootstrap CIs, the
  LINES-MATTER gate (+5pp, CI lower > 0, monotone, >= 3/4 core symbols, >= 4/6 years), and the
  viability arithmetic `required bias = c_rt/(2m) + 2pp` per symbol (EURUSD 5.25pp ... NZDUSD 7.33pp).
  No outcomes were computed.

---

## 8. Review, fixes and open issues

Round-1 review (`rounds/R00/REVIEW_R00.md`, sub-agent E, `VERDICT: FAIL`): 1 MAJOR + 5 MINOR + 5 INFO.
Closed:
- **E1 MAJOR (no-bypass)**: `_metrics_of`/`_agg` are out of `__all__` and token-gated; bypass raises;
  tests added. Verified above.
- **E2 MINOR**: 5 uncaught behaviours locked by `tests/test_data_completeness.py`,
  `test_sealed_bounds.py`, `test_fill_warmup.py`, `test_metrics_dd.py`; each fails under its mutation.
- **E3 MINOR**: `PERCEPTION_SPEC.md` LINE-1 SHAs/line numbers re-pinned + `_htf_align` defect note.
- **E4/E5/E6 MINOR**: bank R18 out-of-range citation replaced; false "COSTS.md does not exist" claim
  fixed; R5/PAF-06 deltas tightened (NR4 already had H4 EMA50, so the delta is the scored
  structural boundary + structural stop, not "independent direction").
- **E11 INFO**: regression re-run on the frozen lib (`afa4ac30…`, T000012..T000021); pre-freeze lines
  kept per append-only policy and documented.
Decisions recorded: **E7 — EMA25 allowed as a logged extra feature** (charter names EMA20/50; must be
declared in the R01 prereg and logged in every evaluation's params). **Corrected Friday policy is the
default for all future rounds**; `legacy_flats` exists only for the regression. Provisional: D1
context uses `min_src=1424` (server trading day) until the Lead rules otherwise.

**Round-2 re-review (`REVIEW_R00.md` round-2 section, appended; final line `VERDICT: PASS`,
file SHA256 `ce35119811025ab6f4c9c7e4344af359d188e96d7994762e3a6f7aa05653db62`).** The reviewer
independently confirmed: E1 closed (bypass raises; `__all__` clean; star-import clean; only
`pa_metrics.py` changed in `lib/`, tests only added), all 5 previously-uncaught mutations now caught
for the right reason (`42 passed` unmutated), the regression intact and certified by the current code
hash `afa4ac30…` including the reviewer's own fresh re-run, and the corrected citations resolve.
Residuals: R2-a/R2-b (PERCEPTION_SPEC LINE-1 hash/line drift — fixed in this file after the review:
all four LINE-1 files' observed hashes listed, `_htf_align` note now cites both revisions) and
R2-c..R2-f (INFO: intentional FAIL/PASS first/last lines; R01 `struct/zones/*` work-in-progress;
`REGRESSION_DR3.md` §5 closure notes are manual annotations). No BLOCKER/MAJOR remains.

Open issues for the Lead:
1. `research/zones/SHORTLIST.md` (ZONE-1 job) is not on disk yet — the R01 bake-off candidate list
   depends on it.
2. LINE-1 `_htf_align` fix not yet confirmed on disk; the perception baseline must use the fixed
   revision (or PA-PRO re-implements the term causally).
3. AUDUSD/USDCAD/NZDUSD c_rt are **proxy 1.4**; `COST_FEASIBILITY.md:271-276` requires measured
   evidence before any promotion on those symbols.
4. D1 completeness convention (`min_src=1424` vs 1440) needs a Lead ruling before HTF context code.
5. The stray ledger line `T000001` (family `X`, developer smoke) inflates the DSR trial count by 1;
   kept per append-only policy.
6. Physics-prereg power floors (1,000 pooled events; 60 resolved breaks) were chosen without an event
   count measurement — the Lead may change them before the freeze.

---

## 9. Round-01 plan (ZONE BAKE-OFF per `docs/CHARTER_ADDENDUM_1.md`)

**R01 is not started.** Proposed plan, in order:

1. **Freeze inputs** (no CPU): copy the FIXED LINE-1 revision into `struct/line1_seed/`; re-pin every
   SHA in `PERCEPTION_SPEC.md` + `docs/PROVENANCE.md`; write `rounds/R01/FREEZE.json` (perception code
   SHA + prereg SHA) BEFORE any outcome. Include the ZONE-1 `struct/zones/common.py` contract and its
   prefix-invariance tests.
2. **Zone generator candidates** (build, light CPU): G0 = LINE-1 swing clusters converted to zones
   (baseline, `struct/zones/line1_cluster_zones.py`); G1..Gk = candidates from the ZONE-1
   `SHORTLIST.md` (best non-repainting indicators, algorithms re-implemented causally with
   attribution) + one PA-PRO swing-cluster generator (`struct/swings.py` -> `struct/zones.py`).
   Every generator registered in `struct/zones/registry.py` behind one interface (zones at bar t,
   causal, with touches/respected/break state and a strength score).
3. **Physics bake-off** (CPU-bound, DESIGN only, core symbols, M5): one `extract -> resolve` pass per
   (generator, symbol); K=5 fake controls; strata + Wilson/bootstrap CIs; BH-FDR across candidates;
   pre-declared winner rule from the prereg (top-tercile lift CI lower > 0, monotone, >= 3/4 symbols,
   >= 4/6 years); one ledger trial per candidate. Estimated **120-180 CPU-min** (4 symbols x 4-6
   generators x ~3 min extraction + ~2 min resolution), chunked inside `pa_slots`.
4. **Family screens** (only after the physics verdict): run the ranked shortlist (<= 8 families, each
   with its pre-declared <= 24-config grid, M5/M15 on core symbols) through `pa_eval.evaluate`;
   physics-gated families (PAF-01/03/07/08) go first if LINES MATTER passes; if it FAILs, R01 pivots
   to the MED/LOW-physics families (PAF-02/10/11/14) per the bank's cross-cutting note.
   Measured anchor: the DR3 regression cost 14.8 s for 4 tiers with 87k entries on EURUSD (2.2M M1
   bars), so a config x 4 symbols x 4 tiers is ~1-4 min. Full 8 x 24 grid would be ~6-8 CPU-hours;
   propose staging to **3-4 CPU-hours** in R01 (top 4 families first, budget stop at 24 configs per
   family across <= 2 market-logic revisions).
5. **Judge + review**: BH-FDR within the round, Deflated Sharpe with the program trial count, equity
   audits on any pass, then one neutral adversarial reviewer; `rounds/R01/ROUND_REPORT.md` +
   `LEADERBOARD.md` update.

Total R01 estimate: **~5-7 CPU-hours** of our python, in 2 slots, plus build time.

---

## 10. Provenance of this round

Every frozen source reused is listed with its SHA256 in `docs/PROVENANCE.md`; no frozen file was
copied into `PA_Pro/` in R00. All writes stayed under `03. EA Developer/PA_Pro/`; no git commit, no
worktree, no MT5/terminal action, no trading tool, no OCR, no ML training. Machine rules followed:
our heavy python <= 2 processes, threads 4, BelowNormal, one heavy process at a time in the foreground.
