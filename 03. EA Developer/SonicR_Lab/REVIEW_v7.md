# REVIEW_v7 — ROUND 2G (+A1G): FRESH NEUTRAL REVIEW

**VERDICT: CONFIRMED-WITH-NOTES.** The printed verdict **FAIL**
(4 gated cells) is arithmetically correct and independently
reproduced. No FAIL-DATA or INCONCLUSIVE condition applies to the
failing cells.

Reviewer: fresh sub-agent, did not do the work. Everything below was
recomputed from the artifacts on disk (raw M1 loaded read-only via
the lane's own guard, post-unlock, for EURUSD/XAUUSD only).

## Checks

| # | check | result | evidence |
|---|-------|--------|----------|
| 1 | LAB_LOG ordering | PASS | LEAD_NOTE_7 sha 25212ea7…ab42 logged 03:47:14Z < A1G T14+power 03:53:21Z < PREREG_V7 sha d89df14b…f9295 03:54:29Z < unlock 03:54:33Z < crash-fix re-hash 03:56:18Z < re-unlock 03:56:24Z < read complete + "T11 re-run post-read PASS (4/4)" 04:11:30Z. |
| 2 | Code hashes | PASS | All 31 files in out/freeze_2g_hashes_a1g.csv sha256-match disk NOW (0 mismatches), incl. holdout_2g.py = ce065b81…8fc3 (the post-crash-fix hash, logged before re-unlock). out/freeze_2g_hashes.csv intact: mtime 03:31:44Z ≈ freeze entry 03:32:17Z, still carries the ORIGINAL pre-fix holdout_2g.py hash e31e2799 and no A1G files — i.e. untouched. PREREG_V7.md and LEAD_NOTE_7.md hashes match logged values. |
| 3 | Whitelist guard | PASS | Fresh python: after `open_holdout(['EURUSD','XAUUSD'])`, `load_m1(sym,1684333392,1789775940,allow_holdout=True)` raises PermissionError for GBPUSD, USDJPY, AUDJPY; EURUSD/XAUUSD load (1,242,663 / 1,175,009 bars). Narrowing whitelist to {XAUUSD} re-blocks EURUSD. Guard = flag AND membership (src/data.py:83-101). |
| 4 | Gates recomputed | PASS | See table below: all 13 cells reproduce to the digit; exactly 4 gated cells fail (G1 FL H1, G1b, G5a, G5b) → FAIL. `G1r(reported)` row excluded from the verdict (holdout_2g.py filters `~gate.str.contains("reported")`). FL am_pm labels: recomputed independently via `dm.london_parts(sig_ctm)` → 0 mismatches, 0 OUT rows in all 4 FL files. |
| 5 | Trade replay | PASS | 5 rows EURUSD FR H1 + 5 rows FR H0 (rng seed 20260924): fill bar = first clean bar crossing the stop; fill = max(stop,open)/min(stop,open) ± roll adj; exit reason/price/ctm = first clean bar hitting SL-then-TP or Friday-flatten open; R=(dir·(exit−entry)−1e-4)/risk. 10/10 exact to <1e-9. Swap: hand-check fill 2023-11-22 (Wed) → n_rolls=3, r_adj=0.94 matches formula. |
| 6 | ±5R list | PASS | out/extreme_2g.csv = 117 rows (tp 67, flat 50). Sampled 12 (rng 7): 11 fully verified — exit sits on a non-voided bar and the exit price obeys the sim convention incl. roll-window ±S; 1 RELFL row verified at clean-bar level only (no RELFL trade CSV exists — reported-only arm). Max exit/fill dev vs prev close = 0.016 — no FAIL-DATA print. |
| 7 | Census | PASS | Recomputed on the holdout slices: EURUSD bars 1,242,663; dup_ts 0; E0' second-stamped 3; minute-aligned >20% off prev close 3; range>10x med 1,945; weeks 175/174. XAUUSD: 1,175,009; 0/0/0; 1,563; 175. Identical to out/census_2g.csv. |
| 8 | Audit list | PASS | Recomputed spike flags for ALL TP winners (not a sample) + |R|>5 union across all 8 frames (2 syms × FR/FL × H0/H1), dedup by (sig_ctm,fill_ctm): expected 152 rows = actual 152, flag strings identical per key (spike 73, \|R\|>5 62, both 17). Columns cover spec (sym, side, fill t+px, exit t, exit px, exit type, R, flag). Both harnesses (H0 115/H1 37) and both modes (FL 91/FR 61) present. |
| 9 | T14 | PASS | `pytest tests/test_spike_2g.py -x`: 3/3 pass (both pre-E0' bogus winners flagged; 0/131 VALIDATION TP winners flagged). tests/test_holdout_2g.py also re-run by me: 4/4 pass. |
| 10 | A1G history + G1r | PASS | PREREG_V7 lines 27-32 carry the required history line verbatim with sha 25212ea7… and "reported, not gated"; LAB_LOG logs that sha before any A1G power (03:47:14Z < 03:53:21Z). gates_2g.csv lists G1r only as `G1r(reported)` = 0.784; RESULTS_v7 labels it "reported only". |

## Gate cells recomputed (from out/trades_2g_*.csv only)

| gate | cell | mine | file | verdict |
|---|---|---|---|---|
| G1 | FR H1 | PF 1.1045, exp +0.0713 | 1.1045 | pass |
| G1 | FL H1 | PF 1.0868 (n=473 AM) | 1.0868 | **FAIL** |
| G1 | FR H0 | PF 1.1070, exp +0.0740 | 1.1070 | pass |
| G1 | FL H0 | PF 1.1450, exp +0.0999 | 1.1450 | pass |
| G1b | FR H1 | 1.0409 (dropped EUR +8.124R, XAU +15.656R) | 1.0409 | **FAIL** |
| G2 | FR H1 | 1.0455 (r_x15 + swap×2) | 1.0455 | pass |
| G2 | FL H1 | 1.0289 | 1.0289 | pass |
| G3 | EURUSD FR H1 | 1.0517 (n=303 ≥150) | 1.0517 | pass |
| G3 | XAUUSD FR H1 | 1.1631 (n=245) | 1.1631 | pass |
| G4 | FL H1 | sep +0.1597 (AM 473 / PM 275) | +0.1597 | pass |
| G5a | FR H1 | MC DD P95 = 58.13 (200 perm, seed 5) | 58.13 | **FAIL** |
| G5b | FR H1 | 2/4 pos years (2023 −5.19, 2024 +13.59, 2025 +33.27, 2026 −2.60) | 2 | **FAIL** |
| G1r | FR H1 | 0.7841 — reported only, NOT gated | 0.7841 | — |

## Required statements

**(a) FAIL arithmetic:** correct. Exactly 4 gated cells fail
(G1 FL/H1 1.087 < 1.10; G1b 1.041 < 1.05; G5a 58.1 > 50; G5b 2/4 < 3);
every other gated cell passes; G1r is reported-only and did not
influence the verdict. Sample floors met (n=303/245 ≥150; coverage
1.006 ≥ 0.90) → no INCONCLUSIVE cell.

**(b) FAIL-DATA check:** the 3 EURUSD census ">20% off prev close"
bars are the minute-aligned BOUNCE-BACK bars immediately after the 3
second-stamped bogus prints (2024-09-25 12:21, 2024-11-11 00:01,
2024-12-26 00:00 — deviation measured against the bogus close).
**No trade in any of the 8 gated frames has its fill or exit on any
of these bars (0 hits), nor on the 3 second-stamped bars (voided by
E0' anyway).** In the 12-row ±5R sample, worst deciding-bar
deviation = 1.6%. FAIL-DATA is NOT triggered; the FAIL stands as a
genuine gate failure, not a data artifact.

**(c) Audit list completeness for the Lead's MT5 tick check:**
complete. My independent rebuild (every TP winner's spike/gap flag +
every |R|>5 trade, all 8 FR/FL frames, deduplicated) reproduces all
152 rows and every flag string exactly; required columns present.
Suitable for the Lead's ±2-min bid/ask check as-is.

## Notes (immaterial, no verdict impact)

1. Two HOLDOUT UNLOCKED lines exist (03:54:33Z, 03:56:24Z) bracketing
   the mid-read crash fix to runs/holdout_2g.py; the fix and re-hash
   were logged (03:56:18Z) before the second unlock, and the manifest
   on disk carries the post-fix hash. Ordering holds.
2. RELFL trade frames exist only in-memory (no RELFL CSV); the one
   sampled RELFL ±5R row was verified at clean-bar/price level only.
   The arm is reported-only (forward-test candidate), so no gate or
   audit consequence.
3. t14 test rewrites out/t14_flagged_val_tp.csv on run — a reporting
   artifact, not a gated one.

## Unverified / out of scope

- The Lead's MT5 tick-history comparison (AUDIT RULE A step c) — by
  design done outside this lane.
- The relative-cap arm's gates (reported-only, forward-test
  candidate); its trades CSVs (RELFR) exist but were not
  re-simulated.
- Power-rerun numbers (P(all)=0.930) — logged pre-unlock; not
  recomputed (not part of the verdict).
