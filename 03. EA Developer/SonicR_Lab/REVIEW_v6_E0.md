# REVIEW_v6_E0 — neutral re-verification of the A4F E0' rerun (round 2F)

Reviewer: fresh neutral subagent; did not do the work. Scope: the 7 checks
below. Read-only verification + independent recomputation; no file touched
except this review. HOLDOUT never accessed (loader enforces; verified).

## Check 1 — LEAD_NOTE_6 frozen before first E0' output: PASS
- `sha256(LEAD_NOTE_6.md)` recomputed = `c17bff6a…7efc`, matches the note
  and LAB_LOG `[2026-09-24T00:34:32Z]` entry verbatim.
- Timeline (heavy_run.log + mtimes): LEAD_NOTE_6.md mtime 00:34:13 →
  LAB_LOG hash entry 00:34:32Z → e0s scan `python -c` 00:34:45–00:35:06Z →
  first E0' output `out/e0s_flags_EURUSD.npz` mtime 00:34:47 →
  `out/e0s_bars.csv` 00:35:06 → rerun_2f_e0s.py 00:38:56–00:40:59Z →
  `_e0s` trade/stat files 00:39:5x–00:40:59 → LAB_LOG STEP1/STEP2 00:42:40Z.
  Hash logged ~15 s before the first E0' artifact — tight but before.
- Note (cosmetic): note title says "00:40Z"; file mtime/log are 00:34.

## Check 2 — E0' implementation equals the note: PASS
- `src/e0.py:79-82` `second_stamp()` = `(m1["t"] % 60) != 0` — timestamp
  only; no price, no future data.
- `src/sim.py:111-113` `eff_void = suspect|void_extra` under
  `skip_suspect`, else `void_extra` — both harnesses as specified.
- Voided bars skipped identically to suspect bars: fill scan (`:143`),
  SL/TP loop (`:184`, also arms the post-void no-gap-bonus TP rule via
  `prev_suspect`), Friday flatten (`:230`), MFE/MAE segment (`:235`).
- Orders unchanged: rerun calls `orders_once` → versioned cache
  `F2_NH_b_dstfix` (validation_2f.py:114-124); cache parquets
  `out/sigs/*_F2_NH_b_dstfix_*.parquet` mtime 23:51–23:59 09-23, NOT
  regenerated during the e0s run. `run_trades` is called with
  `exit_rule=None`, so the void path above is the one used.
- Latent gap (not triggered): `resolve_exit()` takes no `void_extra`;
  a config using `exit_rule` would not void E0' bars. F2_NH_b does not.

## Check 3 — second-stamped population + tests: PASS
- `out/e0s_bars.csv`: 15 rows — EURUSD 6, GBPUSD 5, USDCAD 4; all
  `t%60!=0`, all `suspect=True`. `out/e0s_flags_*.npz` totals agree (15).
- Independently re-found via `src.data.load_m1`: EURUSD 1588854784
  (2020-05-07 12:33:04, o=2.65536, sec=4), 1575223296 (2019-12-01
  18:01:36), 1666187264 (2022-10-19 13:47:44), GBPUSD 1512570880
  (:40), USDCAD 1586495488 (:28) — all present, all non-minute-aligned,
  all suspect.
- `tests/test_e0.py` T10 present (3 tests); `pytest tests/test_e0.py`:
  8/8 pass here.

## Check 4 — changed-trade audit is two-sided: PASS
- Independent outer join (sig_ctm, dir) over all 12 symbols:
  DESIGN `trades_2f_*_dstfix` vs `*_e0s` = exactly 3 changes, all H0:
  GBPUSD -1.0613→-1.1489 (hurt), GBPUSD -1.0409→-0.3595 (helped),
  USDCAD -233.276→-1.0444 (helped). Matches `e0s_diff_design.csv`.
  VALIDATION (fill_ctm≥1578890844) = exactly 4, all H0:
  EURUSD -810.4108→+4.3876 (helped), EURUSD +57.6679→+1.6536 (hurt),
  EURUSD sig 1666260900 removed, r_old=-1.0860 (helped +1.086),
  USDCAD +132.154→+0.6285 (hurt). Matches `e0s_diff_val.csv`.
- Totals: helped=4, hurt=3 — both nonzero; audit is not one-sided.
- Cosmetic: LAB_LOG phrase "removed +1.09" — removed trade was -1.086R;
  the delta is +1.09 helped. Numbers right, wording compressed.

## Check 5 — V1-V3 re-applied per PREREG_V6: PASS
- Gates (PREREG_V6 §VALIDATION RULE) read. Recomputed from `_e0s` files
  with my own pf/sep code and a from-scratch joint bootstrap (2000
  resamples, 28-day blocks on fill_ctm, seed 20260924):
  - H1 fixed: pf_am_x1 1.1249, exp +0.0801, pf_am_x15 1.0781, sep
    0.1627, lb95 0.0853, syms AM>1 = 10 — equals `val_2f_e0s_pooled.csv`.
  - H0 fixed: 1.1446 / +0.0940 / 1.0975 / 0.2004 / 0.1255 / 10 — equals.
  - H1 free: n=3724, pf 1.1598, x15 1.1114, exp +0.1014 — equals
    `val_2f_e0s_free.csv`. H0 free: 4098 / 1.1625 / 1.1145 / +0.1049.
  - V1 (≥1.10 & exp>0 both harnesses, x15≥1.00 on H1, both modes):
    passes; V2 10/12 ≥7: passes; V3 sep>0 & lb95>0 on H1: passes.
- K1-K3 (`confirm_2f_e0s_pooled.csv`): H1 sep .1151 lb95 .0376, H0 sep
  .1459 lb95 .0661, K2 5/5, K3 8/10 years — matches LAB_LOG, all pass.
- H1 identity: sha256 of `trades_2fval_*_e0s_e1` vs `*_e1`,
  `*_AMONLY_e0s_e1` vs `*_e1`, `trades_2f_*_e0s_e1` vs `*_dstfix_e1` —
  byte-identical for ALL 12 symbols (36 pairs), consistent with all 15
  voided bars being suspect.

## Check 6 — HOLDOUT unread: PASS
- `rerun_2f_e0s.py:177-181` re-ran the guard (`load_m1` past
  HOLDOUT_START must raise PermissionError; SystemExit otherwise); the
  run exited rc=0, so it raised. `runner.get_ctx` builds to
  VALIDATION_END only; `load_m1` hard-blocks `end > HOLDOUT_START`;
  grep: no `allow_holdout=True` anywhere in code. LAB_LOG consistent.

## Check 7 — provisional status logged before the rerun: PASS
- LAB_LOG `[2026-09-24T00:34:32Z]` contains the PROVISIONAL paragraph
  (same single VALIDATION read, bug fixed, not a confirmation).
  heavy_run.log: rerun ran 00:38:56–00:40:59Z. Provisional precedes
  rerun by ~4.4 min. (An earlier provisional was also logged 00:17:39Z
  for the withdrawn price-E0 variant.)

## Additional notes (no check failed)
- LEAD_NOTE_6 and E0_BARS.md §6 still say "14 second-stamped bars"
  (pre-scan estimate); the scan found 15 and every downstream artifact
  (e0s_bars.csv, flags, LAB_LOG 00:42:40Z) says 15. Stale prose only.
- RESULTS_v6.md mtime 00:43:10 — an E0' addendum was appended; the
  first-computation FAIL row is preserved in its sensitivity table, so
  "first computation untouched" holds in substance.
- EURUSD VAL fixed list 438→437 rows: one order's only fill bar was
  voided — consistent with the mechanism, not a lost row.

## VERDICT: PASS-WITH-NOTES
All 7 checks verified independently; the only blemishes are cosmetic
(stale "14 bars" prose, note title timestamp, compressed log wording)
and a latent `resolve_exit` gap that F2_NH_b never reaches.

Neutral read: the provisional claim is soundly derived. The E0' rule is
format-only, was frozen (hash logged) before any E0' output, was applied
through the identical void machinery as E1 on both harnesses with orders
unchanged from the versioned cache, and the re-applied V1-V3 reproduce
exactly from the emitted trade files — including the bootstrap. The
changed-trade audit is genuinely two-sided (4 helped / 3 hurt), so the
fix is not a one-directional scrub, and H1's byte-identical output is
exactly what the all-suspect population predicts. The -810.4R trade was
caused by a malformed record; under E0' the gates pass on both harnesses
in both modes. The lab's own framing is correct: this establishes that
the original V1 failure was the data bug, not that the AM edge is
confirmed — confirmation remains gated on the sealed HOLDOUT.
