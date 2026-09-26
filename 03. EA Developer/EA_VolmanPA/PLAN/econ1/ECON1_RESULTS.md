# ECON1_RESULTS — first economic baseline of frozen DR3 (DESIGN 2016-2021)

Prereg `research/VPA-DR3_ECON1_PREREG.md` SHA256 `644DBCBA91B9859AF598906C8BB9C7D8CAB034CBCE99675554B48938C5BE9663` (mtime 17:52:06, before every file in this directory). DR3 code SHA `73497484E2C26EDF44DAE5F1D574C56BBF40BBBFE8192A05AD38B4D782A781E0`. ONE verdict run (G4): no parameter changes, no variants.

Frame: 2016-01-03T22:25:00Z → 2021-12-31T21:00:00Z (440040 M5 bars, 2208641 M1 bars). VAL/OOS/HOLDOUT not loaded (G5).

Signals: 4331 DR3-accepted; matched subset 4216 (115 signal bars sit outside the session windows while their trigger bar is inside; the lift uses the matched subset). Random: K=20 → 84320 entries, 42257 fills.

## 1. Verdict (G6)

| gate | scenario | value | threshold | verdict |
|---|---|---|---|---|
| PF x1 > 1.30 | x1 | 0.795 | > 1.3 | FAIL |
| PF x1.5 >= 1.25 | x1.5 | 0.720 | >= 1.25 | FAIL |
| PF x2 >= 1.00 | x2 | 0.667 | >= 1.0 | FAIL |
| gross PF >= 1.10 | gross | 0.992 | >= 1.1 | FAIL |
| N >= 500 | x1 | 2436 | >= 500 | PASS |
| max DD <= 6% | x1 | 84.192 | <= 6.0 | FAIL |
| b >= 1.70 | x1 | 1.839 | >= 1.7 | PASS |
| LIFT x1 >= +14.1pp | x1 | +0.24pp (CI [-1.61, +2.14]) | >= 14.1 | FAIL |
| LIFT x2 >= +18.2pp | x2 | +1.49pp (CI [-0.29, +3.34]) | >= 18.2 | FAIL |

**VERDICT: FAIL** (G6: any gate fails → FAIL; the Lead escalates to the Owner).

## 2. Metrics per cost scenario

| scenario | N | WR | PF | b | exp R | total R | max DD @0.5% | TP/SL/DAILY/FRIDAY/MIDNIGHT/DATA_END |
|---|---|---|---|---|---|---|---|---|
| gross | 2436 | 34.98% | 0.992 | 1.842 | -0.0051 | -12.4 | 38.96% | 714/1504/156/61/1/0 |
| x1 | 2436 | 30.17% | 0.795 | 1.839 | -0.1385 | -337.5 | 84.19% | 617/1618/139/61/1/0 |
| x1.5 | 2436 | 28.37% | 0.720 | 1.819 | -0.1950 | -474.9 | 91.81% | 574/1671/132/58/1/0 |
| x2 | 2436 | 26.97% | 0.667 | 1.807 | -0.2373 | -578.0 | 95.03% | 546/1710/126/53/1/0 |

Matched random (same engine/bracket):

| scenario | N | WR | PF | b | lift vs DR3 | 95% CI |
|---|---|---|---|---|---|---|
| gross | 42257 | 34.56% | 0.971 | 1.837 | +0.44pp | [-1.49, +2.41] |
| x1 | 42257 | 29.94% | 0.783 | 1.832 | +0.24pp | [-1.61, +2.14] |
| x1.5 | 42257 | 27.58% | 0.695 | 1.825 | +0.83pp | [-0.98, +2.70] |
| x2 | 42257 | 25.52% | 0.625 | 1.822 | +1.49pp | [-0.29, +3.34] |

Signal status counts (cost-independent): `{"CANCELLED": 165, "EXPIRED": 1708, "FILLED": 2436, "VETO_FRIDAY": 22}`

## 3. Equity / DD summary (x1)

- Fills 2436; final equity at 0.5%/trade: **17.6%** of start; max DD **84.19%** (gate ≤ 6%).
- Gross (no cost) final equity 88.9%, max DD 38.96%.
- Realised b 1.839 (gate ≥ 1.70 PASS); the failure is the win rate, not the payoff.

## 4. Per-year (x1 fills)

| year | N | WR | PF | total R |
|---|---|---|---|---|
| 2016 | 408 | 29.4% | 0.802 | -56.5 |
| 2017 | 422 | 28.7% | 0.757 | -71.0 |
| 2018 | 444 | 33.1% | 0.956 | -12.9 |
| 2019 | 378 | 32.0% | 0.840 | -39.0 |
| 2020 | 375 | 26.1% | 0.617 | -101.8 |
| 2021 | 409 | 31.3% | 0.791 | -56.4 |

## 5. EXPLORATORY (no effect on the verdict; DR4 hypotheses only)

Baseline x1: WR 30.17%, PF 0.795, N 2436.

| feature | low | mid | high |
|---|---|---|---|
| room_r (q1=0.562, q2=0.713) | N267 WR33.3% PF0.87 | N265 WR34.0% PF1.00 | N264 WR32.6% PF0.86 |
| ema_dist_atr (q1=1.27, q2=1.69) | N268 WR36.2% PF0.98 | N265 WR29.8% PF0.75 | N266 WR33.5% PF0.98 |
| gap_atr (q1=0, q2=0) | N2428 WR30.2% PF0.80 | N0 WR0.0% PF0.00 | N8 WR25.0% PF0.67 |
| squeeze=1 vs 0 | N20 WR25.0% PF0.46 | N2416 WR30.2% PF0.80 | — |
| lunch=1 vs 0 | N412 WR30.1% PF0.75 | N2024 WR30.2% PF0.81 | — |
| pressure=1 vs 0 | N290 WR32.1% PF0.81 | N2146 WR29.9% PF0.79 | — |
| session | eu: N1120 WR28.7% PF0.80 | us: N1316 WR31.5% PF0.79 | | |
| setup | combi: N6 WR16.7% PF0.40 | pattern_break: N2430 WR30.2% PF0.80 | | |
| side | long: N1197 WR29.0% PF0.75 | short: N1239 WR31.3% PF0.84 | | |

Sensitivities (same trades, no re-run):

- News-window exclusion (12:25-12:45 / 13:25-13:45 UTC): removes 107 fills → N 2329, WR 30.31%, PF 0.798.
- HYP §3.3 gap recheck (>0.3 ATR): would remove 0 fills → N 2436, WR 30.17%, PF 0.795.
- Thursday/Friday calendar deviation (see §6): excluding the 61 FRIDAY-reason fills → N 2375, WR 29.56%, PF 0.784 (the deviation is slightly favourable to DR3; verdict unchanged).

No outcome fields other than the trade P&L are present; the run is DESIGN-only (G5).

## 6. DEVIATIONS & CORRECTIONS (post-review, no re-simulation)

1. **Recorded prereg SHA was a 63-char transcription error.** The file's true SHA256 is `644DBCBA91B9859AF598906C8BB9C7D8CAB034CBCE99675554B48938C5BE9663` (mtime 17:52:06, earlier than every outcome file — the ordering evidence is the file hash + mtime, both verified). The wrong string was recorded in `vpa_econ1_run.py:29`, `vpa_econ1_explore.py:21`, this file's §0 line and `ECON1_METRICS.json`'s `prereg_sha`; all four were corrected after review round 1. The prereg itself was NOT edited after the freeze.
2. **Thursday/Friday calendar deviation (inherited from the frozen P1 baseline).** The weekday formula `((t//86400)+4)%7` used by `vpa_random_baseline.py:157` and inherited by `vpa_econ1_sim.py` is Sunday=0, so the `dow == 4` branch labelled "Friday" fires on **Thursday** 20:00 server. Effect: the Friday veto (22 signals) and the FRIDAY flat (61 exits) act on Thursday; real Friday 20:00 has no special flat (the DAILY 22:00 flat still caps the day). The DR3 and matched-random sides use the identical rule, so the LIFT is unaffected; the sensitivity above shows the verdict is unaffected (PF 0.784 vs 0.795). Per G4 (one run) the semantics were NOT re-run; a corrected `dow` is a DR4 fix.
3. `TRADES_DESIGN.csv` holds the x1 fills (one row per fill, with `cost_mult`/`cost_pips` and the exit reason); the gross/x1.5/x2 aggregates are in `ECON1_METRICS.json` from the same run.
4. 115 of the 4,331 DR3 signals have their SIGNAL bar outside the session windows while their trigger bar is inside (the DR3 session gate is measured at the trigger bar). The matched-random universe skips those signal bars; the LIFT therefore uses the matched subset (4,216 signals); the strategy metrics use all fills.
5. Within-bar assumption: the exit scan includes the fill M1 bar itself (SL-before-TP inside it), matching the frozen baseline convention — not intra-bar path truth.
