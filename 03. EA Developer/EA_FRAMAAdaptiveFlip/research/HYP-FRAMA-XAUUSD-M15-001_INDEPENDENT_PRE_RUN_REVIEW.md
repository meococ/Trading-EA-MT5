# HYP-FRAMA-XAUUSD-M15-001 — independent pre-run review

Verdict: `PASS_BASELINE`.

Reviewed source SHA256: `53ABA54A8C989CDB845E32DB1C0E5570B34B3337D5F9D250EF1D619669C35FF7`.

- Closed-bar FRAMA shift/alignment and exact-next M15 mapping are causal and match the preregistration.
- Money/percent stop-out-aware sizing clamps volume downward with an explicit reserve; inability to trade the minimum lot is a safe reject.
- Tick, property, account, calculation and `OrderCheck` API failures latch `runtime_failed`; the silent tick-size fallback is absent.
- `CurrentM15Open` assigns the current native M15 epoch and returns success.
- Compile is `0 errors, 0 warnings`; the refreshed non-repaint audit binds the current source and passes.

Authorization is limited to one untuned XAUUSD M15 Model-0 TRAIN baseline. This review makes no economic or promotion claim.
