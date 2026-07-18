# Operational invalidation — HYP-UPSC-XAU-M5-001

## Decision

HYP-UPSC-XAU-M5-001 is killed as operationally invalid. Runs
`20260716_135400` and `20260716_135622` are reproducible strategy-tester
observations, but neither is admissible final research evidence.

## Fail-closed reasons

- The first run was rejected because the prereg task packet did not bind the
  terminal include closure.
- The second run bound the include closure and passed the static non-repaint
  audit, but the cost builder found position `144` with `risk_pts=0`.
- The zero-risk row came from callback ordering when one position closed and
  the next opened on the same tester timestamp: pending risk was stored in the
  active-position globals and was reset by the preceding final-close callback.

No report breakdown, hour, weekday, session or regime result may be used to
change the strategy. HYP-UPSC-002 may repair only lifecycle bookkeeping with
separate pending/current/previous position risk slots.

