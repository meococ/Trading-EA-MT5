# HYP-MFI-XAUUSD-M5-001 — Frozen Source/Cadence Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`  
Frozen before any MFI calculation or event count on the specified design window.

## Identity and thesis

- Hypothesis ID: `HYP-MFI-XAUUSD-M5-001`
- Package: `EA_MFIExtremeReentry`
- Family: `tick-volume-weighted-mfi14-extreme-reentry`
- Symbol/timeframe: FivePercent `XAUUSD`, native M5 Bid bars
- Public design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation: 2023–2024 sealed
- Final holdout: 2025+ sealed
- Sole attempt: `MFI001-SOURCE-ATTEMPT-001`

TradingView documents MFI as a 0–100 oscillator combining typical price and volume, with default length 14 and conventional extreme levels 20/80. The research question is whether completed-bar re-entry from those extreme states occurs with a stable 2–5/week population before any trade outcome is considered.

On this CFD, `tick_volume` is only unsigned broker quote activity. The terms positive/negative money flow below are indicator arithmetic based on typical-price change, not real cash flow, trade direction, exchange volume or aggressor pressure.

## Exact completed-bar indicator

For each completed M5 bar `i`:

1. `TP(i) = (high(i) + low(i) + close(i)) / 3`.
2. `RawFlow(i) = TP(i) * tick_volume(i)`.
3. If `TP(i) > TP(i-1)`, positive flow is `RawFlow(i)` and negative flow is zero.
4. If `TP(i) < TP(i-1)`, negative flow is `RawFlow(i)` and positive flow is zero.
5. If typical prices are equal, both flows are zero.
6. `Pos14(i)` and `Neg14(i)` are sums over exactly `i-13..i`.
7. If both sums are positive, `MFI14(i) = 100 - 100/(1 + Pos14/Neg14)`.
8. If only positive sum is positive, MFI is 100; if only negative sum is positive, MFI is zero; both zero is invalid/fail-closed.

An MFI value is usable only if all exact price/tick-volume inputs `i-14..i` are finite, geometrically valid and have positive tick volume. An event at `t` additionally requires a usable `MFI14(t-1)`, so the complete event input is `t-15..t`.

Frozen event on completed bar `t`:

- LONG: `MFI14(t-1) <= 20.0` and `MFI14(t) > 20.0`;
- SHORT: `MFI14(t-1) >= 80.0` and `MFI14(t) < 80.0`;
- simultaneous direction is invalid;
- decision time is source-bar open plus five minutes;
- the immediately following source timestamp must be exactly five minutes later;
- no next-row price may be read;
- no wick, ATR, Relative Volume, session, trend, divergence, price pattern, debounce, daily cap or subgroup filter.

This is extreme re-entry only. It does not claim to implement TradingView's separate four-step “failure swing” pattern.

## Frozen source

- Manifest: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json`
- Manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- Data: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet`
- Data SHA256: `12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380`
- Reader predicate: `2018-01-01T00:00:00Z <= time_utc < 2023-01-01T00:00:00Z`
- Allowed columns only: `symbol`, `timeframe`, `source_epoch`, `time_utc`, `utc_ambiguous`, `high`, `low`, `close`, `tick_volume`
- Forbidden: open/spread/real_volume, post-event OHLC, returns, labels, entries/exits, MFE/MAE, PnL, PF and drawdown

## Frozen gates

All gates must pass:

1. exact preregistration, manifest, data, analyzer and one-shot registry bindings;
2. rows are XAUUSD/M5, UTC-unambiguous, unique, strictly increasing and wholly inside design;
3. at least 300,000 design rows;
4. exact MFI feature coverage at least 99.0% after the first 15 unavailable rows; the first usable event is row 16 because its complete input is `t-15..t`;
5. exact-next-M5 timestamp coverage at least 97.0%;
6. at least 500 events;
7. pooled cadence 2.0–5.0 events per elapsed calendar week;
8. LONG and SHORT share each at least 30%;
9. no year contributes more than 30%;
10. every design year cadence is 1.25–6.50/week;
11. candidate ledger has only timestamp, direction and current/prior MFI source fields;
12. in-attempt deterministic replay is byte-identical.

Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_MFI_REENTRY`; no same-ID rerun, threshold rescue, MQL5 build or economics. All pass gives `SCREENED_SOURCE_PASS_MQL5_IMFI_BUILD_AUTHORIZED`, authorizing only native `iMFI(..., VOLUME_TICK)` implementation/parity/correctness work, not trading economics.

## De-duplication

Repository text/registry search found no prior MFI hypothesis. This state transition is distinct from:

- TVER high Relative Volume + low ATR progress + wick rejection;
- TFCVD real-tick quote polarity;
- VCEX volume-clock exhaustion;
- ECRS compression breakout;
- ASRS pivot sweep/retest;
- ARUC signed same-slot activity-response continuation;
- LVOR low-activity price overshoot/reversal.

Failure radius is only this exact XAUUSD M5 MFI14 20/80 completed-bar re-entry mapping on 2018–2022.

## Authority exclusions

No post-event price, trade, stop, target, sizing, cost, PF, drawdown, optimization, validation, holdout, chart selection, MT5 tester, MQL5 build, paper, promotion or live authority exists in this attempt.
