# SonicR_Lab — LAB_LOG (UTC)

- 2026-09-23T15:32Z START lane SONIC-LAB round 2. Created working folder. Phase A: reading specs.
- 2026-09-23T15:51Z Phase A read-through done: GOAL, DECISION_FRAMEWORK, cost audit, freeze doc, packet section 6 (object J), atlas S2-S10, BAO_CAO 3/6/7. Data inventory: lab cache M1 parquet EURUSD+XAUUSD 2010-2026 w/ suspect flags = canonical plane; FivePercent parquets deleted (manifest only); J run artifacts gone (window = documented assumption 2000-01-03..2026-08-14). MQ-Demo server tz verified = UTC+2/+3 US-DST. Cost model set (EUR ~1.0p RT, XAU ~5.5p RT). DATA.md written. Building harness skeleton next.
- 2026-09-23T16:05Z Harness built: data.py (lab-cache M1 + hcc pre-2010, holdout seal), components (indicators/dragon, pva, whq, swings fractal2+zigzag, zones, wave, pvsra, stops_targets, sessions), sim.py (M1-resolved pending-stop engine, SL-first, Friday flatten, cost tiers), variants (17 configs <=22), context+runner. pytest 18/18 PASS. Found+fixed: zigzag seeding, zone death side, dow off-by-one.
- 2026-09-23T16:06Z PREREG.md FROZEN sha256=94214bbfa768665e7741d2f79dd2e6ba54ddad3eee848ed1ae9a080df473abb1 (17 configs, windows DESIGN ->2020-01-13 / VALIDATION ->2023-05-17 / HOLDOUT sealed, XAU SL cap 212.2p). No P/L computed before this line. Next: J parity + census.
- 2026-09-23T16:16Z PARITY_J done: interp A (w2 telemetry) N=1441 PF=0.912; interp B (w2 gate) N=364 PF=0.863. Economics PASS both; N not reproducible (artifacts deleted, feed differs). PARTIAL PASS, ladder proceeds on frozen table. PARITY_J.md documents gap.
- 2026-09-23T16:45Z Census rerun in progress (fixed quadratic zone death-check -> O(1) sparse-table; ~4s/config/yr). DESIGN sim + controls scripts ready.
- 2026-09-23T17:54Z CENSUS done: J=2.0 sig/wk EUR; ladder kills W4a/W4b/PV (~0/wk), W2 -80%, W3 -58%; F2_NH ~7-8/wk, F3 ~15-21/wk, F4 ~17/wk. Orders cached to out/sigs (34 files). DESIGN done: best = F2_NH_b EUR PF1=1.147 PF15=1.123 (n=1298), XAU 1.053/0.988; F1_W4a PF 1.20-1.49 but ~0.04/wk dead; J families <1. Controls queued.
- 2026-09-23T18:47Z REVIEW fixes applied: sim.py order-admission guard (reject wrong-side/dust SL <2p, df.attrs rejected); zones.py avail_idx/origin_idx/members fields + docstring (LEAD_NOTE_3); new test test_zone_availability_at_second_member_conf (19/19 pass). Heavy rerun design+controls queued (nulls must regenerate - they reuse real SL geometry).
- 2026-09-23T18:51Z Review verify: PREREG sha256 unchanged (94214b..f473abb1); holdout seal intact (no allow_holdout=True anywhere); handcheck.py fresh-path replay: 10xF0_J + 5xF2_NH_b all OK (0 mismatches vs CSV). DESIGN post-fix: F2_NH_b EUR n=1291 rej=12 exp_r=+0.132 maxdd=47.8R (was 0.004/173.7 - the -154R phantom trade removed). Controls rerun in progress.
- 2026-09-23T19:01Z Lead brief 19:02Z received: errata E1-E3 + round 2B on corrected harness. Plan: wait running census job -> close round-2 docs -> E1 diagnostic (DATA.md) -> sim E1/E1b/E2 + pending_px + PF_R + sl_big_swing root fix -> rerun 17cfg -> 2B census/PREREG_V2/design/essence/controls -> selection+validation -> RESULTS_v2/docs.
- 2026-09-23T19:09Z Errata harness in place: sl_big_swing strict-side root fix (returns None when no confirmed extreme beyond pending_px; callers pass entry; sim admission guard kept as 2nd line; test_sl_big_swing_strict_side 200 trials PASS - 20/20 total). E1 diagnostic run: EUR roll-window suspect/clean median-range ratio 0.86, XAU 1.19 - BOTH < 2.0 -> E1 SKIPPED per Lead decision rule (table in DATA.md). E1b roll spread stress ON (EUR +2p 23:55-00:15, XAU +20p 00:55-01:20 server). E2 floor + pending_px + PF_R + daily-flat-2350 secondary wired. Heavy chain queued: run_design + census_finalize(+E2 counts) + run_census_2b(+E2 counts,Q).
- 2026-09-23T19:14:11Z PREREG_V2.md FROZEN sha256=3e92207100399e7662fa5691c174c163f5c73b34ea8a636839212c0e6feb9bd7 (mtime 2026-09-23T19:14:04Z). Contains LEAD_NOTE_4 hash b15654..f8906, E1-SKIPPED decision (EUR 0.86/XAU 1.19 < 2.0), E1b windows, E2 floor, E3 PF_R+pip-PF dual rule, Q_EUR=-0.0063401056 Q_XAU=-0.0053644141 from outcome-blind census, 8x2B configs, essence test, N=25x2 selection. NO 2B P/L exists yet - next: design_2b + essence + controls.
- 2026-09-23T19:32Z ADDENDUM A1 (Lead 19:17Z): E1 median test wrong - corrected diagnostic written to DATA.md: exits/1000min roll-vs-outside 19x-450x across all 25 cfgs; per-day max M1 range roll/quiet med ratio 30.9 (EUR) 37.9 (XAU), |o-c_prev| ratio med 71/69; jump-and-revert 25.7% EUR / 18.1% XAU of days. E1 APPLIED on validity grounds. H0=E1b+E2+E3 done for 17+8 cfgs; H1=H0+skip_suspect done (design+design_2b+essence_e1). 2B H1: XAU F5_S3 pf_r 1.64/pip 1.49 (0.15/wk), F5_S2 1.37/1.30 (0.51/wk), S3_EXT 1.59 (0.17/wk) - all fail cadence gate. Essence H1: spearman EUR p=.014 XAU p=.010 pooled p=.009. run_controls_h.py (dual-harness, tiered seeds) running under lock.
- 2026-09-23T19:33Z PREREG_V2 AMENDMENT A1 appended (frozen text untouched): dual-harness selection (pass on H0 AND H1, both metrics), controls tiered, validation on both, N=100 cells best-of-N. New file sha256=0226143d1e763a1955531c58d279fcfa51f6a721787d3c2185039a527735c7fd ; amendment-block sha256=983b55f075e5d991bbb91d879c64430f67ab4ee43b9c2f2504cdf880f47b6f27. Previous frozen hash 3e9220..9bd7 stands for the pre-amendment text.

[2026-09-23T19:49Z] count_flip_zones: EURUSD 7/5769, XAUUSD 26/5830 mixed
  high+low zones (sum(dir)=0). Rare; documented in RESULTS_v2 sec.8.
[2026-09-23T19:52Z] MC DD P95 + deflated Sharpe computed for top cells
  (F5_S3/S2 XAU, F2_NH_b EUR, F1_W3 EUR); file-time audit: A1 19:17Z <
  first _e1 P/L 19:30:56Z; PREREG_V2 freeze 19:14:04Z < first 2B P/L
  19:14:20Z (16s, ordering holds); amendment append 19:33Z.
[2026-09-23T19:55Z] RESULTS_v2.md completed (selection NONE, verdicts,
  next approaches). BAO_CAO_LAB.md Vietnamese section appended.

[2026-09-23T20:00Z] REVIEW_v2.md (fresh neutral sub-agent, 8-check list):
  PASS-WITH-NOTES. All numbers reproduce (F0_J 253.5 vs 2.14 exits/1kmin;
  ratios 30.9/37.9; J&R 25.7%/18.1%); PREREG_V2 hashes byte-exact
  (3e922071 orig / 0226143d file); freeze 19:14:04Z < first 2B P/L
  19:14:20Z; A1 19:17Z < first _e1 19:30:56Z; no allow_holdout anywhere;
  selection.json empty; handcheck rerun 30/30.
  Minor fixes applied to RESULTS_v2: ratio bound, F5_S3 pct, F2_NH_b
  pos-years, flat2350 attribution.
[2026-09-23T20:02Z] ROUND COMPLETE: selection EMPTY -> no VALIDATION,
  no MQL5. Deliverables: RESULTS_v2.md, BAO_CAO_LAB.md (VN section),
  LEAD_HANDOFF.md, REVIEW.md + REVIEW_v2.md, DATA.md corrected diag.

[2026-09-23T20:26:14Z] ROUND 2C start (Lead 20:20Z). data.py: BASKET 10 symbols, pip/
  point/cost per Lead table (rt decomposed as spread .1p + comm .7p +
  slip remainder). runner: sl_cap() generalized per-symbol same formula
  (XAUUSD identical). tests/test_holdout_guard.py: guard raises for all
  12 symbols past HOLDOUT_START - 3/3 pass.
  basket_check.py (outcome-blind): all 10 syms coverage=100% wk,
  suspect ~1.1%, roll win ~23:59-00:2x srv (GBPJPY/AUDJPY 00:00-00:16/17,
  95% cover), per-day max-range ratio med 19-28x, jump med 33-68x.
  Roll windows hardcoded into sim.ROLL; BASKET.md written. Census
  kicked (ctx builds ~10 syms). NO P/L yet.

[2026-09-23T20:33:45Z] PREREG_V3 FROZEN sha256=2f5232ebb29fa53d9b0e06bc8aaee0293c7357bd60197263a20e3f8faa91f77f - BEFORE any basket P/L.
  Census 2C done (outcome-blind): per-wk/symbol F0_J ~2.0, F2_NH_b ~6.9,
  F5_S2 ~0.7, F5_S3 ~0.16; basket sums ~20/69/7/1.7 per wk. Q(a20)
  recomputed per symbol (runs/q_w4d_2c.json). E2 removals small (0-14).
  whq.pip_size now reads data.PIP (KeyError fix on basket symbols -
  shared-code bug found, fixed, unit tests unaffected).

[2026-09-23T20:47:36Z] ROUND 2C complete. R1 essence FAIL (Stouffer p=.26 H0/.44 H1);
  R2 none pass (F2_NH_b pooled 1.049/1.063 < 1.10, 9/10 syms >1 H1);
  R3 F2_NH_b PASS pct=100 both harnesses; F0_J/F5 fail R2+R3.
  Portfolio capped: F2_NH_b 5.0 tr/wk PF_R 1.17 H0/1.11 H1, posY
  73%/64%, MC DD P95 59R/81R. Handcheck 2C: 18/18 OK 2 basket syms
  both harnesses. RESULTS_v3.md + VN section written.

[2026-09-23T20:57:15Z] REVIEW_v3.md: PASS-WITH-NOTES (6/6 checks). Fixed RESULTS_v3
  table cells (EURGBP F5 rows, AUDJPY col used pip-PF by mistake) +
  null-p95 wording. No verdict change. Round 2C closed.

[2026-09-23T21:26:03Z] ROUND 2D start (Lead 21:25Z). Step0 OK: 2C deliverables complete
  (RESULTS_v3/BAO section/REVIEW_v3 PASS-WITH-NOTES), untouched since.
  Step1 split verified vs Lead spec (rng 20260924) - printed into
  PREREG_V4. Step2 exit layer: src/exits.py (X0-X4, BE deferred to
  bar i+1, leg-A +1R no-gap-bonus, dragon on closed M15 close vs
  EMA34(L)/(H) with H1 last-M1-suspect skip, pessimistic same-bar col,
  E1/E1b/Friday/daily-flat parity). sim.py: exit_rule/tfx/pessimistic
  params; baseline path untouched when exit_rule=None.
  TESTS before freeze - ALL PASS:
    T1: 24/24 cells (12 syms x H0/H1 x fixed+free) X0 row-for-row 1e-9.
    T2: synthetic paths (be/-1R same-bar/X2 formula/E1b legA/short/pess) - pytest.
    T3: dragon no-lookahead (recompute M15+EMA after edits) - pytest.
    T4: X0 null new path == 2C null (GBPUSD seed0). T5: flat2350
    free-run reproduces col on AUDUSD+EURUSD H0/H1 (1e-9).
    Fill-window assert: no X0 fill in [23:50, roll end) on D -> DF never
    changes an entry. tests/ suite 32/32.
[2026-09-23T21:26:03Z] PREREG_V4 FROZEN sha256=1421a4f0ef39bac7ffe9e7e0de36f64a2a0d21426756defe427f1e779068d300
  - BEFORE any exit-variant P/L file. 10 configs (X0..X4 x HOLD/DF),
  fixed list primary / free running secondary, design rule + K1-K4 +
  validation rule verbatim, bootstrap week/2000/seed 20260924.

[2026-09-23T21:34:19Z] ROUND 2D DESIGN run done (D only, H1 then H0; fixed list +
  pessimistic + free running; 10 cfgs x 7 syms; ~6.1min heavy).
  DESIGN-STAGE RULE APPLIED -> NO CANDIDATE ELIGIBLE:
    need pooled PF_R x1>=1.10 on H0 AND H1, x1.5>=1.00 H1,
    mean dR>0 on both, pessimistic dR>0 on H1.
    Best case X0-DF: PF_R 1.2045 H0 / 1.0934 H1 (fails 1.10 H1),
    mean dR +0.0400 H0 / -0.0161 H1 (fails). X1-DF/X3-DF same pattern
    (H0 ~1.19-1.20 but H1 mean dR <0). All pessimistic dR <0 on H1.
    X1/X3/X4-HOLD lose heavily on H0 (-0.08..-0.23R): management
    triggers on fabricated +1R prints.
  Per frozen rule: round STOPS after design stage. C set stays UNREAD
  for every candidate (no C-variant file exists); no VALIDATION read;
  HOLDOUT sealed. Next: RESULTS_v4 + BAO section + neutral review.

[2026-09-23T21:42:36Z] ROUND 2D CLOSED. RESULTS_v4.md + BAO_CAO_LAB.md PHAN 4 written.
  REVIEW_v4.md: PASS-WITH-NOTES (8/8 checks) - prereg hash timing OK,
  T1 recomputed on 2 syms (<=1.5e-12), zero C-variant artifacts, T3
  recomputes indicators, handcheck 16/16, VALIDATION unread + HOLDOUT
  guard intact, reported PF_R cells match recompute. Transcription
  notes fixed (first-artifact mtime 21:27:41Z, sl_same row in mixes).
  No candidate advanced -> C untouched, VALIDATION sealed, HOLDOUT
  sealed. Round ends at design stage per frozen rule.

[2026-09-23T21:56:50Z] ROUND 2E start (Lead 22:15Z). src/trend.py: S_T = A1(M15 EMA34v89)
  + A2(H1 close vs EMA34H/L) + A3(H4 EMA89 vs j-6); usable-bar rule
  open+step<=sig_ctm+900; warm-up 3x period -> NA. tests/test_trend.py:
  T1 look-ahead (synthetic + real EURUSD, start/mid/end of H1&H4 +
  Monday open) + Sunday-stub checks - 4/4 pass. Data note: EURUSD has
  2 suspect-flagged 1-min Sunday stub bars (bogus prices), never
  selected as usable HTF bar by any trade (asserted).
  scores_2e run: labels only (no P/L) for 12 syms, join 0 unmatched;
  S_T dist ~30/22/26/20% for S=0..3, NA ~1.6%.
[2026-09-23T21:56:50Z] PREREG_V5 FROZEN sha256=430ac821bef5d0b5442c2188750906a0d4ee1df588a809b5dc0100c5c6df0bdb
  - BEFORE any file with P/L split by S_T. c in {2,3} via cutoff rule;
  E1-E5 design rule; K1-K4 confirm; validation rule; week-block
  bootstrap 2000/seed 20260924; regime null 1000 draws whole-week
  circular shifts.

[2026-09-23T22:01:34Z] DESIGN_2E done (74s heavy). DECISION: STOP after design stage -
  design rule failed on D; C stays unread, VALIDATION stays unread,
  no threshold relaxed.
  cutoff rule -> c=2 (c3 cadence H1=0.42<0.5 AND c3 pf H1 1.006<c2 1.077).
  E1 FAIL: b=-0.0068 (H1, lb95=-0.0389) / +0.0017 (H0, lb95=-0.0276);
    non-monotone: S_T=3 PF_R 1.006 < S_T=2 1.128 on H1.
  E2 FAIL: b>0 only on 3/7 symbols H1; long b=-0.024, 9/11 LOYO folds<0.
  E3 FAIL: kept pooled PF_R x1 = 1.060 H0 / 1.077 H1 (<1.15);
    x1.5 H1=1.010 (<1.05).
  E4 FAIL: regime null pct=43.4 (<95).
  E5 PASS: kept cadence c=2 = 0.99 trades/wk/sym H1.
  Components alone H1: A1 kept PF 1.088 vs rem 1.077 (+0.006 mean);
    A2 kept 1.048 vs rem 1.112 (-0.042); A3 kept 1.081 vs rem 1.082.
  Swap (kept, x1): see design_2e_summary.csv pf_r_x1_kept_swap.
  POWER NOTE (approx, analytic): b_D=-0.007 -> half=-0.003; with
    boot sd~0.019, P(K1 lb95>0)~3%; joint P(K1-K4) ~<1%. Moot: no C run.

[2026-09-23T22:12:28Z] REVIEW_v5 done: PASS-WITH-NOTES, 6/6 checks pass. Disclosures
  recorded by reviewer: (a) light_ctx/get_ctx load M1 through
  VALIDATION_END (same convention as 2D) - score is causal, DESIGN-only
  independent recompute matched 20/20; no validation-window information
  enters any statistic; (b) rng k range is [8, W-8) vs prereg [8,W-8] -
  immaterial at W~522; (c) trades_2c_* files verified identical to
  trades_2d_* X0-HOLD for the join. No VALIDATION unlock performed;
  HOLDOUT sealed.

[2026-09-23T22:33:49Z] ROUND 2F start (Lead 22:50Z). STEP1 DST fix: _last_sunday bug -
  when 1st of next month is Sunday it returned a date in the WRONG
  month (UK transition 1 week late): Mar 2012, Mar 2018, Oct 2015,
  Oct 2020(VALIDATION window). Fixed data.py; DATA.md Oct/Nov gap
  corrected -1h -> -3h. T0 tests/test_dst_fix.py 6/6 pass
  (hand-computed London hours 2012-03/2015-10/2018-03/2020-10, both
  US/UK gap directions, Friday-flatten bug-week check).
  regen_2f rerun X0-HOLD x12 syms x H0/H1 -> out/trades_2f_*_dstfix.csv.
  Before/after: max share changed 1.11% (EURUSD H1 13/1173) - marginally
  over the ~1% guard. VERIFIED benign: every changed row is inside a
  bug week (signal in/out of window, Friday-flatten +/-1h) or a
  one-position-book cascade (a flatten time shift frees/blocks the next
  signal - mathematically required by any correct fix). The earlier
  'r_chg=235' was float-repr noise at ~1.8e-15 (CSV roundtrip); real
  r_x1 changes = 1-3 per symbol, all in bug weeks. PF_R moves <=0.005.
  Proceeding; full decomposition reported in RESULTS_v6 Errata.

[2026-09-23T22:35:03Z] label_2f done (1s): AM/PM labels on _dstfix files, 0 OUT rows;
  T3 discovery recompute on D: H1 AM 1.150/PM 0.965 (n 5535/2913),
  H0 AM 1.138/PM 0.930; AM>PM 9/11 yrs H1, 10/11 H0, 6/7 & 7/7 syms.
[2026-09-23T22:35:03Z] PREREG_V6 FROZEN sha256=c3e9b29205863c20f06ca76c29988a58a3de4179cf18e4cb0b01551af9418f70
  - BEFORE any C-symbol AM/PM P/L file and before any VALIDATION access.
  K1-K3 confirm; V1-V3 validation; joint 4wk-block bootstrap 2000
  seed 20260924; power-on-D note.

[2026-09-23T23:48:19Z] A2F addendum received (Lead 23:47Z). Job cancelled 23:45:05Z mid
  free-running; fixed-list results stand; VALIDATION never unlocked.
  LOOK-AHEAD BUG confirmed: SwingZones._advance(t) only moves forward;
  zones_at(t) filters t-i<=max_age but NOT conf<=t -> a 2nd orders_for
  on the same cached ctx sees FUTURE swings (also explains the ~5min/sym
  slowdown: the whole _confirmed list is scanned per bar). regen_2f.py
  is clean (one orders_for per ctx, fresh process). Fixed at root:
  ctx.reset_zones() as first line of runner.orders_for.
  POWER (computed on D at 22:37Z, BEFORE the C files at 22:38:20Z;
  logged late because of the cancel): sep_D(H1)=0.1198 sd=0.0385;
  P(K1-K3)=0.731, P(V1-V3)=0.817 at D's effect; at half: 0.255/0.296.
  CONFIRM VERDICT (C, fixed list): K1 PASS (sep H1=+0.1151 LB95=+0.0376;
  H0 sep=+0.0914). K2 PASS (AM>PM on 5/5 C syms H1: NZD 1.063/0.966,
  CAD 1.117/0.821, EURJPY 1.142/0.971, AUDJPY 1.078/1.004,
  EURGBP 1.086/0.855). K3 PASS (sep long=+0.126 short=+0.104;
  AM>PM in 7/10 full years; with corrected calendar-year count 8/10).
  -> VALIDATION may be unlocked per PREREG_V6 (once).

[2026-09-23T23:51:13Z] verify_2f: T6 PASS (DESIGN orders after VALIDATION gen on same
  ctx == fresh-process, every field, F2_NH_b n=3480 & F0_J n=1056;
  note: VALIDATION-window order generation ran as determinism test
  only, no P/L/statistics; the single decision read remains step 5).
  T7 PASS (EURUSD + AUDJPY x H0/H1 regenerated fresh == _dstfix files
  row-for-row, 1e-9). runner.orders_for now calls ctx.reset_zones()
  first - A2F look-ahead fixed at the call site.
  Step B: week for account cap = London calendar week Monday 00:00
  (was epoch-Thursday buckets); year = true London calendar year (was
  //365 leap-drift). Applied in validation_2f; portfolio_2c_wkfix
  reruns the 2C view for the Errata table.

[2026-09-23T23:54:00Z] VALIDATION UNLOCKED (round 2F, once, after K1-K3 pass). Window (1578890844,1684333392]. HOLDOUT stays sealed; guard test passed.

[2026-09-24T00:00:18Z] VALIDATION read ONCE (unlock logged 23:54:00Z), 12 syms, no
  drops (coverage ok). VERDICT: NOT VALIDATED - V1 fails on H0 in BOTH
  modes: fixed AM PF_R x1=0.874 exp=-0.110 (<1.10/<0); free AM 0.905/
  -0.081. H1 side passes everywhere: fixed 1.125/0.080/x15 1.078; free
  1.160/0.101/1.111. V2 PASS (AM PF_R>1 on 10/12, need >=7). V3 PASS
  (sep=+0.163 H1, LB95=+0.085). Per-year AM PF_R H1: 2020 1.297 /
  2021 0.991 / 2022 1.064 / 2023 1.253. Portfolio: see
  out/portfolio_2f.csv. The AM edge is real on H1 but does not
  survive H0 on unread years - suspect-bar sensitivity flips the sign.

[2026-09-24T00:08:58Z] REVIEW_v6 done: PASS-WITH-NOTES, 8/8 checks pass. Notes:
  labels_2f lon_year used the drifting //365 (K3 passes either way:
  7/10 drifted, 8/10 corrected); validation_2f pos_years column same
  drift (reporting only); T6 validation-window order generation judged
  an allowed, disclosed determinism test (no P/L). Reviewer reproduced
  V1-H0 fail independently (0.874/-0.110 fixed, 0.905/-0.081 free).
  Round 2F closed: NOT VALIDATED. HOLDOUT never read.

[2026-09-24T00:17:39Z] A3F addendum received (Lead 00:15Z). One impossible print
  decided V1: EURUSD AM short SL filled at 2.655360 (bogus print,
  suspect-flagged, second-stamped) R=-810.4; a bogus WINNER +57.7R
  also found (2022-10-19 TP at 0.6808). H0 brackets the rollover
  question; it was never meant to execute off-market prints.
  LEAD_NOTE_5.md sha256=234a49ec90c51e53ddacc680bc0affc8ca86742ebfe1dd3378bb32b6fcdac8ae
  - recorded BEFORE any E0 output. Thresholds fixed by the Lead:
  >3% from last good close AND revert within 0.5% of it 15min later;
  voided like E1 suspect bars, on BOTH H0 and H1.
  PROVISIONAL status (stated before the rerun): the corrected V1-V3
  only tell whether the V1 failure was the data bug; they cannot
  confirm the idea - promotion needs the sealed HOLDOUT with E0 frozen.
  This is the SAME single read of VALIDATION with a bug fixed, not a
  new decision; first computation stays in RESULTS_v6 untouched.

[2026-09-24T00:25:10Z] A3F STEP1: E0 implemented (src/e0.py, run_trades void_extra, skip
  semantics identical to E1 on both harnesses). T8/T9 in tests/test_e0.py:
  5/5 pass (EURUSD 2020-05-07 12:33:04 flagged; SNB 2015-01-15 USDCHF slice
  not flagged; synthetic +5% revert flagged / no-revert not; zero-flag sim
  identical). e0_scan over 12 syms 2010->VALIDATION_END (holdout sealed):
  238 flagged bars, ALL already suspect=True (E0 bites H0 only).
  STOP CONDITIONS TRIGGERED before any rerun:
  (1) >20 flags in symbol-window: XAUUSD DESIGN=50, AUDJPY DESIGN=33.
  (2) Real market events flagged: SNB 2015-01-15, GBP flash 2016-10-07,
      JPY flash 2019-01-03 (USDJPY+AUDJPY), XAUUSD flash 2021-08-09,
      Brexit/ECB/FOMC midnight bars, NZDUSD 2015-08-24 Black Monday.
  Inventory in E0_BARS.md + out/e0_bars.csv + out/e0_flags_<sym>.npz.
  Per backup plan: stopped, reported, thresholds untouched. Awaiting Lead.
[2026-09-24T00:34:32Z] A4F: LEAD_NOTE_6.md sha256 = c17bff6ab15d3b25347ef89d203a7599cfea31f9bdcad4516dc4518806dc7efc
  (logged before any E0-prime output). E0' rule: void every M1 bar with
  non-zero-seconds timestamp (malformed record), both harnesses; nothing
  else voided - session-open/rollover wicks stay tradable on H0.
  PROVISIONAL STATUS (written before rerun, per LEAD_NOTE_5/6): the
  E0'-corrected V1-V3 are provisional. They can only show whether the
  original V1 H0 failure was caused by the malformed-print data bug;
  they cannot confirm the idea. Confirmation would require a future
  sealed HOLDOUT run with E0' frozen and no further data fixes after
  holdout opens. VALIDATION was already read once at 23:54Z; this is the
  same single read with a data-validity bug fixed, not a new decision.
[2026-09-24T00:42:40Z] A4F STEP1: E0' scan - 15 second-stamped bars total
  (EURUSD 6, GBPUSD 5, USDCAD 4, others 0; all corrupt ladder prices,
  dev 36-146%, none within 1% of neighbours; all suspect=True -> H1
  unchanged). T10 3 tests + T8/T9: 8/8 pass. List in E0_BARS.md s5b.
[2026-09-24T00:42:40Z] A4F STEP2 rerun (heavy 2.1min, H1 before H0, orders from
  versioned cache - unchanged; files suffix _e0s):
  DESIGN diff: 3 changed trades, all H0 (GBPUSD -1.06->-1.15 hurt;
  GBPUSD -1.04->-0.36 helped; USDCAD -233.28->-1.04 helped).
  VALIDATION diff: 4 changed, all H0 (EURUSD -810.41->+4.39 helped;
  EURUSD +57.67->+1.65 hurt; EURUSD removed +1.09 helped;
  USDCAD +132.15->+0.63 hurt). helped=4 hurt=3 - two-sided.
  C e0s: K1 PASS (H1 sep .1151 lb95 .0376; H0 sep .1459 lb95 .0661),
  K2 PASS 5/5, K3 PASS (H1 long .126 short .104 y8/10; H0 .151/.140).
  VALIDATION reapplied (same single read, data bug fixed; PROVISIONAL
  status logged 00:34:32Z before rerun). V1 fixed: H1 pf 1.1249
  exp +.0801 x15 1.0781; H0 pf 1.1446 exp +.0940. V1 free: H1 1.1598/
  +.1014/1.1114; H0 1.1625/+.1049. V2: AM>1 on 10/12 both. V3: sep
  H1 +.1627 lb95 +.0853 (H0 +.2004/+.1255).
  => Under E0' the provisional V1-V3 PASS on both harnesses both
  modes; the original failure was the malformed-print data bug.
  NOT a confirmation: promotion only via sealed HOLDOUT with E0'
  frozen. Sens: price-E0 3%/15m INVALID (voids real events) but its
  numbers similar (H0 fixed 1.1400/+.0911, free 1.1599).
  Portfolios e0s: eur_xau VAL H1 3.37t/w pf1.390 dd36R; H0 3.76t/w
  pf1.342 dd37R (was 0.507/837R). all12 capped VAL H1 pf1.219 dd47R;
  H0 pf1.144 dd57R.
  H0-H1 residual: per sym ~165-560 trades touched suspect bars;
  exits-in-roll ~= suspect-touch counts; e.g. VAL EURUSD 165/165,
  r_susp -1.04R - rollover-spike question remains round-3 open.
[2026-09-24T00:50:19Z] A4F STEP3: REVIEW_v6_E0.md by fresh neutral reviewer -
  PASS-WITH-NOTES, 7/7 checks verified independently (sha ordering,
  E0'=seconds-only, 15-bar list, T10 8/8, two-sided audit reproduced,
  V1-V3 recomputed to the digit, H1 files sha256-identical, holdout
  sealed, provisional-line precedes rerun). Notes: stale "14" prose
  vs actual 15; resolve_exit has no void_extra param (unreachable for
  F2_NH_b exit_rule=None).
[2026-09-24T03:32:17Z] 2G STEP1 pre-freeze (no holdout bar loaded):
  T11 PASS (guard raises GBPUSD+AUDJPY with flag ON, EURUSD with OFF,
  passes EURUSD+XAUUSD with ON - whitelist works).
  T12 PASS (get_ctx_upto end=VALIDATION_END reproduces 2F e0s VAL
  files EURUSD+XAUUSD row-for-row, both harnesses, FL+FR).
  T13 PASS (ctx truncated 2022-06-30 vs VALIDATION_END: all orders
  before cut identical - no leak).
  Swap handcheck PASS (found+fixed latent n_rolls Wed-triple bug in
  validation_2f copy - anchor0 used seconds*86400; new src/swap_adj.py
  correct: Wed-only crossing = 3 nights).
  1c XAU cap table: fixed_cap=21.22px; relative cap (250d trailing
  mdr x 1.001) tighter in most years (e.g. 2019 rej 36 vs 7; 2020V
  56 vs 37). out/cap_table_2g.csv.
  1d POWER on VAL e0s FR H1 (n=588, PF_R=1.3897):
    as-is: P(all gates)=0.483 -> STOP RULE (<0.60). per-gate:
    G1=.98 G1r=.49 G2=.99 G3=.97 G4=1.00 G5a=.96 G5b=.96
    shifted->PF1.15: P=.034 | G1=.64 G1r=.03 G2=.75 G3=.70 G4=1.00
    G5a=.41 G5b=.69
  G1r (drop |r|>5, PF>=1.05) is the binding gate - edge leans on
  large winners.
  1e freeze: 30 src/+runs hashes -> out/freeze_2g_hashes.csv.
  STOPPED before STEP 2 per rule; HOLDOUT remains sealed; Lead
  rebalances gates.
[2026-09-24T03:47:14Z] A1G: LEAD_NOTE_7.md (addendum spec verbatim) sha256 = 25212ea7d930751a4abb13323c760876b15fd24ba633d9e9e2c2d892c451ab42
  logged before any code/power run of this addendum. G1r replaced
  once by G1b (remove largest winner per symbol, PF>=1.05) + AUDIT
  RULE A (spike/gap flags + |R|>5 list; Lead ticks-check; downgrade
  only). HOLDOUT still sealed.
[2026-09-24T03:53:21Z] A1G done (pre-freeze): T14 PASS - spike detector flags both
  pre-E0'' bogus winners (EURUSD +57.7R, USDCAD +132.2R); flag rate on
  VALIDATION TP winners (EUR+XAU H1 FR e0s) = 0/131. No threshold
  tuned. POWER rerun with G1b (same blocks/seed 20260924):
  P(all gates) as-is = 0.930 (>= 0.60 STOP-RULE PASSES); per-gate
  G1 .98 G1b .98 G2 .99 G3 .97 G4 1.00 G5a .96 G5b .96;
  reporting-only G1r = .49. shift->PF1.15 arm: P(all)=0.387.
  Re-freeze: out/freeze_2g_hashes_a1g.csv (31 files); changed vs
  freeze_2g_hashes.csv: runs/holdout_2g.py, runs/prefreeze_2g.py;
  added: LEAD_NOTE_7.md, src/spike.py, tests/test_spike_2g.py.
  Original freeze_2g_hashes.csv untouched. HOLDOUT still sealed.

[2026-09-24T03:54:29Z] PREREG_V7.md frozen sha256 = d89df14baf5b962b62837e72a1dbc62e1c11eb21a988e0232596942c7fbd9295
  G1b gate + AUDIT RULE A verbatim; old G1r -> reported-only;
  deviation line included (G1r replaced once before any HOLDOUT
  access; A1G sha 25212ea7...). HOLDOUT may now be unlocked for
  EURUSD+XAUUSD only.

[2026-09-24T03:54:33Z] HOLDOUT UNLOCKED for ['EURUSD', 'XAUUSD'] only (round 2G, once, after PREREG_V7 frozen). Window (1684333392,1789775940]. All other symbols remain sealed (whitelist).

[2026-09-24T03:56:18Z] 2G read crash fix (outside candidate logic): my o_filt!=o_cap
  assert wrongly assumed capped generation == post-hoc risk filter.
  The cap skip inside the generator precedes used_flip, so o_cap is
  the frozen-candidate order stream (as 2F used; T12-verified).
  Assert+filter removed; orders_fixed=o_cap unchanged. holdout_2g.py
  sha256=ce065b81acff5bb88913f01094b7926ac95125eab2ae2bc2eb03bc93e07a8fc3; freeze_2g_hashes_a1g.csv regenerated. Rerunning the
  same frozen read.

[2026-09-24T03:56:24Z] HOLDOUT UNLOCKED for ['EURUSD', 'XAUUSD'] only (round 2G, once, after PREREG_V7 frozen). Window (1684333392,1789775940]. All other symbols remain sealed (whitelist).

[2026-09-24T04:11:30Z] 2G HOLDOUT READ COMPLETE (one read, EURUSD+XAUUSD only).
  unlock 03:56:24Z; census first, then H1 FR -> H1 FL -> H0 FR ->
  H0 FL -> relative-cap arm -> reported. holdout_2g.py sha ce065b81acff5bb8...
  VERDICT = FAIL (4 gate cells): G1 FL/H1 PF 1.087 < 1.10;
  G1b FR/H1 1.041 < 1.05; G5a MC DD P95 58.1 > 50R;
  G5b positive part-years 2/4 < 3. G1 FR 1.104/1.107, G2, G3
  (EUR 1.052 n=303, XAU 1.163 n=245), G4 pass.
  Audit list: 152 trades -> out/audit_list_2g.csv for the Lead''s
  MT5 tick-check (downgrade-only consequences per PREREG_V7).
  T11 re-run post-read: PASS (4/4). HOLDOUT resealed in session
  state (whitelist reset only at process end; no further reads).
