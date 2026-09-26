# REVIEW_v5 — ROUND 2E (S_T trend-agreement filter), fresh neutral review

Verdict: **PASS-WITH-NOTES** — all 6 checks pass. Notes below are
wording/cosmetic plus one wall-scope disclosure (check 6). No numbers
found wrong; nothing indicates C, VALIDATION or HOLDOUT leakage into the
2E design outputs.

Local mtimes are +0700; UTC = local − 7h.

## 1. FREEZE ORDERING — PASS

- `sha256(PREREG_V5.md)` recomputed =
  `430ac821bef5d0b5442c2188750906a0d4ee1df588a809b5dc0100c5c6df0bdb` —
  matches the hash in LAB_LOG.md:121 (`[2026-09-23T21:56:50Z] PREREG_V5
  FROZEN sha256=430ac821...`). File mtime 21:56:40Z (freeze stamp 10s
  later, consistent).
- First file with P/L split by S_T: `out/design_2e_persym_e1.csv`
  22:00:04Z; then `design_2e_free.csv` + `design_2e_summary.csv` +
  `base_2d_e1.csv` 22:00:39Z, `base_2d.csv` 22:00:40Z,
  `design_2e_persym.csv` 22:01:13Z. All > 21:56:50Z.
- `out/scores_2e_*.csv` (12 files, 21:55:39–53Z) headers verified for
  all 12: `sig_ctm,dir,sym,A1,A2,A3,S_T` — labels only, no P/L; they
  predate the freeze (allowed). `out/score_dist_2e.csv` (21:55:53Z) is
  counts only (n/long/short + per-year bucket counts), no P/L.
- Sweep of every `out/*.csv` header: the only S_T-bearing files are the
  scores (labels), score_dist (counts) and post-freeze base_2d*. No
  P/L-by-S_T artifact exists before the freeze.
- Note: LAB_LOG line 112 ("ROUND 2E start ... scores_2e run done, tests
  4/4") is stamped 21:56:50Z while describing artifacts written
  21:55:39–53Z, and cites "(Lead 22:15Z)" — batched/sloppy stamping,
  cosmetic only.

## 2. T1 LOOK-AHEAD TEST — PASS

- `tests/test_trend.py` rebuilds the full context from mutated M1 via
  `td.build_trend_ctx(m1b)` (resample M15/H1/H4 + all EMAs recomputed —
  lines 84–91 synthetic, 153–157 real), not a lookup. Mutates every M1
  bar after `sig_ctm+900` (`o,h,l,c += 3.0` synthetic; `c,h += 5.0`
  real) and asserts identical S_T/components both directions.
- Coverage: M15 bars at start/mid/end of an H1 bar (pos15 = 0 / 1–2 / 3)
  and of an H4 bar (pos60 = 0 / 8 / 15), plus Monday open
  (`wd==0 & t15%86400==0`) — lines 58–77. Real-data variant covers
  h1_start/h1_end/h4_start/h4_end + a Monday signal (lines 138–148).
- `python -m pytest tests/test_trend.py -x -q` → **4 passed in 6.78s**.
- Note: in the real test the "monday" predicate `s % 86400 < 86400` is
  always true, so it picks the first Monday signal, not necessarily the
  00:00 open bar; the synthetic test does cover the exact Monday-open
  bar. Minor weakening, coverage still exists overall.

## 3. INDEPENDENT RECOMPUTE — PASS, 20/20

- Throwaway script (temp dir, deleted after use; never imported
  `src.trend`): `dm.load_m1(sym, *dm.DESIGN)` — DESIGN window only, no
  `allow_holdout` — own `dm.resample` to M15/H1/H4, `ind.ema` for
  EMA34/89 (close), EMA34(High/Low) for the H1 dragon, EMA89(H4) vs
  j−6; usable-bar rule `open+step <= sig_ctm+900` applied manually;
  warm-up 266/101/266 re-implemented.
- 20 random rows sampled (seed 20260924) across pooled D-symbol score
  files; 7 D symbols appeared in the sample. **20/20 exact match** on
  S_T and on A1/A2/A3 flags, including S_T=2/1/0 mixes (e.g. XAUUSD
  sig=1377101700 mine (2,1,1,0) = ref). No NA row was sampled; NA logic
  is simple (any component state 0 → NaN) and verified by code read.
- Boundary safe: max sig_ctm = 2020-01-10T17:15Z ≪ DESIGN_END
  (2020-01-13T04:47Z), so no signal bar straddles the design cut.

## 4. NO PREMATURE C OUTPUT — PASS

- `sym` columns of `design_2e_persym.csv`, `design_2e_persym_e1.csv`,
  `design_2e_free.csv`, `base_2d.csv`, `base_2d_e1.csv` contain only the
  7 D symbols (AUDUSD, USDCHF, GBPJPY, USDJPY, GBPUSD, EURUSD, XAUUSD).
  No C-symbol (NZDUSD, USDCAD, EURJPY, AUDJPY, EURGBP) score-split or
  P/L rows exist in any out/ file — no C P/L file exists at all; the
  five `scores_2e_<C>.csv` are labels-only (allowed).
- All `design_2e*` mtimes (22:00:04–22:01:13Z) precede the decision log
  at 22:01:34Z — correct evidence→decision order; nothing C-related
  existed before or after it.
- Note: `design_2e_persym.csv` (22:01:13Z) is not written by any script
  in `runs/` (`design_2e.py` writes only `design_2e_persym_e1.csv`,
  line 255) — an ad-hoc artifact; its H1 rows match persym_e1 values and
  it is D-only, so harmless, but it is an unscripted output.

## 5. NULL & BOOTSTRAP CODE — PASS

- `regime_null_pct` (`runs/design_2e.py`:100–121): ONE `k` drawn per
  draw before the symbol loop (line 109) and applied to all symbols via
  `td.score_at_shifted(..., k*WEEK)` — whole-week circular shifts of the
  per-M15-bar trend-state series (trend.py:93–110, modulo wrap in
  [lo,hi)); A1–A3 recomputed from shifted states vs each trade's own
  `dir`; kept set (`S >= c`) pooled across symbols → `_pf_r`; pct =
  share of nulls strictly below real (line 120). NULL_N=1000,
  NULL_SEED=20260924 (lines 38–39). Matches PREREG_V5 spec.
- `boot_stat` (lines 71–86): calendar 4-week blocks (`_blocks` on
  `fill_ctm`, BLK=28d, line 40); block indices drawn once per resample
  and applied to the pooled df — joint for all symbols/subsets; every
  stat call reseeds `default_rng(20260924)` so statistics share the same
  resample sequence. BOOT_N=2000, seed 20260924 (lines 36–37).
- Nits (immaterial): `rng.integers(8, max(9, W-8))` gives k∈[8,W−9] vs
  prereg "[8, W−8]" (endpoint excluded; W≈522). `score_at_shifted`
  floors to the containing/preceding M15 bar without requiring an exact
  match — weekend gaps reuse the Friday bar; acceptable for a null.
  `b_lb95` and `b_lo90` are the same 5th-percentile column twice.
- E4 null pct=43.4 exists only in the log/stdout (not in any out/ file);
  not independently re-derivable without a rerun — taken as reported.

## 6. VALIDATION / HOLDOUT — PASS (with disclosure)

- No `out/*_val*`/validation outputs (399 files checked).
  `runs/run_validation.py` is a round-2 artifact (mtime 19:34Z Sep 23),
  gated on `runs/selection.json` (empty) — not run this round. LAB_LOG
  has no validation-unlock entry (grep: only rule/freeze mentions).
- No literal `load_m1(end > DESIGN_END)` in `runs/design_2e.py` or
  `runs/score_2e.py`. DISCLOSURE: both reach the VALIDATION window
  physically via helper defaults — `score_2e.py:40` and
  `design_2e.py:167` call `mg.light_ctx(sym)` which loads M1 to
  `dm.VALIDATION_END` (`managed.py:31`); `design_2e.py:288` uses
  `runner.get_ctx` → context built to VALIDATION_END (`runner.py:31`);
  `tests/test_trend.py:114,132` load EURUSD M1 to VALIDATION_END. So
  validation-window bars were read into the label/design pipeline
  without an unlock entry. Impact: nil — S_T is strictly causal (T1) and
  my DESIGN-only recompute reproduced 20/20 labels, proving validation
  bars contribute nothing to any label or statistic; the convention is
  inherited unchanged from round 2D (same helper defaults, passed
  REVIEW_v4). Flagged for transparency, not a leak.
- HOLDOUT guard intact: `data.py:80–84` raises PermissionError for
  `end > HOLDOUT_START`; post-slice check lines 101–103. Verified live:
  `load_m1("EURUSD", VALIDATION[0], COMMON_END)` → PermissionError.
  `tests/test_holdout_guard.py` covers all 12 symbols.

## Other observations

- PREREG_V5 T2 says "X0-HOLD trade files (2D for D, 2C for C)" but
  `managed.load_x0` actually reads `trades_2c_*` / `trades_*` files.
  Verified equivalent: keys and `r_x1` identical to
  `trades_2d_*_X0-HOLD` on all 3 spot-checked symbols × 2 harnesses
  (n and r_x1 equal to 1e-9). Wording loose, content identical.
- Log-reported numbers match `design_2e_summary.csv` (b=-0.0068 H1,
  lb95=-0.0389; +0.0017 H0; c=2; kept PF_R 1.0769/1.0602; cadence 0.99)
  and `score_dist_2e.csv` (S=0..3 = 32.4/22.5/26.2/18.9%, NA 1.71% vs
  "~30/22/26/20%, ~1.6%"). Consistent.
- Stray `nul` file (54 B, contains a shell error string) — cosmetic.
- Decision trail is clean: E1–E4 fail, E5 pass, STOP per frozen rule —
  consistent with the summary values; C/VALIDATION/HOLDOUT untouched.
