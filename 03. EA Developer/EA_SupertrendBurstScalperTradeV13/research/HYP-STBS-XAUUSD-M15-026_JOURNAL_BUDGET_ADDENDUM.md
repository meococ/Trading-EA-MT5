# HYP026 inherited journal-budget engineering addendum

## Informing failure

HYP023 is terminally killed only for truncated journal evidence. Its sealed failure packet and post-failure review remain unchanged. HYP024 froze the resulting four-MiB V11 journal contract but never reached MT5 because of a separate authority omission. HYP025/V12 then terminalized before Alpha because the post-claim validator rejected its own exact one-shot marker. This addendum carries the unchanged journal contract into the fresh HYP026/V13 identity-only clone; it does not reopen any prior outcome or change strategy logic.

The unique HYP023 run segment from `STBS_INIT` through `STBS_SUMMARY` was measured independently in both native UTF-16 tester sources before another MT5 run:

| Source | Full lines | Full raw bytes | `STBS_MARGIN_STRESS_UNSAFE` | Projected lines after exact spam deletion | Projected raw bytes |
|---|---:|---:|---:|---:|---:|
| Tester | 23,452 | 7,844,888 | 19,736 | 3,716 | 871,692 |
| Agent | 23,452 | 9,371,456 | 19,736 | 3,716 | 858,852 |
| Combined | 46,904 | 17,216,344 | 39,472 | 7,432 | 1,730,544 |

Source-log hashes at measurement time:

- Tester `20260810.log`: `A61731C4B1DB51B25BDA36418518C91E69A50857CA0E79121DA9B7713CDEAF06`
- Agent `20260810.log`: `075CA7B1574CAE711C8AA58963DCBB4570A27079FD30DA8BF655EE5847525886`

## Revision boundary

Removing the per-volume print alone would still exceed the former combined one-MiB raw cap. Raising the cap alone would retain more than 17 MiB of spam and also fail. HYP026 inherits the same two already-reviewed engineering controls:

1. Delete only the nondecision `STBS_MARGIN_STRESS_UNSAFE` `PrintFormat` inside `EvaluateMarginCandidate`. Preserve every computation, branch, loop iteration, selected volume and return value.
2. Freeze an explicit combined raw journal cap of `4,194,304` bytes through the HYP026 task packet, receipt and AlphaFactory normalized manifest. Other hypotheses that omit the field retain the one-MiB default.

Four MiB is 2.42 times the exact no-spam replay size. Two MiB has only about 21% headroom; eight MiB is not justified by the measured run. Completeness remains fail-closed: any run at or above the cap, missing terminal summary, unequal duplicate payload, missing sidecar or semantic mismatch is invalid.

No signal, indicator, timeframe, entry, margin threshold, requested volume, order, stop, target, holding, cost, acceptance or risk parameter changes are authorized.
