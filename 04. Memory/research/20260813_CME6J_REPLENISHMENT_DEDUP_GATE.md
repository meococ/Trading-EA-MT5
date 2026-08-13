# CME 6J replenishment de-dup gate — 2026-08-13

## Scope

- Outcome-blind source/mechanism audit only for CME Japanese Yen futures `6J`
  `GLBX.MDP3` `mbp-10` as an input to FivePercent `USDJPY`.
- Proposed object was continuous top-five depth restoration after aggressive
  trades on completed M5 windows, with positive 6J resilience mapped to short
  USDJPY through the reciprocal JPY/USD quotation.
- No target prices/returns/PF, metadata quote, payload download, purchase,
  code, MT5 or backtest was opened.

## Primary-source facts

- Databento MBP-10 documentation:
  https://databento.com/docs/schemas-and-data-formats/mbp-10
- Databento symbology documentation:
  https://databento.com/docs/standards-and-conventions/symbology
- CME FX product guide:
  https://www.cmegroup.com/markets/fx/fx-product-guide.html
- MBP-10 contains every trade and aggregate top-ten book update, but not the
  individual order IDs/fill lineage needed to distinguish new passive orders,
  queue replacement and iceberg refresh. A post-trade depth increase can be
  measured; it cannot be uniquely labelled as the proposed causal population.
- CME quotes 6J as USD per JPY, so a 6J price rise is reciprocal to USDJPY.
  That establishes target inversion only. It does not decide whether observed
  replenishment predicts continuation or absorption/reversal.
- Databento continuous symbology maps each date to a real unadjusted contract
  using calendar, prior-day open-interest or prior-day volume roll rules. The
  rule can be PIT-safe, but roll identity does not cure the feature/sign gate.

## Local de-dup

- Existing package `EA_EventL1Replenishment` already proved CME MBP event/BBO
  semantics and terminally rejected the L1 replenishment candidate because
  same-direction versus contrarian mapping was arbitrary.
- Static multi-level book alignment/transition was consumed by
  `HYP-CME6E-RAWBREAK-*`; macro-event T+60/T+120 depth transfer was consumed by
  HYP008/HYP009. Changing 6E to 6J and event to continuous M5 does not create a
  materially independent information object.
- No CME/Databento rule defines an M5 replenishment measurement or holding
  interval. Choosing one now would introduce an unfrozen fitted horizon.

## Verdict

`NO_6J_REPLENISHMENT_CANDIDATE`

First fatal uncertainty: aggregate MBP-10 cannot uniquely identify the claimed
replenishment population, and the target-reciprocal relation cannot resolve
continuation versus absorption. De-dup and arbitrary horizon independently
fail. No cost call is justified. This is scoped to the proposed 6J object;
overall goal remains `ACTIVE / UNMET`.
