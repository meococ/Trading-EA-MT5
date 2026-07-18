# Stage-0 Freeze — HYP-ICTVIS-EURUSD-M5-001 / EA_ICTVisualEdge

Frozen: 2026-07-18. This document is SHA-bound in the registry `idea` row. It
freezes the **method**, the **de-dup auto-fail predicate**, and the **honest-kill
boundary** BEFORE any chart is rendered or any outcome is read. Nothing below may
be relaxed post-hoc; a later PROBE_PLAN (Stage 3) may only make it stricter.

## 1. What is new here, and what is not

- **New (legitimate):** the *method* — render decision-time (asof) charts on a
  DESIGN window, visually extract candidate features that discriminate winners
  from losers, quantify each into a computable decision-time function, then probe
  mechanically with deflation. No killed lane here ever rendered a chart or did
  data-driven visual feature-discovery; every ICT lane (Unicorn / PO3 / KLR /
  FVG / DRAT) was an a-priori memo funnel.
- **Not new (suspect):** the *object* the seeding report points at
  (sweep -> displacement/MSS/BOS -> FVG/OB retest, killzone timing, HTF bias,
  price-only). This object is already falsified on BOTH axes:
  - **Cadence** when tightened: 0.03-1.3 trades/week (PO3 funnel collapsed to 0
    retests; KLR native 346 -> 61 -> 26 -> 5 -> 1).
  - **Economics** when loosened: PF 0.47-0.76. DRAT is the economics proof —
    cadence in-band at 3.09/week yet PF 0.764 after cost. No interior point has
    both adequate cadence and post-cost positive PF.

## 2. De-dup auto-fail predicate (CENTRAL GUARDRAIL)

The hypothesis **auto-FAILS** if, after visual discovery, the top discriminating
feature(s) map onto the killed ICT primitive set:

```
ICT_PRIMITIVES = {
  liquidity-sweep / stop-run,
  displacement / MSS / BOS / market-structure-shift,
  FVG / OB retest / mitigation,
  killzone / session-time gating,
  HTF directional bias,
}
```

evaluated on **price-only** information on EUR/XAU at M5-M15.

- If data-driven visual search only re-discovers the ICT stack -> verdict is
  **"CONFIRMED_KILLED_OBJECT"**: the lane self-kills by de-dup. The new *method*
  does NOT resurrect an object already falsified. This is a valid, evidence-strong
  outcome (data-driven confirmation beats assertion).
- A feature is **legitimate** ONLY if it either:
  (a) rests on a materially different information set (options-implied, real OI,
      order-flow — NOT price-only), OR
  (b) is a pattern **provably not** one of the 5 primitives above (the mapping
      check must be logged, feature-by-feature).

The mapping evaluation is mechanical and logged in the Stage-2 feature ledger;
each declared feature carries an explicit `maps_to_ict_primitive: yes/no + which`.

## 3. Anti-overfit contract (feature-mining on outcomes is the highest-overfit act)

1. **Visual discovery only on DESIGN window 2015-2018.** Test 2019-2022 and
   holdout 2023+ are NEVER eyeballed during feature design.
2. **Outcomes are mechanical & sealed** (forward R, stop-first, cost-aware). The
   eye only generates *feature hypotheses* from asof (decision-time) images ->
   AI-visual = `AI_EXPLORATORY` idea-generation; the verdict is mechanical +
   deflated, never an AI label used as evidence (Chart-State Label Contract).
3. **Feature budget declared in advance;** every feature/threshold counts as one
   trial for DSR / PBO.
4. **Matched always-on control** (fires every candidate, no feature) — a feature
   must beat control by a margin to prove it discriminates rather than reprices
   noise.
5. **Cadence is a first-class gate** (>= 2/week) alongside full economics — the
   exact axis on which DRAT died.

## 4. Honest-kill boundary & expected outcome

- **Base-rate expectation: self-kill** — the data confirms the ICT object is dead
  (stronger than assertion). Small but real win: the search surfaces a
  materially-different, non-primitive feature that survives deflation.
- **KILL taxonomy** to be stated at verdict: (a) self-kill because feature == dead
  ICT object (de-dup confirmation); (b) feature materially different but fails
  deflation; (c) dies on cadence/economics.
- Cheaper high-probability fork (already in every ICT readout): reopening this
  object needs a **new information set** (order-flow / options / OI), not OHLC.
  That is a data-unlock, not a build.

## 5. Windows (frozen)

| Split    | Range        | Use                                  |
|----------|--------------|--------------------------------------|
| DESIGN   | 2015-2018    | visual discovery + feature design    |
| TRAIN    | 2019-2021    | quantified feature fit / threshold   |
| VAL      | 2022         | out-of-design validation             |
| HOLDOUT  | 2023-present | SEALED, read only at final verdict   |

Symbol EURUSD (primary); XAUUSD reserved as de-dup cross-check only. TF M5 primary,
M15 context. Cost proxy 1.5 pip RT (UNVERIFIED_PROXY), no swap (intraday).
