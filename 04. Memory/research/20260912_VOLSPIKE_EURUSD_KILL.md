# VOLSPIKE EURUSD — KILL (2026-09-12)

Cell 11 of the era-2 governed screen. `HYP-VOL-EU-M15-001` / `EA_VolSpike`.

## Run

- **Run ID:** `20260912_102410` (control, challenger, research-proxy cost tier)
- **Window:** 1999.01.01 → 2026.09.11, `verified_m1_asof`, coverage class
  `VERIFIED_M1_START`
- **Quality:** 99% | **Model:** 0 | Build 6192 isolate

## Result

| Metric | Value | Gate | Verdict |
|---|---|---|---|
| Trades | 14,053 | — | — |
| Cadence | 9.76/wk | 10–40 | FAIL |
| Profit factor | 0.873 | >1.30 | FAIL |
| Net | −$6,898.94 | — | FAIL |
| Max DD | 69.9% | ≤20% | FAIL |
| Win rate | 26.1% | — | — |
| Cost PF x1.0 | 0.717 | — | FAIL |
| Cost PF x1.5 | 0.651 | ≥1.25 | FAIL |
| Cost PF x2.0 | 0.593 | ≥1.00 | FAIL |
| Non-repaint audit | PASS | PASS | PASS |
| WFA (diagnostic) | OOS PF degrades every window | — | FAIL |

## Analysis

Tick-volume spikes (>2x SMA20) on EURUSD M15 marked continuation 26% of the
time — worse than coin flip after spread. Participation bursts on intraday
FX are more often exhaustion than initiation at this granularity; with no TP
and 8-bar hold, losers bled the full 1xATR stop. Even gross-of-cost the
mechanism was negative; costs just deepened it (0.87 → 0.72).

This is the first non-price-only mechanism tested (volume/participation),
and it failed on both cadence AND economics — the spike filter was too
permissive for 10+/wk but the trades it did take lost.

## Verdict: KILL

All provenance/data-quality/nonrepaint gates passed. Registry row appended
(`killed`, run_ids=[20260912_102410]).

## Board state (era-2 screen) — 10 kills, 0 passes

- XAUUSD (5): CRSI-R2, AMA, VwapFade, HourDrift, GbbSqueeze
- EURUSD (5): Ibsc MR 0.68, CamarillaFade MR 0.70, HtfDisplacement mom 0.76,
  LiquiditySweep micro 0.12/wk, M15br breakout 0.68, VolSpike volume 0.72

## Honest read

Seven mechanism families on EURUSD, five on XAU — every one gross-negative
under Model 0 with measured MQ-Demo costs. The falsification screen is doing
its job: intraday M5/M15 edges at this cost structure do not survive a
0.1-pip-spread broker once 8-hour session windows and closed-bar discipline
are enforced. Remaining untested EURUSD-relevant classes are thin
(session-open drives cap at ~10/wk ceiling; GBPUSD candidates need new cost
evidence). Next options:

1. GBPUSD London ORB / NYORB — needs GBPUSD cost evidence; ~5/wk cadence
   likely fails the floor.
2. XAUUSD SessionOpenDrive — 2 sessions x 1 entry = ~10/wk ceiling; XAU
   spread p90 4.2 pips vs full-M15-bar stop (wider, less cost-sensitive).
3. Accept and document: no intraday-scalp sleeve passes MQ-Demo economics —
   pivot to a different contract class (e.g., H1+ hold multi-day, where
   the 10-40/wk cadence gate must be renegotiated with Owner).
