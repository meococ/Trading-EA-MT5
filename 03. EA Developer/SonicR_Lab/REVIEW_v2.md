# REVIEW_v2 — neutral read-only review of the SonicR_Lab round-2 + 2B lane

Reviewed 2026-09-24 (reviewer-run date). Scope: RESULTS_v2.md, DATA.md,
PREREG_V2.md, LAB_LOG.md, runs/*.py, src/*.py, out/*. No files modified;
only read + re-ran stdout-only diagnostics (runs/diag_roll_v2.py,
runs/handcheck.py). Local file times below are UTC+7; LAB_LOG times are UTC
(local − 7h), verified consistent throughout.

## Check 1 — corrected E1 diagnostic numbers — PASS

Recomputed `exits per 1000 trade-minutes in roll window vs outside` from the
trade CSVs using the same methodology as runs/diag_roll_v2.py:28-73
(EUR window mod∈[0,20) i.e. 00:00-00:20 server; XAU [60,80)):

| file | n | exits_in | t_in min | rate_in | rate_out | ratio | DATA.md claim |
|---|---|---|---|---|---|---|---|
| trades_EURUSD_F0_J.csv | 598 | 161 | 635 | 253.54 | 2.14 | 118.6x | 253.5/2.14, 118x |
| trades_EURUSD_F2_NH_b.csv | 1291 | 493 | 13086 | 37.67 | 0.53 | 70.5x | 37.7/0.53, 71x |
| trades_EURUSD_F3_LUCY_a.csv | 4204 | 94 | 262 | 358.78 | 18.66 | 19.2x | 358.8/18.7, 19x |
| trades_XAUUSD_F0_J.csv | 646 | 94 | 797 | 117.94 | 3.60 | 32.7x | 117.9/3.60, 33x |
| trades_XAUUSD_F2_NH_b.csv | 1434 | 520 | 15150 | 34.32 | 0.59 | 58.2x | 34.3/0.59, 58x |
| trades_2b_XAUUSD_F5_S3.csv | 76 | 30 | 930 | 32.26 | 0.54 | 59.8x | 32.3/0.54, 60x |

Exit-share vs time-share (server-hour-0 window, EUR): F0_J 161/598 = 26.9%
of exits inside a window covering 635/205109 = 0.31% of trade-minutes;
F2_NH_b 493/1291 = 38.2% of exits in 0.87% of minutes. Internally
consistent. H1 files show the concentration collapses to ~0.6x-1.9x
(e.g. F0_J_e1: 4 exits in window, rate_in 1.06 vs 1.93 out) — consistent
with E1 voiding those exits.

Full rerun of `python runs/diag_roll_v2.py` reproduced:
- (b) per-day roll/quiet max-range ratio: EUR med=30.94 p90=63.02
  p99=115.63 (reported 30.9/63.0/115.6); |o−c_prev| med=71.20 p90=270.00
  p99=664.40 (reported 71.2/270.0/664.4). XAU med=37.91/86.46/176.38
  (reported 37.9/86.5/176.4); gap 68.78/279.48/839.14 (68.8/279.5/839.1).
  Roll med range EUR 0.00893 vs quiet 0.00030; XAU $15.535 vs $0.40.
- (c) jump-and-revert: EURUSD 665/2586 = 25.7%; XAUUSD 455/2519 = 18.1%
  (exactly as reported).

MINOR: prose bound "every config shows 19x-450x more exits/minute inside
the window" is inaccurate at both ends — recomputed H0 ratios span
~5.7x (XAUUSD F1_W4a) to ~208x (EURUSD F1_W2whq); three cells are below
19x (XAU F1_W4a 5.7x, XAU F3_LUCY_a 7.5x, XAU F3_LUCY_b 14.8x). All six
tabled example values reproduce exactly; the conclusion is unaffected.

## Check 2 — errata applied to every config — PASS

- H0: out/design_summary.csv = 34 rows (17 round-2 cfgs x 2 syms) +
  out/design_summary_2b.csv = 16 rows (8 2B cfgs x 2 syms) = 50 cells.
- H1: out/design_summary_e1.csv (34) + out/design_summary_2b_e1.csv (16)
  = identical 50-cell set (verified programmatically).
- E2 counts: out/census_2b.csv has `e2_removed` column (2B configs);
  round-2 E2 counts in out/census.csv `e2_removed` and in
  design_summary*.csv `rejected` — values agree (e.g. XAUUSD F2_NH_a
  759/4142, F3_LUCY_a 6866/10964, F3_LUCY_b 5507/8622, F4_BAI14 665/9254;
  EURUSD F2_NH_b 13, F3_LUCY_a 18, F3_LUCY_b 17, F1_R1b 3).
- Loser configs have both harness files: trades_{EURUSD,XAUUSD}_F4_BAI14
  .csv+_e1.csv, _F0_J, _F3_LUCY_b all present (F4: 19:09-19:10Z H0 /
  19:31Z H1).
- H1 `suspect` touch count sums to 0 across all 50 cells (H0: 5231) —
  consistent with skip-suspect actually applied.

## Check 3 — PREREG_V2 hash precedes first 2B P/L — PASS

- LAB_LOG.md:14 records freeze 19:14:11Z, file mtime 19:14:04Z,
  sha256=3e922071...9bd7. Earliest 2B P/L file:
  out/trades_2b_EURUSD_F1_W4c.csv mtime 2026-09-23 19:14:20.83Z
  (local 02:14:20.83) — 16 s after the freeze mtime, matching the LAB_LOG
  line-22 audit "(16s, ordering holds)".
- Byte-level verification: sha256 of the file content BEFORE the `---`
  amendment separator (rstrip + trailing CRLF) = 3e92207100399e76… —
  exact match to the logged frozen hash → the ORIGINAL text is
  byte-for-byte untouched. sha256 of the whole current file =
  0226143d1e763a19… — exact match to the logged post-amendment hash →
  nothing edited after the 19:33Z append. PREREG.md sha256 = 94214bbf…
  matches PREREG.sha256; LEAD_NOTE_4.md = b15654a1… as logged.
- Structure: original frozen text (incl. the superseded E1-SKIPPED
  decision) ends line 76; clearly-marked `# AMENDMENT A1 (Lead addendum,
  23/09 19:17Z) - appended, frozen text above untouched` block follows.
  MINOR: the amendment-block sub-hash 983b55f0 could not be reproduced
  from file bytes under any boundary/line-ending variant (likely hashed
  on the in-memory amendment string); the two load-bearing hashes verify.

## Check 4 — W4d Q from census only, before P/L — PASS

- runs/run_census_2b.py:54-57 computes `q = median(dir*meta['a20'])` over
  F0_J DESIGN orders (essence pass) — orders only, no sim/P/L; line 68
  injects `c2["w4d_q"]=q`; orders cached via order_cache.save_orders
  (out/sigs/*.parquet, keyed by DESIGN start) so the P/L run reused
  census-frozen orders; classic.py:126 reads `cfg["w4d_q"]`.
- runs/q_w4d.json: EURUSD −0.006340105631778306, XAUUSD
  −0.0053644141442674665 — matches PREREG_V2.md:49 and RESULTS_v2.md:97.
- Timestamps: census_2b.csv and q_w4d.json mtime 19:13:38.78Z; first
  trades_2b_* 19:14:20.83Z; design_summary_2b.csv 19:14:26.19Z.
  Census strictly precedes all 2B P/L; Q was never re-derived after.

## Check 5 — hand-checked trades — PASS

Re-ran `python runs/handcheck.py`: H0 EURUSD F0_J 10/10 OK, H1 EURUSD
F0_J 10/10 OK, H0 EURUSD F2_NH_b 5/5 OK, H1 EURUSD F2_NH_b 5/5 OK —
"0 mismatches over {10,10,5,5} checked" = 30/30 as claimed.
Methodology is a genuine independent path: handcheck.py:36-88 `recompute()`
replays each sampled order from the cached signal parquet
(out/sigs/…parquet) against raw M1 arrays with its own fill/exit scan
(not a sim.py re-import; shares only friday_flatten + data loading), and
compares fill px, exit px, exit_ctm, reason and pending_px vs both CSVs.
Observed genuine H0/H1 divergence on sig=1320259500 (H0 exit 1.38307 sl
vs H1 exit 1.37000 tp), each matching its own CSV.

## Check 6 — no HOLDOUT access — PASS (with note)

- `allow_holdout` appears only as signatures/defaults (=False) in
  src/data.py:62-96 and src/context.py:73-84; zero call sites pass True.
  LAB_LOG.md contains only seal confirmations, no holdout load.
- out/ contains no validation_summary.csv / val_trades_* / *holdout* files;
  run_validation.py exists but was never run (no outputs) and iterates
  the empty selection anyway. runs/selection.json exists:
  {"selected": [], "n_candidates": 50, "n_pass": 0}, mtime 19:47:13.7Z
  (reported "frozen 19:47Z").
- Max timestamp across every out/*.csv trade artifact = 1684281660 =
  2023-05-17 00:01 srv (out/parity_J_trades.csv), ~14 h BEFORE
  HOLDOUT_START = 1684333392 (2023-05-17 14:23). Nothing crosses the seal.
- INFO note (not a violation): VALIDATION-window bars were loaded —
  (a) the registered J-PARITY control (PREREG.md:32, §6) intentionally
  runs F0_J through 2023-05-17 14:23 = HOLDOUT_START, file written 16:16Z
  as a known-answer harness test; (b) runner.get_ctx builds contexts
  through VALIDATION_END (data plane; only DESIGN signals simulated for
  the research configs). RESULTS_v2 §7 "VALIDATION — NOT READ" is
  accurate for the selection/validation step; the parity control is a
  preregistered exception.

## Check 7 — H1 defined before any H1 P/L — PASS

- Lead addendum A1 timestamped 19:17Z (LAB_LOG.md:15 entry at 19:32Z
  narrates its receipt; PREREG_V2 amendment header "(Lead addendum,
  23/09 19:17Z)"). Earliest H1 artifact:
  out/trades_EURUSD_F0_J_e1.csv mtime 19:30:56.98Z — matches the claimed
  ~19:30:56Z, ~14 min after A1. H1 design summaries 19:31:33-19:31:44Z;
  controls_summary_h.csv 19:45:48Z; selection_table.json 19:47Z.
  The amendment (appended 19:33Z) self-discloses "H1 design P/L existed —
  19:31Z — but controls, selection and validation did not" — accurate.
- sim.py skip_suspect is flag-gated: `skip_suspect: bool = False`
  (sim.py:84); all E1 behaviour sits behind `if skip_suspect and msus[i]`
  or `if skip_suspect:` guards (lines 123, 152-154, 168, 186, 196-197,
  202-205); run_design*.py passes `skip_suspect=(SONIC_E1=="1")` and tags
  outputs _e1. With the flag off the code path is the original H0 path.
- No retro-edit into H0: every H0 artifact predates the H1 run (H0 trades
  19:09:47–19:10:17Z, 2B H0 19:14:20–19:14:26Z, design_summary.csv
  19:10:17Z) and was never rewritten after; handcheck independently
  reproduces H0 CSVs under flag-off semantics.

## Check 8 — selection on BOTH harnesses + both metrics — PASS

runs/select_v2.py confirmed:
- Dual harness: per (sym,cfg) it requires BOTH H0 and H1 rows present
  (line 46-47) and ANDs the gate across h ∈ {H0,H1} (lines 50-64).
- Dual metric: `pf_r_x1>=1.20 AND pf_x1>=1.20 AND pf_r_x15>=1.05 AND
  pf_x15>=1.05` plus `trades_wk>=1.0`, `pos_years/n_years>=0.6`, control
  `pct>=95` on each harness (lines 54-58) — exactly the A1 rule.
- best-of-N: max-PF_R null over all cells (`all_100_cells`) and the
  `ge1trwk` subset (lines 82-107), 10,000 draws each; saved npy files.
- At most 3 advance: `df[df.pass_d5].head(3)` (line 71);
  runs/selection.json = {"selected": [], "n_candidates": 50, "n_pass": 0}.
- Null reproduction: maxpf_null_all_100_cells.npy p50=2.090 p95=2.888
  max=3.270 (reported 2.09/2.89/3.27); ge1trwk p50=1.063 p95=1.151
  max=1.151 (reported 1.06/1.15/1.15); controls_null_h.npz has 88 cells
  (100 − 12 zero-signal cells), 28 in the >=1/wk subset — all as reported.

RESULTS_v2.md §6 selection table vs CSVs (all 6 rows checked):
- XAUUSD F5_S3: PF_R 1.404/1.642, pipPF 1.294/1.488, tr/wk 0.145 — match.
- XAUUSD F5_S3_EXT: 1.364/1.586, 1.252/1.435, pct 98/97 — match.
- XAUUSD F5_S2: 1.149/1.375, 1.106/1.304, pct 100/100, tr/wk 0.52 — match.
- EURUSD F2_NH_b: 1.172/1.192, 1.113/1.136, pct 100/100, tr/wk 2.5 — match.
- EURUSD F1_W3: 1.079/1.194, 1.031/1.147, pct 98/98, tr/wk 0.52 — match.
- XAUUSD F1_PV2a: 0.937/1.076, 0.946/1.127, pct 99/98, tr/wk 0.46 — match.
- Census §5a table vs census_2b.csv: all 16 rows match incl. E2 counts.
- Design §3 and 2B §5b spot rows match the summary CSVs to the printed
  precision (incl. flat2350 numbers: XAU F2_NH_b 0.926→1.038 H0 /
  0.974→1.043 H1; EUR 1.172→1.172).

MINOR table typos (non-load-bearing): XAUUSD F5_S3 pct printed "99 / 97"
vs actual 99/99; EURUSD F2_NH_b "pos-years 2-3/11" (and §10 "pos-years
~25%") matches the XAUUSD row's 2/11-3/11 — actual EUR pos_years are
6/11 (H0) and 7/11 (H1). Neither affects the verdict (both cells fail on
PF/cadence gates regardless).

MINOR: §11 quotes "F5_S3 XAU 1.58 -> 1.67" for flat2350; CSVs show F5_S3
H1 flat = 1.583 and F5_S3_EXT H1 flat = 1.669 — the 1.67 belongs to the
_EXT sibling. Also design_summary_2b.csv (H0) carries no flat2350 columns
(only the _e1 file does), so no 2B H0-flat column exists on disk.

## Overall verdict: PASS-WITH-NOTES

All eight checks pass with direct evidence: corrected E1 diagnostics
reproduce exactly; errata applied to all 50 cells on both harnesses;
PREREG_V2 freeze verifiably precedes first 2B P/L (byte-exact hashes);
Q computed outcome-blind in census before P/L; 30/30 hand-checks replay
clean; HOLDOUT untouched (max artifact ts ~14h inside the seal); H1
defined 19:17Z before first H1 P/L 19:30:56Z with flag-gated machinery;
selection genuinely dual-harness dual-metric and empty.

Issues found (all MINOR, none selection-relevant):
- MINOR: "19x-450x" exit-rate bound is loose — recomputed ≈5.7x-208x
  (3 cells < 19x). Tabled values all exact.
- MINOR: RESULTS_v2 §6 typos — F5_S3 pct "99/97" (actual 99/99);
  EURUSD F2_NH_b "pos-years 2-3/11" quotes the XAU row (actual 6-7/11).
- MINOR: amendment-block sub-hash 983b55f0 not reproducible from file
  bytes (whole-file + frozen-original hashes both verify exactly).
- MINOR: §11 flat2350 "F5_S3 1.58->1.67" conflates F5_S3 (1.583) with
  F5_S3_EXT (1.669); no H0-flat column exists for 2B.
- INFO: VALIDATION-window bars are in the data plane and in the
  registered J-parity control artifact (by design; ends exactly at
  HOLDOUT_START); HOLDOUT itself untouched.
