# GATE A evidence — HYP candidate: European-morning USD bid (EURUSD short)

Status: Stage-0 evidence pack for advisory review (Data-Integrity +
Quant-Methodologist). NOT a prereg. All numbers from `lab/` plane
(hcc_reader v3, suspect-flagged, plausibility-validated, clipped 2010-2026).

## Mechanism claim

At ~11:00 server (≈09:00-10:00 London), EURUSD drifts DOWN through the
European midday. Cross-symbol check says the underlying driver is a USD
bid at European mid-morning (Tue-Fri): EURUSD -, GBPUSD -, USDCHF +,
USDCAD + — directionally coherent USD strengthening, not an EUR quirk.

## Frozen spec candidate (to be confirmed by grid)

- Symbol: EURUSD (deepest pair — flow shows strongest here)
- Direction: SHORT
- Entry: 11:00 server, Tue-Fri only (Monday dead: -0.50, PF 0.95)
- Exit: TIME +240min (through ~15:00 server / London lunch)
- SL: 20 pips (tail protection; median adverse excursion ~14p)
- TP: none (TP caps kill the drift: tp=12 -> net -0.49)
- Cadence: ~4 trades/week (binding constraint vs GOAL 10-40 floor)

## Evidence (corrected sim, next-bar-open entry, SL-first ambiguity)

EURUSD 11h short, Tue-Fri, sl=20 tp=0 hold=240, cost_rt=1.0p:

- n=3460, net +2.81p/trade, PF 1.36, win ~53%
- Per-year: +6.2 max, positive EVERY year 2010-2023 (14 straight),
  2024 -0.60, 2026 -0.13 -> 15/17 pos. h1=+3.87 h2=+1.75 (same sign,
  halved). **Regime decay visible: flat since ~2023-2024.**
- Hour band: smooth peak 10h->14h (PF 1.12/1.40/1.33/1.22) — band not spike.
- Cost gates: x1.5 -> PF 1.32 (>=1.25 OK); x2 -> PF 1.25 (>=1.00 OK);
  x3 -> 1.11.
- MAE med -16.2p (p25 -28.6) vs SL 20; MFE +13.6p med. Exit mix:
  72% TIME / 28% SL (sl=20). Drift curve: -0.2@15m -> -4.1@239m raw.

## Cross-symbol (same cell, Tue-Fri, sl=20 tp=0 hold=240, net)

| Sym | net | PF | pos_yrs |
|---|---|---|---|
| EURUSD | +2.81 | 1.36 | 15/17 |
| GBPUSD | +1.50 | 1.14 | 11/17 |
| USDCHF | -1.51 | 0.82 | 1/17 (i.e. LONG side: USD bid) |
| USDCAD | -0.79 | 0.90 | 5/17 |
| AUDUSD | +0.25 | 1.04 | 10/17 |
| NZDUSD | +0.12 | 1.02 | 8/17 |
| USDJPY | -0.66 | 0.92 | 6/17 |

USD-bid story confirmed; only EURUSD clears economics (deepest pair).

## Integrity status

- 11:00 server = OUTSIDE all suspect windows (roll 00:00-00:15 majors).
- Event/paths auto-drop suspect ctms; ~865 clean events per weekday.
- Fill realism: entry is next-bar-open at a normal liquidity hour —
  no burst-region dependency. With-drift direction (short into falling
  market) -> fills favorable, not adverse.
- Remaining risk: residual garbage bars at plausible magnitude inside
  the window (7 known EURUSD outliers) — suspect-flagged by jump rule.

## Honest weaknesses (for adversarial review)

1. Regime decay 2024-2026 flat — forward expectancy uncertain.
2. Cadence 4/wk < GOAL 10 floor — needs a stack of independent cells.
3. Multiple testing: cell selected from a 24h x 5dow x params grid —
   FDR q-value + post-observation basis must be declared.
4. PF 1.36 barely clears 1.30 — thin margin vs governed slippage.
5. Mechanism story (USD bid) is inferred from cross-symbol pattern,
   not proven causally.

## ADDENDUM 2026-09-19 — systematic grid + stack design (post-doc)

Corrected-sim `drift_hour` grid (pooled weekdays, n>=2000 cells only):

- **EURUSD 12h short: net +2.49, t=7.02, PF 1.35, pos_year 0.94** — best
  systematic cell in the run.
- 11h +2.18/t=6.66/PF1.32/0.88; 13h +1.90/t=5.09/0.82; 14h +1.91/t=5.01;
  10h +1.43/t=4.43; 16h +1.09; 9h +1.04. LONG side: all dead.
- Hour map Tue-Fri (ad-hoc): SHORT positive 08h->16h continuous band
  (+0.51 .. +2.81); LONG negative everywhere; suspect-window hours
  (00/22/23h) drop to n=0 — flagging works.

**Cadence solution — intra-symbol hour-stack** (GOAL counts trades on the
traded symbol; correlated entries are legal but must be declared):

| Stack (Tue-Fri, sl=20 tp=0 hold=240) | /wk | net | PF |
|---|---|---|---|
| (11,12) | 8 | +2.65 | 1.32 |
| (11,12,13) | 12 | +2.55 | 1.29 |
| (11,12,13,14) | 16 | +2.35 | 1.26 |
| (10,11,12,13) | 16 | +2.24 | 1.25 |
| (10..14) 5h | 20 | +2.14 | 1.24 |

- hold=360/480/600 raises net (+2.85/+2.90/+3.09) but PF stays 1.25-1.27.
- sl=15 at hold=480: PF 1.29. PF ceiling of the family ~1.29-1.32.
- Stacked equity: +37,006p over 17,293 trades, maxDD 1,920p;
  every year positive 2010-2023, **2024-2026 all negative**
  (-199/-383/-436p) — decay confirmed at stack level too.

**Structural finding**: the mechanism's PF frontier sits AT the GOAL
boundary (~1.24-1.32 depending on stack width). Best PF+legal cadence
compromise: (11,12,13) = 12/wk, PF 1.29 probe — governed outcome will
land either side of 1.30; that is what the governed run is for.

## GATE A OUTCOME — FAIL (both seats) → candidate RE-MEASURED under sim v3

Both GATE A advisors (Data-Integrity + Quant Methodologist) returned FAIL
on 2026-09-19, independently catching the same critical defect:

**D1 — short-side SL/TP trigger used the wrong bar field** (`labels.py`).
For side=-1 the adverse excursion was computed on bar LOWs
(`(entry-low)/pip`) — the favorable field — so short stops fired only on
whole-bar penetration, missing every wick-touch. Longs were correct.
Effect: every short-side number in this document was biased UP ~+1.5p
(real -20p losses booked as TIME-exit continuation wins).

### Corrected numbers (sim v3, wick-touch stops)

| Cell | v2 (biased) | v3 (correct) |
|---|---|---|
| 11h short Tue-Fri, sl20 h240 | +2.81 / PF 1.36 | **+1.29 / PF 1.15** |
| 11h pure-drift (sl=inf) h240 | — | **+2.35 / PF 1.25** |
| 12h short Mon-Fri sl20 h240 | +2.13 / PF 1.245 | +0.42 / PF 1.04 |
| 13h short Mon-Fri sl20 h240 | +1.84 / PF 1.19 | +0.18 / PF 1.02 |
| 14h short Mon-Fri sl20 h240 | — | -0.69 / PF 0.94 |

- SL rate at 11h rose 28% → 36% — the missed touches were real.
- Baseline control (D7 resolved): all-liquid-hours short = **-0.82** →
  the 11h band IS an incremental effect, not unconditional short-beta.
- But PF ceiling ~1.25 even unstopped; SL-protected (what an EA must
  trade) is 1.15. Regime decay stacks on top (2024-26 was flat even
  under the optimistic v2 numbers).

### VERDICT on candidate: **KILLED-IN-PROBE (sim v3, 2026-09-19)**

Premise real (baseline-controlled, FDR-surviving, cross-symbol coherent)
but economics not capturable at GOAL level — same genus as the M1
event-driven ceiling: real anomaly, too small vs cost. The value-leakage
autopsy: winners MFE +14p med but wick-touches lock -21p at 36% rate;
unstopped TIME capture nets PF 1.25 max. No prereg, no build.

### What remains standing post-v3 (long-side cells were always correct)

- **USDCHF Mon 1h LONG: +1.46 / t=5.01 / PF 1.62 / pos_year 0.76**
  (h60,sl20); h240 variant +1.88/PF1.42/0.82. ~1/wk.
- **USDJPY Mon 1h LONG: +1.47 / t=3.26 / PF 1.37** — same mechanism
  family: Monday Asia-open USD bid. ~1/wk.
- EURUSD Wed 1h LONG +1.44/PF1.27.
- These are v2-correct because the bug only hit shorts; still need
  cadence stacking to approach the 10/wk floor — binding constraint.

### Defects fixed for sim v3 / data-plane v4

- labels.py: side-correct adverse/favorable fields (D1); tail-pad inert
  (h=-inf,l=+inf,sus=1) instead of last-bar phantom paths; ctm-adjacency
  audit counters (gap_entry dropped, gap_path counted); suspect flag now
  also on the signal bar.
- sweep.py: sim_version in cell_hash → all cells auto re-measure under
  v3; sim_version column added.
- validate_bars_against_fills.py: fill key floored to the minute.
- data_plane.py: XAUUSD pip 1e-4 → 0.1 (gold pip convention; old cells
  were unit-degenerate).
- NEW: `lab/test_labels.py` — hand-computed unit tests both sides
  (short wick-touch SL, short TP on lows, long mirror, phantom-tail
  drop). ALL PASS under v3. Permanent guard for this bug class.

### GATE A residual items resolved after the verdicts

- D2 (tick spot-check): EURUSD midday bars vs real tick CSV
  (FivePercentOnline-Real feed): offset-scan shows ctm frame aligns at
  0s; median |tick - bar close| = **0.30p**, p90 = 1.2p — midday .hcc
  bars envelope real tradable prices. Residual deviation is normal
  cross-broker spread noise (probe plane = MetaQuotes-Demo, same feed
  as the governed tester — parity preserved).
- D6 (coverage): EURUSD = 6.2M bars total, ~367-373k/yr ≈ 256 weekdays
  x 1440 — matches documented rate; no weekend/stub inflation.
- Clock: ctm = server wall-time frame confirmed by BOTH the RGR
  fill-join (same-second tester matches) and this tick offset-scan
  (best alignment at 0s).
