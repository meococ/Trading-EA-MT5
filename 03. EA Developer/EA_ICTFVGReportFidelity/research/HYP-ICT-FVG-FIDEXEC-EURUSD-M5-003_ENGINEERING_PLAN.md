# HYP-ICT-FVG-FIDEXEC-EURUSD-M5-003 - frozen execution-hardening plan

Status: **FROZEN BEFORE SOURCE EDIT; NO PRICE OUTCOME AUTHORIZED**

## Identity and boundary

- Parent: `HYP-ICT-FVG-FIDNEWS-EURUSD-M5-002`, terminal `parked` before
  Model 0 because same-broker cost provenance failed.
- Parent source snapshot SHA-256:
  `8BABF2EEE803638E0832D2B6DAFBFA2E6FE6F3E88C24307CFCAE8D0E6D927BE3`.
- This child changes execution/risk bookkeeping only. The two frozen signal
  arms, all thresholds, sessions, news input, entry geometry, SL, TP and
  management parameters remain byte-for-byte equivalent in behavior.
- No Strategy Tester outcome, optimization, holdout access, Model-0
  authorization, promotion or live attachment is granted by this plan.

## Pre-edit findings to close

1. UTC day rollover currently clears the consecutive-loss streak and cooldown,
   contrary to the frozen two-consecutive-lifecycle rule.
2. A terminal restart does not rebuild lifecycle net P&L, so a final close can
   classify only the post-restart deal and corrupt the loss-streak gate.
3. Peak equity is updated in memory but not persisted when a new high occurs,
   allowing a crash/restart to loosen the 8% peak-equity drawdown reference.
4. The send path trusts the `CTrade` boolean without independently validating
   the server retcode and counts an accepted request as an opened lifecycle.
5. A fill-risk emergency close is attempted once; a transient close failure
   does not leave a restart-safe retry flag.

## Frozen implementation delta

- Preserve loss streak/cooldown across UTC day changes; reset only daily equity
  and daily trade count.
- Persist position-bound initial risk, planned money risk, lifecycle net,
  entry UTC date and emergency-close state. Bind persisted fields to the exact
  `POSITION_IDENTIFIER`.
- Rebuild lifecycle net from deal history by `DEAL_POSITION_ID` on restart and
  again on each lifecycle transaction before final loss classification.
- Persist every new peak-equity value and retain the maximum across restart.
- Require an accepted `ResultRetcode`; count `entries_opened` and
  `trades_today` only on the first actual entry deal for a position.
- Block duplicate sends while an owned pending order exists.
- Retry a fill-risk emergency close on every tick and after restart until the
  owned position is absent.

## Acceptance

- Targeted contract tests cover all five findings and the unchanged frozen
  signal/news surface.
- AlphaFactory compile: zero errors and zero warnings.
- Exact new source -> news include -> EX5 -> compile-log receipt.
- Closed-bar/non-repaint audit remains PASS.
- Final state is `parked` with `model0_authorized=false` and
  `promotion_eligible=false` until verified spread, commission and slippage
  inputs exist.
