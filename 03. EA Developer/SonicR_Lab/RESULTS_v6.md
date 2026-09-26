# RESULTS v6 — ROUND 2F: London AM vs PM for F2_NH_b (+A2F addendum)

Round 2F, Lead brief 22:50Z + addendum A2F 23:47Z. One hypothesis: NH_b
trades signalled in the London morning (07-12 London) earn more than
afternoon (12-16). Confirm on C, then one VALIDATION read.
PREREG_V6 sha256 `c3e9b29205863c20f06ca76c29988a58a3de4179cf18e4cb0b01551af9418f70`,
frozen 2026-09-23T22:35:03Z — before any C AM/PM P/L file and before
any VALIDATION access.

## Errata 1 — UK DST edge fix (step 1)

`_last_sunday` returned the 1st-of-next-month when that day was itself
a Sunday, placing the UK transition one week late (Mar 2012, Mar 2018,
Oct 2015, Oct 2020 — the last inside VALIDATION). Fixed in data.py;
DATA.md Oct/Nov US-UK gap corrected -1h -> -3h.
T0 (tests/test_dst_fix.py, 6/6): hand-computed London hours for all
four years, both US/UK gap directions, Friday-flatten bug-week check.

Before/after (_dstfix vs 2C/2D X0-HOLD files, all 12 syms, H0/H1):
per cell 0-4 signals gone + 0-4 new + 1-3 trades with changed r_x1.
Every changed row is inside a bug week (signal moved in/out of
london_ext; Friday flatten shifted ±1h) or is a one-position-book
cascade from those weeks. Max share changed: 1.11% (EURUSD H1,
13/1173) — marginally over the ~1% guard; verified row-by-row benign,
all changes are the mechanical consequence of the correct fix. PF_R
moves ≤0.005 on every cell. Full table: out/dstfix_diff_2f.csv.
A counting artifact (float-repr noise ~1.8e-15 between live df and
CSV) briefly reported ~20% — real r_x1 changes are 1-3 per symbol.

## Errata 2 — zone-engine look-ahead (A2F)

SwingZones._advance(t) only moves forward; zones_at(t) filtered
`t - i <= max_age` but not `conf <= t`, so a second orders_for() on the
same cached ctx saw future-confirmed swings (and scanned a huge list —
the free-running slowdown). regen_2f was clean (one call per fresh
ctx). Fixed at the call site: orders_for() calls ctx.reset_zones()
first; zones_at() semantics untouched (F1/F5 PV look-back relies on
them). orders_for results now cached per (sym,window) under key
'F2_NH_b_dstfix'.

- T6: DESIGN orders generated AFTER a VALIDATION-window generation on
  the same ctx == fresh-process orders, every field — F2_NH_b (n=3480)
  and F0_J (n=1056). PASS.
- T7: EURUSD + AUDJPY x H0/H1 regenerated fresh == _dstfix files
  row-for-row (1e-9). PASS.

## Errata 3 — 2C portfolio week/year fixes (reporting)

Account-cap week was epoch-Thursday buckets; now London calendar week
(Monday 00:00). Year was `//365` (leap drift ~12d by 2020); now true
London calendar year. 2C rerun (out/portfolio_2c_wkfix.csv):

| cfg | harness | mode | PF_R was | PF_R now | MC DD was | MC DD now |
|---|---|---|---|---|---|---|
| F2_NH_b | H1 | capped 5/wk+3 open | 1.11 | 1.017 | ~59-81R | 138.0R |
| F2_NH_b | H0 | capped | 1.17* | 1.031 | — | 130.5R |

(*2C reported capped ~1.17/1.11 — the Thursday-start week buckets had
grouped weekend fills differently; the corrected cap admits slightly
different trades. Conclusion unchanged direction-wise; magnitudes were
overstated.)

## Tests

- T0 DST: 6/6 (see Errata 1).
- T1 fixed list: _dstfix files only; join (sym,sig_ctm,dir) 0 unmatched.
- T2 outcome-blind: AM share ~63% of signals per sym, stable per year.
- T3 discovery recompute on D (allowed): H1 AM 1.150 / PM 0.965
  (n 5535/2913); H0 1.138 / 0.930; AM>PM 9/11 years H1, 6/7 syms —
  matches the Lead's numbers within the DST-fix deltas.
- T6/T7: see Errata 2.

## Power (computed on D BEFORE touching C; logged after the cancel)

sep_D(H1)=+0.1198, bootstrap sd=0.0385 → P(K1-K3 pass)=0.731,
P(V1-V3 pass)=0.817 if C/Val behave like D; at half effect 0.255/0.296.

## Confirm on C (fixed list, DESIGN window) — ALL GATES PASS

| harness | n_AM | n_PM | PF_R AM x1 | PF_R PM x1 | PF_R AM x1.5 | exp AM | exp PM | sep | sep LB95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | 3769 | 2115 | 1.098 | 0.921 | 1.049 | +0.063 | -0.053 | +0.115 | +0.038 |
| H0 | 4264 | 2195 | 1.056 | 0.923 | 1.012 | +0.039 | -0.052 | +0.091 | -0.037 |

- K1 PASS: H1 sep LB95 +0.038>0; H0 sep +0.091>0.
- K2 PASS: AM>PM on 5/5 C syms H1 (NZD 1.063/0.966, CAD 1.117/0.821,
  EURJPY 1.142/0.971, AUDJPY 1.078/1.004, EURGBP 1.086/0.855).
- K3 PASS: sep longs +0.126, shorts +0.104 (H1); AM>PM in 8/10 full
  years (corrected calendar year; 7/10 under the old count — both >=6).
- Reporting: gross AM 1.204 vs PM 1.018 (H1) — the gap exists before
  costs; ex-Friday sep +0.127 / Friday-only +0.049 (H1); swap column
  AM PF_R 1.084 (H1).
- Free-running AM-only C (report): H1 pf 1.10-1.14 per sym (median
  ~1.13); H0 median ~1.10, USDCAD 0.84.

## VALIDATION — read ONCE at 2026-09-23T23:54:00Z (logged)

Window (DESIGN_END, VALIDATION_END] = 2020-01-15 .. 2023-05-25 approx.
HOLDOUT guard test passed (holdout read raises). No symbol dropped
(coverage >90% all 12). Book started empty; indicators warmed on
DESIGN; window-end exits = "window_end" at the last loaded bar.

### V1 — FAIL (needs BOTH harnesses, BOTH modes)

| mode | harness | AM PF_R x1 | exp AM | AM PF_R x1.5 | verdict |
|---|---|---:|---:|---:|---|
| fixed | H1 | 1.125 | +0.080 | 1.078 | pass |
| fixed | H0 | **0.874** | **-0.110** | 0.844 | FAIL |
| free | H1 | 1.160 | +0.101 | 1.111 | pass |
| free | H0 | **0.905** | **-0.081** | 0.873 | FAIL |

### V2 — PASS: AM PF_R > 1.00 on 10/12 syms (H1 fixed; need >=7).
Failures: AUDUSD 0.852, USDCAD 0.789.

### V3 — PASS: sep=+0.163 on H1, LB95=+0.085>0.

### Per-year AM PF_R (H1, fixed list)

2020: 1.297 | 2021: 0.991 | 2022: 1.064 | 2023: 1.253 (partial years).
PM buckets: 0.800 / 0.936 / 0.879 / 0.860 — the AM-PM split persists on
H1 in every validation year.

### The H0/H1 divergence (honest reading)

On DESIGN the gap held on both harnesses (H0 AM 1.14/PM 0.93). On
VALIDATION H0 AM collapses to 0.87 while H1 AM is 1.12. The suspect
rollover bars are denser/wilder in 2020-2023 (crypto-era spreads); AM
trades' multi-day holds cross more roll windows, so fabricated bars hit
them asymmetrically. H1 (which voids suspect bars) says the edge is
real and replicating; H0 says a data-quality artifact can flip it. The
frozen gate demands both → NOT VALIDATED. This is the protocol working:
the borderline case (C pass + H1 validation pass) does not get waved
through.

## Portfolio views (AM-only free-running, 1R/trade)

(a) EURUSD+XAUUSD account:
| window | harness | trades/wk | PF_R | MC DD P95 | +swap PF_R |
|---|---|---:|---:|---:|---:|
| DESIGN | H1 | 3.59 | 1.132 | 70R | 1.092 |
| VALIDATION | H1 | 3.37 | **1.390** | 36R | 1.353 |
| VALIDATION | H0 | 3.77 | **0.507** | 837R | 0.500 |

(b) all-12 account:
| window | harness | mode | trades/wk | PF_R | MC DD P95 |
|---|---|---:|---:|---:|---:|
| DESIGN | H1 | uncapped | 20.5 | 1.145 | 98R |
| DESIGN | H1 | capped 5/wk+3 | 5.00 | 1.087 | 96R |
| VALIDATION | H1 | uncapped | 21.4 | 1.160 | 76R |
| VALIDATION | H1 | capped | 4.99 | **1.219** | 47R |
| VALIDATION | H0 | capped | 5.02 | 1.220 | 57R |

Positive-year shares 1.00 on H1 uncapped both windows.

## Verdict

**K1-K3 all pass on C; V1 fails on H0 (both modes) -> the AM-only
filter is NOT promoted.** The effect is real and replicating on clean
data (H1: sep +0.163, 10/12 symbols, every validation year), but the
preregistered both-harness rule is the guard against exactly this
class of artifact, and it fired.

## Next approaches for the Lead

1. **Quantify how much of the H0 collapse is fabricated bars** — rerun
   validation H0 with suspect bars voided but no other E1 rules; if AM
   H0 jumps to ~1.1, the failure is purely data quality and the
   strategy is tradable on a clean feed (round-3 measures real roll
   spreads anyway). If it stays ~0.9, the AM edge is genuinely fragile.
2. **If promoted to paper only via H1-style hygiene**: an AM-only NH_b
   on EURUSD+XAUUSD did 3.4-3.8 trades/week/account at PF_R 1.39 on
   validation years — but only with suspect bars skipped live
   (impossible in real time) or with the real rollover spread measured.
3. **Pull-back quality filter** (carried from 2E): depth/duration of
   the leg-2 pullback is orthogonal to session and may stack with AM.

## Repro

- runs/regen_2f.py, label_2f.py, confirm_2f.py, verify_2f.py,
  free_2f.py, validation_2f.py, portfolio_2c_wkfix.py
- out/trades_2f_*_dstfix*.csv, labels_2f_*.csv, confirm_2f_*.csv,
  trades_2fval_*.csv, val_2f_*.csv, portfolio_2f.csv,
  portfolio_2c_wkfix.csv, dstfix_diff_2f.csv
- LAB_LOG.md timestamps throughout.

---

# RESULTS_v6 — E0' correction (A3F/A4F addendum, 24/09 00:42Z)

Status: **PROVISIONAL.** VALIDATION was already read once (23:54Z);
this is the same single read with a data-validity bug fixed, not a new
decision. It answers "was the H0 V1 failure caused by malformed
prints?" — it cannot confirm the idea. Promotion only via the sealed
HOLDOUT with E0' frozen. Everything above this section is the first
computation, untouched.

## The bug and the rules considered

The Lead found H0 V1 was decided by one impossible print: EURUSD AM
short (sig 2020-05-04) SL'd at 2.65536 on the second-stamped bar
2020-05-07 12:33:04, R = -810.4; plus a bogus +57.7R winner
(2022-10-19 13:47:44, TP at 0.6808).

- LEAD_NOTE_5 E0 (>3% dev AND <0.5% revert at +15min): WITHDRAWN. The
  scan flagged 238 bars incl. real events (SNB, GBP-2016, JPY-2019,
  XAU-2021 flashes, Brexit/ECB bars, NZD Black-Monday) and >20/sym-
  window on XAUUSD(50)/AUDJPY(33). Backup-plan stop at 00:25Z was
  correct. Kept only as an INVALID sensitivity cell.
- LEAD_NOTE_6 E0' (frozen): void every non-minute-aligned M1 bar —
  format rule, no price, no future data. 15 bars total (EURUSD 6,
  GBPUSD 5, USDCAD 4), all corrupt-ladder prints, all already
  suspect=True (H1 unchanged; E0' bites H0 only).
  sha256 c17bff6a... logged in LAB_LOG 00:34:32Z before any output.

## Tests

T10 (+T8/T9 kept): 8/8 pass — both V1-deciding bars and the
2019-12-01 18:01:36 gap-side print flagged; no minute-aligned bar
flagged; zero-flag windows reproduce existing files row-for-row.

## Changed-trade audit (two-sided)

| window | sym | sig | r_old | r_new | verdict |
|---|---|---|---|---|---|
| DESIGN | GBPUSD | 2012-03-19 | -1.06 | -1.15 | hurt |
| DESIGN | GBPUSD | 2014-05-20 | -1.04 | -0.36 | helped |
| DESIGN | USDCAD | 2015-04-01 | -233.28 | -1.04 | helped |
| VALID | EURUSD | 2020-05-04 | -810.41 | +4.39 | helped |
| VALID | EURUSD | 2022-10-19 | +57.67 | +1.65 | hurt |
| VALID | EURUSD | 2022-10-20 | -1.09 | removed | helped |
| VALID | USDCAD | 2020-04-09 | +132.15 | +0.63 | hurt |

helped 4 / hurt 3. All other files identical (E0' is surgical).
The -810R trade was actually a +4.39R TP that the bogus bar killed.

## C confirm K1-K3 (e0s vs first computation)

| gate | first comp | E0' | verdict |
|---|---|---|---|
| K1 | H1 sep .1151 lb95 .0376; H0 sep .0914 lb -.0374 | H1 same; H0 sep .1459 lb95 .0661 | PASS both |
| K2 | AM>PM 5/5 | 5/5 | PASS |
| K3 | H1 long .126 short .104; AM>PM 8/10y | same (H0 .151/.140) | PASS |

## VALIDATION V1-V3 (provisional, both modes)

| cell | first comp (no E0) | E0' |
|---|---|---|
| V1 fixed H1 | pf 1.1249 exp +.0801 x15 1.0781 | identical |
| V1 fixed H0 | pf 0.8737 exp -.1100 FAIL | **pf 1.1446 exp +.0940 PASS** |
| V1 free H1 | pf 1.1598 exp +.1014 x15 1.1114 | identical |
| V1 free H0 | pf 0.9046 exp -.0805 FAIL | **pf 1.1625 exp +.1049 PASS** |
| V2 | AM>1 10/12 | 10/12 PASS |
| V3 | sep H1 +.1627 lb95 +.0853 | identical PASS |

Per-year AM PF_R H0 e0s: 2020=1.334, 2021=1.020, 2022=1.110,
2023=1.133 — positive every year. H1 unchanged (1.297/0.991/1.064/
1.253).

## Sensitivity (V1-V3 verdict per cell)

| variant | V1 both modes | V2 | V3 | note |
|---|---|---|---|---|
| (i) no E0 | FAIL (H0 -810R) | pass | pass | first computation |
| (ii) E0' (rule) | PASS | PASS | PASS | provisional |
| (iii) price-E0 3%/15m | would pass | pass | pass | INVALID: voids real events (SNB, flashes) |

Under (iii) numbers are similar (H0 fixed 1.1400/+.0911, free 1.1599)
because the real-event bars it wrongly voids sat outside NH_b trade
paths; the rule is still invalid — it is a sensitivity row only.

## Extreme-trade audit (|r_x1|>5)

1424 rows audited (DESIGN+VALIDATION, H0/H1, i vs ii). Four extremes
changed under E0': -233.3R USDCAD DESIGN, -810.4R and +57.7R EURUSD
VAL, +132.2R USDCAD VAL — every one resolves to a normal R or
removal. All other ±5R trades identical. Full list:
out/extreme_2f_audit.csv; diffs: out/e0s_diff_design.csv,
out/e0s_diff_val.csv.

## Portfolios (E0', free-running AM-only)

| view | window | harness | trades/wk/acct | PF_R | MC DD P95 |
|---|---|---|---|---|---|
| EUR+XAU | VALIDATION | H1 | 3.37 | 1.390 | 36R |
| EUR+XAU | VALIDATION | H0 | 3.76 | 1.342 | 37R (was 0.507/837R) |
| EUR+XAU | DESIGN | H1 | 3.59 | 1.132 | 70R |
| EUR+XAU | DESIGN | H0 | 3.94 | 1.050 | 109R |
| all12 capped | VALIDATION | H1 | 4.99 | 1.219 | 47R |
| all12 capped | VALIDATION | H0 | 5.02 | 1.144 | 57R |
| all12 uncapped | VALIDATION | H1 | 21.4 | 1.160 | 76R |
| all12 uncapped | VALIDATION | H0 | 23.5 | 1.162 | 82R |

(swap versions in out/portfolio_2f_e0s.csv; caps: 5/wk, max 3 open,
first-come, London Monday weeks.)

## H0-minus-H1 residual after E0' (the round-3 question)

Per sym/window: ~165-560 trades touched suspect bars; exits inside
roll windows ~= suspect-touch counts (VAL EURUSD 165/165, r_susp
-1.0R; DESIGN XAUUSD r_susp -180R). The rollover-spike population is
still the open question — E0' only removes malformed records, the
session-open wicks remain tradable on H0 by design.

## Repro additions

- src/e0.py (second_stamp + withdrawn price-E0 engine), sim.py
  void_extra; runs/e0_scan.py, runs/rerun_2f_e0s.py;
  tests/test_e0.py T8-T10; E0_BARS.md; out/e0s_*, e0s_diff_*,
  confirm_2f_e0s_pooled.csv, val_2f_e0s_*, sens_2f_pooled.csv,
  extreme_2f_audit.csv, h0h1_residual.csv, portfolio_2f_e0s.csv.
