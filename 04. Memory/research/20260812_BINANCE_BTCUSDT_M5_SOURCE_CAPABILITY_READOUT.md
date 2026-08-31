# Binance BTCUSDT closed-M5 taker-flow capability readout

UTC checkpoint: `2026-08-12T12:13:29Z`  
Verdict: `NO_CANDIDATE_TARGET_HISTORY_GATE_FAIL`  
Stage: pre-hypothesis, source/capability only  
Economics opened: no  
EA/MT5 opened: no

## Proposed information object

- Source: official Binance Spot `BTCUSDT` closed 5-minute kline.
- Permitted fields: open time, close time, total base volume `v`, taker-buy
  base volume `V`, trade count `n`, and live closed flag `x`.
- Derived field considered: signed taker imbalance `I = (2*V-v)/v`, available
  only after the source bar is closed.
- Causal thesis considered: extreme signed aggressive flow on a major BTC
  price-discovery venue may carry into the immediately following FivePercent
  `BTCUSD` CFD M5 bar.
- Sonic-R/Dragon was not an edge input. No threshold, lookback, tail
  probability, direction subset, session, cooldown, stop or target was chosen.

## Official Binance source receipt

Official documentation:

- `https://github.com/binance/binance-public-data/blob/master/README.md`
- `https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md`
- S3 listing endpoint:
  `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?list-type=2&prefix=data%2Fspot%2Fmonthly%2Fklines%2FBTCUSDT%2F5m%2F`

The official archive documents daily/monthly publication, 5m/15m kline
support, `v/V/Q/n`, a checksum beside every ZIP, a January 2025 change from
millisecond to microsecond timestamps, and an exhaustive replacement-file
update list. The live UTC WebSocket kline provides `x` as the close flag and
`V` as taker-buy base volume.

Observed listing receipt:

- listing UTF-8 bytes: `59,292`
- listing SHA256: `C42831739108BB57A714D9BA3833ABF0258D125F89D652CF9F021922C1E6E643`
- exact requested range: `2018-01` through `2026-07`
- months: `103`; ZIP objects: `103`; CHECKSUM objects: `103`
- missing months: `0`; pair anomalies: `0`
- aggregate ZIP bytes: `47,496,825`
- latest object modification in the range: `2026-08-03T10:34:38Z`

Boundary samples were read in memory and not retained as a local dataset:

| Month | ZIP bytes | ZIP SHA256 | Rows | Columns | Time unit | Checksum |
|---|---:|---|---:|---:|---|---|
| 2018-01 | 465,740 | `C08222EAD41339FE656AC2E4389D365A0CADCC0E24C6E538BB76006E4E9EE5E0` | 8,904 | 12 | ms | match |
| 2026-07 | 457,771 | `425F6E1A0DE85DC99D8A7F17924BCB210C8F92100FB71E5993E1D197577B7053` | 8,928 | 12 | us | match |

Source conclusion: free replay, field identity, integrity and live closed-bar
semantics are defensible. Archive revisions require snapshot hashes plus the
official replacement changelog, but this is handleable and is not the terminal
blocker.

## FivePercent target-history receipt

Authority:

- dataset manifest:
  `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json`
- manifest SHA256:
  `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- target file:
  `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/BTCUSD/BTCUSD_M5_ALL_AVAILABLE_20260801.parquet`
- target SHA256:
  `5B4DA734215BA56DE0DEA7C33E06ECC74C44EDE1CED9986AEB5B98F4B2053AE0`
- target contract: native FivePercent broker Bid M5 bars, source epoch primary;
  no interpolation or synthetic filling.

Metadata-only coverage audit:

| Year | Rows | 24x7 M5 denominator | Coverage | Gaps >5m | Largest gap |
|---|---:|---:|---:|---:|---:|
| 2018 | 7,839 | 105,120 | 7.4572% | 7,838 | 50.00h |
| 2019 | 24,843 | 105,120 | 23.6330% | 24,842 | 49.25h |
| 2020 | 24,955 | 105,408 | 23.6747% | 24,954 | 72.25h |
| 2021 | 62,805 | 105,120 | 59.7460% | 11,274 | 48.25h |
| 2022 | 102,297 | 105,120 | 97.3145% | 130 | 8.00h |
| 2023 | 101,586 | 105,120 | 96.6381% | 315 | 46.83h |
| 2024 | 104,760 | 105,408 | 99.3852% | 394 | 1.58h |
| 2025 | 103,794 | 105,120 | 98.7386% | 370 | 7.00h |
| 2026 to 2026-08-02 | 60,499 | partial year | n/a | 215 | 1.25h |

The old years are not merely a few missing intervals: every adjacent observed
bar is separated by more than five minutes in 2018-2020. No broker-session
calendar or other authoritative evidence was found that can turn this sparse
surface into a complete independent `2018-latest` target receipt.

## De-dup and literature boundary

- This source is materially different from
  `HYP-TFCVD-XAUUSD-M5-001`, whose terminal issue was generated broker quote
  ticks and zero proven historical real-tick provenance. That failure radius
  explicitly permits a fresh PIT source/new ID; official Binance `v/V/n/x` is
  true exchange trade-side data, not a candle tick-volume substitute.
- Published BTC price-discovery work supports Binance as an important venue,
  but signed volume evidence is mainly contemporaneous. It does not establish
  a profitable next-FivePercent-bar map.
- Published order-flow work also reports market-order flow is not the whole
  price-discovery object, and recent 1m-to-5m evidence is weak after costs.
  The economic prior is therefore adverse, though not itself a source kill.

## Terminal decision

`NO_CANDIDATE_TARGET_HISTORY_GATE_FAIL`

The Binance source is technically usable, but the proposed sleeve has no
lawful route to the current GOAL because its execution target cannot provide a
defensible independent 2018-latest M5 history receipt. A counts-only source run
cannot create missing target bars, so no hypothesis ID, threshold, analyzer,
download, EA, MQL5 build or MT5 baseline is authorized.

Narrow failure radius: Binance Spot closed-M5 taker imbalance mapped into the
current FivePercent `BTCUSD` M5 target under the mandatory 2018-latest evidence
contract. This is not a market/economic verdict on Binance taker flow and does
not ban the information object on a future complete target.

Reopen only with genuinely new evidence:

1. a continuous, gap-audited, allowed-host `BTCUSD` M5 target from 2018-latest,
   or an explicit Owner change to the evidence period;
2. the same checksum-pinned Binance archive plus timestamp-unit and revision
   controls; and
3. an ex-ante fixed counts-only contract before any source cadence or target
   outcome is read.

Bounded Grok review independently returned `NO_CANDIDATE` for the same
target-history blocker. No outcome, backtest, EA, payment, trial or Git
operation occurred in that review.
