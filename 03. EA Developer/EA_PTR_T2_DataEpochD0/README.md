# EA_PTR_T2_DataEpochD0

Minimal T2/P4 D0 data-epoch synchronization probe for the frozen
`PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH.json` contract.

Scope:
- Intended timeframe: `M5`.
- Required generation binding: `T2`.
- Required epoch manifest SHA256:
  `F47901F60E4314321B4B201ACED1D8D7366AC5D64589C487E893F0153332F648`.
- Telemetry profile: `none`.

Behavior:
- `OnInit` fails closed when `InpHypothesisId` is empty, generation is not `T2`,
  epoch manifest SHA is not exact, collection-only mode is disabled, or runtime
  timeframe is not `M5`.
- `OnTick` observes only the last completed M5 bar via `iTime(_Symbol, PERIOD_M5, 1)`.
- Journal markers are deterministic: `DATA_EPOCH_D0_READY`,
  `DATA_EPOCH_D0_FIRST_CLOSED_BAR`, and `DATA_EPOCH_D0_SUMMARY`.
- The summary reports closed-bar count plus first/last closed-bar timestamps
  from the tester chart series.

Prohibitions:
- No trade API, order checks, account mutation, position/deal inspection, PnL,
  SL/TP, file writes, `FILE_COMMON`, sidecars, indicators, optimization hooks,
  or outcome metrics.
- This package does not grant registry, preregistration, Model 0 economics,
  promotion, paper, or live authority.
