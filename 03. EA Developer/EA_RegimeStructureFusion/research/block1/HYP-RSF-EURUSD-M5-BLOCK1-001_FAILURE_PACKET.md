# HYP-RSF-EURUSD-M5-BLOCK1-001 Failure Packet

## Terminal decision

- State: `KILLED — TERMINAL_NO_SURVIVOR`
- Engineering valid: yes
- Economic valid: no
- Promotion ready: no
- Discovery cells completed: 18/18
- Family outcomes counted: 19 (one Q1 integration smoke plus 18 Block-1 cells)
- Validation and holdout: never opened
- Data contract: EURUSD M5, 2018-01-01 through 2022-12-31, Model 0,
  current spread, 100,000 USD deposit, 1:100 leverage, 0.20% risk, 100%
  history quality, 372,914 bars and 105,949,201 ticks per cell

No cell met both frozen discovery requirements: 2-5 trades/week in every
calendar-year bucket and positive expectancy. This ID must not receive a
parameter rescue.

## Cell readout

| Cell | Session | Stack / mode | Trades | PF | Net USD | Gate |
|---:|---|---|---:|---:|---:|---|
| 01 | London | MBB only / all | 939 | 0.869 | -5,254.73 | cadence + expectancy |
| 02 | London | + context / all | 983 | 0.860 | -5,253.41 | cadence + expectancy |
| 03 | London | + TB / all | 555 | 0.910 | -4,602.40 | cadence + expectancy |
| 04 | London | + QQE / all | 491 | 0.853 | -4,966.39 | cadence + expectancy |
| 05 | London | full / trend | 246 | 0.848 | -3,689.20 | cadence + expectancy |
| 06 | London | full / breakout | 214 | 0.914 | -2,045.75 | cadence + expectancy |
| 07 | Overlap | MBB only / all | 700 | 0.820 | -5,253.09 | cadence + expectancy |
| 08 | Overlap | + context / all | 522 | 0.749 | -5,253.58 | cadence + expectancy |
| 09 | Overlap | + TB / all | 210 | 0.748 | -4,415.82 | cadence + expectancy |
| 10 | Overlap | + QQE / all | 195 | 0.745 | -4,210.17 | cadence + expectancy |
| 11 | Overlap | full / trend | 185 | 0.731 | -4,104.76 | cadence + expectancy |
| 12 | Overlap | full / breakout | 5 | 0.927 | -45.84 | cadence + expectancy |
| 13 | Union | MBB only / all | 890 | 0.856 | -5,253.69 | cadence + expectancy |
| 14 | Union | + context / all | 484 | 0.834 | -5,188.69 | cadence + expectancy |
| 15 | Union | + TB / all | 755 | 0.846 | -5,245.04 | expectancy |
| 16 | Union | + QQE / all | 670 | 0.720 | -5,252.60 | expectancy |
| 17 | Union | full / trend | 423 | 0.663 | -5,244.00 | cadence + expectancy |
| 18 | Union | full / breakout | 219 | 0.914 | -2,124.31 | cadence + expectancy |

Cell 12 has the largest aggregate PF only because it contains five trades.
Cells 15 and 16 are the only cadence-valid configurations; both lose money in
all five yearly buckets. Therefore there is no legitimate "best parameter"
selection in this block.

## Failure radius

1. **MBB entry events alone have no usable edge.** All three base cells are
   negative and the London/Overlap/Union controls consume the usable equity
   buffer above the broker's money-mode stop-out reserve.
2. **AIRD/VRC context routing changes frequency, not expectancy.** Context-only
   cells remain negative and do not consistently enforce the cadence ceiling.
3. **TB SMC is useful as a control surface, not yet as alpha.** In the Union
   session it restores 2-5 trades/week for every year, but Cell 15 remains
   negative in every year (PF 0.846).
4. **QQE timing is a negative marginal contribution in the cadence-valid
   route.** Cell 16 removes 85 trades from Cell 15 and lowers PF to 0.720.
5. **The trend branch is structurally weak.** Trend-only cells are sparse and
   materially negative; any favorable direction/year slice is post-hoc and
   cannot authorize a direction switch under this ID.
6. **The breakout branch is unstable and undersupplied.** Its best annual
   pockets do not repeat and every breakout cell violates the cadence floor.

The failure radius covers the tested synchronous entry/exit geometry on
EURUSD M5. It does not invalidate the indicators as descriptive tools, the
closed-bar integration, telemetry, risk controls or the reusable EA shell.

## Rejected rescues

- Disable losing weekdays, hours, years or directions after seeing the report.
- Select Cell 12 because it has the numerically largest PF on five trades.
- Select the positive 2020 breakout slice or near-flat 2022 trend slice.
- Tune QQE, TB or session thresholds under the same hypothesis.
- Open 2023 validation/holdout to search for a better-looking period.

## Fresh successor boundary

Candidate ID reserved for design only: `HYP-RSF-EURUSD-M5-SEQUENCE-002`.
It is **not preregistered and not authorized to run** in this packet.

The only defensible next mechanism is a finite-state sequence rather than a
same-bar gate stack: AIRD/VRC establishes a regime episode, MBB arms a setup,
TB sweep/reclaim or displacement confirms execution within a frozen expiry
window, and QQE acts only as a route-specific confirmation/invalidation. A
fresh preregistration must freeze the state transitions, timeout, exits,
timezone/session surface, trial count and DSR denominator before any new
outcome is read. Each later symbol must receive its own discovery block; no
EURUSD-selected parameter may be copied as "optimal" to another pair.

## Evidence pointers

- Machine-readable results: `HYP-RSF-EURUSD-M5-BLOCK1-001_RESULTS.json`
- Frozen rules: `../HYP-RSF-EURUSD-M5-BLOCK1-001_FROZEN_PREREG.md`
- Run directories: `02. AlphaFactory/runs/EA_RegimeStructureFusion/<run_id>`
- Last run: `20260806_213758`
- Last report SHA256:
  `AC295A9FDC87349E1A682DD2213C627F94203DAD4BA4CC3C9867E1BB5C7E76F2`
- Last lifecycle SHA256:
  `EBA85025A1E4BC340749628946E6272A1A9F44023D5DAC66BDF5C68B12B72688`
- Last RunMeta SHA256:
  `304089BB6F1B8188E79F48D875E1C13A023B2C504D54772D475FAFB75C3AAA9E`
