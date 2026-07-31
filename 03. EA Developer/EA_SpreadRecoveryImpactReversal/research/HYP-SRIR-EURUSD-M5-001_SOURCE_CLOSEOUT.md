# HYP-SRIR-EURUSD-M5-001 — Source Closeout

## Verdict

`KILL_SOURCE_FEASIBILITY_ZERO_RECOVERY_AND_COVERAGE`

The single authorized attempt `SRIR001-SOURCE-001` completed with terminal
status `SOURCE_FAIL_NO_ECONOMICS_AUTHORITY`. It is engineering-valid,
outcome-blind and terminal. No economics child is authorized from this source
object.

## Evidence

- Frozen V2 plan SHA-256:
  `156E3F6A6BC2D9C29CBACF96380E8980B9245717E36EA3656077C15B29BB74C0`.
- Reviewed registry-row SHA-256:
  `E07DF2D1246DF90B8EB918463F39B3166C94337BB49C4BF714E4537FC68F9210`.
- Source report SHA-256:
  `AF8AB353219CC0914130F8C3324723AD41F1F19BFD67E3E8301F0A9AAFEF0144`.
- Attempt terminal SHA-256:
  `F4B68B7D77E188EC0BA1F119F353ADC4331469A135393B2607A348DC877D9300`.
- Accepted Grok forensic packet SHA-256:
  `CBA4BD17D892EFC2392E349E89F5B736459852FE5CEC89E0F99980210B57EB5C`.

The receipt and terminal hash chains reconcile. Independent replay digests are
identical. The empty classifications and ledger files have the canonical empty-
file SHA-256 because the reconciled population contains zero accepted signals.

## Frozen source result

- Shock funnel: 209 shocks, 93 replacements, 115 expiries and zero accepted
  recovery decisions.
- Positive finite M1 spread ratio: `0.921927917835968` versus `>=0.99`.
- Scheduled M1 formation completeness: `0.9982785602503912` versus `>=0.99`
  (PASS).
- Prior-20 eligible-date baseline availability: `0.7857702729939757` versus
  `>=0.99`.
- TRUE/FOLLOW_CONTROL executable rows: `0 / 0`; cadence `0.0/week`.
- Stage-0 gates: `4 / 13` passed.
- Outcome plane: zero post-entry OHLC rows, returns, trades, economics trials,
  validation/holdout reads, MT5 launches and MQL5 files.

## Failure radius and routing

The kill applies only to the exact EURUSD M5 public-DESIGN same-slot prior-20
eligible-date spread-shock, three-bar spread-recovery plus partial-retracement,
first-per-UTC-day decision surface and its frozen source gates. It does not prove
market-wide no edge.

Do not rerun or rescue this ID by changing shock/recovery thresholds, session,
lookback, missing-spread handling, direction, subgroup, horizon or stop/cost
geometry. Persistent-liquidity or continuation ideas are only research inputs;
they require a materially new mechanism, fresh ID, de-duplication and a new
pre-outcome preregistration before any source or economic access.
