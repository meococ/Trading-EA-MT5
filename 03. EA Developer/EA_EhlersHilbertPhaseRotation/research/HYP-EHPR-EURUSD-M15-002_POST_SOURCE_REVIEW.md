# HYP-EHPR-EURUSD-M15-002 — post-source Lead review

Lead verdict: `PARK_PRE_MQL5_CONTRACT_MISMATCH`

Grok advisory verdict: `B) PARK_PRE_MQL5_CONTRACT_MISMATCH`

## Decision

The source-feasibility gate passed, but the frozen phase-cross clock emits 82.9638 executable events per week. The exact direction tape is 99.49% alternating. Under the frozen baseline lifecycle, one owned position exits on an opposite phase cross; therefore its completion clock remains order-one with the event clock (or at best every other event when an exit consumes the event). That is structurally far above the registry acceptance range of 2–5 completed trades per week.

Grok estimated a mechanical band of roughly 41–83 completed trades per week and recommended no MQL5 build. Lead accepts the contract-mismatch conclusion but corrects Grok's statement that the event tape is strictly alternating: the hash-bound ledger contains 111 same-direction adjacencies. That correction is much too small to bridge the order-of-magnitude gap.

Reaching 2–5 completed trades per week would require retaining only a small fraction of phase crosses through a period cut, threshold, session, cooldown, skip-N, or another sparsifier. Adding any such rule after observing 82.9638/week would be post-hoc rescue and is forbidden. ATR stop, Friday flatten, risk sizing, and DD lock cannot lawfully solve the signal-clock mismatch.

## Scope of failure

- Failed: exact EHPR-002 M15 phase-cross event clock plus opposite-cross lifecycle under the frozen economic cadence contract.
- Not tested: profitability, cost robustness, drawdown, MQL5 runtime, MT5 parity, validation, holdout, promotion, paper, or live trading.
- Not implied: all Ehlers/DSP hypotheses fail, all EURUSD hypotheses fail, or the source dataset lacks useful edge.

Do not build `EA_EhlersHilbertPhaseRotation.mq5` for this hypothesis. A future candidate must preregister a different native event definition before its counts are observed; it may not throttle EHPR-002 after the readout.
