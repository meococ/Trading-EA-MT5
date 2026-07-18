# Cost frontier audit — HYP-UPS-XAU-M5-002

## Verdict

`BLOCKED_BY_MISSING_INPUT`. The historical-spread leg is now backed by a
builder-compatible same-broker M1 export on `D:`, but commission and slippage
cannot be verified from current local evidence. No MT5 research execution is
authorized by this audit.

## Read-only terminal evidence

- MT5 reported `FivePercentOnline-Real`, company `Five Percent Online Ltd`,
  account trade mode `DEMO`, terminal-side `trade_allowed=false`, and zero open
  positions/orders at the latest lane readback.
- Account history contained 11 deals total and zero `XAUUSD` deals. Therefore
  it cannot produce any same-symbol XAU commission or fill-reference sample.
- No orders were sent and no positions were opened during this audit.

## Historical spread leg

`export_unicorn_spread_evidence.py` exported completed `XAUUSD` M1 observations
for 2024-01-01 through 2026-07-15 as bar-close bid plus the spread points
reported by MT5 for that bar.

- rows/valid rows: 894,192 / 894,192;
- unique dates: 656;
- first/last UTC: 2024-01-02 01:05 / 2026-07-15 23:49;
- spread points P50/P90/P99/max: 23 / 44 / 82 / 319;
- zero-spread rows: 28;
- CSV SHA256:
  `D009CC4084AE35FC004DFA68417F64E7DBCBF1CD2A21750707EA1D06E2F69C6B`;
- AlphaFactory `validate_spread_evidence`: `PASS`.

This closes the raw historical-spread-source gap for the observed broker
scope. It does not prove commission or slippage.

## Existing QFSI evidence

Across all local XAU QFSI captures on `D:`:

- 29,378 unique quote ticks, limited to 2026-07-14 and 2026-07-15;
- zero non-empty XAU commission lifecycle rows;
- zero non-empty XAU slippage fill rows.

The official broker material describes metals commission as percentage-based
and directs traders to the current MT5 specification, but the public page does
not provide the XAU percentage rate. It therefore cannot be converted honestly
into the fixed round-turn-per-lot contract required by the current builder.

Sources:

- https://help.the5ers.com/what-are-the-spreads-and-commissions/
- https://lp.the5ers.com/hub-assets-specifications/

## Tick-history probe

Six read-only one-day `copy_ticks_range` probes returned zero ticks for the
sampled dates in 2024, 2025 and January 2026; 2026-07-01 returned 1,201,419.
This is not used to invent a full real-tick cost surface. The M1 spread export
above is preserved separately and its method is explicit.

## Remaining legal inputs

1. At least 30 XAUUSD commission lifecycles with contemporaneous account-
   currency conversion, or an explicit rate source compatible with the
   percentage-based metal commission model.
2. At least 100 XAUUSD fills with independent bid/ask references, including at
   least 30 BUY and 30 SELL samples.
3. Regenerate the task-packet broker/server/account/data identity for the
   broker scope that will actually execute the tester run. The existing packet
   was prepared against a MetaQuotes identity and must not be silently mixed
   with FivePercent evidence.

Until all three are satisfied, `-Execute` remains prohibited and no PF/DD/net
claim is valid.

## Full local-run reuse audit

The follow-up `HYP-UPS-XAU-M5-002_LOCAL_COST_REUSE_AUDIT.md` scanned all local
AlphaFactory XAU run manifests/reports. It found a FivePercent tester run with
335 XAU commission lifecycles and 335 request/fill rows (171 BUY / 164 SELL),
but all modeled entry slippage was zero and the legacy sidecars lack
independent millisecond BID/ASK references plus run-bound source identity.
These are tester clues, not VERIFIED real-execution provenance; the cost gate
therefore remains closed.
