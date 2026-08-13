# HYP-MULTI-TSMOM-D1-005 — terminal source-gate failure

Verdict: `KILL_SOURCE_VALIDATION_BTC_D1_MATCH_BELOW_FROZEN_99P5_NO_ECONOMICS`.

## Evidence

- Frozen source contract SHA256:
  `82CB1576C9F7968F111225515A2F303727308A47C5EC2EA47579194F45C6CB9E`.
- Source validation:
  `research/evidence/source_validation/HYP-MULTI-TSMOM-D1-005_SOURCE_VALIDATION.json`.
- Source validation SHA256:
  `34DFCCA6B9DB8228F3E588CE977693F0040E69463F136F543FEAD132E842E995`.
- All 1,040 monthly receipts bind the frozen contract; no receipt has a
  post-activation crossed BID/ASK open.
- EURUSD, GBPUSD, AUDUSD, NZDUSD, USDJPY, USDCAD, USDCHF and XAUUSD each
  matched official session-anchored D1 OHLC within one source point on 100% of
  common sessions.
- BTCUSD matched 3,265 / 3,288 common sessions = `0.9930048662`, below the
  frozen `0.995` threshold. Maximum session OHLC error was 15 source points.
  The mismatches are concentrated in the 2017 legacy source, but the frozen
  full-history acceptance contract did not exempt that period.

## Authority boundary

No V5 MT5 custom-rate import under the final source identity, strategy DESIGN
run, trade, return, PF, optimization, validation or holdout was opened. V5 has
no economic verdict and no edge claim. The source threshold is not lowered and
the failed BTC mapping is not reinterpreted after readout.

## Failure radius and successor rule

The failure kills the exact nine-asset V5 source/portfolio identity. It does
not invalidate the eight independently source-passing FX/XAU feeds or the
calendar-365 TSMOM mechanism economically, because economics was never opened.
A successor may use a fresh preregistered FX+XAU portfolio identity and defer
BTC to an independent sleeve/source contract. It may not call V5 PASS, reuse
the failed nine-asset validation as a successful receipt, or pool later PnL to
hide a failed sleeve.
