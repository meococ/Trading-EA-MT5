# ASRS de-dup and research review — 2026-07-25

Status: `LEGAL_NEW_STAGE0_ONLY_WITH_STRONG_ADVERSE_PRIOR`.

Source report:

- `05. Playbook/Strategy/BaoCao_DeepResearch_ASRS_Adaptive_Sweep_Reclaim_Scalper_24Jul2026.docx`
- SHA256 `3F05A242323D0B9926AED5AC3B9B6A47A630D1B544F8F298DBAF1335B0A4FF54`

## Evidence adjudication

The report is a hypothesis memo, not evidence that ASRS has an edge. It contains
no ASRS registry identity, frozen plan, data hash, outcome-blind funnel, verified
cost source, Model-0 report, or holdout result. Its claims that the edge exists
on major FX and XAUUSD, remains durable in 2025-2026, and can achieve prop-firm
drawdown targets are therefore unproven.

Primary research supports stop-order clustering and price impact, but not the
report's claimed reversal direction. Osler's currency-market evidence finds that
clustered stop-loss activation can propagate rapid price cascades:
<https://www.newyorkfed.org/research/staff_reports/sr150.html>. That is an adverse
causal prior for automatically fading a sweep, not proof of ASRS mean reversion.

MT5 `iVolume` is tick volume for the selected broker bar, not centralized FX
transaction volume:
<https://www.mql5.com/en/docs/series/ivolume>. The FivePercent M1 shelf has
nonzero tick volume on all 1,491,312 development rows, but real volume is almost
entirely absent. The signal must remain broker-bound and `UNVERIFIED_PROXY`.

## Failure-radius comparison

### HYP-ICTVIS-EURUSD-M5-001

Terminal verdict: `KILL_AT_DESIGN_IN_SAMPLE_ECONOMICS`.

- The generous price-only EURUSD M5 sweep-reversion universe was near-random at
  zero cost: PF `1.019`.
- The best visually seeded top-decile morphology reached only PF `1.12` at zero
  cost and PF `0.573` at the frozen 1.5-pip round-trip proxy.
- Median initial risk was `4.5` pips, so cost consumed about `0.33R` per trade.
- Its explicit reopen boundary is a different object geometry (wider stop or
  different entry) or a new information set, under a fresh hypothesis.

### HYP-ICT-FVG-FID-EURUSD-M5-001

The exact ordered ICT report-fidelity build is parked before Model 0 because
same-broker historical cost and high-impact news provenance are unavailable.
Its matched high-recall control is already the adjacent swing-sweep/reclaim
baseline. Compile/non-repaint success is engineering evidence only.

### HYP-NY sweep-reclaim and other stop-geometry variants

The older NY opening-range sweep-reclaim object failed economic/robustness gates
on indices. VRAS HYP-006 also showed that changing only stop geometry does not
create an edge. These do not blacklist all sweep hypotheses, but they make a
filter-only or stop-only rescue illegal.

## Material delta allowed for HYP-ASRS-EURUSD-M5-001

The new ID is legal only as the following joint object:

1. A mandatory next-bar retest and directional rejection after the reclaim;
   the report's aggressive reclaim-close entry is not the challenger.
2. A sweep-extreme stop with a fixed `0.30 * ATR(14)` buffer, whose measured
   entry-to-stop distribution must be materially wider than the killed
   `4.5`-pip median prior.
3. FivePercent broker tick-volume surge as a broker-specific activity proxy,
   never described as centralized or actual FX volume.

ADX, sessions, N=2/N=3, sweep threshold, RR, news, and HTF bias are not novelty
by themselves and cannot be tuned after a failed funnel or outcome.

## Decision

Open `HYP-ASRS-EURUSD-M5-001` for exactly one outcome-blind Stage-0
cadence/geometry probe. No MQL5, Model 0, parameter grid, symbol transfer,
economics, promotion, paper attach, or live authority exists until every Stage-0
gate in the frozen plan passes.

