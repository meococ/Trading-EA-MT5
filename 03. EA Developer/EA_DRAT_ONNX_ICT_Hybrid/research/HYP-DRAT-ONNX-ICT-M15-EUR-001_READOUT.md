# Readout — HYP-DRAT-ONNX-ICT-M15-EUR-001

Status: `KILL_AT_OFFLINE_PROBE`

Generated: 2026-07-16T05:04:24Z

## Frozen test

- Data: EURUSD M15, FivePercentOnline-Real history, completed bars only.
- Train: 2020-01-01 through 2023-12-31.
- Untouched probe: 2024-01-01 through 2026-06-30.
- Control: rules-only sweep -> MSS -> FVG/OB retest state machine.
- Challenger: identical state machine plus frozen regime/breakout classifier
  gate.
- Fill/cost proxy: next-bar open, same-bar collision scored SL-first, 0.10R
  round-trip falsification cost. This is not verified execution cost.

## Result

| Metric | Rules-only control | ONNX-gated challenger |
|---|---:|---:|
| Trades | 402 | 287 |
| Trades / elapsed week | 3.0855 | 2.2029 |
| PF after proxy cost | 0.7642 | 0.7488 |
| Net R after proxy cost | -67.7523 | -52.8236 |
| Win rate | — | 32.06% |

Challenger yearly net R was negative in every inspected bucket: 2024
`-33.6745R`, 2025 `-14.0022R`, and 2026 partial `-5.1469R`.

The classifiers learned their causal labels adequately enough for the probe:
regime accuracy `0.8709`, regime log loss `0.3770`, breakout Brier `0.00449`.
This did not create a trading edge. The ONNX gate reduced sample count while PF
fell below the already-losing rules-only control.

## Frozen gate decision

PASS:

- breakout Brier <= 0.25;
- challenger cadence stayed within 2-5 trades per elapsed week;
- challenger net loss was smaller than control net loss.

FAIL:

- challenger PF < 1.15;
- challenger net R <= 0;
- challenger PF below control;
- 2024 and 2025 were not both positive.

Verdict is therefore `KILL_AT_OFFLINE_PROBE`. No EA source, ONNX export,
compile, Strategy Tester run or Model 0 claim is authorized under this ID. Any
threshold, session, hold-time, RR or model change would be post-hoc rescue.

## Evidence

- Summary JSON: `HYP-DRAT-ONNX-ICT-M15-EUR-001_OFFLINE_PROBE.json`
  - SHA256: `2A1A48AA8D37416AEEC4E475D6C22238603348B72622359B151D68350F79EF69`
- Trade outcomes: `HYP-DRAT-ONNX-ICT-M15-EUR-001_OFFLINE_TRADES.json`
  - SHA256: `64185C269E7FB5851C31967DBA1A93EC74AE76ECC2BEAC37E891545F0ABA8D78`
- Frozen prereg SHA256:
  `2B5A267E994BAF67A6FE9CFC60E5481B5BD95F6A60D1DD2FB7572EEC31012BF2`
- Frozen probe script SHA256:
  `32BC133EF3152745543FFAF93C3C3D4D64138DB6CE67C1AB0C978F7851A9AB85`

## Storage closeout

Raw training bars stayed in memory and were not written to disk. After the
workflow-owned MT5 terminal was stopped, the protected C roots were searched
for files modified since probe start. No new disposable tester/train/log file
was present, so no deletion was performed. Shared history/account/config were
left untouched.
