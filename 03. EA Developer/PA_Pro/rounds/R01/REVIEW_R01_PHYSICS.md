VERDICT: PASS

Adversarial review of R01 Phase B (zone-generator level-physics bake-off), executed
2026-09-20 from the frozen artifacts on disk.  The round survives: freeze order holds,
all frozen hashes reproduce, the ledger is intact and complete, the gate arithmetic
reproduces bit-for-bit, the extraction is causal, and no fill/PnL path exists.  Two
MAJOR process/documentation defects are recorded below; neither is a prereg-rule
deviation, a look-ahead, nor an unlogged trial, so they do not flip the verdict.

Verified SHAs (recomputed, lowercase hex):

| artifact | SHA256 |
|---|---|
| `rounds/R01/PHYSICS_PREREG.md` | `91b21dc7dc5d3701ba5d68904c8621eb7e10df9e1324bf4aae59d26335252184` |
| `docs/CHARTER_ADDENDUM_2.md` | `dcb85c81e4d1755d7fa2dd8ef5fd934e4f2b65c62556308aa6be4f5b964088ce` |
| `docs/CHARTER_ADDENDUM_1.md` | `37756d6922c7134901e94940a10e03ef4e11f7b72418f754d2ceffe525d38592` |
| `PA_PRO_CHARTER.md` | `3c57536848a4aa6113950d06d50331b8c664e18b79d34e08def2f1019bc5dc2c` |
| `rounds/R01/00_LEAD_RULINGS_READ_FIRST.md` | `ce35ed66a6513436d9e1d80f3d7d1a7fc2a67fa5576fe109ad2759d8d8929365` |
| `research/zones/SHORTLIST.md` | `d669410078bc0410ba6addec52386cfd4abbcb0680767c973f1e2741fc3abe2d` |
| `research/zones/REVIEW_ZONE1.md` | `870f8ae66de532cb18d72c64f27206301a7578d9db8f93800cddabcb29b48b16` |
| `rounds/R01/PARITY.md` | `a3dece3575afafa25afdd5e0903fe05db05451b406a1da6e58b5981cc0a9d074` |
| `rounds/R01/FREEZE.json` | `10a9830eb1f34cadc93fd8876f2d311f35fd175af36d974b434ee7330258be44` |
| `zones_code_sha256` | `3676262d514d50cea959944387559471c999578112f651f641fb0ae12cf1c92d` |
| `lib_code_sha256` | `afa4ac305f19cc7aa4daf2acdc70b5e64686e91a6bf3bcc0fc530141120ef87f` |
| `physics_code_sha256` (frozen value) | `d118b72fee2b6e11493386eca5f4fb8b195d801a6e712b297edddc358c290be9` |
| `physics_code_sha256` (current dir, incl. post-freeze `_diag_dist.py`) | `446c33c38d67d952a86525b9ce63b4972f76a0a2750e34e838ef978c6abe8529` |

## (a) What was checked — commands and key verbatim output

Reviewer scripts live in `research/physics/_review/` (read-only except their own dir).

1. FREEZE order and hashes — PowerShell `Get-Item`/`Get-FileHash` + `_review/verify_freezes.py`:
   - `FREEZE.json` CreationTimeUtc = LastWriteTimeUtc = `2026-09-20 15:35:55Z`.
   - All 48 `OUTCOME_*.csv`: earliest CreationTimeUtc/LastWriteTimeUtc = `2026-09-20 15:36:03Z`.
   - Last `EVENTS_*.csv`/`CONTROLS_*.csv` mtime = `2026-09-20 15:35:19Z` / `15:35:22Z`.
   - Script output: `prereg_sha256: MATCH`, all 8 metadata hashes MATCH, `tables checked: 48 mismatches: 0`, `zones_code_sha256: MATCH`, `lib_code_sha256: MATCH`, `physics_code_sha256(excl _diag_dist.py): MATCH d118b72f…`.
   - Cache stamps: `cache files checked=40 mismatches=0` (size+mtime vs FREEZE `data_files`).
2. Ledger — `pa_ledger.verify()` printed `(True, None)`; 27 lines, exactly 6 `R01 PHYSICS DESIGN`, ids `T000022..T000027`, `spec_ok=True`, `code_ok=True`, `n` = 30782/19031/16009/3288/7450/18218; every `key_metrics` field equals `STATS.json` (`metric mismatches: 0`); `params.freeze_sha256` == recomputed FREEZE sha for all 6; no `sealed_read` lines.
3. Gate arithmetic (independent code `_review/gate_recompute.py`, csv+own bootstrap): all six pooled bounce cells MATCH `STATS.json` exactly, e.g.
   `line1_cluster MATCH D_top mine=-0.05547985 stats=-0.05547985 CI mine=[-0.068589,-0.042550] stats=[-0.068589,-0.042550] p mine=1.00000 stats=1.00000`.
   Continuation endpoint also MATCH (kde_swing `D_cont=+0.286685 [+0.241082,+0.331179]`), descriptive `contam`/`S_CLEAN`/`S_NEAR` MATCH with identical `n`. BH q-values recomputed independently at q=0.10 (`_review/final_checks.py`): `BH MATCH: True` (bounce q=1.0 not rejected; all six cont q=0.0002 rejected).
4. Look-ahead:
   - `phys_extract.py:77-110` reads only `idx = arange(created..t)`, `A[t]`, `c[t-1]`, band at `j<=t`; side rule `cp<=lo[k]`/`cp>=hi[k]`; freshness window `ins[w0:k]` = `[t-24, t-1]`; away scan `[t-24, t-1]`.
   - `phys_resolve.py:57` outcomes start `j0 = t + 1` (first bar `t+1`); continuation `k0 = break_bar + 1`.
   - `phys_controls.py:249-276` anchor `R5` reads `[t-1440, t-1]`; forward read `[t, t+1440]` exists only to construct the fake event (declared design); controls CSV/records carry no real outcome fields.
   - Field check against real bars (EURUSD, 32,452 events, all 6 generators): `bar_t=0 m=0 close_prev=0 close_t=0 intersect=0 side=0` bad. Static-band freshness/away mismatches appear only in the three mutable-band generators (line1 717/133, fractal 31/33, kde 81/23) and are exactly `0` for the three immutable-band generators (profile_va, sd_base, ref_levels) — the signature of correct causal band history, not look-ahead.
   - Full re-extraction (`_review/reextract_check.py`): `fresh rows: 10595 frozen rows: 10595`, `row mismatches: 0`, `counters match extract: True`.
   - Parity rerun (write redirected to `_review/PARITY_RERUN.md` so frozen `PARITY.md` was not touched): all six EURUSD generators `200 bars, 0 mismatches (0.0000%) PASS`.
5. Outcomes ↔ frozen tables: all 48 `OUTCOME_*.csv` are row-identical to the frozen `EVENTS/CONTROLS` on shared columns (`files compared: 48; mismatching files/rows: 0`); outcome window sanity `outcome files checked: 48; window violations: 0`; `EVENTS/CONTROLS files with outcome columns: 0`; `event years: [2016..2021]`.
6. Results consistency (`_review/results_consistency.py`): main table 6/6 MATCH, descriptive table 6/6 MATCH, gate-detail lines 6/6 MATCH against `STATS.json`.
7. Post-run diagnostic (`_review/diag_and_cont.py`): `real dist pips: med 3.78 p25 2.06 p75 6.59`, `ctrl dist pips: med 29.76 p25 19.27 p75 49.40`, `tk_dt: same-bar 0.021 (n=39495) <=288 0.646` — exactly the numbers in `PHYSICS_RESULTS.md:71-73`.
8. Tests: `python -m pytest "03. EA Developer\PA_Pro\research\physics\tests" -q` → `31 passed in 4.09s`, exit 0.
9. Fill-free: `rg -i "pnl|profit|fill|order_|trade_|equity|drawdown|expectancy|pa_fill|pa_eval"` over `research/physics/*.py` returns only the results disclaimer `phys_analysis.py:432` and the read-only cache path `phys_freeze.py:22`; no economic code path.

## (b) Findings by severity

**MAJOR — claimed freeze guard is not implemented.** `phys_analysis.py:4-6` states resolve
"refuses to run unless FREEZE.json exists **and is older than the CSV tables**", and
`run_bakeoff.py:8-9` states verify "refuses if FREEZE.json is older than the CSV mtimes";
but `phys_analysis.py:56-59` (`_freeze_ok`) checks existence only. No actual violation
occurred — mtimes and ctimes prove the order — but the declared guard is absent, so a
future rerun could resolve before a freeze without being stopped. Fix in R02 (changing it
now would alter the frozen `physics_code_sha256`).

**MAJOR — winner-rule text ambiguity around the continuation passes.**
`STATS.json` `kde_swing.cont_gate.pass=true`, `ref_levels.cont_gate.pass=true`, both with
`bh_cont.rejected=true` (q=0.0002), and `PHYSICS_RESULTS.md:19,22` print `PASS` in the
`cont gate` column; but `PHYSICS_RESULTS.md:49-51` narrows "threshold passers" to
"(charter + BH q<=0.10, **bounce endpoint**)" and declares `WINNER: NONE / LINES MATTER not
supported`, and `phys_analysis.py:268` builds `passes` from the bounce gate only. The
prereg says the same thresholds apply to the continuation analogue (`PHYSICS_PREREG.md:207-213`)
and that "a generator's **endpoint** is a pass" (212-213), while the winner rule ranks by
`D_top` (primary endpoint) with materiality measured in `D_top` (217-224). Under the
primary-endpoint reading — the only self-consistent one, since the ranked leader's margin
is a `D_top` quantity — `WINNER: NONE` is mechanical, and SHORTLIST §4 item 3
(`research/zones/SHORTLIST.md:313-315`) explicitly says the baseline is not promoted on a
FAIL. However, the results file never states this interpretation, so a reader sees two
continuation passes next to a FAIL with no explanation. Lead ruling/clarification advised;
not a prereg-rule change, not cherry-picking (all columns are printed).

**MINOR — estimand quote is not word-identical to the only Lead-authored text in the repo.**
`PHYSICS_PREREG.md:65-68` (and `PHYSICS_RESULTS.md:7`) say "an arbitrary level **with** the
same geometry"; `CHARTER_ADDENDUM_2.md:20` item 3 says "an arbitrary level **of** the same
geometry". The prereg attributes its quote to "Lead ruling R01-C1 §2", which is not in the
repo (`rg R01-C1` finds only references), so the verbatim claim cannot be fully verified.
Semantics are identical; recorded for the Lead, not treated as a rule change.

**MINOR — Notes wording.** `PHYSICS_RESULTS.md:63` says "All 12 hypotheses … are ledger
trials (family=PHYSICS)" while the ledger holds 6 lines, one per generator with both
endpoint metrics. This matches prereg §0.7 (`PHYSICS_PREREG.md:52-55`, "12 hypotheses are
fields of those trials, not extra trials"); only the wording is loose.

**INFO — frozen `physics_code_sha256` no longer reproduces from the directory.**
`research/physics/_diag_dist.py` was created at `2026-09-20 22:37:47` local (`15:37:47Z`),
after the freeze; `dir_code_sha256` includes it. Excluding that one diagnostic file, the
directory hashes exactly to the frozen `d118b72f…`, so every core frozen module is
unchanged and the ledger's `code_sha256` is correct. The frozen "physics code" hash also
covers diagnostics (`run_counts.py`, `_diag_*.py`), which is worth narrowing in R02.

**INFO — diagnostic timestamp vs file mtime.** `PHYSICS_RESULTS.md:67` says the section was
"added 2026-09-20T15:44Z"; the file's LastWriteTimeUtc is `2026-09-20 15:38:42Z`, i.e.
earlier than the claimed add time. Content was independently verified; provenance of the
timestamp only.

**INFO — stale pilot script frozen into the tree.** `run_counts.py:126-128` calls
`extract_controls` with the pre-Addendum-2 signature (positional `A, A_valid, symbol,
r5_cap=`), which does not match `phys_controls.extract_controls(events, src, ref, bars,
symbol)`; running `run_counts.py --controls-for ...` today would raise `TypeError`. It is
not on the outcome path (outcomes came from `run_bakeoff.py build`).

**INFO — cosmetic.** `PHYSICS_RESULTS.md:3` renders "DESIGN DESIGN"
(`f"DESIGN {freeze['split']}"`, `phys_analysis.py:333`). `PHYSICS_PREREG.md:41-47`
expected `profile_va` to be UNDERPOWERED; it measured 3,288 resolved events and the
≥1,000 floor was applied as written — expectation, not rule.

## (c) Verdicts on the six required axes

- FREEZE order: **PASS** — FREEZE 15:35:55Z < first outcome 15:36:03Z (ctime and mtime);
  prereg SHA and all 48 table hashes reproduce; cache stamps untouched.
- Prereg fidelity: **PASS** — §5 control rule is character-identical to Addendum 2 item 2
  (normalized containment check `control-rule sentence identical: True`); floors ≥1,000/≥60,
  BH 6×2 at q≤0.10, +5.0pp and +2.0pp are as SHORTLIST §4; one MINOR one-word estimand
  transcription difference vs Addendum 2 item 3 (see findings).
- Look-ahead: **PASS** — real-event features use bars ≤ t only, outcomes start at t+1,
  control forward reads are the declared construction path with no outcome fields; parity
  rerun 0/200×6; full re-extraction reproduces the frozen table; immutable-band generators
  show zero freshness/away violations.
- Ledger integrity: **PASS** — `(True, None)`, exactly 6 new trials `T000022..T000027`,
  one per generator, `spec_sha256` = prereg SHA, metrics = STATS, freeze SHA recorded.
- Gate arithmetic: **PASS** — independent recomputation matches every pooled/cont/descriptive
  number and every gate boolean; BH reproduced.
- Claim consistency: **PASS** with the MAJOR interpretation caveat — no generator dropped,
  no stratum swapped, all printed numbers match `STATS.json`, the post-run diagnostic is
  correctly labelled "not a gate", and the FAIL language matches the prereg's non-overstatement
  sentence; the continuation passes need an explicit Lead interpretation note.

## Could not verify

- The verbatim text of Lead ruling R01-C1 §2 (not in the repo); the estimand was checked
  against Addendum 2 item 3 only.
- That the post-run diagnostic section was authored at the stated `15:44Z` (mtime predates it).
- Full 4-symbol re-extraction/causal replay for all six generators (performed for
  `line1_cluster` EURUSD only, plus parity and the immutable-band static checks).
