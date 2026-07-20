# Logic-to-code matrix — HYP-018

Frozen before source modification. Status describes the intended mapping; the
delivery packet must bind final locations and tests before any completion claim.

| ID | Trader observation / intent | Quantified rule | Role | Intended source surface | Decision-time data | Telemetry proof | Verification | Status |
|---|---|---|---|---|---|---|---|---|
| L01 | Liquidity was swept and reclaimed | Existing latest closed-M5 pivot sweep/reclaim | context | `DetectSweep` | closed M5 only | sweep counters + HumanContext | existing HYP-012 tests | `VERIFIED_PARENT` |
| L02 | Reversal must become structurally visible | Existing bounded three-bar HYP-012 confirmation, unchanged | qualification | `AdvanceContextState` | closed bars `1+`, prior-20 bodies | context funnel | existing contract test | `VERIFIED_PARENT` |
| L03 | Initiation should exist inside the confirmation bar | Mid tick-rule imbalance `(up-down)/(up+down)` from `[bar_open,next_open)` | trigger-observation | new tick profile accumulator | broker ticks already observed before decision | TickInitiation row | red-first deterministic fixtures | `PLANNED` |
| L04 | Quote-path field must add material information | Sign agrees with direction; both agree and non-agree shares ≥20% | de-dup | outcome-blind parser only | collection ledger, no future price | collection result | repeat-hash + split gates | `PLANNED` |
| L05 | Collection cannot mutate the account | Mode 4 logs and clears; no `TryOpenTrade` or order path | risk | mode-4 branch | current state only | zero entries + zero lifecycle rows | source contract + run reconciliation | `PLANNED` |
| L06 | Tick data must not be synthetic or misaligned | Model 0 receipt, `.tkc` coverage, exact bar/profile identity | provenance | AlphaFactory receipt + row schema | run metadata and closed interval | provenance fields | receipt/hash validator | `PLANNED` |

## State machine and sequencing

`EMPTY → SWEPT → (invalidate | timeout | OHLC_CONFIRM) → TICK_PROFILE_LOGGED → EMPTY`.
The tick profile is accumulated online. At the first tick of a new M5 bar, the
previous profile is sealed before that tick initializes the new profile. Only a
sealed profile whose open time equals the confirmation bar open time can be
written. Duplicate setup suppression and HYP-012 timeout/invalidation are
unchanged.

## Stop, target and execution geometry

No order is allowed in HYP-018. The parent sweep-extreme stop plus 1.5 pips and
2R target are calculated only for HumanContext comparability. Existing broker
geometry, sizing and management code must remain dormant because
`InpResearchAutoMode=false` and mode 4 has no call to `TryOpenTrade`.

## Known gaps before outcome

- Quote-mid imbalance is not true signed order flow.
- History quality is expected to be 99% on the full 2018-YTD window; this plan
  permits it for collection only, never for promotion evidence.
- Model-0 and `.tkc` provenance are bound externally because MQL5 does not
  expose the tester modeling mode directly to the EA.
- Economic value and stop compatibility are unknown and deliberately unread.

