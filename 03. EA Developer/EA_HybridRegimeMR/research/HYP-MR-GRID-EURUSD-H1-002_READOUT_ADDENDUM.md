# ADDENDUM — HYP-MR-GRID-EURUSD-H1-002 readout (coverage-scope clarification)

Date: 2026-07-18. Origin: adversarial process review (workflow
`wf_f0010272-8ca`, R2 findings W1/W2). The original READOUT is SHA-bound in
the killed registry row and stays immutable; this addendum clarifies claim
scope without changing the verdict.

1. **Coverage scope (W1).** "Exhaustive" applies to the Stage-1 axes at
   session [7,16): 1350 cells × 6 gate arms, all simulated. The ±1h
   session-shift arms and the 8 gate-threshold variants (declared Stage-2)
   were **eliminated by the frozen necessary-condition routing rule, not
   simulated** — no Stage-1 arm reached gross PF ≥ 1.25, so Stage 2 never ran.
   The net≤gross dominance argument bounds cost tiers of the SAME arm; it does
   not strictly bound a different trade set (a shifted session or changed
   threshold). Given the margin (median gross PF 0.8902, max 1.2476 across
   8100 arms, best DSR 0.0129 vs 0.95), the probability that an untested ±1h
   or threshold variant clears the full gate conjunction is negligible, but
   the claim is an argument, not a measurement. The verdict
   `KILL_FAMILY_EXHAUSTIVE_AT_OFFLINE_GRID` stands with this stated scope.

2. **Parity contingency (W2).** The gate-ablation sub-claim ("no single gate
   lifts any cell") depends on the Wilder ADX/ATR implementations, whose MT5
   iADX/iATR parity is UNVERIFIED. The dominant kill (un-gated control dead
   before cost) is parity-independent. Any future attempt to cite "002 proved
   regime gates add nothing" as standalone evidence must first close MT5
   indicator parity.

Rule promoted from W1 into `05. Playbook/validation_gates.md`
(Multi-simulation section): never label routed-away axes as "exhaustively
simulated".
