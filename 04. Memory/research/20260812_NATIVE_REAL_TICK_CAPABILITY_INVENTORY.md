# Native FivePercent real-tick capability inventory - 2026-08-12

## Purpose

This is a metadata-only source-capability receipt for the current local
FivePercent terminal. It asks whether a zero-cost, train/live-identical broker
tick surface exists before any new mechanism is proposed.

The inventory read only `.tkc` filenames, byte sizes and filesystem timestamps
under:

`02. AlphaFactory/runtime/mt5-portable-fivepercent/bases/FivePercentOnline-Real/ticks`

No TKC payload, Bid, Ask, Last, volume, return, future outcome, threshold or
strategy metric was read. The similarly named Tester cache was excluded to
avoid double counting.

## Frozen expected window

- Start month: `201801`.
- End month: `202607`.
- Expected monthly files: `103`.
- Complete-file metadata gate: every month present, no zero-byte file, and no
  file below 1 MiB. This is only a coarse pre-payload capability gate; it does
  not prove tick integrity, timestamp continuity or broker semantics.

## Result

| Symbol | Months | First-last | Missing | Zero | Under 1 MiB | Total GiB | Minimum bytes | Maximum bytes |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| EURUSD | 103 | 201801-202607 | 0 | 0 | 0 | 1.025 | 4,100,839 | 26,068,657 |
| GBPUSD | 103 | 201801-202607 | 0 | 0 | 0 | 1.414 | 6,591,140 | 32,596,724 |
| USDJPY | 103 | 201801-202607 | 0 | 0 | 0 | 1.475 | 4,275,873 | 43,704,942 |
| XAUUSD | 2 | 202606-202607 | 101 | 0 | 0 | 0.242 | 126,853,307 | 132,504,142 |
| AUDUSD | 43 | 202301-202607 | 60 | 0 | 0 | 0.499 | 5,364,924 | 37,422,930 |
| USDCAD | 43 | 202301-202607 | 60 | 0 | 0 | 0.470 | 6,638,785 | 22,265,211 |
| USDCHF | 43 | 202301-202607 | 60 | 0 | 0 | 0.446 | 5,397,409 | 24,522,345 |
| BTCUSD | 43 | 202301-202607 | 60 | 0 | 1 | 2.172 | 47,212 | 312,541,612 |
| NZDUSD | 14 | 202506-202607 | 89 | 0 | 0 | 0.175 | 6,932,700 | 26,938,074 |

The anomalous BTCUSD file is `202310.tkc`, 47,212 bytes. No inference about
its payload is permitted from size alone.

## Decision

`SOURCE_CAPABILITY_PASS_METADATA_ONLY` for EURUSD, GBPUSD and USDJPY.

This materially changes the lawful discovery frontier: the same broker that
would execute the EA already has a local 2018-latest monthly tick surface for
three FX symbols. It removes the external-provider train/serve mismatch for a
possible tick-derived mechanism. It does not create an edge or authorize an EA.

XAUUSD, BTCUSD and the shorter-history FX symbols fail the current 2018-latest
metadata gate and are excluded from this pass.

## Next frozen gate

Before reading tick values or minting a hypothesis ID:

1. De-duplicate the intended tick information family against the candidate
   registry, failure catalog and surviving EA source tree.
2. Require a named microstructure mechanism with a fixed closed-M5/M15 mapping;
   generic quote momentum, spread recovery, absorption and VRAS relabels are
   not fresh candidates.
3. Freeze a counts-only export contract covering month presence, tick flags,
   timestamp monotonicity, duplicate timestamps, Bid/Ask validity, spread
   validity and closed-bar tick counts. No returns or forward outcomes enter
   this qualification stage.
4. Only after source qualification may a separate preregistration freeze the
   information transform, direction, holding period, risk, costs, design/OOS/
   holdout windows and Model-0 acceptance gates.

