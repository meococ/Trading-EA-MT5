# Grok `/deep-research-trading-meta5` source checkpoint

Status: advisory only; no economic authority and no edge claim.

## Frozen question

The full official Dukascopy Jetta BTC H1 source-only profile found 75,613
matching BID/ASK timestamps from 2017-05 through 2026-08. Ten crossed ASK-open
bars occur only in 2017-11/12, with maximum deficit 23,480 points ($234.80).
There are zero crossed opens from 2018-01 onward. BTC is frozen inactive until
2018-05-14, signals use BID completed closes, and no pre-activation spread has
economic authority.

Proposed containment was to retain raw hashes, synthesize a one-point spread
only for crossed bars strictly before activation because MT5 custom rates
require a nonnegative spread, report all exceptions, and fail any crossed bar
on or after activation.

## Exact Grok verdict

- `VERDICT: ACCEPT_PREACTIVATION_CONTAINMENT`
- `FATAL_ISSUES: None.`
- Required receipt fields: total matching timestamps, count and maximum deficit,
  exact timestamps, proof all crosses are strictly pre-activation, proof zero
  on/after activation, statement of the inactive-only one-point containment,
  and unchanged raw hashes.
- `NO_POSTHOC_CONFIRMATION: YES`

Codex accepts this only as source-contract advice. The local profile and source
receipt remain authoritative; any post-activation crossed open fails V5.
