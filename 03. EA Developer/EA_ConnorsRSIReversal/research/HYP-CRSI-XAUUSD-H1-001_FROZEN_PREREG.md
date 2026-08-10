# HYP-CRSI-XAUUSD-H1-001 — Frozen Connors RSI Extreme-reentry Source Preregistration

Status: `FROZEN_PRE_OUTCOME_SOURCE_ONLY`  
Informing evidence: the terminal Supertrend campaign is abandoned without an economic claim; no Connors RSI outcome informed this object.

## Identity and market thesis

- Hypothesis: `HYP-CRSI-XAUUSD-H1-001`
- Family: `connors-rsi-3-2-100-short-horizon-extreme-reentry`
- Symbol/timeframe: FivePercent XAUUSD native H1 Bid bars
- Design: `[2018-01-01T00:00:00Z, 2023-01-01T00:00:00Z)`
- Validation 2023–2024 and holdout 2025+ remain sealed
- Sole source attempt: `CRSI001-SOURCE-ATTEMPT-001`

TradingView documents Connors RSI as the average of Wilder RSI on price, Wilder RSI on the consecutive up/down streak, and the percentile rank of one-bar rate of change. The canonical defaults are `(3,2,100)`, with original oversold/overbought levels below `10` and above `90`. This is a short-horizon mean-reversion information object: it jointly measures immediate velocity, persistence of consecutive closes, and how unusual the latest return is relative to its own recent distribution.

The repository de-dup scan found no prior Connors RSI / CRSI object. It is materially different from Supertrend recursive ATR-band flips, Vortex range polarity, MFI volume-price flow, Ichimoku cloud alignment, VWAP regimes, sweep/retest and compression-breakout objects.

Formula provenance is TradingView's official Connors RSI help page. TradingView is research provenance only; MT5-native source data, direct MQL5 implementation and AlphaFactory evidence remain the sole acceptance path. No official MQL5 `iConnorsRSI` handle is claimed.

## Exact causal formula

All calculations use completed native H1 `close` values. Bar-count lookbacks span normal market closures. Indicator state is calculated continuously from the exact first native H1 row `2004-06-11T04:00:00Z` through `<2023`; it is never seeded or reset at the 2018 scoring boundary.

### Wilder RSI

For any finite series `X` and length `n`:

- `delta[i] = X[i] - X[i-1]`
- `gain[i] = max(delta[i], 0)`
- `loss[i] = max(-delta[i], 0)`
- at index `n`, seed average gain/loss as the arithmetic mean of deltas `1..n`;
- afterward use Wilder RMA: `avg[t] = ((n-1)*avg[t-1] + current[t]) / n`;
- if both averages are zero, RSI is `50`; if average loss alone is zero, RSI is `100`; if average gain alone is zero, RSI is `0`; otherwise `100 - 100/(1 + avg_gain/avg_loss)`.

### Up/down streak

- `streak[0] = 0`;
- if `close[i] > close[i-1]`, `streak[i] = max(streak[i-1],0)+1`;
- if `close[i] < close[i-1]`, `streak[i] = min(streak[i-1],0)-1`;
- equality resets `streak[i]=0`.

### Percent rank and CRSI

- `roc1[i] = 100 * (close[i]/close[i-1] - 1)`; close must be finite and strictly positive.
- `percent_rank100[t] = count(roc1[j] < roc1[t] for j=t-100..t-1)` because the denominator is exactly 100; equality is not below.
- `CRSI[t] = (RSI3(close)[t] + RSI2(streak)[t] + percent_rank100[t]) / 3`.

The current CRSI at `t` requires closes `t-101..t`; prior CRSI at `t-1` requires closes `t-102..t-1`. The signal union is exactly `t-102..t`, so the first possible source event is index `102` of the full inception frame. All 103 source bars in that union must be finite, have strictly positive close, and satisfy finite geometry `high>=low` and `low<=close<=high`. Flat `H=L=C` bars are valid and are not skipped or reset.

## Frozen signal and execution mapping

- raw LONG at completed bar `t`: prior `CRSI < 10` and current `CRSI >= 10`;
- raw SHORT: prior `CRSI > 90` and current `CRSI <= 90`;
- equality at the current re-entry threshold confirms the event; equality on the prior bar is not armed;
- the signal is the first confirmed re-entry from the official extreme, not entry into the extreme, failure swing, divergence or trend-filtered continuation;
- an executable event requires the immediately following native H1 timestamp to equal `t+1 hour`;
- a raw event followed by a gap is consumed and not persisted;
- only the next timestamp is inspected; no next price is read;
- decision timestamp is `t+1 hour`.

Forbidden: threshold changes, entry-into-extreme substitution, trend/session/news/price/volume/ATR/ADX/VWAP/Fisher filters, cooldown/debounce, position state, stop/target, optimization and outcome fields.

## Frozen source and gates

- Canonical manifest SHA256: `D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23`
- Native H1 data SHA256: `B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3`
- Data path: `02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet`
- Only symbol/timeframe/source epoch/time/UTC ambiguity/high/low/close may be read.
- PyArrow materializes the exact native inception through `<2023`, followed by fail-closed inception and upper-bound assertions. Only `[2018,2023)` rows enter event/gate scoring; pre-2018 rows exist solely to initialize the causal indicator state.

All gates must pass:

1. hash/registry/one-shot bindings and byte-identical replay;
2. exact full-source inception `2004-06-11T04:00:00Z` and at least 25,000 design rows;
3. feature coverage at least 99.0% across all design rows, because prehistory supplies the 102-row dependency;
4. exact-next H1 coverage at least 97.0% of raw extreme entries;
5. at least 500 executable events;
6. pooled cadence 2.0–5.0/week;
7. each direction at least 30%;
8. no calendar year above 30% of executable events;
9. each calendar year cadence 1.25–6.50/week;
10. zero direction conflicts;
11. exact source-only event-ledger allowlist.

Calendar-year cadence and concentration use the executable event's decision timestamp. Any failure gives `PARK_SOURCE_FEASIBILITY_EXACT_CRSI_3_2_100_EXTREME_REENTRY`. All pass gives `SCREENED_SOURCE_PASS_DIRECT_MQL5_CRSI_BUILD_AUTHORIZED`, allowing only indicator/formula implementation, compile, non-repaint and MT5 parity work under a fresh reviewed child. Economics remains unauthorized.

## Authority boundary

No source data may be opened until analyzer/tests/hashes receive independent review and the registry contains one exact unconsumed source-only authority row. This preregistration grants no MQL5 build, MT5 tester, economics, validation, holdout, paper, promotion or live authority.

References:

- TradingView Connors RSI formula and default parameters: `https://www.tradingview.com/support/solutions/43000502017-connors-rsi-crsi/`
- TradingView RSI/Wilder RMA formula: `https://www.tradingview.com/support/solutions/43000502338-relative-strength-index-rsi/`
