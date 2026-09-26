# REVIEW.md - neutral audit + fixes (SonicR_Lab round 2)

Reviewer: fresh-context read-only subagent (agent 62ebf4b1), full
checklist (a)-(f) from the brief. Its raw findings are embedded below;
the "DISPOSITION" column records what the lane did about each item.
Verdict by reviewer: **CONDITIONAL PASS** (no lookahead found anywhere;
one MAJOR simulator bug + one MAJOR governance gap had to be closed).
Both MAJORs are now CLOSED; DESIGN + controls were rerun after the fix.

## Checklist verdicts

| item | verdict | note |
|------|---------|------|
| (a) look-ahead, all components + sim | PASS w/ findings | no lookahead found; A1 MAJOR fixed |
| (b) cost model vs audit | PASS | EUR 1.0p / XAU 5.5p RT exact vs DATA.md |
| (c) PARITY_J | PARTIAL PASS (honest) | amended criterion documented |
| (d) HOLDOUT never loaded | PASS | verified below |
| (e) PREREG hash + registry | PASS | verified below |
| (f) 5 trades hand-recomputed | PASS | 15/15 fresh-path replays exact |

## (a) Look-ahead audit - verified causal

Reviewer verified with file:line (abbreviated): fractal-2 `conf=idx+2`,
`usable()` gates `conf<=t` (swings.py:35,93-105); zigzag emits only on
1.5xATR close-through, trailing extreme excluded (swings.py:73-88);
zones advance only `conf<=t`, death scan bars `<=t` via sparse tables
(zones.py:112-127,157-159); EMA/ATR/PVA strictly trailing, PVA prior-10
(indicators.py, pva.py:32-41); wave legs confirmed-only (wave.py:28-43,
55-71); sim fills only after signal close, gap-aware, SL-first, TTL
exclusive, busy_until off-by-one correct (sim.py:54-152); Friday flatten
exact 20:00 London on 3 sampled exits; F3 uses closed H1 only
(other.py:99-100); prior_break/thru scan only bars <t (wave.py:74-79).

## Findings + dispositions

| # | sev | finding | DISPOSITION |
|---|-----|---------|-------------|
| A1 | MAJOR | Wrong-side SL admitted (`abs(entry-sl)<=0` guard only). `sl_big_swing` can return an extreme beyond entry on the wrong side. Evidence: trades_EURUSD_F2_NH_b.csv:1292 r_x1=-154.32 (risk 1e-6), trades_XAUUSD_F1_R1b.csv:623 r_x1=-14.47. Corrupts exp_r/maxdd/sharpe/MC-DD. | **FIXED** (sim.py:33-38,63-65): order-admission guard rejects `(entry-sl)*dir < MIN_RISK_PIPS*pip` (2 pips, mechanical floor) before the book check; `df.attrs["rejected"]` counts. Fleet count: 11 invalid orders total (EUR F2_NH_b 6+1 tiny, EUR R1b 2, XAU F2_NH_b 1, XAU R1b 1). DESIGN+controls rerun post-fix: F2_NH_b EUR n 1298->1291, exp_r +0.004->+0.132, maxdd 173.7->47.8R; PF 1.148 unchanged. Conclusion unchanged. |
| A2 | MINOR | `zones_at` is stateful; `pvsra_label` lookback j<t sees "zones known at t" not "at j". Affects F1_PV/FULL only (dead). | DOCUMENTED (LEAD_NOTE_4 already discloses; noted in LEAD_HANDOFF for the MQL5 port). No code change - configs dead anyway. |
| A3 | MINOR | `tp_j` checks nearest half-step only vs spec's apparent scan-forward reading. | DOCUMENTED here and in PARITY_J.md; PF parity reproduces within tolerance; sensitivity probe noted as round-3 check. |
| A4 | MINOR | Weekly cap = epoch-week (Thursday boundary) vs "ISO week" in prereg. | DOCUMENTED; impact trivial (cap 5 vs ~2/wk signals). |
| A5 | MINOR | `reentry_used` resets per week not per wave. | MOOT - F1_FULL_RE emits 0 signals. Documented. |
| A6 | NIT | TTL counts from signal bar (live on ttl-1 post-signal bars). | Consistent across all configs; documented. |
| A7 | NIT | vestigial allow_holdout param, dead helper, MFE/MAE include fill-bar pre-fill excursion. | allow_holdout kept (explicit seal flag semantics); MFE/MAE convention documented (mild both-ways bias, equal for all configs). |
| A8 | NIT | F2 stale-pullback semantics; F4 touched_* unbounded. | Documented semantics choices. |
| C1 | MAJOR | The prescribed 10-trade F0_J hand-check (LEAD_NOTE_2) was undocumented. | **CLOSED**: runs/handcheck.py replays orders on raw M1 via a FRESH code path: 10/10 F0_J + 5/5 F2_NH_b exact match (fill px, exit px, exit ctm, reason). Output in LAB_LOG + section (f) below. |
| C2 | MINOR | Amended parity criterion not recorded in PARITY_J/RESULTS errata. | FIXED: PARITY_J.md "Amended criterion" section; RESULTS.md errata. |
| C3 | MINOR | Interpretation B run vs LEAD_NOTE_2 "do not chase N". | Explained in PARITY_J.md: PREREG section 6 itself prescribed the probe; labeled inference; A kept as F0_J. |
| C4 | MINOR | git rev + run cost/tester-model not recorded. | FIXED: recorded as NOT recoverable in PARITY_J.md. |
| C5 | NIT | run_parity.py comment says 1789775940 = J end; it's COMMON_END. | Cosmetic; constant is correct (cap is COMMON_END); comment clarified below fix list. |
| G1 | MINOR | zones docstring stale; avail_idx/origin_idx/members fields absent; tie-zone count missing; availability unit test missing (LEAD_NOTE_3 addendum). | ALL FIXED: docstring rewritten, zone dict carries avail_idx/origin_idx/members, `test_zone_availability_at_second_member_conf` added (19/19 pass), `runs/count_flip_zones.py` counts mixed high+low clusters (result in RESULTS.md). |
| G2 | MINOR | Control (a) groups pool by (hour,dir) not weekday; dir resampled 50/50. | DOCUMENTED as deviation (accepted for round 2; noted for 2B). |
| G3 | MINOR | Bootstrap 2,000 draws vs preregistered 10,000. | DOCUMENTED in RESULTS (disclosed). |
| G4 | MINOR | order_cache silent reuse (stale-signal risk). | DOCUMENTED; sim-side fix required no regen; 2B census regenerates orders anyway. |
| G5 | MINOR | DATA.md stale window dates; heavy_run path; pos_years counts partial 2020; redundant CSV write. | DATA.md dates FIXED; others documented (2020 partial-year counting self-disclosed in RESULTS). |

## (b) Cost model

src/data.py COST == DATA.md == PREREG section: EURUSD 0.1p spread +
0.1p slip x2 + 0.7p comm = 1.0p RT; XAUUSD 2.0 + 1.4x2 + 0.7 = 5.5p RT.
Reviewer's provenance notes: audit shows real comm=0.00 (the 0.7p is a
deliberate conservative bound) and no measured XAU slippage behind 1.4p
- both lean CONSERVATIVE. PASS.

## (c) PARITY_J

Strict prereg N-band fails both interpretations; under the Lead-amended
criterion (LEAD_NOTE_2) PF 0.912 in [0.79,1.09] + density analysis +
10-trade hand-check -> PARTIAL PASS is honest. Amendment trail now in
PARITY_J.md.

## (d) HOLDOUT never loaded - verified (parent)

- `grep -rn allow_holdout src/ runs/`: only signatures/defaults, never
  `True`. `_check_holdout` (data.py:62-66) raises when
  `end_ctm > HOLDOUT_START=1684333392`; every ctx is built with
  `end=VALIDATION_END`; unit test `test_holdout_refused` covers it.
- No `val_*.csv` exists; `runs/selection.json` = empty (round 2).
- Reviewer's defense-in-depth suggestion (assert post-slice max) noted.

## (e) PREREG hash + registry - verified (parent)

`sha256(PREREG.md) = 94214bbfa768665e7741d2f79dd2e6ba54ddad3eee848ed1
ae9a080df473abb1` — identical to LAB_LOG 16:06Z entry and PREREG.sha256.
Registry = 17 configs <=22, field-matched vs PREREG section 5 by
reviewer. No config added after the hash (2B configs live in a SEPARATE
`registry_2b.py` under PREREG_V2, not touching round-2 table).

## (f) Hand recompute - 15 trades, fresh code path (parent)

runs/handcheck.py re-implements fill/exit resolution directly on the
lab-cache M1 parquet (not via sim.py): pending active at sig_ctm+900,
first-cross fill with gap model, SL-first scan, Friday flatten.

- 10/10 F0_J: fill/exit price exact (1e-9), exit time exact, reason
  exact (sl/tp).
- 5/5 F2_NH_b: exact, incl. one Friday `flat` exit.
- Fleet degenerate-SL count: 11 orders (all now rejected at admission).

## Fixes applied this review

1. sim.py: MIN_RISK_PIPS=2 admission guard + rejected counter (A1).
2. zones.py: avail_idx/origin_idx/members fields + corrected docstring.
3. tests: +test_zone_availability_at_second_member_conf (19/19 pass).
4. run_design.py: surfaces rejected count in summary.
5. PARITY_J.md: amended criterion + unrecoverable-rev note.
6. DATA.md: true window dates.
7. DESIGN summary + controls rerun post-fix (heavy lock); trades CSVs
   regenerated.

## Known-acceptable residuals (documented, not promoted)

tp_j nearest-vs-scan ambiguity; epoch-week cap; PVSRA zones-at-t
semantics; TTL-from-signal-bar; fill-bar MFE/MAE inclusion; 2000-draw
max-PF bootstrap; partial-2020 in pos_years. None change any verdict.


---

## Round-2 addendum review (A1, 23/09 19:5xZ)

Fresh neutral review of the corrected E1 diagnostic, dual-harness (H0/H1)
application, PREREG_V2 timing, W4d Q provenance, handchecks, holdout seal,
H1-definition timing and dual-harness selection lives in `REVIEW_v2.md`.

Verdict: PASS-WITH-NOTES - all 8 checks verified; minor prose/typo issues
fixed in RESULTS_v2.md (exit-ratio bound 6x-208x, F5_S3 pct 99/99, F2_NH_b
EUR pos-years 6-7/11, flat2350 attribution to F5_S3_EXT). Outcome
unchanged: empty selection, VALIDATION unread, HOLDOUT sealed.
