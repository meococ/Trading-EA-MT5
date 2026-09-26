# REVIEW_v3.md — Neutral review of ROUND 2C (cross-symbol replication)

Reviewer: fresh neutral sub-agent, read-only. Scope: SonicR_Lab only; no
HOLDOUT data touched. Method: recompute hashes, file-mtime audit, source
inspection, CSV spot recomputation, fresh-path trade replay.

All timestamps below converted to UTC (filesystem reports +0700).

---

## CHECK 1 — PREREG_V3 frozen before first basket P/L: **PASS**

- `sha256sum PREREG_V3.md` (recomputed now) =
  `2f5232ebb29fa53d9b0e06bc8aaee0293c7357bd60197263a20e3f8faa91f77f` —
  byte-identical to the hash in LAB_LOG.md:50 (logged 20:33:45Z).
- PREREG_V3.md mtime = 2026-09-23T20:26:14Z (file written ~7.5 min before
  the log entry; content unchanged since — hash matches).
- Earliest basket P/L file: `out/trades_2c_GBPUSD_F0_J.csv` mtime =
  20:33:53.74Z — 8.7 s AFTER the logged freeze. All 80 trades_2c files,
  design summaries, essence files, controls are later (20:33:53Z → 20:46Z).
- Outcome-blind products correctly predate the freeze: census_2c.csv +
  runs/q_w4d_2c.json = 20:33:36.66Z; order caches (out/sigs/*_1262563200
  .parquet) = 20:27–20:33Z; basket_checks.csv = 20:22Z. These are signal
  lists/diagnostics, not P/L — same ordering pattern accepted in round 2B.
- Caveat noted: LAB_LOG.md itself was last written ~20:47Z (appended
  lines), so the ordering rests on the independent PREREG/trades mtimes,
  which hold. No amendment section exists in PREREG_V3.md (48 lines, hash
  unchanged).

## CHECK 2 — No rule/parameter change vs A1/2B: **PASS**

- `src/variants/registry.py` (mtime 16:00:28Z Sep 23 — pre-2B, untouched):
  F0_J = pure `_J` defaults + tag (line 23); F2_NH_b (lines 45–47):
  session=london_ext, w2=None, sl="bigswing", tp="zone", offset_pips=2.0,
  weekly_cap=0 — matches the atlas-S6-fam2 spec in PREREG_V2.
- `src/variants/registry_2b.py` (mtime 18:48:51Z — before the 19:14Z
  freeze, untouched): F5_S2/F5_S3 (lines 20–23) score_min=2/3,
  sl="bigswing", tp="zone", session=london_j — matches PREREG_V2
  "exits R1b+R2a" (R1b=sl_big_swing, R2a=tp_zone).
- Generators: classic.py 19:14:49Z, other.py 19:04:17Z, stops_targets.py
  19:04:08Z, zones.py 18:45:44Z — all round-2B-era mtimes, zero 2C edits.
  F5 path verified: S = W2any+W3(thru)+W4c+PV2a (classic.py:46), score_min
  gate (line 133), sl_big_swing (156), tp_zone (167). F2 path verified:
  gen_nhat_hoai pullback-arm + close-outside-band trigger, london_ext,
  bigswing/zone exits (other.py:13–82).
- `src/sim.py` (mtime 20:23:05Z — documented 2C edit): ROLL lines 50–51
  keep EURUSD ((1435,15), 2.0e-4) and XAUUSD ((55,80), 20.0*0.1 = 2.0)
  values byte-identical; basket windows appended via `ROLL.update`
  (lines 55–60) — allowed per the check and matching out/basket_checks.csv
  roll_a/roll_b exactly. skip_suspect/E2/E3 share the single `run_trades`
  code path for all 12 symbols; the 2C design script calls it with the
  identical signature used for EUR/XAU (run_design.py:39–40,
  run_design_2b.py:38–39 vs run_design_2c.py:37–38).
- Other documented 2C edits, all behavior-preserving for EUR/XAU:
  data.py basket PIP/POINT/COST; runner.py sl_cap() generalized
  ((120/mdr_EUR)*mdr_sym*PIP — xau_sl_cap delegates to the same formula);
  whq.py pip_size now reads data.PIP (EURUSD→1e-4, XAUUSD→0.1, identical
  to the documented grid; all callers pass `symbol` explicitly).
- Caveat: SonicR_Lab is untracked in git — no byte-diff baseline exists;
  the verdict rests on mtimes + content review + the exact trade replay
  in check 6.

## CHECK 3 — W4d Q recomputed per symbol, census-only: **PASS**

- `runs/run_census_2c.py:57–61`: F0_J essence orders on `*dm.DESIGN`
  (orders only, no sim) → `q = median(dir*a20)` per symbol. angle20
  definition in classic.py:34–38 matches PREREG_V2
  ((dm[t]-dm[t-20])/(20*ATR14[t])).
- `runs/q_w4d_2c.json`: 10 distinct per-symbol Q values
  (-0.0027548 AUDJPY … -0.0074337 AUDUSD); EUR/XAU Q untouched in
  runs/q_w4d.json (-0.0063401056 / -0.0053644141).
- census_2c.csv mtime 20:33:36.66Z precedes the first design/P-L file
  (20:33:53.74Z).
- `w4d_q` is consumed only by classic.py:125–128 when cfg["w4d"] is set;
  none of the 4 round-2C configs uses W4d, and grep shows no Q/median
  recomputation in run_design_2c / run_essence_2c / run_controls_2c
  (they load cached orders). Q recorded anyway per the frozen procedure.

## CHECK 4 — VALIDATION/HOLDOUT unread for all 12 symbols: **PASS**

- `allow_holdout=True`: zero hits in any code file (only docstrings and
  the guard's own message text).
- `pytest tests/test_holdout_guard.py` — **3/3 PASSED** (all 12 symbols
  raise PermissionError for end>HOLDOUT_START, incl. full VALIDATION→END
  spans).
- No `out/validation*` or holdout artifacts; runs/run_validation.py is a
  2B relic driven by selection.json (130 B, empty) — not run this round.
- ctx loads M1 up to VALIDATION_END (runner.py:31 → context.build;
  data.py guard blocks only >HOLDOUT_START). Every 2C script consumes
  only the DESIGN window for signals/pools: run_census_2c.py:57,78
  (`*dm.DESIGN`), run_design_2c.py:33 (cached DESIGN orders),
  run_controls_2c.py:61–63 (pool restricted to DESIGN bar range),
  run_essence_2c.py:36.
- Observation (by design, not a violation): a DESIGN-edge signal's trade
  resolution can spill onto bars just past DESIGN_END (ttl + Friday
  flatten bound). Same semantics as 2B; signals themselves are
  DESIGN-only.

## CHECK 5 — Cost table applied as written: **PASS**

- `data.py:68–71` `_BASKET_RT_PIPS` = {GBPUSD 1.4, USDJPY 1.2, AUDUSD 1.3,
  NZDUSD 1.8, USDCAD 1.6, USDCHF 1.6, EURJPY 1.6, GBPJPY 2.6, EURGBP 1.5,
  AUDJPY 1.8} — exact match to the Lead table (BASKET.md §2).
- Recomputed `sim.round_trip_cost(sym)` for all 10: equals rt*PIP exactly
  (e.g., GBPUSD 0.00014, USDJPY 0.012, GBPJPY 0.026). Decomposition
  spread 0.1p + comm 0.7p + slip (rt−0.8)/2 per side (data.py:72–75)
  sums back to rt pips.
- PIP: JPY→0.01 else 1e-4 (data.py:57–59); EURUSD 1e-4, XAUUSD 0.1
  unchanged; EURUSD RT = 1.0e-4, XAUUSD RT = 0.55 unchanged.
- ROLL stress (sim.py:55–60): +2.0 pips ask side in price units for all
  basket symbols, GBPJPY +3.0 pips; windows equal basket_checks.csv
  roll_a/roll_b (e.g., GBPUSD (1439,28), GBPJPY (0,16), AUDJPY (0,17)).

## CHECK 6 — Hand-checked trades: **PASS**

- Ran `python runs/handcheck_2c.py`: sampled 5 trades each from
  GBPUSD F0_J and EURJPY F2_NH_b H0 CSVs, replayed on both harnesses.
  Result: H0 10/10 OK; H1 8/8 replayed OK + 2 correct skips;
  **TOTAL: 0 mismatches**.
- The 2 H1 "no trade - skip" cases (GBPUSD sig=1391698800, EURJPY
  sig=1455096600): pending fill would have occurred on suspect bars, so
  under H1 no trade exists in the _e1 CSVs — exactly the A1-registered E1
  behavior. (LAB_LOG "18/18 OK" counts the replayed trades; the 2 skips
  are additionally correct absences.)
- `recompute()` (handcheck_2c.py:32–82) is a fresh standalone code path —
  it imports `sim` only for the ROLL constant table (line 20–29), never
  calls `sim.run_trades`. Note: it mirrors the same algorithm by the same
  author rather than being an independently derived implementation; per
  this check's definition it qualifies.

## RESULTS_v3.md spot-check vs out/ CSVs

- Pooled PF_R (controls_2c_pooled.csv) — all 8 cells exact at 3dp:
  F0_J 0.8039/0.8917→"0.804/0.892"; F2_NH_b 1.0488/1.0626→"1.049/1.063";
  F5_S2 0.9491/0.9977→"0.949/0.998"; F5_S3 0.8930/0.9315→"0.893/0.931".
- R3 pooled pct: H1 = 38.7/100/78.85/41.3 → reported 39/100/79/41; H0
  F2_NH_b = 100.0 ✓.
- Essence Stouffer (essence_2c{,_e1}.csv): H0 z=0.6504 p=0.2577,
  H1 z=0.1452 p=0.4423 → reported 0.65/0.258, 0.15/0.442 ✓; rho>0 counts
  (all n≥480): H0 6/10, H1 5/10 ✓; rho range [-0.0609,+0.0563] vs
  claimed [-0.061,+0.056] ✓.
- ">1.00 count H1" recomputed from design_summary_2c_e1.csv:
  F0_J 2, F2_NH_b 9, F5_S2 6, F5_S3 3 — match §4 ✓.
- F2_NH_b pooled PF_R x15 H1 recomputed from trades CSVs = 1.0181 →
  reported 1.018 ✓; x15 ~values for F0_J/F5_S2/F5_S3 = 0.843/0.957/0.895
  vs "~0.85/~0.95/~0.90" ✓.
- Portfolio §7: all 16 rows match out/portfolio_2c.csv (n, tr/wk, PF_R,
  MC DD P95, posY) within rounding ✓.
- Census §2: basket sums = 20.51/68.70/7.15/1.70 per wk vs
  "~20.4/68.7/7.2/1.7" ✓; per-symbol ranges, E2 removals 0–14, Q range
  −0.0028..−0.0074 all verified ✓.

## Issues found (all MINOR — no verdict changes)

- MINOR-1 (RESULTS_v3 §6, EURGBP F5 cells): F5_S2 reported "0.81/0.88"
  equals **pf_x1** (pips PF); true pf_r_x1 = 0.8639/0.9407 → should read
  0.86/0.94. F5_S3 "0.47/0.47" likewise equals pf_x1; pf_r = 0.479/0.480
  → should read 0.48/0.48. Wrong column pulled for 2 cells.
- MINOR-2 (RESULTS_v3 §6, AUDJPY row): 5 of 8 values wrong —
  F5_S3 H0 reported 0.83 vs actual 0.888→0.89; all four H1 values off
  (reported 1.01/1.08/1.07/1.00 vs actual pf_r 0.930/1.049/1.007/0.911 →
  should be 0.93/1.05/1.01/0.91). The F0_J/F5_S3 H1 values coincide with
  pf_x1 (1.007/1.004) but F2_NH_b 1.08 and F5_S2 1.07 match no column —
  transcription errors. Counts and pooled figures were computed from
  CSVs and are correct, so no conclusion is affected.
- MINOR-3 (§5 wording): "Null p95 for pooled basket ~0.95–0.97" holds
  only for the large-n configs (F0_J 0.91–0.94, F2_NH_b 0.95–0.97); the
  pooled null p95 for F5_S2 is 1.015/1.044 and for F5_S3 1.548/1.146
  (controls_2c_pooled.csv). The qualifier "~14k trades" implies F2_NH_b,
  but as written the statement over-generalizes. R3 verdicts unaffected.
- MINOR-4 (hygiene): stray empty `nul` file at repo root (Windows
  redirect artifact); `handcheck_2c` prints "no trade - skip" lines that
  LAB_LOG's "18/18" glosses over (18 replayed-OK + 2 correct absences).
- OBSERVATION (not an issue): the lab is not under version control, so
  "unchanged vs A1" is evidenced by mtimes + content review, not a
  cryptographic diff; and trade resolution legitimately reads a few
  post-DESIGN_END bars for edge signals (documented 2B semantics).

---

## Verdict: **PASS-WITH-NOTES**

All six registered checks pass: the V3 prereg hash is byte-exact and
predates the first basket P/L by ~9 s; the four configs are frozen A1/2B
definitions with only the documented, behavior-neutral 2C additions
(basket costs/pips, per-symbol roll windows and SL cap, whq pip lookup);
per-symbol W4d Q was recomputed outcome-blind before any P/L; the
holdout seal is intact and tested for all 12 symbols; the Lead's cost
table is applied exactly; and 20 sampled trades replay bit-exact on a
fresh code path with the two H1 suspect-bar skips being correct E1
behavior. The FAIL/closest-pass verdicts (R1 p=0.26/0.44, R2 pooled
1.049/1.063 < 1.10, R3 only F2_NH_b at pct=100) reproduce exactly from
the CSVs. The only blemishes are cosmetic: nine wrong cell values in the
RESULTS_v3 §6 per-symbol table (two EURGBP cells pulled the pip-PF
column; five AUDJPY cells are transcription errors that match no column),
and one over-generalized null-p95 sentence — none alters any verdict or
count, since those were computed from the CSVs and verified independently.
