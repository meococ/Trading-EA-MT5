# HYP-RSF-USDJPY-M5-STATE-MODEL-014 - result

## Verdict

`KILL_NO_STABLE_DISCOVERY_EDGE`

USDJPY behaves materially better than EURUSD under the same five-indicator
state model, but the M5 edge does not survive the preregistered dynamic cost or
year stability gates. The 2023-and-later validation period remains sealed.

## Census evidence

- AlphaFactory run: `20260808_010744`.
- Model 0, USDJPY M5, tester envelope 2018-01-01 to 2023-01-01.
- History quality 100%; 372,903 bars; 110,725,834 ticks.
- Census rows 372,902 across 58 columns; zero duplicate timestamps, missing
  cells or non-finite cells.
- Indicator readiness 372,903/372,903 closed bars.
- Entries/final closes 0/0; lifecycle sidecar is header-only.
- AlphaFactory's economic analyzer rejected `No trades found in report` after
  the valid zero-trade run. Required artifacts were already collected; no
  second census was run.

## Preregistered discovery

All six frozen Ridge/shallow-HGB x 3/6/12-bar cells and all 72 train-threshold
fold evaluations were executed. Point geometry was bound at 0.001. Each trade
paid observed spread times
`1.5 + 0.15 * (1 + VRC volatility percentile / 100)`.

No cell survived. Best was Ridge/12 bars:

- 931 primary-threshold trades;
- cadence valid in three yearly folds;
- pooled net PF 0.942903 and net -56.066289 ATR-R;
- median yearly PF 0.968103;
- adjacent cadence PF 0.989295 and 0.895019;
- 2019/2021 lost; 2020/2022 won.

The same best cell had gross PF 1.327617 and +259.469550R before friction, but
dynamic cost consumed 315.535839R. Long and short books both ended below PF
0.95 after cost. This is a cost-dominated M5 signal, not a net edge.

## Indicator and timezone diagnosis

2022 permutation diagnostics ranked MBB, QQE and UTC cyclic terms above TB;
AIRD and VRC had no positive marginal MSE contribution in that fold. This does
not authorize deleting regime indicators: AIRD/VRC remain useful as routers,
but the all-in-one directional regressor did not use them stably.

Some UTC hours and regimes look profitable in the post-hoc failure diagnostic,
while others are strongly negative. They may not be filtered under this ID.
The correct successor changes the sampling resolution to M15, which reduces
spread/ATR pressure and recomputes all five indicators on M15. It must be
preregistered before collection and use no hour/day filter from this readout.

## Failure radius

This kills the exact USDJPY M5 simultaneous-state directional-return surface.
No session, direction, year, threshold or feature-family rescue is allowed.
It does not test five-indicator M15 state, because M15 indicators and their
warm-up/state transitions are not recoverable by resampling M5 outputs.

## Bound artifacts

- Census SHA256: `0EA3B2E17817188AA5B55A4B3E03D893943C0B08ADED4C8792DD8660D687A57B`
- RunMeta SHA256: `79869FB66B104B5E9CC63FE9B770D7C70B64C8C04517FFAB593C13C0BBF1F5A0`
- Report SHA256: `1EA19248D15AEACDD8092F3AD9DBF8E75DAC0FF8002C2A32D35DE5D57832928E`
- Run manifest SHA256: `D68CD344D265A25C83AACEA0BBF150E0A9DA805C12AA7E508CCBDE86E28E46DF`
- Results SHA256: `C2B0F4DE18B26C207F7FF21FD9B7D2957B0426C05BC686A5DC5EAA839446D237`
- Walk-forward folds SHA256: `EB3993DBDC1E80FEC0640383D7FC691E9221A8A55A3160CFEA9934F0DED9D5D8`
- Feature diagnostics SHA256: `213F0160308E33ECB27E9FF0B48CCED9E3979FBA594C9EAFBAF0DCC2CF9D8D04`
- Failure diagnostic SHA256: `6B60A257948015D5EA5BA670B7C3B6B07E06394CEEB808628122D140C9133B4A`

