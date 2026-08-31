# Foundation M5 bar `real_volume` capability closeout — 2026-08-13

## Verdict

`KILL_REAL_VOLUME_PAYLOAD_COVERAGE_OR_TRIVIALITY`

The FiveAssetFoundation M5 schema does contain `real_volume uint64`, and parquet
footer maxima are nonzero. Row-level source-only inspection proves that this is
not a durable 2018-latest or current broker-bar field:

| Symbol | Frozen-window rows | Positive rows | Positive share | Positive interval | July 2026 positive |
|---|---:|---:|---:|---|---:|
| EURUSD | 639,404 | 228 | 0.035658% | 2022-12-25 22:05 to 2022-12-26 17:00 UTC | 0 / 6,543 |
| GBPUSD | 639,318 | 228 | 0.035663% | 2022-12-25 22:05 to 2022-12-26 17:00 UTC | 0 / 6,543 |
| USDJPY | 639,434 | 228 | 0.035657% | 2022-12-25 22:05 to 2022-12-26 17:00 UTC | 0 / 6,543 |
| XAUUSD | 604,078 | 7,769 | 1.286092% | 2018-01-02 07:00 to 2018-02-09 21:45 UTC | 0 / 6,211 |

All four symbols fail the frozen per-year `>=95%`, recent `>=95%` and recent
distinct-value gates. EURUSD, GBPUSD and USDJPY share the exact same narrow
Christmas-2022 positive interval; XAUUSD is positive only in an early-2018
fragment. `KILL_REAL_VOLUME_PROVENANCE_UNRECONCILED` is therefore not reached:
the payload itself fails before provenance can matter.

## Evidence and controls

- Plan SHA256:
  `AD46D9E3F564AEC0EB285BBD83FD66010C9E9A25F7E2F6A2403C019D43F04670`.
- Auditor SHA256:
  `A81B5CC04059C48082A8265C9E6B1F4E44D7D7F8B4336BCFDDBB6F998A9DED7B`.
- Tests SHA256:
  `DE8E24D755F1453A6F4C17C9578243B5115D51E4886BC56D20842D260119FEAD`;
  `5 passed`.
- Report SHA256:
  `D7CAB6A4A7F9543B37ACA8A31E9D626107B5A0BC6A010562810B46BED40813F2`.
- Receipt SHA256:
  `6B7060B6CCE82BCA217F9C730EDF7896EF7256B9086418B6B21071484DBD0C9A`.

The first test collection failed before any parquet row read because the dynamic
test loader had not registered the module for `dataclass` resolution. The test
loader was corrected, `py_compile` and all five tests passed, and the evidence
root was still absent before the sole execution.

The executed audit requested only `time_utc`, `tick_volume` and `real_volume`.
OHLC, spread, returns, direction maps, targets, trades, PnL, PF, MT5, validation
and holdout counters are all exactly zero.

## Research boundary

Do not use isolated nonzero footer maxima or these sparse historical fragments
as actual FX/XAU volume, a signal, a filter or a source rescue. The local
FivePercent M5 bar information surface remains OHLC, spread, broker tick-volume
and timestamps for a replayable 2018-latest contract. No hypothesis ID, EA,
economic test or Grok build is authorized from `real_volume`.

The overall XAU/Forex EA goal remains `ACTIVE / UNMET`. A next mechanism needs a
materially new, durable raw field/source or an independently justified Owner
carve-out—not another transformation of the exhausted local surface.
